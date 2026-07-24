# Batch Assistant Delivery Plan

## Goal
Design and implement a Batch Screening conversational copilot that reuses the existing batch services, preserves scientific and action safety boundaries, and operates the Batch UI through allow-listed actions.

## Phases

| Phase | Status | Outcome |
|---|---|---|
| 0. Repository audit | Complete | Verified backend, frontend, contracts, tests, and gaps |
| 1. Implementation specification | Complete | `docs/agent/batch-assistant-implementation-plan.md` is the implementation source |
| 2. Backend capability slice | Complete | Batch tools, action contracts, confirmation, audit, tests |
| 3. Frontend workspace slice | Complete | Three-column assistant, page context, action dispatcher, tests |
| 4. Integrated workflows | Complete | Filters, errors, selection, comparison, safe run/export |
| 5. Verification | Complete | Unit/integration tests, build, and responsive browser evidence |

## Architecture Guardrails

- Reuse `app/tools/batch.py`; do not copy batch parsing, validation, prediction, or export logic into the Agent.
- Keep LLM output descriptive; deterministic tools own data, filters, comparison inputs, and job actions.
- Never infer or repair SMILES with the LLM.
- Never rank a best compound or invent endpoint meaning, units, thresholds, or probability semantics.
- Read-only and reversible UI actions may execute immediately.
- Starting/cancelling a batch or any non-reversible operation requires deterministic confirmation.
- UI actions remain schema-validated and route-scoped.
- Preserve existing Single and About behavior.
- Add no new frontend state library or animation dependency.

## Edit Scope

- Allowed: `app/agent_runtime/**`, focused additions to `app/tools/batch.py`, `frontend/components/**batch**`, `frontend/components/assistant/**`, `frontend/contexts/**`, `frontend/lib/**agent**`, `frontend/lib/ui-action-dispatcher.ts`, `frontend/app/globals.css`, `tests/**`, `frontend/e2e/**`, `docs/agent/**`.
- Allowed if required: `app/main.py`, `app/schemas.py`, `frontend/lib/api.ts`, `frontend/lib/types.ts`.
- Forbidden: predictor model implementation, Endpoint Registry data mutation, unrelated Single/About redesign, dependency replacement, deployment.

## Test Ruler

- Backend unit tests for every new tool and action/confirmation transition.
- Integration test for status -> filter/error focus -> safe start confirmation.
- Frontend unit tests for context projection and action execution.
- Playwright for Batch Assistant docking, filters, selected row, comparison, confirmation, and independent scrolling.
- Full backend tests, frontend typecheck/lint/tests, production build.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Running backend used the pre-change request contract | Browser search returned an invalid 422 response | Restarted FastAPI with the new contracts and normalized validation errors |
| Consecutive select/open comparison actions observed stale React state | Row selection succeeded but the comparison panel remained closed | Kept validation in the selection action and made the reversible open action independent of an async state read |
| Chinese `第1行和第4行` was not recognized | Request fell through to the model | Extended the deterministic comparison grammar and added a regression test |
