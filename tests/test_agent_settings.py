from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, Mock

import pytest

from app.agent_runtime.provider import (
    AgentProviderError,
    audit_event,
    create_agent_provider,
    run_with_total_timeout,
)
from app.settings import AgentSettings, AgentSettingsError, get_agent_settings


ENV = {
    "AGENT_ENABLED": "false",
    "AGENT_LLM_BASE_URL": "http://127.0.0.1:18080/v1",
    "AGENT_LLM_API_KEY": "unit-test-secret",
    "AGENT_LLM_MODEL": "unit-test-model",
    "AGENT_LLM_CONNECT_TIMEOUT_SECONDS": "2",
    "AGENT_LLM_READ_TIMEOUT_SECONDS": "3",
    "AGENT_LLM_TOTAL_TIMEOUT_SECONDS": "4",
    "OPENAI_AGENTS_DISABLE_TRACING": "1",
}


def apply_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    get_agent_settings.cache_clear()


def test_settings_require_explicit_model(monkeypatch: pytest.MonkeyPatch) -> None:
    apply_env(monkeypatch)
    monkeypatch.setenv("AGENT_LLM_MODEL", "")
    with pytest.raises(AgentSettingsError, match="AGENT_LLM_MODEL"):
        get_agent_settings()


def test_settings_are_explicit_and_agent_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    apply_env(monkeypatch)
    settings = get_agent_settings()
    assert settings.enabled is False
    assert settings.model == "unit-test-model"
    assert settings.base_url == "http://127.0.0.1:18080/v1"
    assert settings.hosted_tracing_disabled is True


def test_provider_builds_responses_model_without_logging_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import app.agent_runtime.provider as provider_module

    apply_env(monkeypatch)
    settings = get_agent_settings()
    fake_client = Mock()
    fake_client.close = AsyncMock()
    fake_model = Mock()
    fake_model.model = "unit-test-model"
    client_factory = Mock(return_value=fake_client)
    model_factory = Mock(return_value=fake_model)
    tracing_switch = Mock()
    monkeypatch.setattr(provider_module, "AsyncOpenAI", client_factory)
    monkeypatch.setattr(provider_module, "OpenAIResponsesModel", model_factory)
    monkeypatch.setattr(provider_module, "set_tracing_disabled", tracing_switch)
    caplog.set_level(logging.INFO, logger="app.agent_audit")
    provider = create_agent_provider(settings)
    audit_event(
        correlation_id="test-correlation",
        model=settings.model,
        status="ok",
        started_at=0,
    )
    assert provider.model.model == "unit-test-model"
    assert client_factory.call_args.kwargs["base_url"] == settings.base_url
    assert client_factory.call_args.kwargs["api_key"] == "unit-test-secret"
    model_factory.assert_called_once_with(
        model="unit-test-model", openai_client=fake_client
    )
    tracing_switch.assert_called_once_with(True)
    assert "unit-test-secret" not in caplog.text
    asyncio.run(provider.client.close())


def test_controlled_timeout_maps_to_stable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    apply_env(monkeypatch)
    base = get_agent_settings()
    settings = AgentSettings(**{**base.__dict__, "total_timeout_seconds": 0.001})

    async def run() -> None:
        with pytest.raises(AgentProviderError) as caught:
            await run_with_total_timeout(asyncio.sleep(0.05), settings)
        assert caught.value.code == "AGENT_TIMEOUT"
        assert "traceback" not in str(caught.value).lower()

    asyncio.run(run())
