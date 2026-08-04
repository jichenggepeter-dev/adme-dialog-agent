# Agent A/B Evaluation Baseline

## Source snapshot

- Repository baseline commit: `6cdaf80a5c7a99663bc9cf05a2e5c41ab4ec4f30`
- Working branch at capture: `agent/issue-8-evidence-rag`
- Additional source state: preserved, uncommitted Issue #8 Evidence RAG implementation
- Archive file count: 244
- Archive size: 3.5 MB
- Archive SHA-256: `ecab14fa00741ab1f4a098a855d67f763fe3e329d4ac40b087238a4d65949e55`
- Stage 2 task brief SHA-256: `de45a1c5ea310ba86f702193b53922a81cb3ff8286de3754b7098e69e0d15f5b`

The archive was built from tracked and non-ignored untracked files. It excluded `.git`, dependency folders, build output, caches, runtime databases, browser state, and ignored local configuration.

## Credential scan

No high-confidence private-key, AWS access-key, GitHub token, OpenAI-style token, or Google API-key pattern was found. The only environment files included were the committed `.env.example` files with documented placeholder values.

## Pre-experiment test baseline

- Backend: 118 passed, 2 skipped.
- Frontend unit tests: 51 passed across 14 files.
- Frontend lint: passed.
- Frontend type check: passed.
- Frontend production build: passed after rerunning outside the restricted sandbox because Turbopack creates a local helper process and binds an internal port.
- Documentation link check: 68 Markdown files and 71 repository-local links checked; 0 broken links.
- Targeted Issue #8 and streaming checks: 29 backend tests and 8 frontend tests passed.

Browser E2E is intentionally recorded after the selected implementation because this baseline run was used only to establish a fast failure ruler before the independent proposals completed.

## External-state limitation

The connected GitHub integration returned HTTP 403 when asked to create the Review App issue, and local `gh` authentication reported an invalid token. No GitHub issue, commit, branch, pull request, or deployment was created during baseline preparation.
