from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.agent_runtime.session_exports as session_exports
from app.agent_runtime.contracts import SessionExportDocument
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.routes import get_agent_runtime
from app.agent_runtime.session_exports import SessionExportService
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_export_requires_confirmation_redacts_secrets_and_is_single_use(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    session_id = session["session_id"]
    repository.add_message(
        session_id,
        "user",
        f"Keep the science, but remove {session_id}, sk-abcdefghijklmnopqrstuvwxyz and Bearer hidden-token.",
        {"system_prompt": "must never leave the server"},
    )
    resource = repository.put_resource(
        session_id,
        "prediction",
        {
            "prediction_mode": "mock",
            "prediction_id": "prediction_public",
            "compound_id": "compound_public",
            "enriched_predictions": {
                "absorption": [
                    {"raw_name": "HIA", "display_name": "Absorption", "value": 0.75}
                ]
            },
            "warnings": [],
            "summary": "Computational result",
            "disclaimer": "Computational prediction only.",
            "api_key": "sk-another-secret-value",
        },
    )
    service = SessionExportService(repository)

    proposal = service.prepare(
        session_id,
        export_format="json",
        expected_state_version=0,
        resource_ids=[resource["resource_id"]],
    )
    assert proposal["action"]["status"] == "awaiting_confirmation"
    assert proposal["action"]["payload"] == {}

    result = service.decide(
        session_id,
        proposal["action"]["action_id"],
        decision="approve",
        expected_state_version=0,
        correlation_id="test-export",
    )
    assert result["status"] == "succeeded"
    assert result["media_type"] == "application/json"
    assert result["size_bytes"] == len(result["content"].encode("utf-8"))
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in result["content"]
    assert "hidden-token" not in result["content"]
    assert session_id not in result["content"]
    assert "must never leave" not in result["content"]
    assert "[REDACTED_CREDENTIAL]" in result["content"]

    document = SessionExportDocument.model_validate_json(result["content"])
    assert document.export_schema_version == "1.0"
    assert document.prediction_mode == "mock"
    assert "session_id" not in document.session.model_dump()
    assert document.selected_resources[0].resource_id == resource["resource_id"]
    assert "api_key" not in json.dumps(document.model_dump(mode="json"))

    with repository.connection() as connection:
        audit = connection.execute(
            "SELECT event_type, summary_json FROM agent_audit_events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert audit["event_type"] == "session_export_succeeded"
    assert "content" not in audit["summary_json"]
    assert "resource_id" not in audit["summary_json"]

    with pytest.raises(AgentCoreError) as replay:
        service.decide(
            session_id,
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
            correlation_id="test-export-replay",
        )
    assert replay.value.code == "ACTION_STALE"


def test_export_rejects_cross_session_and_disallowed_resources(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    owner = repository.create_session()
    stranger = repository.create_session()
    foreign = repository.put_resource(owner["session_id"], "prediction", {"prediction_mode": "real"})
    batch = repository.put_resource(stranger["session_id"], "batch_errors", {"rows": []})
    service = SessionExportService(repository)

    with pytest.raises(AgentCoreError) as cross_session:
        service.prepare(
            stranger["session_id"],
            export_format="json",
            expected_state_version=0,
            resource_ids=[foreign["resource_id"]],
        )
    assert cross_session.value.code == "RESOURCE_NOT_FOUND"

    with pytest.raises(AgentCoreError) as disallowed:
        service.prepare(
            stranger["session_id"],
            export_format="json",
            expected_state_version=0,
            resource_ids=[batch["resource_id"]],
        )
    assert disallowed.value.code == "EXPORT_RESOURCE_NOT_ALLOWED"


def test_export_rejects_when_session_changes_after_confirmation_prompt(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    repository.add_message(session["session_id"], "user", "first")
    service = SessionExportService(repository)
    proposal = service.prepare(
        session["session_id"],
        export_format="markdown",
        expected_state_version=0,
        resource_ids=[],
    )
    repository.add_message(session["session_id"], "assistant", "changed after proposal")

    with pytest.raises(AgentCoreError) as changed:
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
            correlation_id="test-export-changed",
        )
    assert changed.value.code == "EXPORT_STALE"
    assert repository.get_pending_action(
        session["session_id"], proposal["action"]["action_id"]
    )["status"] == "failed"


def test_rejecting_export_generates_no_content_or_success_audit(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    service = SessionExportService(repository)
    proposal = service.prepare(
        session["session_id"],
        export_format="json",
        expected_state_version=0,
        resource_ids=[],
    )

    result = service.decide(
        session["session_id"],
        proposal["action"]["action_id"],
        decision="reject",
        expected_state_version=0,
        correlation_id="test-export-rejected",
    )
    assert result == {
        "status": "rejected",
        "filename": None,
        "media_type": None,
        "content": None,
        "size_bytes": None,
        "schema_version": "1.0",
    }
    with repository.connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM agent_audit_events WHERE event_type = 'session_export_succeeded'"
        ).fetchone()[0] == 0


def test_export_api_prepares_then_returns_a_versioned_download(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    session = client.post("/agent/sessions").json()

    prepared = client.post(
        f"/agent/sessions/{session['session_id']}/exports",
        json={"format": "json", "expected_state_version": 0, "resource_ids": []},
    )
    assert prepared.status_code == 200
    assert prepared.headers["cache-control"] == "no-store, max-age=0"
    proposal = prepared.json()
    assert proposal["action"]["payload"] == {}
    assert proposal["schema_version"] == "1.0"

    approved = client.post(
        f"/agent/sessions/{session['session_id']}/exports/{proposal['action']['action_id']}",
        json={"decision": "approve", "expected_state_version": 0},
    )
    assert approved.status_code == 200
    assert approved.headers["cache-control"] == "no-store, max-age=0"
    result = approved.json()
    assert result["filename"] == "adme-session-export.json"
    SessionExportDocument.model_validate_json(result["content"])
    get_agent_runtime.cache_clear()


def test_export_enforces_item_and_final_byte_limits(tmp_path, monkeypatch) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    repository.add_message(session["session_id"], "user", "first")
    repository.add_message(session["session_id"], "assistant", "second")
    service = SessionExportService(repository)

    monkeypatch.setattr(session_exports, "MAX_EXPORT_MESSAGES", 1)
    with pytest.raises(AgentCoreError) as item_limit:
        service.prepare(
            session["session_id"],
            export_format="json",
            expected_state_version=0,
            resource_ids=[],
        )
    assert item_limit.value.code == "EXPORT_LIMIT_EXCEEDED"

    monkeypatch.setattr(session_exports, "MAX_EXPORT_MESSAGES", 500)
    monkeypatch.setattr(session_exports, "MAX_SESSION_EXPORT_BYTES", 100)
    proposal = service.prepare(
        session["session_id"],
        export_format="json",
        expected_state_version=0,
        resource_ids=[],
    )
    with pytest.raises(AgentCoreError) as byte_limit:
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
            correlation_id="test-export-too-large",
        )
    assert byte_limit.value.code == "EXPORT_LIMIT_EXCEEDED"


def test_export_uses_public_projections_and_discloses_bounded_activity(tmp_path, monkeypatch) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    session_id = session["session_id"]
    repository.add_message(session_id, "user", "visible")
    repository.add_message(session_id, "tool", "internal tool transcript")
    repository.put_resource(session_id, "batch_errors", {"private_batch": True})
    repository.add_audit_event(
        session_id=session_id,
        correlation_id="one",
        event_type="first",
        status="ok",
        summary={"payload": "not exported"},
    )
    repository.add_audit_event(
        session_id=session_id,
        correlation_id="two",
        event_type="second",
        status="ok",
        summary={"prompt": "not exported"},
    )
    monkeypatch.setattr(session_exports, "MAX_EXPORT_ACTIVITIES", 1)
    service = SessionExportService(repository)
    proposal = service.prepare(
        session_id,
        export_format="json",
        expected_state_version=0,
        resource_ids=[],
    )
    result = service.decide(
        session_id,
        proposal["action"]["action_id"],
        decision="approve",
        expected_state_version=0,
        correlation_id="bounded-activity",
    )
    document = SessionExportDocument.model_validate_json(result["content"])
    assert [message.content for message in document.messages] == ["visible"]
    assert document.resources == []
    assert document.activity.total_available == 2
    assert document.activity.included_count == 1
    assert document.activity.older_omitted_count == 1
    assert document.activity.events[0].event_type == "second"


def test_audit_failure_cannot_commit_a_successful_export(tmp_path) -> None:
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    service = SessionExportService(repository)
    proposal = service.prepare(
        session["session_id"],
        export_format="json",
        expected_state_version=0,
        resource_ids=[],
    )
    with repository.connection() as connection:
        connection.execute(
            """CREATE TRIGGER reject_export_audit
               BEFORE INSERT ON agent_audit_events
               WHEN NEW.event_type = 'session_export_succeeded'
               BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END"""
        )
        connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        service.decide(
            session["session_id"],
            proposal["action"]["action_id"],
            decision="approve",
            expected_state_version=0,
            correlation_id="audit-failure",
        )
    assert repository.get_pending_action(
        session["session_id"], proposal["action"]["action_id"]
    )["status"] == "failed"


def test_committed_json_schema_matches_the_executable_v1_contract() -> None:
    committed = json.loads(
        (ROOT / "docs/schemas/agent-session-export-v1.schema.json").read_text()
    )
    assert committed == SessionExportDocument.model_json_schema()
    assert committed["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert committed["additionalProperties"] is False
