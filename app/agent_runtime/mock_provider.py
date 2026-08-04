from __future__ import annotations

from app.agent_runtime.contracts import MockScenarioSelection
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.tool_service import AgentToolService


MOCK_AGENT_LABEL = "Mock Agent v1"
MOCK_CATALOG_VERSION = 1
MOCK_SCENARIO_IDS = (
    "success",
    "confirmation",
    "timeout",
    "tool_failure",
    "insufficient_evidence",
)
MISSING_PREDICTION_ID = "prediction_mock_v1_missing_fixture"
ABSENT_EVIDENCE_QUERY = (
    "What does the corpus say about quantum entanglement in tablet coatings?"
)


def validate_mock_scenario(
    provider_mode: str,
    selection: MockScenarioSelection | None,
) -> str | None:
    if provider_mode == "live":
        if selection is not None:
            raise AgentCoreError(
                "MOCK_SCENARIO_NOT_ALLOWED",
                "Mock scenarios are not accepted in live Agent mode.",
            )
        return None

    if selection is None:
        raise AgentCoreError(
            "MOCK_SCENARIO_REQUIRED",
            "Mock Agent mode requires an explicit versioned scenario.",
        )
    if selection.catalog_version != MOCK_CATALOG_VERSION:
        raise AgentCoreError(
            "MOCK_SCENARIO_VERSION_UNSUPPORTED",
            "The requested Mock Agent scenario catalog version is unsupported.",
        )
    if selection.id not in MOCK_SCENARIO_IDS:
        raise AgentCoreError(
            "MOCK_SCENARIO_UNKNOWN",
            "The requested Mock Agent scenario ID is unknown.",
        )
    return selection.id


def run_mock_scenario(scenario_id: str, tools: AgentToolService) -> str:
    """Run one fixed scenario through named public tool-service methods."""
    if scenario_id == "success":
        _require_result(tools.get_model_information(), status="ok")
        return mock_response_text(
            "The deterministic model-information tool completed"
        )
    if scenario_id == "confirmation":
        _require_result(tools.resolve_compound("CCO"), status="confirmation_required")
        return mock_response_text(
            "Review and confirm the resolved CCO structure; no prediction has run"
        )
    if scenario_id == "timeout":
        raise AgentCoreError(
            "AGENT_TIMEOUT",
            "The local Agent model timed out.",
            503,
            retryable=True,
        )
    if scenario_id == "tool_failure":
        _require_result(
            tools.get_prediction_results(MISSING_PREDICTION_ID),
            status="error",
            error_code="RESOURCE_NOT_FOUND",
        )
        return mock_response_text(
            "The fixed missing prediction fixture exercised the normal tool-error path"
        )
    if scenario_id == "insufficient_evidence":
        result = _require_result(
            tools.search_adme_evidence(ABSENT_EVIDENCE_QUERY),
            status="ok",
        )
        data = result.get("data") or {}
        if data.get("status") != "no_evidence" or data.get("claims") != []:
            raise _scenario_failed()
        return mock_response_text(
            "The approved local evidence corpus returned no evidence and no claims"
        )
    raise AgentCoreError(
        "MOCK_SCENARIO_UNKNOWN",
        "The requested Mock Agent scenario ID is unknown.",
    )


def mock_response_text(detail: str) -> str:
    return f"{MOCK_AGENT_LABEL}: {detail}; it is not a scientific conclusion."


def _require_result(
    result: dict,
    *,
    status: str,
    error_code: str | None = None,
) -> dict:
    if result.get("status") != status:
        raise _scenario_failed()
    if error_code is not None and result.get("error_code") != error_code:
        raise _scenario_failed()
    return result


def _scenario_failed() -> AgentCoreError:
    return AgentCoreError(
        "MOCK_SCENARIO_FAILED",
        "The Mock Agent scenario could not produce its deterministic fixture.",
        500,
    )
