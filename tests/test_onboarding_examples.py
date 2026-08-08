from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent_runtime.mock_provider import (
    MOCK_CATALOG_VERSION,
    MOCK_SCENARIO_IDS,
    SUPPORTED_EVIDENCE_QUERY,
)
from app.agent_runtime.routes import get_agent_runtime
from app.main import app
from app.services.evidence import EvidenceService
from app.tools import batch


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = json.loads(
    (ROOT / "examples" / "onboarding" / "workflows.json").read_text(
        encoding="utf-8"
    )
)


def test_single_onboarding_example_matches_mock_api(monkeypatch) -> None:
    example = WORKFLOWS["single"]
    expected = example["expected"]
    assert WORKFLOWS["schema_version"] == 1
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)

    compound = client.post("/compound/resolve", json={"query": example["query"]})
    prediction = client.post("/predict", json={"smiles": example["query"]})

    assert compound.status_code == 200
    assert prediction.status_code == 200
    assert compound.json()["preferred_name"] == expected["preferred_name"]
    assert compound.json()["molecular_formula"] == expected["molecular_formula"]
    assert compound.json()["canonical_smiles"] == expected["canonical_smiles"]
    assert prediction.json()["prediction_mode"] == expected["prediction_mode"]
    assert expected["prediction_category"] in prediction.json()["predictions"]


def test_batch_onboarding_example_matches_validation_and_run(
    tmp_path: Path, monkeypatch
) -> None:
    example = WORKFLOWS["batch"]
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    monkeypatch.setattr(batch, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(batch, "JOB_ROOT", tmp_path / "jobs")
    sample = ROOT / example["file"]

    upload = batch.create_upload(sample.name, sample.read_bytes())
    job = batch.create_job(upload["upload_id"], example["mapping"])
    batch.run_job(job["job_id"])
    completed = batch.get_job(job["job_id"])

    assert job["summary"] == example["expected_summary"]
    assert completed["status"] == example["expected_final_status"]


def test_assistant_onboarding_example_requires_confirmation_then_runs_mock(
    tmp_path: Path, monkeypatch
) -> None:
    example = WORKFLOWS["assistant"]
    expected = example["expected"]
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("AGENT_PROVIDER_MODE", "mock")
    monkeypatch.setenv("AGENT_DB_PATH", str(tmp_path / "agent.sqlite3"))
    get_agent_runtime.cache_clear()
    client = TestClient(app)
    session = client.post("/agent/sessions").json()

    response = client.post(
        "/agent/chat",
        json={
            "session_id": session["session_id"],
            "message": example["message"],
            "expected_state_version": 0,
            "mock_scenario": {
                "catalog_version": example["catalog_version"],
                "id": example["scenario_id"],
            },
        },
    )
    body = response.json()
    confirmation = body["pending_confirmation"]

    assert example["catalog_version"] == MOCK_CATALOG_VERSION
    assert confirmation["canonical_smiles"] == expected["canonical_smiles"]
    assert confirmation["status"] == expected["status_before_decision"]
    prediction_before_decision = any(
        item["type"] == "prediction" for item in body["structured_payloads"]
    )
    assert prediction_before_decision is expected["prediction_before_decision"]

    approved = client.post(
        "/agent/confirm",
        json={
            "session_id": session["session_id"],
            "confirmation_id": confirmation["confirmation_id"],
            "decision": "approve",
            "expected_state_version": body["state_version"],
        },
    ).json()
    prediction = next(
        item["data"]
        for item in approved["structured_payloads"]
        if item["type"] == "prediction"
    )
    assert prediction["prediction_mode"] == expected["prediction_mode_after_approval"]
    get_agent_runtime.cache_clear()


def test_evidence_onboarding_example_matches_approved_corpus() -> None:
    example = WORKFLOWS["evidence"]
    expected = example["expected"]
    result = EvidenceService().search(example["query"])

    assert example["catalog_version"] == MOCK_CATALOG_VERSION
    assert example["scenario_id"] in MOCK_SCENARIO_IDS
    assert example["query"] == SUPPORTED_EVIDENCE_QUERY
    assert result["status"] == expected["status"]
    assert result["evidence"][0]["source_id"] == expected["source_id"]
    assert result["evidence"][0]["title"] == expected["source_title"]
