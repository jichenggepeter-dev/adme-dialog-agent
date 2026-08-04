# Codex Stage 2 Implementation Result

## Artifact

- Patch: `/private/tmp/adme-ab.EKlzLE/codex-stage2.patch`
- SHA-256: `9af0755c1a8c0f0bc2b41740e1d599e40bec1208e62da0f884f7de74f8736fd8`
- Size: 42,646 bytes / 1,215 lines
- Intentional surface: 11 files, 933 additions, 27 deletions
- Project dependencies and lockfiles changed: no

The patch contains only the intended source, example configuration, and test files. Virtual environments, caches, generated files, and the task brief are excluded. An independent `patch --dry-run -p1` succeeded against the frozen input directory.

## Implementation summary

- Adds explicit `live` and `mock` Agent provider modes; `live` remains the default.
- Adds the strict additive `mock_scenario` request object and five catalog-v1 IDs.
- Runs fixed scenarios only through named `AgentToolService` methods.
- Preserves the existing guardrail, persistence, audit, state-version, confirmation, response, and NDJSON paths.
- Persists Mock origin and catalog version inside the hash-bound confirmation payload.
- Adds a narrow per-call `force_mock` path for confirmation approval, so a Mock-origin approval cannot load ADMET-AI even when `ADME_MOCK_MODE` is absent or false.
- Adds no runtime dependency or general provider/plugin framework.

## Candidate-reported tests

- Focused: 33 passed in 3.94 seconds.
- Full backend: 141 passed, 2 skipped in 4.44 seconds.
- The skips are the existing opt-in live-provider integration tests.

## Independent verification

- Focused with `ADME_MOCK_MODE=true`: 33 passed in 3.86 seconds.
- Focused with `ADME_MOCK_MODE=false`: 33 passed in 3.75 seconds.
- Full backend with the repository's test setting `ADME_MOCK_MODE=true`: 141 passed, 2 skipped in 4.07 seconds.
- Full backend with global `ADME_MOCK_MODE=false`: 138 tests passed, 2 skipped, and 3 existing non-Agent prediction/Batch tests failed because those baseline tests require deterministic scientific Mock mode. The focused Agent suite remained green with `false`; this is recorded as a baseline environment limitation, not attributed to the candidate patch.
- Secret-pattern scan: no credential found. The only key-like match is the committed `.env.example` placeholder `replace-with-your-api-key`.

## Review finding history

The candidate's first green slice still depended on global `ADME_MOCK_MODE` during confirmation approval. Its final self-review identified this as P1, persisted Mock origin in the protected confirmation payload, added per-call force-Mock execution, and reran both suites.

No remaining Stage 2 release-blocking finding was identified in the focused review. One integration consideration remains for the later Review App: the explicit Mock scenario branch intentionally does not run the existing free-form UI-action or Batch-intent parser. That is outside this backend slice but must be handled deliberately when designing the reviewer-facing scenario experience.

## Scope not claimed

Python 3.11, a live LLM provider, frontend selection/labeling, Preview deployment, GitHub status integration, and the Issue #9 browser audit were not verified by this candidate.
