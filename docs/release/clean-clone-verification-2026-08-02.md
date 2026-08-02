# Clean-clone verification — 2026-08-02

This report records the reproducibility check for GitHub Issue #4. It separates
deterministic Mock Mode verification from the optional real ADMET-AI model path.

## Baseline and environment

- Public repository baseline: `55bde1d3a9de6ae9c98bd8e0ca6b8679a066c7fb`
- Platform: macOS 26.2, Apple Silicon (`arm64`)
- Project interpreter: Python 3.13.5 in a newly created `.venv`
- System default interpreter: Python 3.9.6, which does **not** satisfy the
  project's Python 3.11 minimum
- Node.js: 25.8.1
- npm: 11.11.0
- ADMET-AI installed by `requirements.txt`: 2.0.1
- Next.js installed by `frontend/package-lock.json`: 16.2.12

The clone did not contain or reuse a virtual environment, `node_modules`, a
database, uploads, runtime state, browser state, or private configuration.
`.env.example` was used as the documented configuration template.

## Installation

The successful install used a Python interpreter that satisfies the declared
minimum and made the local Node/npm installation available on `PATH`:

```bash
python3.13 -m venv .venv
make setup
```

An earlier operator attempt used a deliberately restricted `PATH` that omitted
the installed Node/npm location, so the frontend install could not start. That
attempt was not treated as a product failure. The README now asks contributors
to check Python, Node, and npm versions before installation and explains how to
choose a newer Python interpreter.

The first install is substantial even when the app will run in Mock Mode:
`requirements.txt` installs the complete real-model stack, including ADMET-AI,
PyTorch, Chemprop, and RDKit. This is a contributor-time and disk-space cost,
not evidence that Mock Mode contacted or loaded the model.

## Automated checks

The clean clone completed:

```bash
make check
```

Results:

- Backend: 105 tests passed, 2 skipped
- Frontend lint: passed
- Frontend type check: passed
- Frontend unit tests: 12 files and 41 tests passed
- Next.js production build: passed; all six application routes generated

The install also reported four high-severity npm audit findings in the current
frontend dependency graph. They remain a disclosed dependency risk; the
production/development distinction and upgrade constraint are tracked in the
project's dependency review rather than hidden by this verification.

## Mock Mode browser check

Because the default ports were already used by another local project, the clean
clone was started without stopping that project:

```bash
ADME_MOCK_MODE=true AGENT_ENABLED=false \
  BACKEND_PORT=8100 FRONTEND_PORT=3100 make dev
```

A headless Chromium check then verified:

- `/single`, `/batch`, and `/about` each returned HTTP 200;
- the Single Molecule page visibly identified **Mock Predictions**;
- aspirin SMILES was resolved locally;
- the explicit structure confirmation was completed;
- the computational summary and Absorption section became visible;
- no page-level JavaScript error occurred.

Four `503` responses from `/agent/sessions` were expected: the optional Agent
was intentionally disabled by `AGENT_ENABLED=false`. They did not affect the
prediction workflow and were not counted as application failures.

## What this report does not verify

This is not a real scientific-model validation. It does not claim that ADMET-AI
weights loaded, that a real prediction was scientifically correct, or that any
result is suitable for clinical, regulatory, safety, or candidate-selection
decisions. Real mode remains the explicit, separate `make smoke-real` check.
