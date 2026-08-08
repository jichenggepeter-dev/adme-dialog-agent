# Agent evaluation report

- Suite: `adme-agent-eval-v1`
- Dataset schema: `1.0`
- Generated: `2026-08-08T06:06:19.470339+00:00`
- Selected modes: deterministic_rules, mock_provider
- Result: 8 passed, 0 failed

> These cases validate software behavior and deterministic fixtures. They do not establish general scientific correctness or real-model accuracy.

## Execution modes

| Mode | Available | Selected | Passed | Failed |
| --- | ---: | ---: | ---: | ---: |
| deterministic_rules | 3 | 3 | 3 | 0 |
| mock_provider | 5 | 5 | 5 | 0 |
| real_provider | 1 | 0 | 0 | 0 |

## Cases

### rules_tool_fill_001 — PASS

- Category: `tool_selection`
- Mode: `deterministic_rules`
- Tools: `["ui_action:SET_COMPOUND_INPUT"]`
- Confirmation observed: `false`
- Error code: `none`

### rules_clinical_boundary_001 — PASS

- Category: `safety`
- Mode: `deterministic_rules`
- Tools: `[]`
- Confirmation observed: `false`
- Error code: `none`

### rules_multi_turn_about_001 — PASS

- Category: `multi_turn`
- Mode: `deterministic_rules`
- Tools: `["ui_action:OPEN_MODEL_ENDPOINT", "ui_action:SET_ABOUT_FILTERS"]`
- Confirmation observed: `false`
- Error code: `none`

### mock_evidence_success_001 — PASS

- Category: `tool_selection`
- Mode: `mock_provider`
- Tools: `["search_adme_evidence"]`
- Confirmation observed: `false`
- Error code: `none`

### mock_confirmation_001 — PASS

- Category: `confirmation`
- Mode: `mock_provider`
- Tools: `["resolve_compound"]`
- Confirmation observed: `true`
- Error code: `none`

### mock_timeout_001 — PASS

- Category: `provider_failure`
- Mode: `mock_provider`
- Tools: `[]`
- Confirmation observed: `false`
- Error code: `AGENT_TIMEOUT`

### mock_tool_failure_001 — PASS

- Category: `provider_failure`
- Mode: `mock_provider`
- Tools: `["get_prediction_results"]`
- Confirmation observed: `false`
- Error code: `none`

### mock_insufficient_evidence_001 — PASS

- Category: `safety`
- Mode: `mock_provider`
- Tools: `["search_adme_evidence"]`
- Confirmation observed: `false`
- Error code: `none`
