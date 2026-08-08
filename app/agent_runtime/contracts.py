from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SinglePageContext(StrictModel):
    page: Literal["single"]
    compound_id: str | None = None
    prediction_id: str | None = None
    selected_endpoint: str | None = None
    active_view: Literal["input", "structure_review", "prediction_results"] = "input"
    compound_query: str = Field(default="", max_length=2_000)
    compound_name: str | None = Field(default=None, max_length=240)
    canonical_smiles: str | None = Field(default=None, max_length=2_000)
    result_available: bool = False
    result_categories: list[str] = Field(default_factory=list, max_length=12)
    prediction_mode: Literal["mock", "real"] | None = None


class BatchPageContext(StrictModel):
    page: Literal["batch"]
    batch_job_id: str | None = None
    selected_compound_ids: list[str] = Field(default_factory=list, max_length=5)
    selected_row_numbers: list[int] = Field(default_factory=list, max_length=5)
    selected_endpoints: list[str] = Field(default_factory=list, max_length=20)
    validation_filter: str | None = None
    prediction_filter: str | None = None
    search_query: str = Field(default="", max_length=200)
    range_endpoint: str | None = Field(default=None, max_length=120)
    range_min: float | None = None
    range_max: float | None = None
    active_view: Literal["upload", "validation", "results", "compound_detail", "comparison"] = "results"
    comparison_open: bool = False
    detail_open: bool = False
    current_page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    total_row_count: int | None = Field(default=None, ge=0)
    filtered_row_count: int | None = Field(default=None, ge=0)
    visible_row_numbers: list[int] = Field(default_factory=list, max_length=100)


class AboutPageContext(StrictModel):
    page: Literal["about"]
    selected_endpoint: str | None = None
    active_category: str | None = None
    search_query: str = Field(default="", max_length=200)
    output_type_filter: str | None = Field(default=None, max_length=120)
    metadata_status_filter: str | None = Field(default=None, max_length=120)
    verified_unit_only: bool = False
    current_page: int = Field(default=1, ge=1)
    filtered_endpoint_count: int | None = Field(default=None, ge=0)
    visible_endpoints: list[str] = Field(default_factory=list, max_length=50)


PageContext = Annotated[
    SinglePageContext | BatchPageContext | AboutPageContext,
    Field(discriminator="page"),
]


class AgentSession(StrictModel):
    session_id: str
    status: Literal["active", "expired"]
    created_at: datetime
    expires_at: datetime
    state_version: int


class AgentMessage(StrictModel):
    message_id: str
    session_id: str
    role: Literal["user", "assistant", "tool", "confirmation"]
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessagePage(StrictModel):
    messages: list[AgentMessage]
    limit: int
    offset: int
    total: int


class MockScenarioSelection(StrictModel):
    catalog_version: int
    id: str = Field(min_length=1, max_length=80)


class AgentChatRequest(StrictModel):
    session_id: str
    message: str = Field(min_length=1, max_length=8_000)
    expected_state_version: int = Field(ge=0)
    page_context: PageContext | None = None
    mock_scenario: MockScenarioSelection | None = None


class ToolActivity(StrictModel):
    tool_name: str
    status: Literal["completed", "error", "blocked"]
    error_code: str | None = None
    resource_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)


class UIActionBase(StrictModel):
    action_id: str
    session_id: str
    target_route: Literal["/single", "/batch", "/about"] | None = None
    expected_state_version: int = Field(ge=0)


class EmptyActionPayload(StrictModel):
    pass


class SetCompoundInputPayload(StrictModel):
    value: str = Field(min_length=1, max_length=500)
    submit: bool = False
    focus: bool = True

    @field_validator("value")
    @classmethod
    def reject_executable_content(cls, value: str) -> str:
        normalized = value.strip()
        if any(token in normalized.lower() for token in ("<script", "javascript:", "document.", "window.", "selector")):
            raise ValueError("Executable or selector content is not allowed.")
        return normalized


class TargetPayload(StrictModel):
    target: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")


class BatchFiltersPayload(StrictModel):
    validation_status: Literal["all", "valid", "duplicate", "invalid_smiles", "missing_smiles"] | None = None
    prediction_status: Literal["all", "completed", "failed", "pending"] | None = None


class BatchSearchPayload(StrictModel):
    query: str = Field(default="", max_length=200)


class BatchEndpointsPayload(StrictModel):
    endpoints: list[str] = Field(min_length=1, max_length=20)


class BatchRangePayload(StrictModel):
    endpoint: str = Field(min_length=1, max_length=120)
    minimum: float | None = None
    maximum: float | None = None


class BatchRowsPayload(StrictModel):
    row_numbers: list[int] = Field(min_length=1, max_length=5)
    purpose: Literal["preview", "comparison"] = "preview"


class BatchExportPayload(StrictModel):
    kind: Literal["results", "errors", "metadata", "filtered"]


class AboutFiltersPayload(StrictModel):
    category: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    output_type: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    metadata_status: Literal["all", "verified", "partial", "unverified"] | None = None


class NavigateAction(UIActionBase):
    type: Literal["NAVIGATE"]
    target_route: Literal["/single", "/batch", "/about"]
    payload: EmptyActionPayload = Field(default_factory=EmptyActionPayload)


class SetCompoundInputAction(UIActionBase):
    type: Literal["SET_COMPOUND_INPUT"]
    target_route: Literal["/single"] = "/single"
    payload: SetCompoundInputPayload


class FocusCompoundInputAction(UIActionBase):
    type: Literal["FOCUS_COMPOUND_INPUT"]
    target_route: Literal["/single"] = "/single"
    payload: EmptyActionPayload = Field(default_factory=EmptyActionPayload)


class FocusBatchUploadAction(UIActionBase):
    type: Literal["FOCUS_BATCH_UPLOAD"]
    target_route: Literal["/batch"] = "/batch"
    payload: EmptyActionPayload = Field(default_factory=EmptyActionPayload)


class TargetAction(UIActionBase):
    type: Literal["FOCUS_RESULT_SECTION", "SELECT_ENDPOINT", "OPEN_MODEL_ENDPOINT", "OPEN_BATCH_JOB", "SELECT_BATCH_ROW", "SHOW_RESOURCE"]
    payload: TargetPayload


class SetBatchFiltersAction(UIActionBase):
    type: Literal["SET_BATCH_FILTERS"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchFiltersPayload


class SetBatchSearchAction(UIActionBase):
    type: Literal["SET_BATCH_SEARCH"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchSearchPayload


class SetBatchEndpointsAction(UIActionBase):
    type: Literal["SET_BATCH_ENDPOINTS"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchEndpointsPayload


class SetBatchRangeAction(UIActionBase):
    type: Literal["SET_BATCH_RANGE"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchRangePayload


class SelectBatchRowsAction(UIActionBase):
    type: Literal["SELECT_BATCH_ROWS"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchRowsPayload


class OpenBatchComparisonAction(UIActionBase):
    type: Literal["OPEN_BATCH_COMPARISON"]
    target_route: Literal["/batch"] = "/batch"
    payload: EmptyActionPayload = Field(default_factory=EmptyActionPayload)


class ExportBatchViewAction(UIActionBase):
    type: Literal["EXPORT_BATCH_VIEW"]
    target_route: Literal["/batch"] = "/batch"
    payload: BatchExportPayload


class SetAboutFiltersAction(UIActionBase):
    type: Literal["SET_ABOUT_FILTERS"]
    target_route: Literal["/about"] = "/about"
    payload: AboutFiltersPayload


UIActionProposal = Annotated[
    NavigateAction | SetCompoundInputAction | FocusCompoundInputAction | FocusBatchUploadAction |
    TargetAction | SetBatchFiltersAction | SetBatchSearchAction |
    SetBatchEndpointsAction | SetBatchRangeAction | SelectBatchRowsAction |
    OpenBatchComparisonAction | ExportBatchViewAction | SetAboutFiltersAction,
    Field(discriminator="type"),
]


class CompoundConfirmation(StrictModel):
    confirmation_id: str
    session_id: str
    type: Literal["compound_structure"]
    status: Literal[
        "proposed",
        "awaiting_confirmation",
        "approved",
        "executing",
        "succeeded",
        "failed",
        "rejected",
        "expired",
        "superseded",
    ]
    payload: dict[str, Any]
    payload_hash: str
    canonical_smiles: str
    expected_state_version: int
    created_at: datetime
    expires_at: datetime
    version: int = 0
    result_resource_id: str | None = None
    error_code: str | None = None


class ConfirmationRequest(StrictModel):
    session_id: str
    confirmation_id: str
    decision: Literal["approve", "reject"]
    expected_state_version: int = Field(ge=0)


class PendingAction(StrictModel):
    action_id: str
    session_id: str
    action_type: str
    status: Literal[
        "proposed",
        "awaiting_confirmation",
        "approved",
        "executing",
        "succeeded",
        "failed",
        "rejected",
        "expired",
        "superseded",
    ]
    payload_hash: str
    payload: dict[str, Any]
    expected_state_version: int
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None


class PendingActionRequest(StrictModel):
    session_id: str
    action_id: str
    decision: Literal["approve", "reject"]
    expected_state_version: int = Field(ge=0)


class ToolResultEnvelope(StrictModel):
    tool_name: str
    status: Literal["ok", "error", "confirmation_required"]
    data: dict[str, Any] | None = None
    resource_id: str | None = None
    error_code: str | None = None
    message: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class EvidenceCitation(StrictModel):
    source_id: str
    title: str
    organization: str
    url: str
    document_date: str
    version: str
    status: Literal["current", "superseded", "draft"]
    captured_at: str
    section: str
    page: int | str | None = None
    chunk_id: str
    excerpt: str


class EvidenceClaim(StrictModel):
    text: str
    evidence: list[EvidenceCitation] = Field(min_length=1, max_length=5)


class EvidenceAnswerData(StrictModel):
    query: str
    status: Literal[
        "supported",
        "partial",
        "conflicting",
        "no_evidence",
        "prohibited",
        "stale_only",
    ]
    availability: Literal["available", "unavailable"]
    assistant_summary: str
    claims: list[EvidenceClaim] = Field(max_length=5)
    evidence: list[EvidenceCitation] = Field(max_length=5)
    source_count: int = Field(ge=0, le=5)
    warnings: list[str] = Field(default_factory=list, max_length=5)


class StructuredPayload(StrictModel):
    type: Literal[
        "none",
        "compound_confirmation",
        "prediction",
        "endpoint_explanation",
        "evidence_answer",
        "batch_summary",
        "comparison",
        "batch_errors",
        "model_information",
        "resource",
        "out_of_scope",
        "error",
    ]
    data: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(StrictModel):
    message_id: str
    text: str
    structured_payloads: list[StructuredPayload] = Field(default_factory=list)
    pending_confirmation: CompoundConfirmation | None = None
    pending_action: PendingAction | None = None
    tool_activity: list[ToolActivity] = Field(default_factory=list)
    ui_action_proposals: list[UIActionProposal] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    state_version: int


class AgentStreamEnvelope(StrictModel):
    version: Literal[1] = 1
    session_id: str = Field(min_length=1, max_length=128)
    message_id: str = Field(min_length=1, max_length=128)
    correlation_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=0)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentStreamHeartbeat(AgentStreamEnvelope):
    type: Literal["heartbeat"] = "heartbeat"


class AgentStreamMessageDelta(AgentStreamEnvelope):
    type: Literal["message_delta"] = "message_delta"
    delta: str = Field(min_length=1, max_length=256)


class AgentStreamToolStarted(AgentStreamEnvelope):
    type: Literal["tool_started"] = "tool_started"
    tool_name: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )


class AgentStreamToolCompleted(AgentStreamEnvelope):
    type: Literal["tool_completed"] = "tool_completed"
    tool_activity: ToolActivity


class AgentStreamConfirmationRequired(AgentStreamEnvelope):
    type: Literal["confirmation_required"] = "confirmation_required"
    pending_confirmation: CompoundConfirmation | None
    pending_action: PendingAction | None

    @model_validator(mode="after")
    def require_exactly_one_pending_record(self) -> AgentStreamConfirmationRequired:
        if (self.pending_confirmation is None) == (self.pending_action is None):
            raise ValueError(
                "Exactly one pending confirmation or pending action is required."
            )
        return self


class AgentStreamResponseCompleted(AgentStreamEnvelope):
    type: Literal["response_completed"] = "response_completed"
    structured_payloads: list[StructuredPayload]
    pending_confirmation: CompoundConfirmation | None
    pending_action: PendingAction | None
    tool_activity: list[ToolActivity]
    ui_action_proposals: list[UIActionProposal]
    warnings: list[str]
    state_version: int = Field(ge=0)


class AgentStreamError(AgentStreamEnvelope):
    type: Literal["error"] = "error"
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9_]+$")
    message: str = Field(min_length=1, max_length=500)
    retryable: bool = False


AgentStreamEvent = Annotated[
    AgentStreamHeartbeat
    | AgentStreamMessageDelta
    | AgentStreamToolStarted
    | AgentStreamToolCompleted
    | AgentStreamConfirmationRequired
    | AgentStreamResponseCompleted
    | AgentStreamError,
    Field(discriminator="type"),
]


class ResourceMetadata(StrictModel):
    resource_id: str
    session_id: str
    resource_type: str
    content_hash: str
    size_bytes: int
    created_at: datetime
    expires_at: datetime


class ResourceResponse(ResourceMetadata):
    data: dict[str, Any] | list[Any]


class StableErrorBody(StrictModel):
    code: str
    message: str
    details: str | None = None
    retryable: bool = False
    correlation_id: str


class StableErrorResponse(StrictModel):
    error: StableErrorBody
