from __future__ import annotations

import sqlite3
from collections.abc import Callable

from app.agent_runtime.errors import AgentCoreError


SCHEMA_VERSION = 4

AGENT_SCHEMA = (
    """CREATE TABLE agent_schema (
           version INTEGER NOT NULL
       )""",
    """CREATE TABLE agent_sessions (
           session_id TEXT PRIMARY KEY,
           status TEXT NOT NULL,
           created_at TEXT NOT NULL,
           last_access_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           state_version INTEGER NOT NULL DEFAULT 0
       )""",
    """CREATE TABLE agent_messages (
           message_id TEXT PRIMARY KEY,
           session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
           role TEXT NOT NULL,
           content TEXT NOT NULL,
           metadata_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE INDEX idx_agent_messages_session
           ON agent_messages(session_id, created_at)""",
    """CREATE TABLE agent_business_state (
           session_id TEXT PRIMARY KEY REFERENCES agent_sessions(session_id),
           state_json TEXT NOT NULL,
           version INTEGER NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE agent_confirmations (
           confirmation_id TEXT PRIMARY KEY,
           session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
           type TEXT NOT NULL,
           status TEXT NOT NULL,
           payload_json TEXT NOT NULL,
           payload_hash TEXT NOT NULL,
           canonical_smiles TEXT NOT NULL,
           expected_state_version INTEGER NOT NULL,
           created_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           consumed_at TEXT,
           version INTEGER NOT NULL DEFAULT 0,
           result_resource_id TEXT,
           error_code TEXT
       )""",
    """CREATE INDEX idx_agent_confirmations_session
           ON agent_confirmations(session_id, created_at)""",
    """CREATE TABLE agent_pending_actions (
           action_id TEXT PRIMARY KEY,
           session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
           action_type TEXT NOT NULL,
           status TEXT NOT NULL,
           payload_json TEXT NOT NULL,
           payload_hash TEXT NOT NULL,
           expected_state_version INTEGER NOT NULL,
           created_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           consumed_at TEXT
       )""",
    """CREATE TABLE agent_resources (
           resource_id TEXT PRIMARY KEY,
           session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
           resource_type TEXT NOT NULL,
           content_json TEXT NOT NULL,
           content_hash TEXT NOT NULL,
           size_bytes INTEGER NOT NULL,
           created_at TEXT NOT NULL,
           expires_at TEXT NOT NULL
       )""",
    """CREATE INDEX idx_agent_resources_session
           ON agent_resources(session_id, created_at)""",
    """CREATE TABLE agent_audit_events (
           event_id TEXT PRIMARY KEY,
           session_id TEXT REFERENCES agent_sessions(session_id),
           correlation_id TEXT NOT NULL,
           event_type TEXT NOT NULL,
           model TEXT,
           tool_name TEXT,
           duration_ms INTEGER,
           status TEXT NOT NULL,
           error_code TEXT,
           summary_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE TABLE agent_session_deletions (
           session_hash TEXT PRIMARY KEY,
           action_hash TEXT NOT NULL,
           deleted_at TEXT NOT NULL,
           counts_json TEXT NOT NULL
       )""",
)

KNOWLEDGE_SCHEMA = (
    """CREATE TABLE knowledge_collections (
           collection_id TEXT PRIMARY KEY,
           display_name TEXT NOT NULL,
           state TEXT NOT NULL,
           provider_access_mode TEXT NOT NULL,
           active_index_version INTEGER NOT NULL DEFAULT 0,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE knowledge_documents (
           document_id TEXT PRIMARY KEY,
           collection_id TEXT NOT NULL REFERENCES knowledge_collections(collection_id) ON DELETE CASCADE,
           display_name TEXT NOT NULL,
           media_type TEXT NOT NULL,
           size_bytes INTEGER NOT NULL,
           normalized_bytes INTEGER NOT NULL,
           sha256 TEXT NOT NULL,
           revision INTEGER NOT NULL,
           state TEXT NOT NULL,
           rights_basis TEXT NOT NULL,
           source_url TEXT,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL,
           UNIQUE(collection_id, sha256)
       )""",
    """CREATE INDEX idx_knowledge_documents_collection
           ON knowledge_documents(collection_id, created_at)""",
    """CREATE TABLE knowledge_index_versions (
           collection_id TEXT NOT NULL REFERENCES knowledge_collections(collection_id) ON DELETE CASCADE,
           version INTEGER NOT NULL,
           schema_version INTEGER NOT NULL,
           source_digest TEXT NOT NULL,
           retrieval_config_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           PRIMARY KEY(collection_id, version)
       )""",
    """CREATE TABLE knowledge_chunks (
           collection_id TEXT NOT NULL,
           index_version INTEGER NOT NULL,
           chunk_id TEXT NOT NULL,
           document_id TEXT NOT NULL,
           document_revision INTEGER NOT NULL,
           position INTEGER NOT NULL,
           excerpt TEXT NOT NULL,
           excerpt_hash TEXT NOT NULL,
           tokens_json TEXT NOT NULL,
           length INTEGER NOT NULL,
           PRIMARY KEY(collection_id, index_version, chunk_id),
           FOREIGN KEY(collection_id, index_version)
             REFERENCES knowledge_index_versions(collection_id, version) ON DELETE CASCADE
       )""",
    """CREATE INDEX idx_knowledge_chunks_document
           ON knowledge_chunks(collection_id, index_version, document_id)""",
)

LATEST_SCHEMA = AGENT_SCHEMA + KNOWLEDGE_SCHEMA


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE agent_confirmations "
        "ADD COLUMN version INTEGER NOT NULL DEFAULT 0"
    )
    connection.execute(
        "ALTER TABLE agent_confirmations ADD COLUMN result_resource_id TEXT"
    )
    connection.execute("ALTER TABLE agent_confirmations ADD COLUMN error_code TEXT")


def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE agent_session_deletions (
               session_hash TEXT PRIMARY KEY,
               action_hash TEXT NOT NULL,
               deleted_at TEXT NOT NULL,
               counts_json TEXT NOT NULL
           )"""
    )


def _migrate_v3_to_v4(connection: sqlite3.Connection) -> None:
    for statement in KNOWLEDGE_SCHEMA:
        connection.execute(statement)


Migration = Callable[[sqlite3.Connection], None]
MIGRATIONS: dict[int, Migration] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
}


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the latest schema or upgrade a supported older schema atomically."""
    try:
        connection.execute("BEGIN IMMEDIATE")
        if not _table_exists(connection, "agent_schema"):
            for statement in LATEST_SCHEMA:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO agent_schema(version) VALUES (?)", (SCHEMA_VERSION,)
            )
            connection.commit()
            return

        rows = connection.execute("SELECT version FROM agent_schema").fetchall()
        if len(rows) != 1:
            raise _schema_error("The Agent database has no single schema version.")

        version = rows[0][0]
        if not isinstance(version, int) or version < 1:
            raise _schema_error(f"Agent database schema version {version!r} is invalid.")
        if version > SCHEMA_VERSION:
            raise _schema_error(
                f"Agent database schema version {version} is newer than supported "
                f"version {SCHEMA_VERSION}. Downgrades are not supported; use a "
                "compatible application version or restore a backup."
            )

        while version < SCHEMA_VERSION:
            migration = MIGRATIONS.get(version)
            if migration is None:
                raise _schema_error(
                    f"No migration is available from Agent database schema version {version}."
                )
            migration(connection)
            version += 1
            connection.execute("UPDATE agent_schema SET version = ?", (version,))

        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


def _schema_error(message: str) -> AgentCoreError:
    return AgentCoreError("AGENT_SCHEMA_MISMATCH", message, 500)
