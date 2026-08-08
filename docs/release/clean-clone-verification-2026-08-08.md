# Clean-clone release verification — 2026-08-08

This report records the final reproducibility check for the v0.1.0 Research
Preview. It covers contributor installation, deterministic Mock behavior, and
the local Review App. It is not a scientific validation of ADMET-AI or a real
LLM-provider evaluation.

## Baseline and isolation

- Release-candidate code baseline:
  `dfb6c43e8c1bd9aa73c2e6c6fc6c83731f803694`
- Pre-release public `main` baseline:
  `ce6dfdce786c63a4736e0cefbff6a87443906f73`
- Platform: macOS 26.2, Apple Silicon (`arm64`)
- Python: 3.12.13 in a newly created `.venv`
- Node.js: 25.8.1
- npm: 11.11.0

The verification used a new `--no-local` clone. It did not reuse a virtual
environment, `node_modules`, a database, uploads, runtime state, environment
configuration, or browser state from a development worktree.

## Installation and reproducibility

The clean clone completed:

```bash
python3.12 -m venv .venv
make setup
```

The complete Python dependency set installed, including ADMET-AI 2.0.1. The
frontend used the committed lock file through `npm ci`; npm reported zero known
vulnerabilities.

An initial clean-clone pass found that `npm install` could rewrite one optional
dependency marker under a different npm major version, and that Next.js 16.3
regenerates `next-env.d.ts` between development and production commands. The
release candidate now uses `npm ci`, generates Next.js types before TypeScript
checking, and ignores the framework-owned declaration file as recommended by
the bundled Next.js documentation.

After setup, verification, production build, and browser smoke testing, the Git
working tree remained clean.

## Standard project checks

The final baseline completed:

```bash
make check
```

Results:

- Documentation: 86 Markdown files and 103 repository-local links checked; no
  broken links.
- Backend: 163 tests passed and 2 opt-in real-provider integration tests were
  skipped.
- Frontend lint and TypeScript checks: passed. The type check generated current
  Next.js route types before running `tsc`.
- Frontend unit and component tests: 19 files and 70 tests passed.
- Next.js 16.3.0 default Turbopack production build: passed; all six application
  routes were generated.

## Browser verification

The complete Playwright suite passed immediately before the reproducibility-only
tooling adjustment: 42 tests across desktop and mobile, covering the Assistant,
streaming, citation cards, Single, Batch, export, and deletion workflows.

On the final baseline, the same keyless Review App smoke path used by CI was
rerun and passed against the real local frontend and FastAPI server:

```bash
cd frontend
npm run test:e2e -- review-app-mock.spec.ts --project=desktop
```

## Limits of this evidence

These checks validate software contracts, local startup, deterministic Mock
predictions, and deterministic Mock Agent behavior. They do not demonstrate
real-model scientific accuracy, clinical or regulatory fitness, a production
deployment, multi-user security, or compatibility with every external LLM
provider. Those claims remain explicitly outside the v0.1.0 release boundary.
