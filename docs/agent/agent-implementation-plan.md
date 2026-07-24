# ADME Conversational Agent Implementation Plan

Status: Phase 0-1 reviewed; backend Agent core complete and awaiting human review before frontend work  
Audit date: 2026-07-12 (America/New_York)

## 1. Scope and Decisions

This plan maps the supplied conversational-agent documents to the current repository. No Agent runtime, route, schema, dependency, or frontend assistant code was added during this phase.

Fixed decisions:

- One conversational session persists across `/single`, `/batch`, and `/about`.
- Name, PubChem CID, and SMILES resolution must stop at structure confirmation before prediction.
- V1 requires structure confirmation even when RDKit deterministically parses a valid SMILES. This is a scientific UX, auditability, and safety policy, not a workaround for RDKit uncertainty. Confirmation shows the canonicalized structure, exposes fragment/charge/salt/input-quality warnings, reveals the actual model input, keeps Human-in-the-loop behavior consistent, and creates a traceable confirmation record.
- The LLM may request only typed, allowlisted scientific tools and UI actions.
- Reversible display actions may execute immediately; side-effect actions require approval.
- ADMET values come only from existing deterministic services, never from the LLM.
- The runtime is the OpenAI Agents SDK with one agent. Hermes is design reference only.
- No shell, arbitrary file access, clinical advice, automatic best-molecule ranking, invented units/thresholds/probabilities, or automatic Endpoint Registry mutation.

## 2. Current Architecture

### Runtime and dependencies

- Project metadata requires Python `>=3.11`; the active `.venv` is Python `3.11.14`.
- Active Node is `25.8.1`, npm is `11.11.0`.
- Backend uses FastAPI `0.139.0`, Pydantic `2.13.4`, and RDKit `2026.3.3` in the active environment.
- `openai==2.45.0`, `openai-agents==0.18.2`, and `admet-ai` are installed in the active `.venv`. SDK-level Responses compatibility with the explicitly configured `gpt-5.4` model is confirmed. Real ADMET-AI model execution has not been rerun in this backend-core phase and remains unverified here.
- Frontend is Next.js `16.2.10`, React `19.2.4`, TypeScript, Vitest, Testing Library, and Playwright.
- The repository directory has no `.git`; rollback cannot rely on a local commit unless version control is initialized above or added later.

### Backend

- FastAPI entry: `app/main.py`, app object `app`.
- `app/agent.py` is an existing rule-based SMILES chat handler. It is not an OpenAI Agents SDK implementation and should be renamed only in a later reviewed migration, not overwritten silently.
- Compound resolution: `app/tools/compound.py` resolves SMILES locally and name/CID through PubChem, then uses RDKit for canonicalization, descriptors, and SVG depiction.
- SMILES validation/extraction: `app/tools/smiles.py`.
- Predictor: `app/tools/admet_predictor.py`; lazy real-model loading, JSON conversion, deterministic mock mode, status reporting, and custom prediction errors are already isolated.
- Endpoint Registry: `app/tools/endpoints.py`; loads bundled ADMET-AI metadata when available, enriches raw values, reports coverage and compatibility, and falls back to unknown metadata without inventing interpretation.
- Batch service: `app/tools/batch.py`; local JSON persistence under `data/uploads` and `data/jobs`, mapping/validation, background thread execution, cancellation, result retrieval, and exports.
- Formatting/scientific summary: `app/formatter.py`; should remain the deterministic interpretation layer used by Agent tools.

### Current API surface

| Method | Path | Current responsibility |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/status` | Backend and predictor status |
| POST | `/compound/resolve` | Name, CID, or SMILES resolution |
| GET | `/endpoints` | Registry document |
| GET | `/endpoints/coverage` | Registry coverage |
| GET | `/endpoints/{raw_key}` | Endpoint detail |
| GET | `/batch/capabilities` | Upload/predictor limits |
| POST | `/batch/upload` | File upload and preview |
| POST | `/batch/jobs` | Create and validate job |
| GET | `/batch/jobs/{job_id}` | Job state |
| GET | `/batch/jobs/{job_id}/results` | Current job payload |
| POST | `/batch/jobs/{job_id}/run` | Start prediction thread |
| POST | `/batch/jobs/{job_id}/cancel` | Cancel job |
| GET | `/batch/jobs/{job_id}/export` | Export results/metadata/JSON |
| POST | `/batch/jobs/{job_id}/export/filtered` | Export selected rows |
| GET | `/batch/jobs/{job_id}/errors` | Export errors |
| POST | `/predict` | Validate and predict one SMILES |
| POST | `/predict/batch` | Legacy list-based batch prediction |
| POST | `/chat` | Existing stateless rule-based SMILES extraction and prediction |

### Frontend

- Root layout: `frontend/app/layout.tsx`, with global `AppHeader` and no provider layer.
- `/single`: server page wrapping client `SingleMoleculeWorkspace`.
- `/batch`: server page wrapping client `BatchWorkspace`; `/batch/[jobId]` hosts the job workspace.
- `/about`: server page wrapping client `ModelInformationWorkspace`.
- Shared components already cover backend status, structure confirmation, predictions, endpoint details, batch upload/mapping/results, exports, errors, loading, and scientific disclaimers.
- State is component-local React `useState`/`useEffect`; there is no Context, Redux, Zustand, Jotai, or persistent cross-route application store.
- `frontend/lib/api.ts` is the centralized fetch client with typed errors and timeouts. `frontend/lib/types.ts` is the shared frontend contract module.

### Tests and commands

- Backend tests: 7 files covering SMILES, formatter, rule-based chat, API, compound resolution, endpoint registry, and batch.
- Frontend unit/component tests: 7 files. E2E specs cover prediction, batch/about, and visual capture.
- `Makefile` provides setup, mock/real smoke, backend/frontend/dev, batch demo, and full checks.
- `scripts/dev.sh` starts backend and frontend together and stops both if either exits.
- Root `.env.example` currently contains only `ADME_MOCK_MODE=true`; frontend has its own API-base example.
- Verified on this audit: backend `44 passed`; frontend lint and typecheck passed; frontend `17 passed`. E2E and production build were not rerun in this phase.

## 3. Product Documents to Code Mapping

| Document goal | Existing foundation | Planned addition |
| --- | --- | --- |
| Cross-page conversation | Root layout and centralized API client | Root `AgentProvider`, session ID persistence, assistant shell |
| Structure confirmation | `/compound/resolve`, `CompoundResponse`, confirmation card | Pending confirmation state and confirm/reject endpoint |
| Scientific tool execution | Deterministic services under `app/tools` | Thin typed Agent function tools only |
| Endpoint explanations | Endpoint Registry and endpoint details UI | Registry-backed explanation tool/card |
| Batch assistance | Batch job service and job workspace | Read-only status/summary/error tools; approved run/cancel actions |
| Page-aware UI actions | Existing workspace component states | Typed page context and allowlisted dispatcher |
| Safety | Existing disclaimer and metadata flags | Input/output/tool guardrails, approval policy, audit events |
| Evaluation | pytest, Vitest, Playwright | Fake-model orchestration tests, safety corpus, action contract tests |

## 4. Agent Tool Reuse Map

All tools must return compact typed results or resource IDs. They must not duplicate service logic.

| Agent tool | Existing service to reuse | Policy |
| --- | --- | --- |
| `resolve_compound` | `app.tools.compound.resolve_compound` | Always returns `confirmation_required`; no prediction in same unconfirmed step |
| `get_compound_context` | New read adapter over confirmed session business state | Read-only; never infer or guess a molecule |
| `predict_single_compound` | Phase 2 neutral service, planned at `app/services/prediction.py`, extracted from the old rule-based handler without duplicating validator/predictor/formatter logic | Requires confirmed canonical SMILES; production Agent code must not depend on `app.agent.predict_adme` |
| `get_prediction_results` | Session resource store; existing prediction payload | Read-only by resource ID |
| `explain_endpoint` | `app.tools.endpoints.get_endpoint` | Use metadata flags; no invented unit or probability language |
| `compare_compounds` | Existing enriched prediction payloads plus deterministic comparison formatter | Read-only; no automatic winner/ranking |
| `get_batch_job_status` | `app.tools.batch.get_job` | Compact job summary, not all rows |
| `summarize_batch_results` | `get_job` plus deterministic aggregation helper | Resource ID and explicit filters; no LLM arithmetic |
| `get_batch_errors` | `get_job` rows or existing error export source | Paginated/compact structured errors |
| `get_model_information` | `predictor_status`, `registry_document`, `registry_coverage` | Read-only and provenance-aware |
| `get_input_quality_assessment` | Phase 2 deterministic RDKit helper, planned at `app/services/input_quality.py`; it may reuse validation primitives but must own its explicit quality schema | Rule-based input-quality checks only, not a statistical applicability-domain score |

In Phase 2, first extract the neutral prediction service. Both the existing `/chat` handler and the future Agent Tool will call it. The existing `/chat` route remains available; this extraction is not part of Phase 1.

The input-quality helper must explicitly calculate and report supported RDKit facts such as fragment count, heavy atom count, molecular weight, formal charge, metal presence, unusual elements, mixture warnings, and size warnings. Existing `validate_smiles()` does not provide this contract. A model returning a numeric prediction does not establish that the prediction is reliable or inside an applicability domain.

`run_batch_job`, `cancel_batch_job`, exports, and navigation are not initial scientific tools. If later exposed, they are explicit UI/business actions with approval rules.

## 5. Missing Backend APIs

Recommended versioned surface:

- `POST /agent/sessions`: create or resume an anonymous local session.
- `GET /agent/sessions/{session_id}`: session metadata and resumable status, excluding raw secrets/provider payloads.
- `GET /agent/sessions/{session_id}/messages`: paginated sanitized history.
- `POST /agent/chat`: non-streaming MVP turn with `session_id`, `message`, and `page_context`.
- `POST /agent/confirm`: approve/reject a pending structure or side-effect action using `confirmation_id` and optimistic version.
- `GET /agent/resources/{resource_id}`: optional bounded retrieval for large prediction/batch resources.
- Later only: `POST /agent/chat/stream` using SSE after provider streaming passes compatibility tests.

Keep current `/chat` intact during migration. Deprecate it only after the new assistant is proven and consumers are migrated.

## 6. Missing Schemas

Backend Pydantic and mirrored TypeScript contracts are needed for:

- `AgentSession`, `AgentMessage`, `AgentChatRequest`, `AgentChatResponse`.
- `PageContext` with route, selected compound/job IDs, visible filters, and state version; no arbitrary DOM or free-form state dump.
- `ToolResultEnvelope` with tool name, status, resource ID, compact payload, error code, and provenance.
- `CompoundConfirmation` with ID, canonical SMILES, depiction, source, status, expiry, and version.
- `PendingAction` with action ID, typed payload, risk class, status, expiry, and version.
- `UIAction` discriminated union and route-specific payloads.
- Stable Agent errors: `AGENT_NOT_CONFIGURED`, `AGENT_PROVIDER_UNAVAILABLE`, `AGENT_PROVIDER_INCOMPATIBLE`, `AGENT_TIMEOUT`, `SESSION_NOT_FOUND`, `CONFIRMATION_REQUIRED`, `CONFIRMATION_EXPIRED`, `ACTION_NOT_ALLOWED`, and `TOOL_FAILED`.

## 7. Session and Business State

Use separate stores even in the local MVP:

- Conversation state: SDK `SQLiteSession` or an application-owned SQLite message table keyed by opaque UUID. Do not depend on provider-hosted conversation state because the local API compatibility is unknown.
- Business state: application-owned SQLite tables for confirmed compound, prediction resource references, selected batch job, pending confirmations/actions, page context version, and audit events.
- Existing batch JSON files remain owned by `app/tools/batch.py`; Agent state stores only job IDs and compact summaries.
- Browser persistence of an opaque session ID is only a correlation mechanism, not complete access control. A bare `session_id` is temporarily acceptable only for the `127.0.0.1`, single-user local MVP. A later shared or remotely accessible version requires at least a separate `session_token` or an HttpOnly cookie. Phase 1 records this risk and does not implement accounts or authentication.
- Add TTL, last-access time, schema version, and a reset action. Never place API keys or full SDK run state in frontend storage.

SQLite is preferable to additional ad hoc JSON files because confirmation transitions and replay protection require atomic updates. A future production store can implement the same repository interfaces.

## 8. Frontend Assistant Mount and Page Context

Mount `AgentProvider` inside `frontend/app/layout.tsx` around `AppHeader` and route content. Render the launcher/panel once at root so it survives client-side navigation. Lazy-load the panel; desktop width follows the product spec and mobile uses a bottom sheet.

Each workspace registers a compact context adapter with the provider:

- `/single`: confirmed compound ID/canonical SMILES, prediction resource ID, current phase, selected endpoint.
- `/batch`: upload/job ID, mapping phase, validation summary, selected rows/endpoints, filters.
- `/about`: selected endpoint key and active filters.

Context registration is typed and route-owned. The assistant must not inspect the DOM, read arbitrary component state, or receive raw batch rows by default.

## 9. UI Action Dispatcher

Implement a single `dispatchAgentUIAction(action)` in the provider. Validate every action against a TypeScript discriminated union and route capability map before dispatch.

Initial allowlist:

- Reversible: `NAVIGATE`, `OPEN_ASSISTANT`, `SELECT_ENDPOINT`, `SET_ABOUT_FILTERS`, `SELECT_BATCH_ROW`, `SET_BATCH_FILTERS`, `FOCUS_COMPOUND_INPUT`, `SHOW_RESOURCE`.
- Confirmation required: `RUN_SINGLE_PREDICTION`, `RUN_BATCH_JOB`, `CANCEL_BATCH_JOB`, `REPLACE_UPLOAD`, `CLEAR_SESSION`, and only the risk-bearing export cases defined below.

Actions include `action_id`, `session_id`, `target_route`, `expected_state_version`, and typed payload. Reject stale, duplicate, unknown, cross-session, and route-incompatible actions. Log the outcome without sensitive payloads.

Export confirmation is contextual, not universal. Consider whether the user explicitly requested the export, the data scope, destination, sensitive notes, overwrite behavior, and third-party transfer. An explicit request to download the current result locally, without server overwrite or external transfer, normally needs no second confirmation. Confirmation is mandatory when the Agent proposes an unrequested export, exports complete batch data or sensitive notes, overwrites a file, or uploads/sends data to an external system.

## 10. Human-in-the-Loop Model

Use explicit states:

`proposed -> awaiting_confirmation -> approved -> executing -> succeeded | failed`

and terminal alternatives:

`rejected | expired | superseded`

Structure confirmation is a distinct mandatory gate, not a generic button acknowledgment. Prediction tools accept only a confirmed compound reference whose canonical SMILES matches the business-state record. Side-effect approval is single-use, versioned, expires, and binds to exact normalized arguments. Resuming an SDK interruption must use serialized run state only after compatibility is verified; otherwise resume through application-owned orchestration state.

## 11. Guardrails

- Input: reject clinical treatment/dosing requests, arbitrary shell/file/network requests, registry mutations, unsupported molecules, and requests to skip structure confirmation.
- Tool input: validate with strict Pydantic schemas; resolve IDs server-side; enforce size, ownership, confirmation, and state-version checks immediately before execution.
- Tool output: convert to JSON-safe bounded envelopes; attach source and metadata status; omit large raw payloads in favor of resource IDs.
- Agent output: prohibit clinical/regulatory conclusions, unverified units/thresholds/probability language, molecule guessing, fabricated values, and automatic best-compound ranking.
- Scientific language: values and interpretations must originate from prediction results, formatter rules, or verified Endpoint Registry fields. Always include the computational-prediction disclaimer where results are discussed.
- Runtime: expose only registered function tools. Do not configure hosted shell, local shell, file, computer, code interpreter, web search, MCP, handoffs, or agents-as-tools.

## 12. Tracing, Logging, and Redaction

- OpenAI-hosted Agents SDK tracing is disabled by default (`OPENAI_AGENTS_DISABLE_TRACING=1` and runtime configuration). Application-owned local audit tracing remains enabled.
- Local structured audit logs use correlation ID, model, tool name, duration, stable status/error code, and later may add session hash, turn ID, and resource ID.
- Never log API keys, Authorization headers, full prompts, raw provider responses, full tool arguments/results, depiction SVG, uploaded file contents, or all batch rows.
- Hash or truncate SMILES and compound queries in operational logs; retain full scientific inputs only in the explicit local business store where required.
- Add a redaction unit test corpus and verify exception handlers do not leak provider payloads.

## 13. Test Strategy

- Compatibility: direct HTTP and SDK smoke tests against `18080`, opt-in integration marker.
- Unit: tool schemas, tool-to-service adapters, state transitions, confirmation replay/expiry, guardrails, redaction, and UI action validation.
- Orchestration: fake model/provider emits deterministic tool calls; no real LLM required in normal tests.
- Contract: Pydantic-to-TypeScript fixtures and stable error envelopes.
- API: session/chat/confirm/history happy paths, timeouts, unavailable provider, malformed tool calls, stale actions, and cross-session access.
- Scientific regression: assert no Agent path changes predictor, formatter, registry, compound, or batch outputs.
- Frontend: provider persistence, confirmation cards, pending/error states, dispatcher allowlist, route context registration, keyboard/focus behavior.
- E2E: cross-page session, name/CID/SMILES structure confirmation, single prediction, endpoint explanation, batch status, rejected side effect, provider outage, and mobile panel.
- Safety evaluation: clinical requests, prompt injection, shell/file requests, fabricated-unit prompts, skip-confirmation prompts, winner-ranking prompts, oversized batch requests, and poisoned tool output.

## 14. Risks and Blockers

1. The local Codex API proxy is a separate long-running process; Agent availability depends on it remaining active. See `local-llm-compatibility.md`.
2. Direct and SDK-level Responses, tool calling, continuation, multi-turn, streaming, and timeout probes pass with explicit `AGENT_LLM_MODEL=gpt-5.4`; there is no model-name fallback in code.
3. OpenAI Agents SDK is installed and pinned in the project environment.
4. Python 3.11.14 is the active runtime; SDK smoke also passed on Python 3.13.5. Real ADMET-AI execution remains a separate integration boundary.
5. ADMET-AI is installed, but its real model load/prediction smoke has not been rerun for this phase and must not be claimed as verified.
6. Existing `app/agent.py` naming collides conceptually with the planned `app/agent/` package.
7. Existing business persistence is JSON/thread based and has no ownership/auth boundary or transactional confirmation model.
8. CORS permits only port 3000; local Next.js fallback ports such as 3001 will fail browser API calls unless configuration is generalized safely.
9. Current `/chat` predicts immediately after extracting a SMILES and therefore does not satisfy mandatory structure confirmation.
10. No local Git repository exists for atomic rollback.

## 15. Phased File Modification Plan

### Phase 1: provider compatibility and configuration

Files: `requirements.txt`, `pyproject.toml`, `.env.example`, `app/settings.py`, `scripts/smoke_test_agent_llm.py`, `tests/integration/test_agent_llm.py`, compatibility docs.

Acceptance: pinned SDK imports on Python 3.11 and active runtime; environment validation; `OpenAIResponsesModel` completes a strict function-tool round trip against the verified local proxy; no product route or UI yet.

`AGENT_LLM_MODEL` is mandatory whenever Agent configuration is loaded. Code must not use a hidden fallback such as `os.getenv("AGENT_LLM_MODEL", "gpt-5.4")`; use explicit environment validation or Pydantic Settings with an explainable configuration error. The `.env.example` value is an example only and must be confirmed against `GET /v1/models`.

### Phase 2: neutral service boundary and contracts

Files: `app/services/prediction.py`, `app/agent_runtime/contracts.py`, `app/schemas.py`, focused service tests. Avoid the `app/agent` package name until the existing module migration is explicit.

Acceptance: current `/predict`, `/chat`, and batch tests remain unchanged; new typed contracts serialize; no duplicated predictor/compound/registry logic.

### Phase 3: state repositories and confirmation engine

Files: `app/agent_runtime/state.py`, `app/agent_runtime/repositories.py`, `app/agent_runtime/confirmations.py`, SQLite migration/init module, tests.

Acceptance: atomic session/business state, TTL, replay protection, optimistic version checks, and concurrent confirmation tests pass.

### Phase 4: read-only Agent tools and guardrails

Files: `app/agent_runtime/tools.py`, `guardrails.py`, `resources.py`, tests.

Acceptance: each tool calls the mapped service once, produces bounded JSON-safe output, and cannot access shell/files or bypass confirmation.

### Phase 5: single-agent runtime and non-streaming API

Files: `app/agent_runtime/runtime.py`, `provider.py`, `routes.py`, `app/main.py`, `app/schemas.py`, API/orchestration tests.

Acceptance: session/chat/confirm/history work with fake provider; one-agent limit; provider outage returns stable errors; current routes remain compatible.

### Phase 6: root assistant and read-only UI actions

Files: `frontend/app/layout.tsx`, `frontend/components/assistant/*`, `frontend/lib/agent-api.ts`, `agent-types.ts`, provider/dispatcher tests, minimal route adapter changes.

Acceptance: session persists across routes; accessible panel; typed page context; only reversible allowlisted actions execute.

### Phase 7: approved side effects and evaluation

Files: confirmation/action UI, route adapters, backend action policy, safety evaluation fixtures, Playwright specs, documentation.

Acceptance: every side effect pauses, shows exact action, is single-use, and is auditable; all safety/e2e cases pass; no scientific-output regression.

### Phase 8: optional streaming

Files only after provider acceptance: SSE route, streaming client hook, cancellation tests.

Acceptance: ordered events, cancellation, reconnect/error behavior, and no duplicate tool/action execution.

## 16. Rollback Strategy

- Keep the Agent behind `AGENT_ENABLED=false` by default and a separate frontend feature flag.
- Add new `/agent/*` routes without changing existing route contracts.
- Keep existing `/chat` until migration acceptance.
- Use additive SQLite tables with schema versions; do not migrate existing batch JSON storage in this project phase.
- Each phase must be independently removable by deleting its new modules and root provider mount.
- Before implementation, initialize or confirm an enclosing Git repository and create a baseline commit. Without Git, create a timestamped project archive before each approved phase.
- Rollback never rewrites Single, Batch, About, predictor, registry, or stored batch jobs.

## 17. Incompatible Local LLM Path

- Use explicit `OpenAIResponsesModel` first because the live direct Responses probe passed and the same server has previously rejected a Chat Completions `temperature` parameter.
- If the SDK Responses path fails but a narrowly shaped Chat Completions tool call passes, test explicit `OpenAIChatCompletionsModel` without unsupported parameters.
- If streaming is missing, ship non-streaming MVP only.
- If native structured output is missing but function arguments are valid JSON, rely on strict function-tool schemas and Pydantic validation.
- If tool calls or tool-result continuation are unreliable, stop conversational execution and return `AGENT_PROVIDER_INCOMPATIBLE`; do not parse free-form text into tool calls.
- Keep deterministic APIs and the current workspace usable with the assistant disabled.
- A provider adapter may normalize protocol shape, but it may not invent tool calls, scientific values, units, or confirmations.

## 18. Recommended Phase 1 Scope

After human approval, implement only provider configuration and the SDK compatibility smoke harness. Pin `openai-agents` and `openai`, add the three required environment variables, default the local development model to the environment-configured `gpt-5.4`, and verify `OpenAIResponsesModel` with one strict function tool. Do not add Agent routes, tools, sessions, or frontend components until this gate passes.

## 19. Phase 0 Acceptance Record

- Required product/architecture/tool/safety/frontend/roadmap documents were reviewed from the supplied documentation pack.
- Real repository modules, routes, pages, state, dependencies, scripts, and tests were audited.
- The local Codex API proxy was started and direct protocol compatibility was verified for health, model discovery, Responses, Chat, tools, continuation, multi-turn, streaming, and timeout handling.
- Backend and frontend unit baselines passed.
- Only this plan and the local compatibility report were created.

## 20. Phase 1 Acceptance Record

- Pinned `openai==2.45.0` and `openai-agents==0.18.2` in both dependency declarations.
- Added strict, Agent-only environment settings with `AGENT_ENABLED=false` by default and mandatory `AGENT_LLM_MODEL` validation.
- Added a minimal `AsyncOpenAI` plus `OpenAIResponsesModel` provider boundary with explicit timeouts, stable error mapping, hosted tracing disabled, and local audit logging retained.
- Verified ordinary response, strict tool call, JSON arguments, tool continuation, tool error continuation, multi-turn context, timeout mapping, and tracing behavior against the local `gpt-5.4` endpoint.
- Verified SDK imports and smoke behavior on Python 3.13.5 and Python 3.11.14.
- Backend regression: 48 passed, 1 opt-in integration test skipped by default.
- Frontend regression: lint and typecheck passed; 17 tests passed.
- Production build, Playwright E2E, and real ADMET-AI smoke were not run in Phase 1.
- No Agent product routes, product tool wrappers, SQLite state, frontend Assistant, UI actions, or deployment were implemented.

## 21. Backend Core Acceptance Record

- Neutral prediction, deterministic input-quality, and neutral comparison services are implemented; legacy `/predict` and `/chat` contracts remain passing.
- Strict Agent contracts and stable errors cover sessions, typed page context, messages, confirmations, pending actions, tool envelopes, structured payloads, UI action proposals, and bounded resources.
- SQLite schema version 1 separates sessions, messages, business state, confirmations, pending actions, resources, and local audit events without migrating existing batch JSON.
- Structure confirmation is hash-bound, canonical-SMILES-bound, expiring, optimistic-versioned, session-owned, and single-use. Names, CIDs, and valid SMILES all stop before prediction.
- Exactly eleven scientific function tools are registered. No run/cancel batch, export, shell, file, web, MCP, hosted, code execution, Registry mutation, or deletion tool exists.
- One non-streaming Agent uses the explicit local `gpt-5.4` Responses provider with bounded turns/tool calls, hosted tracing disabled, local redacted audit logging enabled, and layered guardrails.
- Six non-streaming APIs are implemented: session create/read/history, chat, confirmation, and bounded resource retrieval. No streaming route exists.
- Agent-focused tests: 31 passed. Full backend: 75 passed, 2 opt-in tests skipped by default. Real local provider/API integration: 2 passed.
- Frontend source was not modified; lint, typecheck, and 17 tests passed.
- Production frontend build, Playwright E2E, and real ADMET-AI smoke were not run. Frontend Assistant, streaming, deployment, arbitrary tools, and Multi-Agent were not implemented.
