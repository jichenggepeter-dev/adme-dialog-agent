# Session export contract

Session export lets a user download the current Assistant session without
publishing server credentials, internal prompts, or full diagnostic records.
It is a local data-portability feature, not a backup or an account-wide export.

## User flow

1. Choose JSON or Markdown in the Assistant header and select **Export**.
2. Review the exact inclusion and exclusion lists in the confirmation dialog.
3. Select **Download** to approve, or **Cancel** to reject the one-shot action.
4. If the session changes while the dialog is open, prepare and review a new
   export. The old approval cannot silently include newer data.

The server creates the file in memory and returns it to the browser. It does
not write an export file to disk.

## Version 1.0 contents

| Included | Excluded |
| --- | --- |
| Current session metadata | API keys, authorization values, cookies, secrets, and credential-looking strings |
| Conversation text | Message metadata, system prompts, and internal prompts |
| Confirmation status summaries | Confirmation payloads and canonical structures stored only for execution |
| Bounded activity fields: event, tool, duration, status, error, time | Full audit summaries, correlation IDs, provider metadata, and model IDs |
| Active `compound` and `prediction` resource metadata | Raw prediction and Batch resources, including their metadata |
| Explicitly selected `compound` and `prediction` resources | Cross-session, expired, raw prediction, and Batch resources |

Every JSON file contains `export_schema_version`, `exported_at`,
`snapshot_taken_at`, and `prediction_mode`. It omits the opaque session ID
because that ID is the local access capability. The executable versioned schema is
`SessionExportDocument` in `app/agent_runtime/contracts.py`, mirrored by the
committed `docs/schemas/agent-session-export-v1.schema.json` artifact. The
export service validates the complete document against that model before
serialization, and tests require the artifact to remain byte-structurally in
sync with the executable schema.

## Limits

- 500 messages
- 100 confirmation summaries
- the most recent 200 activity events, with the number of older omitted events
- 100 resource manifest entries
- 20 explicitly selected resources
- 1,000,000 UTF-8 bytes for the final file

The server returns `EXPORT_LIMIT_EXCEEDED` when an item or byte limit is exceeded.
It never presents a silently truncated file as a complete export.

## API and confirmation boundary

`POST /agent/sessions/{session_id}/exports` creates an expiring
`session_export_v1` action. The action binds the chosen format, selected resource
IDs, schema version, state version, snapshot time, limits, counts, and an immutable snapshot hash. Its public
response intentionally hides the action payload.

`POST /agent/sessions/{session_id}/exports/{action_id}` approves or rejects the
action. Approval is atomic and one-shot. A replay, stale state, changed
snapshot, cross-session action, or cross-session resource is rejected.

Successful generation atomically closes the one-shot action and writes a
redacted `session_export_succeeded` event with only the format, schema version,
counts, and final byte size. Exported content and resource identifiers are not
copied into the audit summary.
