"""Bounded retries, explicit outcomes and a replayable state trace."""

import asyncio
import json
from datetime import UTC, datetime

from .tools import RetryableError

TRANSITIONS = {
    "pending": {"running"},
    "running": {"retrying", "succeeded", "failed", "unknown"},
    "retrying": {"running"},
}
TERMINAL = {"succeeded", "failed", "unknown"}


class Harness:
    def __init__(self, tool, trace_path, run_id, timeout_seconds, max_attempts, retry_delay_seconds):
        if timeout_seconds <= 0 or max_attempts < 1 or retry_delay_seconds < 0:
            raise ValueError("Invalid execution limits")
        self.tool, self.path, self.run_id = tool, trace_path, run_id
        self.timeout = timeout_seconds
        self.max_attempts, self.delay = max_attempts, retry_delay_seconds
        self.state, self.sequence = "pending", 0
        # One exclusive file per invocation; never append a new run to an old trace.
        self.path.open("x", encoding="utf-8").close()

    def transition(self, state, event, attempt, call):
        if state not in TRANSITIONS.get(self.state, set()):
            raise ValueError(f"Invalid transition {self.state} -> {state}")
        self.sequence += 1
        record = {
            "schema_version": 1, "run_id": self.run_id, "sequence": self.sequence,
            "timestamp": datetime.now(UTC).isoformat(), "from": self.state,
            "state": state, "event": event, "attempt": attempt,
            "idempotency_key": call.idempotency_key, "request_fingerprint": call.fingerprint,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
        self.state = state

    async def run(self, call):
        for attempt in range(1, self.max_attempts + 1):
            self.transition("running", "attempt_started", attempt, call)
            try:
                result = await asyncio.wait_for(self.tool.execute(call), timeout=self.timeout)
            except TimeoutError:
                # A timeout alone cannot prove that a remote side effect did not happen.
                try:
                    result = self.tool.lookup(call)
                except Exception:
                    self.transition("unknown", "reconciliation_failed", attempt, call)
                    return {"state": self.state, "result": None}
                state = "succeeded" if result is not None else "unknown"
                self.transition(state, "timeout_reconciled" if result else "timeout_unresolved", attempt, call)
                return {"state": self.state, "result": result}
            except RetryableError:
                if attempt == self.max_attempts:
                    # Response loss can occur after an effect even on the final attempt.
                    try:
                        result = self.tool.lookup(call)
                    except Exception:
                        self.transition("unknown", "reconciliation_failed", attempt, call)
                        return {"state": self.state, "result": None}
                    self.transition("succeeded" if result else "failed", "attempts_exhausted", attempt, call)
                    return {"state": self.state, "result": result}
                self.transition("retrying", "retryable_error", attempt, call)
                await asyncio.sleep(self.delay)
            except ValueError:
                self.transition("failed", "request_rejected", attempt, call)
                return {"state": self.state, "result": None}
            except Exception:
                self.transition("unknown", "unexpected_adapter_error", attempt, call)
                return {"state": self.state, "result": None}
            else:
                self.transition("succeeded", "tool_completed", attempt, call)
                return {"state": self.state, "result": result}
        raise AssertionError("Unreachable")


def replay(path):
    """Validate/reconstruct a trace; never execute a tool."""
    state, run_id, fingerprint, key = "pending", None, None, None
    count = 0
    for count, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        if count == 1:
            run_id, fingerprint, key = row["run_id"], row["request_fingerprint"], row["idempotency_key"]
        if (row["schema_version"] != 1 or row["sequence"] != count or row["run_id"] != run_id
                or row["request_fingerprint"] != fingerprint or row["idempotency_key"] != key
                or row["from"] != state or row["state"] not in TRANSITIONS.get(state, set())):
            raise ValueError("Invalid trace continuity")
        state = row["state"]
    if count == 0:
        raise ValueError("Empty trace")
    return {"run_id": run_id, "state": state, "events": count, "complete": state in TERMINAL}
