from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.agent_runtime.routes import get_agent_runtime
from app.main import app
from app.settings import get_agent_settings


pytestmark = pytest.mark.agent_llm_integration


@pytest.mark.skipif(
    os.getenv("RUN_AGENT_LLM_INTEGRATION", "").lower() not in {"1", "true", "yes"},
    reason="Set RUN_AGENT_LLM_INTEGRATION=true with the local Codex API running.",
)
def test_real_agent_api_stops_for_confirmation_then_predicts(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()
    client = TestClient(app)

    session_response = client.post("/agent/sessions")
    assert session_response.status_code == 200
    session = session_response.json()
    chat_response = client.post(
        "/agent/chat",
        json={
            "session_id": session["session_id"],
            "message": (
                "Predict ADME for this valid SMILES. Resolve it first and stop for "
                "structure confirmation: CC(=O)OC1=CC=CC=C1C(=O)O"
            ),
            "expected_state_version": 0,
        },
    )
    assert chat_response.status_code == 200
    chat = chat_response.json()
    assert chat["pending_confirmation"] is not None
    assert [item["tool_name"] for item in chat["tool_activity"]] == [
        "resolve_compound"
    ]
    state = get_agent_runtime().repository.get_business_state(session["session_id"])
    assert state["state"].get("latest_prediction_id") is None

    confirmation = chat["pending_confirmation"]
    confirm_response = client.post(
        "/agent/confirm",
        json={
            "session_id": session["session_id"],
            "confirmation_id": confirmation["confirmation_id"],
            "decision": "approve",
            "expected_state_version": chat["state_version"],
        },
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["tool_activity"][0]["tool_name"] == "predict_single_compound"
    assert confirmed["structured_payloads"][0]["data"]["prediction_mode"] == "mock"
    assert confirmed["text"].startswith("Mock mode:")
    get_agent_runtime.cache_clear()
