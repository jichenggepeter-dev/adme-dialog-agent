from __future__ import annotations

import re
from typing import Any
from uuid import uuid4
from pydantic import TypeAdapter

from app.agent_runtime.contracts import UIActionProposal

ACTION_ADAPTER = TypeAdapter(UIActionProposal)


def resolve_ui_action(
    message: str, session_id: str, state_version: int, page: str | None
) -> tuple[str, list[dict[str, Any]]] | None:
    """Resolve a narrow allowlist of explicit, reversible interface intents."""
    text = " ".join(message.strip().split())
    lowered = text.lower()

    input_match = re.search(
        r"(?:把|将)\s*([A-Za-z0-9+_.\-]+)\s*(?:填入|输入到|放入).*(?:输入框|单分子)|"
        r"(?:fill|put|enter)\s+([A-Za-z0-9+_.\-]+)\s+(?:into|in).*(?:input|field)",
        text,
        re.IGNORECASE,
    )
    if input_match:
        value = input_match.group(1) or input_match.group(2)
        return _result(
            "我会把 %s 填入单分子输入框，并保持未运行状态。" % value,
            "SET_COMPOUND_INPUT", session_id, state_version, "/single",
            {"value": value, "submit": False, "focus": True},
        )

    if any(phrase in lowered for phrase in ("聚焦到分子输入框", "focus compound input", "focus the compound input")):
        return _result("我会聚焦到单分子输入框。", "FOCUS_COMPOUND_INPUT", session_id, state_version, "/single", {})

    chinese_upload = "上传" in lowered and any(token in lowered for token in ("batch", "批次", "文件", "csv", "tsv", "smi"))
    if chinese_upload or any(phrase in lowered for phrase in ("upload batch", "upload csv", "upload a file")):
        return _result("我会打开 Batch 上传工作流并聚焦文件选择区。请选择要分析的 CSV、TSV 或 SMI 文件。", "FOCUS_BATCH_UPLOAD", session_id, state_version, "/batch", {})

    endpoint_match = re.search(r"(?:打开|查看|带我去看)\s*([A-Za-z0-9_.-]+).*(?:模型信息|metadata|model information)", text, re.IGNORECASE)
    if endpoint_match:
        endpoint = endpoint_match.group(1)
        return _result("我会打开 %s 的模型信息。" % endpoint, "OPEN_MODEL_ENDPOINT", session_id, state_version, "/about", {"target": endpoint})

    result_match = re.search(r"(?:打开|聚焦|查看)\s*(toxicity|absorption|distribution|metabolism|excretion).*(?:结果)?", lowered)
    if result_match:
        category = result_match.group(1)
        return _result("我会聚焦到 %s 结果。" % category.title(), "FOCUS_RESULT_SECTION", session_id, state_version, "/single", {"target": category})

    endpoint_only = re.search(r"(?:打开|查看)\s*([A-Za-z][A-Za-z0-9_.-]+)\s*$", text, re.IGNORECASE)
    if endpoint_only and page == "about":
        endpoint = endpoint_only.group(1)
        return _result("我会打开 %s 的端点信息。" % endpoint, "OPEN_MODEL_ENDPOINT", session_id, state_version, "/about", {"target": endpoint})

    if any(phrase in lowered for phrase in ("只显示失败", "只看失败", "show only failed")):
        return _result("我会只显示预测失败的分子。", "SET_BATCH_FILTERS", session_id, state_version, "/batch", {"prediction_status": "failed"})
    if any(phrase in lowered for phrase in ("只看 valid", "只显示 valid", "show only valid")):
        return _result("我会只显示验证通过的分子。", "SET_BATCH_FILTERS", session_id, state_version, "/batch", {"validation_status": "valid"})
    if any(phrase in lowered for phrase in ("第一条失败", "first failed")):
        return _result("我会选中第一条失败记录。", "SELECT_BATCH_ROW", session_id, state_version, "/batch", {"target": "first-failed"})
    search_match = re.search(r"(?:找到|搜索|查找|search for|find)\s+([A-Za-z0-9+_.\-]+)", text, re.IGNORECASE)
    if search_match and page == "batch":
        query = search_match.group(1)
        return _result(f"我会在当前批次中搜索 {query}。", "SET_BATCH_SEARCH", session_id, state_version, "/batch", {"query": query})
    rows_match = re.search(
        r"(?:比较|compare)\s*((?:(?:第\s*)?\d+\s*(?:行)?\s*(?:和|与|及|,|，|、|\s)*){2,5})",
        text,
        re.IGNORECASE,
    )
    if rows_match and page == "batch":
        rows = [int(value) for value in re.findall(r"\d+", rows_match.group(1))][:5]
        if 2 <= len(rows) <= 5:
            first = _action("SELECT_BATCH_ROWS", session_id, state_version, "/batch", {"row_numbers": rows, "purpose": "comparison"})
            second = _action("OPEN_BATCH_COMPARISON", session_id, state_version, "/batch", {})
            return "我会选择这些已完成的批次记录，并打开中立比较。", [first, second]
    endpoints_match = re.search(r"(?:只显示|显示|focus on)\s+([A-Za-z0-9_.\-、,，\s]+)\s*(?:端点|endpoints?)", text, re.IGNORECASE)
    if endpoints_match and page == "batch":
        endpoints = [value for value in re.split(r"[、,，\s]+", endpoints_match.group(1).strip()) if value][:20]
        if endpoints:
            return _result("我会更新当前批次的端点列。", "SET_BATCH_ENDPOINTS", session_id, state_version, "/batch", {"endpoints": endpoints})
    if page == "batch" and any(phrase in lowered for phrase in ("导出错误", "export errors")):
        return _result("我会导出当前批次的错误记录。", "EXPORT_BATCH_VIEW", session_id, state_version, "/batch", {"kind": "errors"})
    if page == "batch" and any(phrase in lowered for phrase in ("导出当前筛选", "export filtered")):
        return _result("我会导出当前筛选结果。", "EXPORT_BATCH_VIEW", session_id, state_version, "/batch", {"kind": "filtered"})
    if "打开当前 batch job" in lowered or "open current batch job" in lowered:
        return _result("我会打开当前批处理任务。", "OPEN_BATCH_JOB", session_id, state_version, "/batch", {"target": "current"})

    if any(phrase in lowered for phrase in ("只看 unverified", "only unverified")):
        return _result("我会只显示未验证元数据的端点。", "SET_ABOUT_FILTERS", session_id, state_version, "/about", {"metadata_status": "unverified"})
    category_match = re.search(r"(?:切换到|只看)\s*(absorption|distribution|metabolism|excretion|toxicity)", lowered)
    if category_match and page == "about":
        category = category_match.group(1)
        return _result("我会切换到 %s 端点。" % category, "SET_ABOUT_FILTERS", session_id, state_version, "/about", {"category": category})
    return None


def _result(text: str, action_type: str, session_id: str, version: int, route: str, payload: dict[str, Any]):
    return text, [_action(action_type, session_id, version, route, payload)]


def _action(action_type: str, session_id: str, version: int, route: str, payload: dict[str, Any]) -> dict:
    raw = {"type": action_type, "action_id": f"action_{uuid4().hex}", "session_id": session_id, "target_route": route, "expected_state_version": version, "payload": payload}
    return ACTION_ADAPTER.validate_python(raw).model_dump(mode="json")
