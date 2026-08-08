# Contributing to ADME Dialog Agent

Thank you for helping build a transparent, local-first ADME/ADMET exploration
workflow. Contributions are welcome from cheminformatics, scientific software,
Agent engineering, product design, accessibility, testing, and documentation.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) and
[project positioning](docs/project-positioning.md) before starting a
substantial change. The [documentation index](docs/README.md) identifies which
documents are current contracts and which are historical records.

## Find or propose work

- Choose an open issue, especially one labeled `good first issue` or
  `help wanted`.
- Comment before starting so contributors do not duplicate work.
- For a new feature, open a feature request describing the user problem before
  implementing it.
- Do not use a public issue for security vulnerabilities, API keys, private
  molecular data, or session data. Follow [SECURITY.md](SECURITY.md).

## Contribution lanes

### Scientific correctness

Changes to endpoint definitions, units, output types, model provenance, or
scientific explanations must cite a primary or authoritative source. An LLM
response is not evidence.

### Agent safety and evaluation

Changes to tool access, confirmations, context, memory, exports, deletion, or
other Agent autonomy must include tests for authorization, failure handling,
and prohibited scientific conclusions.

### Product and frontend

UI changes must preserve mock/real provenance, scientific disclaimers, keyboard
access, and neutral comparison language. Visual design must not imply
unverified confidence, safety, or candidate ranking.

### Backend and developer experience

Backend changes must preserve mock mode, local-first privacy defaults, bounded
storage, and stable redacted errors. Installation improvements should work for
a clean clone rather than depending on a contributor's machine.

## Development setup

Start with the [15-minute contributor Quick Start](docs/contributor-quick-start.md)
if this is your first change. It demonstrates all four product workflows and
explains the scientific-evidence boundary before asking you to read the wider
architecture.

For the cleanest first run, use the pinned Docker Compose environment:

```bash
docker compose up --build
```

For native development, install uv 0.11.32, Node.js 22.23.1, and npm. uv
installs Python 3.11.15 from `.python-version` when needed.

```bash
make setup
make dev
```

See the [contributor environment guide](docs/contributor-environment.md) for
supported platforms, incremental Compose Watch, disposable data, and recovery
commands.

The default development and test workflow must not require a real model API
key. Keep all credentials in the backend `.env`; never use a `NEXT_PUBLIC_*`
variable for a secret.

## Tests

Run the narrowest tests for your change, then the relevant broader checks:

```bash
make verify
```

`make verify` validates repository-local documentation links, backend tests,
deterministic Agent evaluation, frontend lint and types, frontend unit tests,
and the production build. It uses no provider secret. `make check` remains an
alias for existing contributor notes.

Use Playwright for changed user workflows:

```bash
cd frontend
npm run test:e2e
```

Live LLM and real-model checks are opt-in and must not be required by normal CI.

## Pull requests

Keep each pull request focused on one outcome. In the description:

- state the user or contributor problem;
- explain the selected approach and alternatives;
- identify scientific, privacy, Agent-autonomy, or migration impact;
- list the exact checks you ran;
- include screenshots for visible UI changes;
- confirm that fixtures and logs contain no private data.

Maintainers may request a smaller change if a pull request mixes unrelated
scientific, Agent, backend, and visual changes.

## License

By submitting a contribution, you agree that your contribution may be
distributed under the project's [MIT License](LICENSE). Only submit code,
documentation, data, and media that you have the right to contribute.
