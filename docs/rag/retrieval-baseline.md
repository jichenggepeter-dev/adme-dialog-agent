# Evidence retrieval baseline and hybrid-search gate

This benchmark gives Issue [#26](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/26)
a fair starting point. It measures whether a retrieval method finds the intended
source; it does not grade generated prose or claim that a retrieved passage is
scientifically correct.

## Why the original evaluation is not enough for comparison

The original 13-question Evidence RAG evaluation remains the safety and contract
regression gate. Its questions deliberately match the small approved corpus and
the lexical retriever scores `1.0` for status, retrieval relevance, citation
support, and abstention. That is useful for detecting breakage, but it leaves no
room to measure a better ranking method.

The versioned retrieval set adds direct wording, paraphrases, abbreviations,
metadata questions, and hard negatives. Every case identifies the relevant
source without placing a source ID or exact source title in the query. Candidate
methods must use the same committed corpus and cases; adding documents or
rewriting queries after seeing results would invalidate the comparison.

## Run it

```bash
make evaluate-rag-baseline
```

The command writes JSON and Markdown reports under `evaluation/reports/`. The
committed [Markdown report](../../evaluation/reports/evidence-retrieval-baseline-v1.md)
is the first lexical baseline. `make verify-backend` also runs the benchmark and
writes disposable copies under the verification report directory.

## Metrics and interpretation

- **Recall@1 and Recall@3** report whether a labelled relevant source appears in
  the first one or three returned sources.
- **MRR** rewards putting the first relevant source closer to rank one.
- **Hard-negative accuracy** checks that unrelated questions return no evidence.
- The existing Evidence RAG evaluator continues to own status, citation,
  prohibited-request, stale-source, conflict, and abstention regressions.
- Latency is a local comparison sample. It is not a hosted-service benchmark or
  production service-level objective.

The report records the corpus hash, retrieval configuration, Python version,
query count, network use, and new runtime dependency list. Rankings and quality
scores must be identical on repeated runs against the same corpus. Timing is
expected to vary by machine.

## Initial baseline

The current lexical implementation reaches Recall@3 `0.706` and MRR `0.676`
across 17 relevant-source queries. Direct queries remain perfect and all four
hard negatives abstain. Abbreviation and metadata questions expose the largest
gaps. These values are descriptive results for the tiny fixed corpus, not
general search-quality claims.

## Candidates for Issue #26

| Candidate | Value to test | Cost or risk to measure |
| --- | --- | --- |
| Metadata-aware lexical ranking | Uses the dates, lifecycle status, version, and topics already stored with each source | Smallest change, but does not solve semantic paraphrases by itself |
| Local dense retrieval | Can recover synonyms and abbreviations through semantic similarity | Requires a pinned embedding model, model-rights review, download/storage, cold-start, and deletion accounting |
| Lexical + dense rank fusion | Preserves exact-token matches while adding semantic recall | Adds tuning and makes ranking explanations more complex |
| Dedicated vector storage | May help when user collections become much larger | Native binaries, migrations, backup/deletion behavior, and operational maintenance are not justified by the current nine passages |

The cheapest experiment is metadata-aware ranking, followed by dense scoring in
memory on this tiny corpus. A vector database should be evaluated only after a
fixed embedding model shows a repeatable quality gain. SQLite FTS5 documents its
built-in BM25 ranking, Sentence Transformers documents local asymmetric semantic
search, and Qdrant and LanceDB document hybrid rank fusion. `sqlite-vec` is a
local SQLite-aligned candidate, but its pre-1.0 extension and platform behavior
need separate validation before adoption.

Primary project documentation used to define those candidates:

- [SQLite FTS5](https://sqlite.org/fts5.html)
- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [`sqlite-vec`](https://github.com/asg017/sqlite-vec)
- [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- [LanceDB hybrid search](https://docs.lancedb.com/search/hybrid-search)

## Adoption gate

A candidate must improve the fixed ranking metrics on repeated runs while
keeping hard-negative accuracy and every original Evidence RAG regression at
their current values. The experiment must separately disclose warm-query
latency, cold start, index size, model and package licenses, dependency changes,
offline behavior, migration needs, and deletion behavior. A small score increase
does not automatically justify a new database or model runtime.

The completed [hybrid retrieval study](hybrid-retrieval-study.md) applies this
gate. It finds a promising metadata-only direction but does not approve a dense
or hybrid method for production.
