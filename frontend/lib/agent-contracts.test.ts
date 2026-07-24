import { describe, expect, it } from "vitest";
import { agentErrorSchema, agentResponseSchema } from "./agent-schemas";
import { executeUIAction, resetExecutedActionsForTests } from "./ui-action-dispatcher";
import { registerAssistantCapabilities } from "./assistant-capabilities";

const response = {
  message_id: "msg_1", text: "Computational result.", structured_payloads: [], pending_confirmation: null,
  pending_action: null, tool_activity: [], ui_action_proposals: [], warnings: [], state_version: 2,
};

describe("Agent runtime contracts", () => {
  it("accepts the frozen response and rejects extra fields", () => {
    expect(agentResponseSchema.safeParse(response).success).toBe(true);
    expect(agentResponseSchema.safeParse({ ...response, raw_provider_body: "secret" }).success).toBe(false);
  });
  it("requires the stable error envelope", () => {
    expect(agentErrorSchema.safeParse({ error: { code: "AGENT_TIMEOUT", message: "Timed out", details: null, retryable: true, correlation_id: "corr" } }).success).toBe(true);
    expect(agentErrorSchema.safeParse({ error: { code: "X", message: "bad" } }).success).toBe(false);
  });
});

describe("UI action allowlist", () => {
  const base = { action_id: "action_1", session_id: "session_1", target_route: "/single" as const, expected_state_version: 3 };
  it("executes a real registered capability", async () => {
    resetExecutedActionsForTests(); let received = "";
    const unregister = registerAssistantCapabilities("/single", { execute(action) { received = String(action.payload.value); return { targetId: "compound-input", message: "Input updated" }; } });
    const result = await executeUIAction({ ...base, type: "SET_COMPOUND_INPUT", payload: { value: "ibuprofen", submit: false, focus: true } }, { sessionId: "session_1", stateVersion: 3, currentRoute: "/single", navigate: () => undefined });
    expect(result.ok).toBe(true); expect(received).toBe("ibuprofen"); unregister();
  });
  it("rejects duplicate, stale, unknown, and cross-session actions", async () => {
    resetExecutedActionsForTests(); const unregister = registerAssistantCapabilities("/single", { execute() { return { message: "done" }; } });
    const action = { ...base, type: "FOCUS_COMPOUND_INPUT", payload: {} };
    expect((await executeUIAction(action, { sessionId: "session_1", stateVersion: 3, currentRoute: "/single", navigate: () => undefined })).ok).toBe(true);
    expect(await executeUIAction(action, { sessionId: "session_1", stateVersion: 3, currentRoute: "/single", navigate: () => undefined })).toMatchObject({ ok: false, code: "ACTION_DUPLICATE" });
    expect(await executeUIAction({ ...action, action_id: "stale" }, { sessionId: "session_1", stateVersion: 4, currentRoute: "/single", navigate: () => undefined })).toMatchObject({ ok: false, code: "ACTION_STALE" });
    expect(await executeUIAction({ ...action, action_id: "other", session_id: "other" }, { sessionId: "session_1", stateVersion: 3, currentRoute: "/single", navigate: () => undefined })).toMatchObject({ ok: false, code: "ACTION_NOT_ALLOWED" });
    expect(await executeUIAction({ ...action, action_id: "bad", type: "EVAL_JAVASCRIPT" }, { sessionId: "session_1", stateVersion: 3, currentRoute: "/single", navigate: () => undefined })).toMatchObject({ ok: false, code: "ACTION_INVALID" }); unregister();
  });
  it("accepts bounded Batch actions and rejects oversized row selections", async () => {
    resetExecutedActionsForTests(); let received: unknown = null;
    const unregister = registerAssistantCapabilities("/batch/job_1", { execute(action) { received = action.payload; return { targetId: "batch-results", message: "Rows selected" }; } });
    const batchBase = { action_id: "batch_1", session_id: "session_1", target_route: "/batch" as const, expected_state_version: 3 };
    const valid = { ...batchBase, type: "SELECT_BATCH_ROWS", payload: { row_numbers: [2, 5], purpose: "comparison" } };
    expect((await executeUIAction(valid, { sessionId: "session_1", stateVersion: 3, currentRoute: "/batch/job_1", navigate: () => undefined })).ok).toBe(true);
    expect(received).toEqual({ row_numbers: [2, 5], purpose: "comparison" });
    const invalid = { ...batchBase, action_id: "batch_2", type: "SELECT_BATCH_ROWS", payload: { row_numbers: [1, 2, 3, 4, 5, 6], purpose: "comparison" } };
    expect(await executeUIAction(invalid, { sessionId: "session_1", stateVersion: 3, currentRoute: "/batch/job_1", navigate: () => undefined })).toMatchObject({ ok: false, code: "ACTION_INVALID" });
    unregister();
  });
});
