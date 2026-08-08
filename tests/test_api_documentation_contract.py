from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from app.agent_runtime.contracts import (
    AgentChatRequest,
    AgentChatResponse,
    AgentStreamEvent,
    ConfirmationRequest,
    EvidenceAnswerData,
    EvidenceCitation,
    StableErrorResponse,
)
from app.api_contract import API_CONTRACT_VERSION, STREAM_EVENT_VERSION
from app.main import app
from app.knowledge_contracts import KnowledgeSearchRequest, KnowledgeSearchResponse


V1_ROOT = Path(__file__).resolve().parents[1] / "docs" / "api" / "v1"
EXAMPLES = V1_ROOT / "examples"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v1_manifest_matches_the_public_openapi_contract() -> None:
    manifest = _json(V1_ROOT / "contract.json")
    openapi = app.openapi()
    published_routes = {
        (method.upper(), path)
        for path, operations in openapi["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }
    documented_routes = {
        (route["method"], route["path"]) for route in manifest["routes"]
    }

    assert openapi["info"]["version"] == API_CONTRACT_VERSION
    assert manifest["api_contract_version"] == API_CONTRACT_VERSION
    assert manifest["stream_event_version"] == STREAM_EVENT_VERSION
    assert documented_routes == published_routes


def test_v1_examples_match_executable_models() -> None:
    AgentChatRequest.model_validate(_json(EXAMPLES / "agent-chat-request.json"))
    AgentChatResponse.model_validate(_json(EXAMPLES / "agent-chat-response.json"))
    ConfirmationRequest.model_validate(_json(EXAMPLES / "confirmation-request.json"))
    StableErrorResponse.model_validate(_json(EXAMPLES / "error-response.json"))
    EvidenceCitation.model_validate(_json(EXAMPLES / "source-card.json"))
    EvidenceAnswerData.model_validate(_json(EXAMPLES / "evidence-answer.json"))
    KnowledgeSearchRequest.model_validate(_json(EXAMPLES / "knowledge-search-request.json"))
    KnowledgeSearchResponse.model_validate(_json(EXAMPLES / "knowledge-search-response.json"))

    adapter = TypeAdapter(AgentStreamEvent)
    observed_types = set()
    for filename, terminal_type in (
        ("stream-events.ndjson", "response_completed"),
        ("stream-error-events.ndjson", "error"),
    ):
        events = [
            adapter.validate_json(line)
            for line in (EXAMPLES / filename).read_text(encoding="utf-8").splitlines()
            if line
        ]
        observed_types.update(event.type for event in events)
        assert [event.sequence for event in events] == list(range(len(events)))
        assert all(event.version == STREAM_EVENT_VERSION for event in events)
        assert events[-1].type == terminal_type

    assert observed_types == {
        "heartbeat",
        "tool_started",
        "tool_completed",
        "message_delta",
        "confirmation_required",
        "response_completed",
        "error",
    }
