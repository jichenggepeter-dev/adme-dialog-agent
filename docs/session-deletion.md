# Session deletion contract

Session deletion permanently removes one current Assistant session after an
explicit, one-shot confirmation. It is not an account deletion and does not
claim ownership of globally shared Batch files.

## User flow

1. Select **Delete session** in the Assistant header.
2. Review exact row counts, deletion categories, and retained categories.
3. Select **Cancel** to reject without deleting session data, or select **Delete
   session** to approve the irreversible action.
4. After success, the browser clears the deleted session from memory and
   creates a fresh empty session. It never rereads the deleted session.

If any covered session data changes while the dialog is open, approval returns
`DELETE_STALE` and the user must review a new request.

## Deleted in one transaction

- the session record;
- conversation messages;
- business and page state;
- confirmations and pending actions;
- session-owned Agent resources, including Agent-side Batch summaries;
- session audit events.

All child rows, the session row, and the minimal deletion receipt are handled
inside one SQLite `BEGIN IMMEDIATE` transaction. A failure rolls back every
delete, so a session cannot be left half-deleted.

## Deliberately retained

- Global Batch uploads and jobs under `ADME_DATA_DIR`. Their current storage
  records have no `session_id` or trustworthy ownership mapping, so deleting
  them here could destroy data shared with another workflow.
- Application evidence, models, configuration, and source data.
- One minimal deletion receipt containing SHA-256 hashes of the former session
  capability and approved action ID, deletion time, and row counts.

The receipt remains for the lifetime of the local database so an interrupted
approval can be retried safely. It contains no raw session ID, action ID, message, resource ID,
filename, content, or audit payload. It allows an exact retry of the approved
request to return the same logical result. A different action ID cannot use the
receipt.

## API

`POST /agent/sessions/{session_id}/deletions` creates an expiring
`delete_session_v1` proposal bound to the expected state version and a digest
of the complete private-session ownership snapshot.

Preparing or rejecting a request changes only that dedicated deletion control
record. It does not update the session row (including `last_access_at` or
`state_version`) and does not change messages, business state, confirmations,
other pending actions, resources, or audit events. This narrow control-plane
record is necessary to prove explicit consent; no covered session data is
deleted until approval.

`POST /agent/sessions/{session_id}/deletions/{action_id}` rejects or approves
the proposal. Rejection terminalizes only the deletion control record. Approval verifies ownership, expiry, payload integrity, state
version, and the snapshot digest before entering the atomic delete.

Deleted sessions and their former resources return the existing stable
`SESSION_NOT_FOUND` and `RESOURCE_NOT_FOUND` responses. Deletion-route responses
use `Cache-Control: no-store, max-age=0`.
