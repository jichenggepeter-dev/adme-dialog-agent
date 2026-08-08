from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, TypeVar

import httpx
from agents import ModelBehaviorError, OpenAIResponsesModel, set_tracing_disabled
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.settings import AgentSettings, AgentSettingsError


logger = logging.getLogger("app.agent_audit")
T = TypeVar("T")


class AgentProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AgentProvider:
    client: AsyncOpenAI
    model: OpenAIResponsesModel
    settings: AgentSettings


def create_agent_provider(settings: AgentSettings) -> AgentProvider:
    """Build the SDK Responses adapter without creating a product Agent."""
    if settings.provider_mode != "live":
        raise AgentSettingsError(
            "The OpenAI-compatible provider is available only in live mode."
        )
    set_tracing_disabled(settings.hosted_tracing_disabled)
    timeout = httpx.Timeout(
        connect=settings.connect_timeout_seconds,
        read=settings.read_timeout_seconds,
        write=settings.read_timeout_seconds,
        pool=settings.connect_timeout_seconds,
    )
    client = AsyncOpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=timeout,
        max_retries=0,
    )
    model = OpenAIResponsesModel(model=settings.model, openai_client=client)
    return AgentProvider(client=client, model=model, settings=settings)


async def run_with_total_timeout(
    operation: Awaitable[T], settings: AgentSettings
) -> T:
    try:
        async with asyncio.timeout(settings.total_timeout_seconds):
            return await operation
    except Exception as exc:
        raise map_provider_error(exc) from None


def map_provider_error(exc: Exception) -> AgentProviderError:
    if isinstance(exc, (TimeoutError, APITimeoutError)):
        return AgentProviderError("AGENT_TIMEOUT", "The local Agent model timed out.")
    if isinstance(exc, AuthenticationError):
        return AgentProviderError(
            "AGENT_AUTHENTICATION_FAILED",
            "The local Agent model rejected its credentials.",
        )
    if isinstance(exc, RateLimitError):
        return AgentProviderError(
            "AGENT_RATE_LIMITED", "The local Agent model is rate limited."
        )
    if isinstance(exc, APIConnectionError):
        return AgentProviderError(
            "AGENT_PROVIDER_UNAVAILABLE", "The local Agent model is unavailable."
        )
    if isinstance(exc, APIStatusError):
        return AgentProviderError(
            "AGENT_PROVIDER_ERROR", "The local Agent model returned an error."
        )
    if isinstance(exc, AgentProviderError):
        return exc
    if isinstance(exc, ModelBehaviorError):
        return AgentProviderError(
            "AGENT_PROVIDER_INVALID_RESPONSE",
            "The local Agent model returned an invalid response.",
        )
    return AgentProviderError(
        "AGENT_PROVIDER_ERROR", "The local Agent model request failed."
    )


def audit_event(
    *,
    correlation_id: str,
    model: str,
    status: str,
    started_at: float,
    tool_name: str | None = None,
    error_code: str | None = None,
) -> None:
    logger.info(
        "agent_audit correlation_id=%s model=%s tool=%s duration_ms=%d status=%s error_code=%s",
        correlation_id,
        model,
        tool_name or "none",
        int((time.monotonic() - started_at) * 1000),
        status,
        error_code or "none",
    )
