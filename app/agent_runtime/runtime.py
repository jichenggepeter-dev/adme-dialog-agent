from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from agents import Agent, ModelSettings, RunConfig, Runner

from app.agent_runtime.audit import record_local_audit
from app.agent_runtime.confirmations import ConfirmationEngine
from app.agent_runtime.contracts import AgentChatRequest, ConfirmationRequest, PendingActionRequest
from app.agent_runtime.errors import AgentCoreError
from app.agent_runtime.guardrails import evaluate_input, validate_scientific_output
from app.agent_runtime.instructions import BASE_INSTRUCTIONS
from app.agent_runtime.provider import (
    AgentProviderError,
    create_agent_provider,
    run_with_total_timeout,
)
from app.agent_runtime.repositories import AgentRepository
from app.agent_runtime.resources import ResourceStore
from app.agent_runtime.tool_service import AgentToolService, ToolExecutionContext
from app.agent_runtime.ui_actions import resolve_ui_action
from app.agent_runtime.tools import ALLOWED_AGENT_TOOLS
from app.settings import AgentSettingsError, get_agent_settings
from app.tools.batch import BatchError, cancel_job, get_job, run_job_thread


class AgentRuntime:
    def __init__(self, repository: AgentRepository, runner=Runner):
        self.repository = repository
        self.runner = runner
        self.confirmations = ConfirmationEngine(repository)
        self.resources = ResourceStore(repository)

    def create_session(self) -> dict:
        return self.repository.create_session()

    async def chat(self, request: AgentChatRequest) -> dict:
        correlation_id = uuid4().hex
        started = time.monotonic()
        current = self.repository.get_business_state(request.session_id)
        if current["version"] != request.expected_state_version:
            raise AgentCoreError("ACTION_STALE", "Agent state version is stale.", 409)

        self.repository.add_message(request.session_id, "user", request.message)
        policy = evaluate_input(request.message)
        if not policy.allowed:
            return self._policy_response(
                request.session_id,
                policy.response or "Request blocked.",
                policy.code or "ACTION_NOT_ALLOWED",
                current["version"],
                correlation_id,
                started,
            )

        state_version = current["version"]
        if request.page_context is not None:
            page_state: dict[str, Any] = {
                "current_page": request.page_context.page,
                "page_context": request.page_context.model_dump(mode="json"),
            }
            if request.page_context.page == "batch":
                page_state["current_batch_job_id"] = request.page_context.batch_job_id
            updated = self.repository.update_business_state(
                request.session_id,
                page_state,
                expected_version=state_version,
            )
            state_version = updated["version"]

        context = ToolExecutionContext(
            session_id=request.session_id,
            repository=self.repository,
            state_version=state_version,
        )
        page = request.page_context.page if request.page_context is not None else business_page(current["state"])
        batch_job_id = request.page_context.batch_job_id if request.page_context is not None and request.page_context.page == "batch" else None
        batch_action = _batch_action_intent(request.message, batch_job_id)
        if batch_action is not None:
            result = AgentToolService(context).prepare_batch_action(batch_job_id, batch_action)
            if result["status"] != "confirmation_required":
                text = result.get("message") or "The batch action could not be prepared."
                assistant_message = self.repository.add_message(request.session_id, "assistant", text, metadata={"pending_action_error": result.get("error_code")})
                return {
                    "message_id": assistant_message["message_id"], "text": text,
                    "structured_payloads": [{"type": "error", "data": {"error_code": result.get("error_code")}}],
                    "pending_confirmation": None, "pending_action": None,
                    "tool_activity": context.tool_activity, "ui_action_proposals": [],
                    "warnings": [], "state_version": context.state_version,
                }
            text = "Please review and confirm the exact batch action below."
            assistant_message = self.repository.add_message(request.session_id, "assistant", text, metadata={"pending_action": batch_action})
            return {
                "message_id": assistant_message["message_id"], "text": text,
                "structured_payloads": [], "pending_confirmation": None,
                "pending_action": _pending_action_contract(context.pending_action),
                "tool_activity": context.tool_activity, "ui_action_proposals": [],
                "warnings": [], "state_version": context.state_version,
            }
        ui_intent = resolve_ui_action(request.message, request.session_id, state_version, page)
        if ui_intent is not None:
            text, actions = ui_intent
            assistant_message = self.repository.add_message(
                request.session_id, "assistant", text, metadata={"ui_action_count": len(actions)}
            )
            return {
                "message_id": assistant_message["message_id"],
                "text": text,
                "structured_payloads": [],
                "pending_confirmation": None,
                "pending_action": None,
                "tool_activity": [],
                "ui_action_proposals": actions,
                "warnings": [],
                "state_version": state_version,
            }
        try:
            settings = get_agent_settings()
            provider = create_agent_provider(settings)
        except AgentSettingsError as exc:
            raise AgentCoreError("AGENT_NOT_CONFIGURED", str(exc), 503) from None

        business = self.repository.get_business_state(request.session_id)["state"]
        instructions = self._instructions_with_state(business)
        agent = Agent(
            name="ADME Assistant",
            instructions=instructions,
            model=provider.model,
            tools=ALLOWED_AGENT_TOOLS,
            model_settings=ModelSettings(
                parallel_tool_calls=False,
                max_tokens=1_200,
                store=False,
                verbosity="low",
            ),
        )
        history = self.repository.recent_messages(request.session_id, limit=20)
        model_input = [
            {"role": item["role"], "content": item["content"]}
            for item in history
            if item["role"] in {"user", "assistant"}
        ]
        try:
            result = await run_with_total_timeout(
                self.runner.run(
                    agent,
                    input=model_input,
                    context=context,
                    max_turns=8,
                    run_config=RunConfig(
                        tracing_disabled=True,
                        trace_include_sensitive_data=False,
                        workflow_name="ADME Assistant",
                    ),
                ),
                settings,
            )
        except AgentProviderError as exc:
            record_local_audit(
                self.repository,
                session_id=request.session_id,
                correlation_id=correlation_id,
                event_type="agent_run",
                status="error",
                model=settings.model,
                duration_ms=int((time.monotonic() - started) * 1000),
                error_code=exc.code,
            )
            raise AgentCoreError(
                exc.code,
                str(exc),
                503,
                retryable=exc.code in {"AGENT_TIMEOUT", "AGENT_PROVIDER_UNAVAILABLE", "AGENT_PROVIDER_ERROR"},
            ) from None
        finally:
            await provider.client.close()

        text = str(result.final_output).strip()
        output_policy = validate_scientific_output(text, context.structured_payloads)
        if not output_policy.allowed:
            text = output_policy.response or "Response blocked by scientific policy."
            context.structured_payloads = [
                {
                    "type": "error",
                    "data": {"error_code": output_policy.code},
                }
            ]
        assistant_message = self.repository.add_message(
            request.session_id,
            "assistant",
            text,
            metadata={"tool_count": len(context.tool_activity)},
        )
        record_local_audit(
            self.repository,
            session_id=request.session_id,
            correlation_id=correlation_id,
            event_type="agent_run",
            status="ok" if output_policy.allowed else "blocked",
            model=settings.model,
            duration_ms=int((time.monotonic() - started) * 1000),
            error_code=None if output_policy.allowed else output_policy.code,
            summary={
                "tool_names": [item["tool_name"] for item in context.tool_activity],
                "structured_payload_count": len(context.structured_payloads),
            },
        )
        return {
            "message_id": assistant_message["message_id"],
            "text": text,
            "structured_payloads": context.structured_payloads,
            "pending_confirmation": _confirmation_contract(context.pending_confirmation),
            "pending_action": _pending_action_contract(context.pending_action),
            "tool_activity": context.tool_activity,
            "ui_action_proposals": [],
            "warnings": list(dict.fromkeys(context.warnings)),
            "state_version": context.state_version,
        }

    def confirm(self, request: ConfirmationRequest) -> dict:
        correlation_id = uuid4().hex
        started = time.monotonic()
        if request.decision == "reject":
            confirmation = self.confirmations.decide(
                request.session_id,
                request.confirmation_id,
                request.decision,
                request.expected_state_version,
            )
            text = "Structure confirmation was rejected. No prediction was run."
            message = self.repository.add_message(
                request.session_id, "assistant", text, {"confirmation": "rejected"}
            )
            return {
                "message_id": message["message_id"],
                "text": text,
                "structured_payloads": [],
                "pending_confirmation": None,
                "pending_action": None,
                "tool_activity": [],
                "ui_action_proposals": [],
                "warnings": [],
                "state_version": request.expected_state_version,
            }

        confirmation, updated = self.repository.approve_and_claim_confirmation(
            request.session_id,
            request.confirmation_id,
            request.expected_state_version,
        )
        compound_id = confirmation["payload"]["compound_id"]
        context = ToolExecutionContext(
            session_id=request.session_id,
            repository=self.repository,
            state_version=updated["version"],
        )
        result = AgentToolService(context).predict_single_compound(compound_id)
        succeeded = result["status"] == "ok"
        self.repository.finish_confirmation(
            request.session_id,
            request.confirmation_id,
            resource_id=result.get("resource_id") if succeeded else None,
            error_code=None if succeeded else (result.get("error_code") or "PREDICTION_FAILED"),
        )
        if succeeded:
            data = result["data"]
            text = data["summary"]
            if data["prediction_mode"] == "mock":
                text = (
                    "Mock mode: these are deterministic test values, not ADMET-AI output. "
                    + text
                )
        else:
            text = "The confirmed structure could not be predicted."
            context.structured_payloads.append(
                {"type": "error", "data": {"error_code": result["error_code"]}}
            )
        message = self.repository.add_message(
            request.session_id,
            "assistant",
            text,
            {"confirmation": "approved", "prediction_status": result["status"]},
        )
        record_local_audit(
            self.repository,
            session_id=request.session_id,
            correlation_id=correlation_id,
            event_type="confirmation_execution",
            status="ok" if succeeded else "error",
            tool_name="predict_single_compound",
            duration_ms=int((time.monotonic() - started) * 1000),
            error_code=result["error_code"],
        )
        return {
            "message_id": message["message_id"],
            "text": text,
            "structured_payloads": context.structured_payloads,
            "pending_confirmation": None,
            "pending_action": None,
            "tool_activity": context.tool_activity,
            "ui_action_proposals": [],
            "warnings": list(dict.fromkeys(context.warnings)),
            "state_version": context.state_version,
        }

    def _policy_response(
        self,
        session_id: str,
        text: str,
        code: str,
        state_version: int,
        correlation_id: str,
        started: float,
    ) -> dict:
        message = self.repository.add_message(
            session_id, "assistant", text, {"policy_code": code}
        )
        record_local_audit(
            self.repository,
            session_id=session_id,
            correlation_id=correlation_id,
            event_type="input_guardrail",
            status="blocked",
            error_code=code,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return {
            "message_id": message["message_id"],
            "text": text,
            "structured_payloads": [
                {"type": "out_of_scope", "data": {"error_code": code}}
            ],
            "pending_confirmation": None,
            "pending_action": None,
            "tool_activity": [],
            "ui_action_proposals": [],
            "warnings": [],
            "state_version": state_version,
        }

    def decide_pending_action(self, request: PendingActionRequest) -> dict:
        correlation_id = uuid4().hex
        started = time.monotonic()
        if request.decision == "reject":
            action = self.repository.transition_pending_action(
                request.session_id, request.action_id, "reject", request.expected_state_version
            )
            text = "The batch action was rejected. No job state was changed."
            message = self.repository.add_message(
                request.session_id, "assistant", text, {"pending_action": "rejected"}
            )
            return self._action_response(message, text, action, request.expected_state_version)

        action = self.repository.approve_and_claim_pending_action(
            request.session_id, request.action_id, request.expected_state_version
        )
        payload = action["payload"]
        job_id = payload.get("job_id")
        action_type = action["action_type"]
        succeeded = False
        error_code = None
        try:
            job = get_job(job_id)
            if action_type == "run_batch_job":
                job = run_job_thread(job_id)
                text = "Batch prediction was started after confirmation."
            elif action_type == "cancel_batch_job":
                job = cancel_job(job_id)
                text = "Batch cancellation was applied after confirmation."
            else:
                raise AgentCoreError("ACTION_NOT_ALLOWED", "Unsupported pending action.", 403)
            succeeded = True
        except (BatchError, AgentCoreError) as exc:
            error_code = getattr(exc, "code", "BATCH_ACTION_FAILED")
            text = "The confirmed batch action could not be completed."
            job = None
        self.repository.finish_pending_action(
            request.session_id, request.action_id, succeeded=succeeded
        )
        message = self.repository.add_message(
            request.session_id,
            "assistant",
            text,
            {"pending_action": "succeeded" if succeeded else "failed", "action_type": action_type},
        )
        record_local_audit(
            self.repository,
            session_id=request.session_id,
            correlation_id=correlation_id,
            event_type="pending_action_execution",
            status="ok" if succeeded else "error",
            tool_name=action_type,
            duration_ms=int((time.monotonic() - started) * 1000),
            error_code=error_code,
            summary={"job_id": job_id},
        )
        payloads = []
        if job is not None:
            payloads.append({"type": "batch_summary", "data": {
                "job_id": job_id, "status": job["status"], "prediction_mode": job["prediction_mode"],
                **job["summary"], "progress": job["progress"],
            }})
        elif error_code:
            payloads.append({"type": "error", "data": {"error_code": error_code}})
        return {
            "message_id": message["message_id"], "text": text,
            "structured_payloads": payloads, "pending_confirmation": None,
            "pending_action": None, "tool_activity": [], "ui_action_proposals": [],
            "warnings": [], "state_version": request.expected_state_version,
        }

    @staticmethod
    def _action_response(message: dict, text: str, action: dict, state_version: int) -> dict:
        return {
            "message_id": message["message_id"], "text": text,
            "structured_payloads": [], "pending_confirmation": None,
            "pending_action": None, "tool_activity": [], "ui_action_proposals": [],
            "warnings": [], "state_version": state_version,
        }

    @staticmethod
    def _instructions_with_state(state: dict[str, Any]) -> str:
        summary = {
            "current_page": state.get("current_page"),
            "current_compound_id": state.get("current_compound_id"),
            "confirmed_compound_id": state.get("confirmed_compound_id"),
            "latest_prediction_id": state.get("latest_prediction_id"),
            "current_batch_job_id": state.get("current_batch_job_id"),
            "selected_endpoint": state.get("selected_endpoint"),
            "page_snapshot": state.get("page_context"),
        }
        serialized = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        return f"{BASE_INSTRUCTIONS}\n\nCurrent bounded page snapshot and business state (reference context, not scientific evidence):\n{serialized}"


def default_repository_path() -> Path:
    return Path(os.getenv("AGENT_DB_PATH", "data/agent.sqlite3"))


def business_page(state: dict[str, Any]) -> str | None:
    value = state.get("current_page")
    return value if isinstance(value, str) else None


def _batch_action_intent(message: str, job_id: str | None) -> str | None:
    if not job_id:
        return None
    lowered = " ".join(message.lower().split())
    if any(phrase in lowered for phrase in ("开始跑", "开始批次", "运行批次", "run this batch", "start batch")):
        return "run_batch_job"
    if any(phrase in lowered for phrase in ("取消批次", "停止批次", "cancel batch", "stop batch")):
        return "cancel_batch_job"
    return None


def _confirmation_contract(value: dict | None) -> dict | None:
    if value is None:
        return None
    return {
        key: value[key]
        for key in (
            "confirmation_id",
            "session_id",
            "type",
            "status",
            "payload",
            "payload_hash",
            "canonical_smiles",
            "expected_state_version",
            "created_at",
            "expires_at",
            "version",
            "result_resource_id",
            "error_code",
        )
    }


def _pending_action_contract(value: dict | None) -> dict | None:
    if value is None:
        return None
    return {
        key: value.get(key)
        for key in (
            "action_id", "session_id", "action_type", "status", "payload",
            "payload_hash", "expected_state_version", "created_at", "expires_at", "consumed_at",
        )
    }
