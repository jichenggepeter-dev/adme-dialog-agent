from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agent_runtime.confirmations import ConfirmationEngine
from app.agent_runtime.contracts import EvidenceAnswerData, ToolResultEnvelope
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository
from app.services.comparison import ComparisonError, compare_prediction_payloads
from app.services.input_quality import InputQualityError, assess_input_quality
from app.services.prediction import PredictionServiceError, predict_single_smiles
from app.services.evidence import search_evidence
from app.tools.batch import BatchError, get_job
from app.tools.compound import CompoundResolutionError, resolve_compound
from app.tools.endpoints import (
    get_endpoint,
    registry_coverage,
    registry_document,
    unknown_endpoint,
)
from app.tools.admet_predictor import predictor_status


MAX_TOOL_CALLS = 8
MAX_IDENTICAL_TOOL_CALLS = 2


@dataclass
class ToolExecutionContext:
    session_id: str
    repository: AgentRepository
    state_version: int
    mock_agent_catalog_version: int | None = None
    tool_activity: list[dict[str, Any]] = field(default_factory=list)
    structured_payloads: list[dict[str, Any]] = field(default_factory=list)
    pending_confirmation: dict[str, Any] | None = None
    pending_action: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    call_fingerprints: list[str] = field(default_factory=list)
    blocked: bool = False


class AgentToolService:
    def __init__(self, context: ToolExecutionContext):
        self.context = context
        self.repository = context.repository
        self.confirmations = ConfirmationEngine(self.repository)

    def resolve_compound(self, query: str) -> dict:
        return self._execute("resolve_compound", lambda: self._resolve_compound(query), {"query": query})

    def _resolve_compound(self, query: str) -> dict:
        compound = resolve_compound(query)
        quality = assess_input_quality(compound["canonical_smiles"])
        compound_id = f"compound_{uuid4().hex}"
        compound_payload = {**compound, "compound_id": compound_id, "input_quality": quality}
        if self.context.mock_agent_catalog_version is not None:
            compound_payload.update(
                {
                    "agent_provider_mode": "mock",
                    "mock_catalog_version": self.context.mock_agent_catalog_version,
                }
            )
        resource = self.repository.put_resource(
            self.context.session_id, "compound", compound_payload
        )
        state = self.repository.get_business_state(self.context.session_id)["state"]
        compounds = dict(state.get("compounds") or {})
        compounds[compound_id] = resource["resource_id"]
        updated = self.repository.update_business_state(
            self.context.session_id,
            {
                "current_compound_id": compound_id,
                "compounds": compounds,
                "confirmed_compound_id": None,
                "confirmed_canonical_smiles": None,
            },
            expected_version=self.context.state_version,
        )
        self.context.state_version = updated["version"]
        confirmation = self.confirmations.propose_compound(
            self.context.session_id,
            compound_payload,
            expected_state_version=self.context.state_version,
        )
        self.context.pending_confirmation = confirmation
        self.context.structured_payloads.append(
            {"type": "compound_confirmation", "data": compound_payload}
        )
        self.context.warnings.extend(quality["warnings"])
        return self._envelope(
            "resolve_compound",
            "confirmation_required",
            data={
                "compound_id": compound_id,
                "preferred_name": compound["preferred_name"],
                "canonical_smiles": compound["canonical_smiles"],
                "input_quality": quality,
                "requires_confirmation": True,
                "confirmation_id": confirmation["confirmation_id"],
            },
            resource_id=resource["resource_id"],
            provenance={"compound": compound["data_source"], "quality": "RDKit rules"},
        )

    def get_compound_context(self, compound_id: str) -> dict:
        return self._execute(
            "get_compound_context", lambda: self._get_compound_context(compound_id), {"compound_id": compound_id}
        )

    def _get_compound_context(self, compound_id: str) -> dict:
        state = self.repository.get_business_state(self.context.session_id)["state"]
        resource_id = (state.get("compounds") or {}).get(compound_id)
        if not resource_id:
            raise AgentCoreError("RESOURCE_NOT_FOUND", "Compound context was not found.", 404)
        resource = self.repository.get_resource(self.context.session_id, resource_id)
        data = dict(resource["data"])
        data["confirmed"] = state.get("confirmed_compound_id") == compound_id
        data.pop("depiction_svg", None)
        return self._envelope(
            "get_compound_context", "ok", data=data, resource_id=resource_id
        )

    def get_input_quality_assessment(self, compound_id: str) -> dict:
        return self._execute(
            "get_input_quality_assessment",
            lambda: self._get_input_quality_assessment(compound_id),
            {"compound_id": compound_id},
        )

    def _get_input_quality_assessment(self, compound_id: str) -> dict:
        compound = self._get_compound_resource(compound_id)
        quality = assess_input_quality(compound["canonical_smiles"])
        return self._envelope(
            "get_input_quality_assessment",
            "ok",
            data=quality,
            provenance={"source": "RDKit deterministic rules"},
        )

    def predict_single_compound(self, compound_id: str) -> dict:
        return self._execute(
            "predict_single_compound", lambda: self._predict_single_compound(compound_id), {"compound_id": compound_id}
        )

    def _predict_single_compound(self, compound_id: str) -> dict:
        current = self.repository.get_business_state(self.context.session_id)
        state = current["state"]
        if state.get("confirmed_compound_id") != compound_id:
            raise AgentCoreError(
                "CONFIRMATION_REQUIRED", "Compound structure confirmation is required.", 409
            )
        compound = self._get_compound_resource(compound_id)
        if compound["canonical_smiles"] != state.get("confirmed_canonical_smiles"):
            raise AgentCoreError(
                "TOOL_RESULT_INVALID", "Confirmed SMILES does not match compound state.", 409
            )
        result = (
            predict_single_smiles(compound["canonical_smiles"], force_mock=True)
            if self.context.mock_agent_catalog_version is not None
            else predict_single_smiles(compound["canonical_smiles"])
        )
        prediction_id = f"prediction_{uuid4().hex}"
        raw = self.repository.put_resource(
            self.context.session_id,
            "raw_prediction",
            result["raw_predictions"],
        )
        stored = {
            **{key: value for key, value in result.items() if key != "raw_predictions"},
            "prediction_id": prediction_id,
            "compound_id": compound_id,
            "raw_predictions_resource_id": raw["resource_id"],
        }
        prediction_resource = self.repository.put_resource(
            self.context.session_id, "prediction", stored
        )
        predictions = dict(state.get("predictions") or {})
        predictions[prediction_id] = prediction_resource["resource_id"]
        updated = self.repository.update_business_state(
            self.context.session_id,
            {
                "latest_prediction_id": prediction_id,
                "predictions": predictions,
            },
            expected_version=current["version"],
        )
        self.context.state_version = updated["version"]
        compact = {
            "prediction_id": prediction_id,
            "compound_id": compound_id,
            "status": "completed",
            "prediction_mode": stored["prediction_mode"],
            "model_metadata": stored["model_metadata"],
            "raw_predictions_resource_id": raw["resource_id"],
            "prediction_resource_id": prediction_resource["resource_id"],
            "summary": stored["summary"],
            "warnings": stored["warnings"],
            "disclaimer": stored["disclaimer"],
        }
        self.context.structured_payloads.append({"type": "prediction", "data": compact})
        self.context.warnings.extend(stored["warnings"])
        return self._envelope(
            "predict_single_compound",
            "ok",
            data=compact,
            resource_id=prediction_resource["resource_id"],
            provenance={"predictor": stored["model_metadata"]},
        )

    def get_prediction_results(
        self,
        prediction_id: str,
        categories: list[str] | None = None,
        endpoints: list[str] | None = None,
    ) -> dict:
        return self._execute(
            "get_prediction_results",
            lambda: self._get_prediction_results(prediction_id, categories, endpoints),
            {"prediction_id": prediction_id, "categories": categories, "endpoints": endpoints},
        )

    def _get_prediction_results(
        self, prediction_id: str, categories: list[str] | None, endpoints: list[str] | None
    ) -> dict:
        resource = self._get_prediction_resource(prediction_id)
        data = resource["data"]
        enriched = data.get("enriched_predictions") or {}
        filtered: dict[str, list[dict]] = {}
        for category, entries in enriched.items():
            if categories and category not in categories:
                continue
            selected = [
                entry
                for entry in entries
                if not endpoints
                or (entry.get("raw_name") or entry.get("raw_key")) in endpoints
            ]
            if selected:
                filtered[category] = selected
        structured = {
            "prediction_id": prediction_id,
            "prediction_mode": data["prediction_mode"],
            "enriched_predictions": filtered,
            "warnings": data["warnings"],
            "disclaimer": data["disclaimer"],
        }
        self.context.structured_payloads.append(
            {"type": "prediction", "data": structured}
        )
        return self._envelope(
            "get_prediction_results",
            "ok",
            data={**structured, "results": filtered},
            resource_id=resource["resource_id"],
        )

    def explain_endpoint(self, endpoint_name: str) -> dict:
        return self._execute(
            "explain_endpoint", lambda: self._explain_endpoint(endpoint_name), {"endpoint_name": endpoint_name}
        )

    def _explain_endpoint(self, endpoint_name: str) -> dict:
        metadata = get_endpoint(endpoint_name) or unknown_endpoint(endpoint_name)
        self.context.structured_payloads.append(
            {"type": "endpoint_explanation", "data": metadata}
        )
        return self._envelope(
            "explain_endpoint",
            "ok",
            data=metadata,
            provenance={"source": "Endpoint Registry"},
        )

    def search_adme_evidence(self, query: str, top_k: int = 3) -> dict:
        return self._execute(
            "search_adme_evidence",
            lambda: self._search_adme_evidence(query, top_k),
            {"query": query, "top_k": top_k},
        )

    def _search_adme_evidence(self, query: str, top_k: int) -> dict:
        data = EvidenceAnswerData.model_validate(
            search_evidence(query, top_k)
        ).model_dump(mode="json")
        self.context.structured_payloads.append(
            {"type": "evidence_answer", "data": data}
        )
        self.context.warnings.extend(data["warnings"])
        return self._envelope(
            "search_adme_evidence",
            "ok",
            data=data,
            provenance={
                "source": "Approved local FDA evidence corpus",
                "retrieval": "deterministic lexical BM25",
            },
        )

    def get_model_information(self) -> dict:
        return self._execute("get_model_information", self._get_model_information, {})

    def _get_model_information(self) -> dict:
        registry = registry_document()
        status = (
            predictor_status(force_mock=True)
            if self.context.mock_agent_catalog_version is not None
            else predictor_status()
        )
        data = {
                **status,
                "registry_schema_version": registry["registry_schema_version"],
                "registry_coverage": registry_coverage(list(registry["endpoints"])),
                "scientific_limitations": [
                    "Computational predictions are not experimental measurements.",
                    "Outputs are not clinical or regulatory conclusions.",
                    "Endpoint semantics depend on verified Registry metadata.",
                ],
            }
        self.context.structured_payloads.append({"type": "model_information", "data": data})
        return self._envelope(
            "get_model_information",
            "ok",
            data=data,
            provenance={"registry": "Endpoint Registry", "predictor": "ADMET-AI wrapper"},
        )

    def get_batch_job_status(self, job_id: str) -> dict:
        return self._execute(
            "get_batch_job_status", lambda: self._get_batch_job_status(job_id), {"job_id": job_id}
        )

    def _get_batch_job_status(self, job_id: str) -> dict:
        job = get_job(job_id)
        progress = job["progress"]
        total = progress["total"] or 0
        data = {
            "job_id": job_id,
            "status": job["status"],
            "prediction_mode": job["prediction_mode"],
            **job["summary"],
            "completed_count": progress["completed"],
            "failed_count": progress["failed"],
            "progress": progress["processed"] / total if total else 0.0,
        }
        self.context.structured_payloads.append({"type": "batch_summary", "data": data})
        return self._envelope(
            "get_batch_job_status",
            "ok",
            data=data,
        )

    def get_batch_errors(self, job_id: str) -> dict:
        return self._execute("get_batch_errors", lambda: self._get_batch_errors(job_id), {"job_id": job_id})

    def _get_batch_errors(self, job_id: str) -> dict:
        job = get_job(job_id)
        errors = [
            {
                "row_number": row["row_number"],
                "compound_id": row.get("compound_id"),
                "compound_name": row.get("compound_name"),
                "input_smiles": row.get("input_smiles"),
                "error_code": row.get("error_code"),
                "error_message": row.get("error_message"),
                "retry_eligible": row.get("prediction_status") == "failed",
            }
            for row in job["rows"]
            if row.get("error_code") or row.get("prediction_status") == "failed"
        ]
        resource = self.repository.put_resource(
            self.context.session_id, "batch_errors", errors
        )
        self.context.structured_payloads.append(
            {"type": "batch_errors", "data": {"job_id": job_id, "error_count": len(errors), "errors": errors[:25]}}
        )
        return self._envelope(
            "get_batch_errors",
            "ok",
            data={"job_id": job_id, "error_count": len(errors), "errors": errors[:25]},
            resource_id=resource["resource_id"],
        )

    def summarize_batch_results(
        self,
        job_id: str,
        scope: str = "overview",
        selected_compound_ids: list[str] | None = None,
        selected_endpoints: list[str] | None = None,
    ) -> dict:
        return self._execute(
            "summarize_batch_results",
            lambda: self._summarize_batch_results(
                job_id, scope, selected_compound_ids, selected_endpoints
            ),
            {"job_id": job_id, "scope": scope, "selected_compound_ids": selected_compound_ids, "selected_endpoints": selected_endpoints},
        )

    def _summarize_batch_results(
        self,
        job_id: str,
        scope: str,
        selected_compound_ids: list[str] | None,
        selected_endpoints: list[str] | None,
    ) -> dict:
        if scope not in {"overview", "errors", "selected_compounds", "selected_endpoints"}:
            raise AgentCoreError("TOOL_CALL_INVALID", "Unsupported batch summary scope.")
        job = get_job(job_id)
        selected = set(selected_endpoints or [])
        endpoint_values: dict[str, list[float]] = {}
        failed_rows = 0
        completed_rows = 0
        for row in job["rows"]:
            if row.get("prediction_status") == "failed":
                failed_rows += 1
            if row.get("prediction_status") == "completed":
                completed_rows += 1
            for endpoint, value in (row.get("raw_predictions") or {}).items():
                if selected and endpoint not in selected:
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    endpoint_values.setdefault(endpoint, []).append(float(value))
        endpoint_statistics = {
            endpoint: {"count": len(values), "min": min(values), "max": max(values), "mean": sum(values) / len(values)}
            for endpoint, values in endpoint_values.items()
        }
        data = {
            "job_id": job_id,
            "scope": scope,
            "status": job["status"],
            "prediction_mode": job["prediction_mode"],
            "validation_summary": job["summary"],
            "progress": job["progress"],
            "selected_compound_ids": (selected_compound_ids or [])[:25],
            "selected_endpoints": (selected_endpoints or [])[:25],
            "completed_rows": completed_rows,
            "failed_rows": failed_rows,
            "duplicate_rows": job["summary"].get("duplicate_molecules", 0),
            "endpoint_statistics": endpoint_statistics,
            "ranking": None,
            "winner": None,
        }
        self.context.structured_payloads.append({"type": "batch_summary", "data": data})
        return self._envelope("summarize_batch_results", "ok", data=data)

    def get_batch_rows(
        self,
        job_id: str,
        row_numbers: list[int] | None = None,
        compound_ids: list[str] | None = None,
    ) -> dict:
        return self._execute(
            "get_batch_rows",
            lambda: self._get_batch_rows(job_id, row_numbers, compound_ids),
            {"job_id": job_id, "row_numbers": row_numbers, "compound_ids": compound_ids},
        )

    def _get_batch_rows(
        self, job_id: str, row_numbers: list[int] | None, compound_ids: list[str] | None
    ) -> dict:
        rows_requested = list(dict.fromkeys(row_numbers or []))
        ids_requested = list(dict.fromkeys(compound_ids or []))
        if not rows_requested and not ids_requested:
            raise AgentCoreError("TOOL_CALL_INVALID", "Provide row numbers or compound IDs.")
        if len(rows_requested) > 5 or len(ids_requested) > 5:
            raise AgentCoreError("TOOL_CALL_INVALID", "At most five batch rows may be read.")
        job = get_job(job_id)
        rows = [
            row for row in job["rows"]
            if row["row_number"] in rows_requested or row.get("compound_id") in ids_requested
        ]
        if not rows:
            raise AgentCoreError("RESOURCE_NOT_FOUND", "No matching batch rows were found.", 404)
        compact = [{
            "row_number": row["row_number"],
            "compound_id": row.get("compound_id"),
            "compound_name": row.get("compound_name"),
            "canonical_smiles": row.get("canonical_smiles"),
            "validation_status": row.get("validation_status"),
            "prediction_status": row.get("prediction_status"),
            "available_endpoints": sorted((row.get("raw_predictions") or {}).keys()),
            "error_code": row.get("error_code"),
        } for row in rows]
        return self._envelope("get_batch_rows", "ok", data={"job_id": job_id, "rows": compact})

    def compare_batch_rows(
        self, job_id: str, row_numbers: list[int], endpoints: list[str]
    ) -> dict:
        return self._execute(
            "compare_batch_rows",
            lambda: self._compare_batch_rows(job_id, row_numbers, endpoints),
            {"job_id": job_id, "row_numbers": row_numbers, "endpoints": endpoints},
        )

    def _compare_batch_rows(
        self, job_id: str, row_numbers: list[int], endpoints: list[str]
    ) -> dict:
        unique_rows = list(dict.fromkeys(row_numbers))
        unique_endpoints = list(dict.fromkeys(endpoints))
        if not 2 <= len(unique_rows) <= 5:
            raise AgentCoreError("TOOL_CALL_INVALID", "Compare between two and five rows.")
        if not 1 <= len(unique_endpoints) <= 20:
            raise AgentCoreError("TOOL_CALL_INVALID", "Select between one and twenty endpoints.")
        job = get_job(job_id)
        by_number = {row["row_number"]: row for row in job["rows"]}
        missing = [number for number in unique_rows if number not in by_number]
        if missing:
            raise AgentCoreError("RESOURCE_NOT_FOUND", f"Batch rows were not found: {missing}.", 404)
        selected = [by_number[number] for number in unique_rows]
        incomplete = [row["row_number"] for row in selected if row.get("prediction_status") != "completed"]
        if incomplete:
            raise AgentCoreError("TOOL_CALL_INVALID", f"Rows are not completed: {incomplete}.")
        available = set().union(*[(row.get("raw_predictions") or {}).keys() for row in selected])
        unknown = [key for key in unique_endpoints if key not in available]
        if unknown:
            raise AgentCoreError("TOOL_CALL_INVALID", f"Endpoints are unavailable: {unknown}.")
        compounds = [{
            "row_number": row["row_number"],
            "compound_id": row.get("compound_id"),
            "compound_name": row.get("compound_name"),
        } for row in selected]
        matrix = [{
            "endpoint": endpoint,
            "values": [
                {"row_number": row["row_number"], "value": (row.get("raw_predictions") or {}).get(endpoint)}
                for row in selected
            ],
        } for endpoint in unique_endpoints]
        data = {
            "job_id": job_id,
            "compounds": compounds,
            "endpoints": unique_endpoints,
            "matrix": matrix,
            "ranking": None,
            "winner": None,
            "note": "Raw model outputs are shown neutrally; no overall ranking is applied.",
        }
        resource = self.repository.put_resource(self.context.session_id, "batch_comparison", data)
        self.context.structured_payloads.append({"type": "comparison", "data": data})
        return self._envelope("compare_batch_rows", "ok", data=data, resource_id=resource["resource_id"])

    def prepare_batch_action(self, job_id: str, action_type: str) -> dict:
        return self._execute(
            "prepare_batch_action",
            lambda: self._prepare_batch_action(job_id, action_type),
            {"job_id": job_id, "action_type": action_type},
        )

    def _prepare_batch_action(self, job_id: str, action_type: str) -> dict:
        if action_type not in {"run_batch_job", "cancel_batch_job"}:
            raise AgentCoreError("ACTION_NOT_ALLOWED", "Unsupported batch action.", 403)
        job = get_job(job_id)
        if action_type == "run_batch_job" and job["status"] != "ready":
            raise AgentCoreError("BATCH_JOB_NOT_READY", "The batch job is not ready to run.", 409)
        if action_type == "cancel_batch_job" and job["status"] in {"completed", "completed_with_errors", "failed", "cancelled"}:
            raise AgentCoreError("BATCH_JOB_NOT_CANCELLABLE", "The batch job cannot be cancelled.", 409)
        action = self.repository.create_pending_action(
            self.context.session_id,
            action_type,
            {"job_id": job_id, "action_type": action_type, "status_at_proposal": job["status"]},
            self.context.state_version,
        )
        self.context.pending_action = action
        return self._envelope(
            "prepare_batch_action",
            "confirmation_required",
            data={"action_id": action["action_id"], "job_id": job_id, "action_type": action_type},
        )

    def compare_compounds(
        self,
        prediction_ids: list[str],
        categories: list[str] | None = None,
        endpoints: list[str] | None = None,
    ) -> dict:
        return self._execute(
            "compare_compounds",
            lambda: self._compare_compounds(prediction_ids, categories, endpoints),
            {"prediction_ids": prediction_ids, "categories": categories, "endpoints": endpoints},
        )

    def _compare_compounds(
        self, prediction_ids: list[str], categories: list[str] | None, endpoints: list[str] | None
    ) -> dict:
        payloads = []
        for prediction_id in prediction_ids:
            resource = self._get_prediction_resource(prediction_id)
            payloads.append(resource["data"])
        result = compare_prediction_payloads(
            payloads, categories=categories, endpoints=endpoints
        )
        self.context.structured_payloads.append({"type": "comparison", "data": result})
        return self._envelope("compare_compounds", "ok", data=result)

    def _get_compound_resource(self, compound_id: str) -> dict:
        state = self.repository.get_business_state(self.context.session_id)["state"]
        resource_id = (state.get("compounds") or {}).get(compound_id)
        if not resource_id:
            raise AgentCoreError("RESOURCE_NOT_FOUND", "Compound was not found.", 404)
        return self.repository.get_resource(self.context.session_id, resource_id)["data"]

    def _get_prediction_resource(self, prediction_id: str) -> dict:
        state = self.repository.get_business_state(self.context.session_id)["state"]
        resource_id = (state.get("predictions") or {}).get(prediction_id)
        if not resource_id:
            raise AgentCoreError("RESOURCE_NOT_FOUND", "Prediction was not found.", 404)
        return self.repository.get_resource(self.context.session_id, resource_id)

    def _execute(self, tool_name: str, operation, arguments: dict[str, Any]) -> dict:
        if self.context.blocked:
            return self._envelope(tool_name, "error", error_code="AGENT_TOOL_LIMIT", message="Agent tool execution is blocked for this turn.")
        fingerprint = hashlib.sha256(
            json.dumps([tool_name, arguments], sort_keys=True, default=str).encode()
        ).hexdigest()
        if self.context.call_fingerprints.count(fingerprint) >= MAX_IDENTICAL_TOOL_CALLS:
            self.context.blocked = True
            return self._record_error(tool_name, "AGENT_TOOL_LOOP", "Repeated tool-call loop detected.")
        if len(self.context.call_fingerprints) >= MAX_TOOL_CALLS:
            self.context.blocked = True
            return self._record_error(
                tool_name, "AGENT_TOOL_LIMIT", "Agent tool-call limit reached."
            )
        self.context.call_fingerprints.append(fingerprint)
        if len(self.context.call_fingerprints) >= 6:
            recent = self.context.call_fingerprints[-6:]
            if recent[0] == recent[2] == recent[4] and recent[1] == recent[3] == recent[5]:
                self.context.blocked = True
                return self._record_error(tool_name, "AGENT_TOOL_LOOP", "Alternating tool-call loop detected.")
        try:
            result = operation()
        except (
            AgentCoreError,
            CompoundResolutionError,
            PredictionServiceError,
            InputQualityError,
            ComparisonError,
            BatchError,
        ) as exc:
            return self._record_error(
                tool_name,
                getattr(exc, "code", "TOOL_FAILED"),
                str(exc),
            )
        try:
            validated = ToolResultEnvelope.model_validate(result).model_dump(mode="json")
        except ValidationError:
            return self._record_error(
                tool_name, "TOOL_RESULT_INVALID", "Tool result failed schema validation."
            )
        self.context.tool_activity.append(
            {
                "tool_name": tool_name,
                "status": "completed",
                "resource_id": validated.get("resource_id"),
                "error_code": None,
            }
        )
        return validated

    def _record_error(self, tool_name: str, code: str, message: str) -> dict:
        self.context.tool_activity.append(
            {
                "tool_name": tool_name,
                "status": "error",
                "resource_id": None,
                "error_code": code,
            }
        )
        return self._envelope(
            tool_name, "error", error_code=code, message=message
        )

    @staticmethod
    def _envelope(
        tool_name: str,
        status: str,
        *,
        data: dict | None = None,
        resource_id: str | None = None,
        error_code: str | None = None,
        message: str | None = None,
        provenance: dict | None = None,
    ) -> dict:
        return {
            "tool_name": tool_name,
            "status": status,
            "data": data,
            "resource_id": resource_id,
            "error_code": error_code,
            "message": message,
            "provenance": provenance or {},
        }
