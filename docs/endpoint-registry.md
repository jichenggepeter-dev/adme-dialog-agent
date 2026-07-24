# Endpoint Registry

Registry schema version: `2.0`. Compatible runtime: ADMET-AI `2.x`.

## Layer boundaries

1. Raw prediction: immutable raw key/value output from ADMET-AI.
2. Registry metadata: versioned endpoint meaning and provenance, never molecule values.
3. Enriched result: raw key/value combined with matched registry metadata.
4. Computational summary: cautious prose generated from enriched results.

The API continues to return raw grouped `predictions` and additionally returns
`enriched_predictions`. Registry failure never blocks prediction; unknown fields
remain visible with `output_type=unknown` and `metadata_status=unverified`.

## Output types

Supported types are classification probability, classification label,
regression, molecular descriptor, percentile, count, rule-based, derived value,
categorical, and unknown. A bounded number is never typed from its value alone.

## Categories

Absorption, distribution, metabolism, excretion, toxicity, physicochemical,
drug-likeness, benchmark percentiles, and other are supported. Registry metadata
takes precedence over keyword grouping.

## Matching

Order: exact raw name, explicit alias, conservative normalized formatting, then
unknown fallback. Normalization handles case and spaces/hyphens versus
underscores. It does not remove scientific tokens, so CYP substrate and inhibitor
tasks cannot collapse into one entry. Fuzzy matching is prohibited.

## Verification

- `verified`: directly supported by executable package code or explicit bundled
  metadata semantics, including RDKit calculations and DrugBank percentiles.
- `partial`: task identity/type/unit are package-supported, but endpoint-specific
  scientific interpretation still requires the linked primary task source.
- `unverified`: no matched metadata.

Units render only when `unit_verified=true`.

