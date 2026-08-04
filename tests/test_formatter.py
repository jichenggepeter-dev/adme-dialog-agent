from app.formatter import generate_summary, group_predictions


def test_caco2_key_goes_to_absorption():
    assert "Caco2_Wang" in group_predictions({"Caco2_Wang": 0.7})["absorption"]


def test_bbb_key_goes_to_distribution():
    assert "BBB_Martins" in group_predictions({"BBB_Martins": 0.3})["distribution"]


def test_cyp_key_goes_to_metabolism():
    assert "CYP2D6_Substrate_CarbonMangels" in group_predictions({"CYP2D6_Substrate_CarbonMangels": 0.2})["metabolism"]


def test_clearance_key_goes_to_excretion():
    assert "Clearance_Hepatocyte_AZ" in group_predictions({"Clearance_Hepatocyte_AZ": 5.3})["excretion"]


def test_herg_key_goes_to_toxicity():
    assert "hERG" in group_predictions({"hERG": 0.21})["toxicity"]


def test_unknown_key_goes_to_other():
    assert "Unknown_Property" in group_predictions({"Unknown_Property": 1})["other"]


def test_caco2_value_is_not_described_as_probability():
    grouped = group_predictions({"Caco2_Wang": 0.71})
    summary = generate_summary(grouped)
    assert "predicted numerical value" in summary
    assert "high predicted probability" not in summary
    assert "require domain-specific interpretation and experimental validation" in summary
    assert "priorit" not in summary.lower()
