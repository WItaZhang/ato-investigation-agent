import json
from pathlib import Path

import pytest
import yaml

from src.investigation import census_gate, merge_candidates, validate_verdicts
from src.llm import Analyst, BudgetExceeded
from src.model import Assessment, Investigation, Verdict
from src.trainer import run


def config():
    return yaml.safe_load(Path("configs/investigation.yaml").read_text())


def test_rejects_fabricated_evidence_and_missing_accounts():
    cards = [{"account_id": "a", "evidence": [{"id": "e"}]}]
    with pytest.raises(ValueError):
        validate_verdicts(cards, [])
    with pytest.raises(ValueError):
        validate_verdicts(cards, [Verdict(account_id="a", label="takeover",
                                        reason="claim", evidence_ids=["fabricated"])])


def test_uncertain_accounts_cannot_pass_gate():
    cards = [{"account_id": "a", "evidence": [
        {"id": "e", "risk": {"final_action": "allow"}}]}]
    verdicts = [Verdict(account_id="a", label="uncertain", reason="missing evidence",
                        evidence_ids=["e"])]
    assert census_gate(cards, verdicts, 0.3)["status"] == "unresolved"


def test_overlap_bridge_does_not_merge_disjoint_groups():
    candidates = [{"account_ids": [1, 2]}, {"account_ids": [1, 2, 3, 4]},
                  {"account_ids": [3, 4]}]
    assert len(merge_candidates(candidates, 0.8)) == 2


def test_zero_budget_blocks_before_network(tmp_path):
    cfg = config()["llm"]
    cfg["budget_usd"] = 0
    analyst = Analyst(cfg, tmp_path, client=object())
    with pytest.raises(BudgetExceeded):
        analyst.ask("test", [], Assessment)
    assert analyst.calls == 0


def test_preparation_keeps_labels_out_of_cards(tmp_path):
    run_dir = run(tmp_path, config(), prepare_only=True)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    cards = json.loads((Path(metrics["processed_path"]) / "cards.json").read_text())
    assert metrics["status"] == "prepared_only"
    assert metrics["groups"] == 3
    assert not metrics["live_llm_verified"]
    assert all(set(card) == {"account_id", "evidence"}
               for group in cards.values() for card in group)


class StubAnalyst:
    """Test-only fixture interpreter; never shipped as an offline LLM mode."""
    def __init__(self, config, run_dir):
        self.reserved = self.actual = 0

    def ask(self, instructions, payload, schema):
        if schema is Investigation:
            return Investigation(summary="Fixture", entry="unknown", takeover="fixture",
                                 abuse="fixture", policy_gaps=["observe"], uncertainties=[])
        verdicts = []
        for card in payload:
            evidence = card["evidence"][0]
            label = ("takeover" if evidence["sensitive_actions"] else "not_takeover"
                     if evidence["owner_confirmed"] else "uncertain")
            verdicts.append(Verdict(account_id=card["account_id"], label=label,
                                    reason="Test fixture only", evidence_ids=[evidence["id"]]))
        return Assessment(verdicts=verdicts)


def test_pipeline_reconciles_and_evaluates_without_claiming_live_verification(tmp_path):
    run_dir = run(tmp_path, config(), analyst_factory=StubAnalyst)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["status"] == "completed_prototype"
    assert metrics["evaluated"] == 330
    assert metrics["recall"] == 1
    assert not metrics["live_llm_verified"]
    results = json.loads((Path(metrics["processed_path"]) / "results.json").read_text())
    assert {r["gate"]["status"] for r in results} == {"pass", "reject", "unresolved"}
