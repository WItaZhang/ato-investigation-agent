"""Strict event and tool-call protocols."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass


def identifier(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value))


@dataclass(frozen=True)
class LoginEvent:
    event_id: str
    account_id: str
    new_device: bool
    mfa_passed: bool
    failed_attempts: int

    def __post_init__(self):
        if not identifier(self.event_id) or not identifier(self.account_id):
            raise ValueError("Invalid synthetic event/account identifier")
        if type(self.new_device) is not bool or type(self.mfa_passed) is not bool:
            raise ValueError("new_device and mfa_passed must be booleans")
        if type(self.failed_attempts) is not int or not 0 <= self.failed_attempts <= 10000:
            raise ValueError("failed_attempts must be an integer from 0 to 10000")


@dataclass(frozen=True)
class ToolCall:
    tool: str
    account_id: str
    event_id: str
    action: str
    idempotency_key: str

    def __post_init__(self):
        if self.tool != "mock.apply_protection" or self.action not in {"require_mfa", "review"}:
            raise ValueError("Tool or action is not allowed")
        if not all(identifier(v) for v in (self.account_id, self.event_id, self.idempotency_key)):
            raise ValueError("Invalid identifier")

    @property
    def fingerprint(self):
        payload = asdict(self)
        payload.pop("idempotency_key")
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def make_call(event, action):
    key = hashlib.sha256(f"v1:{event.account_id}:{event.event_id}:{action}".encode()).hexdigest()
    return ToolCall("mock.apply_protection", event.account_id, event.event_id, action, key)
