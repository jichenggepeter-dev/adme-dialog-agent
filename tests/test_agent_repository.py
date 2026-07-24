from __future__ import annotations

import sqlite3

import pytest

from app.agent_runtime.confirmations import ConfirmationEngine
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository


def repository(tmp_path) -> AgentRepository:
    return AgentRepository(tmp_path / "agent.sqlite3")


def test_schema_contains_separate_state_tables(tmp_path) -> None:
    repo = repository(tmp_path)
    with repo.connection() as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "agent_sessions",
        "agent_messages",
        "agent_business_state",
        "agent_confirmations",
        "agent_pending_actions",
        "agent_resources",
        "agent_audit_events",
    } <= names


def test_messages_are_paginated(tmp_path) -> None:
    repo = repository(tmp_path)
    session = repo.create_session()
    for index in range(3):
        repo.add_message(session["session_id"], "user", f"message-{index}")
    page = repo.list_messages(session["session_id"], limit=2, offset=1)
    assert page["total"] == 3
    assert [item["content"] for item in page["messages"]] == [
        "message-1",
        "message-2",
    ]


def test_confirmation_is_single_use_and_cross_session_safe(tmp_path) -> None:
    repo = repository(tmp_path)
    engine = ConfirmationEngine(repo)
    first = repo.create_session()
    second = repo.create_session()
    confirmation = engine.propose_compound(
        first["session_id"],
        {"compound_id": "compound-1", "canonical_smiles": "CCO"},
        expected_state_version=0,
    )
    with pytest.raises(AgentCoreError) as cross_session:
        engine.decide(
            second["session_id"], confirmation["confirmation_id"], "approve", 0
        )
    assert cross_session.value.code == "ACTION_NOT_ALLOWED"

    engine.decide(first["session_id"], confirmation["confirmation_id"], "reject", 0)
    with pytest.raises(AgentCoreError) as replay:
        engine.decide(first["session_id"], confirmation["confirmation_id"], "approve", 0)
    assert replay.value.code == "CONFIRMATION_REPLAYED"


def test_resource_is_bounded_and_owned_by_session(tmp_path) -> None:
    repo = repository(tmp_path)
    first = repo.create_session()
    second = repo.create_session()
    resource = repo.put_resource(first["session_id"], "test", {"ok": True})
    assert repo.get_resource(first["session_id"], resource["resource_id"])["data"] == {
        "ok": True
    }
    with pytest.raises(AgentCoreError) as caught:
        repo.get_resource(second["session_id"], resource["resource_id"])
    assert caught.value.code == "RESOURCE_NOT_FOUND"

    with pytest.raises(AgentCoreError) as oversized:
        repo.put_resource(first["session_id"], "too-large", {"value": "x" * 300_000})
    assert oversized.value.code == "RESOURCE_TOO_LARGE"


def test_pending_action_is_hash_bound_and_single_use(tmp_path) -> None:
    repo = repository(tmp_path)
    session = repo.create_session()
    action = repo.create_pending_action(
        session["session_id"], "clear_session", {"scope": "current"}, 0
    )
    approved = repo.transition_pending_action(
        session["session_id"], action["action_id"], "approve", 0
    )
    assert approved["status"] == "approved"
    with pytest.raises(AgentCoreError) as replay:
        repo.transition_pending_action(
            session["session_id"], action["action_id"], "approve", 0
        )
    assert replay.value.code == "ACTION_STALE"


def test_pending_action_atomic_claim_and_finish_reject_replay(tmp_path) -> None:
    repo = repository(tmp_path)
    session = repo.create_session()
    action = repo.create_pending_action(
        session["session_id"], "run_batch_job", {"job_id": "job-1"}, 0
    )
    claimed = repo.approve_and_claim_pending_action(
        session["session_id"], action["action_id"], 0
    )
    assert claimed["status"] == "executing"
    finished = repo.finish_pending_action(
        session["session_id"], action["action_id"], succeeded=True
    )
    assert finished["status"] == "succeeded"
    with pytest.raises(AgentCoreError) as replay:
        repo.approve_and_claim_pending_action(
            session["session_id"], action["action_id"], 0
        )
    assert replay.value.code == "ACTION_STALE"


def test_business_state_uses_optimistic_version(tmp_path) -> None:
    repo = repository(tmp_path)
    session = repo.create_session()
    updated = repo.update_business_state(
        session["session_id"], {"current_page": "single"}, expected_version=0
    )
    assert updated["version"] == 1
    with pytest.raises(AgentCoreError) as stale:
        repo.update_business_state(
            session["session_id"], {"current_page": "about"}, expected_version=0
        )
    assert stale.value.code == "ACTION_STALE"
