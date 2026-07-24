import { z } from "zod";

const record = z.record(z.string(), z.unknown());
export const sessionSchema = z.object({ session_id: z.string(), status: z.enum(["active", "expired"]), created_at: z.string(), expires_at: z.string(), state_version: z.number().int().nonnegative() }).strict();
export const messagePageSchema = z.object({ messages: z.array(z.object({ message_id: z.string(), session_id: z.string(), role: z.enum(["user", "assistant", "tool", "confirmation"]), content: z.string(), created_at: z.string(), metadata: record }).strict()), limit: z.number(), offset: z.number(), total: z.number() }).strict();
const confirmationSchema = z.object({ confirmation_id: z.string(), session_id: z.string(), type: z.literal("compound_structure"), status: z.string(), payload: record, payload_hash: z.string(), canonical_smiles: z.string(), expected_state_version: z.number(), created_at: z.string(), expires_at: z.string(), version: z.number().default(0), result_resource_id: z.string().nullable().default(null), error_code: z.string().nullable().default(null) }).strict();
export const pendingActionSchema = z.object({ action_id: z.string(), session_id: z.string(), action_type: z.enum(["run_batch_job", "cancel_batch_job"]), status: z.string(), payload: record, payload_hash: z.string(), expected_state_version: z.number(), created_at: z.string(), expires_at: z.string(), consumed_at: z.string().nullable().default(null) }).strict();
const actionBase = { action_id: z.string().min(1), session_id: z.string().min(1), expected_state_version: z.number().int().nonnegative() };
const emptyPayload = z.object({}).strict();
export const uiActionSchema = z.discriminatedUnion("type", [
  z.object({ ...actionBase, type: z.literal("NAVIGATE"), target_route: z.enum(["/single", "/batch", "/about"]), payload: emptyPayload }).strict(),
  z.object({ ...actionBase, type: z.literal("SET_COMPOUND_INPUT"), target_route: z.literal("/single"), payload: z.object({ value: z.string().min(1).max(500), submit: z.literal(false).default(false), focus: z.boolean().default(true) }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("FOCUS_COMPOUND_INPUT"), target_route: z.literal("/single"), payload: emptyPayload }).strict(),
  z.object({ ...actionBase, type: z.literal("FOCUS_BATCH_UPLOAD"), target_route: z.literal("/batch"), payload: emptyPayload }).strict(),
  ...(["FOCUS_RESULT_SECTION", "SELECT_ENDPOINT", "OPEN_MODEL_ENDPOINT", "OPEN_BATCH_JOB", "SELECT_BATCH_ROW", "SHOW_RESOURCE"] as const).map((type) => z.object({ ...actionBase, type: z.literal(type), target_route: z.enum(["/single", "/batch", "/about"]).nullable(), payload: z.object({ target: z.string().regex(/^[A-Za-z0-9_.-]+$/) }).strict() }).strict()),
  z.object({ ...actionBase, type: z.literal("SET_BATCH_FILTERS"), target_route: z.literal("/batch"), payload: z.object({ validation_status: z.enum(["all", "valid", "duplicate", "invalid_smiles", "missing_smiles"]).nullable().optional(), prediction_status: z.enum(["all", "completed", "failed", "pending"]).nullable().optional() }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("SET_BATCH_SEARCH"), target_route: z.literal("/batch"), payload: z.object({ query: z.string().max(200) }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("SET_BATCH_ENDPOINTS"), target_route: z.literal("/batch"), payload: z.object({ endpoints: z.array(z.string().min(1).max(120)).min(1).max(20) }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("SET_BATCH_RANGE"), target_route: z.literal("/batch"), payload: z.object({ endpoint: z.string().min(1).max(120), minimum: z.number().nullable().optional(), maximum: z.number().nullable().optional() }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("SELECT_BATCH_ROWS"), target_route: z.literal("/batch"), payload: z.object({ row_numbers: z.array(z.number().int().positive()).min(1).max(5), purpose: z.enum(["preview", "comparison"]).default("preview") }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("OPEN_BATCH_COMPARISON"), target_route: z.literal("/batch"), payload: emptyPayload }).strict(),
  z.object({ ...actionBase, type: z.literal("EXPORT_BATCH_VIEW"), target_route: z.literal("/batch"), payload: z.object({ kind: z.enum(["results", "errors", "metadata", "filtered"]) }).strict() }).strict(),
  z.object({ ...actionBase, type: z.literal("SET_ABOUT_FILTERS"), target_route: z.literal("/about"), payload: z.object({ category: z.string().regex(/^[A-Za-z0-9_.-]+$/).nullable().optional(), output_type: z.string().regex(/^[A-Za-z0-9_.-]+$/).nullable().optional(), metadata_status: z.enum(["all", "verified", "partial", "unverified"]).nullable().optional() }).strict() }).strict(),
]);
export const agentResponseSchema = z.object({ message_id: z.string(), text: z.string(), structured_payloads: z.array(z.object({ type: z.enum(["none", "compound_confirmation", "prediction", "endpoint_explanation", "batch_summary", "batch_errors", "comparison", "model_information", "resource", "out_of_scope", "error"]), data: record }).strict()), pending_confirmation: confirmationSchema.nullable(), pending_action: pendingActionSchema.nullable().default(null), tool_activity: z.array(z.object({ tool_name: z.string(), status: z.enum(["completed", "error", "blocked"]), error_code: z.string().nullable(), resource_id: z.string().nullable() }).strict()), ui_action_proposals: z.array(uiActionSchema), warnings: z.array(z.string()), state_version: z.number().int().nonnegative() }).strict();
export const agentErrorSchema = z.object({ error: z.object({ code: z.string(), message: z.string(), details: z.string().nullable(), retryable: z.boolean(), correlation_id: z.string() }).strict() }).strict();
const jsonValue: z.ZodType<unknown> = z.lazy(() => z.union([z.string(), z.number(), z.boolean(), z.null(), z.array(jsonValue), z.record(z.string(), jsonValue)]));
export const predictionResourceSchema = z.object({
  input_smiles: z.string(), canonical_smiles: z.string().nullable(),
  predictions: z.record(z.string(), z.record(z.string(), jsonValue)),
  enriched_predictions: z.record(z.string(), z.array(record)).default({}),
  summary: z.string(), disclaimer: z.string(), prediction_mode: z.enum(["mock", "real"]),
}).passthrough();
export const resourceResponseSchema = z.object({ resource_id: z.string(), session_id: z.string(), resource_type: z.string(), content_hash: z.string(), size_bytes: z.number(), created_at: z.string(), expires_at: z.string(), data: z.unknown() }).strict();
export { confirmationSchema };
