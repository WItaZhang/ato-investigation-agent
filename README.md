# ATO Investigation Agent

This project is being rebuilt to reproduce an account takeover investigation
workflow: anomalous login cohorts, account evidence cards, attack reconstruction,
retrospective victim discovery, and policy diagnosis. See the
[reproduction plan](docs/reproduction-plan.md) for scope and unresolved details.

## Investigation prototype

```sh
uv sync --locked
uv run --locked python main.py --config configs/investigation.yaml --prepare-only
# Configure OPENAI_API_KEY locally before the next command.
uv run --locked python main.py --config configs/investigation.yaml
```

The first command generates synthetic data and cards without adjudicating them.
The second uses real structured LLM responses for account judgments and evidence
synthesis. Configuration selects GPT-5.4 mini, with a US$1 per-run reservation
budget. API credentials are the sole documented environment-variable exception;
all experimental settings live in YAML. No `.env` file is loaded automatically.
Price assumptions are from the [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
checked on 2026-09-25; update them before running if provider rates change.
The budget is an application estimate, not a provider-side billing guarantee.

Each run saves its config, metrics, model-call audits and log under `logs/`.
Generated inputs and isolated labels go to `data/staging/`; evidence and results
go to `data/processed/`. No model receives the labels. Failed runs retain a failed
status; missing credentials do not silently fall back to mock judgments.

Implemented: baseline scan, cohort merging, evidence cards, real LLM adapter,
evidence-ID checks, full-cohort prevalence bounds, basic observed-rule diagnosis,
and bounded evidence synthesis. **Not yet implemented:** condition refinement,
batch-registration filtering, stratified sequential sampling, full timeline
reconstruction, validated retrospective expansion, or versioned knowledge sync.
Full-cohort bounds describe unknown labels, not statistical confidence in LLM
accuracy. Synthetic fixtures and mock tests do not establish real-world quality.

## Legacy execution harness

The code below is the **legacy AccountGuard prototype**, retained as a tested
execution component. It is not the completed investigation pipeline.

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
