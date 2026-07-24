from __future__ import annotations

from app.agent_runtime.repositories import AgentRepository


class BusinessStateStore:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def get(self, session_id: str) -> dict:
        return self.repository.get_business_state(session_id)

    def update(self, session_id: str, patch: dict, expected_version: int) -> dict:
        return self.repository.update_business_state(
            session_id, patch, expected_version=expected_version
        )
