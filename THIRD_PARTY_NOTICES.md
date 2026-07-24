# Third-Party Notices

ADME Dialog Agent is distributed under the MIT License. Third-party software,
models, datasets, services, and media remain subject to their own licenses and
terms.

This document records key direct components. It is not yet a complete audit of
every transitive package in `uv.lock` or the frontend lockfile. That audit is a
release requirement on the roadmap.

## Scientific software

### ADMET-AI

- Project: <https://github.com/swansonk14/admet_ai>
- License: MIT
- Use: local computational ADME/ADMET prediction

If ADMET-AI is useful in research, cite:

> Kyle Swanson, Parker Walther, Jeremy Leitz, Souhrid Mukherjee, Joseph C. Wu,
> Rabindra V. Shivnaraine, and James Zou. "ADMET-AI: A machine learning ADMET
> platform for evaluation of large-scale chemical libraries."
> <https://doi.org/10.1101/2023.12.28.573531>

### RDKit

- Project: <https://github.com/rdkit/rdkit>
- License: BSD-3-Clause
- Use: optional structure validation, canonicalization, and rendering

## Agent and backend software

### OpenAI Agents SDK for Python

- Project: <https://github.com/openai/openai-agents-python>
- License: MIT
- Use: optional Agent orchestration and tool calling

### OpenAI Python

- Project: <https://github.com/openai/openai-python>
- License: Apache-2.0
- Use: OpenAI-compatible Responses API client

### FastAPI

- Project: <https://github.com/fastapi/fastapi>
- License: MIT
- Use: backend HTTP API

## Frontend software

### Next.js

- Project: <https://github.com/vercel/next.js>
- License: MIT
- Use: frontend application framework

### React

- Project: <https://github.com/facebook/react>
- License: MIT
- Use: frontend user interface

## External services

### PubChem

Compound name and CID resolution may use PubChem services. PubChem is an
external service, not bundled software. Users are responsible for reviewing
the applicable service policies before submitting confidential information.

## Models, datasets, and media

The repository license does not relicense ADMET-AI model artifacts, training
datasets, PubChem content, third-party images, or user-supplied molecular data.
Do not add any such asset without documenting its source, license, and
redistribution permission.
