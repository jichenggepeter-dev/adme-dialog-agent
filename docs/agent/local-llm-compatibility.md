# Local LLM Compatibility Report

Status: Phase 1 accepted  
Validation date: 2026-07-12 (America/New_York)

## Configuration

The local API is provided by `hotchpotch/openai-api-server-via-codex`, backed by the locally authenticated official Codex CLI.

```text
Base URL: http://127.0.0.1:18080/v1
Selected model: gpt-5.4
Wire API: Responses
```

The API key is intentionally omitted. Application code reads the base URL, API key, and model from required environment variables. `AGENT_LLM_MODEL` has no code fallback.

## Pinned SDK Versions

| Package | Version |
| --- | --- |
| `openai` | `2.45.0` |
| `openai-agents` | `0.18.2` |

`openai-agents==0.18.2` declares `openai>=2.45.0,<3`, so the pins are mutually compatible.

## Python Compatibility

| Python | Result |
| --- | --- |
| 3.13.5 | SDK imports and full SDK smoke passed before the environment was rebuilt |
| 3.11.14 | SDK imports, project dependency installation, full SDK smoke, and backend suite passed |

The active project `.venv` is now Python 3.11.14, matching the project's minimum supported runtime.

## Server Startup and Discovery

Codex authentication was verified with `codex login status`. The proxy was started with:

```bash
uvx --refresh-package openai-api-server-via-codex openai-api-server-via-codex
```

Observed checks:

- `GET /healthz`: HTTP 200, `{"status":"ok"}`.
- `GET /v1/models`: advertised `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`, and `gpt-5.4-mini`.
- `gpt-5.3-codex-spark` was not advertised and is not configured.
- A direct strict function call with `gpt-5.4` passed before the SDK test.

## SDK-Level Results

The project smoke test uses `AsyncOpenAI`, `OpenAIResponsesModel`, `Agent`, `Runner`, and strict local function tools from the pinned SDK.

| Scenario | Result | Evidence |
| --- | --- | --- |
| SDK import | Pass | Both pinned packages import in Python 3.11 and 3.13 |
| Responses adapter | Pass | All model calls used `POST /v1/responses` with `gpt-5.4` |
| Ordinary response | Pass | Exact output `ADME_AGENT_TEXT_OK`; no tool was available or called |
| Strict tool call | Pass | `lookup_compound_label` called exactly once |
| JSON arguments | Pass | Parsed arguments were `{"query":"aspirin"}` |
| Tool continuation | Pass | Final answer contained tool-returned label `Aspirin` and status `found` |
| Tool error continuation | Pass | Stable `COMPOUND_NOT_FOUND` envelope produced a final answer without crash, retry, or invented compound |
| Multi-turn | Pass | Next turn recalled `Aspirin`; cumulative tool-call count remained one |
| Timeout mapping | Pass | Controlled delay mapped to `AGENT_TIMEOUT` without traceback/provider payload |
| Hosted SDK tracing | Pass | Disabled before client/model execution |
| Local audit logging | Pass | Logged correlation ID, model, tool name, duration, status, and stable error code fields |
| Explicit integration test | Pass | `1 passed` with the opt-in environment flag |

The smoke output reported overall `"ok": true` in both Python 3.13.5 and Python 3.11.14.

## Security and Logging

- OpenAI-hosted Agents SDK tracing is disabled by default.
- Application-owned structured audit logging remains enabled.
- Logs do not include API keys, Authorization headers, full prompts, raw provider responses, full tool payloads, or batch data.
- The proxy binds to `127.0.0.1`; widening the bind address requires explicit authentication and a separate security review.
- The proxy consumes the authenticated ChatGPT/Codex account quota and must remain a separate long-running process.

## Exact Commands

```bash
# SDK smoke through the project environment
make smoke-agent-llm

# Explicit real integration test
RUN_AGENT_LLM_INTEGRATION=true \
  .venv/bin/pytest -q tests/integration/test_agent_llm_compatibility.py -s

# Normal backend suite; real local LLM test skips by default
ADME_MOCK_MODE=true .venv/bin/pytest -q

# Frontend regression checks
cd frontend
npm run lint
npm run typecheck
npm run test
```

## Regression Results

- Backend: `48 passed, 1 skipped`.
- Frontend lint: passed.
- Frontend typecheck: passed.
- Frontend tests: 7 files, 17 tests passed.
- Production frontend build: not run in Phase 1.
- Playwright E2E: not run in Phase 1.
- Real ADMET-AI prediction smoke: not run as part of Agent Phase 1.

## Known Limitations

- Phase 1 validates SDK compatibility only; there is no product Agent route, scientific tool wrapper, session store, confirmation flow, or frontend assistant.
- Chat Completions is not selected. Earlier Oyster testing found that this proxy rejected a Chat request containing `temperature`; Responses is the accepted adapter.
- Timeout validation uses the same provider execution boundary with a controlled delay, rather than deliberately forcing a live model request to hang.
- The local proxy lifecycle is external to FastAPI. If its terminal/process stops, future Agent calls will be unavailable while existing ADME features remain unaffected.
- No deployment or multi-user access control was implemented.

## Phase 1 Decision

Phase 1 passes all approved acceptance criteria. The project may proceed to Phase 2 only after human review. Until then, Agent functionality remains disabled and no later-phase implementation should begin.

