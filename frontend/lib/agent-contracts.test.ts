import { describe, expect, it } from "vitest";
import { agentErrorSchema, agentResponseSchema, agentStreamEventSchema } from "./agent-schemas";
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
  it("strictly validates evidence payloads", () => {
    const evidence = {
      ...response,
      structured_payloads: [{ type: "evidence_answer", data: {
        query: "mass balance", status: "no_evidence", availability: "available",
        assistant_summary: "No adequate passage was found.", claims: [], evidence: [],
        source_count: 0, warnings: [],
      } }],
    };
    expect(agentResponseSchema.safeParse(evidence).success).toBe(true);
    expect(agentResponseSchema.safeParse({ ...evidence, structured_payloads: [{ ...evidence.structured_payloads[0], data: { ...evidence.structured_payloads[0].data, invented_confidence: 0.9 } }] }).success).toBe(false);
  });
  it("requires the stable error envelope", () => {
    expect(agentErrorSchema.safeParse({ error: { code: "AGENT_TIMEOUT", message: "Timed out", details: null, retryable: true, correlation_id: "corr" } }).success).toBe(true);
    expect(agentErrorSchema.safeParse({ error: { code: "X", message: "bad" } }).success).toBe(false);
  });
  it("accepts the hash-bound Mock Agent marker in confirmation streams", () => {
    const payload = {
      input_query: "CCO", preferred_name: "Resolved SMILES compound", pubchem_cid: null,
      molecular_formula: "C2H6O", molecular_weight: 46.069, canonical_smiles: "CCO",
      isomeric_smiles: "CCO", data_source: "Local RDKit", depiction_svg: "<svg></svg>",
      warnings: [], compound_id: "compound_1", agent_provider_mode: "mock", mock_catalog_version: 1,
      input_quality: { parse_status: "valid", fragment_count: 1, heavy_atom_count: 3, molecular_weight: 46.069, total_formal_charge: 0, metal_presence: false, metal_elements: [], unusual_elements: [], mixture_warning: false, size_warning: false, warnings: [], is_applicability_domain_score: false },
    } as const;
    const pending = {
      confirmation_id: "confirm_1", session_id: "session_1", type: "compound_structure",
      status: "awaiting_confirmation", payload, payload_hash: "hash", canonical_smiles: "CCO",
      expected_state_version: 1, created_at: "2026-08-04T00:00:00Z", expires_at: "2026-08-04T00:10:00Z",
      version: 0, result_resource_id: null, error_code: null,
    } as const;
    expect(agentStreamEventSchema.safeParse({
      version: 1, session_id: "session_1", message_id: "msg_1", correlation_id: "corr_1",
      sequence: 0, type: "confirmation_required", pending_confirmation: pending, pending_action: null,
    }).success).toBe(true);
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
