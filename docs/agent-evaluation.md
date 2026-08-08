# Agent evaluation suite

The version-1 Agent evaluation suite is a small regression harness for tool
choice, exact tool arguments, confirmation behavior, prohibited language,
provider failures, and multi-turn execution. It tests software behavior; it is
not evidence of general scientific correctness, ADMET-AI accuracy, or clinical
fitness.

## Versioned cases

The reviewable dataset is
[`evaluation/agent/cases-v1.json`](../evaluation/agent/cases-v1.json). Every case
declares:

- one category and one execution mode;
- one or more user turns with optional bounded page context;
- the exact ordered operations and arguments expected;
- forbidden operations;
- whether confirmation must be present;
- prohibited response phrases;
- expected public error and policy codes.

UI actions use names such as `ui_action:SET_COMPOUND_INPUT`; backend tools use
their public Agent tool names. Dataset and report schemas are both version 1.0.

## Execution modes

| Mode | Meaning | Default |
| --- | --- | --- |
| `deterministic_rules` | Input guardrails and deterministic UI intent handling | Yes |
| `mock_provider` | Versioned no-key Mock Agent scenarios through the real local API | Yes |
| `real_provider` | Explicit external-provider evaluation using the configured backend provider | No |

The report always lists how many cases exist and ran in each mode, so Mock or
rule results cannot be presented as real-provider results. Real-provider mode
is opt-in because it can use credentials, incur cost, and vary with the chosen
provider.

## Run the suite

Run the deterministic default and write JSON plus Markdown reports:

```bash
python scripts/evaluate_agent.py
```

Run one category independently:

```bash
python scripts/evaluate_agent.py --category confirmation
```

Run the explicitly configured real-provider cases:

```bash
python scripts/evaluate_agent.py --mode real_provider
```

The default report paths are `evaluation/reports/agent-eval-v1.json` and
`evaluation/reports/agent-eval-v1.md`. A failed expectation returns a non-zero
exit code. CI runs only `deterministic_rules` and `mock_provider`, requires no
provider secret, and writes its temporary reports outside the repository.

## Reading results

The JSON report is intended for automation. The Markdown report summarizes
execution modes and case-level outcomes for maintainers. Response previews are
bounded and cases contain only committed evaluation prompts. Passing this suite
means the declared fixtures behaved as expected; it does not validate arbitrary
questions, unseen providers, or scientific conclusions.
