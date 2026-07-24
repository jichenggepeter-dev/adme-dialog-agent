# Current State Audit

Audit date: 2026-07-10

## Repository state

The repository is a small FastAPI application with a deliberately isolated
ADMET-AI adapter. It is not currently a Git repository, so change review must
use direct file inspection rather than `git diff`.

```text
adme-dialog-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── formatter.py
│   ├── main.py
│   ├── schemas.py
│   └── tools/
│       ├── __init__.py
│       ├── admet_predictor.py
│       └── smiles.py
├── examples/
│   ├── sample_outputs.json
│   └── sample_requests.json
├── scripts/
│   ├── inspect_admet_keys.py
│   └── smoke_test_admet.py
├── tests/
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_formatter.py
│   └── test_smiles.py
├── .env.example
├── pyproject.toml
├── README.md
└── requirements.txt
```

Generated `.venv`, cache, and bytecode files are omitted from the tree above.

## Runtime and dependencies

- Active Python: 3.13.5 at `.venv/bin/python`
- Declared Python support: 3.11 or newer
- Node: 25.8.1
- npm: 11.11.0
- ADMET-AI: 2.0.1
- FastAPI: 0.139.0
- Pydantic: 2.13.4
- Torch: 2.13.0
- Chemprop: 2.2.4
- RDKit: 2026.3.3

`requirements.txt` currently declares FastAPI, Uvicorn, Pydantic, pytest,
python-dotenv, ADMET-AI, pandas, and NumPy. RDKit is installed transitively by
ADMET-AI in this environment and is also offered as a project optional extra.

## API surface

Current routes:

- `GET /health` returns `{\"status\": \"ok\"}`.
- `POST /predict` accepts `PredictRequest` and returns `PredictionResponse`.
- `POST /predict/batch` accepts `BatchPredictRequest` and returns an untyped
  per-molecule `results` list.
- `POST /chat` accepts `ChatRequest` and returns `ChatResponse`.

Request schemas:

- `PredictRequest`: `smiles: str`
- `BatchPredictRequest`: `smiles_list: list[str]`
- `ChatRequest`: `message: str`

Response schemas:

- `SmilesValidationResult`: validation state, input, optional canonical SMILES,
  and optional error.
- `PredictionResponse`: input and canonical SMILES, grouped predictions,
  summary, and disclaimer.
- `ChatResponse`: conversational message, detected SMILES, and optional result.

## Prediction modes

`app/tools/admet_predictor.py` owns all ADMET-AI-specific integration. It:

- checks `ADME_MOCK_MODE` for `1`, `true`, `yes`, or `on`;
- returns deterministic mock values without importing ADMET-AI;
- imports and initializes `ADMETModel` lazily;
- caches one model instance in `_MODEL`;
- converts pandas, NumPy, mappings, sequences, and non-finite floats into
  JSON-safe values.

Mock and real execution are separate internally, but API responses do not yet
identify which mode produced a result. The model cache state is also not
exposed safely.

## Tests and scripts

Tests cover SMILES validation/extraction, category grouping, the rule-based
agent, and the four existing API routes. The suite does not require the real
model by design.

Smoke scripts:

- `scripts/smoke_test_admet.py` initializes the real model, predicts aspirin,
  and prints raw and JSON-safe output.
- `scripts/inspect_admet_keys.py` prints observed keys and stores a sample under
  `examples/sample_outputs.json`.

## Baseline verification

Command:

```bash
source .venv/bin/activate
ADME_MOCK_MODE=true pytest -v
```

Result: test collection failed before running tests. FastAPI 0.139.0 uses a
Starlette TestClient that now requires the `httpx2` package, but that package is
not declared in the development dependencies. The failure is a test-environment
dependency issue, not an ADMET prediction failure.

Real smoke command:

```bash
unset ADME_MOCK_MODE
python scripts/smoke_test_admet.py
```

Result: passed. ADMET-AI 2.0.1 initialized and returned a plain Python `dict`
for aspirin. Warnings about an unwritable Matplotlib cache and low DataLoader
worker count were non-fatal.

## Gaps before frontend development

- Add the missing API-test dependency and restore mock test execution.
- Add `GET /status` without forcing model initialization.
- Make mock versus real mode explicit in the API contract.
- Add stable structured API errors and avoid returning raw exception text.
- Configure local-only CORS for ports 3000 on localhost and 127.0.0.1.
- Add typed batch responses.
- Add development commands and environment diagnostics.
- Add a frontend API contract based on the stabilized backend schemas.

No duplicated implementation was found. `SmilesValidationResult` is currently
defined but not used as a route response, and `predict_one` is imported directly
in `app/main.py` without being used there; those are minor cleanup candidates.
