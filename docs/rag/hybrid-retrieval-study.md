# Hybrid retrieval study and decision

Issue [#26](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/26)
asked whether keyword, vector, and metadata retrieval could improve the initial
Evidence RAG without unjustified latency, dependencies, or maintenance. The
answer from this first controlled experiment is **not yet for dense or hybrid
retrieval**. Metadata-aware lexical ranking is the most promising follow-up, but
it also needs another iteration before production use.

## Decision in plain language

The current corpus has seven sources and nine passages. A vector database would
not make this amount of data meaningfully easier to store or search. The useful
question is whether semantic vectors find evidence that keywords miss.

The dense and hybrid methods found more relevant sources overall, but they also
returned an FDA drug-interaction source for an unrelated protein-docking
question. Their hard-negative accuracy fell from `1.000` to `0.750`. The model
also adds an approximately 92 MB cache plus a Transformers runtime. That trade
is not acceptable for the current Research Preview.

Adding already-stored source metadata to lexical ranking improved Recall@3 from
`0.706` to `0.824` and kept hard-negative accuracy at `1.000`. However, it
ranked the withdrawn 2020 drug-interaction guidance ahead of the current M12
guidance for one direct question, reducing the direct-query MRR from `1.000` to
`0.875`. It is therefore a useful direction, not finished production behavior.

No application code, API, database schema, or default dependency changes as a
result of this study.

## Fixed experiment

The study used the versioned 21-query benchmark created in Issue #58 and the
unchanged FDA corpus. Dataset and corpus hashes are recorded in the generated
[Markdown report](../../evaluation/reports/hybrid-retrieval-study-v1.md) and
[JSON report](../../evaluation/reports/hybrid-retrieval-study-v1.json).

The methods were fixed before reading their scores:

1. **Lexical:** the production BM25-style retriever and its existing abstention
   threshold.
2. **Metadata lexical:** the same scoring and threshold after adding source
   date, year, month, version, and lifecycle status to searchable tokens.
3. **Dense:** cosine similarity from
   `sentence-transformers/all-MiniLM-L6-v2`, fixed to revision
   `826711e54e001c83835913827a843d8dd0a1def9`, on CPU with a `0.35` threshold.
4. **Hybrid RRF:** reciprocal-rank fusion of lexical and dense rankings with
   `k=60`.
5. **Hybrid metadata RRF:** the same fusion using metadata-aware lexical
   ranking.

The model and Sentence Transformers package both declare Apache-2.0. The model
is cached outside the repository and no provider, API key, remote vector store,
or external corpus is used. The final report was generated in offline mode
after the first public-model download.

## Results

| Method | Recall@1 | Recall@3 | MRR | Hard negatives | Median warm query |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current lexical | 0.647 | 0.706 | 0.676 | 1.000 | 0.028 ms |
| Metadata lexical | 0.706 | 0.824 | 0.765 | 1.000 | 0.056 ms |
| Dense | 0.706 | 0.765 | 0.735 | 0.750 | 4.6 ms |
| Lexical + dense RRF | 0.765 | 0.765 | 0.765 | 0.750 | 4.0 ms |
| Metadata + dense RRF | 0.765 | 0.824 | 0.794 | 0.750 | 3.9 ms |

All five methods produced identical rankings on the repeated run. With the
model already cached, the recorded CPU model load was about 150 ms and the
nine-passage embedding build about 225 ms. Those values and query timings are
local comparison measurements on the recorded Mac, not production service
levels. Initial model download time is excluded.

The adoption gate requires both overall Recall@3 and MRR improvement, unchanged
hard-negative accuracy, and no Recall@3 or MRR regression in any relevant query
category. No method passed all four conditions.

## Cost and maintenance comparison

| Area | Metadata lexical | Dense or hybrid |
| --- | --- | --- |
| New production dependency | None | Sentence Transformers and model runtime if adopted |
| New stored artifact | None | Approximately 92 MB model cache plus embeddings |
| Offline behavior | Already offline | Offline only after the model is obtained or pre-seeded |
| Deletion and migration | Existing source/index rebuild | Model version and embedding-index migration must be defined |
| Explanation | Existing token and metadata matches | Similarity and fusion ranks require additional explanation |
| Current quality risk | Can prefer a stale exact-title match | One hard negative returned unrelated evidence |

A dedicated vector store was intentionally not tested. With nine passages,
in-memory cosine scoring isolates the value of the embeddings without adding a
database. A store should be evaluated only if user collections become large
enough that measured indexing or query cost requires it.

## Reproduce

Install the optional, locked research environment and run the comparison:

```bash
make evaluate-rag-hybrid
```

The first run downloads the pinned public model. After it is cached, verify that
the experiment works without network access:

```bash
HF_HUB_OFFLINE=1 uv run --extra rag-research \
  python scripts/evaluate_hybrid_retrieval.py --offline
```

The default `make setup`, application runtime, and CI do not install or execute
the research extra.

## Recommended follow-up

Do not ship dense retrieval, RRF, `sqlite-vec`, LanceDB, Qdrant, or another
vector database from this result. If retrieval work continues, create a small
implementation issue for lifecycle-aware metadata ranking that explicitly
prefers current sources over superseded sources, then validate it on a second
held-out query set. Abbreviation expansion should be evaluated separately; the
current study did not solve DDI, DILI, and renal PK shorthand reliably.

The study design follows the official Sentence Transformers semantic-search and
hybrid RRF examples and Qdrant's RRF description:

- <https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html>
- <https://www.sbert.net/examples/sparse_encoder/applications/retrieve_rerank/README.html>
- <https://qdrant.tech/documentation/search/hybrid-queries/>
