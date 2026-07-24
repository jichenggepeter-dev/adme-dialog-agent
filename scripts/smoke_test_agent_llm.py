from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import Agent, Runner, function_tool  # noqa: E402

from app.agent_runtime.provider import (  # noqa: E402
    AgentProviderError,
    audit_event,
    create_agent_provider,
    run_with_total_timeout,
)
from app.settings import AgentSettings, AgentSettingsError, get_agent_settings  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


async def run_compatibility_smoke(
    settings: AgentSettings | None = None,
) -> dict[str, Any]:
    settings = settings or get_agent_settings()
    provider = create_agent_provider(settings)
    report: dict[str, Any] = {
        "base_url": settings.base_url,
        "model": settings.model,
        "hosted_tracing_disabled": settings.hosted_tracing_disabled,
        "scenarios": {},
    }

    try:
        report["scenarios"]["text"] = await _text_scenario(provider)
        tool_result, success_tool = await _tool_success_scenario(provider)
        report["scenarios"]["tool_success"] = tool_result
        report["scenarios"]["tool_error"] = await _tool_error_scenario(provider)
        report["scenarios"]["multi_turn"] = await _multi_turn_scenario(
            provider, success_tool
        )
        report["scenarios"]["timeout_mapping"] = await _timeout_scenario(settings)
        report["scenarios"]["tracing"] = {
            "ok": settings.hosted_tracing_disabled,
            "hosted_tracing": "disabled",
            "local_audit_logging": "enabled",
        }
    finally:
        await provider.client.close()

    report["ok"] = all(
        scenario.get("ok") is True for scenario in report["scenarios"].values()
    )
    return report


async def _text_scenario(provider) -> dict[str, Any]:
    agent = Agent(
        name="Phase 1 text compatibility probe",
        instructions="Follow the user's exact output request. No tools are available.",
        model=provider.model,
    )
    result = await _run(
        provider,
        agent,
        "Say exactly: ADME_AGENT_TEXT_OK",
        tool_name=None,
    )
    output = str(result.final_output).strip()
    return {"ok": output == "ADME_AGENT_TEXT_OK", "output": output}


async def _tool_success_scenario(provider) -> tuple[dict[str, Any], Any]:
    calls: list[str] = []

    @function_tool(strict_mode=True)
    def lookup_compound_label(query: str) -> dict[str, str]:
        """Return a fixed local compatibility label for a compound query."""
        calls.append(query)
        return {"query": query, "status": "found", "label": "Aspirin"}

    agent = Agent(
        name="Phase 1 tool compatibility probe",
        instructions=(
            "Call lookup_compound_label exactly once with query aspirin. "
            "Then state the returned label and status. Never invent tool results."
        ),
        tools=[lookup_compound_label],
        model=provider.model,
    )
    result = await _run(
        provider,
        agent,
        'Use lookup_compound_label(query="aspirin") and report its local result.',
        tool_name="lookup_compound_label",
    )
    output = str(result.final_output).strip()
    ok = calls == ["aspirin"] and "aspirin" in output.lower() and "found" in output.lower()
    return (
        {
            "ok": ok,
            "tool_calls": len(calls),
            "arguments": {"query": calls[0]} if calls else None,
            "output": output,
        },
        (agent, result, calls),
    )


async def _tool_error_scenario(provider) -> dict[str, Any]:
    calls: list[str] = []

    @function_tool(strict_mode=True)
    def lookup_missing_label(query: str) -> dict[str, str]:
        """Return a stable local not-found envelope for compatibility testing."""
        calls.append(query)
        return {"status": "error", "error_code": "COMPOUND_NOT_FOUND"}

    agent = Agent(
        name="Phase 1 tool error compatibility probe",
        instructions=(
            "Call lookup_missing_label exactly once. If it returns an error, state only "
            "that the compound was not found and include the error code. Do not retry or "
            "invent a compound."
        ),
        tools=[lookup_missing_label],
        model=provider.model,
    )
    result = await _run(
        provider,
        agent,
        'Use lookup_missing_label(query="not-a-real-compound") once.',
        tool_name="lookup_missing_label",
    )
    output = str(result.final_output).strip()
    ok = calls == ["not-a-real-compound"] and "COMPOUND_NOT_FOUND" in output
    return {"ok": ok, "tool_calls": len(calls), "output": output}


async def _multi_turn_scenario(provider, success_tool) -> dict[str, Any]:
    agent, first_result, calls = success_tool
    history = first_result.to_input_list()
    history.append(
        {
            "role": "user",
            "content": (
                "Without calling any tool again, what label did the local tool return "
                "in the previous turn? Reply with the label only."
            ),
        }
    )
    result = await _run(provider, agent, history, tool_name=None)
    output = str(result.final_output).strip()
    return {
        "ok": output.lower() == "aspirin" and calls == ["aspirin"],
        "tool_calls_across_turns": len(calls),
        "output": output,
    }


async def _timeout_scenario(settings: AgentSettings) -> dict[str, Any]:
    short_settings = AgentSettings(
        **{
            **settings.__dict__,
            "total_timeout_seconds": 0.001,
        }
    )
    try:
        await run_with_total_timeout(asyncio.sleep(0.05), short_settings)
    except AgentProviderError as exc:
        return {"ok": exc.code == "AGENT_TIMEOUT", "error_code": exc.code}
    return {"ok": False, "error_code": None}


async def _run(provider, agent: Agent, input_value, tool_name: str | None):
    correlation_id = uuid4().hex
    started_at = time.monotonic()
    try:
        result = await run_with_total_timeout(
            Runner.run(agent, input=input_value), provider.settings
        )
    except AgentProviderError as exc:
        audit_event(
            correlation_id=correlation_id,
            model=provider.settings.model,
            tool_name=tool_name,
            status="error",
            error_code=exc.code,
            started_at=started_at,
        )
        raise
    audit_event(
        correlation_id=correlation_id,
        model=provider.settings.model,
        tool_name=tool_name,
        status="ok",
        started_at=started_at,
    )
    return result


def main() -> int:
    try:
        report = asyncio.run(run_compatibility_smoke())
    except (AgentSettingsError, AgentProviderError) as exc:
        code = getattr(exc, "code", "AGENT_PROVIDER_ERROR")
        print(json.dumps({"ok": False, "error_code": code, "message": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
