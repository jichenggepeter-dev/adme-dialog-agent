# Documentation

This index separates current product contracts from historical implementation
records. Start here instead of guessing from a filename.

## Contributor start here

- [Repository README](../README.md): product overview and first local run
- [Contributing guide](../CONTRIBUTING.md): contribution rules and pull-request checks
- [Testing guide](testing-guide.md): Mock Mode, real-model checks, and test layers
- [Security policy](../SECURITY.md): secrets and private vulnerability reports
- [Project positioning](project-positioning.md): users, non-goals, and scientific boundary
- [Concise roadmap](../ROADMAP.md): current milestones
- [Detailed roadmap and acceptance criteria](roadmap-detailed-requirements.md): full requirements behind the milestones

## Current product and scientific references

These documents describe intended current behavior. Code, schemas, and tests
remain the executable source of truth when a document is accidentally stale.

- [Frontend product specification](frontend-product-spec.md)
- [Batch product specification](v2-batch-product-spec.md)
- [Batch file format](batch-file-format.md)
- [Batch job architecture](batch-job-architecture.md)
- [Model information page](model-information-page.md)
- [Endpoint registry](endpoint-registry.md)
- [Endpoint metadata provenance](endpoint-metadata-provenance.md)
- [Computational summary rules](computational-summary-rules.md)

## Current Agent contracts

- [Agent documentation index](agent/00_README_AGENT_DOCS.md)
- [Backend core architecture](agent/backend-core-architecture.md)
- [Backend API](agent/backend-api.md)
- [Session and confirmation model](agent/session-and-confirmation.md)
- [Tool reference](agent/tool-reference.md)
- [Frontend Assistant contract](agent/frontend-assistant-contract.md)
- [Safety and audit](agent/safety-and-audit.md)

## Current release and maintenance evidence

- [Frontend dependency security](frontend-dependency-security.md)
- [Clean-clone verification — 2026-08-02](release/clean-clone-verification-2026-08-02.md)
- [Issue #1 beginner packaging tutorial](issue-1-python-packaging-tutorial.md)

## Historical records retained in place

Plans, audits, reviews, handoffs, QA reports, test reports, fix reports, and
`current-state` snapshots record how the project reached its current state.
They are intentionally retained for course and open-source history, but are
**non-normative**: they may contain old versions, ports, layouts, status, or
future-tense implementation instructions.

This applies especially to:

- the numbered Agent design package `agent/01_*` through `agent/06_*`;
- `agent/*plan*`, `agent/*report*`, `agent/*review*`, `agent/*handoff*`, and
  `agent/*audit*`;
- root documents named `*audit*`, `*qa*`, `*testing*`, `*current-state*`, or
  `*design-decisions*`;
- [real-model diagnostics](real-model-diagnostics.md), which records one past
  environment rather than guaranteeing every current installation.

When records conflict, use this authority order:

1. current code, schemas, and passing tests;
2. current references linked above;
3. roadmap documents for future intent;
4. historical records for context only.

Run `make docs-check` to validate repository-local Markdown links after moving,
adding, or renaming documentation.
