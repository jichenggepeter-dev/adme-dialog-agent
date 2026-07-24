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
