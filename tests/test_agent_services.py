from __future__ import annotations

import pytest

from app.services.comparison import ComparisonError, compare_prediction_payloads
from app.services.input_quality import assess_input_quality
from app.services.prediction import predict_single_smiles


def test_neutral_prediction_preserves_raw_metadata_and_mock_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADME_MOCK_MODE", "true")
    result = predict_single_smiles("CC(=O)OC1=CC=CC=C1C(=O)O")
    assert result["prediction_mode"] == "mock"
    assert result["raw_predictions"]["Caco2_Wang"] == 0.71
    assert result["model_metadata"]["model_name"] == "Deterministic development fixture"
    assert result["warnings"]


def test_input_quality_reports_fragments_charge_and_no_ad_score() -> None:
    result = assess_input_quality("[Na+].CC(=O)[O-]")
    assert result["parse_status"] == "valid"
    assert result["fragment_count"] == 2
    assert result["total_formal_charge"] == 0
    assert result["metal_presence"] is True
    assert result["mixture_warning"] is True
    assert result["is_applicability_domain_score"] is False


@pytest.mark.parametrize("count", [1, 6])
def test_comparison_rejects_out_of_bounds_count(count: int) -> None:
    with pytest.raises(ComparisonError) as caught:
        compare_prediction_payloads([{} for _ in range(count)])
    assert caught.value.code == "INVALID_COMPARISON_SIZE"


def test_comparison_never_selects_a_winner() -> None:
    result = compare_prediction_payloads(
        [
            {"prediction_id": "one", "compound_id": "c1", "enriched_predictions": {}},
            {"prediction_id": "two", "compound_id": "c2", "enriched_predictions": {}},
        ]
    )
    assert result["winner"] is None
    assert result["ranking"] is None
