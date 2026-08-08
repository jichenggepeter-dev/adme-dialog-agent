# Testing Guide

This project has two prediction modes and several layers of tests. Normal
development should use mock mode so tests are fast and deterministic. Real mode
is a separate integration check of the scientific model and its dependencies.

## Test types

- **Unit test:** checks one small piece of Python or TypeScript logic in
  isolation, such as SMILES extraction or numeric formatting.
- **API test:** calls FastAPI routes in process and checks HTTP status codes and
  JSON contracts without starting a server.
- **Integration test:** checks that separate parts work together. The real
  ADMET-AI smoke test is an integration test because it exercises third-party
  model code, Torch, Chemprop, and model assets.
- **Smoke test:** answers a narrow question: can the most important path run at
  all? It is intentionally smaller than the full suite.
- **End-to-end test:** drives the application in a browser from user input to
  visible results. Playwright covers this after the frontend is running.

## Mock and real modes

Mock mode is enabled with `ADME_MOCK_MODE=true`. It returns deterministic sample
properties and never imports or loads ADMET-AI. Use it for unit tests, API tests,
frontend development, and most end-to-end tests.

Real mode is active when `ADME_MOCK_MODE` is unset. It initializes ADMET-AI on
the first prediction. Use it before a release or after changing scientific
dependencies or `app/tools/admet_predictor.py`.

## Recommended workflow

```bash
make verify
ADME_MOCK_MODE=true make dev
# Exercise /single, /batch, and /about at http://localhost:3000.
```

Run `make test-unit` for Python logic and `make test-api` for FastAPI routes.
Run `make verify` for the broad local check after setup. Each stage names the
smaller command to rerun. `make verify-container` executes the same layers in
the pinned Docker environment.

Real model verification is a separate, opt-in integration check because it can
download or load model assets and takes substantially longer:

```bash
make smoke-real
```

If ports 3000 or 8000 are already in use, keep the two services aligned with:

```bash
ADME_MOCK_MODE=true BACKEND_PORT=8100 FRONTEND_PORT=3100 make dev
```

## Reading failures

Pytest shows the failed test name first, then the assertion or traceback. Read
from the final exception line upward until you reach project code. A collection
error means tests could not start, commonly because an import or dependency is
missing. An assertion failure means the test ran but actual behavior differed
from the expectation.

FastAPI tracebacks appear in the terminal running `make backend`. API responses
intentionally contain a stable error code and safe message rather than internal
traceback details. Match the request time and route in the terminal log when
diagnosing a server failure.

## HTTP status codes

- `200`: the request succeeded.
- `400`: the submitted value, such as a SMILES string, was unacceptable.
- `422`: the JSON body did not match the required request schema.
- `500`: an unexpected backend error occurred.
- `503`: the prediction service or real model was unavailable.

The frontend maps these responses and stable backend error codes to readable
states. It does not display Python tracebacks.
