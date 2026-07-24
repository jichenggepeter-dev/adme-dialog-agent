# Batch Assistant Findings

## Existing Backend

- `app/tools/batch.py` owns upload parsing, suggested mapping, job validation, duplicate handling, execution, cancellation, exports, and persisted JSON job state.
- Existing Agent tools already provide `get_batch_job_status`, `get_batch_errors`, and `summarize_batch_results`.
- Existing summaries explicitly return `ranking: null` and `winner: null`, preserving the no-ranking boundary.
- `compare_compounds` currently compares session-owned single-prediction resources; it cannot directly compare rows in a batch job.
- Current confirmation contract only models `compound_structure`; side-effecting Batch actions need a generalized action confirmation path or a dedicated batch-action confirmation contract.

## Existing Frontend

- `/batch` owns upload, mapping, validation, and initial run.
- `/batch/[jobId]` owns status polling, filters, search, endpoint selection, range filtering, row selection, comparison selection, exports, cancellation, and compound preview.
- Existing Batch capabilities support `SET_BATCH_FILTERS`, `SELECT_BATCH_ROW`, and `OPEN_BATCH_JOB`.
- Existing page context includes batch job ID, selected compounds/endpoints, and validation/prediction filters, but the provider currently emits empty selections/default filters instead of live page state.
- Batch detail is already a three-column grid: job overview, results table, selected compound preview. Assistant can replace the left overview without obscuring the central table.

## Primary Gaps

- Live Batch page context bridge from workspace state to Assistant provider.
- Batch-specific guided/docked Assistant workspace.
- Deterministic row selection by row number, first failed, first invalid, first missing, or explicit compound ID.
- Batch-row comparison tool that reads job rows directly and remains neutral.
- Safe job-start confirmation and action execution.
- Allow-listed export UI action and explicit confirmation policy for downloads if required by product decision.
- Structured Batch summary/error cards designed for compact left-rail use.
- Tests for natural-language orchestration against real page state.

## Delivered Resolution

- Batch pages now publish live bounded context instead of provider defaults.
- Batch Assistant search, endpoint, range, row selection, comparison, and export actions are typed, route-scoped, and page-validated.
- Batch row comparison reads persisted job rows and explicitly returns no ranking or winner.
- Run and cancel use single-use pending actions with TTL, stale-state checks, atomic claim, replay prevention, and explicit confirmation.
- Desktop Batch review uses a docked left Assistant plus independently scrollable results and preview regions; narrower screens use an overlay with no horizontal overflow.
