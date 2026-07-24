# Backend Agent API

All routes are non-streaming and live under `/agent`. Errors use the existing stable envelope:

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

Approval validates ownership, expiry, payload hash, canonical SMILES, and state version before prediction. Rejection performs no prediction. Replay returns `CONFIRMATION_REPLAYED`.

## Resource

```http
GET /agent/resources/{resource_id}?session_id=session_...
```

Resources are session-owned, hash-verified JSON with a 256 KB limit and TTL. This is not a file API and cannot read arbitrary paths.

## Stable Errors

Implemented errors include `AGENT_DISABLED`, `AGENT_NOT_CONFIGURED`, `AGENT_PROVIDER_UNAVAILABLE`, `AGENT_TIMEOUT`, `SESSION_NOT_FOUND`, `SESSION_EXPIRED`, `CONFIRMATION_REQUIRED`, `CONFIRMATION_EXPIRED`, `CONFIRMATION_REPLAYED`, `ACTION_NOT_ALLOWED`, `ACTION_STALE`, `RESOURCE_NOT_FOUND`, `RESOURCE_TOO_LARGE`, `TOOL_FAILED`, `TOOL_RESULT_INVALID`, and `SCIENTIFIC_POLICY_VIOLATION`.
