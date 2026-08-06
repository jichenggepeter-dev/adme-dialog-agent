from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.agent_runtime.errors import AgentCoreError


SCHEMA_VERSION = 3
DEFAULT_SESSION_TTL_SECONDS = 24 * 60 * 60
DEFAULT_CONFIRMATION_TTL_SECONDS = 15 * 60
DEFAULT_RESOURCE_TTL_SECONDS = 24 * 60 * 60
MAX_RESOURCE_BYTES = 256_000


class AgentRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            if "FOREIGN KEY constraint failed" in str(exc):
                raise AgentCoreError(
                    "SESSION_NOT_FOUND", "Agent session was not found.", 404
                ) from exc
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_schema (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_access_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    state_version INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS agent_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_messages_session
                    ON agent_messages(session_id, created_at);
                CREATE TABLE IF NOT EXISTS agent_business_state (
                    session_id TEXT PRIMARY KEY REFERENCES agent_sessions(session_id),
                    state_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_confirmations (
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
                );
                CREATE INDEX IF NOT EXISTS idx_agent_confirmations_session
                    ON agent_confirmations(session_id, created_at);
                CREATE TABLE IF NOT EXISTS agent_pending_actions (
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
                );
                CREATE TABLE IF NOT EXISTS agent_resources (
                    resource_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
                    resource_type TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_resources_session
                    ON agent_resources(session_id, created_at);
                CREATE TABLE IF NOT EXISTS agent_audit_events (
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
                );
                CREATE TABLE IF NOT EXISTS agent_session_deletions (
                    session_hash TEXT PRIMARY KEY,
                    action_hash TEXT NOT NULL,
                    deleted_at TEXT NOT NULL,
                    counts_json TEXT NOT NULL
                );
                """
            )
            row = connection.execute("SELECT version FROM agent_schema LIMIT 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO agent_schema(version) VALUES (?)", (SCHEMA_VERSION,)
                )
            else:
                version = row["version"]
                if version == 1:
                    connection.execute(
                        "ALTER TABLE agent_confirmations ADD COLUMN version INTEGER NOT NULL DEFAULT 0"
                    )
                    connection.execute(
                        "ALTER TABLE agent_confirmations ADD COLUMN result_resource_id TEXT"
                    )
                    connection.execute(
                        "ALTER TABLE agent_confirmations ADD COLUMN error_code TEXT"
                    )
                    version = 2
                if version == 2:
                    version = 3
                if version != SCHEMA_VERSION:
                    raise AgentCoreError(
                        "AGENT_SCHEMA_MISMATCH", "Agent database schema is incompatible.", 500
                    )
                connection.execute("UPDATE agent_schema SET version = ?", (version,))
            connection.commit()

    def create_session(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> dict:
        now = _now()
        session_id = f"session_{uuid4().hex}"
        expires = now + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO agent_sessions VALUES (?, 'active', ?, ?, ?, 0)",
                (session_id, _iso(now), _iso(now), _iso(expires)),
            )
            connection.execute(
                "INSERT INTO agent_business_state VALUES (?, '{}', 0, ?)",
                (session_id, _iso(now)),
            )
            connection.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            if _parse(row["expires_at"]) <= _now() or row["status"] == "expired":
                connection.execute(
                    "UPDATE agent_sessions SET status = 'expired' WHERE session_id = ?",
                    (session_id,),
                )
                connection.commit()
                raise AgentCoreError("SESSION_EXPIRED", "Agent session has expired.", 410)
            connection.execute(
                "UPDATE agent_sessions SET last_access_at = ? WHERE session_id = ?",
                (_iso(_now()), session_id),
            )
            connection.commit()
            return dict(row)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
        *,
        message_id: str | None = None,
    ) -> dict:
        self.get_session(session_id)
        stored_message_id = message_id or f"msg_{uuid4().hex}"
        created = _now()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO agent_messages VALUES (?, ?, ?, ?, ?, ?)",
                (
                    stored_message_id,
                    session_id,
                    role,
                    content,
                    _json(metadata or {}),
                    _iso(created),
                ),
            )
            connection.commit()
        return {
            "message_id": stored_message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": _iso(created),
        }

    def list_messages(self, session_id: str, limit: int, offset: int) -> dict:
        self.get_session(session_id)
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)
        with self.connection() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM agent_messages WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            rows = connection.execute(
                """SELECT * FROM agent_messages WHERE session_id = ?
                   ORDER BY created_at, message_id LIMIT ? OFFSET ?""",
                (session_id, bounded_limit, bounded_offset),
            ).fetchall()
        return {
            "messages": [
                {
                    "message_id": row["message_id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
            "limit": bounded_limit,
            "offset": bounded_offset,
            "total": total,
        }

    def recent_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        self.get_session(session_id)
        bounded_limit = max(1, min(limit, 100))
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT * FROM agent_messages WHERE session_id = ?
                   ORDER BY created_at DESC, message_id DESC LIMIT ?""",
                (session_id, bounded_limit),
            ).fetchall()
        return [
            {
                "message_id": row["message_id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in reversed(rows)
        ]

    def get_business_state(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        with self.connection() as connection:
            row = connection.execute(
                "SELECT state_json FROM agent_business_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return {"state": json.loads(row["state_json"]), "version": session["state_version"]}

    def update_business_state(
        self, session_id: str, patch: dict[str, Any], expected_version: int | None = None
    ) -> dict:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            session = connection.execute(
                "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if session is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            if _parse(session["expires_at"]) <= _now():
                raise AgentCoreError("SESSION_EXPIRED", "Agent session has expired.", 410)
            current_version = session["state_version"]
            if expected_version is not None and expected_version != current_version:
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            row = connection.execute(
                "SELECT state_json FROM agent_business_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            state = json.loads(row["state_json"])
            state.update(patch)
            new_version = current_version + 1
            now = _iso(_now())
            connection.execute(
                "UPDATE agent_business_state SET state_json = ?, version = ?, updated_at = ? WHERE session_id = ?",
                (_json(state), new_version, now, session_id),
            )
            connection.execute(
                "UPDATE agent_sessions SET state_version = ?, last_access_at = ? WHERE session_id = ?",
                (new_version, now, session_id),
            )
            connection.commit()
        return {"state": state, "version": new_version}

    def create_confirmation(
        self,
        session_id: str,
        payload: dict[str, Any],
        canonical_smiles: str,
        expected_state_version: int,
        ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS,
    ) -> dict:
        session = self.get_session(session_id)
        if session["state_version"] != expected_state_version:
            raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
        confirmation_id = f"confirm_{uuid4().hex}"
        payload_json = _json(payload)
        created = _now()
        expires = created + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """UPDATE agent_confirmations SET status = 'superseded', consumed_at = ?
                   WHERE session_id = ? AND status = 'awaiting_confirmation'""",
                (_iso(created), session_id),
            )
            connection.execute(
                """INSERT INTO agent_confirmations
                   (confirmation_id, session_id, type, status, payload_json, payload_hash,
                    canonical_smiles, expected_state_version, created_at, expires_at,
                    consumed_at, version, result_resource_id, error_code)
                   VALUES (?, ?, 'compound_structure', 'awaiting_confirmation', ?, ?, ?, ?, ?, ?, NULL, 0, NULL, NULL)""",
                (
                    confirmation_id,
                    session_id,
                    payload_json,
                    _hash(payload_json),
                    canonical_smiles,
                    expected_state_version,
                    _iso(created),
                    _iso(expires),
                ),
            )
            connection.commit()
        return self.get_confirmation(session_id, confirmation_id)

    def get_confirmation(self, session_id: str, confirmation_id: str) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT c.* FROM agent_confirmations c
                   JOIN agent_sessions s ON s.session_id = c.session_id
                   WHERE c.confirmation_id = ? AND c.session_id = ?""",
                (confirmation_id, session_id),
            ).fetchone()
            if row is None:
                raise AgentCoreError(
                    "ACTION_NOT_ALLOWED", "Confirmation was not found for this session.", 404
                )
            result = dict(row)
            result["payload"] = json.loads(result.pop("payload_json"))
            return result

    def approve_and_claim_confirmation(
        self, session_id: str, confirmation_id: str, expected_state_version: int
    ) -> tuple[dict, dict]:
        now = _now()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT c.*, s.status AS session_status, s.expires_at AS session_expires,
                          s.state_version AS current_state_version, b.state_json
                   FROM agent_confirmations c
                   JOIN agent_sessions s ON s.session_id = c.session_id
                   JOIN agent_business_state b ON b.session_id = c.session_id
                   WHERE c.confirmation_id = ? AND c.session_id = ?""",
                (confirmation_id, session_id),
            ).fetchone()
            if row is None:
                raise AgentCoreError("CONFIRMATION_NOT_FOUND", "Confirmation was not found.", 404)
            if row["session_status"] != "active" or _parse(row["session_expires"]) <= now:
                raise AgentCoreError("SESSION_EXPIRED", "Agent session has expired.", 410)
            if _parse(row["expires_at"]) <= now:
                connection.execute(
                    """UPDATE agent_confirmations SET status='expired', consumed_at=?, version=version+1
                       WHERE confirmation_id=? AND session_id=? AND status='awaiting_confirmation'""",
                    (_iso(now), confirmation_id, session_id),
                )
                connection.commit()
                raise AgentCoreError("CONFIRMATION_EXPIRED", "Confirmation has expired.", 410)
            if row["status"] != "awaiting_confirmation":
                raise AgentCoreError("CONFIRMATION_REPLAYED", "Confirmation has already been handled.", 409)
            if row["current_state_version"] != expected_state_version:
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(row["payload_json"]) != row["payload_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Confirmation payload integrity check failed.", 409)
            payload = json.loads(row["payload_json"])
            if payload.get("canonical_smiles") != row["canonical_smiles"] or not payload.get("compound_id"):
                raise AgentCoreError("TOOL_RESULT_INVALID", "Confirmation payload is invalid.", 409)

            claimed = connection.execute(
                """UPDATE agent_confirmations
                   SET status='executing', version=version+1
                   WHERE confirmation_id=? AND session_id=? AND status='awaiting_confirmation'
                     AND version=? AND expires_at>?""",
                (confirmation_id, session_id, row["version"], _iso(now)),
            )
            if claimed.rowcount != 1:
                connection.rollback()
                raise AgentCoreError("CONFIRMATION_REPLAYED", "Confirmation could not be claimed.", 409)
            state = json.loads(row["state_json"])
            state.update(
                {
                    "confirmed_compound_id": payload["compound_id"],
                    "confirmed_canonical_smiles": row["canonical_smiles"],
                    "last_confirmation_id": confirmation_id,
                }
            )
            new_version = expected_state_version + 1
            updated = connection.execute(
                """UPDATE agent_business_state SET state_json=?, version=?, updated_at=?
                   WHERE session_id=? AND version=?""",
                (_json(state), new_version, _iso(now), session_id, expected_state_version),
            )
            if updated.rowcount != 1:
                connection.rollback()
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            connection.execute(
                "UPDATE agent_sessions SET state_version=?, last_access_at=? WHERE session_id=?",
                (new_version, _iso(now), session_id),
            )
            connection.commit()
        return self.get_confirmation(session_id, confirmation_id), {"state": state, "version": new_version}

    def finish_confirmation(
        self, session_id: str, confirmation_id: str, *, resource_id: str | None, error_code: str | None
    ) -> dict:
        status = "succeeded" if resource_id and not error_code else "failed"
        with self.connection() as connection:
            result = connection.execute(
                """UPDATE agent_confirmations
                   SET status=?, consumed_at=?, result_resource_id=?, error_code=?, version=version+1
                   WHERE confirmation_id=? AND session_id=? AND status='executing'""",
                (status, _iso(_now()), resource_id, error_code, confirmation_id, session_id),
            )
            connection.commit()
        if result.rowcount != 1:
            raise AgentCoreError("CONFIRMATION_REPLAYED", "Confirmation is not executing.", 409)
        return self.get_confirmation(session_id, confirmation_id)

    def transition_confirmation(
        self,
        session_id: str,
        confirmation_id: str,
        from_status: str,
        to_status: str,
        expected_state_version: int,
    ) -> dict:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM agent_confirmations WHERE confirmation_id = ? AND session_id = ?",
                (confirmation_id, session_id),
            ).fetchone()
            if row is None:
                raise AgentCoreError(
                    "ACTION_NOT_ALLOWED", "Confirmation was not found for this session.", 404
                )
            if _parse(row["expires_at"]) <= _now():
                connection.execute(
                    "UPDATE agent_confirmations SET status = 'expired', consumed_at = ? WHERE confirmation_id = ?",
                    (_iso(_now()), confirmation_id),
                )
                connection.commit()
                raise AgentCoreError(
                    "CONFIRMATION_EXPIRED", "Confirmation has expired.", 410
                )
            if row["status"] != from_status:
                raise AgentCoreError(
                    "CONFIRMATION_REPLAYED",
                    "Confirmation has already been handled or superseded.",
                    409,
                )
            if from_status == "awaiting_confirmation":
                session = connection.execute(
                    "SELECT state_version FROM agent_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if session["state_version"] != expected_state_version:
                    raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(row["payload_json"]) != row["payload_hash"]:
                raise AgentCoreError(
                    "TOOL_RESULT_INVALID", "Confirmation payload integrity check failed.", 409
                )
            consumed = _iso(_now()) if to_status in {"rejected", "succeeded", "failed"} else None
            connection.execute(
                """UPDATE agent_confirmations SET status = ?, consumed_at = ?, version = version + 1
                   WHERE confirmation_id = ? AND session_id = ? AND status = ? AND version = ?""",
                (to_status, consumed, confirmation_id, session_id, from_status, row["version"]),
            )
            if connection.total_changes != 1:
                connection.rollback()
                raise AgentCoreError("CONFIRMATION_REPLAYED", "Confirmation transition lost its claim.", 409)
            connection.commit()
        return self.get_confirmation(session_id, confirmation_id)

    def put_resource(
        self,
        session_id: str,
        resource_type: str,
        data: dict[str, Any] | list[Any],
        ttl_seconds: int = DEFAULT_RESOURCE_TTL_SECONDS,
    ) -> dict:
        self.get_session(session_id)
        content = _json(data)
        size = len(content.encode("utf-8"))
        if size > MAX_RESOURCE_BYTES:
            raise AgentCoreError(
                "RESOURCE_TOO_LARGE", "Agent resource exceeds the storage limit.", 413
            )
        resource_id = f"resource_{uuid4().hex}"
        created = _now()
        expires = created + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO agent_resources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resource_id,
                    session_id,
                    resource_type,
                    content,
                    _hash(content),
                    size,
                    _iso(created),
                    _iso(expires),
                ),
            )
            connection.commit()
        return self.get_resource(session_id, resource_id)

    def create_pending_action(
        self,
        session_id: str,
        action_type: str,
        payload: dict[str, Any],
        expected_state_version: int,
        ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS,
        *,
        action_id: str | None = None,
    ) -> dict:
        session = self.get_session(session_id)
        if session["state_version"] != expected_state_version:
            raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
        stored_action_id = action_id or f"action_{uuid4().hex}"
        payload_json = _json(payload)
        created = _now()
        expires = created + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO agent_pending_actions
                   VALUES (?, ?, ?, 'awaiting_confirmation', ?, ?, ?, ?, ?, NULL)""",
                (
                    stored_action_id,
                    session_id,
                    action_type,
                    payload_json,
                    _hash(payload_json),
                    expected_state_version,
                    _iso(created),
                    _iso(expires),
                ),
            )
            connection.commit()
        return self.get_pending_action(session_id, stored_action_id)

    def prepare_session_deletion(
        self,
        session_id: str,
        *,
        expected_state_version: int,
        action_id: str,
        ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS,
    ) -> tuple[dict, dict[str, int]]:
        """Create the deletion control record without touching session data."""
        created = _now()
        expires = created + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            session = connection.execute(
                "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if session is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            if session["status"] != "active" or _parse(session["expires_at"]) <= created:
                raise AgentCoreError("SESSION_EXPIRED", "Agent session has expired.", 410)
            if session["state_version"] != expected_state_version:
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)

            snapshot = _session_deletion_snapshot(connection, session_id)
            payload_json = _json(
                {
                    "snapshot_hash": _hash(_json(snapshot)),
                    "policy_version": 1,
                }
            )
            connection.execute(
                """INSERT INTO agent_pending_actions
                   VALUES (?, ?, 'delete_session_v1', 'awaiting_confirmation',
                           ?, ?, ?, ?, ?, NULL)""",
                (
                    action_id,
                    session_id,
                    payload_json,
                    _hash(payload_json),
                    expected_state_version,
                    _iso(created),
                    _iso(expires),
                ),
            )
            counts = _session_deletion_counts(connection, session_id)
            connection.commit()
        return self.get_pending_action(session_id, action_id), counts

    def reject_session_deletion(
        self,
        session_id: str,
        action_id: str,
        *,
        expected_state_version: int,
    ) -> None:
        """Reject one deletion proposal without adding messages or touching the session."""
        now = _now()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            session = connection.execute(
                "SELECT state_version FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            action = connection.execute(
                """SELECT * FROM agent_pending_actions
                   WHERE action_id = ? AND session_id = ? AND action_type = 'delete_session_v1'""",
                (action_id, session_id),
            ).fetchone()
            if action is None:
                raise AgentCoreError("ACTION_NOT_ALLOWED", "Deletion action was not found.", 404)
            if action["status"] != "awaiting_confirmation" or _parse(action["expires_at"]) <= now:
                raise AgentCoreError("ACTION_STALE", "Deletion action is stale.", 409)
            if (
                action["expected_state_version"] != expected_state_version
                or session["state_version"] != expected_state_version
            ):
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(action["payload_json"]) != action["payload_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Action payload integrity failed.", 409)
            changed = connection.execute(
                """UPDATE agent_pending_actions SET status = 'rejected', consumed_at = ?
                   WHERE action_id = ? AND session_id = ? AND status = 'awaiting_confirmation'""",
                (_iso(now), action_id, session_id),
            )
            if changed.rowcount != 1:
                raise AgentCoreError("ACTION_STALE", "Deletion action is stale.", 409)
            connection.commit()

    def get_pending_action(self, session_id: str, action_id: str) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_pending_actions WHERE action_id = ? AND session_id = ?",
                (action_id, session_id),
            ).fetchone()
        if row is None:
            raise AgentCoreError("ACTION_NOT_ALLOWED", "Pending action was not found.", 404)
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def transition_pending_action(
        self,
        session_id: str,
        action_id: str,
        decision: str,
        expected_state_version: int,
    ) -> dict:
        target = "approved" if decision == "approve" else "rejected"
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM agent_pending_actions WHERE action_id = ? AND session_id = ?",
                (action_id, session_id),
            ).fetchone()
            if row is None:
                raise AgentCoreError("ACTION_NOT_ALLOWED", "Pending action was not found.", 404)
            if _parse(row["expires_at"]) <= _now():
                connection.execute(
                    "UPDATE agent_pending_actions SET status = 'expired', consumed_at = ? WHERE action_id = ?",
                    (_iso(_now()), action_id),
                )
                connection.commit()
                raise AgentCoreError("ACTION_STALE", "Pending action has expired.", 410)
            if row["status"] != "awaiting_confirmation":
                raise AgentCoreError("ACTION_STALE", "Pending action was already handled.", 409)
            session = connection.execute(
                "SELECT state_version FROM agent_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if session["state_version"] != expected_state_version:
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(row["payload_json"]) != row["payload_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Action payload integrity failed.", 409)
            connection.execute(
                """UPDATE agent_pending_actions SET status = ?, consumed_at = ?
                   WHERE action_id = ? AND session_id = ? AND status = 'awaiting_confirmation'""",
                (target, _iso(_now()), action_id, session_id),
            )
            connection.commit()
        return self.get_pending_action(session_id, action_id)

    def approve_and_claim_pending_action(
        self, session_id: str, action_id: str, expected_state_version: int
    ) -> dict:
        now = _now()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT a.*, s.status AS session_status, s.expires_at AS session_expires,
                          s.state_version AS current_state_version
                   FROM agent_pending_actions a
                   JOIN agent_sessions s ON s.session_id = a.session_id
                   WHERE a.action_id = ? AND a.session_id = ?""",
                (action_id, session_id),
            ).fetchone()
            if row is None:
                raise AgentCoreError("ACTION_NOT_ALLOWED", "Pending action was not found.", 404)
            if row["session_status"] != "active" or _parse(row["session_expires"]) <= now:
                raise AgentCoreError("SESSION_EXPIRED", "Agent session has expired.", 410)
            if _parse(row["expires_at"]) <= now:
                connection.execute(
                    "UPDATE agent_pending_actions SET status='expired', consumed_at=? WHERE action_id=?",
                    (_iso(now), action_id),
                )
                connection.commit()
                raise AgentCoreError("ACTION_STALE", "Pending action has expired.", 410)
            if row["status"] != "awaiting_confirmation":
                raise AgentCoreError("ACTION_STALE", "Pending action was already handled.", 409)
            if row["current_state_version"] != expected_state_version:
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(row["payload_json"]) != row["payload_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Action payload integrity failed.", 409)
            claimed = connection.execute(
                """UPDATE agent_pending_actions SET status='executing'
                   WHERE action_id=? AND session_id=? AND status='awaiting_confirmation'""",
                (action_id, session_id),
            )
            if claimed.rowcount != 1:
                connection.rollback()
                raise AgentCoreError("ACTION_STALE", "Pending action could not be claimed.", 409)
            connection.commit()
        return self.get_pending_action(session_id, action_id)

    def finish_pending_action(
        self, session_id: str, action_id: str, *, succeeded: bool
    ) -> dict:
        status = "succeeded" if succeeded else "failed"
        with self.connection() as connection:
            result = connection.execute(
                """UPDATE agent_pending_actions SET status=?, consumed_at=?
                   WHERE action_id=? AND session_id=? AND status='executing'""",
                (status, _iso(_now()), action_id, session_id),
            )
            connection.commit()
        if result.rowcount != 1:
            raise AgentCoreError("ACTION_STALE", "Pending action is not executing.", 409)
        return self.get_pending_action(session_id, action_id)

    def get_session_deletion_snapshot(
        self, session_id: str, *, exclude_action_id: str | None = None
    ) -> dict:
        with self.connection() as connection:
            connection.execute("BEGIN")
            return _session_deletion_snapshot(
                connection, session_id, exclude_action_id=exclude_action_id
            )

    def get_session_deletion_counts(self, session_id: str) -> dict[str, int]:
        with self.connection() as connection:
            if connection.execute(
                "SELECT 1 FROM agent_sessions WHERE session_id = ?", (session_id,)
            ).fetchone() is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            return _session_deletion_counts(connection, session_id)

    def delete_session_atomically(
        self,
        session_id: str,
        action_id: str,
        *,
        expected_state_version: int,
    ) -> dict:
        session_hash = _deletion_hash("session", session_id)
        action_hash = _deletion_hash("action", action_id)
        now = _now()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = connection.execute(
                "SELECT * FROM agent_session_deletions WHERE session_hash = ?",
                (session_hash,),
            ).fetchone()
            if receipt is not None:
                if receipt["action_hash"] != action_hash:
                    raise AgentCoreError(
                        "ACTION_NOT_ALLOWED", "Deletion action was not found.", 404
                    )
                connection.commit()
                return {
                    "deleted_at": receipt["deleted_at"],
                    "counts": json.loads(receipt["counts_json"]),
                }

            session = connection.execute(
                "SELECT * FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
            action = connection.execute(
                """SELECT * FROM agent_pending_actions
                   WHERE session_id = ? AND action_id = ? AND action_type = 'delete_session_v1'""",
                (session_id, action_id),
            ).fetchone()
            if action is None:
                raise AgentCoreError("ACTION_NOT_ALLOWED", "Deletion action was not found.", 404)
            if _parse(action["expires_at"]) <= now or action["status"] != "awaiting_confirmation":
                raise AgentCoreError("ACTION_STALE", "Deletion action is stale.", 409)
            if (
                action["expected_state_version"] != expected_state_version
                or session["state_version"] != expected_state_version
            ):
                raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)
            if _hash(action["payload_json"]) != action["payload_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Action payload integrity failed.", 409)
            payload = json.loads(action["payload_json"])
            snapshot_hash = payload.get("snapshot_hash")
            if not isinstance(snapshot_hash, str):
                raise AgentCoreError("TOOL_RESULT_INVALID", "Deletion snapshot is invalid.", 409)
            current_snapshot = _session_deletion_snapshot(
                connection, session_id, exclude_action_id=action_id
            )
            if _hash(_json(current_snapshot)) != snapshot_hash:
                raise AgentCoreError(
                    "DELETE_STALE",
                    "The session changed after deletion was prepared. Please review a new request.",
                    409,
                )

            counts = _session_deletion_counts(connection, session_id)
            tables = {
                "messages": "agent_messages",
                "business_state": "agent_business_state",
                "confirmations": "agent_confirmations",
                "pending_actions": "agent_pending_actions",
                "resources": "agent_resources",
                "audit_events": "agent_audit_events",
            }
            for name, table in tables.items():
                deleted = connection.execute(
                    f"DELETE FROM {table} WHERE session_id = ?", (session_id,)
                )
                if deleted.rowcount != counts[name]:
                    raise AgentCoreError("AGENT_STORAGE_ERROR", "Session deletion did not complete.", 500)
            deleted_session = connection.execute(
                "DELETE FROM agent_sessions WHERE session_id = ?", (session_id,)
            )
            if deleted_session.rowcount != 1:
                raise AgentCoreError("AGENT_STORAGE_ERROR", "Session deletion did not complete.", 500)
            deleted_at = _iso(now)
            connection.execute(
                "INSERT INTO agent_session_deletions VALUES (?, ?, ?, ?)",
                (session_hash, action_hash, deleted_at, _json(counts)),
            )
            connection.commit()
        return {"deleted_at": deleted_at, "counts": counts}

    def get_resource(self, session_id: str, resource_id: str) -> dict:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT r.* FROM agent_resources r
                   JOIN agent_sessions s ON s.session_id = r.session_id
                   WHERE r.resource_id = ? AND r.session_id = ? AND s.status = 'active'
                     AND s.expires_at > ?""",
                (resource_id, session_id, _iso(_now())),
            ).fetchone()
            if row is None:
                raise AgentCoreError("RESOURCE_NOT_FOUND", "Agent resource was not found.", 404)
            if _parse(row["expires_at"]) <= _now():
                raise AgentCoreError("RESOURCE_NOT_FOUND", "Agent resource has expired.", 404)
            if _hash(row["content_json"]) != row["content_hash"]:
                raise AgentCoreError("TOOL_RESULT_INVALID", "Resource integrity check failed.", 500)
            result = dict(row)
            result["data"] = json.loads(result.pop("content_json"))
            return result

    def add_audit_event(
        self,
        *,
        session_id: str | None,
        correlation_id: str,
        event_type: str,
        status: str,
        model: str | None = None,
        tool_name: str | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO agent_audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"audit_{uuid4().hex}",
                    session_id,
                    correlation_id,
                    event_type,
                    model,
                    tool_name,
                    duration_ms,
                    status,
                    error_code,
                    _json(summary or {}),
                    _iso(_now()),
                ),
            )
            connection.commit()


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _deletion_hash(kind: str, value: str) -> str:
    return _hash(f"session-deletion-v1:{kind}:{value}")


def _session_deletion_snapshot(
    connection: sqlite3.Connection,
    session_id: str,
    *,
    exclude_action_id: str | None = None,
) -> dict[str, Any]:
    session = connection.execute(
        """SELECT status, created_at, expires_at, state_version
           FROM agent_sessions WHERE session_id = ?""",
        (session_id,),
    ).fetchone()
    if session is None:
        raise AgentCoreError("SESSION_NOT_FOUND", "Agent session was not found.", 404)
    queries = {
        "messages": """SELECT message_id, role, content, metadata_json, created_at
                       FROM agent_messages WHERE session_id=? ORDER BY message_id""",
        "business_state": """SELECT state_json, version, updated_at
                             FROM agent_business_state WHERE session_id=?""",
        "confirmations": """SELECT confirmation_id, status, version, consumed_at,
                                    result_resource_id, error_code
                             FROM agent_confirmations WHERE session_id=? ORDER BY confirmation_id""",
        "resources": """SELECT resource_id, resource_type, content_hash, size_bytes, expires_at
                        FROM agent_resources WHERE session_id=? ORDER BY resource_id""",
        "audit_events": """SELECT event_id, event_type, status, error_code, summary_json, created_at
                           FROM agent_audit_events WHERE session_id=? ORDER BY event_id""",
    }
    pending_actions = connection.execute(
        """SELECT action_id, action_type, status, payload_hash, expires_at, consumed_at
           FROM agent_pending_actions
           WHERE session_id = ? AND (? IS NULL OR action_id != ?)
           ORDER BY action_id""",
        (session_id, exclude_action_id, exclude_action_id),
    ).fetchall()
    return {
        "session": dict(session),
        "pending_actions": [dict(row) for row in pending_actions],
        **{
            name: [dict(row) for row in connection.execute(query, (session_id,)).fetchall()]
            for name, query in queries.items()
        },
    }


def _session_deletion_counts(
    connection: sqlite3.Connection, session_id: str
) -> dict[str, int]:
    tables = {
        "messages": "agent_messages",
        "business_state": "agent_business_state",
        "confirmations": "agent_confirmations",
        "pending_actions": "agent_pending_actions",
        "resources": "agent_resources",
        "audit_events": "agent_audit_events",
    }
    return {
        "sessions": 1,
        **{
            name: connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            for name, table in tables.items()
        },
    }
