# Issue #14 dual-agent architecture review

- Repository baseline: `16434d246c2f1d5e8e38912935ecb494e5b7b1c6`
- Independent reviewer: ChatGPT Pro
- Review conversation: <https://chatgpt.com/c/6a74f9db-2ee0-83ea-8b14-0e95b06b48fe>
- Verdict on the initial proposal: **PASS WITH CHANGES**
- Final implementation and acceptance owner: Codex

## Findings adopted

1. Preparing and rejecting deletion now use dedicated repository operations.
   They create or terminalize only the `delete_session_v1` control record and
   never update the session row, messages, state, confirmations, resources, or
   audit events.
2. Approval uses one `BEGIN IMMEDIATE` transaction and does not reuse the
   generic claim/finish helpers. It verifies session/action ownership, action
   type and TTL, payload integrity, the three-way state-version binding, and an
   immutable session snapshot before the first delete.
3. The terminal receipt is bound to domain-separated hashes of both the
   deleted session capability and the exact approved action. Only an exact
   retry can receive the original receipt.
4. The frontend retires the old session generation before approval. Late
   stream events and completions from that generation cannot repopulate React
   state after deletion, and a replacement session is installed only into the
   expected generation.
5. Success and expected error responses on deletion routes use
   `Cache-Control: no-store, max-age=0`. Foreign-key failures from late
   session-owned writes are normalized to `SESSION_NOT_FOUND`.
6. Tests cover schema migration, confirmation/rejection boundaries, ownership,
   stale snapshots, three-way version binding, atomic rollback, foreign-key
   integrity, exact idempotent retry, stable not-found behavior, frontend
   clearing, and desktop/mobile E2E.

## Judgment calls

- The dedicated pending action is retained as a narrow control-plane record
  because the product must prove explicit consent. The documentation states
  precisely that “no change before approval” means no covered session data is
  deleted or mutated; only this confirmation record may change.
- Batch uploads and jobs remain untouched. The current Batch storage has no
  trustworthy `session_id` ownership mapping, so deleting referenced files
  would cross the authorization boundary.
- One representative mid-transaction failure-injection test is used instead
  of test-only hooks after every SQL statement. SQLite transaction rollback,
  row-count checks, and `foreign_key_check` provide the remaining invariant
  coverage without adding production branching for tests.
- The receipt remains for the lifetime of the local database. Secure physical
  erasure from SQLite pages, WAL files, backups, or storage snapshots is not
  claimed.
- Authentication redesign, soft deletion, Batch ownership migration,
  filesystem cleanup, and LLM-initiated deletion remain outside Issue #14.
