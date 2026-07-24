# Computational Summary Rules

Summary text is generated from enriched endpoint results, not raw numerical
ranges or endpoint-name guessing.

- Probability language requires `classification_probability`, documented
  positive-class semantics, enabled probability language, and verified or
  explicitly partial package metadata.
- Unknown bounded values use neutral numerical-value language.
- Regression values use neutral numerical-value language and verified units only.
- Descriptors, counts, rules, and derived values state the calculated value.
- Percentile language requires verified DrugBank percentile metadata and names
  the documented approved-DrugBank reference set.
- Percentiles never imply favorable or unfavorable direction.
- Summaries must not use good, bad, safe, unsafe, clinical risk, favorable, or
  unfavorable conclusions.
- All summaries end with an experimental-validation boundary.

