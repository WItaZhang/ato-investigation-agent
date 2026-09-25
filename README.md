# AccountGuard Agent

**Agent demo 的 harness 工程复现 / An agent harness engineering demo.**

本项目关注 agent demo 的执行框架复现与工程完善：把执行契约、状态、失败处理、
幂等和追踪做成可运行、可验证的实现。数据接入和知识库用合成数据、测试夹具和
可替换接口表达；复现范围不包含私有系统接入或真实知识库内容。

**当前实现范围：单工具执行 harness。** 仓库中的登录事件、MFA 和 review 是临时
合成测试场景，用来验证执行器；它们不定义目标业务流程，也不代表已完成目标项目
的复现。完整工作流编排尚未实现。边界见 [复现范围](docs/reproduction-scope.md)。

The current executable is a single-tool harness using synthetic login fixtures.
It runs offline with no API key. Its demonstrated behavior is execution reliability;
the fixture policy is neither a production account-protection design nor a trained detector.

```sh
uv sync --locked
uv run --locked python -m accountguard demo
uv run --locked python -m pytest -q
```

The fixture demo writes traces and a SQLite mock-action ledger under `runs/`.
Within these test fixtures, a new device without MFA triggers `require_mfa`;
repeated failures trigger `review`; a routine event produces `no_action`.
See the [current execution contract](docs/execution-contract.md).

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

Next step: map the target technical workflow to execution stages, state and tool
contracts, then represent its private dependencies with synthetic fixtures.
Workflow fidelity and any additional harness improvements will be documented
separately so that a design extension is not presented as part of the original system.

MIT licensed. No personal work history or user account data is included.
