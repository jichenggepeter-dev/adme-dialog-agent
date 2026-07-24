# UI Action and Message Rendering Audit

Date: 2026-07-12

## Decision

The reported behavior is reproduced by the implementation. The backend never
emits a UI action in a normal Agent response, and the frontend has no mounted
route capabilities that could execute one. Message Markdown is rendered as
plain text.

## Current data flow

```text
User message
  -> POST /agent/chat
  -> AgentRuntime.chat
  -> OpenAI Agents SDK returns final_output text
  -> backend hardcodes ui_action_proposals=[]
  -> strict frontend API schema preserves the empty array
  -> AssistantProvider iterates the empty array
  -> dispatcher is never called
  -> no route capability exists
  -> page React state does not change
```

## Root causes and evidence

### 1. Backend actions are always empty

- `app/agent_runtime/runtime.py:83-94` creates a text-output Agent with the 11
  scientific tools only. There is no typed response model or UI-action output
  channel.
- `app/agent_runtime/runtime.py:136` converts `result.final_output` directly to
  a string.
- `app/agent_runtime/runtime.py:166-174` hardcodes
  `"ui_action_proposals": []`.
- `app/agent_runtime/instructions.py:4-29` contains scientific safety and tool
  rules but no instruction to emit supported reversible page actions.

Therefore the model can only describe an action in prose. Its statement that it
cannot operate the interface follows from the absence of an action output
contract, not from a frontend schema loss.

### 2. The backend action contract is incomplete and inconsistent

- `app/agent_runtime/contracts.py:79-88` has an uppercase action union, but uses
  obsolete names such as `POPULATE_SINGLE_INPUT`, `SELECT_COMPOUND`, and
  `SET_BATCH_FILTER`.
- It lacks `session_id`, `SET_COMPOUND_INPUT`, `FOCUS_COMPOUND_INPUT`,
  `SELECT_BATCH_ROW`, `SET_BATCH_FILTERS`, `SET_ABOUT_FILTERS`, and
  `SHOW_RESOURCE`.
- Its payload is an unrestricted flat primitive dictionary rather than a
  discriminated, action-specific payload schema. It cannot enforce that
  `submit` defaults to false or reject unexpected selector/HTML/command fields.

### 3. The frontend preserves actions but validates them too loosely

- `frontend/lib/agent-api.ts:20-22,33` validates and returns the full Agent
  response; it does not drop `ui_action_proposals`.
- `frontend/lib/agent-schemas.ts:7` preserves the array, but validates `type` as
  any string and `payload` as any primitive record. This does not mirror the
  backend discriminated union.
- `frontend/contexts/assistant-provider.tsx:36-40` reads and attempts to
  dispatch actions.

### 4. Dispatcher validation is partial and execution is mostly a no-op

- `frontend/lib/ui-action-dispatcher.ts:3-10` checks only action ID, state
  version, and two string allowlists. It does not validate session ownership,
  route compatibility, duplicate IDs, or payload shape.
- `frontend/lib/ui-action-dispatcher.ts:13-17` handles navigation directly,
  uses a forbidden generic `document.querySelector` for focus, and sends a
  global `CustomEvent` for every other action.
- No component listens for `adme-assistant-action`, so those actions report
  success without changing state.
- Rejected actions are silently ignored by
  `frontend/contexts/assistant-provider.tsx:39`; users receive no execution
  failure.

### 5. No route capability registry exists

- `frontend/components/single-molecule-workspace.tsx:14-23` owns the compound
  input and prediction state, but exposes no capability registration.
- `frontend/components/model-information-workspace.tsx:20-26` owns endpoint
  search, filters, and selected endpoint, but exposes no capability.
- `frontend/components/batch-job-workspace.tsx:20-25` owns row/filter state, but
  exposes no capability.
- Inputs and target sections do not expose controlled refs or target IDs for
  focus, scroll, and highlight.
- Consequently navigation cannot wait for the destination page to mount before
  applying an action, and stale closures cannot be unregistered.

### 6. Raw Markdown is rendered as text

- `frontend/components/assistant/assistant-panel.tsx:15` renders every message
  as `<p>{message.content}</p>`.
- No Markdown renderer is installed or used. Therefore `**DILI 模型信息**` is
  displayed literally.
- Assistant prose and structured cards are both rendered, so endpoint fields
  may be duplicated in long model-generated lists and cards.
- Existing CSS gives the paragraph a compact 1.45 inherited line height, with
  no Chinese-specific paragraph/list rhythm.

## Where the action chain breaks

The first break is the backend hardcoded empty array. Two additional breaks
would remain after fixing it: action-specific runtime validation is absent, and
the frontend dispatcher has no route capability to call. All three layers must
be fixed together.

## Repair design

1. Add strict action-specific Pydantic models with session, route, version, and
   payload validation. `SET_COMPOUND_INPUT.submit` defaults to false.
2. Add deterministic UI-intent resolution for the supported reversible
   commands before the scientific LLM/tool path. UI actions remain response
   proposals, not scientific tools. Unsupported requests continue to the Agent.
3. Update Agent instructions so supported page actions are proposed rather than
   merely described, while never claiming completion before frontend execution.
4. Mirror the discriminated union in Zod and TypeScript.
5. Add a lifecycle-safe route capability registry. Each page registers real
   React setters and element refs, then unregisters on unmount.
6. Replace the dispatcher with async execution: strict validation, session and
   version checks, duplicate rejection, optional navigation, capability wait,
   execution, and a structured result.
7. Add one transition coordinator for collapse, execution, target highlight,
   launcher progress/completion/failure, and reduced motion.
8. Render Assistant prose through `react-markdown` with GFM, no raw HTML plugin,
   a restricted element set, and safe links. Prefer structured cards and keep
   prose concise through instructions.

## Required tests

- Backend typed action generation, non-submitting input, unsupported intent,
  strict payload rejection, and non-completion wording.
- Frontend schema preservation, malformed/stale/duplicate/session/route
  rejection, route wait, real capability execution, visible failure, transition
  states, target highlighting, and reduced motion.
- Markdown bold/list/paragraph rendering, raw HTML non-execution, and structured
  card rendering.
- Playwright: ibuprofen input without resolve/predict; DILI navigation and
  selection; failed batch filter; Chinese Markdown; unknown action rejection.

## Scope boundaries

The repair does not add streaming, deployment, arbitrary DOM selectors,
JavaScript/HTML/command execution, scientific tools, Registry mutation,
multi-agent behavior, shell/file/web/MCP access, or frontend scientific
interpretation.
