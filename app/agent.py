from __future__ import annotations

from app.services.prediction import PredictionServiceError, predict_single_smiles
from app.tools.smiles import extract_candidate_smiles, validate_smiles


def predict_adme(smiles: str) -> dict:
    try:
        result = predict_single_smiles(smiles)
    except PredictionServiceError as exc:
        return {
            "error": str(exc),
            "validation": exc.validation,
        }
    # Preserve the legacy response contract while the neutral service retains richer data.
    return {
        key: result[key]
        for key in (
            "input_smiles",
            "canonical_smiles",
            "predictions",
            "enriched_predictions",
            "summary",
            "disclaimer",
            "prediction_mode",
        )
    }


def handle_chat_message(message: str) -> dict:
    candidate = extract_candidate_smiles(message)
    if candidate is None:
        return {
            "message": "Please provide a valid SMILES string for the small molecule you want to evaluate.",
            "detected_smiles": None,
            "result": None,
        }

    validation = validate_smiles(candidate)
    if not validation["is_valid"]:
        return {
            "message": f"I found a possible SMILES string, but it could not be validated: {validation['error']}",
            "detected_smiles": candidate,
            "result": None,
        }

    result = predict_adme(validation["canonical_smiles"] or candidate)

    return {
        "message": "Here are the computational ADME/ADMET predictions for the detected molecule.",
        "detected_smiles": candidate,
        "result": result,
    }
