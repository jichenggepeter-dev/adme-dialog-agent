# Backend Agent API

All routes live under `/agent`. The primary browser chat path is a versioned
NDJSON response stream; the non-streaming chat response remains available.
Errors use the existing stable envelope:

```json
{"error":{"code":"AGENT_DISABLED","message":"The conversational Agent is disabled.","details":null}}
```

## Create Session

```http
POST /agent/sessions
```

Returns `session_id`, status, timestamps, and `state_version`.

## Get Session

```http
GET /agent/sessions/{session_id}
```

An expired session returns `SESSION_EXPIRED`; an unknown ID returns `SESSION_NOT_FOUND`.

## Message History

```http
GET /agent/sessions/{session_id}/messages?limit=50&offset=0
```

Pagination is bounded to 100 messages per request.

## Chat

```http
POST /agent/chat
```

```json
{
  "session_id": "session_...",
  "message": "Predict aspirin",
  "expected_state_version": 0,
  "page_context": {"page":"single","compound_id":null,"prediction_id":null,"selected_endpoint":null}
}
```

`page_context` is a strict discriminated union for `single`, `batch`, or `about`. Arbitrary DOM and free-form page state are rejected.

The response contains:

- `text`
- `structured_payloads`
- `pending_confirmation`
- `tool_activity`
- `ui_action_proposals`
- `warnings`
- `state_version`

A prediction request first returns a compound confirmation. It does not predict in that unconfirmed flow.

## Stream Chat

```http
POST /agent/chat/stream
Content-Type: application/json
Accept: application/x-ndjson
```

The request body matches `POST /agent/chat`. Each newline-delimited event has
`version`, `session_id`, `message_id`, `correlation_id`, an increasing
`sequence`, `occurred_at`, and a discriminating `type`:

- `heartbeat`
- `tool_started`
- `tool_completed`
- `message_delta`
- `confirmation_required`
- `response_completed`
- `error`

The response uses `Cache-Control: no-store` and disables proxy buffering.
Clients reject unknown events, identity changes, sequence gaps, duplicate
terminal events, and content after a terminal event. Cancellation does not
automatically retry a tool or confirmation.

## Confirm

```http
POST /agent/confirm
```

```json
{
  "session_id":"session_...",
  "confirmation_id":"confirm_...",
  "decision":"approve",
  "expected_state_version":1
}
```

Approval validates ownership, expiry, payload hash, canonical SMILES, and state
version before prediction. Rejection performs no prediction. Replay returns
`CONFIRMATION_REPLAYED`.

## Session Export

```http
POST /agent/sessions/{session_id}/exports
POST /agent/sessions/{session_id}/exports/{action_id}
```

The first route prepares a state- and snapshot-bound JSON or Markdown export.
The second explicitly approves or rejects it. Responses use
`Cache-Control: no-store, max-age=0`; approval returns the in-memory download
content and records only a redacted success summary. See
[the export contract](../session-export.md).

## Session Deletion

```http
POST /agent/sessions/{session_id}/deletions
POST /agent/sessions/{session_id}/deletions/{action_id}
```

The first route returns exact deletion counts and retained categories. The
second explicitly approves or rejects the irreversible action. Approval is
atomic, session-owned, snapshot-bound, and idempotent for the exact action. See
[the deletion contract](../session-deletion.md).

## Resource

```http
GET /agent/resources/{resource_id}?session_id=session_...
```

Resources are session-owned, hash-verified JSON with a 256 KB limit and TTL. This is not a file API and cannot read arbitrary paths.

## Stable Errors

Implemented errors include `AGENT_DISABLED`, `AGENT_NOT_CONFIGURED`,
`AGENT_PROVIDER_UNAVAILABLE`, `AGENT_TIMEOUT`, `SESSION_NOT_FOUND`,
`SESSION_EXPIRED`, `CONFIRMATION_REQUIRED`, `CONFIRMATION_EXPIRED`,
`CONFIRMATION_REPLAYED`, `ACTION_NOT_ALLOWED`, `ACTION_STALE`, `DELETE_STALE`,
`EXPORT_STALE`, `EXPORT_LIMIT_EXCEEDED`, `RESOURCE_NOT_FOUND`,
`RESOURCE_TOO_LARGE`, `TOOL_FAILED`, `TOOL_RESULT_INVALID`, and
`SCIENTIFIC_POLICY_VIOLATION`.
