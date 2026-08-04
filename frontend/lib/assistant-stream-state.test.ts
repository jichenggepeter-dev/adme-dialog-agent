import { describe, expect, it } from "vitest";
import type { AgentResponse, AgentStreamEvent } from "./agent-types";
import { applyStreamEvent, finalizeStreamedMessage } from "./assistant-stream-state";

const base = { version: 1 as const, session_id: "session_1", message_id: "msg_1", correlation_id: "corr_1" };

describe("streamed assistant message state", () => {
  it("creates one placeholder, appends deltas to it, and finalizes it once", () => {
    let messages = applyStreamEvent([], { ...base, type: "heartbeat", sequence: 0 });
    messages = applyStreamEvent(messages, { ...base, type: "message_delta", sequence: 1, delta: "Hello " });
    messages = applyStreamEvent(messages, { ...base, type: "message_delta", sequence: 2, delta: "world" });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({ message_id: "msg_1", content: "Hello world" });

    const response: AgentResponse = { message_id: "msg_1", text: "Hello world", structured_payloads: [{ type: "none", data: {} }], pending_confirmation: null, pending_action: null, tool_activity: [], ui_action_proposals: [], warnings: [], state_version: 2 };
    messages = finalizeStreamedMessage(messages, "session_1", response);
    messages = finalizeStreamedMessage(messages, "session_1", response);
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({ content: "Hello world", payloads: response.structured_payloads });
  });

  it("records tool completion on the same placeholder", () => {
    const event: AgentStreamEvent = { ...base, type: "tool_completed", sequence: 0, tool_activity: { tool_name: "resolve_compound", status: "completed", error_code: null, resource_id: null } };
    const messages = applyStreamEvent([], event);
    expect(messages).toHaveLength(1);
    expect(messages[0].tools).toEqual([event.tool_activity]);
  });
});
