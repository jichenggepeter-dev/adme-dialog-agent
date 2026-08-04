export type PageContext =
  | {
      page: "single";
      compound_id?: string | null;
      prediction_id?: string | null;
      selected_endpoint?: string | null;
      active_view?: "input" | "structure_review" | "prediction_results";
      compound_query?: string;
      compound_name?: string | null;
      canonical_smiles?: string | null;
      result_available?: boolean;
      result_categories?: string[];
      prediction_mode?: "mock" | "real" | null;
    }
  | {
      page: "batch";
      batch_job_id?: string | null;
      selected_compound_ids: string[];
      selected_row_numbers: number[];
      selected_endpoints: string[];
      validation_filter?: string | null;
      prediction_filter?: string | null;
      search_query?: string;
      range_endpoint?: string | null;
      range_min?: number | null;
      range_max?: number | null;
      active_view?: "upload" | "validation" | "results" | "compound_detail" | "comparison";
      comparison_open?: boolean;
      detail_open?: boolean;
      current_page?: number;
      page_size?: number;
      total_row_count?: number | null;
      filtered_row_count?: number | null;
      visible_row_numbers?: number[];
    }
  | {
      page: "about";
      selected_endpoint?: string | null;
      active_category?: string | null;
      search_query?: string;
      output_type_filter?: string | null;
      metadata_status_filter?: string | null;
      verified_unit_only?: boolean;
      current_page?: number;
      filtered_endpoint_count?: number | null;
      visible_endpoints?: string[];
    };

export type AgentMessage = {
  message_id: string;
  session_id: string;
  role: "user" | "assistant" | "tool" | "confirmation";
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ToolActivity = {
  tool_name: string;
  status: "completed" | "error" | "blocked";
  error_code: string | null;
  resource_id: string | null;
};

export type EvidenceCitation = {
  source_id: string;
  title: string;
  organization: string;
  url: string;
  document_date: string;
  version: string;
  status: "current" | "superseded" | "draft";
  captured_at: string;
  section: string;
  page: number | string | null;
  chunk_id: string;
  excerpt: string;
};

export type EvidenceAnswerData = Record<string, unknown> & {
  query: string;
  status: "supported" | "partial" | "conflicting" | "no_evidence" | "prohibited" | "stale_only";
  availability: "available" | "unavailable";
  assistant_summary: string;
  claims: { text: string; evidence: EvidenceCitation[] }[];
  evidence: EvidenceCitation[];
  source_count: number;
  warnings: string[];
};

export type StructuredPayload =
  | { type: "evidence_answer"; data: EvidenceAnswerData }
  | {
      type:
    | "none"
    | "compound_confirmation"
    | "prediction"
    | "endpoint_explanation"
    | "batch_summary"
    | "batch_errors"
    | "comparison"
    | "model_information"
    | "resource"
    | "out_of_scope"
    | "error";
      data: Record<string, unknown>;
    };

export type Confirmation = {
  confirmation_id: string;
  session_id: string;
  type: "compound_structure";
  status: string;
  payload: Record<string, unknown>;
  payload_hash: string;
  canonical_smiles: string;
  expected_state_version: number;
  created_at: string;
  expires_at: string;
  version: number;
  result_resource_id: string | null;
  error_code: string | null;
};

export type PendingAction = {
  action_id: string;
  session_id: string;
  action_type: "run_batch_job" | "cancel_batch_job";
  status: string;
  payload: Record<string, unknown>;
  payload_hash: string;
  expected_state_version: number;
  created_at: string;
  expires_at: string;
  consumed_at: string | null;
};

export type UIAction = {
  action_id: string;
  session_id: string;
  type:
    | "NAVIGATE"
    | "SET_COMPOUND_INPUT"
    | "FOCUS_COMPOUND_INPUT"
    | "FOCUS_BATCH_UPLOAD"
    | "FOCUS_RESULT_SECTION"
    | "SELECT_ENDPOINT"
    | "OPEN_MODEL_ENDPOINT"
    | "OPEN_BATCH_JOB"
    | "SELECT_BATCH_ROW"
    | "SET_BATCH_FILTERS"
    | "SET_BATCH_SEARCH"
    | "SET_BATCH_ENDPOINTS"
    | "SET_BATCH_RANGE"
    | "SELECT_BATCH_ROWS"
    | "OPEN_BATCH_COMPARISON"
    | "EXPORT_BATCH_VIEW"
    | "SET_ABOUT_FILTERS"
    | "SHOW_RESOURCE";
  target_route: "/single" | "/batch" | "/about" | null;
  expected_state_version: number;
  payload: Record<string, unknown>;
};

export type AgentResponse = {
  message_id: string;
  text: string;
  structured_payloads: StructuredPayload[];
  pending_confirmation: Confirmation | null;
  pending_action: PendingAction | null;
  tool_activity: ToolActivity[];
  ui_action_proposals: UIAction[];
  warnings: string[];
  state_version: number;
};

export type AgentSession = {
  session_id: string;
  status: "active" | "expired";
  created_at: string;
  expires_at: string;
  state_version: number;
};

export type AgentError = {
  code: string;
  message: string;
  details: string | null;
  retryable: boolean;
  correlation_id: string;
};

export type AgentStreamEnvelope = {
  version: 1;
  session_id: string;
  message_id: string;
  correlation_id: string;
  sequence: number;
};

export type AgentStreamHeartbeat = AgentStreamEnvelope & {
  type: "heartbeat";
};

export type AgentStreamMessageDelta = AgentStreamEnvelope & {
  type: "message_delta";
  delta: string;
};

export type AgentStreamToolStarted = AgentStreamEnvelope & {
  type: "tool_started";
  tool_name: string;
};

export type AgentStreamToolCompleted = AgentStreamEnvelope & {
  type: "tool_completed";
  tool_activity: ToolActivity;
};

export type AgentStreamConfirmationRequired = AgentStreamEnvelope & {
  type: "confirmation_required";
  pending_confirmation: Confirmation | null;
  pending_action: PendingAction | null;
};

export type AgentStreamResponseCompleted = AgentStreamEnvelope & {
  type: "response_completed";
  structured_payloads: StructuredPayload[];
  pending_confirmation: Confirmation | null;
  pending_action: PendingAction | null;
  tool_activity: ToolActivity[];
  ui_action_proposals: UIAction[];
  warnings: string[];
  state_version: number;
};

export type AgentStreamError = AgentStreamEnvelope & {
  type: "error";
  code: string;
  message: string;
  retryable: boolean;
};

export type AgentStreamEvent =
  | AgentStreamHeartbeat
  | AgentStreamMessageDelta
  | AgentStreamToolStarted
  | AgentStreamToolCompleted
  | AgentStreamConfirmationRequired
  | AgentStreamResponseCompleted
  | AgentStreamError;

export type AssistantStreamStatus =
  | "idle"
  | "connecting"
  | "generating"
  | "tool"
  | "waiting_confirmation"
  | "completed"
  | "failed";
