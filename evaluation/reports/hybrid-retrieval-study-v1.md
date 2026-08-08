# Hybrid retrieval study v1

This is a fixed-corpus research comparison for Issue #26. It is not a production rollout or a scientific-validity claim.

## Experiment identity

- Dataset SHA-256: `2eba797c5bef848e71b815d215de4c28b75fa35fb29d0746c6eb560f5186f6c3`
- Corpus SHA-256: `b3bf131163b079a014e4ec04bdc6ba4e90963ceed636cd5d8f68b1b2c52ea3d3`
- Model: `sentence-transformers/all-MiniLM-L6-v2` at `826711e54e001c83835913827a843d8dd0a1def9`
- Model license: `Apache-2.0`
- Cached model bytes: `91578367`
- Offline replay: `True`
- Model load: `161.95` ms; nine-passage index build: `299.53` ms
- Dense threshold: `0.35`; RRF k: `60`
- Production dependency change: none; the model stack is an optional research extra

## Quality and warm-query latency

| Method | Recall@1 | Recall@3 | MRR | Hard negatives | Median ms | p95 ms | Quality gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lexical | 0.647 | 0.706 | 0.676 | 1.000 | 0.0275 | 0.0693 | fail |
| metadata_lexical | 0.765 | 0.824 | 0.794 | 1.000 | 0.0589 | 0.0737 | pass |
| dense | 0.765 | 0.765 | 0.765 | 0.750 | 5.4002 | 6.2362 | fail |
| hybrid_rrf | 0.765 | 0.765 | 0.765 | 0.750 | 4.5337 | 4.9073 | fail |
| hybrid_metadata_rrf | 0.824 | 0.824 | 0.824 | 0.750 | 4.5636 | 5.2805 | fail |

The quality gate requires Recall@3 and MRR to improve overall, hard-negative accuracy to remain 1.0, and no relevant query category to regress on Recall@3 or MRR. Passing this table is necessary but not sufficient for production adoption.

## Repeatability

- `lexical`: `identical` rankings on the repeated run
- `metadata_lexical`: `identical` rankings on the repeated run
- `dense`: `identical` rankings on the repeated run
- `hybrid_rrf`: `identical` rankings on the repeated run
- `hybrid_metadata_rrf`: `identical` rankings on the repeated run

## Locked package versions

- `sentence-transformers==5.6.1`
- `transformers==5.14.1`
- `torch==2.13.0`
- `numpy==2.4.6`
- `scikit-learn==1.9.0`
- `huggingface-hub==1.27.0`
- `tokenizers==0.22.2`

Warm-query timings are local comparison samples on the recorded platform, not production service-level claims. Model download time is excluded; model load and index construction are reported separately.
