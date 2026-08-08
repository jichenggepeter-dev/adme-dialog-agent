# Session and Confirmation

## SQLite Schema

Schema version: `3`.

| Table | Purpose |
| --- | --- |
| `agent_sessions` | TTL, status, last access, authoritative state version |
| `agent_messages` | Paginated user/assistant/tool/confirmation history |
| `agent_business_state` | Structured current compound, confirmation, prediction, batch, endpoint, and page references |
| `agent_confirmations` | Hash-bound structure confirmations and lifecycle |
| `agent_pending_actions` | Hash-bound future side-effect proposals; none are exposed as initial tools |
| `agent_resources` | Bounded session-owned JSON resources |
| `agent_audit_events` | Redacted local operational/audit events |
| `agent_session_deletions` | Minimal hashed receipts for idempotent approved deletion retries |

Existing `data/jobs` and `data/uploads` JSON storage is unchanged.

Schema initialization upgrades supported version-1 confirmation columns to
version 2 and recognizes version 3 deletion receipts. An unknown schema version
fails with `AGENT_SCHEMA_MISMATCH`; this is not yet the general migration
tooling planned for v0.3.

## Concurrency and Integrity

- Mutating operations use `BEGIN IMMEDIATE` transactions.
- `expected_state_version` enforces optimistic concurrency.
- Resource and confirmation/action payloads are SHA-256 bound.
- Confirmation and action decisions are single-use.
- Session ownership is checked before resource, confirmation, or action access.
- Sessions, confirmations, actions, and resources have expiration timestamps.

## Structure Confirmation State Machine

```text
proposed
  -> awaiting_confirmation
  -> approved
  -> executing
  -> succeeded | failed

terminal: rejected | expired | superseded
```

The implementation creates structure confirmations directly in `awaiting_confirmation`. New pending structure confirmation supersedes an older pending one for the same session.

## Scientific Confirmation Policy

Names, PubChem CIDs, and valid SMILES all require confirmation. RDKit parse success does not waive confirmation. The confirmation records the canonical structure actually sent to the predictor and exposes fragments, charge, salts/mixtures, metals, unusual elements, and size warnings.

Prediction requires both:

1. `confirmed_compound_id` in structured business state.
2. An exact canonical SMILES match between the confirmed record and compound resource.

Rejected, expired, superseded, stale, cross-session, or replayed confirmation cannot run prediction.

## Session export and deletion actions

Session export and deletion use expiring `agent_pending_actions` records with an
expected state version, a hash-bound private payload, and explicit approve or
reject decisions.

- Export binds its format, limits, selected resources, and immutable session
  snapshot before producing an in-memory JSON or Markdown download. It writes a
  redacted success audit event but never stores the exported file.
- Deletion binds the complete owned-session snapshot before one
  `BEGIN IMMEDIATE` transaction removes the session and child rows. A minimal
  receipt retains only hashed identifiers, time, and counts so the exact
  approved retry is idempotent.
- Global Batch uploads and jobs are not deleted because their current storage
  has no trustworthy session ownership mapping.

The full inclusion, exclusion, and retention rules are documented in
[session export](../session-export.md) and
[session deletion](../session-deletion.md).
