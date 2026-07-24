# Batch Screening Conversational Assistant Implementation Plan

Status: implementation source, 2026-07-13  
Scope: Batch Screening Assistant only. Existing Single Molecule and Model Information behavior must remain intact.

## 1. Product Goal

Turn the Assistant into the conversational control and interpretation layer for Batch Screening, while keeping deterministic services authoritative for data and actions.

Users must be able to:

1. Ask for the current batch status and data-quality summary.
2. Find validation and prediction failures without scanning the table.
3. Search, filter, select, and compare rows in natural language.
4. Focus on selected endpoints while preserving page context.
5. Request run, cancellation, and export through bounded workflows.
6. Keep the Assistant visible on the left while independently scrolling results.

The Assistant must not calculate predictions, guess or repair SMILES, invent endpoint semantics, rank a best molecule, modify the Endpoint Registry, or issue clinical/regulatory conclusions. It receives no shell, filesystem, SQL, arbitrary HTTP, or arbitrary UI tool.

## 2. Real Repository Mapping

| Capability | Existing owner | Implementation decision |
| --- | --- | --- |
| Upload and column mapping | `app/tools/batch.py` | Reuse unchanged |
| Validation and deduplication | `app/tools/batch.py` | Reuse unchanged |
| Run and cancellation | `app/tools/batch.py` | Invoke only after Agent confirmation |
| Status and results | `app/tools/batch.py` | Read through deterministic Agent tools |
| Export | Existing FastAPI batch routes | Trigger via allowlisted client action |
| Endpoint meaning | Endpoint Registry | Reuse; never infer metadata |
| Session/resources/audit | Agent repositories | Extend current contracts |
| Side-effect confirmation | `agent_pending_actions` | Activate existing hash-bound storage |

Current gaps:

- `BatchPageContext` exists, but the provider sends empty selections and endpoints.
- Batch UI actions only cover status filters, one row, and opening a job.
- Existing comparison tools do not compare rows belonging to a batch job.
- Pending actions are repository-tested but not exposed through runtime/API/UI.
- The floating Assistant competes with the right preview for space.
- Generic structured cards do not present Batch information compactly.

## 3. Target Experience

### Layout

On `/batch` and `/batch/[jobId]`, the opened Assistant docks into the left column. Results remain in the center and the selected compound/job preview remains on the right. The Assistant and results columns scroll independently. Existing lightweight CSS transitions are used and `prefers-reduced-motion` is honored; no animation or state dependency is added.

At narrow widths the layout becomes stacked/in-flow without hiding table controls or trapping page scroll.

### Progressive disclosure

- Status card: status, progress, mode, and headline counts.
- Issue card: total and first 10 rows, with `See more` for the bounded remainder.
- Comparison card: uniform endpoint rows and 2-5 compound columns; no ranking.
- Pending action card: exact job, action, consequence, Confirm, and Reject.
- Large payloads remain in session resources rather than chat text.

### Core journeys

1. `这个批次现在怎么样？` calls `get_batch_job_status` and reports factual counts.
2. `只看预测失败的分子，并选中第一条。` calls `get_batch_errors`, applies filters, and highlights the row.
3. `找到 ibuprofen 并打开它。` searches only the current batch and selects an exact matching row.
4. `只显示 BBB_Martins、hERG 和 DILI。` changes columns only after keys are verified against registry/job output.
5. `比较第 2、5、8 行的 toxicity endpoints。` creates a neutral side-by-side comparison for completed rows.
6. `开始跑这个批次。` creates a hash-bound pending action and requires explicit approval.
7. `导出当前筛选结果。` uses the existing export route and does not mutate scientific state.
8. Cancellation uses the same explicit side-effect confirmation as run.

## 4. Live Page Context

The page owns Batch UI state and publishes a bounded context to the global provider:

```json
{
  "page": "batch",
  "batch_job_id": "batch_...",
  "selected_compound_ids": ["CMP-001"],
  "selected_row_numbers": [1],
  "selected_endpoints": ["BBB_Martins", "hERG"],
  "validation_filter": "valid",
  "prediction_filter": "completed",
  "search_query": "ibuprofen",
  "range_endpoint": "BBB_Martins",
  "range_min": null,
  "range_max": null
}
```

Bounds: at most 5 selected rows, 20 endpoints, and 200 search characters. No predictions, CSV content, API keys, local paths, or model traces enter page context. The server revalidates every job ID, row, and endpoint.

## 5. Agent Tools

Existing tools retained:

- `get_batch_job_status(job_id)`
- `get_batch_errors(job_id)`
- `summarize_batch_results(job_id, scope, selected_compound_ids, selected_endpoints)`

New deterministic tools:

### `get_batch_rows`

Inputs: job ID plus bounded row numbers or exact compound IDs. Returns identity, validation/prediction status, and available endpoint keys. It resolves references to existing rows; it does not resolve new compounds.

### `compare_batch_rows`

Inputs: job ID, 2-5 row numbers, and 1-20 endpoint keys. Returns a neutral matrix and missing-value notices. Completed rows only; no score, winner, desirability label, or sorting.

### `prepare_batch_action`

Inputs: job ID and `run_batch_job` or `cancel_batch_job`. It validates current job state and creates a pending action; it never executes the action.

## 6. UI Action Allowlist

Add strict discriminated actions:

| Action | Payload | Confirmation |
| --- | --- | --- |
| `SET_BATCH_SEARCH` | bounded `query` | No |
| `SET_BATCH_ENDPOINTS` | verified `endpoints[]` | No |
| `SET_BATCH_RANGE` | endpoint/min/max | No |
| `SELECT_BATCH_ROWS` | up to 5 row numbers and purpose | No |
| `OPEN_BATCH_COMPARISON` | empty | No |
| `EXPORT_BATCH_VIEW` | allowlisted export kind | No |

Run/cancel are not ordinary UI actions. They execute only through approved pending actions.

Every UI action must pass schema validation, session equality, expected state version, route capability registration, duplicate protection, and page-level target/value validation.

## 7. Human-in-the-Loop Model

```text
awaiting_confirmation -> approved -> executing -> succeeded
                      -> rejected
                      -> expired
                      -> failed
```

Requirements:

- Existing SHA-256 payload binding, session binding, state-version binding, and TTL are retained.
- Approval is single-use and replay-safe.
- Batch state is checked again immediately before execution.
- Proposed, approved/rejected, executing, succeeded/failed events are audited without secrets or file contents.
- The confirmation card names the exact job and action.
- A text confirmation is accepted only while one visible pending action exists; buttons are primary.

## 8. Backend File Plan

- `contracts.py`: live context, UI actions, pending-action response/decision schemas.
- `tool_service.py`: row lookup, batch comparison, action preparation/execution adapter.
- `tools.py`: register deterministic read/preparation tools only.
- `repositories.py`: atomic pending-action claim/finish helpers.
- `runtime.py`: expose and execute confirmed actions.
- `routes.py`: action decision/status endpoints.
- `instructions.py`: Batch tool use and safety rules.
- `ui_actions.py`: deterministic common Batch commands.

Prediction and Endpoint Registry ownership do not change.

## 9. Frontend File Plan

- `assistant-page-context.tsx`: live publisher contract.
- `assistant-provider.tsx`: consume current page context and support Batch docking/actions.
- `agent-types.ts`, `agent-schemas.ts`, `agent-api.ts`: mirror strict contracts.
- `ui-action-dispatcher.ts`: dispatch new allowlisted actions.
- `batch-workspace.tsx`: pre-run context and safe-run handoff.
- `batch-job-workspace.tsx`: docking, live context, capabilities, independent scroll.
- Assistant panel/cards: Batch prompts, action confirmation, compact cards, See more.
- `globals.css`: stable responsive columns and reduced motion.

React context and local page state remain the state-management model.

## 10. Test Strategy

Backend tests cover context bounds, row lookup, neutral comparison, invalid/incomplete rows, unknown endpoints, action hash/expiry/stale/replay/wrong-session behavior, and run/cancel service delegation.

Frontend tests cover Zod schemas, live context projection, each reversible capability, pending-action decisions, and 10-row progressive disclosure.

Browser acceptance covers docking, independent scroll, failed-row filtering, endpoint columns, neutral comparison, export, reject/approve run, replay errors, and desktop/mobile layout without clipping or overlap.

## 11. Delivery Phases and Acceptance

### Phase 1: Contracts and live context

The provider sends real bounded Batch state and existing tests remain green.

### Phase 2: Read-only intelligence

Status, issues, lookup, endpoint focus, and comparison use deterministic data only.

### Phase 3: Docked Assistant and UI actions

The three-column workspace is stable, independently scrollable, responsive, and all reversible actions pass registered capabilities.

### Phase 4: Side effects and export

Run/cancel are hash-bound, expiring, single-use actions; export uses existing allowlisted routes.

### Phase 5: Verification

Backend/frontend tests and production build pass; Playwright desktop/mobile acceptance passes; docs include verification commands.

## 12. Risks and Rollback

- Malformed LLM output: strict schemas and deterministic resolver for common commands.
- Stale context: state-version binding and server revalidation.
- Large batches: bounded IDs/counts in prompts; details stored as resources.
- Duplicate execution: atomic pending-action claim and job-state check.
- Assistant obscures results: docked column, responsive fallback, independent scroll.
- Comparison becomes ranking: prohibit scores/winners/sorting and retain disclaimer.

Rollback is phase-local. New capabilities can be unregistered while manual controls remain authoritative. Pending action tools can be disabled while existing manual Run/Cancel APIs continue to work. No batch data migration is required.

## 13. Definition of Done

All core journeys work on real existing batch data; live context is correct; reversible and side-effect actions follow separate safety paths; the layout has no scroll trap or overlap; tests/build/browser checks pass; and ADMET-AI remains the only prediction source with scientific disclaimers visible.
