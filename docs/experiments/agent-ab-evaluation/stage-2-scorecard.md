# Stage 2 Implementation Scorecard

This scoring model is locked before Candidate B's implementation is available. Response time is context only and earns no points.

| Criterion | Weight | Full-credit evidence |
| --- | ---: | --- |
| Required behavior | 25 | Both chat routes work without LLM settings; five explicit catalog-v1 scenarios and stable validation errors behave exactly as specified. |
| Scientific and external-call safety | 20 | No OpenAI client, ADMET-AI loader, PubChem request, real sleep, or unsupported scientific claim occurs in deterministic paths, including after confirmation. |
| Architecture and compatibility | 15 | Reuses the current runtime, tool service, schemas, guardrails, persistence, audit, and NDJSON path with additive changes and no unrelated behavior break. |
| Confirmation integrity | 15 | No prediction occurs before approval; approval is hash/state/ownership/TTL protected, forces deterministic Mock output independent of global mode, and replay cannot execute twice. |
| Test quality and independent verification | 15 | Focused and full suites pass; tests use meaningful external-call sentinels, normalized transcript comparison, guardrail/stale-state checks, and can expose an implementation defect rather than merely mirror it. |
| Simplicity and delivery hygiene | 10 | Small legible patch, no new dependency/framework, clean apply-ready artifact, exact results and limitations, no generated files or unsupported claims. |

## Candidate A

| Criterion | Score | Evidence |
| --- | ---: | --- |
| Required behavior | 25/25 | Implements both routes through the shared runtime, exact catalog-v1 IDs, explicit selection, stable mode/version/ID errors, and all five required tool/error paths. |
| Scientific and external-call safety | 20/20 | OpenAI construction, ADMET loading, PubChem, and sleeps have failing sentinels. Mock-origin approval uses a persisted, hash-bound catalog marker and per-call force-Mock path even with global scientific Mock mode false. |
| Architecture and compatibility | 14/15 | Additive settings/request changes, shared tool service, guardrails, audit, state, response, and NDJSON contracts are retained. One point is reserved because Mock scenario dispatch intentionally precedes existing UI-action and Batch-intent parsing; later frontend integration must make that behavior explicit. |
| Confirmation integrity | 15/15 | No prediction before approval; stored payload is ownership/state/TTL/hash protected; replay returns `CONFIRMATION_REPLAYED`; an execution counter remains exactly one. |
| Test quality and independent verification | 14/15 | Candidate and independent focused/full suites pass; normalized streams and external sentinels are strong. Python 3.11 was not separately exercised. |
| Simplicity and delivery hygiene | 8/10 | No dependency or framework was added and the runtime design stays narrow. The 11-file, 933-addition patch is test-heavy but larger than the smallest possible slice. Artifact is clean and applies dry-run. |
| **Total** | **96/100** | Complete, verifiable implementation with no remaining Stage 2 blocker. |

## Candidate B

| Criterion | Score | Evidence |
| --- | ---: | --- |
| Required behavior | 0/25 | No source change or runnable artifact was delivered. |
| Scientific and external-call safety | 2/20 | The response refused to fabricate unverified claims, but no implementation exists to evaluate. |
| Architecture and compatibility | 0/15 | No patch or changed file was available. |
| Confirmation integrity | 0/15 | No executable confirmation implementation or test was delivered. |
| Test quality and independent verification | 0/15 | The final answer states tests could not be verified and provides no log or artifact, despite earlier progress UI claiming focused tests with SDK shims. |
| Simplicity and delivery hygiene | 2/10 | The limitation is stated honestly and no junk artifact was supplied, but the required delivery is absent. |
| **Total** | **4/100** | Honest refusal, but not an implementation deliverable. |

## Decision

- Candidate A: Codex GPT-5.6 Ultra (`96/100`)
- Candidate B: ChatGPT Pro (`4/100`)

Codex wins the Stage 2 implementation comparison. The selected patch is Candidate A's independently reverified artifact. Candidate B's missing artifact is retained as an experimental result and is not silently replaced by advice from its progress trace.

## Workflow conclusion

For this repository and this tool setup:

- Codex should own repository inspection, implementation, test execution, patch production, and final validation.
- ChatGPT Pro can remain an optional research or critique channel when a question benefits from long-form exploration, but it should not sit on the critical path for local code delivery unless its execution/file artifact capability is confirmed at the start.
- The orchestrator should use a strict response contract and a time-bounded progress rule; a long hidden analysis with no durable artifact is not treated as completed work.
