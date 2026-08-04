# A/B Task Brief: Keyless PR Review App

## Experiment purpose

Compare two coding agents on the same repository snapshot and the same task before either agent can see the other's answer. The comparison covers architecture planning first and implementation quality second.

The repository snapshot is based on commit `6cdaf80a5c7a99663bc9cf05a2e5c41ab4ec4f30` plus the preserved, uncommitted Issue #8 Evidence RAG work. The supplied archive is the complete task input. Do not assume access to the original checkout, private repositories, browser state, credentials, or unlisted services.

## Product outcome

Create a non-production Review App workflow in which a contributor opens a pull request and a reviewer receives one temporary HTTPS link. The reviewer must be able to experience proposed functionality without cloning the repository, installing dependencies, signing in to the application, or supplying a model API key.

This is a professional pre-merge review environment, not production. It must exercise the real frontend components, API contracts, typed streaming parser, confirmation rules, guardrails, and evidence-card contracts. Only external model/scientific-provider behavior may be replaced with deterministic Mock behavior.

## Work packages

### GitHub Issue #12: deterministic no-key Mock Agent provider

- No external provider or API key is required.
- Identical inputs produce stable, versioned events and tool paths.
- Selectable scenarios cover success, confirmation, timeout, tool failure, and insufficient evidence.
- Mock output never presents a real scientific conclusion.
- The interface always identifies Mock mode.
- CI can run the core Agent browser flow with the provider.

### New issue: keyless PR Review App

- Each pull request can expose a shareable Preview link built from that pull request's source revision.
- The frontend must not point at a stale shared backend when reviewing backend changes.
- Preview state is isolated and disposable; it must not use production or contributor-local data.
- Deployment status is visible on the pull request.
- Preview instances expire or are removed after the pull request closes.
- The repository explains Preview limitations and the distinction between CI, Preview, staging, and production.

### GitHub Issue #9: end-to-end product experience audit

- Audit first use, Single, Batch, About, Assistant, typed streaming, and Evidence RAG from a new-user perspective.
- Review hierarchy, terminology, empty states, errors, recovery, keyboard path, and responsive layout.
- Confirm that structure confirmation, Preview/Mock warnings, source cards, and streaming states are distinguishable.
- Every finding needs evidence, affected step, severity, user impact, and recommendation.
- Release-blocking findings must be fixed or explicitly block release.
- Save the evidence-backed report in the repository.

## Architecture boundaries

- Preserve the existing Next.js 16 App Router frontend and FastAPI backend.
- Preserve existing API and typed NDJSON streaming contracts unless a documented additive change is required.
- Preserve human confirmation for prediction, batch execution, export, deletion, and other consequential actions.
- Do not add multi-agent orchestration, arbitrary tools, arbitrary document upload, clinical advice, candidate ranking, or production persistence.
- Do not load ADMET-AI or call PubChem in deterministic demo paths.
- Do not depend on SQLite durability across serverless invocations.
- Do not put secrets in source, `NEXT_PUBLIC_*` variables, fixtures, logs, or browser state.
- Deployment-platform credentials, if later required to connect an account, are operational credentials and must remain outside the repository.
- Prefer a small, legible vertical slice over defensive abstractions and unrelated refactors.

## Required scenario contract

Define a small versioned catalog with stable scenario identifiers. At minimum:

- `success`
- `confirmation`
- `timeout`
- `tool_failure`
- `insufficient_evidence`

The selected scenario must be explicit and testable; avoid hidden prompt keyword magic. Scenario output must use the same event and structured-card schemas as the normal Agent path.

## Stage 1 deliverable: independent design

Do not write implementation code in Stage 1. Return:

1. Recommended deployment architecture and why it fits this repository.
2. One rejected alternative and the concrete reason it is weaker.
3. Exact files/modules to create or change.
4. Mock provider interface and scenario data shape.
5. Request, streaming, confirmation, and state lifecycle.
6. CI and browser-test design.
7. Product audit capture plan.
8. Risks, non-goals, and unresolved external setup.
9. A staged implementation plan whose first slice is independently runnable.

Do not claim that tests, deployment, or account configuration were completed.

## Stage 2 deliverable: implementation

Stage 2 will be assigned only after Stage 1 is scored. It will require a minimal complete patch, focused tests, exact commands/results, and a list of anything not verified. Do not commit, push, open a pull request, deploy, or modify external services.
