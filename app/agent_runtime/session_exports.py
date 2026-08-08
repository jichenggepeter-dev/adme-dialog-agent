from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from typing import Any

from app.agent_runtime.contracts import SessionExportDocument
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository


SESSION_EXPORT_SCHEMA_VERSION = "1.0"
MAX_EXPORT_MESSAGES = 500
MAX_EXPORT_CONFIRMATIONS = 100
MAX_EXPORT_ACTIVITIES = 200
MAX_EXPORT_RESOURCE_MANIFEST = 100
MAX_SELECTED_RESOURCES = 20
MAX_SESSION_EXPORT_BYTES = 1_000_000

INCLUDED_FIELDS = [
    "session metadata",
    "conversation messages",
    "confirmation summaries",
    "bounded activity history",
    "active resource manifest",
    "explicitly selected compound and prediction resources",
]
EXCLUDED_FIELDS = [
    "credential fields and credential-looking values",
    "internal and system prompts",
    "message metadata and confirmation payloads",
    "full audit summaries and provider metadata",
    "raw prediction and Batch resource contents",
]
ALLOWED_RESOURCE_TYPES = {"compound", "prediction"}
CREDENTIAL_PATTERNS = (
    re.compile(r"session_[0-9a-f]{32}"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?:gh[pousr]|glpat|hf)_[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(
        r"-----BEGIN [^-\n]*PRIVATE KEY-----.*?-----END [^-\n]*PRIVATE KEY-----",
        re.DOTALL,
    ),
)


class SessionExportService:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def prepare(
        self,
        session_id: str,
        *,
        export_format: str,
        expected_state_version: int,
        resource_ids: list[str],
    ) -> dict:
        if export_format not in {"json", "markdown"}:
            raise AgentCoreError("INVALID_REQUEST", "Export format is not supported.", 422)
        if len(resource_ids) > MAX_SELECTED_RESOURCES or len(resource_ids) != len(set(resource_ids)):
            raise AgentCoreError(
                "INVALID_REQUEST", "Export resource identifiers must be unique and bounded.", 422
            )
        snapshot = self._snapshot(session_id, resource_ids)
        self._validate_snapshot(snapshot)
        snapshot_taken_at = datetime.now(UTC).isoformat()
        counts = _snapshot_counts(snapshot)
        action = self.repository.create_pending_action(
            session_id,
            "session_export_v1",
            {
                "format": export_format,
                "resource_ids": resource_ids,
                "snapshot_hash": _snapshot_hash(snapshot),
                "snapshot_taken_at": snapshot_taken_at,
                "schema_version": SESSION_EXPORT_SCHEMA_VERSION,
                "counts": counts,
                "max_export_bytes": MAX_SESSION_EXPORT_BYTES,
            },
            expected_state_version,
        )
        return {
            "action": _public_action(action),
            "schema_version": SESSION_EXPORT_SCHEMA_VERSION,
            "included": INCLUDED_FIELDS,
            "excluded": EXCLUDED_FIELDS,
            "max_export_bytes": MAX_SESSION_EXPORT_BYTES,
            "snapshot_taken_at": snapshot_taken_at,
            "counts": counts,
        }

    def decide(
        self,
        session_id: str,
        action_id: str,
        *,
        decision: str,
        expected_state_version: int,
        correlation_id: str,
    ) -> dict:
        action = self.repository.get_pending_action(session_id, action_id)
        if action["action_type"] != "session_export_v1":
            raise AgentCoreError("ACTION_NOT_ALLOWED", "Pending action is not an export.", 404)
        if decision == "reject":
            self.repository.transition_pending_action(
                session_id, action_id, "reject", expected_state_version
            )
            return _empty_result("rejected")
        if decision != "approve":
            raise AgentCoreError("INVALID_REQUEST", "Export decision is invalid.", 422)

        claimed = False
        try:
            action = self.repository.approve_and_claim_pending_action(
                session_id, action_id, expected_state_version
            )
            claimed = True
            payload = action["payload"]
            if payload.get("schema_version") != SESSION_EXPORT_SCHEMA_VERSION:
                raise AgentCoreError(
                    "TOOL_RESULT_INVALID", "Export proposal schema is invalid.", 409
                )
            resource_ids = payload.get("resource_ids")
            export_format = payload.get("format")
            if not isinstance(resource_ids, list) or export_format not in {"json", "markdown"}:
                raise AgentCoreError(
                    "TOOL_RESULT_INVALID", "Export proposal payload is invalid.", 409
                )
            snapshot = self._snapshot(session_id, resource_ids)
            self._validate_snapshot(snapshot)
            if _snapshot_hash(snapshot) != payload.get("snapshot_hash"):
                raise AgentCoreError(
                    "EXPORT_STALE",
                    "The session changed after the export confirmation was prepared. Please review a new export.",
                    409,
                )

            snapshot_taken_at = payload.get("snapshot_taken_at")
            if not isinstance(snapshot_taken_at, str):
                raise AgentCoreError(
                    "TOOL_RESULT_INVALID", "Export proposal snapshot is invalid.", 409
                )
            document = self._document(snapshot, snapshot_taken_at)
            content = (
                document.model_dump_json(indent=2)
                if export_format == "json"
                else _render_markdown(document)
            )
            _assert_no_credentials(content)
            size_bytes = len(content.encode("utf-8"))
            if size_bytes > MAX_SESSION_EXPORT_BYTES:
                raise AgentCoreError(
                    "EXPORT_LIMIT_EXCEEDED",
                    "The session export exceeds the documented size limit.",
                    413,
                )

            self.repository.finish_pending_action_with_audit(
                session_id,
                action_id,
                action_type="session_export_v1",
                correlation_id=correlation_id,
                event_type="session_export_succeeded",
                summary={
                    "format": export_format,
                    "schema_version": SESSION_EXPORT_SCHEMA_VERSION,
                    "message_count": len(snapshot["messages"]),
                    "confirmation_count": len(snapshot["confirmations"]),
                    "activity_count": len(snapshot["activity"]),
                    "resource_count": len(snapshot["resources"]),
                    "selected_resource_count": len(snapshot["selected_resources"]),
                    "size_bytes": size_bytes,
                },
            )
            extension = "json" if export_format == "json" else "md"
            return {
                "status": "succeeded",
                "filename": f"adme-session-export.{extension}",
                "media_type": "application/json" if export_format == "json" else "text/markdown",
                "content": content,
                "size_bytes": size_bytes,
                "schema_version": SESSION_EXPORT_SCHEMA_VERSION,
            }
        except Exception:
            if claimed:
                try:
                    self.repository.finish_pending_action(session_id, action_id, succeeded=False)
                except AgentCoreError:
                    pass
            raise

    def _snapshot(self, session_id: str, resource_ids: list[str]) -> dict:
        return self.repository.get_session_export_snapshot(
            session_id,
            resource_ids,
            message_limit=MAX_EXPORT_MESSAGES,
            confirmation_limit=MAX_EXPORT_CONFIRMATIONS,
            activity_limit=MAX_EXPORT_ACTIVITIES,
            resource_limit=MAX_EXPORT_RESOURCE_MANIFEST,
        )

    def _validate_snapshot(self, snapshot: dict) -> None:
        bounds = (
            ("messages", MAX_EXPORT_MESSAGES),
            ("confirmations", MAX_EXPORT_CONFIRMATIONS),
            ("resources", MAX_EXPORT_RESOURCE_MANIFEST),
        )
        if any(len(snapshot[name]) > limit for name, limit in bounds):
            raise AgentCoreError(
                "EXPORT_LIMIT_EXCEEDED", "The session exceeds the documented export item limits.", 413
            )
        for resource in snapshot["selected_resources"]:
            if resource["resource_type"] not in ALLOWED_RESOURCE_TYPES:
                raise AgentCoreError(
                    "EXPORT_RESOURCE_NOT_ALLOWED",
                    "Only compound and prediction resources may be included in a session export.",
                    422,
                )

    def _document(self, snapshot: dict, snapshot_taken_at: str) -> SessionExportDocument:
        session = snapshot["session"]
        prediction_modes = set(snapshot["prediction_modes"])
        prediction_mode = (
            "mixed"
            if len(prediction_modes) > 1
            else next(iter(prediction_modes), "unknown")
        )
        return SessionExportDocument.model_validate(
            {
                "exported_at": datetime.now(UTC),
                "snapshot_taken_at": snapshot_taken_at,
                "prediction_mode": prediction_mode,
                "session": {
                    key: session[key]
                    for key in ("status", "created_at", "expires_at", "state_version")
                },
                "included_fields": INCLUDED_FIELDS,
                "excluded_fields": EXCLUDED_FIELDS,
                "limits": {
                    "messages": MAX_EXPORT_MESSAGES,
                    "confirmations": MAX_EXPORT_CONFIRMATIONS,
                    "activities": MAX_EXPORT_ACTIVITIES,
                    "resource_manifest": MAX_EXPORT_RESOURCE_MANIFEST,
                    "selected_resources": MAX_SELECTED_RESOURCES,
                    "final_bytes": MAX_SESSION_EXPORT_BYTES,
                },
                "messages": [
                    {**message, "content": _redact_credentials(message["content"])}
                    for message in snapshot["messages"]
                ],
                "confirmations": [
                    {
                        **confirmation,
                        "result_resource_id": (
                            confirmation["result_resource_id"]
                            if confirmation["result_resource_id"] in {
                                resource["resource_id"] for resource in snapshot["resources"]
                            }
                            else None
                        ),
                    }
                    for confirmation in snapshot["confirmations"]
                ],
                "activity": {
                    "limit": MAX_EXPORT_ACTIVITIES,
                    "total_available": snapshot["activity_total"],
                    "included_count": len(snapshot["activity"]),
                    "older_omitted_count": max(
                        0, snapshot["activity_total"] - len(snapshot["activity"])
                    ),
                    "events": [
                        {
                            key: event[key]
                            for key in (
                                "event_type",
                                "tool_name",
                                "duration_ms",
                                "status",
                                "error_code",
                                "created_at",
                            )
                        }
                        for event in snapshot["activity"]
                    ],
                },
                "resources": snapshot["resources"],
                "selected_resources": [
                    {
                        **{key: resource[key] for key in (
                            "resource_id",
                            "resource_type",
                            "content_hash",
                            "size_bytes",
                            "created_at",
                            "expires_at",
                        )},
                        "data": _project_resource(resource),
                    }
                    for resource in snapshot["selected_resources"]
                ],
            }
        )


def _public_action(action: dict) -> dict:
    return {
        key: action[key]
        for key in (
            "action_id",
            "session_id",
            "action_type",
            "status",
            "expected_state_version",
            "created_at",
            "expires_at",
            "consumed_at",
        )
    } | {"payload": {}}


def _empty_result(status: str) -> dict:
    return {
        "status": status,
        "filename": None,
        "media_type": None,
        "content": None,
        "size_bytes": None,
        "schema_version": SESSION_EXPORT_SCHEMA_VERSION,
    }


def _snapshot_counts(snapshot: dict) -> dict[str, int]:
    return {
        "messages": len(snapshot["messages"]),
        "confirmations": len(snapshot["confirmations"]),
        "activities": len(snapshot["activity"]),
        "resources": len(snapshot["resources"]),
        "selected_resources": len(snapshot["selected_resources"]),
    }


def _snapshot_hash(snapshot: dict) -> str:
    fingerprint = {
        **snapshot,
        "session": {
            key: snapshot["session"][key]
            for key in ("session_id", "status", "created_at", "expires_at", "state_version")
        },
    }
    encoded = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _project_resource(resource: dict) -> dict:
    data = resource["data"]
    if not isinstance(data, dict):
        raise AgentCoreError("TOOL_RESULT_INVALID", "Export resource is invalid.", 409)
    if resource["resource_type"] == "compound":
        return {
            "kind": "compound",
            "compound_id": _optional_text(data.get("compound_id")),
            "input_query": _optional_text(data.get("input_query")),
            "preferred_name": _optional_text(data.get("preferred_name")),
            "pubchem_cid": data.get("pubchem_cid"),
            "molecular_formula": _optional_text(data.get("molecular_formula")),
            "molecular_weight": data.get("molecular_weight"),
            "canonical_smiles": _optional_text(data.get("canonical_smiles")),
            "isomeric_smiles": _optional_text(data.get("isomeric_smiles")),
            "data_source": _optional_text(data.get("data_source")),
            "warnings": _text_list(data.get("warnings")),
        }
    if resource["resource_type"] == "prediction":
        mode = data.get("prediction_mode")
        if mode not in {"mock", "real"}:
            raise AgentCoreError("TOOL_RESULT_INVALID", "Prediction mode is invalid.", 409)
        categories: list[dict] = []
        enriched = data.get("enriched_predictions")
        if isinstance(enriched, dict):
            for category in sorted(enriched):
                entries = enriched[category]
                if not isinstance(category, str) or not isinstance(entries, list):
                    continue
                projected = [_project_endpoint(entry) for entry in entries if isinstance(entry, dict)]
                if projected:
                    categories.append(
                        {"category": _redact_credentials(category), "endpoints": projected}
                    )
        return {
            "kind": "prediction",
            "prediction_id": _optional_text(data.get("prediction_id")),
            "compound_id": _optional_text(data.get("compound_id")),
            "prediction_mode": mode,
            "summary": _optional_text(data.get("summary")),
            "disclaimer": _optional_text(data.get("disclaimer")),
            "warnings": _text_list(data.get("warnings")),
            "categories": categories,
        }
    raise AgentCoreError("EXPORT_RESOURCE_NOT_ALLOWED", "Export resource is not allowed.", 422)


def _project_endpoint(value: dict) -> dict:
    endpoint = value.get("raw_name") or value.get("raw_key") or value.get("display_name")
    if not isinstance(endpoint, str) or not endpoint:
        raise AgentCoreError("TOOL_RESULT_INVALID", "Prediction endpoint is invalid.", 409)
    return {
        "endpoint": _redact_credentials(endpoint),
        "display_name": _optional_text(value.get("display_name")),
        "value": value.get("value"),
        "output_type": _optional_text(value.get("output_type")),
        "positive_class": _optional_text(value.get("positive_class")),
        "supports_probability_language": value.get("supports_probability_language"),
        "unit": _optional_text(value.get("unit")),
        "unit_verified": value.get("unit_verified"),
        "metadata_status": _optional_text(value.get("metadata_status")),
    }


def _optional_text(value: Any) -> str | None:
    return _redact_credentials(value) if isinstance(value, str) else None


def _text_list(value: Any) -> list[str]:
    return [_redact_credentials(item) for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _redact_credentials(value: str) -> str:
    redacted = value
    for pattern in CREDENTIAL_PATTERNS:
        redacted = pattern.sub("[REDACTED_CREDENTIAL]", redacted)
    return redacted


def _assert_no_credentials(content: str) -> None:
    if any(pattern.search(content) for pattern in CREDENTIAL_PATTERNS):
        raise AgentCoreError(
            "EXPORT_SENSITIVE_CONTENT", "The export contains prohibited credential material.", 422
        )


def _render_markdown(document: SessionExportDocument) -> str:
    lines = [
        "# ADME Dialog Agent session export",
        "",
        f"- Schema version: {document.export_schema_version}",
        f"- Exported at: {document.exported_at.isoformat()}",
        f"- Snapshot taken at: {document.snapshot_taken_at.isoformat()}",
        f"- Prediction mode: {document.prediction_mode}",
        "",
        "## Included",
        "",
        *[f"- {item}" for item in document.included_fields],
        "",
        "## Excluded",
        "",
        *[f"- {item}" for item in document.excluded_fields],
        "",
        "## Conversation",
        "",
    ]
    for message in document.messages:
        lines.extend(
            [
                f"### {message.role.title()} · {message.created_at.isoformat()}",
                "",
                *[f"> {html.escape(line)}" for line in message.content.splitlines() or [""]],
                "",
            ]
        )
    lines.extend(["## Confirmation summaries", ""])
    for confirmation in document.confirmations:
        lines.append(
            f"- `{confirmation.confirmation_id}` — {confirmation.type}, {confirmation.status}, created {confirmation.created_at.isoformat()}"
        )
    if not document.confirmations:
        lines.append("- None")
    lines.extend(["", "## Activity", ""])
    for event in document.activity.events:
        tool = f" · {event.tool_name}" if event.tool_name else ""
        lines.append(f"- {event.created_at.isoformat()} · {event.event_type}{tool} · {event.status}")
    if not document.activity.events:
        lines.append("- None")
    if document.activity.older_omitted_count:
        lines.append(f"- {document.activity.older_omitted_count} older events intentionally omitted")
    lines.extend(["", "## Resource manifest", ""])
    for resource in document.resources:
        lines.append(
            f"- `{resource.resource_id}` — {resource.resource_type}, {resource.size_bytes} bytes"
        )
    if not document.resources:
        lines.append("- None")
    if document.selected_resources:
        lines.extend(["", "## Selected resource data", ""])
        for resource in document.selected_resources:
            lines.extend(
                [
                    f"### {resource.resource_type} · `{resource.resource_id}`",
                    "",
                    *[
                        f"    {line}"
                        for line in json.dumps(
                            resource.data.model_dump(mode="json"),
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        ).splitlines()
                    ],
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
