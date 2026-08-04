# Issue #8 implementation and independent verification

Date: 2026-08-03

Issue: [#8 — Build a small citation-grounded ADME Evidence RAG workflow](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/8)

Local branch: `agent/issue-8-evidence-rag`

Baseline: `6cdaf80a5c7a99663bc9cf05a2e5c41ab4ec4f30`

## Dual-agent record

The source package sent to ChatGPT Pro was 3,629,814 bytes with SHA-256
`80c53e2e4695205c0267c3b89daa29c85152fbb79c9928635c4ef0d6090b210e`.
The conversation is:

<https://chatgpt.com/c/6a714b71-1fb0-83ea-b2aa-f40cc17b7a83>

ChatGPT Pro twice failed to provide code. Its first run displayed progress that
claimed backend, frontend, and tests had been implemented, then acknowledged
that no patch or ZIP existed. After receiving that contradiction and a reduced
vertical-slice request, it again displayed “implemented” progress and finally
acknowledged that it had produced no repository artifact. Those claims were not
used as evidence. Codex implemented and verified the local change independently.

## Implemented scope

- Seven FDA source records and nine short excerpts, including one explicitly
  superseded record for stale-source behavior.
- A deterministic, dependency-free local index builder with source content
  hashes and stable chunk IDs.
- A compact lexical BM25-style retrieval and policy service with `supported`,
  `partial`, `conflicting`, `no_evidence`, `prohibited`, and `stale_only` states.
- Claim-level provenance and numeric-token validation against exact evidence
  spans.
- One allowlisted `search_adme_evidence` Agent tool and strict backend payload.
- Matching strict TypeScript/Zod contracts and an evidence/source-card UI.
- Thirteen repeatable evaluation questions. The conflict case is a labelled
  synthetic test fixture; no scientific conflict is invented in the FDA corpus.
- Source, rights, rebuild, evaluation, and limitation documentation.

No vector database, embeddings provider, crawler, arbitrary PDF ingestion, new
Agent framework, or runtime dependency was added. Prediction remains independent
of the evidence index.

## Verification evidence

- Full backend: `118 passed, 2 skipped`.
- Frontend: lint passed; typecheck passed; 14 test files and 51 tests passed.
- Production build passed with Next.js 16.2.11.
- Dedicated evidence E2E: desktop and mobile passed (`2 passed`).
- Full E2E: 35 passed and one unrelated mobile test failed. The same test,
  `assistant-actions.spec.ts` / `applies failed batch filter once`, failed in the
  clean Issue #7 worktree with the same textarea/form pointer interception. It is
  a pre-existing mobile Assistant drawer defect, not an Issue #8 regression.
- Two independent index rebuilds and the committed index were byte-identical:
  29,275 bytes, SHA-256
  `cc9685ed491883f7f7456a9d60fe958a56cd4f0b4734a538bdc95b3936831863`.
- Evaluation: 13 questions; status accuracy, retrieval relevance, citation
  support, and abstention accuracy were each `1.0`.
- Markdown: 64 files and 70 repository-local links checked; zero broken links.

The evaluation metrics describe only the curated deterministic test set. They
are not external scientific validation, production validation, or evidence that
the corpus covers arbitrary ADME questions.

## Publication state

All Issue #8 changes are local and uncommitted in the isolated worktree. No
commit, push, pull request, deployment, database migration, or production
configuration change was performed.
