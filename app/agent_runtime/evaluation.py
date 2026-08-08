from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent_runtime.routes import get_agent_runtime
from app.agent_runtime.tool_service import AgentToolService
from app.main import app
from app.settings import get_agent_settings


ExecutionMode = Literal["deterministic_rules", "mock_provider", "real_provider"]


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvalTurn(EvalModel):
    message: str = Field(min_length=1, max_length=8_000)
    page_context: dict[str, Any] | None = None


class ExpectedArguments(EvalModel):
    operation: str = Field(min_length=1)
    arguments: dict[str, Any]


class AgentEvalCase(EvalModel):
    case_id: str = Field(pattern=r"^[a-z0-9_]+$")
    category: str = Field(min_length=1)
    execution_mode: ExecutionMode
    turns: list[EvalTurn] = Field(min_length=1)
    mock_scenario_id: str | None
    expected_tools: list[str]
    forbidden_tools: list[str]
    expected_arguments: list[ExpectedArguments]
    requires_confirmation: bool
    prohibited_language: list[str] = Field(min_length=1)
    expected_error_code: str | None
    expected_policy_code: str | None

    @model_validator(mode="after")
    def validate_expectations(self) -> AgentEvalCase:
        if self.execution_mode == "real_provider" and self.mock_scenario_id is not None:
            raise ValueError("Real-provider cases cannot select a Mock scenario.")
        if self.execution_mode != "real_provider" and not self.mock_scenario_id:
            raise ValueError("Deterministic cases require a Mock scenario fixture.")
        if set(self.expected_tools) & set(self.forbidden_tools):
            raise ValueError("Expected and forbidden tools must not overlap.")
        expected_argument_tools = [item.operation for item in self.expected_arguments]
        if expected_argument_tools != self.expected_tools:
            raise ValueError("Expected arguments must align with expected tool order.")
        return self


class AgentEvalDataset(EvalModel):
    schema_version: Literal["1.0"]
    suite_id: str
    description: str
    validation_boundary: str
    cases: list[AgentEvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> AgentEvalDataset:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Agent evaluation case IDs must be unique.")
        return self


def load_dataset(path: Path) -> AgentEvalDataset:
    return AgentEvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def run_evaluation(
    dataset: AgentEvalDataset,
    *,
    modes: set[str],
    categories: set[str] | None = None,
    case_ids: set[str] | None = None,
) -> dict[str, Any]:
    selected = [
        case
        for case in dataset.cases
        if case.execution_mode in modes
        and (not categories or case.category in categories)
        and (not case_ids or case.case_id in case_ids)
    ]
    if not selected:
        raise ValueError("No Agent evaluation cases matched the selected filters.")
    results: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="adme-agent-eval-") as directory:
        environment = {
            "AGENT_ENABLED": "true",
            "AGENT_DB_PATH": str(Path(directory) / "agent.sqlite3"),
            "ADME_MOCK_MODE": "true",
            "OPENAI_AGENTS_DISABLE_TRACING": "1",
        }
        with patch.dict(os.environ, environment, clear=False):
            get_agent_settings.cache_clear()
            get_agent_runtime.cache_clear()
            with TestClient(app) as client:
                for case in selected:
                    results.append(_run_case(client, case))
    get_agent_settings.cache_clear()
    get_agent_runtime.cache_clear()

    available = Counter(case.execution_mode for case in dataset.cases)
    by_mode = {
        mode: {
            "available": available[mode],
            "selected": sum(result["execution_mode"] == mode for result in results),
            "passed": sum(
                result["execution_mode"] == mode and result["passed"]
                for result in results
            ),
            "failed": sum(
                result["execution_mode"] == mode and not result["passed"]
                for result in results
            ),
        }
        for mode in ("deterministic_rules", "mock_provider", "real_provider")
    }
    return {
        "report_schema_version": "1.0",
        "suite_id": dataset.suite_id,
        "dataset_schema_version": dataset.schema_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "selected_modes": sorted(modes),
        "selected_categories": sorted(categories) if categories else [],
        "validation_boundary": dataset.validation_boundary,
        "summary": {
            "selected": len(results),
            "passed": sum(result["passed"] for result in results),
            "failed": sum(not result["passed"] for result in results),
            "by_execution_mode": by_mode,
        },
        "results": results,
    }


def _run_case(client: TestClient, case: AgentEvalCase) -> dict[str, Any]:
    provider_mode = "live" if case.execution_mode == "real_provider" else "mock"
    os.environ["AGENT_PROVIDER_MODE"] = provider_mode
    get_agent_settings.cache_clear()

    session_response = client.post("/agent/sessions")
    if session_response.status_code != 200:
        return _failed_setup_result(case, session_response)
    session = session_response.json()
    state_version = session["state_version"]
    observed_calls: list[dict[str, Any]] = []
    response_text: list[str] = []
    confirmation_seen = False
    error_code: str | None = None
    policy_codes: list[str] = []
    original_execute = AgentToolService._execute

    def capture_execute(
        service: AgentToolService,
        tool_name: str,
        operation,
        arguments: dict[str, Any],
    ) -> dict:
        observed_calls.append(
            {"operation": tool_name, "arguments": _json_value(arguments)}
        )
        return original_execute(service, tool_name, operation, arguments)

    with patch.object(AgentToolService, "_execute", capture_execute):
        for turn in case.turns:
            payload: dict[str, Any] = {
                "session_id": session["session_id"],
                "message": turn.message,
                "expected_state_version": state_version,
            }
            if turn.page_context is not None:
                payload["page_context"] = turn.page_context
            if case.mock_scenario_id is not None:
                payload["mock_scenario"] = {
                    "catalog_version": 1,
                    "id": case.mock_scenario_id,
                }
            response = client.post("/agent/chat", json=payload)
            body = response.json()
            if response.status_code != 200:
                error_code = (body.get("error") or {}).get("code")
                break
            response_text.append(body["text"])
            state_version = body["state_version"]
            confirmation_seen = confirmation_seen or body["pending_confirmation"] is not None
            for item in body["structured_payloads"]:
                if item["type"] == "out_of_scope" and item["data"].get("error_code"):
                    policy_codes.append(item["data"]["error_code"])
            for action in body["ui_action_proposals"]:
                observed_calls.append(
                    {
                        "operation": f"ui_action:{action['type']}",
                        "arguments": action["payload"],
                    }
                )

    failures = _evaluate_case(
        case,
        observed_calls=observed_calls,
        response_text="\n".join(response_text),
        confirmation_seen=confirmation_seen,
        error_code=error_code,
        policy_codes=policy_codes,
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "execution_mode": case.execution_mode,
        "passed": not failures,
        "failures": failures,
        "observed_tools": [item["operation"] for item in observed_calls],
        "observed_arguments": observed_calls,
        "confirmation_observed": confirmation_seen,
        "error_code": error_code,
        "policy_codes": policy_codes,
        "response_preview": "\n".join(response_text)[:320],
    }


def _evaluate_case(
    case: AgentEvalCase,
    *,
    observed_calls: list[dict[str, Any]],
    response_text: str,
    confirmation_seen: bool,
    error_code: str | None,
    policy_codes: list[str],
) -> list[str]:
    failures: list[str] = []
    observed_tools = [item["operation"] for item in observed_calls]
    if observed_tools != case.expected_tools:
        failures.append(
            f"Expected tools {case.expected_tools}, observed {observed_tools}."
        )
    forbidden = sorted(set(observed_tools) & set(case.forbidden_tools))
    if forbidden:
        failures.append(f"Forbidden tools were observed: {forbidden}.")
    expected_arguments = [item.model_dump(mode="json") for item in case.expected_arguments]
    if observed_calls != expected_arguments:
        failures.append("Observed tool arguments did not match the declared sequence.")
    if confirmation_seen != case.requires_confirmation:
        failures.append(
            f"Expected confirmation={case.requires_confirmation}, observed={confirmation_seen}."
        )
    lowered = response_text.lower()
    prohibited = [phrase for phrase in case.prohibited_language if phrase.lower() in lowered]
    if prohibited:
        failures.append(f"Prohibited language was observed: {prohibited}.")
    if error_code != case.expected_error_code:
        failures.append(
            f"Expected error {case.expected_error_code}, observed {error_code}."
        )
    if case.expected_policy_code not in (policy_codes or [None]):
        failures.append(
            f"Expected policy code {case.expected_policy_code}, observed {policy_codes}."
        )
    return failures


def _failed_setup_result(case: AgentEvalCase, response) -> dict[str, Any]:
    try:
        error_code = (response.json().get("error") or {}).get("code")
    except (AttributeError, ValueError):
        error_code = None
    return {
        "case_id": case.case_id,
        "category": case.category,
        "execution_mode": case.execution_mode,
        "passed": False,
        "failures": [f"Session setup failed with HTTP {response.status_code}."],
        "observed_tools": [],
        "observed_arguments": [],
        "confirmation_observed": False,
        "error_code": error_code,
        "policy_codes": [],
        "response_preview": "",
    }


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Agent evaluation report",
        "",
        f"- Suite: `{report['suite_id']}`",
        f"- Dataset schema: `{report['dataset_schema_version']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Selected modes: {', '.join(report['selected_modes'])}",
        f"- Result: {summary['passed']} passed, {summary['failed']} failed",
        "",
        f"> {report['validation_boundary']}",
        "",
        "## Execution modes",
        "",
        "| Mode | Available | Selected | Passed | Failed |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for mode, values in summary["by_execution_mode"].items():
        lines.append(
            f"| {mode} | {values['available']} | {values['selected']} | "
            f"{values['passed']} | {values['failed']} |"
        )
    lines.extend(["", "## Cases", ""])
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        lines.extend(
            [
                f"### {result['case_id']} — {status}",
                "",
                f"- Category: `{result['category']}`",
                f"- Mode: `{result['execution_mode']}`",
                f"- Tools: `{json.dumps(result['observed_tools'], ensure_ascii=False)}`",
                f"- Confirmation observed: `{str(result['confirmation_observed']).lower()}`",
                f"- Error code: `{result['error_code'] or 'none'}`",
            ]
        )
        for failure in result["failures"]:
            lines.append(f"- Failure: {failure}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
