from app.tools.smiles import extract_candidate_smiles, validate_smiles


ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_valid_aspirin_smiles():
    result = validate_smiles(ASPIRIN)
    assert result["is_valid"] is True
    assert result["input_smiles"] == ASPIRIN


def test_empty_smiles():
    result = validate_smiles("")
    assert result["is_valid"] is False
    assert "empty" in result["error"].lower()


def test_clearly_invalid_smiles():
    result = validate_smiles("not a smiles")
    assert result["is_valid"] is False


def test_extract_candidate_smiles_from_message():
    message = f"Predict ADME for aspirin: {ASPIRIN}"
    assert extract_candidate_smiles(message) == ASPIRIN

