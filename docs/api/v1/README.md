# API contract v1

This is the current public contract for the local FastAPI backend. It describes
what another program may send and receive; it is separate from the application
release number shown by `GET /status`.

| Contract | Current version | Where a client sees it |
| --- | --- | --- |
| REST requests and responses | `1.0` | `/openapi.json` → `info.version` and this directory |
| Agent stream events | `1` | Each NDJSON event's `version` field |
| Agent errors | `1` | The v1 error envelope below |
| Confirmation flows | `1` | The v1 request and response schemas below |
| Evidence answer and source card | `1` | The examples and schemas in this directory |
| Session export document | `1.0` | `export_schema_version` in the export document |

The v1 routes keep their existing unprefixed paths for compatibility. The
contract version is published through OpenAPI instead of being repeated in
every URL. Run the backend and open `http://127.0.0.1:8000/docs` for the
interactive request and response schemas.

The machine-readable [contract manifest](contract.json) records every public
method and path. A test compares it with the application OpenAPI document, so a
route cannot be added or removed silently.

## Route catalog

| Area | Routes | Request and success response |
| --- | --- | --- |
| Service | `GET /health`, `GET /status` | No body; health or runtime status object |
| Compound | `POST /compound/resolve` | `CompoundResolveRequest` → `CompoundResponse` |
| Endpoints | `GET /endpoints`, `/endpoints/coverage`, `/endpoints/{raw_key}` | No body; registry, coverage, or endpoint metadata object |
| Prediction | `POST /predict`, `POST /predict/batch` | `PredictRequest` or `BatchPredictRequest` → prediction result object |
| Legacy chat | `POST /chat` | `ChatRequest` → `ChatResponse` |
| Batch upload | `GET /batch/capabilities`, `POST /batch/upload` | No body or multipart file → capabilities or upload summary |
| Batch jobs | `POST /batch/jobs`, `GET /batch/jobs/{job_id}`, `GET /batch/jobs/{job_id}/results` | `BatchJobCreateRequest` or no body → job state and results |
| Batch actions | `POST /batch/jobs/{job_id}/run`, `/cancel` | No body → updated job state |
| Batch export | `GET /batch/jobs/{job_id}/export`, `/errors`, `POST /batch/jobs/{job_id}/export/filtered` | Query or `BatchFilteredExportRequest` → downloadable content |
| Agent session | `POST /agent/sessions`, `GET /agent/sessions/{session_id}`, `/messages` | No body; session or paginated message contract |
| Agent chat | `POST /agent/chat`, `/chat/stream` | `AgentChatRequest` → `AgentChatResponse` or v1 NDJSON events |
| Agent decision | `POST /agent/confirm`, `/agent/actions/decide` | v1 decision request → `AgentChatResponse` |
| Agent status | `GET /agent/actions/{action_id}`, `/agent/confirmations/{confirmation_id}` | Query includes `session_id`; returns current decision record |
| Agent resource | `GET /agent/resources/{resource_id}` | Query includes `session_id`; returns hash-verified resource data |
| Session export | `POST /agent/sessions/{session_id}/exports`, then `/{action_id}` | Prepare or decision request → proposal or result |
| Session deletion | `POST /agent/sessions/{session_id}/deletions`, then `/{action_id}` | Prepare or decision request → proposal or deletion receipt |

OpenAPI is the field-level reference for every model named above. Existing
specialized documents remain useful explanations: [Backend Agent API](../../agent/backend-api.md),
[batch file format](../../batch-file-format.md), and [session export](../../session-export.md).

## Agent chat example

Send [the example request](examples/agent-chat-request.json) to
`POST /agent/chat`. A successful non-streaming reply follows
[this response contract](examples/agent-chat-response.json). `page_context` is
a strict `single`, `batch`, or `about` object; arbitrary browser state is not
accepted.

## Streaming example

`POST /agent/chat/stream` accepts the same request and returns
`application/x-ndjson`. [The successful example stream](examples/stream-events.ndjson)
shows heartbeat, tool, text, confirmation, and completion events. The
[error example](examples/stream-error-events.ndjson) shows the alternate
terminal path. Each file contains one JSON object per line. Every event carries
the same session, message, and correlation identity, an increasing sequence,
and `version: 1`. The final event is exactly one `response_completed` or
`error` event.

Clients should reject an unknown event version rather than guessing. New event
types require at least a REST v1 minor contract update; incompatible event
shapes require a new stream-event version.

## Confirmation flow

Consequential actions are two-step operations:

1. A chat or prepare route returns a pending confirmation or action with its
   identifiers and `expected_state_version`. Nothing consequential has run yet.
2. The user chooses approve or reject.
3. The client sends the matching decision, such as the
   [compound confirmation example](examples/confirmation-request.json).
4. The backend verifies session ownership, expiry, payload identity, replay,
   and state version before executing or rejecting the action.

Clients must not create a new payload during approval. A stale, expired, or
replayed decision returns a stable error instead of silently executing.
Compound prediction uses `/agent/confirm`; general pending actions use
`/agent/actions/decide`; export and deletion use their own decision routes.

## Errors

Agent and validation errors use the v1 envelope shown in
[the error example](examples/error-response.json):

```text
error.code            stable machine-readable code
error.message         safe message for a person
error.details         optional bounded detail
error.retryable       whether retrying unchanged input can help
error.correlation_id  identifier for diagnostics
```

Some older non-Agent endpoints return the same `error` object without
`retryable` and `correlation_id`. Those fields are optional for REST v1 clients
outside `/agent`; they are required for Agent and request-validation errors.
Provider bodies, credentials, prompts, and tracebacks are never public error
fields.

## Evidence answer and source card

[The evidence-answer example](examples/evidence-answer.json) shows a supported
answer. Each claim contains the source cards that support that specific claim.
The flat `evidence` list supports source-card display and does not replace the
claim-level relationship.

[The source-card example](examples/source-card.json) includes source identity,
canonical URL, document lifecycle status, capture date, exact section or page,
stable chunk ID, and reviewable excerpt. Clients must display `superseded` or
`draft` status and must not convert retrieval into a clinical, safety,
regulatory, dosing, or compound-ranking conclusion.

Evidence status is one of `supported`, `partial`, `conflicting`, `no_evidence`,
`prohibited`, or `stale_only`. Availability separately reports whether the
approved local index could be read.

## Change and migration rules

Read the [API change, deprecation, and migration policy](../versioning-and-migrations.md)
before changing a route or schema. Documentation-only corrections do not change
the contract version. Additive fields or routes increment the minor contract;
incompatible changes require a new major contract and a migration guide.
