# Backend Core Test Report

Validation date: 2026-07-12  
Runtime: Python 3.11.14  
SDK: `openai==2.45.0`, `openai-agents==0.18.2`  
Provider: local Responses API, explicit `gpt-5.4`

## Pre-Implementation Baseline

- Backend: 48 passed, 1 opt-in integration skipped.
- Frontend lint: passed.
- Frontend typecheck: passed.
- Frontend: 17 tests passed.

Rollback archive: local pre-implementation backup (not distributed with the
repository).

## Focused Coverage

- Name, CID, and valid SMILES all stop at structure confirmation.
- Confirmed compound predicts; reject, expiry, cross-session access, and replay do not.
- Mock prediction remains explicitly labeled.
- Unknown endpoint metadata remains neutral and Registry-backed.
- Comparison rejects 1 or 6 predictions and never selects a winner.
- Input quality reports deterministic RDKit facts and no applicability-domain score.
- SQLite schema separation, pagination, TTL fields, resource ownership/size, action replay, payload hash, and optimistic version are covered.
- Clinical, shell/file injection, Registry mutation, arbitrary context, and tool allowlist boundaries are covered.
- Provider connection and timeout errors map to stable redacted codes.
- Disabled Agent does not affect existing health/API behavior.

## Provider Integration

The opt-in backend runtime integration uses the real local `gpt-5.4` provider. It verifies that the single Agent calls only `resolve_compound`, returns confirmation without prediction, and predicts only after explicit confirmation.

## Final Results

- Agent-focused tests: 31 passed.
- Full backend suite: 75 passed, 2 opt-in integration tests skipped by default.
- Opt-in local provider/API integration: 2 passed using the real local `gpt-5.4` Responses provider.
- Frontend lint: passed.
- Frontend typecheck: passed.
- Frontend tests: 7 files, 17 tests passed.
- Existing `/health`, `/predict`, `/predict/batch`, legacy `/chat`, compound, Registry, and batch tests remain passing.

Production frontend build, Playwright E2E, and real ADMET-AI smoke were not run and are not claimed as passing.
