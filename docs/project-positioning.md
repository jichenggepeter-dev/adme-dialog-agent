# ADME Dialog Agent: Project Positioning

Status: approved product direction for the `0.1.x` Research Preview

## Product definition

ADME Dialog Agent is an open-source, local-first, human-in-the-loop workspace
for exploring computational ADME/ADMET predictions through visual and
controlled conversational workflows.

It is first a complete scientific exploration product for users, and second a
reference implementation for bounded, auditable scientific Agents. It is not a
general Agent SDK, a clinical tool, or an autonomous drug-selection system.

## Users and job to be done

The primary users are early-stage drug-discovery researchers who have one or
more candidate compounds but do not want to assemble a Python, API, and batch
processing workflow before inspecting computational ADME/ADMET predictions.

Students in medicinal chemistry, cheminformatics, and related fields are a
secondary audience. Scientific-software and Agent developers are an important
contributor audience.

The core job is:

> Given a compound name, PubChem CID, SMILES string, or small batch, help me
> confirm what structure will be analyzed, inspect transparent computational
> predictions, compare like-for-like endpoint values, and export the results
> without turning model output into an unsupported scientific conclusion.

## Core workflow

```text
Input compound
-> resolve and confirm structure
-> run prediction
-> inspect raw values, metadata, and provenance
-> filter or compare compatible endpoints
-> export results
```

The product reduces workflow friction while keeping the user responsible for
scientific interpretation and downstream decisions.

## Product pillars

### Transparent ADME exploration

- Accept names, CIDs, SMILES strings, and batch files.
- Preserve raw model output and prediction provenance.
- Separate known metadata from unknown or unverified metadata.
- Show whether results came from deterministic mock mode or a real model.

### Controlled scientific copilot

- Allow low-risk, reversible navigation and filtering actions.
- Require confirmation before prediction, batch execution, export, or deletion.
- Ground explanations in structured tool output.
- Never rank candidates or create an unvalidated composite score.

### Local-first research workflow

- Keep sessions, audit events, and results local by default.
- Run the default development and test flow without an API key.
- Make every external service and its data boundary explicit.
- Collect no product telemetry by default.

## Human-Agent boundary

The Agent may automatically:

- explain endpoint definitions and visible page state;
- search, filter, select, and switch views;
- resolve a compound and present the resulting structure;
- summarize structured results with their provenance;
- compare compatible raw endpoint values neutrally.

The Agent must request confirmation before:

- running a confirmed single-compound prediction;
- starting or cancelling a batch job;
- exporting results or conversations;
- deleting sessions or local data.

The Agent must never:

- make experimental, clinical, regulatory, or safety claims;
- recommend a best drug candidate;
- translate higher or lower values into better or worse without validated
  endpoint semantics;
- invent units, confidence, applicability-domain evidence, or measurements;
- run arbitrary shell commands, code, or file operations;
- modify the endpoint registry;
- send complete user datasets to an undeclared external service.

## Scientific responsibility

The project supports exploration and understanding of computational
predictions. It does not make experimental, clinical, regulatory, safety, or
candidate-selection decisions.

An allowed statement reports what a model produced:

> The model produced a higher value for compound A on this endpoint.

A prohibited statement turns that output into an unsupported conclusion:

> Compound A is safer or is the better drug candidate.

The same boundary applies in the UI, API, exports, documentation, tests, and
contributor review.

## Data and external services

The application is local-first, not necessarily offline:

- direct SMILES handling and mock predictions can run locally;
- name and CID resolution may call PubChem;
- real ADMET-AI execution loads its scientific model locally;
- the optional Agent sends bounded context to the provider configured by the
  person running the project;
- conversation and prediction data remain in local SQLite and file storage
  unless a user explicitly exports them.

Accounts, cloud sync, hosted multi-user storage, and default telemetry are not
part of the `0.1.x` product.

## Repository identity

The repository is a full-product monorepo containing:

- FastAPI backend and deterministic scientific services;
- Next.js frontend;
- Agent runtime, tool contracts, guardrails, and confirmations;
- tests and evaluation fixtures;
- examples and public documentation;
- contributor tooling.

It is not yet a plugin platform. A reusable framework should be extracted only
after a second real scientific workflow proves the abstraction.

## Release status

Version `0.1.0` is a Research Preview for education, software development, and
exploratory research. APIs and storage schemas may change before `1.0`.

The preview does not promise:

- production or multi-user deployment readiness;
- stable public APIs or database migrations;
- validated model confidence or applicability-domain estimates;
- clinical, regulatory, or safety suitability.

## Success measures

The north-star measure is core exploration task success: a user can confirm a
structure, run a prediction, understand provenance, and compare or export
results without producing an unsupported scientific conclusion.

Guardrails are treated as hard requirements:

- zero unconfirmed high-impact actions;
- zero cross-session data leakage;
- zero mock results represented as real predictions;
- zero invented units or confidence claims;
- zero clinical, safety, or automatic candidate-ranking conclusions;
- zero secrets or user runtime data committed to the repository.

GitHub stars and usage counts are discovery signals, not proof of product
value.

## Community model

The project welcomes contributions in four lanes:

1. scientific correctness and metadata provenance;
2. Agent safety and evaluation;
3. product, frontend, and accessibility;
4. backend and developer experience.

Scientific claims require evidence. Changes that expand Agent autonomy require
explicit safety tests. Contributors do not need expertise in every lane.

## Explicit non-goals

The current roadmap excludes:

- a general scientific-Agent platform;
- a plugin marketplace;
- autonomous candidate selection;
- medical or clinical advice;
- a multi-user SaaS account system;
- automatic cloud synchronization;
- redistribution of third-party assets without permission.
