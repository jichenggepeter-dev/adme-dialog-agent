# Frontend Assistant Contract

Date: 2026-07-12

## Ownership

The backend owns sessions, messages, business state, confirmation state,
resources, and scientific results. The frontend owns panel presentation, draft
text, request state, and compact current-route context. Only the opaque session
ID is persisted in `localStorage`.

## Non-streaming API

- `POST /agent/sessions`
- `GET /agent/sessions/{session_id}`
- `GET /agent/sessions/{session_id}/messages`
- `POST /agent/chat`
- `POST /agent/confirm`
- `GET /agent/confirmations/{confirmation_id}?session_id=...`
- `GET /agent/resources/{resource_id}?session_id=...`

All browser responses are runtime-validated with strict Zod schemas. Unknown
top-level fields are rejected. The client sends a correlation ID and uses an
AbortController timeout. Confirmations are never automatically retried.

## Session and page context

The provider is mounted in the root layout and survives navigation among
`/single`, `/batch`, and `/about`. It sends only typed route context; it does not
inspect the DOM or send batch rows.

## Confirmation

The client renders only backend-issued confirmation data. Approval sends:

```json
{
  "session_id": "session_...",
  "confirmation_id": "confirm_...",
  "decision": "approve",
  "expected_state_version": 1
}
```

No SMILES or replacement payload is accepted in the confirmation request. On a
timeout, the client may query confirmation status before any user-directed
retry.

## Structured payloads

Supported renderers: compound confirmation, prediction, endpoint explanation,
batch summary, batch errors, comparison, model information, resource,
out-of-scope, and error. Mock mode is labeled explicitly. The UI does not infer
probabilities, units, positive classes, directionality, rankings, or winners.

## UI actions

Reversible actions are allowlisted and dispatched as typed events or route
navigation. Side-effecting actions are classified as confirmation-required and
are not automatically executed. Unknown, malformed, duplicate, stale, and
route-incompatible actions are rejected. No JavaScript, selector, HTML, shell,
file, web, or MCP execution exists.

## Error envelope

Agent errors contain `code`, `message`, `details`, `retryable`, and
`correlation_id`. The UI never renders provider response bodies, prompts,
credentials, tracebacks, chain of thought, or raw tool arguments.

## Activity and evidence trace

Each streamed assistant message may expose a collapsed, user-facing activity
trace. It is a bounded projection of the validated stream, not an audit-log
viewer and not a reasoning transcript.

- The first heartbeat is labeled **Response stream active**. Later heartbeats
  are ignored by the projection.
- Tool entries show the allowlisted tool label, lifecycle status, UTC event
  time, monotonic duration, and a bounded error code when present.
- Evidence entries reuse the existing bounded citation title and URL. Only
  HTTP(S) URLs without embedded credentials are interactive.
- Confirmation and error entries copy no action payload, arguments, exception
  message, user message, prompt, provider body, or resource contents.
- The final response replaces its streamed placeholder only when the session
  and message identity match. The stream parser separately enforces session,
  message, correlation, sequence, and terminal-event integrity.
- At most 40 projected entries are retained per assistant message.

The disclosure uses native `details`, `summary`, `ol`, `time`, links, and
buttons. Status is written as text. A recovery button only returns keyboard
focus to the message box; it never retries, submits, confirms, or invokes a
tool automatically.
