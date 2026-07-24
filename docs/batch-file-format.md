# Batch File Format

Supported UTF-8 formats are CSV, TSV, and whitespace-delimited SMI. CSV/TSV
files require a header. SMI uses `SMILES` followed by an optional name.

- Required mapped field: SMILES
- Optional mapped fields: compound ID and compound name
- Maximum file size: 5 MB
- Maximum rows: 5,000
- Empty, unsupported, oversized, and invalidly encoded files are rejected
- Missing and invalid SMILES remain visible
- Duplicates are detected by canonical SMILES and retained as source rows

Examples live in `examples/batch/`. Unmapped input columns are preserved in the
upload record but are not currently included in the results UI.
