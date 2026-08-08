# Safety and Audit

## Scientific Boundaries

- Predictions are computational outputs, not measurements.
- No clinical, patient, dose, treatment, regulatory, or definitive safety conclusion.
- No invented ADME value, unit, threshold, positive class, directionality, source, or model version.
- Unknown/unverified Endpoint Registry metadata remains explicit.
- Mock mode is labeled as deterministic test data, not ADMET-AI output.
- Comparison is neutral and never ranks a best compound.

## Layered Enforcement

1. Input capability policy blocks clinical requests, arbitrary execution/file access, Registry mutation, and instruction-override attacks before the provider.
2. The SDK receives exactly eleven strict allowlisted tools and no hosted/arbitrary tools.
3. Tool services enforce session ownership, state version, confirmation, canonical SMILES, resource limits, and comparison cardinality.
4. Agent instructions prohibit confirmation bypass and scientific fabrication.
5. Output policy blocks explicit prohibited clinical/scientific claims before persistence.

This is not a single string blacklist: authorization and scientific facts are enforced by typed contracts, deterministic services, business state, confirmation records, and tool allowlisting.

## Hosted and Local Tracing

- OpenAI-hosted Agents SDK tracing: OFF.
- Sensitive SDK trace inclusion: OFF.
- Application-owned SQLite audit logging: ON.

Local audit events may record correlation ID, model, tool name, duration, stable status/error code, counts, hashes, and resource IDs.

They do not record API keys, Authorization headers, full prompts, raw provider responses, full tool payloads, arbitrary file content, or complete batch data. SMILES, queries, and messages in audit summaries are hashed rather than stored verbatim.

Conversation messages are intentionally stored as product history and are separate from operational audit logs.

## User-facing Activity Trace

The Assistant activity trace is also separate from operational audit logs. It
is created in memory from an exact frontend allowlist and is bounded to 40
entries per assistant message. It may contain an opaque correlation ID,
allowlisted tool name, stable status or error code, UTC event time, monotonic
duration, and an already-approved evidence source title and HTTP(S) URL.

It does not expose the SQLite audit table, chain of thought, full prompts, user
messages, tool arguments, confirmation payloads, raw provider responses,
resource contents, Batch rows, API keys, Authorization headers, or tracebacks.
The trace has no control that can run a tool or bypass confirmation. Its error
recovery control only focuses the existing message box.
