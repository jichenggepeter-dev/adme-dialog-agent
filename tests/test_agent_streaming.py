from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

import app.agent_runtime.runtime as runtime_module
from app.agent_runtime.contracts import (
    AgentChatRequest,
    AgentStreamEvent,
)
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.routes import get_agent_runtime
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.streaming import response_events, stream_agent_chat
from app.main import app
from app.tools import batch


STREAM_IDENTITY = {
    "session_id": "session_test",
    "message_id": "msg_test",
    "correlation_id": "corr_test",
}


def _response(text: str = "Validated computational guidance.") -> dict:
    return {
        "message_id": STREAM_IDENTITY["message_id"],
        "text": text,
        "structured_payloads": [],
        "pending_confirmation": None,
        "pending_action": None,
        "tool_activity": [],
        "ui_action_proposals": [],
        "warnings": [],
        "state_version": 0,
    }


async def _collect(
    runtime: AgentRuntime,
    request: AgentChatRequest,
    *,
    message_id: str = "msg_stream",
    correlation_id: str = "corr_stream",
) -> list[dict]:
    events: list[dict] = []
    iterator: AsyncIterator[bytes] = stream_agent_chat(
        runtime,
        request,
        message_id=message_id,
        correlation_id=correlation_id,
    )
    async for line in iterator:
        events.append(json.loads(line))
    return events


def _terminal_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event["type"] in {"response_completed", "error"}]


def test_stream_event_union_is_strict_and_confirmation_is_bounded() -> None:
    adapter = TypeAdapter(AgentStreamEvent)
    valid = {
        "version": 1,
        "type": "heartbeat",
        **STREAM_IDENTITY,
        "sequence": 0,
    }
    assert adapter.validate_python(valid).sequence == 0
    with pytest.raises(ValidationError):
        adapter.validate_python({**valid, "provider_prompt": "secret"})
    with pytest.raises(ValidationError):
        adapter.validate_python({**valid, "version": 2})
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                **valid,
                "type": "confirmation_required",
                "pending_confirmation": None,
                "pending_action": None,
            }
        )


def test_response_events_are_deterministic_monotonic_and_reassemble_text() -> None:
    text = "A validated answer with enough text to require deterministic chunks. " * 3
    response = _response(text)
    response["tool_activity"] = [
        {
            "tool_name": "explain_endpoint",
            "status": "completed",
            "error_code": None,
            "resource_id": "resource_1",
        }
    ]
    events = list(
        response_events(
            response,
            **STREAM_IDENTITY,
            start_sequence=1,
        )
    )
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert events[0].type == "tool_completed"
    assert "".join(
        event.delta for event in events if event.type == "message_delta"
    ) == text
    assert events[-1].type == "response_completed"
    assert sum(event.type in {"response_completed", "error"} for event in events) == 1
    for event in events:
        assert event.version == 1
        assert event.session_id == STREAM_IDENTITY["session_id"]
        assert event.message_id == STREAM_IDENTITY["message_id"]
        assert event.correlation_id == STREAM_IDENTITY["correlation_id"]


def test_stream_route_preserves_non_streaming_runtime_and_persisted_message_id(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    session = client.post("/agent/sessions").json()

    response = client.post(
        "/agent/chat/stream",
        headers={"X-Correlation-ID": "corr_route_test"},
        json={
            "session_id": session["session_id"],
            "message": "把 ibuprofen 填入输入框，但先不要运行。",
            "expected_state_version": 0,
            "page_context": {"page": "single"},
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert [event["sequence"] for event in events] == list(range(len(events)))
    assert events[0]["type"] == "heartbeat"
    assert events[-1]["type"] == "response_completed"
    assert len(_terminal_events(events)) == 1
    assert {event["correlation_id"] for event in events} == {"corr_route_test"}
    assert len({event["message_id"] for event in events}) == 1
    assert "".join(
        event["delta"] for event in events if event["type"] == "message_delta"
    ).startswith("我会把 ibuprofen")
    assert events[-1]["ui_action_proposals"][0]["type"] == "SET_COMPOUND_INPUT"

    history = client.get(
        f"/agent/sessions/{session['session_id']}/messages"
    ).json()["messages"]
    assistant = [message for message in history if message["role"] == "assistant"]
    assert assistant[0]["message_id"] == events[0]["message_id"]
    get_agent_runtime.cache_clear()


def test_policy_blocked_stream_has_deltas_and_one_completion(tmp_path) -> None:
    class RunnerThatMustNotRun:
        async def run(self, *args, **kwargs):
            raise AssertionError("Policy-blocked input must not invoke the model")

    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    runtime = AgentRuntime(repository, runner=RunnerThatMustNotRun())
    events = asyncio.run(
        _collect(
            runtime,
            AgentChatRequest(
                session_id=session["session_id"],
                message="What dosage should this patient take?",
                expected_state_version=0,
            ),
        )
    )

    assert events[0]["type"] == "heartbeat"
    assert events[-1]["type"] == "response_completed"
    assert len(_terminal_events(events)) == 1
    assert "patient" in "".join(
        event["delta"] for event in events if event["type"] == "message_delta"
    ).lower()
    assert events[-1]["structured_payloads"] == [
        {"type": "out_of_scope", "data": {"error_code": "OUT_OF_SCOPE"}}
    ]


def test_confirmation_required_stream_does_not_run_batch_prediction(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(batch, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(batch, "JOB_ROOT", tmp_path / "jobs")
    upload = batch.create_upload("batch.csv", b"id,smiles\n1,CCO\n")
    job = batch.create_job(
        upload["upload_id"],
        {"smiles": "smiles", "compound_id": "id", "compound_name": None},
    )

    def must_not_run(_: str) -> dict:
        raise AssertionError("Streaming a pending action must not execute it")

    monkeypatch.setattr(runtime_module, "run_job_thread", must_not_run)
    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    runtime = AgentRuntime(repository)
    events = asyncio.run(
        _collect(
            runtime,
            AgentChatRequest(
                session_id=session["session_id"],
                message="Run this batch",
                expected_state_version=0,
                page_context={
                    "page": "batch",
                    "batch_job_id": job["job_id"],
                    "selected_compound_ids": [],
                    "selected_row_numbers": [],
                    "selected_endpoints": [],
                },
            ),
        )
    )

    confirmation_events = [
        event for event in events if event["type"] == "confirmation_required"
    ]
    assert len(confirmation_events) == 1
    assert confirmation_events[0]["pending_confirmation"] is None
    assert confirmation_events[0]["pending_action"]["action_type"] == "run_batch_job"
    assert batch.get_job(job["job_id"])["status"] == "ready"
    assert events[-1]["type"] == "response_completed"
    assert len(_terminal_events(events)) == 1


def test_internal_failure_is_a_single_stable_public_error(tmp_path) -> None:
    class FailingRuntime(AgentRuntime):
        async def chat(self, request, **kwargs):
            raise RuntimeError("database password=do-not-expose")

    repository = AgentRepository(tmp_path / "agent.sqlite3")
    session = repository.create_session()
    events = asyncio.run(
        _collect(
            FailingRuntime(repository),
            AgentChatRequest(
                session_id=session["session_id"],
                message="Explain the model.",
                expected_state_version=0,
            ),
        )
    )

    assert [event["type"] for event in events] == ["heartbeat", "error"]
    assert len(_terminal_events(events)) == 1
    error = events[-1]
    assert error == {
        "version": 1,
        "type": "error",
        "session_id": session["session_id"],
        "message_id": "msg_stream",
        "correlation_id": "corr_stream",
        "sequence": 1,
        "code": "INTERNAL_ERROR",
        "message": "The Agent request could not be completed.",
        "retryable": False,
    }
    assert "password" not in json.dumps(error).lower()
