# ADME Conversational Agent Backend Core Review Handoff

Review date: 2026-07-12  
Project: repository root  
Status: Backend core implemented; frontend work has not started

## Review Request

Please review the implemented backend Agent core for correctness, scientific safety, state integrity, security boundaries, maintainability, and compliance with the supplied Agent specifications.

Prioritize concrete bugs, behavioral regressions, race conditions, confirmation bypasses, cross-session access, tool overreach, hallucination risks, missing tests, and contract mismatches. Do not propose frontend implementation yet.

## Fixed Runtime Configuration

```text
Python: 3.11.14
openai: 2.45.0
openai-agents: 0.18.2
LLM Base URL: http://127.0.0.1:18080/v1
Explicit model: gpt-5.4
Wire API: Responses
Feature flag default: AGENT_ENABLED=false
```

`AGENT_LLM_MODEL` is required explicitly. There is no model-name fallback in Python code.

## Implemented Scope

- Neutral deterministic prediction, input-quality, and comparison services
- Strict Pydantic contracts and stable errors
- SQLite session, message, business-state, confirmation, action, resource, and audit storage
- Structure-confirmation state machine
- Eleven strict scientific function tools
- Layered guardrails and scientific instructions
- One OpenAI Agents SDK Agent, non-streaming
- Six `/agent/*` APIs
- Local structured audit logging with redaction
- Unit, API, repository, service, safety, and real-provider integration tests

Not implemented:

- Frontend Assistant or UI Actions dispatcher
- Streaming/SSE route
- Multi-Agent, handoffs, agents-as-tools
- MCP or hosted tools
- Shell, file, web, code-execution, Registry-mutation, batch-run/cancel, or external-export tools
- Authentication/accounts or deployment

## Mandatory Product Behavior

```text
Prediction request
-> resolve name/CID/SMILES
-> canonical structure and input-quality assessment
-> create mandatory structure confirmation
-> stop without prediction
-> explicit confirmation
-> validate session ownership, expiry, state version, payload hash, and canonical SMILES
-> run deterministic prediction service
-> store bounded prediction resources
```

Valid RDKit-parsable SMILES still require confirmation. Rejected, expired, replayed, superseded, stale, or cross-session confirmations must never predict.

## Primary Review Files

### Existing API compatibility

- `app/agent.py`
- `app/main.py`
- `app/schemas.py`

### Neutral services

- `app/services/prediction.py`
- `app/services/input_quality.py`
- `app/services/comparison.py`

### Contracts and state

- `app/agent_runtime/contracts.py`
- `app/agent_runtime/errors.py`
- `app/agent_runtime/repositories.py`
- `app/agent_runtime/state.py`
- `app/agent_runtime/resources.py`
- `app/agent_runtime/confirmations.py`

### Agent execution

- `app/agent_runtime/provider.py`
- `app/agent_runtime/instructions.py`
- `app/agent_runtime/guardrails.py`
- `app/agent_runtime/tool_service.py`
- `app/agent_runtime/tools.py`
- `app/agent_runtime/runtime.py`
- `app/agent_runtime/routes.py`
- `app/agent_runtime/audit.py`

### Configuration

- `app/settings.py`
- `.env.example`
- `requirements.txt`
- `pyproject.toml`
- `Makefile`

## API Surface

```http
POST /agent/sessions
GET  /agent/sessions/{session_id}
GET  /agent/sessions/{session_id}/messages
POST /agent/chat
POST /agent/confirm
GET  /agent/resources/{resource_id}?session_id=...
```

No `/agent/chat/stream` route exists.

Agent responses contain:

- `text`
- `structured_payloads`
- `pending_confirmation`
- `tool_activity`
- `ui_action_proposals`
- `warnings`
- `state_version`

## SQLite Schema

Schema version: `1`

```text
agent_schema
agent_sessions
agent_messages
agent_business_state
agent_confirmations
agent_pending_actions
agent_resources
agent_audit_events
```

Important properties:

- Conversation history and business state are separate.
- Mutations use `BEGIN IMMEDIATE` transactions.
- Business state uses optimistic `expected_state_version` checks.
- Confirmation/action/resource payloads are SHA-256 bound.
- Confirmations and pending actions are single-use and expiring.
- Resources are session-owned, JSON-only, TTL-bound, and limited to 256 KB.
- Existing Batch JSON storage was not migrated.

## Registered Tool Allowlist

```text
resolve_compound
get_compound_context
get_input_quality_assessment
predict_single_compound
get_prediction_results
explain_endpoint
get_model_information
get_batch_job_status
get_batch_errors
summarize_batch_results
compare_compounds
```

Please verify that each wrapper remains thin and calls existing deterministic services instead of duplicating predictor, compound, Registry, formatter, or batch logic.

## Scientific Safety Rules

- ADME values must come from deterministic tools, never LLM calculation.
- Predictions must not be described as measurements.
- No clinical, dosing, patient, regulatory, or definitive safety conclusions.
- No invented units, thresholds, positive classes, directionality, provenance, or model versions.
- Endpoint explanations must use only Endpoint Registry metadata.
- Unknown/unverified metadata must remain neutral.
- Mock mode must be clearly labeled as deterministic test data.
- Comparison accepts 2-5 predictions and never ranks or selects a winner.
- Prompt injection cannot grant additional tools or bypass confirmation.

## Audit and Privacy

OpenAI-hosted SDK tracing and sensitive trace inclusion are disabled. Application-owned SQLite audit events remain enabled.

Audit summaries may contain correlation ID, model, tool name, duration, stable status/error code, counts, hashes, and resource IDs.

They must not contain:

- API keys or Authorization headers
- Full prompts
- Raw provider responses
- Full tool payloads
- Complete batch data
- Arbitrary local file contents

SMILES, query, and message fields are hashed when included in audit summaries.

## Test Evidence

```text
Agent-focused tests:           31 passed
Full backend suite:            75 passed, 2 skipped
Opt-in real provider/API tests: 2 passed
Frontend lint:                 passed
Frontend typecheck:            passed
Frontend tests:                17 passed
```

Real provider integration exercised:

```text
POST /agent/sessions
-> POST /agent/chat using local gpt-5.4
-> resolve_compound only
-> confirmation returned, no prediction
-> POST /agent/confirm
-> predict_single_compound
-> mock prediction response
```

Commands:

```bash
AGENT_ENABLED=false ADME_MOCK_MODE=true .venv/bin/pytest -q

RUN_AGENT_LLM_INTEGRATION=true \
AGENT_ENABLED=true \
ADME_MOCK_MODE=true \
.venv/bin/pytest -q tests/integration -s

cd frontend
npm run lint
npm run typecheck
npm run test
```

## Existing Documentation

- `docs/agent/agent-implementation-plan.md`
- `docs/agent/local-llm-compatibility.md`
- `docs/agent/backend-core-architecture.md`
- `docs/agent/backend-api.md`
- `docs/agent/session-and-confirmation.md`
- `docs/agent/tool-reference.md`
- `docs/agent/safety-and-audit.md`
- `docs/agent/backend-core-test-report.md`

## Known Limitations and Risks

1. Real ADMET-AI model loading/prediction was not rerun in this phase; Agent integration used deterministic mock prediction mode.
2. The local Codex proxy is a separate process. Agent calls fail when port `18080` is unavailable, while existing ADME routes remain usable.
3. A bare `session_id` is not authentication. This is acceptable only for the current `127.0.0.1`, single-user MVP.
4. The output guardrail is intentionally narrow and supplements, rather than replaces, typed tools and deterministic scientific policies. Review whether additional structured output validation is required before frontend work.
5. SQLite is appropriate for the local MVP but has not been load-tested for many simultaneous sessions.
6. Production frontend build, Playwright E2E, and real ADMET-AI smoke were not run.

## Requested Review Questions

1. Can any path invoke prediction without a valid, current, session-owned structure confirmation?
2. Are confirmation transitions atomic and resistant to replay, stale versions, payload changes, and cross-session access?
3. Can resources or messages be accessed across sessions?
4. Does any tool duplicate or bypass existing deterministic scientific services?
5. Can model output invent scientific facts despite the Registry and tool contracts?
6. Are mock and real prediction modes impossible to confuse in API responses?
7. Are the tool-call and turn limits enforceable under malformed or adversarial model behavior?
8. Can prompt injection gain shell, file, web, MCP, Registry mutation, batch mutation, or export capabilities?
9. Are audit records sufficiently useful while remaining properly redacted?
10. Are error envelopes stable, non-sensitive, and compatible with a future frontend?
11. Does `AGENT_ENABLED=false` fully isolate the Agent provider and storage from existing application startup?
12. Which issues must be fixed before beginning the frontend Assistant phase?

## Review Output Format

Please return findings first, ordered by severity, with exact file and line references. Separate:

1. Blocking issues before frontend work
2. Important correctness/security/scientific issues
3. Missing tests or documentation
4. Open questions and assumptions
5. Brief overall recommendation: approve, approve with fixes, or do not proceed

Do not begin implementation or rewrite the frontend during this review.
