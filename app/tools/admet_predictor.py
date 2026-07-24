from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from collections.abc import Mapping, Sequence
from typing import Any


_MODEL: Any | None = None
_MODEL_INITIALIZED_AT: str | None = None


class ADMETPredictionError(RuntimeError):
    """Base class for failures inside the ADMET-AI integration boundary."""

    code = "PREDICTION_FAILED"


class ADMETModelNotAvailableError(ADMETPredictionError):
    code = "MODEL_NOT_AVAILABLE"


class ADMETModelLoadError(ADMETPredictionError):
    code = "MODEL_LOAD_FAILED"


def is_mock_mode() -> bool:
    return os.getenv("ADME_MOCK_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def get_model():
    global _MODEL, _MODEL_INITIALIZED_AT
    if is_mock_mode():
        return None

    if _MODEL is not None:
        return _MODEL

    try:
        from admet_ai import ADMETModel
    except ImportError as exc:
        raise ADMETModelNotAvailableError(
            "ADMET-AI is not installed or could not be imported. "
            "Install dependencies with `pip install -r requirements.txt`, or set ADME_MOCK_MODE=true."
        ) from exc

    try:
        _MODEL = ADMETModel()
        _MODEL_INITIALIZED_AT = datetime.now(UTC).isoformat()
    except Exception as exc:  # pragma: no cover - depends on local model/runtime setup
        raise ADMETModelLoadError("The ADMET-AI model could not be initialized.") from exc

    return _MODEL


def predict_one(smiles: str) -> dict:
    if is_mock_mode():
        return _mock_prediction(smiles)

    model = get_model()
    try:
        prediction = model.predict(smiles=smiles)
    except Exception as exc:  # pragma: no cover - depends on real ADMET-AI runtime
        raise ADMETPredictionError("ADMET-AI prediction did not complete.") from exc

    serializable = to_jsonable(prediction)
    if isinstance(serializable, list):
        if len(serializable) == 1 and isinstance(serializable[0], dict):
            return serializable[0]
        return {"predictions": serializable}
    if isinstance(serializable, dict):
        return serializable
    return {"prediction": serializable}


def predict_many(smiles_list: list[str]) -> list[dict]:
    if is_mock_mode():
        return [_mock_prediction(smiles) for smiles in smiles_list]

    model = get_model()
    try:
        prediction = model.predict(smiles=smiles_list)
    except Exception as exc:  # pragma: no cover - depends on real ADMET-AI runtime
        raise ADMETPredictionError("ADMET-AI batch prediction did not complete.") from exc

    serializable = to_jsonable(prediction)
    if isinstance(serializable, list):
        return [item if isinstance(item, dict) else {"prediction": item} for item in serializable]
    if isinstance(serializable, dict):
        records = _records_from_dict(serializable)
        if records is not None:
            return records
        return [serializable]
    return [{"prediction": serializable}]


def to_jsonable(value: Any) -> Any:
    try:
        import numpy as np  # type: ignore
    except ImportError:  # pragma: no cover
        np = None

    try:
        import pandas as pd  # type: ignore
    except ImportError:  # pragma: no cover
        pd = None

    if pd is not None:
        if isinstance(value, pd.DataFrame):
            return to_jsonable(value.to_dict(orient="records"))
        if isinstance(value, pd.Series):
            return to_jsonable(value.to_dict())

    if np is not None:
        if isinstance(value, np.generic):
            return to_jsonable(value.item())
        if isinstance(value, np.ndarray):
            return to_jsonable(value.tolist())

    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    return value


def _records_from_dict(value: dict) -> list[dict] | None:
    if not value:
        return []

    lengths = {
        len(item)
        for item in value.values()
        if isinstance(item, list)
    }
    if len(lengths) != 1:
        return None

    row_count = next(iter(lengths))
    records: list[dict] = []
    for index in range(row_count):
        records.append(
            {
                key: item[index] if isinstance(item, list) else item
                for key, item in value.items()
            }
        )
    return records


def _mock_prediction(smiles: str) -> dict:
    return {
        "Caco2_Wang": 0.71,
        "HIA_Hou": 0.89,
        "Bioavailability_Ma": 0.56,
        "BBB_Martins": 0.34,
        "CYP2D6_Substrate_CarbonMangels": 0.12,
        "Clearance_Hepatocyte_AZ": 5.3,
        "hERG": 0.21,
    }


def predictor_status() -> dict[str, bool | str]:
    mock_mode = is_mock_mode()
    if mock_mode:
        available = True
    else:
        try:
            import admet_ai  # noqa: F401
        except ImportError:
            available = False
        else:
            available = True

    return {
        "prediction_mode": "mock" if mock_mode else "real",
        "model_loaded": False if mock_mode else _MODEL is not None,
        "predictor_available": available,
        "model_name": "ADMET-AI" if not mock_mode else "Deterministic development fixture",
        "model_version": None,
        "last_initialized": None if mock_mode else _MODEL_INITIALIZED_AT,
        "execution_environment": "local",
        "input_type": "small-molecule SMILES",
    }
