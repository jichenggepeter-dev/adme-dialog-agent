# Agent database migrations

The local Agent database has its own integer schema version. It is independent
from the application release, REST API contract, stream events, evidence
payloads, and session export format.

The current Agent database schema is version `3`. This version covers only the
SQLite file configured by `AGENT_DB_PATH` (normally `data/agent.sqlite3`). Batch
uploads and jobs remain separate local JSON storage.

## Upgrade behavior

`AgentRepository` checks the schema before reading or writing session data:

- A new empty database is created directly at the latest schema.
- Version 1 adds the confirmation lifecycle result fields to become version 2.
- Version 2 adds hashed session-deletion receipts to become version 3.
- Migrations run in order inside one `BEGIN IMMEDIATE` transaction.
- The stored version changes only in the same transaction as its schema change.
- Reopening a version-3 database performs no migration.
- If any step fails, SQLite rolls back the entire sequence and leaves the old
  version and schema unchanged.

A database with a version newer than this application is rejected with
`AGENT_SCHEMA_MISMATCH`. Automatic downgrade is intentionally unsupported
because older code may misread newer data.

## Back up before an upgrade

Stop the backend first so no request writes to the file during backup. From the
repository root:

```bash
mkdir -p backups
sqlite3 data/agent.sqlite3 ".backup 'backups/agent-before-upgrade.sqlite3'"
```

If `AGENT_DB_PATH` points elsewhere, use that path instead. Keep the backup out
of Git: Agent databases can contain session messages, molecular inputs, and
local audit records.

## Recover from a failed upgrade

The migration transaction already preserves the pre-upgrade database when a
step fails. Keep the error and original file for diagnosis. If the file itself
was damaged outside the migration transaction:

1. Stop the backend.
2. Rename the damaged database instead of deleting it.
3. Copy the backup to the configured `AGENT_DB_PATH`.
4. Start the same application version that created the backup and confirm the
   session list before attempting another upgrade.

Example using the default location:

```bash
mv data/agent.sqlite3 data/agent.failed.sqlite3
cp backups/agent-before-upgrade.sqlite3 data/agent.sqlite3
```

Do not edit `agent_schema.version` manually. A version number does not prove
that its table changes completed.

## Adding a future migration

Add one function keyed by the source version in
`app/agent_runtime/migrations.py`, raise `SCHEMA_VERSION` by one, and update the
latest-schema definition for new databases. The same pull request must add an
old-version SQL fixture, a data-preservation assertion, a failure rollback
test, and user-facing backup or recovery notes for any new risk.
