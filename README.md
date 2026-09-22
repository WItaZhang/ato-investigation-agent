# AccountGuard Agent

**账号防护 Agent 的最小执行框架 / A minimal account protection agent harness.**

AccountGuard directly communicates the purpose: protect accounts. This first
version uses transparent rules and synthetic login events. It runs offline with
no API key and simulates MFA challenges and review requests. It is an executable
engineering prototype, not a production security product or a trained detector.

```sh
uv sync --locked
uv run --locked python -m accountguard demo
uv run --locked python -m pytest -q
```

The demo writes traces and a SQLite mock-action ledger under `runs/`. A new device
without MFA triggers `require_mfa`; repeated failures trigger `review`. A routine
event produces `no_action`. See [execution contract](docs/execution-contract.md).

| Scenario | Expected first-run outcome |
|---|---|
| New device | succeeded, one mock MFA action |
| Transient pre-effect error | bounded retry, succeeded |
| Lost response after commit | retry reads the persisted result, no duplicate action |
| Timeout without a committed result | unknown, no blind automatic retry |
| Repeated login failures | succeeded, one mock review action |

Replay any printed trace path with `uv run --locked python -m accountguard replay
runs/<run-id>.jsonl`. Replay reconstructs state without running tools. Running the
demo again reuses persistent keys; completed scenarios may return immediately
from the ledger. Use another `output_dir` in a copied TOML for fresh fault demos.

## Scope

- Strict event/tool dataclasses, allowlisted actions, timeout, bounded retry,
  persistent mock idempotency, explicit terminal states and JSONL trace replay.
- Standard library runtime; `uv.lock` includes development dependencies.
- No real account connector, credentials, passwords, session tokens, model API,
  autonomous lockout or account recovery. Rules do not prove attack detection quality.
- The mock commits effect and deduplication record atomically. A real service needs
  its own idempotency support and reconciliation API; the SQLite mock does not
  provide distributed exactly-once delivery for external account actions.

Next step: agree on one provider and read-only login-event schema, add recorded
synthetic fixtures, then evaluate false positives before enabling any real action.
Model routing and memory belong after this contract is stable.

MIT licensed. No personal work history or user account data is included.
