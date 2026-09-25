# Execution contract v0

This is the contract of the current **single-tool fixture demo**, not a specification
of the target business workflow. `LoginEvent` and the two mock actions exercise
runtime behavior and are replaceable. See [reproduction scope](reproduction-scope.md).

`LoginEvent`: event_id, account_id (synthetic identifiers), new_device, mfa_passed,
failed_attempts. Unknown or malformed fields are rejected by dataclass construction.

`ToolCall`: tool=`mock.apply_protection`, account_id, event_id,
action=`require_mfa|review`, idempotency_key. No arbitrary tool invocation is supported.
The idempotency key binds account, event, action and version; the stored fingerprint
also binds the entire request payload. Key reuse with different parameters fails.

```
pending -> running -> succeeded
                  -> retrying -> running
                  -> failed
                  -> unknown
```

Only `RetryableError` permits another attempt; config bounds count and delay.
Timeouts attempt a read-only ledger lookup. A committed result means succeeded;
no proof means unknown and requires reconciliation, not blind retry. An unexpected
adapter exception is also unknown. Cancellation is cooperative: this mock uses
async waits; a blocking or cancellation-resistant real tool needs process isolation
or a provider-enforced deadline. `failed` covers rejected requests and exhausted
pre-effect failures; it does not mean an ambiguous external action was rolled back.

Trace records contain schema_version, run_id, sequence, UTC timestamp, from/state,
event, attempt, idempotency_key and request fingerprint. They omit account IDs and
raw events. These hashes are correlation identifiers, not an anonymization promise.
Replay checks state continuity, run/key/fingerprint identity and event sequence;
it is not a cryptographic audit or an automatic resume mechanism. An interrupted
trace remains incomplete. Only synthetic data should be used in this version.

The SQLite transaction commits the mock action and its deduplication result
together. Persistence covers process restarts. Trace append and ledger commit are
separate, so a crash can leave an incomplete trace even when an action was committed;
reconciliation must check the ledger. No production account connector exists yet.

Acceptance coverage includes transient error, timeout, timeout after commit,
lost acknowledgement, exhausted attempts, restart deduplication, conflicting keys,
concurrent duplicate calls, malformed protocol and invalid trace replay.
