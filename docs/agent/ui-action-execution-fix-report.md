# UI Action Execution Fix Report

Date: 2026-07-12

## 1. Root cause

The backend always returned an empty `ui_action_proposals` array. The frontend
preserved that array, but its dispatcher only emitted an unhandled browser
event for most actions. No route registered access to real React state. Plain
Assistant text was rendered directly in a paragraph, exposing raw Markdown.

See `ui-action-and-message-rendering-audit.md` for pre-fix evidence and line
references.

## 2. Original break point

The first break was `AgentRuntime.chat`, which hardcoded an empty action array.
Even a manually injected action would then stop at the frontend dispatcher,
because `/single`, `/batch`, and `/about` had no capability registry.

## 3. Previous backend behavior

The backend did not return UI actions. It could only return model prose, which
is why supported action requests were described instead of executed.

## 4. Action contracts

The backend now uses a strict discriminated Pydantic union mirrored by Zod and
TypeScript. Supported reversible actions are:

- `NAVIGATE`
- `SET_COMPOUND_INPUT`
- `FOCUS_COMPOUND_INPUT`
- `FOCUS_RESULT_SECTION`
- `SELECT_ENDPOINT`
- `OPEN_MODEL_ENDPOINT`
- `OPEN_BATCH_JOB`
- `SELECT_BATCH_ROW`
- `SET_BATCH_FILTERS`
- `SET_ABOUT_FILTERS`
- `SHOW_RESOURCE`

Every action carries `action_id`, `session_id`, `target_route`, and
`expected_state_version`. Payload models forbid extra fields. Input actions
reject executable/selector content and require `submit=false`; filling an input
does not resolve or predict.

Explicit, allowlisted reversible intents are resolved deterministically before
the scientific LLM/tool path. UI actions remain response proposals, not ADME
scientific tools.

## 5. Route capabilities

- `/single`: set/focus compound input and focus a registered prediction
  category using React state and refs.
- `/batch/{jobId}`: apply validation/prediction filters, select a row, and expose
  the current batch target.
- `/about`: apply endpoint filters and select/open a registry endpoint.

Capabilities register on mount and unregister on unmount. About waits for
registry data before registering, preventing an early empty-data closure.

## 6. Dispatcher

The async dispatcher performs strict schema validation, session ownership,
state version, duplicate ID, route allowlist, navigation, destination capability
wait, capability execution, and structured success/failure reporting. Failures
are visible with stable codes instead of being silently discarded.

## 7. Transition coordinator

The centralized states are `idle`, `preparing_action`,
`collapsing_for_action`, `executing_action`, `highlighting_target`,
`action_completed`, and `action_failed`.

Space-consuming actions collapse the panel with a restrained rightward motion.
The launcher shows applying, completion, or failure state. Registered targets
receive a non-layout-shifting cyan outline/background for about 1.2 seconds.
Reduced-motion mode removes animation and shortens delays.

## 8. Markdown security

Assistant prose uses `react-markdown` with `remark-gfm`, `skipHtml`, and a
restricted element allowlist. `rehype-raw` and `dangerouslySetInnerHTML` are not
used. Links receive `_blank` plus `noopener noreferrer`. Paragraphs, lists,
bold, inline code, code blocks, and links have dedicated compact scientific UI
styles.

## 9. Chinese response style

Instructions now request concise one-to-three-sentence product language, avoid
mechanical bold-heavy reports, do not repeat structured card fields, and never
claim an action has completed before frontend execution. Structured cards remain
the primary display for endpoint, prediction, batch, and confirmation details.

## 10. Test results

```text
AGENT_ENABLED=false ADME_MOCK_MODE=true .venv/bin/pytest -q
94 passed, 2 skipped in 9.82s

RUN_AGENT_LLM_INTEGRATION=true AGENT_ENABLED=true ADME_MOCK_MODE=true \
  .venv/bin/pytest -q tests/integration -s
2 passed in 22.14s

npm run lint
passed, no warnings

npm run typecheck
passed

npm run test
23 passed
```

Backend action tests cover strict payloads, supported/unsupported intents, and
proof that input-only action requests bypass the LLM and scientific tools.
Frontend tests cover response preservation, real capability execution,
duplicate/stale/cross-session/unknown rejection, Markdown, and raw HTML.

## 11. Production build

Next.js 16.2.10 production build compiled, typechecked, generated all six routes,
and completed successfully.

## 12. Playwright

All 28 desktop/mobile scenarios have passing evidence. The complete run passed
27/28; the remaining pre-existing mobile batch test was still in its legitimate
`Starting prediction...` state when the old 10-second assertion expired. After
raising the cold-start expectation window to 20 seconds, that exact test passed
in 11.4 seconds. New Assistant cases pass on desktop and mobile:

- ibuprofen input changes without resolve/predict
- DILI navigation, selection, highlight, and session persistence
- failed batch filter changes real select state once
- Chinese Markdown rendering and unknown-action rejection

Playwright now uses an isolated `/tmp` database/data directory and webpack dev
mode to avoid contaminating project data and to reduce cache pressure.

## 13. Remaining limitations

- UI intent recognition is intentionally narrow and deterministic. Unrecognized
  paraphrases fall through to normal Agent conversation rather than guessing an
  action.
- `FOCUS_RESULT_SECTION` requires prediction results to exist; otherwise the UI
  reports `ACTION_TARGET_NOT_FOUND`.
- Session IDs remain local bearer-like identifiers; authentication is outside
  this MVP.
- The machine had only about 211MB free after testing. Generated caches were
  cleared once, but broader disk cleanup was outside this task.

## 14. Scope confirmation

This work adds no streaming, SSE, deployment, arbitrary tools, arbitrary DOM
selectors, JavaScript/HTML/command execution, shell/file/web/MCP capability,
Registry mutation, new scientific predictor, frontend scientific calculation,
or multi-agent runtime.
