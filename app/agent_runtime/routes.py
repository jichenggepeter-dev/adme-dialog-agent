from __future__ import annotations

from functools import lru_cache
import re
from uuid import uuid4

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.agent_runtime.contracts import (
    AgentChatRequest,
    AgentChatResponse,
    AgentSession,
    ConfirmationRequest,
    CompoundConfirmation,
    MessagePage,
    PendingAction,
    PendingActionRequest,
    ResourceResponse,
    SessionDeletionDecisionRequest,
    SessionDeletionPrepareRequest,
    SessionDeletionProposal,
    SessionDeletionResult,
    SessionExportDecisionRequest,
    SessionExportPrepareRequest,
    SessionExportProposal,
    SessionExportResult,
)
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.runtime import AgentRuntime, default_repository_path
from app.agent_runtime.session_deletion import SessionDeletionService
from app.agent_runtime.session_exports import SessionExportService
from app.agent_runtime.streaming import STREAM_MEDIA_TYPE, stream_agent_chat
from app.settings import is_agent_enabled


router = APIRouter(prefix="/agent", tags=["agent"])


@lru_cache(maxsize=1)
def get_agent_runtime() -> AgentRuntime:
    return AgentRuntime(AgentRepository(default_repository_path()))


def require_agent_enabled() -> None:
    if not is_agent_enabled():
        raise AgentCoreError(
            "AGENT_DISABLED", "The conversational Agent is disabled.", 503
        )


@router.post("/sessions", response_model=AgentSession)
def create_agent_session() -> dict:
    require_agent_enabled()
    return _session_contract(get_agent_runtime().create_session())


@router.get("/sessions/{session_id}", response_model=AgentSession)
def get_agent_session(session_id: str) -> dict:
    require_agent_enabled()
    return _session_contract(get_agent_runtime().repository.get_session(session_id))


@router.get("/sessions/{session_id}/messages", response_model=MessagePage)
def get_agent_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    require_agent_enabled()
    return get_agent_runtime().repository.list_messages(session_id, limit, offset)


@router.post(
    "/sessions/{session_id}/deletions",
    response_model=SessionDeletionProposal,
)
def prepare_session_deletion(
    session_id: str,
    deletion_request: SessionDeletionPrepareRequest,
    response: Response,
) -> dict:
    require_agent_enabled()
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return SessionDeletionService(get_agent_runtime().repository).prepare(
        session_id,
        expected_state_version=deletion_request.expected_state_version,
    )


@router.post(
    "/sessions/{session_id}/deletions/{action_id}",
    response_model=SessionDeletionResult,
)
def decide_session_deletion(
    session_id: str,
    action_id: str,
    deletion_request: SessionDeletionDecisionRequest,
    response: Response,
) -> dict:
    require_agent_enabled()
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return SessionDeletionService(get_agent_runtime().repository).decide(
        session_id,
        action_id,
        decision=deletion_request.decision,
        expected_state_version=deletion_request.expected_state_version,
    )


@router.post(
    "/sessions/{session_id}/exports",
    response_model=SessionExportProposal,
)
def prepare_session_export(
    session_id: str,
    export_request: SessionExportPrepareRequest,
    response: Response,
) -> dict:
    require_agent_enabled()
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return SessionExportService(get_agent_runtime().repository).prepare(
        session_id,
        export_format=export_request.format,
        expected_state_version=export_request.expected_state_version,
        resource_ids=export_request.resource_ids,
    )


@router.post(
    "/sessions/{session_id}/exports/{action_id}",
    response_model=SessionExportResult,
)
def decide_session_export(
    session_id: str,
    action_id: str,
    export_request: SessionExportDecisionRequest,
    request: Request,
    response: Response,
) -> dict:
    require_agent_enabled()
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return SessionExportService(get_agent_runtime().repository).decide(
        session_id,
        action_id,
        decision=export_request.decision,
        expected_state_version=export_request.expected_state_version,
        correlation_id=_correlation_id(request),
    )


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest) -> dict:
    require_agent_enabled()
    return await get_agent_runtime().chat(request)


@router.post("/chat/stream")
async def agent_chat_stream(
    request: AgentChatRequest,
    http_request: Request,
) -> StreamingResponse:
    require_agent_enabled()
    correlation_id = _correlation_id(http_request)
    message_id = f"msg_{uuid4().hex}"
    return StreamingResponse(
        stream_agent_chat(
            get_agent_runtime(),
            request,
            message_id=message_id,
            correlation_id=correlation_id,
        ),
        media_type=STREAM_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/confirm", response_model=AgentChatResponse)
def agent_confirm(request: ConfirmationRequest) -> dict:
    require_agent_enabled()
    return get_agent_runtime().confirm(request)


@router.post("/actions/decide", response_model=AgentChatResponse)
def decide_pending_action(request: PendingActionRequest) -> dict:
    require_agent_enabled()
    return get_agent_runtime().decide_pending_action(request)


@router.get("/actions/{action_id}", response_model=PendingAction)
def get_pending_action_status(action_id: str, session_id: str = Query(...)) -> dict:
    require_agent_enabled()
    return get_agent_runtime().repository.get_pending_action(session_id, action_id)


@router.get("/confirmations/{confirmation_id}", response_model=CompoundConfirmation)
def get_confirmation_status(confirmation_id: str, session_id: str = Query(...)) -> dict:
    require_agent_enabled()
    value = get_agent_runtime().repository.get_confirmation(session_id, confirmation_id)
    return {key: value[key] for key in CompoundConfirmation.model_fields}


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
def get_agent_resource(resource_id: str, session_id: str = Query(...)) -> dict:
    require_agent_enabled()
    return get_agent_runtime().resources.get(session_id, resource_id)


def _session_contract(session: dict) -> dict:
    return {
        key: session[key]
        for key in (
            "session_id",
            "status",
            "created_at",
            "expires_at",
            "state_version",
        )
    }


def _correlation_id(request: Request) -> str:
    supplied = request.headers.get("X-Correlation-ID", "")
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", supplied):
        return supplied
    return uuid4().hex
