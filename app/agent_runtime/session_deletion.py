from __future__ import annotations

from uuid import uuid4

from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository


DELETED_CATEGORIES = [
    "current session record",
    "conversation messages",
    "business and page state",
    "confirmations and pending actions",
    "session-owned Agent resources",
    "session audit events",
]
RETAINED_CATEGORIES = [
    "shared Batch uploads and jobs",
    "application evidence and model files",
    "minimal hashed deletion receipt",
]


class SessionDeletionService:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def prepare(self, session_id: str, *, expected_state_version: int) -> dict:
        action_id = f"action_{uuid4().hex}"
        action, counts = self.repository.prepare_session_deletion(
            session_id,
            expected_state_version=expected_state_version,
            action_id=action_id,
        )
        return {
            "action": _public_action(action),
            "counts": counts,
            "deleted": DELETED_CATEGORIES,
            "retained": RETAINED_CATEGORIES,
        }

    def decide(
        self,
        session_id: str,
        action_id: str,
        *,
        decision: str,
        expected_state_version: int,
    ) -> dict:
        if decision == "reject":
            self.repository.reject_session_deletion(
                session_id,
                action_id,
                expected_state_version=expected_state_version,
            )
            return {
                "status": "rejected",
                "deleted_at": None,
                "counts": None,
                "retained": RETAINED_CATEGORIES,
            }
        if decision != "approve":
            raise AgentCoreError("INVALID_REQUEST", "Deletion decision is invalid.", 422)
        receipt = self.repository.delete_session_atomically(
            session_id,
            action_id,
            expected_state_version=expected_state_version,
        )
        return {
            "status": "deleted",
            "deleted_at": receipt["deleted_at"],
            "counts": receipt["counts"],
            "retained": RETAINED_CATEGORIES,
        }


def _public_action(action: dict) -> dict:
    return {
        key: action[key]
        for key in (
            "action_id",
            "session_id",
            "action_type",
            "status",
            "expected_state_version",
            "created_at",
            "expires_at",
            "consumed_at",
        )
    } | {"payload": {}}
