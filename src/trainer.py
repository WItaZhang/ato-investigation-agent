"""Run and evaluate the investigation workflow; no model training is performed."""

import json

from .data import load_dataset
from .detector import scan
from .investigation import cards_for, census_gate, diagnose, merge_candidates, validate_verdicts
from .llm import Analyst
from .model import Assessment, Investigation
from .synthetic import generate
from .utils import start_run, write_json


def run(root, config, prepare_only=False, analyst_factory=Analyst):
    run_dir, logger = start_run(root, config)
    metrics = {"status": "running", "live_llm_verified": False}
    try:
        logger.info("Generating synthetic inputs; labels are isolated from model inputs")
        data, labels = generate(config)
        staging = root / config["data"]["staging_path"] / run_dir.name
        write_json(staging / "dataset.json", data)
        write_json(staging / "labels.json", labels)
        data = load_dataset(staging / "dataset.json")
        target = config["synthetic"]["target_date"]
        candidates = scan(data["events"], target, config["scan"])
        groups = merge_candidates(candidates, config["investigation"]["merge_overlap"])
        processed = root / config["data"]["processed_path"] / run_dir.name
        write_json(processed / "candidates.json", candidates)
        write_json(processed / "groups.json", groups)
        cards = {g["id"]: cards_for(data, g["account_ids"], target) for g in groups}
        write_json(processed / "cards.json", cards)
        metrics.update(groups=len(groups), candidates=len(candidates),
                       processed_path=str(processed), staging_path=str(staging))
        if prepare_only:
            metrics["status"] = "prepared_only"
            logger.info("Preparation finished; no model call or adjudication performed")
            return run_dir
        analyst = analyst_factory(config["llm"], run_dir)
        results, predictions = [], {}
        for group in groups:
            group_cards = cards[group["id"]]
            verdicts = []
            batch_size = config["llm"]["batch_size"]
            if batch_size <= 0:
                raise ValueError("batch_size must be positive")
            for start in range(0, len(group_cards), batch_size):
                batch = group_cards[start:start + batch_size]
                answer = analyst.ask(config["llm"]["assessment_prompt"], batch, Assessment)
                validate_verdicts(batch, answer.verdicts)
                verdicts.extend(answer.verdicts)
            gate = census_gate(group_cards, verdicts, config["investigation"]["takeover_gate"])
            result = {"group_id": group["id"], "gate": gate,
                      "verdicts": [v.model_dump() for v in verdicts]}
            if gate["status"] == "pass":
                gaps = diagnose(group_cards)
                write_json(processed / f"{group['id']}-policy-evidence.json", gaps)
                # Synthesis is bounded to account examples; the gate covers the full cohort.
                payload = {"gate": gate, "cards": group_cards[:batch_size],
                           "policy_evidence": gaps[:batch_size]}
                summary = analyst.ask(config["llm"]["synthesis_prompt"], payload, Investigation)
                result["investigation"] = summary.model_dump()
                result["retrospective_status"] = "not_implemented"
            predictions.update({v.account_id: v.label for v in verdicts})
            results.append(result)
            write_json(processed / "results.json", results)
            logger.info("Group %s completed: %s", group["id"], gate["status"])
        matched = sum(predictions[aid] == labels[aid] for aid in predictions)
        tp = sum(v == "takeover" and labels[aid] == "takeover" for aid, v in predictions.items())
        fp = sum(v == "takeover" and labels[aid] != "takeover" for aid, v in predictions.items())
        actual_positive = sum(v == "takeover" for v in labels.values())
        metrics.update(status="completed_prototype", live_llm_verified=analyst_factory is Analyst,
                       evaluated=len(predictions), label_agreement=matched / len(predictions) if predictions else None,
                       precision=tp / (tp + fp) if tp + fp else None,
                       recall=tp / actual_positive if actual_positive else None,
                       reserved_usd=analyst.reserved, actual_usd=analyst.actual)
        report = ["# Synthetic ATO investigation prototype", "",
                  "This run does not establish real-world detection accuracy.", "",
                  f"Groups: {len(groups)}. Evaluated accounts: {len(predictions)}.", ""]
        for result in results:
            report += [f"## {result['group_id']}", "", f"Gate: {result['gate']['status']}", ""]
            if "investigation" in result:
                report += [json.dumps(result["investigation"], ensure_ascii=False, indent=2), ""]
        (run_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
        return run_dir
    except Exception as exc:
        metrics.update(status="failed", error_type=type(exc).__name__)
        # Do not serialize exception bodies, which can contain provider request data.
        logger.error("Run stopped: %s", type(exc).__name__)
        raise
    finally:
        write_json(run_dir / "metrics.json", metrics)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
