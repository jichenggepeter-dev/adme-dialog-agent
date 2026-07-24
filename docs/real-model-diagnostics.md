# Real Model Diagnostics

Diagnostic date: 2026-07-10

## Outcome

Real ADMET-AI prediction is working in the current local environment. The
reported mock-versus-real concern could not be reproduced as a real-model
failure. The verified failure was instead in API test collection: the installed
FastAPI/Starlette TestClient required `httpx2`, which was not declared.

## Environment

```text
Python        3.13.5
ADMET-AI      2.0.1
Torch         2.13.0
Chemprop      2.2.4
RDKit         2026.3.3
FastAPI       0.139.0
Pydantic      2.13.4
```

The active interpreter and pip both resolve inside `.venv`.

## Original error

`ADME_MOCK_MODE=true pytest -v` failed during collection with:

```text
RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.
```

The smallest real smoke test did not raise a traceback. It initialized
`ADMETModel`, predicted aspirin, and returned a plain Python dictionary.

## Root cause and fix

Root cause: the development dependency list did not include the HTTP client
required by the installed TestClient implementation.

Fixes applied:

- Declared `httpx2` in `requirements.txt` and the `dev` optional dependency.
- Added stable predictor exception classes for model availability, model load,
  and prediction failures.
- Added `GET /status` without forcing model initialization.
- Added explicit `prediction_mode` to prediction results.
- Added local-only CORS origins for the Next.js development server.
- Added structured errors for invalid SMILES and invalid request bodies.
- Kept all ADMET-AI imports, loading, caching, and output conversion inside
  `app/tools/admet_predictor.py`.

## Verification

Mock tests:

```bash
source .venv/bin/activate
ADME_MOCK_MODE=true pytest -v
```

Result: 20 passed.

Real smoke test:

```bash
source .venv/bin/activate
unset ADME_MOCK_MODE
python scripts/smoke_test_admet.py
```

Result: passed; raw output type was `dict`.

Real API:

```bash
unset ADME_MOCK_MODE
uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/status
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"smiles":"CC(=O)OC1=CC=CC=C1C(=O)O"}'
```

`/status` reported real mode, an unloaded model, and an available predictor.
`/predict` returned HTTP 200, canonical aspirin SMILES, grouped properties,
summary, disclaimer, and `prediction_mode: real`.

## Remaining limitations

- The first real request initializes the model and emits verbose Lightning
  progress output.
- Matplotlib may use a temporary cache when the user cache directory is not
  writable. This is a warning, not a prediction failure.
- Torch detects Apple MPS but ADMET-AI currently runs this prediction on CPU.
- Python 3.13 works in this environment, but Python 3.11 remains the more
  conservative baseline for third-party scientific package compatibility.
- Scientific property units and endpoint semantics come from ADMET-AI and are
  not yet annotated in the UI; the application therefore avoids invented
  thresholds and good/bad labels.
