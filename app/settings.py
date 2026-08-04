from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, cast


class AgentSettingsError(RuntimeError):
    code = "AGENT_NOT_CONFIGURED"


AgentProviderMode = Literal["live", "mock"]


@dataclass(frozen=True)
class AgentSettings:
    enabled: bool
    base_url: str | None
    api_key: str | None
    model: str | None
    connect_timeout_seconds: float | None
    read_timeout_seconds: float | None
    total_timeout_seconds: float | None
    hosted_tracing_disabled: bool
    provider_mode: AgentProviderMode = "live"


@lru_cache(maxsize=1)
def get_agent_settings() -> AgentSettings:
    """Load Agent-only settings without affecting the existing application."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    enabled = _read_bool("AGENT_ENABLED", default=False)
    provider_mode = get_agent_provider_mode()
    if provider_mode == "mock":
        return AgentSettings(
            enabled=enabled,
            base_url=None,
            api_key=None,
            model=None,
            connect_timeout_seconds=None,
            read_timeout_seconds=None,
            total_timeout_seconds=None,
            hosted_tracing_disabled=_read_bool(
                "OPENAI_AGENTS_DISABLE_TRACING", default=True
            ),
            provider_mode=provider_mode,
        )

    base_url = _required("AGENT_LLM_BASE_URL")
    api_key = _required("AGENT_LLM_API_KEY")
    model = _required("AGENT_LLM_MODEL")
    connect_timeout = _positive_float("AGENT_LLM_CONNECT_TIMEOUT_SECONDS")
    read_timeout = _positive_float("AGENT_LLM_READ_TIMEOUT_SECONDS")
    total_timeout = _positive_float("AGENT_LLM_TOTAL_TIMEOUT_SECONDS")
    if total_timeout < connect_timeout:
        raise AgentSettingsError(
            "AGENT_LLM_TOTAL_TIMEOUT_SECONDS must be at least the connect timeout."
        )

    return AgentSettings(
        enabled=enabled,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        connect_timeout_seconds=connect_timeout,
        read_timeout_seconds=read_timeout,
        total_timeout_seconds=total_timeout,
        hosted_tracing_disabled=_read_bool(
            "OPENAI_AGENTS_DISABLE_TRACING", default=True
        ),
        provider_mode=provider_mode,
    )


def get_agent_provider_mode() -> AgentProviderMode:
    """Read the explicit Agent execution mode without loading live credentials."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    value = os.getenv("AGENT_PROVIDER_MODE", "live").strip().lower()
    if value not in {"live", "mock"}:
        raise AgentSettingsError(
            "AGENT_PROVIDER_MODE must be either 'live' or 'mock'."
        )
    return cast(AgentProviderMode, value)


def is_agent_enabled() -> bool:
    """Read only the feature flag so disabled routes never require provider settings."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return _read_bool("AGENT_ENABLED", default=False)


def _required(name: str) -> str:
    try:
        value = os.environ[name].strip()
    except KeyError as exc:
        raise AgentSettingsError(f"Missing required Agent setting: {name}.") from exc
    if not value:
        raise AgentSettingsError(f"Agent setting must not be empty: {name}.")
    return value


def _positive_float(name: str) -> float:
    value = _required(name)
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AgentSettingsError(f"Agent setting must be numeric: {name}.") from exc
    if parsed <= 0:
        raise AgentSettingsError(f"Agent setting must be positive: {name}.")
    return parsed


def _read_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise AgentSettingsError(f"Agent setting must be a boolean: {name}.")
