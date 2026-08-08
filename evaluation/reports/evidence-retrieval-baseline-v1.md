# Evidence retrieval baseline v1

This report measures the existing deterministic lexical retriever on a fixed corpus. It is a comparison baseline, not evidence of scientific correctness or a production performance claim.

## Baseline identity

- Dataset: `evidence-retrieval-v1` (21 queries)
- Corpus SHA-256: `b3bf131163b079a014e4ec04bdc6ba4e90963ceed636cd5d8f68b1b2c52ea3d3`
- Python: `3.11.14`
- Retrieval: deterministic lexical BM25-style scoring, top 3
- New runtime dependencies: none
- Network access: none

## Quality

| Slice | Queries | Recall@1 | Recall@3 | MRR |
| --- | ---: | ---: | ---: | ---: |
| Overall relevant | 17 | 0.647 | 0.706 | 0.676 |
| abbreviation | 4 | 0.250 | 0.250 | 0.250 |
| direct | 4 | 1.000 | 1.000 | 1.000 |
| metadata | 4 | 0.500 | 0.500 | 0.500 |
| paraphrase | 5 | 0.800 | 1.000 | 0.900 |

Hard-negative accuracy: `1.000`.

The non-perfect paraphrase and abbreviation slices are intentional: they remove the old evaluation ceiling and give Issue #26 room to demonstrate—or fail to demonstrate—a repeatable improvement.

## Local latency sample

Local comparative measurement only; not a production latency claim.

- Samples: 21
- Median: 0.0367 ms
- p95: 0.0717 ms

## Per-query results

| ID | Category | Expected | Retrieved | Reciprocal rank |
| --- | --- | --- | --- | ---: |
| `direct-ddi` | direct | fda-m12-2024 | fda-m12-2024 | 1.000 |
| `direct-mass-balance` | direct | fda-mass-balance-2024 | fda-mass-balance-2024, fda-renal-pk-2024 | 1.000 |
| `direct-metabolites` | direct | fda-metabolites-2016 | fda-metabolites-2016, fda-m12-2024, fda-food-effect-2026 | 1.000 |
| `direct-renal` | direct | fda-renal-pk-2024 | fda-renal-pk-2024, fda-m12-2024, fda-food-effect-2026 | 1.000 |
| `paraphrase-liver` | paraphrase | fda-dili-2009 | fda-dili-2009 | 1.000 |
| `paraphrase-food` | paraphrase | fda-food-effect-2026 | fda-dili-2009, fda-food-effect-2026, fda-metabolites-2016 | 0.500 |
| `paraphrase-renal` | paraphrase | fda-renal-pk-2024 | fda-renal-pk-2024 | 1.000 |
| `paraphrase-mass-balance` | paraphrase | fda-mass-balance-2024 | fda-mass-balance-2024, fda-renal-pk-2024 | 1.000 |
| `paraphrase-metabolites` | paraphrase | fda-metabolites-2016 | fda-metabolites-2016 | 1.000 |
| `abbreviation-ddi` | abbreviation | fda-m12-2024 | none | 0.000 |
| `abbreviation-dili` | abbreviation | fda-dili-2009 | none | 0.000 |
| `abbreviation-food-effect` | abbreviation | fda-food-effect-2026 | fda-food-effect-2026, fda-renal-pk-2024 | 1.000 |
| `abbreviation-renal` | abbreviation | fda-renal-pk-2024 | none | 0.000 |
| `metadata-m12-date` | metadata | fda-m12-2024 | none | 0.000 |
| `metadata-metabolites-year` | metadata | fda-metabolites-2016 | none | 0.000 |
| `metadata-withdrawn` | metadata | fda-in-vitro-ddi-2020-withdrawn | fda-in-vitro-ddi-2020-withdrawn | 1.000 |
| `metadata-food-date` | metadata | fda-food-effect-2026 | fda-food-effect-2026 | 1.000 |
| `hard-negative-quantum` | hard_negative | none | none | n/a |
| `hard-negative-zebrafish` | hard_negative | none | none | n/a |
| `hard-negative-crispr` | hard_negative | none | none | n/a |
| `hard-negative-docking` | hard_negative | none | none | n/a |
