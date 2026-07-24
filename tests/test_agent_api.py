from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent_runtime.routes import get_agent_runtime
from app.main import app
from app.settings import get_agent_settings


def test_enabled_session_history_and_bounded_resource_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_runtime.cache_clear()
    client = TestClient(app)

    created = client.post("/agent/sessions")
    assert created.status_code == 200
    session = created.json()
    assert session["state_version"] == 0

    fetched = client.get(f"/agent/sessions/{session['session_id']}")
    assert fetched.status_code == 200
    history = client.get(f"/agent/sessions/{session['session_id']}/messages")
    assert history.status_code == 200
    assert history.json()["messages"] == []

    runtime = get_agent_runtime()
    resource = runtime.resources.put(session["session_id"], "test", {"ok": True})
    response = client.get(
        f"/agent/resources/{resource['resource_id']}",
        params={"session_id": session["session_id"]},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True}
    get_agent_runtime.cache_clear()


def test_enabled_chat_reports_missing_model_without_breaking_session(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    monkeypatch.setenv("AGENT_LLM_MODEL", "")
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    session = client.post("/agent/sessions").json()
    response = client.post(
        "/agent/chat",
        json={
            "session_id": session["session_id"],
            "message": "Explain the current model.",
            "expected_state_version": 0,
        },
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AGENT_NOT_CONFIGURED"
    assert client.get("/health").status_code == 200
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()
