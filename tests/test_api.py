from fastapi.testclient import TestClient

from app.main import app


ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_does_not_load_model(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["prediction_mode"] == "mock"
    assert response.json()["model_loaded"] is False


def test_resolve_smiles():
    client = TestClient(app)
    response = client.post("/compound/resolve", json={"query": ASPIRIN})
    assert response.status_code == 200
    assert response.json()["molecular_formula"] == "C9H8O4"
    assert "<svg" in response.json()["depiction_svg"]


def test_endpoints_registry():
    client = TestClient(app)
    response = client.get("/endpoints")
    assert response.status_code == 200
    assert response.json()["endpoints"]["Caco2_Wang"]["prediction_type"] == "regression"


def test_predict(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.post("/predict", json={"smiles": ASPIRIN})
    assert response.status_code == 200
    payload = response.json()
    assert payload["input_smiles"] == ASPIRIN
    assert "absorption" in payload["predictions"]
    assert payload["prediction_mode"] == "mock"


def test_invalid_smiles_has_structured_error(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.post("/predict", json={"smiles": "not a smiles"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SMILES"


def test_invalid_request_has_structured_error(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.post("/predict", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_chat(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.post("/chat", json={"message": f"Predict ADME properties for aspirin: {ASPIRIN}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_smiles"] == ASPIRIN
    assert payload["result"] is not None


def test_predict_batch(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    client = TestClient(app)
    response = client.post(
        "/predict/batch",
        json={"smiles_list": [ASPIRIN, "O=C(O)c1ccccc1", "not a smiles"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 3
    assert "predictions" in payload["results"][0]
    assert "predictions" in payload["results"][1]
    assert "error" in payload["results"][2]
