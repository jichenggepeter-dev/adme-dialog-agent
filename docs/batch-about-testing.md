# Batch and About Testing

Backend tests cover CSV/TSV/SMI parsing, file errors, mapping, row validation,
duplicates, empty valid sets, job execution, actual progress counts, partial
failure, cancellation, missing jobs, exports, formula-injection protection,
endpoint detail, and expanded status.

Frontend component tests cover upload accessibility, format guidance, mapping,
validation counts, model status, endpoint metadata, search, and scientific
boundaries. Playwright covers the mock success workflow, mixed input, result
review/export controls, about filters/details, navigation, and responsive
overflow.

Run `make check` and `cd frontend && npm run test:e2e`.
