from fastapi.testclient import TestClient

from app.formatter import generate_summary, group_predictions
from app.main import app
from app.tools import endpoints


def test_exact_alias_and_safe_normalized_matching():
    assert endpoints.match_endpoint("AMES")[1] == "exact"
    assert endpoints.match_endpoint("Mutagenicity")[0]["raw_name"] == "AMES"
    assert endpoints.match_endpoint("Mutagenicity")[1] == "alias"
    assert endpoints.match_endpoint("Caco2 Wang")[0]["raw_name"] == "Caco2_Wang"
    assert endpoints.match_endpoint("Caco2 Wang")[1] == "normalized"


def test_normalization_does_not_collapse_cyp_scientific_roles():
    substrate, _ = endpoints.match_endpoint("CYP3A4 Substrate CarbonMangels")
    inhibitor, _ = endpoints.match_endpoint("CYP3A4 Veith")
    assert substrate["raw_name"] == "CYP3A4_Substrate_CarbonMangels"
    assert inhibitor["raw_name"] == "CYP3A4_Veith"
    assert substrate["raw_name"] != inhibitor["raw_name"]


def test_unknown_and_registry_failure_fallback(monkeypatch):
    unknown, match_type = endpoints.match_endpoint("New_Model_Field")
    assert match_type == "unmatched"
    assert unknown["output_type"] == "unknown"
    assert unknown["metadata_status"] == "unverified"
    monkeypatch.setattr(endpoints, "load_registry", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
    fallback, fallback_match = endpoints.match_endpoint("AMES")
    assert fallback_match == "unmatched"
    assert fallback["raw_name"] == "AMES"


def test_non_model_output_types_and_categories():
    assert endpoints.match_endpoint("molecular_weight")[0]["output_type"] == "descriptor"
    assert endpoints.match_endpoint("hydrogen_bond_acceptors")[0]["output_type"] == "count"
    assert endpoints.match_endpoint("Lipinski")[0]["output_type"] == "rule_based"
    assert endpoints.match_endpoint("QED")[0]["output_type"] == "derived"
    percentile = endpoints.match_endpoint("QED_drugbank_approved_percentile")[0]
    assert percentile["output_type"] == "percentile"
    assert percentile["category"] == "benchmark"


def test_verified_units_are_explicit_and_unverified_units_are_suppressed():
    molecular_weight = endpoints.match_endpoint("molecular_weight")[0]
    assert molecular_weight["unit"] == "Da"
    assert molecular_weight["unit_verified"] is True
    unknown = endpoints.unknown_endpoint("unknown")
    assert unknown["unit"] is None
    assert unknown["unit_verified"] is False


def test_version_compatibility_warning_is_non_fatal():
    assert endpoints.compatibility_warning("2.0.1") is None
    assert "outside" in endpoints.compatibility_warning("3.0.0")


def test_enriched_result_preserves_raw_name_and_value():
    enriched = endpoints.enrich_endpoint("AMES", 0.080123)
    assert enriched["raw_name"] == "AMES"
    assert enriched["value"] == 0.080123
    assert enriched["output_type"] == "classification_probability"


def test_summary_probability_language_is_gated_by_registry_metadata():
    verified = generate_summary(group_predictions({"AMES": 0.08}))
    unknown = generate_summary(group_predictions({"Unverified_Bounded_Value": 0.91}))
    assert "model probability" in verified
    assert "model probability" not in unknown
    assert "predicted numerical value" in unknown


def test_summary_percentile_language_is_gated_and_neutral():
    percentile = generate_summary(group_predictions({"AMES_drugbank_approved_percentile": 82.4}))
    assert "82.4th percentile" in percentile
    lowered = percentile.lower()
    assert all(word not in lowered for word in ("good", "bad", "safe", "unsafe", "favorable", "unfavorable", "risk"))


def test_registry_coverage_endpoint_reports_observed_schema():
    response = TestClient(app).get("/endpoints/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_output_count"] == 104
    assert payload["exact_match_count"] == 104
    assert payload["unmatched_count"] == 0
