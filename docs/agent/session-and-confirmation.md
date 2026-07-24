# Session and Confirmation

## SQLite Schema

Schema version: `1`.

| Table | Purpose |
| --- | --- |
| `agent_sessions` | TTL, status, last access, authoritative state version |
| `agent_messages` | Paginated user/assistant/tool/confirmation history |
| `agent_business_state` | Structured current compound, confirmation, prediction, batch, endpoint, and page references |
| `agent_confirmations` | Hash-bound structure confirmations and lifecycle |
| `agent_pending_actions` | Hash-bound future side-effect proposals; none are exposed as initial tools |
| `agent_resources` | Bounded session-owned JSON resources |
| `agent_audit_events` | Redacted local operational/audit events |

Existing `data/jobs` and `data/uploads` JSON storage is unchanged.

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
