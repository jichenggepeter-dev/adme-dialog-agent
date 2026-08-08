import { describe, expect, it } from "vitest";
import type { AgentActivityItem, AgentStreamEvent } from "./agent-types";
import {
  MAX_ACTIVITY_ITEMS,
  appendActivityFromEvent,
  activityItemsFromEvent,
} from "./agent-activity-trace";

const base = {
  version: 1 as const,
  session_id: "session_1",
  message_id: "msg_1",
  correlation_id: "corr_1",
  occurred_at: "2026-08-06T12:00:00.000Z",
};

const citation = {
  source_id: "fda-m12-2024",
  title: "M12 Drug Interaction Studies",
  organization: "U.S. Food and Drug Administration",
  url: "https://www.fda.gov/m12",
  document_date: "2024-08",
  version: "Final",
  status: "current" as const,
  captured_at: "2026-08-03",
  section: "Summary",
  page: null,
  chunk_id: "fda-m12-2024:fixture",
  excerpt: "Bounded evidence excerpt.",
};

describe("Agent activity trace projection", () => {
  it("projects request, tool start/end, confirmation, and retryable error without content", () => {
    const events: AgentStreamEvent[] = [
      { ...base, type: "heartbeat", sequence: 0 },
      { ...base, type: "tool_started", sequence: 1, tool_name: "resolve_compound" },
      {
        ...base,
        type: "tool_completed",
        sequence: 2,
        tool_activity: {
          tool_name: "resolve_compound",
          status: "completed",
          error_code: null,
          resource_id: "resource_1",
          started_at: base.occurred_at,
          completed_at: base.occurred_at,
          duration_ms: 0,
        },
      },
      {
        ...base,
        type: "confirmation_required",
        sequence: 3,
        pending_confirmation: null,
        pending_action: {
          action_id: "action_1",
          session_id: "session_1",
          action_type: "run_batch_job",
          status: "awaiting_confirmation",
          payload: { job_id: "job_1", action_type: "run_batch_job", status_at_proposal: "ready" },
          payload_hash: "hash",
          expected_state_version: 0,
          created_at: base.occurred_at,
          expires_at: base.occurred_at,
          consumed_at: null,
        },
      },
      { ...base, type: "error", sequence: 4, code: "AGENT_TIMEOUT", message: "Timed out", retryable: true },
    ];

    const items = events.flatMap(activityItemsFromEvent);
    expect(items.map((item) => [item.kind, item.status])).toEqual([
      ["request", "started"],
      ["tool", "started"],
      ["tool", "completed"],
      ["confirmation", "waiting"],
      ["error", "error"],
    ]);
    expect(items.at(-1)?.recovery).toBe("edit_and_retry");
    expect(JSON.stringify(items)).not.toContain("Timed out");
    expect(Object.keys(items.at(-1) ?? {}).sort()).toEqual([
      "correlation_id", "error_code", "id", "kind", "occurred_at", "recovery", "sequence", "status",
    ]);
  });

  it("links supported evidence once and turns no evidence into an unknown", () => {
    const supported: AgentStreamEvent = {
      ...base,
      type: "response_completed",
      sequence: 1,
      structured_payloads: [{
        type: "evidence_answer",
        data: {
          query: "not copied to trace",
          status: "supported",
          availability: "available",
          assistant_summary: "Bounded summary",
          claims: [{ text: "Bounded claim", evidence: [citation] }],
          evidence: [citation, citation],
          source_count: 1,
          warnings: [],
        },
      }],
      pending_confirmation: null,
      pending_action: null,
      tool_activity: [],
      ui_action_proposals: [],
      warnings: [],
      state_version: 1,
    };
    const noEvidence: AgentStreamEvent = {
      ...supported,
      sequence: 2,
      structured_payloads: [{
        type: "evidence_answer",
        data: {
          query: "not copied to trace",
          status: "no_evidence",
          availability: "available",
          assistant_summary: "No evidence",
          claims: [],
          evidence: [],
          source_count: 0,
          warnings: [],
        },
      }],
    };

    const supportedItems = activityItemsFromEvent(supported);
    expect(supportedItems.filter((item) => item.kind === "evidence")).toHaveLength(1);
    expect(supportedItems.find((item) => item.kind === "evidence")).toMatchObject({
      source_url: citation.url,
      chunk_id: citation.chunk_id,
      status: "supported",
    });
    expect(JSON.stringify(supportedItems)).not.toContain("not copied to trace");
    expect(activityItemsFromEvent(noEvidence)).toContainEqual(
      expect.objectContaining({ kind: "unknown", status: "no_evidence", recovery: "refine_question" }),
    );
  });

  it("deduplicates entries and enforces the display bound", () => {
    let items: AgentActivityItem[] = [];
    for (let sequence = 0; sequence < MAX_ACTIVITY_ITEMS + 10; sequence += 1) {
      const event: AgentStreamEvent = { ...base, type: "tool_started", sequence, tool_name: "resolve_compound" };
      items = appendActivityFromEvent(items, event);
      items = appendActivityFromEvent(items, event);
    }
    expect(items).toHaveLength(MAX_ACTIVITY_ITEMS);
    expect(new Set(items.map((item) => item.id)).size).toBe(items.length);
  });

  it("keeps only the first stream heartbeat", () => {
    const first: AgentStreamEvent = { ...base, type: "heartbeat", sequence: 0 };
    const second: AgentStreamEvent = { ...base, type: "heartbeat", sequence: 1 };
    expect(appendActivityFromEvent(appendActivityFromEvent([], first), second)).toHaveLength(1);
  });
});
