# ADME Discovery Workspace — Frontend Assistant Implementation Plan

## Entry Gate

Frontend work begins only after the backend review-and-fix round confirms:

- No prediction path bypasses mandatory structure confirmation
- Confirmation transitions are atomic and replay-safe
- Cross-session access is blocked
- Tool and turn limits are enforceable
- Agent-disabled mode is isolated
- Error envelopes are stable
- Structured scientific outputs are safe for rendering

The frontend must not compensate for backend security or scientific-policy gaps.

## Goal

Add a global right-side **ADME Assistant** to `/single`, `/batch`, and `/about`.

The reference image establishes the desktop design direction:

- Integrated right-side scientific copilot panel
- Cool white / pale gray background
- Deep navy and teal accents
- Thin borders and controlled shadows
- Medium information density
- Structured cards over generic chat bubbles
- Compact tool activity
- Scientific metadata visible beside values
- Persistent composer at panel bottom

## Scope

Included:

- Root Assistant provider
- Cross-route session persistence
- Floating launcher and side panel
- Message composer and history
- Tool activity
- Structured cards
- Confirmation cards
- Page-context adapters
- UI Action dispatcher
- Error/offline states
- Accessibility and responsive behavior
- Unit, Playwright, and visual tests
- Non-streaming backend integration

Excluded:

- SSE streaming
- Multi-Agent
- Authentication/accounts
- Deployment
- Arbitrary DOM control
- Frontend scientific calculations
- Shell/file/web/MCP capabilities

## Architecture

Recommended structure:

```text
frontend/
├── components/assistant/
│   ├── assistant-launcher.tsx
│   ├── assistant-panel.tsx
│   ├── assistant-header.tsx
│   ├── assistant-context-bar.tsx
│   ├── assistant-message-list.tsx
│   ├── assistant-composer.tsx
│   ├── tool-activity.tsx
│   └── cards/
├── contexts/
│   ├── assistant-provider.tsx
│   └── assistant-page-context.tsx
├── hooks/
│   ├── use-assistant.ts
│   └── use-agent-session.ts
└── lib/
    ├── agent-api.ts
    ├── agent-types.ts
    ├── agent-schemas.ts
    └── ui-action-dispatcher.ts
```

## State Ownership

Frontend owns:

- Panel open/closed
- Draft input
- Request/loading state
- Temporary UI errors
- Current route context registration

Backend owns:

- Session
- Message history
- Business state
- Confirmed compounds
- Pending confirmations
- Prediction resources
- Batch resources
- State version

Persist locally only the opaque session ID and optional panel state. Do not store API keys, raw resources, tool payloads, or authoritative business state.

## API Integration

Use:

```http
POST /agent/sessions
GET  /agent/sessions/{session_id}
GET  /agent/sessions/{session_id}/messages
POST /agent/chat
POST /agent/confirm
GET  /agent/resources/{resource_id}?session_id=...
```

Centralize fetch, timeout, AbortController, error parsing, and correlation IDs in `frontend/lib/agent-api.ts`. Never automatically retry confirmations or side-effect requests.

## Page Context

`/single`:

- current phase
- compound reference
- prediction resource ID
- selected endpoint/category
- state version

`/batch`:

- job ID
- validation status
- selected row/compound IDs
- active endpoints and filters
- preview compound

`/about`:

- selected endpoint
- category
- output type filter
- metadata status filter

Do not send all batch rows or inspect the DOM.

## Structured Payload Cards

Implement:

- Compound Confirmation
- Prediction Summary
- Endpoint Explanation
- Batch Summary
- Batch Errors
- Comparison
- Model Information
- Resource Card

Scientific rules:

- Mock mode must be explicit
- Unknown metadata remains neutral
- Do not convert numerical values into probabilities
- Do not rank or select a winner
- Preserve warnings and provenance
- Use tabular numerals
- Use monospace for SMILES

## Tool Activity

Show only sanitized statuses:

- Resolving compound
- Checking structure
- Loading endpoint metadata
- Reading batch status
- Running prediction

Never show chain of thought, raw JSON, provider internals, or full tool arguments.

## Confirmation UX

Structure confirmation must show:

- 2D structure
- Name
- PubChem CID
- Formula
- Molecular weight
- Canonical SMILES
- Input-quality warnings
- Confirm Structure / Change Input / Cancel

The confirm request must send only backend-issued identifiers, decision, and expected state version. The client must never substitute a new SMILES during confirmation.

## UI Action Dispatcher

Allowlisted reversible actions:

- `NAVIGATE`
- `SELECT_ENDPOINT`
- `SET_ABOUT_FILTERS`
- `SELECT_BATCH_ROW`
- `SET_BATCH_FILTERS`
- `FOCUS_COMPOUND_INPUT`
- `SHOW_RESOURCE`

Confirmation-required proposals:

- `RUN_SINGLE_PREDICTION`
- `RUN_BATCH_JOB`
- `CANCEL_BATCH_JOB`
- `EXPORT_RESULTS`
- `REPLACE_UPLOAD`
- `CLEAR_SESSION`

Reject unknown, malformed, stale, duplicate, cross-session, and route-incompatible actions. Never evaluate generated JavaScript, selectors, HTML, or commands.

## Milestones

1. Backend contract freeze and representative fixtures
2. TypeScript types, runtime schemas, and API client
3. Root provider, launcher, and panel shell
4. Message history, composer, errors, and tool activity
5. Structured payload cards
6. Route context adapters
7. UI Action dispatcher
8. Confirmation flows
9. Accessibility and responsive behavior
10. Unit, Playwright, build, and visual validation

## Acceptance

Frontend is complete only when:

- It visually matches the existing workspace and reference design
- Session persists across routes
- Page context is typed and compact
- Non-streaming Agent chat works
- Confirmation cannot be fabricated client-side
- Structured payloads render correctly
- Mock/real modes are visibly distinct
- Unknown metadata stays neutral
- UI actions are allowlisted
- Error envelopes render consistently
- Accessibility passes
- Desktop/tablet/mobile layouts work
- Lint, typecheck, tests, build, and Playwright pass
- No streaming, deployment, arbitrary tools, or multi-agent work is added
