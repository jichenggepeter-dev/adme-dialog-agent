from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.agent_runtime.contracts import (
    AgentChatRequest,
    AgentChatResponse,
    AgentStreamConfirmationRequired,
    AgentStreamError,
    AgentStreamEvent,
    AgentStreamHeartbeat,
    AgentStreamMessageDelta,
    AgentStreamResponseCompleted,
    AgentStreamToolCompleted,
    AgentStreamToolStarted,
)
from app.agent_runtime.errors import AgentCoreError
from app.api_contract import STREAM_EVENT_VERSION

if TYPE_CHECKING:
    from app.agent_runtime.runtime import AgentRuntime


logger = logging.getLogger(__name__)
STREAM_MEDIA_TYPE = "application/x-ndjson"
MESSAGE_DELTA_CHARS = 64


def split_validated_text(text: str) -> Iterator[str]:
    for start in range(0, len(text), MESSAGE_DELTA_CHARS):
        delta = text[start : start + MESSAGE_DELTA_CHARS]
        if delta:
            yield delta


def response_events(
    response: dict,
    *,
    session_id: str,
    message_id: str,
    correlation_id: str,
    start_sequence: int,
) -> Iterator[AgentStreamEvent]:
    validated = AgentChatResponse.model_validate(response)
    sequence = start_sequence
    envelope = {
        "version": STREAM_EVENT_VERSION,
        "session_id": session_id,
        "message_id": message_id,
        "correlation_id": correlation_id,
    }

    for activity in validated.tool_activity:
        started_at = activity.started_at or datetime.now(UTC)
        completed_at = activity.completed_at or started_at
        yield AgentStreamToolStarted(
            **envelope,
            sequence=sequence,
            occurred_at=started_at,
            tool_name=activity.tool_name,
        )
        sequence += 1
        yield AgentStreamToolCompleted(
            **envelope,
            sequence=sequence,
            occurred_at=completed_at,
            tool_activity=activity,
        )
        sequence += 1

    for delta in split_validated_text(validated.text):
        yield AgentStreamMessageDelta(
            **envelope,
            sequence=sequence,
            delta=delta,
        )
        sequence += 1

    if validated.pending_confirmation is not None or validated.pending_action is not None:
        yield AgentStreamConfirmationRequired(
            **envelope,
            sequence=sequence,
            pending_confirmation=validated.pending_confirmation,
            pending_action=validated.pending_action,
        )
        sequence += 1

    yield AgentStreamResponseCompleted(
        **envelope,
        sequence=sequence,
        structured_payloads=validated.structured_payloads,
        pending_confirmation=validated.pending_confirmation,
        pending_action=validated.pending_action,
        tool_activity=validated.tool_activity,
        ui_action_proposals=validated.ui_action_proposals,
        warnings=validated.warnings,
        state_version=validated.state_version,
    )


def encode_event(event: AgentStreamEvent) -> bytes:
    return (event.model_dump_json() + "\n").encode("utf-8")


async def stream_agent_chat(
    runtime: AgentRuntime,
    request: AgentChatRequest,
    *,
    message_id: str,
    correlation_id: str,
) -> AsyncIterator[bytes]:
    envelope = {
        "version": STREAM_EVENT_VERSION,
        "session_id": request.session_id,
        "message_id": message_id,
        "correlation_id": correlation_id,
    }
    sequence = 0
    yield encode_event(AgentStreamHeartbeat(**envelope, sequence=sequence))
    sequence += 1

    try:
        response = await runtime.chat(
            request,
            assistant_message_id=message_id,
            correlation_id=correlation_id,
        )
        events = list(
            response_events(
                response,
                session_id=request.session_id,
                message_id=message_id,
                correlation_id=correlation_id,
                start_sequence=sequence,
            )
        )
        for event in events:
            yield encode_event(event)
    except asyncio.CancelledError:
        raise
    except AgentCoreError as exc:
        yield encode_event(
            AgentStreamError(
                **envelope,
                sequence=sequence,
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
            )
        )
    except Exception:
        logger.exception("Agent streaming request failed", extra={"correlation_id": correlation_id})
        yield encode_event(
            AgentStreamError(
                **envelope,
                sequence=sequence,
                code="INTERNAL_ERROR",
                message="The Agent request could not be completed.",
                retryable=False,
            )
        )
