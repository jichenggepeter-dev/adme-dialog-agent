# Stage 1 Blind Scorecard

The identities are intentionally omitted from this working scorecard. Each proposal is scored against the rubric before either candidate sees the other's answer. Response time is not scored.

## Candidate A

| Criterion | Score | Evidence |
| --- | ---: | --- |
| Requirement coverage | 20/20 | Covers all five explicit Mock scenarios, a PR-head Review App lifecycle, the full Issue #9 audit surface, and clearly separates Preview from production. |
| Repository architecture fit | 19/20 | Correctly reuses Next.js, FastAPI, `AgentToolService`, typed NDJSON v1, confirmation storage, SQLite, and the Evidence index. The same-origin, single-revision design avoids a stale shared backend. One point is reserved because proposed periodic heartbeats and a capabilities API widen the contract beyond the minimum requested slice. |
| Scientific and security boundaries | 15/15 | Mock output is explicitly non-scientific; direct `CCO` avoids PubChem; ADMET-AI and model credentials are absent; existing confirmation and output guardrails stay authoritative; public access limitations are called out rather than hidden. |
| Simplicity and maintainability | 9/15 | The design is coherent but proposes a broad surface: three supervised processes in one container, a new capability contract, provider split, heartbeats, a minimal requirements set, many documents, and a large test/audit matrix. Several elements are useful later but exceed the smallest independently runnable slice. |
| Test quality | 15/15 | Defines focused settings/provider/API/stream/confirmation tests, explicit negative network/model assertions, a real non-intercepted browser flow, normalized determinism checks, and a packaged-container smoke test. |
| Preview fidelity | 10/10 | One image is built from the PR head, serves matching frontend/backend through one HTTPS origin, publishes PR status, isolates ephemeral state, and is removed when the PR closes. |
| Change risk and rollout | 5/5 | Names cost, plan capability, fork-PR, access, cold-start, SQLite, single-worker, proxy buffering, dependency, licensing, and cleanup risks, with reversible implementation phases. |
| **Total** | **93/100** | Strong and source-grounded, with its principal weakness being scope size rather than correctness. |

## Candidate B

| Criterion | Score | Evidence |
| --- | ---: | --- |
| Requirement coverage | 4/20 | Mentions an ephemeral Preview and existing confirmation/session paths, but omits all five scenario designs, the PR deployment/status/teardown mechanism, and the entire Issue #9 audit plan. |
| Repository architecture fit | 10/20 | Correctly identifies typed NDJSON, SQLite/local state, the existing vertical path, confirmation flow, and Playwright infrastructure. It does not provide the required exact files, provider interface, request shape, or lifecycle. |
| Scientific and security boundaries | 3/15 | Advises preserving confirmation and local state but does not address visibly non-scientific Mock output, ADMET-AI/PubChem/network exclusion, secrets, public access, or production-data isolation. |
| Simplicity and maintainability | 7/15 | The advice is concise and favors a minimal vertical slice, but the absence of a concrete coherent design is under-specification rather than useful simplicity. |
| Test quality | 2/15 | Says to reuse the existing test organization but supplies no backend, frontend, browser, negative-network, determinism, or Preview smoke design. |
| Preview fidelity | 2/10 | Calls for ephemeral isolated previews, but provides no platform topology, same-revision frontend/backend guarantee, PR status, HTTPS link, or teardown mechanism. |
| Change risk and rollout | 1/5 | Notes restart/persistence boundaries in general, but provides no staged implementation, operational setup, cost, access, cold-start, fork-PR, or rollback analysis. |
| **Total** | **29/100** | Source-aware high-level advice, but it did not produce the nine explicitly required Stage 1 deliverables. |

## Identity reveal and Stage 1 decision

- Candidate A: Codex GPT-5.6 Ultra (`93/100`)
- Candidate B: ChatGPT Pro (`29/100`)

Codex wins Stage 1 planning. Its answer is materially more complete, source-grounded, testable, and operationally credible. The reviewer's correction to carry into implementation is to reduce Codex's proposed change surface and avoid treating later hardening as part of the first working slice.

ChatGPT Pro's initial answer is retained as an experimental result, not silently replaced. The prolonged analysis was given repeated no-interruption checks; after the same progress step remained visible, `Answer now` was used at 27 minutes 37 seconds to obtain the model's current deliverable. Response time is not included in the score.
