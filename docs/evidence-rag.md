# ADME Evidence RAG

The ADME evidence workflow is a small, offline retrieval layer for bounded
educational explanations. It does not predict molecules and does not turn
retrieved text into clinical, dosing, safety, regulatory, or compound-ranking
advice.

## Corpus and rights

`resources/evidence/corpus.json` contains short excerpts from seven official
FDA pages captured on 2026-08-03. Six records are current guidances. One record
is deliberately marked `superseded` so stale-source behavior is testable. Each
record keeps its canonical URL, document date, lifecycle status, capture date,
section, and FDA reuse-policy basis.

FDA states that FDA-authored website text and graphics are public domain unless
otherwise noted. The project nevertheless keeps links and capture dates because
FDA pages change. A maintainer must re-check the canonical page, lifecycle
status, excerpt, and policy before updating or adding a source. Do not add
third-party papers or datasets without a separate redistribution review.

## Rebuild and evaluate

The committed index is derived entirely from the corpus and needs no network or
provider key:

```bash
python scripts/build_evidence_index.py
python scripts/evaluate_evidence_rag.py
python scripts/evaluate_evidence_retrieval.py
```

The builder creates content hashes, stable chunk IDs, and lexical term counts.
Running it twice on unchanged input must produce byte-for-byte identical output.
The evaluator reports retrieval relevance, claim citation support, status
accuracy, and abstention accuracy separately. Its conflict case uses a clearly
labelled synthetic test fixture; the shipped FDA corpus does not invent a
scientific disagreement.

The separate [retrieval baseline](rag/retrieval-baseline.md) uses harder fixed
queries to compare ranking methods without changing the corpus or weakening the
existing safety and citation regression set.

## Runtime behavior

`search_adme_evidence` is the only Agent tool added by this workflow. It returns
one of:

- `supported`: current indexed passages support bounded claims;
- `partial`: only part of a multi-part question is covered;
- `conflicting`: current passages in the same conflict group disagree;
- `no_evidence`: the approved index has no adequate passage;
- `prohibited`: the request asks for diagnosis, dosing, clinical safety,
  treatment, or compound ranking;
- `stale_only`: only a superseded or non-current record matched.

Claims carry their own evidence objects rather than relying on a flat citation
list. Numeric tokens are accepted only when they occur in the cited excerpt.
If the index is missing or corrupt, the tool abstains and reports the evidence
layer unavailable. The prediction API and normal prediction flow do not depend
on the evidence index.

## Known limits

- The corpus is intentionally small and English-only.
- Retrieval is deterministic metadata-aware lexical BM25-style scoring, not
  semantic search. Existing date, version, and lifecycle fields participate in
  ranking; ordinary queries remain limited to current sources, while explicit
  withdrawn or superseded queries may retrieve historical records.
- It does not ingest arbitrary PDFs, crawl websites, or use embeddings.
- Source links and lifecycle status require periodic human review.
- Retrieval relevance is not proof that a scientific claim is universally
  correct; displayed excerpts remain the reviewable evidence.
