# V2 Batch Product Specification

The batch workspace is a four-step workflow: upload, map columns, validate, and
run/review. It supports row-preserving validation, canonical-SMILES duplicate
groups, one prediction per unique molecule, partial failures, search and status
filters, endpoint-column selection, numeric range filtering, pagination,
compound preview/detail, neutral 2-5 compound comparison, and exports.

Color communicates application state only. The product does not score, rank, or
label scientific quality. Mock results are explicitly identified as deterministic
development fixtures.
