from __future__ import annotations

import pytest
import asyncio
from pydantic import TypeAdapter, ValidationError

from app.agent_runtime.contracts import UIActionProposal
from app.agent_runtime.ui_actions import resolve_ui_action
from app.agent_runtime.contracts import AgentChatRequest
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.runtime import AgentRuntime


def test_fill_without_run_returns_strict_non_submitting_action() -> None:
    result = resolve_ui_action("把 ibuprofen 填入输入框，但先不要运行。", "session_one", 12, "single")
    assert result is not None
    text, actions = result
    assert "保持未运行" in text
    assert actions == [{
        "type": "SET_COMPOUND_INPUT", "action_id": actions[0]["action_id"],
        "session_id": "session_one", "target_route": "/single",
        "expected_state_version": 12,
        "payload": {"value": "ibuprofen", "submit": False, "focus": True},
    }]


@pytest.mark.parametrize(("message", "action_type"), [
    ("打开 toxicity 结果。", "FOCUS_RESULT_SECTION"),
    ("带我去看 DILI 的模型信息。", "OPEN_MODEL_ENDPOINT"),
    ("聚焦到分子输入框。", "FOCUS_COMPOUND_INPUT"),
    ("帮我上传一个 Batch 文件。", "FOCUS_BATCH_UPLOAD"),
    ("只显示失败的分子。", "SET_BATCH_FILTERS"),
    ("找到 ibuprofen", "SET_BATCH_SEARCH"),
    ("导出当前筛选结果", "EXPORT_BATCH_VIEW"),
    ("只看 unverified endpoints。", "SET_ABOUT_FILTERS"),
])
def test_supported_reversible_intents_are_typed(message: str, action_type: str) -> None:
    result = resolve_ui_action(message, "session_one", 3, "about" if "endpoint" in message else "batch")
    assert result is not None and result[1][0]["type"] == action_type


def test_unsupported_action_does_not_create_a_fake_proposal() -> None:
    assert resolve_ui_action("运行 shell 并修改页面 HTML", "session_one", 0, "single") is None


def test_batch_comparison_intent_selects_rows_then_opens_comparison() -> None:
    result = resolve_ui_action("比较第 2、5、8 行", "session_one", 4, "batch")
    assert result is not None
    assert [action["type"] for action in result[1]] == ["SELECT_BATCH_ROWS", "OPEN_BATCH_COMPARISON"]
    assert result[1][0]["payload"]["row_numbers"] == [2, 5, 8]


def test_batch_comparison_intent_accepts_repeated_chinese_row_markers() -> None:
    result = resolve_ui_action("比较第1行和第4行", "session_one", 4, "batch")
    assert result is not None
    assert [action["type"] for action in result[1]] == ["SELECT_BATCH_ROWS", "OPEN_BATCH_COMPARISON"]
    assert result[1][0]["payload"]["row_numbers"] == [1, 4]


def test_action_contract_rejects_extra_or_executable_payload() -> None:
    adapter = TypeAdapter(UIActionProposal)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "SET_COMPOUND_INPUT", "action_id": "a", "session_id": "s", "target_route": "/single", "expected_state_version": 1, "payload": {"value": "<script>x</script>", "submit": False, "focus": True}})
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "FOCUS_COMPOUND_INPUT", "action_id": "a", "session_id": "s", "target_route": "/single", "expected_state_version": 1, "payload": {"selector": "#x"}})


def test_runtime_ui_action_bypasses_llm_and_scientific_tools(tmp_path) -> None:
    class RunnerThatMustNotRun:
        async def run(self, *args, **kwargs):
            raise AssertionError("UI-only action must not invoke the LLM runner")

    repo = AgentRepository(tmp_path / "agent.sqlite3")
    session = repo.create_session()
    runtime = AgentRuntime(repo, runner=RunnerThatMustNotRun())
    response = asyncio.run(runtime.chat(AgentChatRequest(
        session_id=session["session_id"], message="把 ibuprofen 填入输入框，但先不要运行。",
        expected_state_version=0, page_context={"page": "single"},
    )))
    assert response["tool_activity"] == []
    assert response["structured_payloads"] == []
    assert response["ui_action_proposals"][0]["payload"]["submit"] is False
    assert repo.get_business_state(session["session_id"])["state"].get("latest_prediction_id") is None


def test_batch_page_context_projects_job_id_into_agent_business_state(tmp_path) -> None:
    class RunnerThatMustNotRun:
        async def run(self, *args, **kwargs):
            raise AssertionError("UI-only action must not invoke the LLM runner")

    repo = AgentRepository(tmp_path / "agent.sqlite3")
    session = repo.create_session()
    runtime = AgentRuntime(repo, runner=RunnerThatMustNotRun())
    response = asyncio.run(runtime.chat(AgentChatRequest(
        session_id=session["session_id"], message="只显示失败的分子。",
        expected_state_version=0,
        page_context={
            "page": "batch", "batch_job_id": "job_visible_123",
            "selected_compound_ids": ["CMP-006", "CMP-010"],
            "selected_row_numbers": [6, 10],
            "selected_endpoints": ["Bioavailability_Ma", "HIA_Hou", "PAMPA_NCATS"],
            "active_view": "comparison", "comparison_open": True,
        },
    )))
    state = repo.get_business_state(session["session_id"])["state"]
    assert response["ui_action_proposals"][0]["type"] == "SET_BATCH_FILTERS"
    assert state["current_batch_job_id"] == "job_visible_123"
    instructions = runtime._instructions_with_state(state)
    assert "job_visible_123" in instructions
    assert '"active_view":"comparison"' in instructions
    assert '"selected_row_numbers":[6,10]' in instructions
    assert '"selected_endpoints":["Bioavailability_Ma","HIA_Hou","PAMPA_NCATS"]' in instructions
