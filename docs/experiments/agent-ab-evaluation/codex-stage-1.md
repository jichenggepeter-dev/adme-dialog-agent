# Stage 1 — Independent design

> Experiment metadata: Design-only proposal against baseline commit `6cdaf80a5c7a99663bc9cf05a2e5c41ab4ec4f30` and source archive SHA-256 `ecab14fa00741ab1f4a098a855d67f763fe3e329d4ac40b087238a4d65949e55`; no implementation, tests, deployment, or external account configuration was performed.

## 1. Recommended deployment architecture

Use a Render Blueprint Preview Environment with one Docker web service per pull request, built from the PR head SHA.

```text
Temporary HTTPS URL
        |
      Caddy
   /api/*    /*
      |       |
  FastAPI   Next.js 16
      |
  /tmp/review-app/
  ├── agent.sqlite3
  └── data/{uploads,jobs}
```

The container should run:

- Caddy on the platform `$PORT`, with buffering disabled for `/api/agent/chat/stream`.
- Next.js standalone on loopback port 3000.
- One Uvicorn worker on loopback port 8000.
- `NEXT_PUBLIC_API_BASE_URL=/api`, so every browser request is same-origin.
- `AGENT_ENABLED=true`, `AGENT_PROVIDER_MODE=mock`, and `ADME_MOCK_MODE=true`.
- `COMPOUND_LOOKUP_MODE=local_only` so deterministic review paths cannot call PubChem.
- `AGENT_DB_PATH` and `ADME_DATA_DIR` under an ephemeral `/tmp/review-app`; no persistent disk and no production or contributor-local mounts.
- No `AGENT_LLM_*` variables, model key, production database, or other application secret.

This fits the repository because:

- Next.js and FastAPI are built from one checkout and shipped in one image, making a stale shared backend impossible.
- A single worker matches the process-local lock and daemon-thread assumptions in `app/tools/batch.py` and the SQLite implementation in `app/agent_runtime/repositories.py`.
- The current frontend’s `NEXT_PUBLIC_API_BASE_URL` and loopback-only FastAPI CORS are handled by a same-origin reverse proxy rather than broadening CORS.
- The checked-in `resources/evidence/index.json` can be copied read-only into the image, while all mutable state remains disposable.
- The reviewer receives one HTTPS link and needs neither an application account nor a provider key.
- The platform’s GitHub integration should publish a deployment/check status on the PR and remove the environment when the PR closes.

A persistent global banner must say, on every route: “PR Preview · Mock Agent · Mock predictions · temporary synthetic state · not scientific conclusions.” The capabilities response should also expose the PR revision, provider mode, and scenario-catalog version so the UI can show which revision it is exercising.

The repository’s current `SECURITY.md` explicitly rejects unauthenticated internet-facing use. Therefore the default recommendation includes platform-level repository/team access protection, not an in-application login. If the chosen account cannot protect previews—or if any external sign-in is disallowed—the public deployment must remain blocked pending a security exception and review.

## 2. Rejected alternative

Reject a Vercel frontend preview paired with one shared FastAPI backend.

It is weaker because backend-changing PRs would still run against stale code, different PRs would share SQLite and Batch state, and two independent deployments would require race-prone URL injection and cleanup. Moving this FastAPI backend into serverless functions is not a drop-in fix: it depends on SQLite, filesystem JSON jobs, daemon threads, long Agent requests, and process-local state.

## 3. Exact file/module change surface

Create:

- `app/agent_runtime/live_provider.py`
- `app/agent_runtime/mock_provider.py`
- `app/agent_runtime/mock_scenarios.py`
- `tests/test_agent_mock_provider.py`
- `frontend/components/review-mode-banner.tsx`
- `frontend/components/review-mode-banner.test.tsx`
- `frontend/e2e/review-app-mock.spec.ts`
- `frontend/e2e/product-audit.spec.ts`
- `requirements-preview.txt`
- `.dockerignore`
- `Dockerfile.preview`
- `Caddyfile.preview`
- `scripts/start_review_app.sh`
- `render.yaml`
- `docs/agent/mock-provider.md`
- `docs/review-app.md`
- `docs/audits/issue-9-product-experience-audit.md`
- selected synthetic evidence under `docs/images/audits/issue-9/`

Change:

- `app/settings.py`: add `live|mock` provider mode; require LLM URL/key/model only in live mode.
- `app/agent_runtime/provider.py`: provider protocol, turn/result types, shared errors, and lazy factory.
- `app/agent_runtime/runtime.py`: invoke the selected provider through that protocol while retaining input/output guardrails, persistence, auditing, page state, and confirmation logic.
- `app/agent_runtime/contracts.py`: additive explicit scenario selection, capabilities, and mock-run metadata.
- `app/agent_runtime/routes.py`: add `GET /agent/capabilities`; reject missing mock scenarios and mock scenarios sent to live mode.
- `app/agent_runtime/streaming.py`: carry scenario metadata, preserve event version 1, and add periodic heartbeats while the full turn is pending.
- `app/tools/compound.py`: fail closed for non-SMILES name/CID lookup in preview local-only mode.
- `.env.example`: document provider mode and review-only settings without adding credentials.
- `frontend/lib/agent-types.ts`, `frontend/lib/agent-schemas.ts`, and `frontend/lib/agent-api.ts`: capabilities, explicit scenario selection, and strict response metadata.
- `frontend/contexts/assistant-provider.tsx`: load capabilities and always attach the selected scenario in Mock mode.
- `frontend/components/assistant/assistant-panel.tsx`: scenario selector, Mock identity, correct error/blocked tool rendering, and `search_adme_evidence` labeling.
- `frontend/app/layout.tsx` and `frontend/app/globals.css`: persistent review banner and responsive styling.
- `frontend/next.config.ts`: standalone production output.
- `frontend/playwright.config.ts`: unique temporary state, Mock Agent environment, no reused server in CI, and configurable base URL for the packaged container.
- `frontend/package.json`: focused Review App browser command if useful.
- `tests/test_agent_settings.py`, `tests/test_agent_api.py`, `tests/test_agent_streaming.py`, and `tests/test_agent_backend_core.py`.
- `frontend/lib/agent-contracts.test.ts`, `frontend/lib/agent-stream.test.ts`, and `frontend/components/assistant/cards/structured-card.test.tsx`.
- `.github/workflows/ci.yml`: no-key Agent integration, Chromium browser flow, and preview-image smoke.
- `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/README.md`, `docs/testing-guide.md`, `.github/pull_request_template.md`, and `THIRD_PARTY_NOTICES.md`.

Audit-derived product fixes should touch only files named by evidenced findings. A likely release-gate question is whether immediate downloads in `frontend/components/export-actions.tsx` and automatic `EXPORT_BATCH_VIEW` execution in `frontend/components/batch-job-workspace.tsx` satisfy the repository’s stated export-confirmation rule.

## 4. Mock provider interface and scenario shape

The provider seam should be conceptually:

```text
AgentTurnProvider.run_turn(
  turn: message + history + instructions + explicit scenario,
  context: existing ToolExecutionContext
) -> AgentTurnResult(text, provider metadata)
```

The live implementation wraps the current OpenAI Agents SDK behavior. The Mock implementation never creates an OpenAI client. It dispatches only through an explicit map to public `AgentToolService` methods—never reflection, arbitrary imports, or arbitrary tool names—so the real tool limits, structured payloads, guardrails, resources, and confirmations remain active.

Request selection is additive and explicit:

```json
{
  "mock_scenario": {
    "catalog_version": 1,
    "id": "confirmation"
  }
}
```

The validated catalog shape is:

```json
{
  "catalog_version": 1,
  "scenarios": [{
    "id": "success",
    "revision": 1,
    "label": "Success",
    "terminal": "response_completed",
    "tool_plan": [{
      "name": "get_model_information",
      "arguments": {},
      "expected_status": "ok"
    }],
    "safe_text": "Mock Agent v1: deterministic review output, not a scientific conclusion."
  }]
}
```

Required paths:

| Scenario | Fixed tool path | Expected result |
|---|---|---|
| `success` | `get_model_information` | Normal model-information card |
| `confirmation` | `resolve_compound("CCO")`; after approval, existing `predict_single_compound` confirmation path | Real confirmation state/card followed by explicitly Mock prediction |
| `timeout` | No tool; controlled `AGENT_TIMEOUT` from Mock provider | Heartbeat then terminal retryable error |
| `tool_failure` | `get_prediction_results("prediction_missing_fixture")` | Tool activity with `RESOURCE_NOT_FOUND` and normal error card |
| `insufficient_evidence` | `search_adme_evidence` with a fixed absent-corpus query | Existing `evidence_answer` card with `no_evidence`, zero claims |

The message still passes through the existing input guardrail, and final text still passes `validate_scientific_output`. Mock text must always identify the catalog/version and must not summarize a fixture as a real scientific conclusion.

Determinism covers scenario revision, tool names, arguments, status, text, card content, event types/order, and 64-character delta boundaries. Session/message/resource IDs and timestamps remain intentionally unique; tests should compare normalized transcripts rather than falsely promising byte-identical UUIDs.

## 5. Request, stream, confirmation, and state lifecycle

1. PR opens; the platform builds one image from the PR head SHA and starts an empty, single-replica environment.
2. The browser loads capabilities, displays the Mock/Preview banner, and creates the existing 24-hour Agent session.
3. Every Mock chat request includes `session_id`, message, `expected_state_version`, bounded page context, and explicit catalog/version/scenario.
4. `AgentRuntime.chat()` checks state version, persists the user message, applies the input guardrail, updates page context, and invokes the Mock provider.
5. The Mock provider executes fixed plans through `AgentToolService`; normal structured cards, tool activity, warnings, and pending records are produced.
6. NDJSON retains version 1 and one terminal event. The observable order is heartbeat(s), existing `tool_completed` activity, deterministic message deltas, optional `confirmation_required`, then `response_completed`; failures terminate with `error`. The current backend is post-processed streaming, not provider token streaming, and documentation/tests must say so. `tool_started` should remain unused unless a genuine progress callback is implemented.
7. For `confirmation`, `resolve_compound("CCO")` stores the compound, increments state, supersedes an older pending compound confirmation, and returns the existing hash-bound record. It must not predict yet.
8. Approval uses only the stored confirmation ID and expected version. The existing atomic claim verifies session ownership, TTL, hash, canonical SMILES, version, and replay protection before Mock prediction. Rejection runs no prediction; replay or stale versions fail closed.
9. SQLite resources and Batch JSON live only inside the preview container. A restart may erase them; a reload creates a new frontend session. This is a documented Preview limitation, not durability.
10. PR close triggers platform removal. No Preview disk, database, upload, or conversation is promoted to staging or production.

## 6. CI and browser-test design

Keep the current backend and frontend jobs, then add:

- A Python Mock Agent job running the new provider, settings, API, streaming, guardrail, tool-error, confirmation approve/reject/replay, and evidence tests without any `AGENT_LLM_*` variables.
- Negative tests that make `AsyncOpenAI`, ADMET-AI loading, and PubChem lookup fail the test if deterministic scenarios touch them.
- A frontend contract job for capabilities, scenario metadata, every terminal event, and strict structured-card schemas.
- A live Playwright test using the real Next frontend and FastAPI Mock provider, with no `page.route()` interception for Agent endpoints.
- A Docker-image job that builds `Dockerfile.preview`, runs the image locally, waits on `/api/health`, and executes the same core browser flow through Caddy. This catches proxy buffering, path stripping, content type, download headers, and frontend/backend packaging drift.
- Unique temporary DB/data paths and `reuseExistingServer: false` in CI.
- Chromium desktop as the required gate; a focused Pixel 7/keyboard run for banner, confirmation, errors, and Evidence RAG.
- Playwright trace and failure screenshots as CI artifacts.

The live core spec should exercise all five scenarios, verify Mock identity, ensure no prediction before confirmation, approve once, render the prediction resource, show timeout/tool failure distinctly, recover by selecting success, and render `no_evidence` without citations or scientific claims.

The deployment integration should publish the exact revision and URL as a PR deployment/check. Backend/frontend/unit/browser/image checks should pass before the Preview is treated as ready.

## 7. Product-audit capture plan

Run the audit from a fresh browser context and fresh preview state using only direct SMILES and repository sample Batch files.

Capture:

- First use and persistent Preview/Mock identity.
- Single: input, structure review, approval/rejection, loading, results, errors, recovery, export.
- Batch: upload, mapping, validation, run/cancel confirmation, progress, results, comparison, export.
- About: hierarchy, search/filtering, endpoint detail, provenance, Mock/real distinction.
- Assistant: launcher/panel/guided flow, all five scenarios, typed stream states, cancel/recovery, page transitions.
- Evidence RAG: supported, partial, conflicting, no-evidence, prohibited, stale-only, and unavailable cards.
- Desktop, Pixel 7, keyboard-only path, focus return, responsive overflow, reduced motion, and 200% zoom.

The durable report at `docs/audits/issue-9-product-experience-audit.md` should record for each finding:

- ID and tested PR revision.
- Route and affected step.
- viewport/input method.
- screenshot, trace/test name, selector, or response evidence.
- severity and release-blocking status.
- user impact.
- concrete recommendation.
- owner/status and verification evidence after a fix.

Define release blockers as confirmation bypasses, unsupported scientific conclusions/ranking, secret or private-data exposure, an unusable core no-key flow, or a keyboard/responsive defect that prevents completion. A release-blocking finding must be fixed and re-evidenced or leave the Review App deployment status explicitly blocked.

## 8. Risks, non-goals, and external setup

Key risks:

- `SECURITY.md` says the current app lacks authentication and tenant isolation. Platform access protection and a focused security review are mandatory before public exposure.
- SQLite, lazy TTL enforcement, Batch JSON, daemon threads, and process-local locks require exactly one backend worker/replica.
- Restarts lose state, and confirmations left `executing` have no reconciliation worker.
- Current streaming waits for the complete Agent turn; proxy heartbeats mitigate idle timeouts but do not make it token streaming.
- The current full requirements install ADMET-AI even in Mock mode. `requirements-preview.txt` should contain a pinned minimal runtime with RDKit but no ADMET-AI or live-provider packages; live imports must be lazy.
- Fork PRs execute untrusted code. They require manual deployment approval, no injected secrets, read-only repository permissions, and no `pull_request_target` workflow that exposes credentials.
- `.dockerignore` must exclude `.env*` other than examples, `data/`, SQLite files, uploads, `.venv`, `node_modules`, logs, test artifacts, and VCS metadata.
- Preview name/CID resolution must fail locally rather than call PubChem.
- The Evidence index must be explicitly copied because it is currently a source-tree resource, not declared Python package data.
- Existing Agent documentation is behind the code on streaming, schema version, and the current 15-tool allowlist; documentation must be corrected.
- Export confirmation and the difference between a user click and an Assistant-triggered export need an explicit audit decision.

Non-goals:

- Production deployment, staging implementation, durable persistence, autoscaling, or multi-user tenancy.
- Real ADMET-AI, PubChem, or live LLM calls in Preview/CI.
- Multi-agent orchestration, arbitrary tools, arbitrary document upload, clinical advice, ranking, or candidate selection.
- A provider-token streaming rewrite.
- Treating Mock output or the product audit as scientific/model validation.

External setup still required:

- A Render account/workspace and GitHub repository connection.
- Confirmation that the account/plan supports PR Preview Environments, deployment statuses, access protection, concurrent previews, and automatic close cleanup.
- Billing/build-minute limits and a policy for stale open PRs.
- Repository/team access policy and manual approval policy for fork PRs.
- Branch protection naming the required CI and Preview checks.
- Optional organization access gateway/custom domain if native Preview protection is insufficient.

Those operational credentials stay in the platform/GitHub integration and never enter source, fixtures, `NEXT_PUBLIC_*`, logs, or the application container. If Render cannot meet the lifecycle/access requirements, use another platform with the same per-PR Docker/check/cleanup contract; do not fall back to a shared backend.

## 9. Staged implementation plan

1. **Independently runnable no-key slice.** Add the provider protocol, versioned catalog, five scenarios, explicit request field, capabilities route, frontend selector/banner, and focused backend/frontend tests. Run locally with:

   ```text
   AGENT_ENABLED=true
   AGENT_PROVIDER_MODE=mock
   ADME_MOCK_MODE=true
   COMPOUND_LOOKUP_MODE=local_only
   AGENT_DB_PATH=/tmp/adme-review-agent.sqlite3
   ADME_DATA_DIR=/tmp/adme-review-data
   ```

   This slice is complete when a browser can exercise success, confirmation, timeout, tool failure, and insufficient evidence without LLM settings.

2. **Contract and browser gate.** Add periodic streaming heartbeats, scenario metadata, strict frontend validation, correct tool-error rendering, and the non-intercepted Playwright core flow. Preserve all current confirmation and state-version tests.

3. **One-image Review App.** Add the minimal pinned runtime, standalone Next build, Caddy proxy, process supervision, non-root image, ephemeral paths, Docker smoke, and documentation. Verify the browser test against the packaged single URL.

4. **PR lifecycle integration.** Add and validate `render.yaml`, connect the external account, expose the PR-head revision, publish the deployment status, test close cleanup, and document fork/access behavior.

5. **Issue #9 audit and release gate.** Capture the full new-user matrix, commit the evidence-backed report, fix only evidenced release blockers in narrow patches, rerun affected browser/unit checks, and leave the deployment blocked for any unresolved release-blocking finding.

This is a design-only Stage 1 proposal. No source files were changed, no tests were run, and no deployment or external account configuration was completed.
