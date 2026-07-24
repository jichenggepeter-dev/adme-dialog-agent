# Backend Review Fix Report

Date: 2026-07-12

## Gate result

**Stage A passed. Frontend Assistant implementation may begin.**

## Fixes completed

- Upgraded the Agent SQLite schema from v1 to v2 with an in-place migration.
- Added confirmation row versions, terminal result resource IDs, and stable
  terminal error codes.
- Added an atomic approve-and-claim transaction. It validates session activity,
  expiry, state version, payload hash, structure identity, row status, and row
  version; the conditional update must affect exactly one row.
- Added session-scoped confirmation recovery at
  `GET /agent/confirmations/{confirmation_id}?session_id=...`.
- Scoped confirmation, pending-action, and resource reads by session in SQL.
  Resource access also requires an active, unexpired owning session.
- Added deterministic scientific-output validation against structured tool
  facts for mock/real provenance, experimental claims, probability language,
  units, class semantics, and ranking/safety language.
- Added canonical tool-call fingerprints, repeated-call and alternating-loop
  detection, a hard per-turn limit, and stable `AGENT_TOOL_LOOP` and
  `AGENT_TOOL_LIMIT` errors.
- Added endpoint comparison compatibility for missing values, output type,
  verified unit, prediction mode, model version, and metadata verification.
  Ranking, winner selection, and composite scoring remain disabled.
- Added deterministic batch endpoint count/min/max/mean statistics, failed-row
  counts, and duplicate-row counts without exposing full rows to the model.
- Froze uppercase allowlisted UI action types with action identity, target route,
  and expected state version. Added documented structured payload variants.
- Added an Agent error envelope with retryability and correlation ID. Provider
  bodies, credentials, prompts, tracebacks, and raw payloads are not returned.
- Strengthened local audit summaries with hashed session correlation and bounded
  recursive redaction.
- Proved Agent-disabled mode does not initialize the Agent database and does not
  break the existing prediction or health routes.

## Added regression coverage

- Concurrent confirmation claim and replay rejection.
- Confirmation terminal outcome recovery.
- Cross-session and expired-session resource isolation.
- Cross-session message isolation.
- Unsupported probability, unit, provenance, measurement, and ranking claims.
- Identical tool-call loop detection.
- Mock/real and verified-unit comparison incompatibility.
- Disabled-mode DB non-creation and stable Agent error fields.

## Verification evidence

```text
.venv/bin/pytest -q
85 passed, 2 skipped in 9.04s
```

The two default skips are opt-in live LLM integration tests. They were then run
against the local Codex-backed OpenAI-compatible API:

```text
RUN_AGENT_LLM_INTEGRATION=true \
AGENT_LLM_BASE_URL=http://127.0.0.1:18080/v1 \
AGENT_LLM_API_KEY=local-dev-key \
AGENT_LLM_MODEL=gpt-5.4 \
.venv/bin/pytest -q \
  tests/integration/test_agent_llm_compatibility.py \
  tests/integration/test_agent_backend_runtime_integration.py

2 passed in 20.00s
```

`GET /v1/models` confirmed `gpt-5.4` is currently available. The live flow
successfully stopped after compound resolution for mandatory structure
confirmation and predicted only after approval.

## Remaining accepted limitations

- Session IDs are bearer-like local identifiers; user authentication and
  authorization are outside this loopback MVP.
- SQLite supports the local single-process MVP. A production deployment should
  use a transactional server database while preserving conditional claims.
- Recovery reports durable status and a result resource ID. Automatic worker
  resumption of an interrupted `executing` confirmation is not implemented;
  operators can detect and reconcile it without duplicate execution.
- The local OpenAI-compatible proxy is a development dependency and must be
  started separately before live Agent use.

## Rollback

A local pre-Stage-A backup was retained outside the repository and is not
distributed with the project.
