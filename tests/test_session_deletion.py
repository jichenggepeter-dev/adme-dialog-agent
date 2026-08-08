from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.agent_runtime.confirmations import ConfirmationEngine
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.routes import get_agent_runtime
from app.agent_runtime.session_deletion import SessionDeletionService
from app.main import app


def populated_session(repository: AgentRepository) -> tuple[dict, dict]:
    session = repository.create_session()
    session_id = session["session_id"]
    repository.add_message(session_id, "user", "private conversation")
    resource = repository.put_resource(session_id, "prediction", {"prediction_mode": "mock"})
    ConfirmationEngine(repository).propose_compound(
        session_id,
        {"compound_id": "compound-one", "canonical_smiles": "CCO"},
        expected_state_version=0,
    )
    repository.create_pending_action(
        session_id, "run_batch_job", {"job_id": "shared-job"}, 0
    )
    repository.add_audit_event(
        session_id=session_id,
        correlation_id="audit-one",
        event_type="agent_run",
        status="ok",
        summary={"message": "not retained"},
    )
    return session, resource


def test_deletion_requires_confirmation_is_owned_and_is_idempotent(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    owner, resource = populated_session(repository)
    stranger = repository.create_session()
    service = SessionDeletionService(repository)

    proposal = service.prepare(owner["session_id"], expected_state_version=0)
    assert proposal["action"]["payload"] == {}
    assert proposal["counts"] == {
        "sessions": 1,
        "messages": 1,
        "business_state": 1,
        "confirmations": 1,
        "pending_actions": 2,
        "resources": 1,
        "audit_events": 1,
    }
    assert "shared Batch uploads and jobs" in proposal["retained"]

    rejected = service.decide(
        owner["session_id"],
        proposal["action"]["action_id"],
        decision="reject",
        expected_state_version=0,
    )
    assert rejected["status"] == "rejected"
    assert repository.get_session(owner["session_id"])["status"] == "active"

    approved_proposal = service.prepare(owner["session_id"], expected_state_version=0)
    with pytest.raises(AgentCoreError) as cross_session:
        service.decide(
            stranger["session_id"],
            approved_proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
        )
    assert cross_session.value.code == "ACTION_NOT_ALLOWED"

    deleted = service.decide(
        owner["session_id"],
        approved_proposal["action"]["action_id"],
        decision="approve",
        expected_state_version=0,
    )
    assert deleted["status"] == "deleted"
    assert deleted["counts"]["pending_actions"] == 3
    assert "session_id" not in json.dumps(deleted)

    with pytest.raises(AgentCoreError) as missing_session:
        repository.get_session(owner["session_id"])
    assert missing_session.value.code == "SESSION_NOT_FOUND"
    with pytest.raises(AgentCoreError) as missing_resource:
        repository.get_resource(owner["session_id"], resource["resource_id"])
    assert missing_resource.value.code == "RESOURCE_NOT_FOUND"
    assert repository.get_session(stranger["session_id"])["status"] == "active"

    repeated = service.decide(
        owner["session_id"],
        approved_proposal["action"]["action_id"],
        decision="approve",
        expected_state_version=0,
    )
    assert repeated == deleted
    with pytest.raises(AgentCoreError) as wrong_retry:
        service.decide(
            owner["session_id"],
            "action_not_the_approved_delete",
            decision="approve",
            expected_state_version=0,
        )
    assert wrong_retry.value.code == "ACTION_NOT_ALLOWED"

    with repository.connection() as connection:
        tombstone = connection.execute(
            "SELECT * FROM agent_session_deletions"
        ).fetchone()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    assert tombstone is not None
    assert owner["session_id"] not in json.dumps(dict(tombstone))
    assert foreign_key_errors == []


def test_prepare_and_reject_only_change_the_deletion_control_record(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    session_id = session["session_id"]
    repository.add_message(session_id, "user", "keep me until approval")
    service = SessionDeletionService(repository)

    with repository.connection() as connection:
        before_session = dict(connection.execute(
            "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
        ).fetchone())
        before_message = dict(connection.execute(
            "SELECT * FROM agent_messages WHERE session_id = ?", (session_id,)
        ).fetchone())

    proposal = service.prepare(session_id, expected_state_version=0)
    with repository.connection() as connection:
        after_prepare_session = dict(connection.execute(
            "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
        ).fetchone())
        after_prepare_message = dict(connection.execute(
            "SELECT * FROM agent_messages WHERE session_id = ?", (session_id,)
        ).fetchone())
    assert after_prepare_session == before_session
    assert after_prepare_message == before_message

    service.decide(
        session_id,
        proposal["action"]["action_id"],
        decision="reject",
        expected_state_version=0,
    )
    with repository.connection() as connection:
        after_reject_session = dict(connection.execute(
            "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
        ).fetchone())
        action_status = connection.execute(
            "SELECT status FROM agent_pending_actions WHERE action_id = ?",
            (proposal["action"]["action_id"],),
        ).fetchone()[0]
    assert after_reject_session == before_session
    assert action_status == "rejected"


def test_deletion_rolls_back_every_table_when_one_delete_fails(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session, resource = populated_session(repository)
    service = SessionDeletionService(repository)
    proposal = service.prepare(session["session_id"], expected_state_version=0)
    with repository.connection() as connection:
        connection.execute(
            """CREATE TRIGGER block_resource_delete
               BEFORE DELETE ON agent_resources
               BEGIN SELECT RAISE(ABORT, 'resource delete failed'); END"""
        )
        connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
        )
    assert repository.get_session(session["session_id"])["status"] == "active"
    assert repository.get_resource(session["session_id"], resource["resource_id"])["data"]
    assert repository.get_pending_action(
        session["session_id"], proposal["action"]["action_id"]
    )["status"] == "awaiting_confirmation"
    with repository.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM agent_session_deletions").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_deletion_requires_new_confirmation_when_session_changes(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    service = SessionDeletionService(repository)
    proposal = service.prepare(session["session_id"], expected_state_version=0)
    repository.add_message(session["session_id"], "user", "added after confirmation")

    with pytest.raises(AgentCoreError) as stale:
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
        )
    assert stale.value.code == "DELETE_STALE"
    assert repository.get_session(session["session_id"])["status"] == "active"
    assert repository.list_messages(session["session_id"], 10, 0)["total"] == 1


def test_deletion_binds_request_action_and_session_versions(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    service = SessionDeletionService(repository)
    proposal = service.prepare(session["session_id"], expected_state_version=0)
    with repository.connection() as connection:
        connection.execute(
            "UPDATE agent_pending_actions SET expected_state_version = 1 WHERE action_id = ?",
            (proposal["action"]["action_id"],),
        )
        connection.commit()

    with pytest.raises(AgentCoreError) as stale:
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
        )
    assert stale.value.code == "ACTION_STALE"
    assert repository.get_session(session["session_id"])["status"] == "active"


def test_late_session_owned_write_has_stable_not_found_error(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    service = SessionDeletionService(repository)
    proposal = service.prepare(session["session_id"], expected_state_version=0)
    service.decide(
        session["session_id"],
        proposal["action"]["action_id"],
        decision="approve",
        expected_state_version=0,
    )

    with pytest.raises(AgentCoreError) as missing:
        with repository.connection() as connection:
            connection.execute(
                "INSERT INTO agent_messages VALUES (?, ?, 'user', 'late', '{}', ?)",
                ("msg_late", session["session_id"], "2026-08-06T12:00:00+00:00"),
            )
            connection.commit()
    assert missing.value.code == "SESSION_NOT_FOUND"


def test_deletion_api_returns_stable_receipt_on_retry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    session = client.post("/agent/sessions").json()
    prepared = client.post(
        f"/agent/sessions/{session['session_id']}/deletions",
        json={"expected_state_version": 0},
    )
    assert prepared.status_code == 200
    assert prepared.headers["cache-control"] == "no-store, max-age=0"
    proposal = prepared.json()

    path = f"/agent/sessions/{session['session_id']}/deletions/{proposal['action']['action_id']}"
    deleted = client.post(
        path, json={"decision": "approve", "expected_state_version": 0}
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    repeated = client.post(
        path, json={"decision": "approve", "expected_state_version": 0}
    )
    assert repeated.status_code == 200
    assert repeated.json() == deleted.json()
    assert client.get(f"/agent/sessions/{session['session_id']}").status_code == 404

    wrong_action = client.post(
        f"/agent/sessions/{session['session_id']}/deletions/action_wrong",
        json={"decision": "approve", "expected_state_version": 0},
    )
    assert wrong_action.status_code == 404
    assert wrong_action.headers["cache-control"] == "no-store, max-age=0"
    get_agent_runtime.cache_clear()
