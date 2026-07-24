from __future__ import annotations

from typing import Any


class ComparisonError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def compare_prediction_payloads(
    predictions: list[dict[str, Any]],
    *,
    categories: list[str] | None = None,
    endpoints: list[str] | None = None,
) -> dict[str, Any]:
    if not 2 <= len(predictions) <= 5:
        raise ComparisonError(
            "INVALID_COMPARISON_SIZE", "Comparison requires 2 to 5 predictions."
        )

    selected_categories = set(categories or [])
    selected_endpoints = set(endpoints or [])
    rows: list[dict[str, Any]] = []
    endpoint_records: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        enriched = prediction.get("enriched_predictions") or {}
        values: list[dict[str, Any]] = []
        for category, entries in enriched.items():
            if selected_categories and category not in selected_categories:
                continue
            for entry in entries:
                raw_name = entry.get("raw_name") or entry.get("raw_key")
                if selected_endpoints and raw_name not in selected_endpoints:
                    continue
                value_record = {
                        "raw_name": raw_name,
                        "category": category,
                        "value": entry.get("value"),
                        "output_type": entry.get("output_type"),
                        "unit": entry.get("unit") if entry.get("unit_verified") else None,
                        "metadata_status": entry.get("metadata_status", "unknown"),
                        "prediction_mode": prediction.get("prediction_mode"),
                        "model_version": (prediction.get("model_metadata") or {}).get("model_version"),
                    }
                values.append(value_record)
                endpoint_records.setdefault(str(raw_name), []).append(value_record)
        rows.append(
            {
                "prediction_id": prediction.get("prediction_id"),
                "compound_id": prediction.get("compound_id"),
                "values": values,
            }
        )

    compatibility = []
    for raw_name in sorted(endpoint_records):
        records = endpoint_records[raw_name]
        reasons: list[str] = []
        if len(records) != len(predictions):
            reasons.append("missing_endpoint_value")
        for field, reason in (("output_type", "output_type_mismatch"), ("unit", "verified_unit_mismatch"), ("prediction_mode", "prediction_mode_mismatch"), ("model_version", "model_version_mismatch")):
            if len({record.get(field) for record in records}) > 1:
                reasons.append(reason)
        if any(record.get("metadata_status") not in {"verified", "complete"} for record in records):
            reasons.append("metadata_not_verified")
        compatibility.append({
            "raw_name": raw_name,
            "comparable": not reasons,
            "reasons": reasons,
            "warning": None if not reasons else "Values are shown but must not be interpreted as directly comparable.",
        })
    return {
        "comparison_count": len(rows),
        "rows": rows,
        "endpoint_compatibility": compatibility,
        "ranking": None,
        "winner": None,
        "interpretation": (
            "Values are presented neutrally. No best-compound ranking or undocumented "
            "directionality is applied."
        ),
    }
