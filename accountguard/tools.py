"""A mock side effect and deduplication record committed in one SQLite transaction."""

import asyncio
import json
import sqlite3
from contextlib import closing


class RetryableError(Exception):
    """Adapter knows this attempt did not apply an effect, or can deduplicate it."""


class KeyConflict(ValueError):
    pass


class MockProtectionTool:
    def __init__(self, database, fault="none"):
        if fault not in {"none", "transient", "exhausted", "timeout", "lost_ack", "timeout_after_effect"}:
            raise ValueError("Unknown fault injection scenario")
        self.database = database
        self.fault = fault
        self.calls = 0
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS actions (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL)")

    def lookup(self, call):
        with closing(sqlite3.connect(self.database)) as conn:
            row = conn.execute("SELECT fingerprint, result FROM actions WHERE key=?", (call.idempotency_key,)).fetchone()
        if row:
            if row[0] != call.fingerprint:
                raise KeyConflict("Idempotency key already belongs to a different request")
            return json.loads(row[1])
        return None

    async def execute(self, call):
        self.calls += 1
        existing = self.lookup(call)
        if existing is not None:
            return existing
        if self.fault in {"transient", "exhausted"} and (self.calls == 1 or self.fault == "exhausted"):
            raise RetryableError("Injected pre-effect failure")
        if self.fault == "timeout":
            await asyncio.Event().wait()  # No effect; cancellation is cooperative in this mock.
        result = {"mock": True, "action": call.action, "applied": True}
        with closing(sqlite3.connect(self.database)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT fingerprint, result FROM actions WHERE key=?", (call.idempotency_key,)).fetchone()
            if row:
                if row[0] != call.fingerprint:
                    raise KeyConflict("Idempotency key conflict")
                return json.loads(row[1])
            # The row IS the mock action. There is no external account mutation.
            conn.execute("INSERT INTO actions VALUES (?, ?, ?)",
                         (call.idempotency_key, call.fingerprint, json.dumps(result)))
        if self.fault == "lost_ack" and self.calls == 1:
            raise RetryableError("Injected response loss after commit")
        if self.fault == "timeout_after_effect":
            await asyncio.Event().wait()
        return result
