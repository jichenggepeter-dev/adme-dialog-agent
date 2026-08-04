from __future__ import annotations

from typing import Any

from app.formatter import (
    DISCLAIMER,
    generate_summary,
    group_enriched_predictions,
    group_predictions,
)
from app.tools.admet_predictor import (
    ADMETPredictionError,
    is_mock_mode,
    predict_one,
    predictor_status,
)
from app.tools.smiles import validate_smiles


class PredictionServiceError(RuntimeError):
    def __init__(self, code: str, message: str, validation: dict | None = None):
        super().__init__(message)
        self.code = code
        self.validation = validation


def predict_single_smiles(
    smiles: str,
    *,
    force_mock: bool = False,
) -> dict[str, Any]:
    """Run the existing deterministic prediction pipeline without chat language."""
    validation = validate_smiles(smiles)
    if not validation["is_valid"]:
        raise PredictionServiceError(
            "INVALID_SMILES",
            validation["error"] or "Invalid SMILES string.",
            validation=validation,
        )

    prediction_smiles = validation["canonical_smiles"] or validation[
        "input_smiles"
    ].strip()
    try:
        raw_predictions = (
            predict_one(prediction_smiles, force_mock=True)
            if force_mock
            else predict_one(prediction_smiles)
        )
    except ADMETPredictionError as exc:
        raise PredictionServiceError(exc.code, str(exc), validation=validation) from exc

    grouped = group_predictions(raw_predictions)
    status = predictor_status(force_mock=True) if force_mock else predictor_status()
    warnings: list[str] = []
    mock_mode = force_mock or is_mock_mode()
    if mock_mode:
        warnings.append(
            "Mock predictions are deterministic test data, not ADMET-AI model output."
        )

    return {
        "input_smiles": validation["input_smiles"],
        "canonical_smiles": validation["canonical_smiles"],
        "predictions": grouped,
        "enriched_predictions": group_enriched_predictions(raw_predictions),
        "raw_predictions": raw_predictions,
        "summary": generate_summary(grouped),
        "disclaimer": DISCLAIMER,
        "prediction_mode": "mock" if mock_mode else "real",
        "model_metadata": {
            "model_name": status["model_name"],
            "model_version": status["model_version"],
            "model_loaded": status["model_loaded"],
            "execution_environment": status["execution_environment"],
        },
        "warnings": warnings,
        "validation": validation,
    }
