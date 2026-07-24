# Cross-page Assistant Layout and Batch Upload Plan

Status: implementation source, 2026-07-13

## Product decisions

- One Assistant session persists across Single Molecule, Batch Screening, and Model Information.
- Each page exposes only its own allowlisted context and UI actions.
- On desktop, the open Assistant occupies the same left-side workspace position on all three pages.
- On narrower screens, the Assistant becomes a conventional overlay so page content is not compressed beyond a usable width.
- Structure confirmation remains mandatory before a single-compound prediction.
- Batch file selection is always initiated by the user. The Assistant may explain and focus the upload control, but it cannot silently read a local file.

## Current batch upload capability

The manual four-stage workflow already exists:

1. Upload a CSV, TSV, or SMI file.
2. Map SMILES, compound ID, and compound name columns.
3. Review validation, invalid rows, missing values, and duplicates.
4. Confirm and run the batch prediction.

The backend routes and deterministic parsing/validation services are already implemented. The missing product layer is an Assistant-guided entry into this workflow.

## Assistant-guided batch upload follow-up

The follow-up implementation should add only bounded UI assistance:

1. Navigate to `/batch` and focus the upload target.
2. Explain accepted formats and surface the existing file picker.
3. After the user selects a file, read only the server-produced upload metadata and suggested mapping.
4. Propose column mapping changes through a strict UI action schema.
5. Summarize validation results and ask for explicit confirmation before starting prediction.

The Assistant must not receive raw file bytes, local file paths, arbitrary filesystem access, or permission to bypass the existing parser and validation service.

## This implementation slice

- Use one shared left-docked panel style on `/single`, `/batch`, `/batch/[jobId]`, and `/about`.
- Reserve page space while the Assistant is open on Single, pre-run Batch, Batch results, and Model Information.
- Preserve the embedded Single Molecule guided-confirmation workspace.
- Slow panel entrance and exit to approximately twice the previous duration.
- Add a real exit phase so closing is animated instead of immediately unmounting.
- Keep `prefers-reduced-motion` behavior and avoid new dependencies.

## Batch handoff behavior implemented

- The Batch setup page now publishes a validated job ID to the Agent as soon as row validation creates the job.
- The current browser route supplies a non-empty job ID fallback if a live page-context snapshot is temporarily incomplete.
- Agent business state projects `page_context.batch_job_id` into `current_batch_job_id`, which is the bounded field exposed in model instructions.
- `帮我上传一个 Batch 文件` produces only the allowlisted `FOCUS_BATCH_UPLOAD` action. It focuses and highlights the existing user-operated chooser; it does not receive file bytes or paths.
- After the user reviews mapping and validation, asking the Assistant to run the batch creates the existing confirmation-bound pending action.
- After approval starts the job, the frontend reads the returned `batch_summary.job_id` and navigates to `/batch/{job_id}`, where Run & Review loads the analysis.

## Acceptance criteria

- Opening the Assistant on each primary page places it on the left at desktop widths.
- Closing it animates smoothly and restores the page layout after the animation.
- Single guided structure confirmation does not render underneath a second Assistant panel.
- Batch upload controls remain user-operated and functional.
- At 1180 px and below, content returns to the existing responsive layout and the Assistant overlays from the right.
- Typecheck, lint, unit tests, and production build pass.
