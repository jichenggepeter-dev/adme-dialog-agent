import type {
  AgentActivityItem,
  AgentStreamEvent,
  EvidenceAnswerData,
  EvidenceCitation,
} from "./agent-types";

export const MAX_ACTIVITY_ITEMS = 40;

function item(
  event: AgentStreamEvent,
  kind: AgentActivityItem["kind"],
  status: AgentActivityItem["status"],
  suffix: string,
  detail: Partial<AgentActivityItem> = {},
): AgentActivityItem {
  return {
    id: `${event.correlation_id}:${event.sequence}:${kind}:${suffix}`,
    kind,
    status,
    occurred_at: event.occurred_at ?? new Date().toISOString(),
    correlation_id: event.correlation_id,
    sequence: event.sequence,
    ...detail,
  };
}

function evidenceItems(
  event: Extract<AgentStreamEvent, { type: "response_completed" }>,
  data: EvidenceAnswerData,
): AgentActivityItem[] {
  const citations = new Map<string, EvidenceCitation>();
  for (const citation of data.evidence) citations.set(citation.chunk_id, citation);
  for (const claim of data.claims) {
    for (const citation of claim.evidence) citations.set(citation.chunk_id, citation);
  }
  if (citations.size === 0) {
    return [
      item(event, "unknown", data.status, data.status, {
        recovery: "refine_question",
      }),
    ];
  }
  return [...citations.values()].map((citation) =>
    item(event, "evidence", data.status, citation.chunk_id, {
      source_title: citation.title,
      source_url: citation.url,
      chunk_id: citation.chunk_id,
    }),
  );
}

export function activityItemsFromEvent(event: AgentStreamEvent): AgentActivityItem[] {
  if (event.type === "heartbeat") {
    return [item(event, "request", "started", "accepted")];
  }
  if (event.type === "tool_started") {
    return [item(event, "tool", "started", event.tool_name, { tool_name: event.tool_name })];
  }
  if (event.type === "tool_completed") {
    const activity = event.tool_activity;
    return [
      item(
        event,
        "tool",
        activity.status === "completed" ? "completed" : activity.status === "blocked" ? "blocked" : "error",
        `${activity.tool_name}:${activity.status}`,
        {
          tool_name: activity.tool_name,
          ...(activity.error_code ? { error_code: activity.error_code } : {}),
          ...(activity.duration_ms == null ? {} : { duration_ms: activity.duration_ms }),
          ...(activity.status === "completed" ? {} : { recovery: "review_error" as const }),
        },
      ),
    ];
  }
  if (event.type === "confirmation_required") {
    return [item(event, "confirmation", "waiting", "required", { recovery: "review_confirmation" })];
  }
  if (event.type === "error") {
    return [
      item(event, "error", "error", event.code, {
        error_code: event.code,
        recovery: event.retryable ? "edit_and_retry" : "review_error",
      }),
    ];
  }
  if (event.type === "response_completed") {
    const activities = event.structured_payloads.flatMap((payload) =>
      payload.type === "evidence_answer" ? evidenceItems(event, payload.data) : [],
    );
    return [...activities, item(event, "response", "completed", "completed")];
  }
  return [];
}

export function appendActivityFromEvent(
  current: AgentActivityItem[],
  event: AgentStreamEvent,
): AgentActivityItem[] {
  if (event.type === "heartbeat" && current.some((entry) => entry.kind === "request")) {
    return current;
  }
  const byId = new Map(current.map((entry) => [entry.id, entry]));
  for (const entry of activityItemsFromEvent(event)) byId.set(entry.id, entry);
  return [...byId.values()].slice(-MAX_ACTIVITY_ITEMS);
}
