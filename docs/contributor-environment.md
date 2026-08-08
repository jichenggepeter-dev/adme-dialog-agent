# Reproducible Contributor Environment

The supported contributor baseline is intentionally narrow: Python 3.11.15,
uv 0.11.32, Node.js 22.23.1, npm's committed lockfile, and Mock Mode. The
repository provides both a Docker Compose path and a native macOS/Linux path.
Neither path needs a provider key.

## Supported environments

| Path | Supported host | Runtime source | Best for |
| --- | --- | --- | --- |
| Docker Compose | Docker Desktop on macOS, Windows/WSL2, or Linux; Compose 2.22+ | Exact images and lockfiles in this repository | Clean clones and machine-independent onboarding |
| Native | macOS or Linux; Windows through WSL2 | `.python-version`, `.nvmrc`, `uv.lock`, and `package-lock.json` | Fast edit-test loops and editor integration |

Native Windows shells are not currently a supported target because the
Makefile and service launcher use POSIX commands. Use Docker Desktop or WSL2.
The containers are development tools, not hardened production images.

## Docker cold start

From a clean clone:

```bash
docker compose up --build
```

Open:

- <http://127.0.0.1:3000/single>
- <http://127.0.0.1:3000/batch>
- <http://127.0.0.1:3000/about>
- <http://127.0.0.1:8000/docs>

The backend is forced into deterministic Mock Mode, the Agent is disabled, and
the Compose file does not read or mount a host `.env` file. Source-build
contexts exclude credentials, Git metadata, local databases, browser state,
and generated artifacts through `.dockerignore`.

The first build downloads the pinned base images and locked dependencies, so it
is slower than later starts. Subsequent starts reuse Docker layers:

```bash
docker compose up
```

## Incremental development

Compose Watch synchronizes source edits while keeping Python and Node
dependencies inside their images:

```bash
docker compose watch
```

Changes under `app/`, `scripts/`, or `frontend/` are synchronized. Changes to
`pyproject.toml`, `uv.lock`, or `frontend/package-lock.json` rebuild the
affected image. Stop the foreground process with Ctrl+C.

## Disposable state

Sessions, Batch jobs, uploads, exports, and the Agent SQLite database live in
the Compose-managed `adme-dev-data` volume, not in the source checkout. Stop
containers without deleting that state with:

```bash
make container-down
```

Delete the containers and the project-scoped development volume with:

```bash
make container-reset
```

`make container-reset` permanently removes only this Compose project's
disposable development state. It does not delete tracked source files or host
credentials.

## Container quality gate

Run the same documentation, backend, Agent, frontend, and production-build
layers used by CI:

```bash
make verify-container
```

Browser E2E and real ADMET-AI checks remain opt-in because they are slower and
have different system or model requirements.

## Native cold start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.11.32,
Node.js 22.23.1, and npm. uv reads `.python-version` and can install the pinned
Python automatically.

```bash
uv python install
make setup
make dev
```

`make setup` performs `uv sync --locked --extra dev` and `npm ci`; it refuses
to rewrite either lockfile. The required uv version is enforced by
`pyproject.toml`.

For the incremental native workflow, rerun `make setup` only after a dependency
file changes. Normal source edits need only the relevant test or `make dev`.

## One-command verification

After native setup:

```bash
make verify
```

The command stops on the first failure and names the layer and retry command.
It covers documentation links, all normal backend tests, deterministic Agent
evaluation, frontend lint and types, frontend unit tests, and the production
build. `make check` remains an alias for compatibility.

Optional gates stay separate:

```bash
cd frontend && npm run test:e2e
make smoke-real
make test-agent-integration
```

The default gate sets Mock Mode, disables the Agent provider, and requires no
API key.

## Network and privacy boundaries

- Image and dependency installation requires access to Docker Hub, GitHub
  Container Registry, PyPI, and the npm registry.
- Direct-SMILES Mock workflows do not need PubChem or an LLM provider.
- Compound name and CID resolution may contact PubChem.
- A host `.env` file is not copied into an image or mounted by Compose.
- Real model assets, private datasets, and provider credentials are outside the
  default contributor environment.
