import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from threading import Barrier

import pytest

from accountguard.contracts import LoginEvent, ToolCall, make_call
from accountguard.harness import Harness, replay
from accountguard.policy import decide
from accountguard.tools import MockProtectionTool


def execute(tmp_path, fault="none", call=None, run_id="run", attempts=2):
    call = call or make_call(LoginEvent("e1", "a1", True, False, 0), "require_mfa")
    tool = MockProtectionTool(tmp_path / "actions.db", fault)
    harness = Harness(tool, tmp_path / f"{run_id}.jsonl", run_id, 0.02, attempts, 0)
    return asyncio.run(harness.run(call)), tool


@pytest.mark.parametrize("fault,expected", [
    ("none", "succeeded"), ("transient", "succeeded"), ("lost_ack", "succeeded"),
    ("timeout", "unknown"), ("timeout_after_effect", "succeeded"), ("exhausted", "failed"),
])
def test_failure_scenarios_have_replayable_outcomes(tmp_path, fault, expected):
    result, tool = execute(tmp_path, fault)
    assert result["state"] == expected
    assert replay(tmp_path / "run.jsonl")["state"] == expected
    assert tool.calls <= 2
    if fault == "timeout":
        assert tool.calls == 1


def test_lost_response_and_restart_do_not_duplicate_effect(tmp_path):
    execute(tmp_path, "lost_ack")
    execute(tmp_path, run_id="restart")
    with closing(sqlite3.connect(tmp_path / "actions.db")) as conn:
        assert conn.execute("SELECT count(*) FROM actions").fetchone()[0] == 1


def test_last_attempt_lost_ack_is_reconciled(tmp_path):
    result, _ = execute(tmp_path, "lost_ack", attempts=1)
    assert result["state"] == "succeeded"


def test_same_key_different_account_is_rejected(tmp_path):
    call = make_call(LoginEvent("e1", "a1", True, False, 0), "require_mfa")
    execute(tmp_path, call=call)
    result, _ = execute(tmp_path, call=replace(call, account_id="a2"), run_id="conflict")
    assert result["state"] == "failed"


def test_concurrent_duplicate_calls_commit_once(tmp_path):
    call = make_call(LoginEvent("e1", "a1", True, False, 0), "require_mfa")
    tools = [MockProtectionTool(tmp_path / "actions.db") for _ in range(2)]
    barrier = Barrier(2)

    def run(tool):
        barrier.wait(timeout=5)
        return asyncio.run(tool.execute(call))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, tools))
    assert len(results) == 2 and all(result["applied"] for result in results)
    with closing(sqlite3.connect(tmp_path / "actions.db")) as conn:
        assert conn.execute("SELECT count(*) FROM actions").fetchone()[0] == 1


def test_replay_rejects_tampered_sequence(tmp_path):
    execute(tmp_path)
    path = tmp_path / "run.jsonl"
    rows = path.read_text().splitlines()
    row = json.loads(rows[-1])
    row["sequence"] = 99
    rows[-1] = json.dumps(row)
    path.write_text("\n".join(rows))
    with pytest.raises(ValueError):
        replay(path)


def test_protocol_and_policy():
    with pytest.raises(ValueError):
        LoginEvent("e", "a", "true", False, 0)
    with pytest.raises(ValueError):
        ToolCall("shell", "a", "e", "review", "k")
    event = LoginEvent("e", "a", False, True, 0)
    assert decide(event, {"review_failure_threshold": 5})[0] is None
    assert decide(replace(event, failed_attempts=5), {"review_failure_threshold": 5})[0] == "review"


def test_unknown_fault_is_not_silently_accepted(tmp_path):
    with pytest.raises(ValueError):
        MockProtectionTool(tmp_path / "actions.db", "typo")
