# Batch and About Current-State Audit

Audit date: 2026-07-11

## Existing frontend routes

- `/` redirects to `/single`.
- `/single` is a complete two-stage compound resolution and prediction workspace.
- `/batch` is a static placeholder with no upload or batch workflow.
- `/about` is a static three-panel placeholder.
- `/batch/[jobId]` does not exist.

## Shared layout

The root layout owns one persistent `AppHeader`, skip link, metadata, and global
design tokens. Navigation already exposes Single Molecule, Batch Screening, and
Model Information. Active state currently checks exact paths and must be refined
so nested batch job routes keep Batch Screening active.

## Reusable single-molecule components

- `CompoundConfirmationCard` renders backend-supplied RDKit depiction and identity.
- `PredictionResults`, `PredictionCategory`, `PropertyRow`, `EndpointDetails`, and
  `RawOutputPanel` can render grouped batch-row details without duplicating
  endpoint interpretation logic.
- `ScientificDisclaimer`, loading, empty, error, and status components can be reused.
- API calls and explicit TypeScript contracts are centralized in `frontend/lib`.

## Existing backend batch capability

`POST /predict/batch` accepts a JSON list of SMILES and returns independent
per-molecule results. It performs no file parsing, column mapping, row
preservation, duplicate handling, job persistence, progress tracking,
cancellation, or export. The predictor adapter already caches the real model and
offers `predict_many`, but the route currently calls the normal prediction
service per input.

## Existing endpoint registry capability

`GET /endpoints` returns seven endpoints observed in deterministic mock output.
Each record preserves the raw key and includes display name, category,
prediction type, optional unit, description, limitations, and a boolean
verification flag. Units are currently absent and metadata is unverified. There
is no single-endpoint route, pagination, or richer metadata-status vocabulary.

## Prediction and status modes

`GET /status` reports actual mock/real mode, whether the model is loaded, whether
the predictor package is available, and backend version. Model name, model
version, and initialization timestamp are not currently reported and must render
as unavailable rather than being invented.

## Missing backend work

- Safe CSV, TSV, and SMI parsing with explicit limits.
- Column mapping and row-level validation contracts.
- Canonical-SMILES duplicate grouping while retaining all source rows.
- UUID batch jobs with atomic local JSON/CSV storage under `data/jobs`.
- Real processed/completed/failed counts and terminal-state handling.
- Partial failures, cancellation contract, result reads, and safe exports.
- Formula-injection protection and structured batch error codes.
- Endpoint detail and expanded status contracts.

## Missing frontend work

- Four-step upload, mapping, validation, run/review workflow.
- Batch job overview, summary metrics, progress, results table, filters,
  endpoint selection, pagination, compound preview/detail, comparison, and exports.
- Nested `/batch/[jobId]` route.
- Data-driven model overview, endpoint catalog/details, prediction modes,
  scientific scope, source responsibilities, limitations, and metadata footer.

## Risks and blockers

- In-process execution and local files are not durable production job infrastructure.
- Real ADMET-AI calls are expensive and not safely interruptible mid-call; cancellation
  can prevent subsequent work but cannot terminate an active third-party model call.
- The observed endpoint registry is intentionally incomplete and must not invent
  units, thresholds, descriptions, or model versions.
- Browser file upload and polling require careful cleanup to avoid overlapping requests.
- The repository is not a Git repository, so review uses direct file inspection.

## Implementation plan

1. Add typed parsing, validation, job-storage, execution, progress, cancellation,
   and export modules behind new `/batch/*` routes.
2. Extend status and endpoint metadata without loading the model or fabricating values.
3. Add test fixtures and backend tests before wiring the frontend.
4. Build reusable batch workflow components and `/batch/[jobId]` review route.
5. Build the model transparency center from actual `/status` and `/endpoints` data.
6. Add component and Playwright coverage, responsive captures, and design QA.

## Expected implementation files

- Backend: `app/main.py`, `app/schemas.py`, `app/tools/batch.py`,
  `app/tools/batch_storage.py`, `app/tools/endpoints.py`, predictor status helpers.
- Frontend: `app/batch/page.tsx`, `app/batch/[jobId]/page.tsx`,
  `app/about/page.tsx`, shared header/CSS, new batch and model-information components,
  `lib/api.ts`, `lib/types.ts`, and error mappings.
- Tests and fixtures: backend batch/endpoint tests, frontend component tests,
  Playwright flows, and `examples/batch/*`.
- Documentation: batch product, format, architecture, endpoint registry, model page,
  testing, and design-decision documents plus README and Makefile updates.

## Baseline verification

- Backend: 25 tests passed.
- Frontend lint: passed.
- Frontend typecheck: passed.
- Frontend components: 11 tests passed.
- Next.js production build: passed.
- Existing Playwright desktop/mobile suite: 12 tests passed.

