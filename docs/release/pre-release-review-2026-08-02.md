# Pre-release security and rights review — 2026-08-02

This is the evidence report for GitHub Issue #6. It is a repository readiness
review, not legal advice and not a guarantee that every upstream artifact is
cleared for every jurisdiction or use.

## Scope and baseline

- Branch baseline: public `main` at
  `55bde1d3a9de6ae9c98bd8e0ca6b8679a066c7fb`
- Current proposed tree plus all 15 revisions reachable before the final #6
  commit were included in the review
- Reviewed: tracked filenames and text, example environment files, ignore
  rules, runtime-data patterns, direct dependency metadata, ADMET-AI installed
  contents, scientific upstream notices, Git history for media, and local
  Markdown links
- Excluded from source review: generated `.venv`, `node_modules`, `.next`, test
  reports, and other ignored build/runtime directories

## Secret and private-data scan

A redacting Python scanner enumerated every revision with `git rev-list --all`,
read source-like tracked blobs with `git show`, and checked for private-key headers,
high-confidence provider token formats, cloud access-key formats, and literal
credential assignments. It emitted only file paths and line numbers, never a
matched value.

Recorded result:

```text
revisions_scanned=15
unique_flagged_locations=0
```

Additional filename and tree review found only `.env.example` and
`frontend/.env.example` as tracked environment files. Their provider values are
explicit placeholders. No tracked cookie store, private key, runtime database,
upload, log, browser-auth state, cache, or build directory was found.

The scanner is pattern-based, not a proof that no secret has ever existed. A
future tagged release should also run a maintained entropy/history scanner such
as Gitleaks in CI.

## Ignore coverage

`.gitignore` already covered environment files, Python and frontend caches,
SQLite state, jobs, uploads, demo logs, and build/test outputs. This review added
coverage for:

- common package-manager and network credential files;
- PEM/key/container private-key extensions;
- nested databases, exports, and session directories;
- Playwright/browser authentication, storage-state, and cookie files.

Ignored files are only a guardrail. Contributors must still inspect staged
changes and must use private reporting for an exposed credential.

## Dependency and scientific-asset review

Direct Python and npm dependency licenses and reviewed versions are recorded in
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md). `uv.lock` and
`frontend/package-lock.json` remain the complete resolved inventories.

ADMET-AI 2.0.1 declares MIT for its Python distribution, which includes model
checkpoints and a DrugBank-derived approved-drug reference CSV. This repository
does not copy those artifacts; `pip` obtains them as part of the upstream
dependency. Two residual upstream-data questions remain explicit:

1. TDC states that individual datasets have their own licenses, so its MIT code
   license does not by itself clear every training dataset.
2. DrugBank states that use or redistribution of its content requires an
   applicable license and citation. Commercial use or redistribution of a
   built environment therefore needs separate review.

The documented default remains Mock Mode, which does not import or load
ADMET-AI. Real model use must not be described as covered solely by this
repository's MIT license.

## Media and example data

Ten retained PNGs are repository-maintainer-created UI captures and now have a
hash inventory and contribution attestation in
[`asset-provenance.md`](asset-provenance.md). The tracked CSV/SMI examples are
small project demonstration inputs. One unused JPEG with no source or license
record was removed from the current tree instead of making an unsupported
rights claim.

## Commands and checks

Representative commands used during the review:

```bash
git rev-list --all
git ls-files
git log --diff-filter=A -- docs/images docs/agent/reference/assist.jpeg
shasum -a 256 docs/images/*
python -c "import importlib.metadata as m; ..."
node -e "...read direct package metadata..."
make docs-check
git diff --check
```

The full clean-clone test and browser results are recorded separately in
[`clean-clone-verification-2026-08-02.md`](clean-clone-verification-2026-08-02.md).

## Release decision and residual risk

The current repository tree is suitable for a public **research-preview source
release** once CI passes, with these limitations kept visible:

- this was an engineering review, not legal counsel;
- ADMET-AI model-training dataset rights and DrugBank-derived reference-data
  terms require downstream review, especially for commercial or binary reuse;
- the frontend dependency audit still has disclosed high-severity findings;
- the secret scan was pattern-based and should be complemented by an automated
  maintained scanner for a tagged release;
- retained screenshot provenance relies on the maintainer's project-media
  attestation recorded in this change.

Do not call this a production, clinical, regulatory, safety, or fully audited
scientific release.
