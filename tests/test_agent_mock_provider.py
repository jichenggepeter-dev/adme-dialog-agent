from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.agent_runtime.provider as provider_module
import app.agent_runtime.runtime as runtime_module
import app.agent_runtime.tool_service as tool_service_module
import app.tools.admet_predictor as predictor_module
import app.tools.compound as compound_module
from app.agent_runtime.guardrails import PolicyDecision
from app.agent_runtime.mock_provider import (
    ABSENT_EVIDENCE_QUERY,
    MISSING_PREDICTION_ID,
    MOCK_SCENARIO_IDS,
)
from app.agent_runtime.routes import get_agent_runtime
from app.main import app
from app.settings import get_agent_settings


LLM_SETTING_NAMES = (
    "AGENT_LLM_BASE_URL",
    "AGENT_LLM_API_KEY",
    "AGENT_LLM_MODEL",
    "AGENT_LLM_CONNECT_TIMEOUT_SECONDS",
    "AGENT_LLM_READ_TIMEOUT_SECONDS",
    "AGENT_LLM_TOTAL_TIMEOUT_SECONDS",
)
MOCK_BOUNDARY_PARTS = ("Mock Agent v1", "not a scientific conclusion")


@pytest.fixture
def mock_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_PROVIDER_MODE", "mock")
    monkeypatch.delenv("ADME_MOCK_MODE", raising=False)
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    for name in LLM_SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()
    with TestClient(app) as client:
        yield client
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()


def _create_session(client: TestClient) -> dict[str, Any]:
    response = client.post("/agent/sessions")
    assert response.status_code == 200
    return response.json()


def _chat(
    client: TestClient,
    scenario_id: str,
    *,
    message: str = "Run the selected deterministic review scenario.",
    expected_state_version: int = 0,
):
    session = _create_session(client)
    response = client.post(
        "/agent/chat",
        json={
            "session_id": session["session_id"],
            "message": message,
            "expected_state_version": expected_state_version,
            "mock_scenario": {"catalog_version": 1, "id": scenario_id},
        },
    )
    return session, response


def _assert_mock_boundary(text: str) -> None:
    assert all(part in text for part in MOCK_BOUNDARY_PARTS)


def test_catalog_has_exactly_the_five_version_one_scenarios() -> None:
    assert MOCK_SCENARIO_IDS == (
        "success",
        "confirmation",
        "timeout",
        "tool_failure",
        "insufficient_evidence",
    )


def test_success_uses_model_information_and_does_not_infer_from_keywords(
    mock_client: TestClient,
) -> None:
    _, response = _chat(
        mock_client,
        "success",
        message="The words timeout and confirmation must not select a scenario.",
    )

    assert response.status_code == 200
    body = response.json()
    _assert_mock_boundary(body["text"])
    assert [item["tool_name"] for item in body["tool_activity"]] == [
        "get_model_information"
    ]
    assert body["tool_activity"][0]["status"] == "completed"
    assert [item["type"] for item in body["structured_payloads"]] == [
        "model_information"
    ]
    model_information = body["structured_payloads"][0]["data"]
    assert model_information["prediction_mode"] == "mock"
    assert model_information["model_loaded"] is False
    assert model_information["model_name"] == "Deterministic development fixture"


def test_confirmation_stops_then_approval_predicts_mock_output_once(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def pubchem_must_not_run(*_args, **_kwargs):
        raise AssertionError("Direct CCO must not call PubChem")

    def model_must_not_load(*_args, **_kwargs):
        raise AssertionError("Mock prediction must not load ADMET-AI")

    prediction_calls = 0
    resolved_queries: list[str] = []
    predict_single_smiles = tool_service_module.predict_single_smiles
    resolve_compound = tool_service_module.AgentToolService.resolve_compound

    def count_prediction(smiles: str, *, force_mock: bool = False) -> dict:
        nonlocal prediction_calls
        prediction_calls += 1
        return predict_single_smiles(smiles, force_mock=force_mock)

    def capture_resolve(service, query: str) -> dict:
        resolved_queries.append(query)
        return resolve_compound(service, query)

    monkeypatch.setattr(compound_module, "_fetch_pubchem", pubchem_must_not_run)
    monkeypatch.setattr(predictor_module, "get_model", model_must_not_load)
    monkeypatch.setattr(tool_service_module, "predict_single_smiles", count_prediction)
    monkeypatch.setattr(
        tool_service_module.AgentToolService,
        "resolve_compound",
        capture_resolve,
    )

    session, response = _chat(mock_client, "confirmation")

    assert response.status_code == 200
    body = response.json()
    _assert_mock_boundary(body["text"])
    assert [item["tool_name"] for item in body["tool_activity"]] == [
        "resolve_compound"
    ]
    confirmation = body["pending_confirmation"]
    assert confirmation["status"] == "awaiting_confirmation"
    assert confirmation["canonical_smiles"] == "CCO"
    assert confirmation["payload"]["agent_provider_mode"] == "mock"
    assert confirmation["payload"]["mock_catalog_version"] == 1
    assert resolved_queries == ["CCO"]
    assert prediction_calls == 0
    state = get_agent_runtime().repository.get_business_state(session["session_id"])
    assert state["state"].get("latest_prediction_id") is None

    approval = {
        "session_id": session["session_id"],
        "confirmation_id": confirmation["confirmation_id"],
        "decision": "approve",
        "expected_state_version": body["state_version"],
    }
    monkeypatch.setenv("AGENT_PROVIDER_MODE", "live")
    monkeypatch.setenv("ADME_MOCK_MODE", "false")
    approved = mock_client.post("/agent/confirm", json=approval)

    assert approved.status_code == 200
    approved_body = approved.json()
    _assert_mock_boundary(approved_body["text"])
    assert approved_body["structured_payloads"][0]["data"]["prediction_mode"] == "mock"
    assert [item["tool_name"] for item in approved_body["tool_activity"]] == [
        "predict_single_compound"
    ]
    assert prediction_calls == 1

    replay = mock_client.post("/agent/confirm", json=approval)
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "CONFIRMATION_REPLAYED"
    assert prediction_calls == 1

    monkeypatch.setenv("AGENT_PROVIDER_MODE", "mock")
    rejected_session, rejected_chat = _chat(mock_client, "confirmation")
    rejected_confirmation = rejected_chat.json()["pending_confirmation"]
    monkeypatch.setenv("AGENT_PROVIDER_MODE", "live")
    rejected = mock_client.post(
        "/agent/confirm",
        json={
            "session_id": rejected_session["session_id"],
            "confirmation_id": rejected_confirmation["confirmation_id"],
            "decision": "reject",
            "expected_state_version": rejected_chat.json()["state_version"],
        },
    )
    assert rejected.status_code == 200
    _assert_mock_boundary(rejected.json()["text"])
    assert prediction_calls == 1


def test_timeout_is_immediate_retryable_application_error(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        asyncio,
        "sleep",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Mock timeout must not sleep")
        ),
    )
    monkeypatch.setattr(
        time,
        "sleep",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Mock timeout must not sleep")
        ),
    )

    session, response = _chat(mock_client, "timeout")

    assert response.status_code == 503
    assert response.json()["error"] | {"correlation_id": "normalized"} == {
        "code": "AGENT_TIMEOUT",
        "message": "The local Agent model timed out.",
        "details": None,
        "retryable": True,
        "correlation_id": "normalized",
    }
    with get_agent_runtime().repository.connection() as connection:
        audit = connection.execute(
            "SELECT status, error_code FROM agent_audit_events "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session["session_id"],),
        ).fetchone()
    assert dict(audit) == {"status": "error", "error_code": "AGENT_TIMEOUT"}


def test_tool_failure_uses_normal_missing_prediction_error_path(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str] | None, list[str] | None]] = []
    get_prediction_results = tool_service_module.AgentToolService.get_prediction_results

    def capture_lookup(
        service,
        prediction_id: str,
        categories: list[str] | None = None,
        endpoints: list[str] | None = None,
    ) -> dict:
        calls.append((prediction_id, categories, endpoints))
        return get_prediction_results(service, prediction_id, categories, endpoints)

    monkeypatch.setattr(
        tool_service_module.AgentToolService,
        "get_prediction_results",
        capture_lookup,
    )
    _, response = _chat(mock_client, "tool_failure")

    assert response.status_code == 200
    body = response.json()
    _assert_mock_boundary(body["text"])
    assert body["tool_activity"] == [
        {
            "tool_name": "get_prediction_results",
            "status": "error",
            "error_code": "RESOURCE_NOT_FOUND",
            "resource_id": None,
        }
    ]
    assert body["structured_payloads"] == []
    assert calls == [(MISSING_PREDICTION_ID, None, None)]


def test_insufficient_evidence_returns_existing_no_evidence_payload(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []
    search_adme_evidence = tool_service_module.AgentToolService.search_adme_evidence

    def capture_search(service, query: str, top_k: int = 3) -> dict:
        calls.append((query, top_k))
        return search_adme_evidence(service, query, top_k)

    monkeypatch.setattr(
        tool_service_module.AgentToolService,
        "search_adme_evidence",
        capture_search,
    )
    _, response = _chat(mock_client, "insufficient_evidence")

    assert response.status_code == 200
    body = response.json()
    _assert_mock_boundary(body["text"])
    assert [item["tool_name"] for item in body["tool_activity"]] == [
        "search_adme_evidence"
    ]
    evidence = body["structured_payloads"][0]
    assert evidence["type"] == "evidence_answer"
    assert evidence["data"]["status"] == "no_evidence"
    assert evidence["data"]["claims"] == []
    assert evidence["data"]["evidence"] == []
    assert calls == [(ABSENT_EVIDENCE_QUERY, 3)]


def test_unexpected_tool_envelope_fails_the_scenario_stably(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tool_service_module.AgentToolService,
        "get_model_information",
        lambda _service: {"status": "error", "error_code": "FIXTURE_BROKEN"},
    )

    _, response = _chat(mock_client, "success")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "MOCK_SCENARIO_FAILED"


def test_all_scenarios_avoid_provider_network_model_loader_pubchem_and_sleep(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(name: str):
        def fail(*_args, **_kwargs):
            raise AssertionError(f"{name} must not be reached")

        return fail

    monkeypatch.setattr(runtime_module, "create_agent_provider", forbidden("live provider"))
    monkeypatch.setattr(provider_module, "AsyncOpenAI", forbidden("OpenAI client"))
    monkeypatch.setattr(predictor_module, "get_model", forbidden("ADMET-AI loader"))
    monkeypatch.setattr(compound_module, "_fetch_pubchem", forbidden("PubChem"))
    monkeypatch.setattr(asyncio, "sleep", forbidden("async sleep"))
    monkeypatch.setattr(time, "sleep", forbidden("sleep"))

    for scenario_id in MOCK_SCENARIO_IDS:
        _, response = _chat(mock_client, scenario_id)
        assert response.status_code == (503 if scenario_id == "timeout" else 200)


@pytest.mark.parametrize(
    ("provider_mode", "scenario", "expected_code"),
    [
        ("mock", None, "MOCK_SCENARIO_REQUIRED"),
        (
            "mock",
            {"catalog_version": 2, "id": "success"},
            "MOCK_SCENARIO_VERSION_UNSUPPORTED",
        ),
        (
            "mock",
            {"catalog_version": 1, "id": "unknown"},
            "MOCK_SCENARIO_UNKNOWN",
        ),
        (
            "live",
            {"catalog_version": 1, "id": "success"},
            "MOCK_SCENARIO_NOT_ALLOWED",
        ),
    ],
)
def test_scenario_mode_errors_have_stable_codes(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    provider_mode: str,
    scenario: dict[str, Any] | None,
    expected_code: str,
) -> None:
    monkeypatch.setenv("AGENT_PROVIDER_MODE", provider_mode)
    get_agent_settings.cache_clear()
    session = _create_session(mock_client)
    payload = {
        "session_id": session["session_id"],
        "message": "Run a bounded scenario.",
        "expected_state_version": 0,
    }
    if scenario is not None:
        payload["mock_scenario"] = scenario

    response = mock_client.post("/agent/chat", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["retryable"] is False


def test_mock_scenario_shape_remains_strict(mock_client: TestClient) -> None:
    session = _create_session(mock_client)
    response = mock_client.post(
        "/agent/chat",
        json={
            "session_id": session["session_id"],
            "message": "Run a bounded scenario.",
            "expected_state_version": 0,
            "mock_scenario": {
                "catalog_version": 1,
                "id": "success",
                "arbitrary_tool": "shell",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_mock_mode_preserves_input_guardrail_and_stale_state(
    mock_client: TestClient,
) -> None:
    _, guarded = _chat(
        mock_client,
        "success",
        message="What dose should this patient take?",
    )
    assert guarded.status_code == 200
    guarded_body = guarded.json()
    _assert_mock_boundary(guarded_body["text"])
    assert guarded_body["structured_payloads"] == [
        {"type": "out_of_scope", "data": {"error_code": "OUT_OF_SCOPE"}}
    ]
    assert guarded_body["tool_activity"] == []

    _, stale = _chat(mock_client, "success", expected_state_version=1)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ACTION_STALE"


def test_mock_mode_preserves_output_guardrail_messages_and_audit(
    mock_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def block_output(_text: str, _payloads: list[dict[str, Any]]) -> PolicyDecision:
        nonlocal calls
        calls += 1
        return PolicyDecision(
            False,
            "SCIENTIFIC_POLICY_VIOLATION",
            "The fixed output guardrail blocked this response.",
        )

    monkeypatch.setattr(runtime_module, "validate_scientific_output", block_output)

    session, response = _chat(mock_client, "success")

    assert response.status_code == 200
    body = response.json()
    _assert_mock_boundary(body["text"])
    assert body["structured_payloads"] == [
        {
            "type": "error",
            "data": {"error_code": "SCIENTIFIC_POLICY_VIOLATION"},
        }
    ]
    assert calls == 1
    messages = get_agent_runtime().repository.list_messages(
        session["session_id"], 20, 0
    )["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    with get_agent_runtime().repository.connection() as connection:
        audit = connection.execute(
            "SELECT status, error_code FROM agent_audit_events "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session["session_id"],),
        ).fetchone()
    assert dict(audit) == {
        "status": "blocked",
        "error_code": "SCIENTIFIC_POLICY_VIOLATION",
    }


@pytest.mark.parametrize("scenario_id", MOCK_SCENARIO_IDS)
def test_semantically_identical_streams_have_equal_normalized_transcripts(
    mock_client: TestClient,
    scenario_id: str,
) -> None:
    first = _stream(mock_client, scenario_id)
    second = _stream(mock_client, scenario_id)

    assert _normalize(first) == _normalize(second)
    assert [event["sequence"] for event in first] == list(range(len(first)))
    _assert_event_type_order(first, scenario_id)
    terminal = [event for event in first if event["type"] in {"response_completed", "error"}]
    assert len(terminal) == 1


def _assert_event_type_order(events: list[dict[str, Any]], scenario_id: str) -> None:
    event_types = [event["type"] for event in events]
    assert event_types.count("heartbeat") == 1
    if scenario_id == "timeout":
        assert event_types == ["heartbeat", "error"]
        return

    assert event_types[:2] == ["heartbeat", "tool_completed"]
    assert event_types[-1] == "response_completed"
    message_types = event_types[2:-1]
    if scenario_id == "confirmation":
        assert message_types[-1] == "confirmation_required"
        message_types = message_types[:-1]
    assert message_types
    assert set(message_types) == {"message_delta"}


def _stream(client: TestClient, scenario_id: str) -> list[dict[str, Any]]:
    session = _create_session(client)
    response = client.post(
        "/agent/chat/stream",
        headers={"X-Correlation-ID": "normalization-test"},
        json={
            "session_id": session["session_id"],
            "message": "Run the selected deterministic review scenario.",
            "expected_state_version": 0,
            "mock_scenario": {"catalog_version": 1, "id": scenario_id},
        },
    )
    assert response.status_code == 200
    return [json.loads(line) for line in response.text.splitlines() if line]


DYNAMIC_KEYS = {
    "session_id",
    "message_id",
    "correlation_id",
    "confirmation_id",
    "compound_id",
    "prediction_id",
    "resource_id",
    "raw_predictions_resource_id",
    "prediction_resource_id",
    "payload_hash",
    "created_at",
    "expires_at",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in sorted(value.items())
            if key not in DYNAMIC_KEYS
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value
