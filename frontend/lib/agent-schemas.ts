import { z } from "zod";

const record = z.record(z.string(), z.unknown());
const identifier = z.string().min(1).max(128);
const pendingStatusSchema = z.enum([
  "proposed",
  "awaiting_confirmation",
  "approved",
  "executing",
  "succeeded",
  "failed",
  "rejected",
  "expired",
  "superseded",
]);

export const sessionSchema = z
  .object({
    session_id: z.string(),
    status: z.enum(["active", "expired"]),
    created_at: z.string(),
    expires_at: z.string(),
    state_version: z.number().int().nonnegative(),
  })
  .strict();

export const messagePageSchema = z
  .object({
    messages: z.array(
      z
        .object({
          message_id: z.string(),
          session_id: z.string(),
          role: z.enum(["user", "assistant", "tool", "confirmation"]),
          content: z.string(),
          created_at: z.string(),
          metadata: record,
        })
        .strict(),
    ),
    limit: z.number(),
    offset: z.number(),
    total: z.number(),
  })
  .strict();

export const confirmationSchema = z
  .object({
    confirmation_id: z.string(),
    session_id: z.string(),
    type: z.literal("compound_structure"),
    status: z.string(),
    payload: record,
    payload_hash: z.string(),
    canonical_smiles: z.string(),
    expected_state_version: z.number(),
    created_at: z.string(),
    expires_at: z.string(),
    version: z.number().default(0),
    result_resource_id: z.string().nullable().default(null),
    error_code: z.string().nullable().default(null),
  })
  .strict();

export const pendingActionSchema = z
  .object({
    action_id: z.string(),
    session_id: z.string(),
    action_type: z.enum(["run_batch_job", "cancel_batch_job"]),
    status: z.string(),
    payload: record,
    payload_hash: z.string(),
    expected_state_version: z.number(),
    created_at: z.string(),
    expires_at: z.string(),
    consumed_at: z.string().nullable().default(null),
  })
  .strict();

const actionBase = {
  action_id: z.string().min(1),
  session_id: z.string().min(1),
  expected_state_version: z.number().int().nonnegative(),
};
const emptyPayload = z.object({}).strict();

export const uiActionSchema = z.discriminatedUnion("type", [
  z
    .object({
      ...actionBase,
      type: z.literal("NAVIGATE"),
      target_route: z.enum(["/single", "/batch", "/about"]),
      payload: emptyPayload,
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_COMPOUND_INPUT"),
      target_route: z.literal("/single"),
      payload: z
        .object({
          value: z.string().min(1).max(500),
          submit: z.literal(false).default(false),
          focus: z.boolean().default(true),
        })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("FOCUS_COMPOUND_INPUT"),
      target_route: z.literal("/single"),
      payload: emptyPayload,
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("FOCUS_BATCH_UPLOAD"),
      target_route: z.literal("/batch"),
      payload: emptyPayload,
    })
    .strict(),
  ...(
    [
      "FOCUS_RESULT_SECTION",
      "SELECT_ENDPOINT",
      "OPEN_MODEL_ENDPOINT",
      "OPEN_BATCH_JOB",
      "SELECT_BATCH_ROW",
      "SHOW_RESOURCE",
    ] as const
  ).map((type) =>
    z
      .object({
        ...actionBase,
        type: z.literal(type),
        target_route: z.enum(["/single", "/batch", "/about"]).nullable(),
        payload: z
          .object({ target: z.string().regex(/^[A-Za-z0-9_.-]+$/) })
          .strict(),
      })
      .strict(),
  ),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_BATCH_FILTERS"),
      target_route: z.literal("/batch"),
      payload: z
        .object({
          validation_status: z
            .enum(["all", "valid", "duplicate", "invalid_smiles", "missing_smiles"])
            .nullable()
            .optional(),
          prediction_status: z
            .enum(["all", "completed", "failed", "pending"])
            .nullable()
            .optional(),
        })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_BATCH_SEARCH"),
      target_route: z.literal("/batch"),
      payload: z.object({ query: z.string().max(200) }).strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_BATCH_ENDPOINTS"),
      target_route: z.literal("/batch"),
      payload: z
        .object({ endpoints: z.array(z.string().min(1).max(120)).min(1).max(20) })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_BATCH_RANGE"),
      target_route: z.literal("/batch"),
      payload: z
        .object({
          endpoint: z.string().min(1).max(120),
          minimum: z.number().nullable().optional(),
          maximum: z.number().nullable().optional(),
        })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SELECT_BATCH_ROWS"),
      target_route: z.literal("/batch"),
      payload: z
        .object({
          row_numbers: z.array(z.number().int().positive()).min(1).max(5),
          purpose: z.enum(["preview", "comparison"]).default("preview"),
        })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("OPEN_BATCH_COMPARISON"),
      target_route: z.literal("/batch"),
      payload: emptyPayload,
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("EXPORT_BATCH_VIEW"),
      target_route: z.literal("/batch"),
      payload: z
        .object({ kind: z.enum(["results", "errors", "metadata", "filtered"]) })
        .strict(),
    })
    .strict(),
  z
    .object({
      ...actionBase,
      type: z.literal("SET_ABOUT_FILTERS"),
      target_route: z.literal("/about"),
      payload: z
        .object({
          category: z.string().regex(/^[A-Za-z0-9_.-]+$/).nullable().optional(),
          output_type: z.string().regex(/^[A-Za-z0-9_.-]+$/).nullable().optional(),
          metadata_status: z
            .enum(["all", "verified", "partial", "unverified"])
            .nullable()
            .optional(),
        })
        .strict(),
    })
    .strict(),
]);

export const structuredPayloadSchema = z
  .object({
    type: z.enum([
      "none",
      "compound_confirmation",
      "prediction",
      "endpoint_explanation",
      "batch_summary",
      "batch_errors",
      "comparison",
      "model_information",
      "resource",
      "out_of_scope",
      "error",
    ]),
    data: record,
  })
  .strict();

export const toolActivitySchema = z
  .object({
    tool_name: z.string(),
    status: z.enum(["completed", "error", "blocked"]),
    error_code: z.string().nullable(),
    resource_id: z.string().nullable(),
  })
  .strict();

export const agentResponseSchema = z
  .object({
    message_id: z.string(),
    text: z.string(),
    structured_payloads: z.array(structuredPayloadSchema),
    pending_confirmation: confirmationSchema.nullable(),
    pending_action: pendingActionSchema.nullable().default(null),
    tool_activity: z.array(toolActivitySchema),
    ui_action_proposals: z.array(uiActionSchema),
    warnings: z.array(z.string()),
    state_version: z.number().int().nonnegative(),
  })
  .strict();

export const agentErrorSchema = z
  .object({
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        details: z.string().nullable(),
        retryable: z.boolean(),
        correlation_id: z.string(),
      })
      .strict(),
  })
  .strict();

const inputQualitySchema = z
  .object({
    parse_status: z.enum(["valid", "invalid"]),
    fragment_count: z.number().int().nonnegative(),
    heavy_atom_count: z.number().int().nonnegative(),
    molecular_weight: z.number().nonnegative().nullable(),
    total_formal_charge: z.number().int().nullable(),
    metal_presence: z.boolean(),
    metal_elements: z.array(z.string().min(1).max(4)).max(32),
    unusual_elements: z.array(z.string().min(1).max(4)).max(32),
    mixture_warning: z.boolean(),
    size_warning: z.boolean(),
    warnings: z.array(z.string().max(500)).max(20),
    is_applicability_domain_score: z.literal(false),
  })
  .strict();

const streamCompoundPayloadSchema = z
  .object({
    input_query: z.string().max(2_000),
    preferred_name: z.string().min(1).max(240),
    pubchem_cid: z.number().int().positive().nullable(),
    molecular_formula: z.string().min(1).max(120),
    molecular_weight: z.number().nonnegative(),
    canonical_smiles: z.string().min(1).max(2_000),
    isomeric_smiles: z.string().min(1).max(2_000).nullable(),
    data_source: z.string().min(1).max(120),
    depiction_svg: z.string().min(1).max(250_000),
    warnings: z.array(z.string().max(500)).max(20),
    compound_id: z.string().min(1).max(128),
    input_quality: inputQualitySchema,
  })
  .strict();

const streamConfirmationSchema = z
  .object({
    confirmation_id: identifier,
    session_id: identifier,
    type: z.literal("compound_structure"),
    status: pendingStatusSchema,
    payload: streamCompoundPayloadSchema,
    payload_hash: z.string().min(1).max(128),
    canonical_smiles: z.string().min(1).max(2_000),
    expected_state_version: z.number().int().nonnegative(),
    created_at: z.string(),
    expires_at: z.string(),
    version: z.number().int().nonnegative(),
    result_resource_id: z.string().max(128).nullable(),
    error_code: z.string().max(80).nullable(),
  })
  .strict();

const streamPendingActionSchema = z
  .object({
    action_id: identifier,
    session_id: identifier,
    action_type: z.enum(["run_batch_job", "cancel_batch_job"]),
    status: pendingStatusSchema,
    payload: z
      .object({
        job_id: z.string().min(1).max(128),
        action_type: z.enum(["run_batch_job", "cancel_batch_job"]),
        status_at_proposal: z.string().min(1).max(40).regex(/^[A-Za-z0-9_-]+$/),
      })
      .strict(),
    payload_hash: z.string().min(1).max(128),
    expected_state_version: z.number().int().nonnegative(),
    created_at: z.string(),
    expires_at: z.string(),
    consumed_at: z.string().nullable(),
  })
  .strict();

const streamEnvelope = {
  version: z.literal(1),
  session_id: identifier,
  message_id: identifier,
  correlation_id: identifier,
  sequence: z.number().int().nonnegative(),
};

export const agentStreamEventSchema = z
  .discriminatedUnion("type", [
    z.object({ ...streamEnvelope, type: z.literal("heartbeat") }).strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("message_delta"),
        delta: z.string().min(1).max(256),
      })
      .strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("tool_started"),
        tool_name: z.string().min(1).max(120).regex(/^[A-Za-z0-9_.-]+$/),
      })
      .strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("tool_completed"),
        tool_activity: toolActivitySchema,
      })
      .strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("confirmation_required"),
        pending_confirmation: streamConfirmationSchema.nullable(),
        pending_action: streamPendingActionSchema.nullable(),
      })
      .strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("response_completed"),
        structured_payloads: z.array(structuredPayloadSchema),
        pending_confirmation: streamConfirmationSchema.nullable(),
        pending_action: streamPendingActionSchema.nullable(),
        tool_activity: z.array(toolActivitySchema),
        ui_action_proposals: z.array(uiActionSchema),
        warnings: z.array(z.string().max(500)).max(50),
        state_version: z.number().int().nonnegative(),
      })
      .strict(),
    z
      .object({
        ...streamEnvelope,
        type: z.literal("error"),
        code: z.string().min(1).max(80).regex(/^[A-Z0-9_]+$/),
        message: z.string().min(1).max(500),
        retryable: z.boolean(),
      })
      .strict(),
  ])
  .superRefine((event, context) => {
    if (event.type !== "confirmation_required") return;
    if ((event.pending_confirmation === null) === (event.pending_action === null)) {
      context.addIssue({
        code: "custom",
        message: "Exactly one pending confirmation or pending action is required.",
      });
    }
  });

const jsonValue: z.ZodType<unknown> = z.lazy(() =>
  z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.null(),
    z.array(jsonValue),
    z.record(z.string(), jsonValue),
  ]),
);

export const predictionResourceSchema = z
  .object({
    input_smiles: z.string(),
    canonical_smiles: z.string().nullable(),
    predictions: z.record(z.string(), z.record(z.string(), jsonValue)),
    enriched_predictions: z.record(z.string(), z.array(record)).default({}),
    summary: z.string(),
    disclaimer: z.string(),
    prediction_mode: z.enum(["mock", "real"]),
  })
  .passthrough();

export const resourceResponseSchema = z
  .object({
    resource_id: z.string(),
    session_id: z.string(),
    resource_type: z.string(),
    content_hash: z.string(),
    size_bytes: z.number(),
    created_at: z.string(),
    expires_at: z.string(),
    data: z.unknown(),
  })
  .strict();
