from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import app.agent_runtime.tool_service as tool_service_module
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.guardrails import validate_scientific_output
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.tool_service import AgentToolService, ToolExecutionContext
from app.services.comparison import compare_prediction_payloads
from app.agent_runtime.routes import get_agent_runtime
from app.main import app


ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def _resolved(_: str) -> dict:
    return {
        "input_query": "aspirin", "preferred_name": "Aspirin", "pubchem_cid": 2244,
        "molecular_formula": "C9H8O4", "molecular_weight": 180.16,
        "canonical_smiles": ASPIRIN, "isomeric_smiles": ASPIRIN,
        "data_source": "test", "depiction_svg": "<svg />", "warnings": [],
    }


def _propose(repo: AgentRepository, monkeypatch: pytest.MonkeyPatch):
    session = repo.create_session()
    monkeypatch.setattr(tool_service_module, "resolve_compound", _resolved)
    context = ToolExecutionContext(session["session_id"], repo, 0)
    AgentToolService(context).resolve_compound("aspirin")
    return session, context


def test_confirmation_claim_is_atomic_and_recoverable(tmp_path, monkeypatch) -> None:
    repo = AgentRepository(tmp_path / "agent.sqlite3")
    session, context = _propose(repo, monkeypatch)
    confirmation_id = context.pending_confirmation["confirmation_id"]

    def claim():
        try:
            value, _ = repo.approve_and_claim_confirmation(
                session["session_id"], confirmation_id, context.state_version
            )
            return value["status"]
        except AgentCoreError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: claim(), range(2)))
    assert sorted(outcomes) == ["CONFIRMATION_REPLAYED", "executing"]
    repo.finish_confirmation(
        session["session_id"], confirmation_id,
        resource_id="resource_result", error_code=None,
    )
    recovered = repo.get_confirmation(session["session_id"], confirmation_id)
    assert recovered["status"] == "succeeded"
    assert recovered["result_resource_id"] == "resource_result"


def test_cross_session_and_expired_session_cannot_read_resources_or_messages(tmp_path) -> None:
    repo = AgentRepository(tmp_path / "agent.sqlite3")
    owner = repo.create_session()
    stranger = repo.create_session()
    resource = repo.put_resource(owner["session_id"], "test", {"secret": True})
    repo.add_message(owner["session_id"], "user", "private")
    with pytest.raises(AgentCoreError):
        repo.get_resource(stranger["session_id"], resource["resource_id"])
    assert repo.list_messages(stranger["session_id"], 50, 0)["messages"] == []
    with repo.connection() as connection:
        connection.execute(
            "UPDATE agent_sessions SET expires_at=? WHERE session_id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), owner["session_id"]),
        )
        connection.commit()
    with pytest.raises(AgentCoreError):
        repo.get_resource(owner["session_id"], resource["resource_id"])


@pytest.mark.parametrize("claim", [
    "This is a real ADMET-AI output.",
    "The result was experimentally measured.",
    "This is the safer and better compound.",
    "The predicted risk is 67%.",
    "Clearance is 12 mg/kg.",
])
def test_scientific_guardrail_blocks_unsupported_claims(claim: str) -> None:
    decision = validate_scientific_output(
        claim,
        [{"type": "prediction", "data": {"prediction_mode": "mock"}}],
    )
    assert decision.allowed is False
    assert decision.code == "SCIENTIFIC_POLICY_VIOLATION"


def test_scientific_guardrail_allows_supported_absorption_explanation() -> None:
    payload = {
        "type": "prediction",
        "data": {
            "prediction_mode": "real",
            "enriched_predictions": {
                "absorption": [
                    {
                        "display_name": "Oral Bioavailability",
                        "positive_class": "Oral Bioavailability",
                        "supports_probability_language": True,
                        "unit": None,
                        "unit_verified": True,
                    },
                    {
                        "display_name": "Cell Effective Permeability",
                        "supports_probability_language": False,
                        "unit": "log(10^-6 cm/s)",
                        "unit_verified": True,
                    },
                ]
            },
        },
    }
    explanation = (
        "Oral Bioavailability returned a model probability of 0.833 for the "
        "documented positive class. Caco-2 permeability was -5.44 cm/s. "
        "Review the endpoint metadata to better understand the result."
    )
    assert validate_scientific_output(explanation, [payload]).allowed is True


def test_prediction_result_tool_exposes_facts_to_output_guardrail(tmp_path) -> None:
    repo = AgentRepository(tmp_path / "agent.sqlite3")
    session = repo.create_session()
    prediction_id = "prediction_test"
    resource = repo.put_resource(
        session["session_id"],
        "prediction",
        {
            "prediction_mode": "real",
            "warnings": [],
            "disclaimer": "Computational prediction only.",
            "enriched_predictions": {
                "absorption": [
                    {
                        "raw_name": "HIA_Hou",
                        "display_name": "Human Intestinal Absorption",
                        "value": 0.9,
                        "positive_class": "Human Intestinal Absorption",
                        "supports_probability_language": True,
                        "unit": None,
                        "unit_verified": True,
                    }
                ]
            },
        },
    )
    updated = repo.update_business_state(
        session["session_id"],
        {"predictions": {prediction_id: resource["resource_id"]}},
        expected_version=0,
    )
    context = ToolExecutionContext(
        session["session_id"], repo, updated["version"]
    )
    result = AgentToolService(context).get_prediction_results(
        prediction_id, ["absorption"], None
    )

    assert result["status"] == "ok"
    assert context.structured_payloads[0]["type"] == "prediction"
    facts = context.structured_payloads[0]["data"]["enriched_predictions"]
    assert facts["absorption"][0]["raw_name"] == "HIA_Hou"


def test_tool_service_blocks_identical_and_alternating_loops(tmp_path) -> None:
    repo = AgentRepository(tmp_path / "agent.sqlite3")
    session = repo.create_session()
    context = ToolExecutionContext(session["session_id"], repo, 0)
    service = AgentToolService(context)
    assert service.explain_endpoint("hERG")["status"] == "ok"
    assert service.explain_endpoint("hERG")["status"] == "ok"
    repeated = service.explain_endpoint("hERG")
    assert repeated["error_code"] == "AGENT_TOOL_LOOP"
    assert context.blocked is True


def test_comparison_marks_mode_and_unit_mismatches_without_ranking() -> None:
    def prediction(identifier: str, mode: str, unit: str):
        return {
            "prediction_id": identifier, "compound_id": identifier,
            "prediction_mode": mode, "model_metadata": {"model_version": "1"},
            "enriched_predictions": {"absorption": [{
                "raw_name": "Caco2", "value": 1.0, "output_type": "regression",
                "unit": unit, "unit_verified": True, "metadata_status": "verified",
            }]},
        }
    result = compare_prediction_payloads([
        prediction("one", "mock", "cm/s"), prediction("two", "real", "m/s")
    ])
    endpoint = result["endpoint_compatibility"][0]
    assert endpoint["comparable"] is False
    assert set(endpoint["reasons"]) >= {"verified_unit_mismatch", "prediction_mode_mismatch"}
    assert result["ranking"] is None and result["winner"] is None


def test_agent_disabled_does_not_create_database(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "must-not-exist.sqlite3"
    monkeypatch.setenv("AGENT_ENABLED", "false")
    monkeypatch.setenv("AGENT_DB_PATH", str(db_path))
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.post("/predict", json={"smiles": ASPIRIN}).status_code == 200
    response = client.post("/agent/sessions")
    assert response.status_code == 503
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details", "retryable", "correlation_id"}
    assert error["retryable"] is False
    assert not db_path.exists()
    get_agent_runtime.cache_clear()
