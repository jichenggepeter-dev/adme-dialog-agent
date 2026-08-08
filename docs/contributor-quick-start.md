# Contributor 15-minute Quick Start

This path lets a new contributor run the real frontend and backend, while all
predictions and Agent behavior use deterministic test data. It needs no API
key, provider account, private molecule, or real ADMET model download.

The 15-minute estimate starts after Git and Docker are installed. A first image
download can take longer on a slow network. If Docker is unavailable, use the
[native setup](../CONTRIBUTING.md#development-setup) instead.

## 0–3 minutes: start the onboarding workspace

From a fresh clone:

```bash
make onboarding
```

Wait until Compose reports both services healthy, then open
`http://127.0.0.1:3000/single`.

This command starts:

- deterministic Mock predictions;
- the versioned `Mock Agent v1` scenario catalog;
- local-only session and Batch storage;
- the actual FastAPI and Next.js application.

It does not call an LLM provider, PubChem, or the real ADMET-AI model during
the fixed examples below. **Mock** demonstrates software behavior, not
scientific accuracy.

## 3–6 minutes: Single workflow

1. Confirm that the page says **Mock Predictions**.
2. Enter `CCO` in **Compound name, PubChem CID, or SMILES**.
3. Select **Resolve Compound**.
4. Expect **Resolved Compound: Resolved SMILES compound**, formula `C2H6O`,
   canonical SMILES `CCO`, and source **Local RDKit**.
5. Notice that no computational summary exists yet.
6. Select **Confirm Structure & Run Prediction**.
7. Expect **Computational Summary**, an **Absorption** section, and the visible
   Mock label.

`CCO` is the text representation of ethanol. The fixed values in this step are
checked against the current backend in CI.

## 6–9 minutes: Batch workflow

1. Open `http://127.0.0.1:3000/batch`.
2. Upload `examples/batch/sample_mixed.csv` from the clone.
3. Accept the suggested `smiles`, `compound_id`, and `compound_name` mapping.
4. Select **Validate dataset**.
5. Expect 5 total rows: 3 valid rows, 1 invalid SMILES, 1 missing SMILES, and
   1 duplicate; there are 2 unique valid molecules.
6. Select **Run Batch Prediction**.
7. Expect the job status **completed**. Invalid and missing source rows remain
   visible instead of disappearing.

The duplicate is retained as a source row but its canonical molecule is only
predicted once.

## 9–12 minutes: Assistant confirmation workflow

1. Return to `/single` and select **Open ADME Assistant**.
2. Under **Test scenario**, choose **Structure confirmation**.
3. Enter `Show the fixed structure-confirmation workflow.` and send it.
4. Expect an ethanol (`CCO`) guided-analysis card with status
   **Awaiting confirmation**.
5. Confirm that no prediction result exists before your decision.
6. Select **Confirm & Run Prediction**.
7. Expect a Mock computational summary.

In Mock Agent mode, your message is recorded but the selected versioned
scenario determines the behavior. This makes product review repeatable. It is
not a general-purpose LLM response.

## 12–14 minutes: evidence-search workflow

1. In the Assistant, choose **Successful tool run**.
2. Send `What does M12 say about drug interactions?`.
3. Expect a **Supported** evidence answer and a source card titled
   **M12 Drug Interaction Studies** with an FDA link.
4. Optionally choose **Insufficient evidence**, send any non-private text, and
   expect **No evidence** with no invented claim.

The first result comes from the small committed FDA excerpt corpus. Retrieval
does not prove a scientific claim is universally correct and must not become
dosing, clinical, safety, regulatory, or candidate-ranking advice.

## 14–15 minutes: stop and choose a contribution lane

Stop the services without deleting the Docker volume:

```bash
make container-down
```

Choose the smallest lane matching the issue:

| Lane | Typical starting files | Focused checks | Extra requirement |
| --- | --- | --- | --- |
| Scientific metadata | `app/tools/endpoints.py`, `docs/endpoint-*.md`, `tests/test_endpoint_registry.py` | `make test-api` and the relevant registry test | Primary or authoritative scientific evidence |
| Agent safety | `app/agent_runtime/`, `tests/test_agent_*.py` | `make test-agent` | Authorization, prohibited-output, and failure-path tests when autonomy changes |
| Frontend/accessibility | `frontend/components/`, `frontend/e2e/` | `npm run lint`, focused Vitest or Playwright | Keyboard, screen-reader, Mock/real provenance, and neutral language |
| Backend/developer experience | `app/services/`, `app/tools/`, `scripts/`, `Makefile` | Focused Pytest, then `make verify` | Preserve local-first storage, Mock mode, and redacted errors |

Read [CONTRIBUTING.md](../CONTRIBUTING.md) before changing files. A good first
issue should name one observable outcome, a narrow file area, and a focused
verification command. It should not require learning the whole architecture,
using a provider key, or handling real user data. If the `good first issue`
filter is empty or a ticket is too broad, ask a maintainer to narrow a task;
do not choose a tracking or post-deadline research issue as a substitute.

## When scientific evidence is required

Provide a primary or authoritative source when a change affects any of these:

- endpoint definition, unit, output type, positive class, or direction;
- model, training dataset, benchmark, or data-source provenance;
- evidence-corpus text, source lifecycle status, or scientific summary;
- language that interprets a higher/lower value, compares compounds, or states
  a limitation, safety boundary, or applicability claim.

An LLM answer, search-result snippet, or unsourced blog is not evidence. Record
the canonical URL or DOI, version/date, exact section or page, and what the
source supports. Re-check reuse rights before committing third-party text,
data, or media.

Pure formatting, accessibility markup, refactoring, or test maintenance does
not need a scientific citation only when it leaves scientific meaning
unchanged. State that explicitly in the pull request.

## Common errors and recovery

| Symptom | What it usually means | Recovery |
| --- | --- | --- |
| Cannot connect to the Docker daemon | Docker Desktop/Engine is not running | Start Docker, wait until it is ready, then rerun `make onboarding` |
| Port 3000 or 8000 is already allocated | Another local service or older project run owns the port | Stop that process or run `make container-down` for this project, then retry |
| Assistant says disabled or no Test scenario appears | The normal development profile was started instead of onboarding mode | Run `make container-down`, then `make onboarding` |
| A container is unhealthy | Build, dependency, or startup failed | Run `docker compose logs backend frontend` and read the first error for the unhealthy service |
| Expected text differs | The clone is on another revision or local edits changed behavior | Record `git rev-parse --short HEAD`, check `git status`, and compare with [the machine-checked workflow file](../examples/onboarding/workflows.json) |
| Local onboarding state is corrupt and disposable | The Docker data volume contains stale test state | Run `make container-reset`, then `make onboarding`; this deletes only this Compose project's disposable volume |
| `make verify` fails | One repository gate is failing | Rerun the smaller command named immediately above the failure before changing unrelated code |

Never paste an API key, private molecule, unpublished dataset, session export,
or personal path into a public issue. Use synthetic examples and follow
[SECURITY.md](../SECURITY.md) for vulnerabilities.

## What completion proves

Completing this page proves that the contributor can start the no-key workspace
and exercise four current product paths. It does not prove real-model accuracy,
live-provider compatibility, production security, or scientific validity.

For the project to claim independent onboarding success, a person outside the
implementation effort must complete this page without author assistance and
record the result using the [onboarding validation form](onboarding-validation.md).
