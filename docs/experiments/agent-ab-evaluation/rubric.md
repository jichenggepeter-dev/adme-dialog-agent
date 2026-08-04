# Agent A/B Evaluation Rubric

Score each proposal before revealing the other agent's identity or asking either agent to critique the other. Record concrete evidence for every score.

| Criterion | Weight | What earns full credit |
| --- | ---: | --- |
| Requirement coverage | 20 | Covers every required Mock scenario, PR-specific preview behavior, and every Issue #9 audit surface without silently widening scope. |
| Repository architecture fit | 20 | Reuses the current Next.js, FastAPI, event schemas, guardrails, and services with clear ownership and no duplicated product logic. |
| Scientific and security boundaries | 15 | Keeps Mock results visibly non-scientific, requires confirmations, avoids secrets and production data, and respects ephemeral state limitations. |
| Simplicity and maintainability | 15 | Uses the smallest coherent design, few dependencies, explicit configuration, and no speculative defensive framework. |
| Test quality | 15 | Defines focused backend and frontend tests plus a deterministic browser flow that can fail for meaningful contract regressions. |
| Preview fidelity | 10 | The link runs the pull request's matching frontend and backend behavior, reports status in GitHub, and has a credible teardown lifecycle. |
| Change risk and rollout | 5 | Identifies migration, hosting, cost, cold-start, and failure risks and provides reversible phase boundaries. |

## Stage 2 evidence

When implementations are compared, add objective evidence:

- targeted tests passed/failed;
- full repository gates passed/failed;
- diff size and number of touched modules;
- dependency and lockfile changes;
- security/secret scan results;
- Preview contract smoke result;
- reviewer corrections required;
- unsupported or unverified claims.

Response time may be recorded as context, but it is not a quality score because browser state, queueing, and model runtime are uncontrolled variables.
