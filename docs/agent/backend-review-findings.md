# Backend Agent Core Review Findings

Date: 2026-07-12

Scope: the implemented FastAPI Agent core, persistence layer, tool wrappers,
guardrails, contracts, and existing tests. This is a pre-fix review; line
references describe the implementation at review time.

## Gate decision

**Stage A does not pass. Frontend Assistant implementation must not begin yet.**

The core architecture correctly isolates the Agent runtime from the existing
Single, Batch, About, resolver, RDKit, and ADMET-AI services. However, the
confirmation lifecycle, session isolation, scientific-output validation, and
tool-loop controls do not yet meet the product and safety contracts.

## Findings

### [P0] Confirmation approval is not an atomic, recoverable execution claim

- Evidence: `app/agent_runtime/runtime.py:206-223` updates business state,
  transitions the confirmation to `executing`, runs prediction, and records the
  final status in separate transactions.
- Evidence: `app/agent_runtime/repositories.py:351-405` performs a read/check/
  update sequence and the final update is keyed only by `confirmation_id`.
- Evidence: `app/agent_runtime/repositories.py:69-80` stores neither a row
  version nor a result resource/error reference.
- Impact: a crash between transactions can leave an approved/executing action
  with no recoverable outcome. Concurrent or retried requests are serialized by
  SQLite but are not claimed by a conditional update whose `rowcount == 1`.
- Required fix: add a schema migration, atomic approve-and-claim operation using
  session, status, version, expiry, payload integrity, and state version in the
  transaction; persist terminal resource/error information; expose a
  session-scoped confirmation status endpoint for timeout recovery.

### [P0] Session ownership and expiry are not enforced in SQL for all resources

- Evidence: confirmation lookup selects by ID only and checks session ownership
  in Python (`app/agent_runtime/repositories.py:333-349`).
- Evidence: pending actions follow the same pattern
  (`app/agent_runtime/repositories.py:474-483`).
- Evidence: resources select by ID only, check ownership in Python, and do not
  require the owning session to remain active and unexpired
  (`app/agent_runtime/repositories.py:523-536`).
- Impact: current behavior is fail-closed in normal paths, but the persistence
  boundary does not guarantee tenant/session isolation and an expired session
  can still retrieve an otherwise unexpired resource.
- Required fix: scope reads and state transitions by both resource/action ID and
  session ID in SQL, join active session state where appropriate, and add
  cross-session and expired-session tests.

### [P0] Scientific output guardrail cannot validate claims against tool facts

- Evidence: `app/agent_runtime/guardrails.py:52-70` checks only six fixed text
  phrases and accepts no structured tool payload.
- Impact: the model can invent a probability, unit, positive-class meaning,
  directionality, provenance, or call a mock result real without triggering the
  guardrail. Claims such as safer/better rankings or experimental measurements
  are also insufficiently covered.
- Required fix: validate generated text against sanitized structured facts
  (`output_type`, unit verification, metadata status, probability and
  directionality support, prediction mode), then replace unsafe output with a
  deterministic cautious response or a stable policy error.

### [P1] Tool-call limits do not detect repeated or alternating loops

- Evidence: `app/agent_runtime/tool_service.py:406-453` counts only activity
  entries, appends another entry after the limit, and does not fingerprint calls.
- Impact: identical tool calls or alternating-tool loops can consume turns and
  repeatedly invoke services. Limit failures use the generic
  `ACTION_NOT_ALLOWED` code and are not a stable loop contract.
- Required fix: canonical call fingerprints, duplicate and alternating-loop
  detection, a hard blocked state, and stable `AGENT_TOOL_LIMIT` /
  `AGENT_TOOL_LOOP` errors. Test malformed, unknown, extra, oversized, and
  repeated calls.

### [P1] Agent API errors lack retry and correlation semantics

- Evidence: `app/agent_runtime/contracts.py:193-200` and
  `app/main.py:36-40,71-74` return only code, message, and details.
- Evidence: `app/agent_runtime/errors.py:4-8` has no retryability metadata.
- Impact: the frontend cannot safely distinguish retryable provider/timeouts
  from stale or policy failures, and support cannot correlate failures without
  exposing logs.
- Required fix: freeze an Agent-specific error envelope containing `code`,
  `message`, `retryable`, `correlation_id`, and sanitized `details`; ensure no
  provider body, traceback, credential, prompt, or raw payload leaks.

### [P1] Compound comparisons do not assess scientific compatibility

- Evidence: `app/services/comparison.py:12-63` flattens endpoint rows but does
  not compare endpoint presence, output type, verified unit, prediction mode,
  model version, or metadata status.
- Impact: scientifically incompatible values can be displayed side by side as
  if directly comparable.
- Required fix: emit endpoint-level `comparable`, reason, and warning fields;
  retain the existing prohibition on ranking, winner selection, and composite
  scores. Cover mock/real, unit, output-type, missing-value, and unknown-metadata
  cases.

### [P1] Batch summaries omit deterministic endpoint statistics

- Evidence: the batch Agent tool currently returns job-level summary/progress
  rather than computing selected endpoint count, missing/failed rows, duplicate
  treatment, and numeric min/max/mean in Python.
- Impact: the model would need row-level data or would have to infer statistics,
  violating the deterministic-tool boundary.
- Required fix: compute bounded aggregate statistics in the backend and provide
  only sanitized aggregates to the LLM.

### [P1] Backend/frontend contracts are not yet frozen for the Assistant

- Evidence: `app/agent_runtime/contracts.py:79-91` uses lowercase UI action
  names and lacks action identity, target route, and expected state version.
- Evidence: `app/agent_runtime/contracts.py:154-164` lacks the documented
  `batch_errors`, `model_information`, and generic `resource` payload variants.
- Impact: implementing the frontend now would encode a drifting contract and
  create unsafe free-form dispatch behavior.
- Required fix: freeze strict page-context, payload, confirmation, UI-action,
  and error fixtures before frontend implementation. UI actions must remain an
  allowlist and side-effecting actions must require confirmation.

### [P2] Audit records need stronger default correlation and exception coverage

- Evidence: `app/agent_runtime/audit.py:9-48` redacts common sensitive fields,
  but session hashes and turn identifiers are not automatically included and
  exception/redaction behavior is not comprehensively tested.
- Impact: incident diagnosis is weaker, while future callers may accidentally
  include sensitive nested values.
- Required fix: add safe session/turn correlation, recursive bounded redaction,
  and tests for provider errors, tool errors, prompts, authorization values,
  SMILES, and nested payloads.

## Positive observations

- ADMET prediction remains in the existing deterministic service; the LLM does
  not calculate scientific values.
- Agent initialization is lazy and route-gated, so the intended disabled-mode
  isolation is structurally sound, subject to an explicit regression test.
- Pydantic request models use `extra="forbid"` and page context is a
  discriminated union.
- Resources are hashed, size-limited, and stored outside model-visible message
  history.
- Existing comparison output explicitly disables ranking and winner selection.

## Required verification before Stage B

1. Confirmation concurrency, replay, crash-recovery, stale-state, expiry,
   tamper, cross-session, and timeout-status tests pass.
2. Scientific hallucination tests cover unknown endpoints, units, probability,
   classification semantics, mock/real provenance, measurements, rankings, and
   poisoned tool output.
3. Tool-loop and strict-schema tests pass.
4. Agent-disabled tests prove legacy routes work without creating the Agent DB
   or initializing an LLM provider.
5. Comparison, batch aggregate, error-envelope, audit-redaction, and message/
   resource isolation tests pass.
6. Backend unit and integration suites pass with no new failure or warning.

## Assumptions

- Session IDs are unguessable bearer-like identifiers in this loopback MVP;
  user authentication is outside the current phase.
- SQLite remains the local persistence implementation. The conditional-update
  and recovery contracts must remain portable to a production database later.
- The local OpenAI-compatible server is treated as an untrusted compatibility
  surface. Deterministic policy enforcement remains outside the model.
