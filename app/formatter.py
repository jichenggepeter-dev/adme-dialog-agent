from __future__ import annotations

from numbers import Number
from typing import Any

from app.tools.endpoints import enrich_predictions, match_endpoint


DISCLAIMER = (
    "This tool provides computational ADME/ADMET predictions only. "
    "The outputs are not experimental measurements and should not be used as "
    "clinical, regulatory, or safety conclusions."
)

CATEGORY_ORDER = (
    "absorption", "distribution", "metabolism", "excretion", "toxicity",
    "physicochemical", "drug_likeness", "benchmark", "other",
)


def group_predictions(raw_predictions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {category: {} for category in CATEGORY_ORDER}
    for key, value in raw_predictions.items():
        metadata, _ = match_endpoint(key)
        category = metadata["category"] if metadata["category"] in grouped else "other"
        grouped[category][key] = value
    return grouped


def group_enriched_predictions(raw_predictions: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORY_ORDER}
    for endpoint in enrich_predictions(raw_predictions):
        category = endpoint["category"] if endpoint["category"] in grouped else "other"
        grouped[category].append(endpoint)
    return grouped


def generate_summary(grouped_predictions: dict[str, Any]) -> str:
    raw = {key: value for values in grouped_predictions.values() for key, value in (values.items() if isinstance(values, dict) else [])}
    populated = [category for category in CATEGORY_ORDER if grouped_predictions.get(category)]
    if not populated:
        return "The predictor returned no endpoint values. Review the raw model response before further use."

    labels = [category.replace("_", " ") for category in populated]
    sentences = [f"The model returned prediction fields grouped under {_join_phrases(labels)}."]
    observations = [_describe_enriched(endpoint) for endpoint in enrich_predictions(raw)]
    observations = [observation for observation in observations if observation][:4]
    if observations:
        sentences.append("Selected outputs: " + "; ".join(observations) + ".")
    sentences.append(
        "These computational outputs require domain-specific interpretation "
        "and experimental validation."
    )
    return " ".join(sentences)


def _describe_enriched(endpoint: dict[str, Any]) -> str:
    value = endpoint["value"]
    if not isinstance(value, Number) or isinstance(value, bool):
        return f"{endpoint['display_name']} returned {value!s}"
    number = float(value)
    unit = f" {endpoint['unit']}" if endpoint["unit_verified"] and endpoint["unit"] and endpoint["output_type"] != "percentile" else ""

    if (
        endpoint["output_type"] == "classification_probability"
        and endpoint["supports_probability_language"]
        and endpoint["positive_class"]
        and endpoint["metadata_status"] in {"verified", "partial"}
    ):
        return f"{endpoint['display_name']} returned a model probability of {number:.3g} for the documented positive class ({endpoint['positive_class']})"

    if endpoint["output_type"] == "percentile" and endpoint["metadata_status"] == "verified":
        return f"{endpoint['display_name']} is at the {number:.3g}th percentile in the documented DrugBank approved reference set"

    if endpoint["output_type"] in {"descriptor", "count", "rule_based", "derived"}:
        return f"{endpoint['display_name']} is {number:.3g}{unit}"

    return f"{endpoint['display_name']} returned a predicted numerical value of {number:.3g}{unit}"


def _join_phrases(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
