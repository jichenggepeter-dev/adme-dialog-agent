# Course Progress and Verification Report — 2026-08-04

Project: ADME Dialog Agent

Team: one student contributor

Course milestone: August 10 Research Preview

Issue: [#11 — Prepare the course demonstration and verification evidence](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/11)

## Plain-language project summary

ADME Dialog Agent is an open-source workspace for inspecting computational
predictions about how a potential drug might be absorbed, distributed,
metabolized, excreted, and associated with toxicity-related model fields. A
person confirms the chemical structure before prediction, can inspect how
fields are described, and can use a constrained Assistant to call approved
tools.

The course demonstration uses ethanol (`CCO`) as a familiar demo molecule and
uses deterministic Mock data. This demonstrates and tests the software
workflow but does not validate a scientific model or establish that a compound
is safe, effective, clinically suitable, or preferable to another compound.

## Features and tasks completed

### Open-source repository foundation

- Published the source repository under the MIT license for project-owned code.
- Added contribution, conduct, security, support, and third-party notices.
- Documented separate license and redistribution risks for scientific models,
  training datasets, and DrugBank-derived data rather than describing all
  upstream material as MIT.
- Removed credentials, runtime databases, uploads, caches, and browser state
  from the publishable source set.
- Verified installation and Mock operation from a clean second clone.

### Product workflow

- Built Single Molecule, Batch Screening, and Model Information pages.
- Added structure resolution and explicit confirmation before prediction.
- Added deterministic Mock predictions and clear Mock/real-mode labels.
- Added endpoint metadata and provenance-oriented result presentation.
- Added a cross-page Assistant with session state and constrained UI actions.

### Agent engineering and safety

- Added a defined live-update format for messages, tool activity,
  confirmations, completion, and errors.
- Added single-use, session-owned confirmation records before prediction or
  other higher-impact actions.
- Added bounded tools, scientific-language rules, audit events, resource
  ownership checks, and stable failure responses.
- Added a deterministic no-key Mock Agent with success, confirmation, timeout,
  tool-failure, and insufficient-evidence scenarios.

### Citation-grounded Evidence RAG

- Added a small, redistributable corpus of captured FDA source excerpts.
- Added repeatable keyword lookup, versioned source records, digital
  fingerprints, permanent excerpt identifiers, and citation-linked claims.
- Added supported, partial, conflicting-fixture, stale-only, prohibited, and
  no-evidence behavior.
- Added a visible Evidence card that keeps claims, excerpts, source links, and
  provenance together.
- Added thirteen fixed evaluation questions. On this curated set, status,
  retrieval, citation-support, and abstention checks each scored `1.0`. These
  scores are not broad scientific validation.

### Product review and CI

- Added a clearly labeled no-key PR Review App configuration.
- Audited the real local frontend and API across five repeatable test
  scenarios.
- Corrected eight product-experience findings covering state recovery,
  confirmation contracts, layout, scrolling, error visibility, prediction
  status, and scientific wording.
- Added GitHub Actions for backend tests, frontend lint/typecheck/unit/build,
  and an automated check that the local no-key demo starts and completes its
  basic workflow.
- PR [#40](https://github.com/jichenggepeter-dev/adme-dialog-agent/pull/40)
  passed all three GitHub Actions jobs at revision `d3d2648` and was merged as
  `bd4275e`.

## Planned work not completed by August 3

### Course demonstration package

The final timed script, fallback matrix, and professor-facing progress report
were not complete by August 3 because implementation and independent validation
of streaming, Evidence RAG, Mock Agent, and the product audit had to finish
first. The demonstration is now the next required item and this report is part
of that work.

### Public HTTPS Review App

The repository contains a Render Blueprint, but no public Preview Environment
has been enabled. Render requires repository administration, a paid workspace,
and acceptance of preview compute cost. A public link is useful for review but
is not required to prove that the source, tests, and local no-key workflow work.

### Real-model validation

The course path has not validated ADMET-AI model accuracy or scientific
suitability. Real-model execution has larger dependencies and separate
scientific and licensing questions. The course build therefore uses clearly
labeled Mock output and does not convert software verification into a model
claim.

### Optional activity trace

The Agent Activity and Evidence Trace prototype in Issue #10 remains optional.
It was not allowed to delay the required streaming, Evidence RAG, product audit,
or course demonstration work.

## Revised plan through August 10

| Priority | Task | Completion evidence |
| --- | --- | --- |
| Must | Review and merge PR #40 | Complete: green CI, reviewed diff, correct authorship, and merge commit `bd4275e` |
| Must | Complete Issue #11 demonstration package | Five-minute runbook, fallbacks, matching screenshots, and durable report |
| Must | Rehearse the five-minute core path once | Recorded duration, revision, observed deviations, and chosen fallback |
| Must | Publish honest Research Preview notes | Actual date, Mock/real distinction, known limitations, and remaining risks |
| Should | Verify the final merged revision from a clean checkout | Backend, frontend, build, and relevant E2E evidence |
| Could | Prototype Issue #10 Activity Trace | Only if every Must item is complete |

The August 10 scope does not include arbitrary document upload, automatic paper
crawling, GraphRAG, multi-Agent orchestration, autonomous loops, candidate
ranking, production deployment, or clinical decision support.

## What is specifically FOSS work

The open-source contribution is not only the application interface. It includes:

1. a public license that applies to project-owned code and a clear record of
   which third-party models or datasets have separate terms;
2. reproducible setup and a no-secret development path;
3. public issues, reviewable commits, pull requests, and CI evidence;
4. contributor governance, security reporting, and documentation authority;
5. typed contracts, deterministic fixtures, regression tests, and failure
   reports;
6. provenance records for scientific sources and project-created screenshots;
7. honest separation of completed engineering, unverified science, and future
   research.

The draft demonstration documents also received an
[independent clarity and coverage review](issue-11-independent-review-2026-08-04.md).
Its documentation findings were checked against Issue #11 before being applied;
the reviewer did not independently verify the code or test results.

## Verification evidence available now

| Evidence | Result | Evidence location or identifier |
| --- | --- | --- |
| PR #40 Backend tests | Passed in GitHub Actions, 2m03s | Revision `d3d26487ac053eb4d5adf600c55b0608b2367706`; [run 30950173090](https://github.com/jichenggepeter-dev/adme-dialog-agent/actions/runs/30950173090) |
| PR #40 Frontend checks | Passed in GitHub Actions, 1m09s | Same revision and GitHub Actions run |
| PR #40 Keyless Review App smoke test | Passed in GitHub Actions, 3m44s | Same revision and GitHub Actions run |
| Clean-copy verification | Installation, Mock tests, and browser flow passed | [`clean-clone-verification-2026-08-02.md`](clean-clone-verification-2026-08-02.md) |
| Issue #11 targeted backend checks | 27 tests passed locally in 9.32s | `tests/test_agent_mock_provider.py`; `tests/test_evidence_rag.py`; local branch `agent/issue-11-course-demo` based on `d3d2648` |
| Issue #11 targeted frontend checks | 9 tests, lint, and typecheck passed locally | `frontend/lib/review-mode.test.ts`; `frontend/components/adme-assistant.test.tsx`; local branch above |
| Issue #11 full backend gate | 141 passed, 2 skipped locally in 42.79s | Full `pytest` run recorded in this report; final committed revision still pending |
| Issue #11 full frontend gates | Lint, typecheck, 55 unit tests, and production build passed locally | `frontend/package.json` gate commands; final committed revision still pending |
| Issue #11 Review App desktop E2E | One exact browser flow passed in 7.9s (13.9s total run) | `frontend/e2e/review-app-mock.spec.ts`; local frontend and API |
| Evidence evaluation | 13 questions; four bounded metrics each `1.0` | `evaluation/evidence_rag_questions.json`; `scripts/evaluate_evidence_rag.py` |
| Product audit | Five Mock scenarios observed through the real local frontend and API | [`issue-9-product-experience-audit.md`](../audits/issue-9-product-experience-audit.md) and `docs/images/audits/issue-9/` |
| Issue #11 browser check | Supported FDA evidence and no-evidence paths passed through the real local frontend and API | `docs/images/course-demo/supported-evidence.jpg` (`2cbad8dc…d61f8cc`) and `no-evidence.jpg` (`41b40c2d…018ddc`) |
| Secret boundary | Review App and default CI require no model-provider credential | `.github/workflows/ci.yml`; `render.yaml`; [`review-app.md`](../review-app.md) |

The historical PR #40 GitHub Actions run is:

<https://github.com/jichenggepeter-dev/adme-dialog-agent/actions/runs/30950173090>

## Remaining verification before the class demonstration

- recapture the two course backup frames with the exact final commit displayed
  in the Review App banner;
- rerun the complete gate set from the final committed revision;
- rehearse the five-minute path and record its actual duration;
- run GitHub CI for the Issue #11 PR and review its diff against current `main`;
- if an HTTPS Review App is desired, separately authorize and fund the Render
  setup, then verify creation, revision display, update, and teardown.

## Current limitations stated to the professor

- The demonstrated prediction is Mock test data.
- The Evidence RAG corpus is intentionally small and does not cover arbitrary
  scientific questions.
- The project is local-first and is not an operated multi-user production
  service.
- Real ADMET-AI use may require substantial dependencies and separate review of
  model-training and reference-data rights.
- The project does not provide clinical, regulatory, safety, efficacy, dosing,
  or candidate-selection conclusions.
- Export, deletion, expanded Agent evaluation, accessibility automation, and
  privacy hardening are planned for later versions.

## Reflection

The realistic course outcome is a well-documented Research Preview with strong
engineering boundaries, not a production drug-discovery platform. Prioritizing
streaming contracts, confirmation safety, deterministic Mock behavior,
citation provenance, CI, and reproducible evidence produced a smaller but more
credible open-source deliverable than attempting GraphRAG, autonomous loops, or
multi-Agent orchestration before the baseline was stable.
