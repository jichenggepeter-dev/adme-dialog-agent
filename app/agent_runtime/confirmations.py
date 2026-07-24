from __future__ import annotations

from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.repositories import AgentRepository


class ConfirmationEngine:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def propose_compound(
        self,
        session_id: str,
        compound: dict,
        expected_state_version: int,
    ) -> dict:
        canonical_smiles = compound.get("canonical_smiles")
        if not canonical_smiles:
            raise AgentCoreError(
                "TOOL_RESULT_INVALID", "Resolved compound lacks canonical SMILES.", 500
            )
        return self.repository.create_confirmation(
            session_id,
            payload=compound,
            canonical_smiles=canonical_smiles,
            expected_state_version=expected_state_version,
        )

    def decide(
        self,
        session_id: str,
        confirmation_id: str,
        decision: str,
        expected_state_version: int,
    ) -> dict:
        target = "approved" if decision == "approve" else "rejected"
        return self.repository.transition_confirmation(
            session_id,
            confirmation_id,
            "awaiting_confirmation",
            target,
            expected_state_version,
        )

    def mark_executing(self, confirmation: dict) -> dict:
        return self.repository.transition_confirmation(
            confirmation["session_id"],
            confirmation["confirmation_id"],
            "approved",
            "executing",
            confirmation["expected_state_version"],
        )

    def mark_finished(self, confirmation: dict, succeeded: bool) -> dict:
        return self.repository.transition_confirmation(
            confirmation["session_id"],
            confirmation["confirmation_id"],
            "executing",
            "succeeded" if succeeded else "failed",
            confirmation["expected_state_version"],
        )
