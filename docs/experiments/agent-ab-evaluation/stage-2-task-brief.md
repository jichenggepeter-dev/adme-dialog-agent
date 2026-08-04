# A/B Stage 2 Task Brief: Minimal Mock Agent Backend Slice

## Experiment rule

Implement this task in the supplied isolated source copy. Do not inspect or reuse another agent's solution. Do not change the original checkout, commit, push, open a pull request, deploy, or operate an external service.

The input is the same source snapshot used for Stage 1:

- baseline commit: `6cdaf80a5c7a99663bc9cf05a2e5c41ab4ec4f30`
- source archive SHA-256: `ecab14fa00741ab1f4a098a855d67f763fe3e329d4ac40b087238a4d65949e55`

## Outcome

Add the smallest complete backend slice for GitHub Issue #12: a deterministic, no-key Mock Agent provider that exercises existing Agent contracts and real deterministic tool services without creating an OpenAI client.

This stage deliberately excludes frontend work, deployment files, CI workflow changes, and broad refactors. A later integration stage will consume the chosen backend design.

## Required behavior

1. Add an explicit Agent provider mode with exactly `live` and `mock` values.
2. `live` remains the default and preserves existing behavior and settings validation.
3. In `mock` mode, `/agent/chat` and `/agent/chat/stream` work without `AGENT_LLM_BASE_URL`, `AGENT_LLM_API_KEY`, or `AGENT_LLM_MODEL`.
4. A chat request can select one versioned scenario explicitly. Do not infer scenarios from message keywords.
5. Accept exactly this request shape as an additive field:

   ```json
   {
     "mock_scenario": {
       "catalog_version": 1,
       "id": "success"
     }
   }
   ```

6. The version-1 catalog contains exactly these stable IDs:

   - `success`
   - `confirmation`
   - `timeout`
   - `tool_failure`
   - `insufficient_evidence`

7. A request in Mock mode must include a valid scenario. A Mock scenario sent in Live mode must be rejected. Unsupported catalog versions or IDs must be rejected with a stable application error.
8. Scenario behavior:

   - `success`: invoke the existing deterministic model-information tool path and return a visibly Mock, non-scientific response.
   - `confirmation`: resolve direct SMILES `CCO` through the existing tool service and return the existing compound confirmation contract. Do not predict before approval. Existing `/agent/confirm` behavior remains the execution path after approval.
   - `timeout`: produce the existing retryable `AGENT_TIMEOUT` error contract without sleeping or calling an external provider.
   - `tool_failure`: invoke the existing prediction-result lookup with a fixed missing fixture ID so the normal tool-error path is observable.
   - `insufficient_evidence`: invoke the existing Evidence RAG tool with a fixed absent-corpus query and return the existing `no_evidence` structured payload with no claims.

9. Mock scenarios must invoke only explicit, allowlisted public methods on `AgentToolService`. Do not use reflection, dynamic imports, arbitrary tool names, ADMET-AI, PubChem, or network access.
10. Preserve the current input guardrail, output guardrail, repository persistence, state-version checks, confirmation security, audit logging, `AgentChatResponse`, and NDJSON version-1 event schemas.
11. Determinism applies to the selected tool path, arguments, tool status, structured-card content, response text, and event type/order. UUIDs, timestamps, and persisted resource identifiers may remain unique; tests must normalize those fields instead of claiming byte-for-byte identity.
12. Every successful Mock response text must identify `Mock Agent v1` and state that it is not a scientific conclusion. The confirmation flow may add the same boundary text while retaining the existing confirmation card.

## Simplicity constraints

- Prefer one small scenario catalog/runner and a narrow runtime branch or injectable seam.
- Do not introduce a general plugin framework, dependency-injection container, new web framework, queue, database, provider registry, process supervisor, or new runtime dependency.
- Do not change the frontend, Docker/deployment files, GitHub Actions, unrelated services, or existing Evidence RAG data.
- Do not implement periodic streaming heartbeats or provider-token streaming in this slice.
- Avoid defensive checks already enforced by Pydantic, the repository, or `AgentToolService`.

## Tests that must be added and run

Add focused backend tests proving:

- Mock mode loads and chats without any `AGENT_LLM_*` setting.
- Live mode still requires its existing provider settings.
- all five scenario IDs follow their required paths;
- missing/unknown/wrong-version scenarios and a Mock scenario in Live mode fail with stable codes;
- the OpenAI client, ADMET-AI loader, PubChem lookup, and real sleep are not reached by deterministic scenarios;
- confirmation creates a pending record and no prediction, then the existing approval endpoint produces explicitly Mock prediction output exactly once;
- repeated semantically identical runs have equal normalized event transcripts;
- existing guardrail and stale-state behavior remains active.

Run the focused tests and the full backend suite. Report exact commands and results. If the environment prevents a test, report the exact blocker and do not claim success.

## Deliverables

Return:

1. A unified patch or complete changed files that can be applied to the isolated baseline.
2. A concise change summary and design rationale.
3. Exact tests run and their raw pass/fail totals.
4. Files changed, dependencies changed, and approximate diff size.
5. Anything not verified and any known limitation.

Do not claim frontend, Preview deployment, GitHub status integration, or the Issue #9 product audit is complete in this stage.
