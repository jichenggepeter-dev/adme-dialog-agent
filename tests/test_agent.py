from app.agent import handle_chat_message


ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_message_with_valid_smiles_returns_result(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    response = handle_chat_message(f"Predict ADME properties for aspirin: {ASPIRIN}")
    assert response["detected_smiles"] == ASPIRIN
    assert response["result"] is not None
    assert "absorption" in response["result"]["predictions"]


def test_message_without_smiles_asks_user_to_provide_one(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    response = handle_chat_message("Can you predict this molecule?")
    assert response["result"] is None
    assert "Please provide" in response["message"]


def test_invalid_smiles_returns_error(monkeypatch):
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    response = handle_chat_message("Predict ADME for C1CC")
    assert response["result"] is None
    assert "could not be validated" in response["message"]

