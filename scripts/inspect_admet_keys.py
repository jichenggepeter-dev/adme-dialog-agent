from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.admet_predictor import to_jsonable  # noqa: E402


ASPIRIN_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"
OUTPUT_PATH = PROJECT_ROOT / "examples" / "sample_outputs.json"


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
        raise SystemExit(f"ADMET-AI key inspection failed: {exc}") from exc

    serializable = to_jsonable(prediction)
    record = _first_record(serializable)
    keys = list(record.keys()) if isinstance(record, dict) else []

    print("Raw ADMET-AI output keys:")
    for key in keys:
        print(key)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "smiles": ASPIRIN_SMILES,
                "raw_output_keys": keys,
                "raw_prediction": serializable,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved sample output to {OUTPUT_PATH}")


def _first_record(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


if __name__ == "__main__":
    main()

