# Issue #13 dual-agent architecture review

- Repository baseline: `16434d246c2f1d5e8e38912935ecb494e5b7b1c6`
- Independent reviewer: ChatGPT Pro
- Review conversation: <https://chatgpt.com/c/6a74f2fe-6c14-83ea-9aa0-3bab72a3615d>
- Verdict on the initial proposal: **PASS WITH CHANGES**
- Final implementation and acceptance owner: Codex

## Findings adopted

1. A state version alone does not cover messages, confirmations, audit events,
   or resources. The one-shot proposal now stores a digest of a consistent,
   ordered snapshot and approval rejects a changed snapshot with
   `EXPORT_STALE`.
2. Export projection is allowlist-first. Only user/assistant messages are read;
   confirmation and activity fields are selected explicitly; Batch and raw
   resources are absent even from the manifest; selected compound/prediction
   data uses strict versioned DTOs.
3. The raw session ID is omitted from exported files because it is the current
   local access capability.
4. A committed strict JSON Schema v1 mirrors the executable Pydantic model.
   JSON validates before serialization and Markdown is rendered from the same
   validated model.
5. Activity is the most recent 200 eligible events, emitted chronologically
   with total, included, and omitted counts. Other item limits fail explicitly.
6. Successful action finalization and the redacted audit insertion now commit
   in one SQLite transaction. No content is returned if that transaction fails.
7. The confirmation dialog exposes current-session scope, format, snapshot
   time, counts, exclusions, redaction behavior, and the byte cap using native
   keyboard-operable controls.

## Judgment calls

- Per-table cursor fields were not added because the stored digest covers the
  complete ordered projection and approval rereads it from one consistent
  SQLite snapshot. Adding cursors would duplicate that invariant.
- Incremental streaming serialization was not added. Existing inputs are
  already bounded (8,000 characters per chat message and 256 KB per resource),
  source row counts are capped before generation, and the final file has an
  authoritative 1,000,000-byte limit. The maximum in-memory source remains
  small and bounded for this local application.
- Server-side export persistence, replayable downloads, account-wide export,
  Batch export, authentication redesign, and a generic policy framework remain
  out of scope for this issue.
