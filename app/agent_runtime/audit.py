from __future__ import annotations

import hashlib
from typing import Any

from app.agent_runtime.repositories import AgentRepository


def record_local_audit(
    repository: AgentRepository,
    *,
    session_id: str | None,
    correlation_id: str,
    event_type: str,
    status: str,
    model: str | None = None,
    tool_name: str | None = None,
    duration_ms: int | None = None,
    error_code: str | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    repository.add_audit_event(
        session_id=session_id,
        correlation_id=correlation_id,
        event_type=event_type,
        status=status,
        model=model,
        tool_name=tool_name,
        duration_ms=duration_ms,
        error_code=error_code,
        summary={
            **_redact_summary(summary or {}),
            **({"session_hash": hashlib.sha256(session_id.encode()).hexdigest()[:16]} if session_id else {}),
        },
    )


def _redact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in summary.items():
        normalized = key.lower()
        if any(token in normalized for token in ("api_key", "authorization", "prompt", "payload", "raw")):
            continue
        if normalized in {"smiles", "query", "message"} and isinstance(value, str):
            redacted[f"{key}_hash"] = hashlib.sha256(value.encode()).hexdigest()[:16]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            redacted[key] = value
        elif isinstance(value, list):
            redacted[f"{key}_count"] = len(value)
        elif isinstance(value, dict):
            redacted[key] = _redact_summary(dict(list(value.items())[:20]))
    return redacted
