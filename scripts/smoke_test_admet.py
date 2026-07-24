from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.admet_predictor import to_jsonable  # noqa: E402


ASPIRIN_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"


def main() -> None:
    try:
        from admet_ai import ADMETModel
    except ImportError as exc:
        raise SystemExit(
            "Could not import ADMET-AI. Install dependencies with "
            "`pip install -r requirements.txt`, or use ADME_MOCK_MODE=true for app tests."
        ) from exc

    try:
        model = ADMETModel()
        prediction = model.predict(smiles=ASPIRIN_SMILES)
    except Exception as exc:
        raise SystemExit(f"ADMET-AI smoke test failed: {exc}") from exc

    print("Raw prediction object:")
    print(prediction)
    print("\nPython type:")
    print(type(prediction))
    print("\nJSON-like prediction:")
    print(json.dumps(to_jsonable(prediction), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

