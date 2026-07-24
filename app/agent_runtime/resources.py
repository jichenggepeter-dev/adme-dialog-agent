from __future__ import annotations

from typing import Any

from app.agent_runtime.repositories import AgentRepository


class ResourceStore:
    """Bounded JSON resource access; never a generic file interface."""

    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def put(
        self, session_id: str, resource_type: str, data: dict[str, Any] | list[Any]
    ) -> dict:
        return self.repository.put_resource(session_id, resource_type, data)

    def get(self, session_id: str, resource_id: str) -> dict:
        return self.repository.get_resource(session_id, resource_id)
