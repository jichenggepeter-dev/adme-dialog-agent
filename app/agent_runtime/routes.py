from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Query

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
)
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.runtime import AgentRuntime, default_repository_path
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


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest) -> dict:
    require_agent_enabled()
    return await get_agent_runtime().chat(request)


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
