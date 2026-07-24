from __future__ import annotations

import csv
import importlib.metadata
import re
from functools import lru_cache
from typing import Any


REGISTRY_SCHEMA_VERSION = "2.0"
COMPATIBLE_ADMET_AI_VERSIONS = ["2.x"]
LAST_UPDATED = "2026-07-11"
PERCENTILE_SUFFIX = "_drugbank_approved_percentile"

PHYCHEM_OVERRIDES = {
    "molecular_weight": ("physicochemical", "descriptor", "Molecular descriptor"),
    "logP": ("physicochemical", "descriptor", "Molecular descriptor"),
    "hydrogen_bond_acceptors": ("physicochemical", "count", "Count"),
    "hydrogen_bond_donors": ("physicochemical", "count", "Count"),
    "Lipinski": ("drug_likeness", "rule_based", "Rule-based"),
    "QED": ("drug_likeness", "derived", "Derived value"),
    "stereo_centers": ("physicochemical", "count", "Count"),
    "tpsa": ("physicochemical", "descriptor", "Molecular descriptor"),
    "PAINS_alert": ("drug_likeness", "count", "Count"),
    "BRENK_alert": ("drug_likeness", "count", "Count"),
    "NIH_alert": ("drug_likeness", "count", "Count"),
}

OUTPUT_TYPE_LABELS = {
    "classification_probability": "Classification probability",
    "classification_label": "Classification",
    "regression": "Regression",
    "descriptor": "Molecular descriptor",
    "percentile": "Percentile",
    "count": "Count",
    "rule_based": "Rule-based",
    "derived": "Derived value",
    "categorical": "Categorical",
    "unknown": "Metadata not verified",
}


def normalize_endpoint_name(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[\s-]+", "_", value.strip().lower())).strip("_")


def _package_version() -> str | None:
    try:
        return importlib.metadata.version("admet-ai")
    except importlib.metadata.PackageNotFoundError:
        return None


def _unit(raw_unit: str) -> str | None:
    if raw_unit in {"", "-", "#", "# of 4"}:
        return None
    return {"Dalton": "Da", "hr": "h", "uL/min/10^6 cells": "µL/min/10⁶ cells", "uL/min/mg": "µL/min/mg"}.get(raw_unit, raw_unit)


def _source(row: dict[str, str], source_name: str = "ADMET-AI bundled endpoint metadata") -> dict[str, str | None]:
    return {
        "name": source_name,
        "reference": row.get("url") or None,
        "version": _package_version(),
    }


def _base_entry(row: dict[str, str]) -> dict[str, Any]:
    raw_name = row["id"]
    package_category = row["category"].lower()
    if raw_name in PHYCHEM_OVERRIDES:
        category, output_type, _ = PHYCHEM_OVERRIDES[raw_name]
        prediction_task = "rdkit_calculation"
        status = "verified"
        supports_probability = False
        positive_class = None
        description = f"Calculated molecular property: {row['name']}."
        interpretation = "This is a calculated molecular property, not an experimental measurement or model probability."
    else:
        category = package_category
        output_type = "classification_probability" if row["task_type"] == "classification" else "regression"
        prediction_task = "binary_classification" if row["task_type"] == "classification" else "regression"
        status = "partial"
        supports_probability = row["task_type"] == "classification"
        positive_class = row["name"] if supports_probability else None
        description = f"ADMET-AI endpoint for the documented task: {row['name']}."
        interpretation = "Task identity, output type, and package-reported unit are documented; consult the linked task source before scientific interpretation."

    return {
        "raw_name": raw_name,
        "raw_key": raw_name,
        "display_name": row["name"],
        "aliases": [row["name"]],
        "category": category,
        "output_type": output_type,
        "output_type_label": OUTPUT_TYPE_LABELS[output_type],
        "prediction_type": output_type,
        "prediction_task": prediction_task,
        "positive_class": positive_class,
        "unit": _unit(row["units"]),
        "unit_verified": True,
        "description": description,
        "interpretation_note": interpretation,
        "interpretation_limitations": interpretation,
        "directionality": "context_dependent",
        "source": _source(row),
        "metadata_status": status,
        "metadata_verified": status == "verified",
        "supports_probability_language": supports_probability,
        "supports_directional_language": False,
        "compatible_admet_ai_versions": COMPATIBLE_ADMET_AI_VERSIONS,
        "experimental_validation_note": "Experimental validation is required before scientific or development decisions.",
    }


def _percentile_entry(base: dict[str, Any]) -> dict[str, Any]:
    raw_name = f"{base['raw_name']}{PERCENTILE_SUFFIX}"
    return {
        "raw_name": raw_name,
        "raw_key": raw_name,
        "display_name": f"{base['display_name']} — DrugBank approved percentile",
        "aliases": [],
        "category": "benchmark",
        "output_type": "percentile",
        "output_type_label": OUTPUT_TYPE_LABELS["percentile"],
        "prediction_type": "percentile",
        "prediction_task": "reference_set_percentile",
        "positive_class": None,
        "unit": "percentile",
        "unit_verified": True,
        "description": f"Percentile of {base['display_name']} relative to the ADMET-AI bundled DrugBank approved reference set.",
        "interpretation_note": "This is a relative position in the documented reference distribution, not a measure of clinical quality, safety, or efficacy.",
        "interpretation_limitations": "Reference-set composition and model version affect the percentile; do not interpret direction as favorable or unfavorable.",
        "directionality": "context_dependent",
        "source": {
            "name": "ADMET-AI DrugBank approved reference percentile implementation",
            "reference": "https://github.com/swansonk14/admet_ai",
            "version": _package_version(),
        },
        "metadata_status": "verified",
        "metadata_verified": True,
        "supports_probability_language": False,
        "supports_directional_language": False,
        "compatible_admet_ai_versions": COMPATIBLE_ADMET_AI_VERSIONS,
        "experimental_validation_note": "Percentiles are contextual computational comparisons and require domain-specific validation.",
    }


def unknown_endpoint(raw_name: str) -> dict[str, Any]:
    return {
        "raw_name": raw_name,
        "raw_key": raw_name,
        "display_name": raw_name.replace("_", " "),
        "aliases": [],
        "category": "other",
        "output_type": "unknown",
        "output_type_label": OUTPUT_TYPE_LABELS["unknown"],
        "prediction_type": "unknown",
        "prediction_task": None,
        "positive_class": None,
        "unit": None,
        "unit_verified": False,
        "description": None,
        "interpretation_note": "Endpoint metadata has not been verified.",
        "interpretation_limitations": "Preserve the raw value and consult a primary source before interpretation.",
        "directionality": "unknown",
        "source": None,
        "metadata_status": "unverified",
        "metadata_verified": False,
        "supports_probability_language": False,
        "supports_directional_language": False,
        "compatible_admet_ai_versions": COMPATIBLE_ADMET_AI_VERSIONS,
        "experimental_validation_note": "No scientific interpretation should be made until this metadata is verified.",
    }


def _load_package_rows() -> list[dict[str, str]]:
    distribution = importlib.metadata.distribution("admet-ai")
    resource = distribution.locate_file("admet_ai/resources/data/admet.csv")
    with resource.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def load_registry() -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for row in _load_package_rows():
        base = _base_entry(row)
        entries[base["raw_name"]] = base
        entries[f"{base['raw_name']}{PERCENTILE_SUFFIX}"] = _percentile_entry(base)
    return entries


def registry_document() -> dict[str, Any]:
    warning = compatibility_warning()
    try:
        endpoints = load_registry()
    except Exception:
        endpoints = {}
        warning = "Endpoint registry metadata could not be loaded; raw outputs will remain visible as unverified."
    return {
        "registry_schema_version": REGISTRY_SCHEMA_VERSION,
        "compatible_admet_ai_versions": COMPATIBLE_ADMET_AI_VERSIONS,
        "last_updated": LAST_UPDATED,
        "running_admet_ai_version": _package_version(),
        "compatibility_warning": warning,
        "endpoints": endpoints,
    }


def list_endpoints() -> dict[str, dict[str, Any]]:
    return registry_document()["endpoints"]


def _lookup_indexes(registry: dict[str, dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    aliases: dict[str, str] = {}
    normalized: dict[str, str] = {}
    for raw_name, entry in registry.items():
        normalized.setdefault(normalize_endpoint_name(raw_name), raw_name)
        for alias in entry["aliases"]:
            aliases.setdefault(normalize_endpoint_name(alias), raw_name)
    return aliases, normalized


def match_endpoint(raw_name: str) -> tuple[dict[str, Any], str]:
    try:
        registry = load_registry()
    except Exception:
        return unknown_endpoint(raw_name), "unmatched"
    if raw_name in registry:
        return registry[raw_name], "exact"
    aliases, normalized = _lookup_indexes(registry)
    key = normalize_endpoint_name(raw_name)
    if key in aliases:
        return registry[aliases[key]], "alias"
    if key in normalized:
        return registry[normalized[key]], "normalized"
    return unknown_endpoint(raw_name), "unmatched"


def get_endpoint(raw_name: str) -> dict[str, Any] | None:
    endpoint, match_type = match_endpoint(raw_name)
    return None if match_type == "unmatched" else {**endpoint, "match_type": match_type}


def enrich_endpoint(raw_name: str, value: Any) -> dict[str, Any]:
    metadata, match_type = match_endpoint(raw_name)
    return {"raw_name": raw_name, "value": value, "match_type": match_type, **metadata}


def enrich_predictions(raw_predictions: dict[str, Any]) -> list[dict[str, Any]]:
    return [enrich_endpoint(raw_name, value) for raw_name, value in raw_predictions.items()]


def registry_coverage(raw_names: list[str]) -> dict[str, Any]:
    enriched = [match_endpoint(name) for name in raw_names]
    match_counts = {kind: sum(match_type == kind for _, match_type in enriched) for kind in ("exact", "alias", "normalized", "unmatched")}
    statuses = {status: sum(endpoint["metadata_status"] == status for endpoint, _ in enriched) for status in ("verified", "partial", "unverified")}
    return {
        "raw_output_count": len(raw_names),
        "exact_match_count": match_counts["exact"],
        "alias_match_count": match_counts["alias"],
        "normalized_match_count": match_counts["normalized"],
        "unmatched_count": match_counts["unmatched"],
        "verified_count": statuses["verified"],
        "partial_count": statuses["partial"],
        "unverified_count": statuses["unverified"],
        "compatibility_warning": compatibility_warning(),
    }


def compatibility_warning(version: str | None = None) -> str | None:
    running = version if version is not None else _package_version()
    if running is None:
        return "ADMET-AI is not installed; registry compatibility cannot be confirmed."
    if not running.startswith("2."):
        return f"Registry metadata targets ADMET-AI 2.x; running version {running} is outside that range."
    return None
