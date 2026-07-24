from __future__ import annotations

import asyncio
import os

import pytest

from scripts.smoke_test_agent_llm import run_compatibility_smoke


pytestmark = pytest.mark.agent_llm_integration


@pytest.mark.skipif(
    os.getenv("RUN_AGENT_LLM_INTEGRATION", "").lower() not in {"1", "true", "yes"},
    reason="Set RUN_AGENT_LLM_INTEGRATION=true with the local Codex API running.",
)
def test_local_agent_sdk_compatibility() -> None:
    report = asyncio.run(run_compatibility_smoke())
    assert report["model"] == os.environ["AGENT_LLM_MODEL"]
    assert report["hosted_tracing_disabled"] is True
    assert report["ok"] is True
