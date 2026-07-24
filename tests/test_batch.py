from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools import batch


@pytest.fixture(autouse=True)
def isolated_batch_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(batch, "JOB_ROOT", tmp_path / "jobs")


def _upload(client: TestClient, content: str, filename: str = "batch.csv") -> dict:
    response = client.post("/batch/upload", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 200
    return response.json()


def _job(client: TestClient, upload: dict, mapping: dict | None = None) -> dict:
    response = client.post("/batch/jobs", json={"upload_id": upload["upload_id"], "mapping": mapping or {"smiles": "smiles", "compound_id": "id", "compound_name": "name"}})
    assert response.status_code == 200
    return response.json()


def test_csv_tsv_and_smi_parsing():
    columns, rows, kind = batch.parse_batch_file("a.csv", b"id,smiles\n1,CCO\n")
    assert (columns, kind, rows[0]["smiles"]) == (["id", "smiles"], "csv", "CCO")
    assert batch.parse_batch_file("a.tsv", b"id\tsmiles\n1\tCCO\n")[2] == "tsv"
    assert batch.parse_batch_file("a.smi", b"CCO Ethanol\n")[0] == ["smiles", "name"]


def test_upload_rejects_unsupported_type():
    with pytest.raises(batch.BatchError, match="CSV"):
        batch.parse_batch_file("a.xlsx", b"content")


def test_mapping_validation_duplicate_and_missing_rows():
    client = TestClient(app)
    upload = _upload(client, "id,name,smiles\n1,A,CCO\n2,B,CCO\n3,C,C1(CC\n4,D,\n")
    job = _job(client, upload)
    assert job["summary"] == {"total_rows": 4, "valid_molecules": 2, "invalid_smiles": 1, "missing_smiles": 1, "duplicate_molecules": 1, "unique_valid_molecules": 1}
    assert [row["validation_status"] for row in job["rows"]] == ["valid", "duplicate", "invalid_smiles", "missing_smiles"]


def test_missing_mapping_and_no_valid_molecules():
    client = TestClient(app)
    upload = _upload(client, "id,smiles\n1,\n")
    missing = client.post("/batch/jobs", json={"upload_id": upload["upload_id"], "mapping": {"smiles": ""}})
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "MISSING_SMILES_COLUMN"
    response = client.post("/batch/jobs", json={"upload_id": upload["upload_id"], "mapping": {"smiles": "smiles"}})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_VALID_MOLECULES"


def test_batch_job_run_progress_and_duplicate_mapping():
    client = TestClient(app)
    job = _job(client, _upload(client, "id,name,smiles\n1,A,CCO\n2,B,CCO\n3,C,O\n"))
    assert client.post(f"/batch/jobs/{job['job_id']}/run").status_code == 200
    for _ in range(100):
        current = client.get(f"/batch/jobs/{job['job_id']}").json()
        if current["status"] in batch.TERMINAL_STATES:
            break
        time.sleep(0.01)
    assert current["status"] == "completed"
    assert current["progress"] == {"processed": 2, "total": 2, "completed": 2, "failed": 0}
    assert current["rows"][0]["predictions"] == current["rows"][1]["predictions"]


def test_partial_failure(monkeypatch):
    client = TestClient(app)
    job = _job(client, _upload(client, "id,name,smiles\n1,A,CCO\n2,B,O\n"))
    original = batch.predict_one
    monkeypatch.setattr(batch, "predict_one", lambda smiles: (_ for _ in ()).throw(batch.ADMETPredictionError("failed")) if smiles == "O" else original(smiles))
    batch.run_job(job["job_id"])
    current = batch.get_job(job["job_id"])
    assert current["status"] == "completed_with_errors"
    assert current["progress"]["failed"] == 1


def test_cancellation_and_job_not_found():
    client = TestClient(app)
    job = _job(client, _upload(client, "id,name,smiles\n1,A,CCO\n"))
    assert client.post(f"/batch/jobs/{job['job_id']}/cancel").json()["status"] == "cancelled"
    missing = client.get("/batch/jobs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404


def test_exports_and_formula_injection_protection():
    client = TestClient(app)
    job = _job(client, _upload(client, "id,name,smiles\n=CMD,+Name,CCO\n"))
    batch.run_job(job["job_id"])
    exported = client.get(f"/batch/jobs/{job['job_id']}/export?kind=results")
    assert exported.status_code == 200
    assert "'=CMD" in exported.text and "'+Name" in exported.text
    assert client.get(f"/batch/jobs/{job['job_id']}/errors").status_code == 200
    assert client.get(f"/batch/jobs/{job['job_id']}/export?kind=metadata").headers["content-type"].startswith("application/json")


def test_endpoint_detail_and_expanded_status():
    client = TestClient(app)
    status = client.get("/status").json()
    assert status["execution_environment"] == "local"
    assert status["model_version"] is None
    endpoint = client.get("/endpoints/Caco2_Wang").json()
    assert endpoint["raw_key"] == "Caco2_Wang"
    assert endpoint["metadata_status"] == "partial"
