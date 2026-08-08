# Frontend Assistant Contract

Updated: 2026-08-08

## Ownership

The backend owns sessions, messages, business state, confirmation state,
resources, and scientific results. The frontend owns panel presentation, draft
text, request state, the in-memory opaque session ID, and compact current-route
context. A page reload creates a new session; the frontend does not persist the
session capability in browser storage.

## API and streaming

- `POST /agent/sessions`
- `GET /agent/sessions/{session_id}`
- `GET /agent/sessions/{session_id}/messages`
- `POST /agent/chat/stream`
- `POST /agent/chat`
- `POST /agent/confirm`
- `POST /agent/actions/decide`
- `POST /agent/sessions/{session_id}/exports`
- `POST /agent/sessions/{session_id}/exports/{action_id}`
- `POST /agent/sessions/{session_id}/deletions`
- `POST /agent/sessions/{session_id}/deletions/{action_id}`
- `GET /agent/confirmations/{confirmation_id}?session_id=...`
- `GET /agent/resources/{resource_id}?session_id=...`

The browser uses version-1 `application/x-ndjson` streaming for normal chat and
retains the non-streaming contract. Every response or event is runtime-validated
with strict Zod schemas. Unknown top-level fields and invalid stream identity or
ordering are rejected. The client sends a correlation ID and uses an
AbortController. Confirmations and side-effecting actions are never
automatically retried.

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

Session export and deletion have their own user-opened confirmation dialogs.
The model cannot call them as tools. Export returns a download only after
approval. Successful deletion aborts the current stream, increments a local
session-generation barrier, clears all current state, and creates a fresh empty
session; late events from the deleted generation are ignored.

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
