import { afterEach, describe, expect, it, vi } from "vitest";
import { consumeAgentEventStream, streamAgentMessage } from "./agent-api";

const identity = { sessionId: "session_1", correlationId: "corr_1" };
const envelope = { version: 1 as const, session_id: "session_1", message_id: "msg_1", correlation_id: "corr_1" };

function streamChunks(chunks: string[]) {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}

function completed(sequence: number) {
  return { ...envelope, type: "response_completed", sequence, structured_payloads: [], pending_confirmation: null, pending_action: null, tool_activity: [], ui_action_proposals: [], warnings: [], state_version: 1 };
}

afterEach(() => vi.unstubAllGlobals());

describe("Agent NDJSON stream", () => {
  it("assembles ordered deltas split across arbitrary chunks", async () => {
    const lines = [
      JSON.stringify({ ...envelope, type: "heartbeat", sequence: 0 }),
      JSON.stringify({ ...envelope, type: "message_delta", sequence: 1, delta: "Hello " }),
      JSON.stringify({ ...envelope, type: "message_delta", sequence: 2, delta: "world" }),
      JSON.stringify(completed(3)),
    ].join("\n") + "\n";
    const response = await consumeAgentEventStream(
      streamChunks([lines.slice(0, 17), lines.slice(17, 83), lines.slice(83)]),
      identity,
    );
    expect(response).toMatchObject({ message_id: "msg_1", text: "Hello world", state_version: 1 });
  });

  it("deduplicates an identical legacy event without an activity timestamp", async () => {
    const heartbeat = JSON.stringify({ ...envelope, type: "heartbeat", sequence: 0 });
    const body = `${heartbeat}\n${heartbeat}\n${JSON.stringify(completed(1))}\n`;

    await expect(consumeAgentEventStream(streamChunks([body]), identity)).resolves.toMatchObject({
      message_id: "msg_1",
      state_version: 1,
    });
  });

  it.each([
    ["unknown event", { ...envelope, type: "mystery", sequence: 0 }, "AGENT_STREAM_INVALID"],
    ["wrong identity", { ...envelope, session_id: "session_2", type: "heartbeat", sequence: 0 }, "AGENT_STREAM_INVALID"],
    ["skipped sequence", { ...envelope, type: "heartbeat", sequence: 1 }, "AGENT_STREAM_SEQUENCE"],
  ])("rejects %s", async (_name, event, code) => {
    await expect(consumeAgentEventStream(streamChunks([JSON.stringify(event) + "\n"]), identity)).rejects.toMatchObject({ code });
  });

  it("rejects events after the terminal event", async () => {
    const body = [completed(0), { ...envelope, type: "message_delta", sequence: 1, delta: "late" }]
      .map((event) => JSON.stringify(event)).join("\n") + "\n";
    await expect(consumeAgentEventStream(streamChunks([body]), identity)).rejects.toMatchObject({ code: "AGENT_STREAM_TERMINAL" });
  });

  it("maps a caller abort without claiming server cancellation", async () => {
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    })));
    const controller = new AbortController();
    const request = streamAgentMessage("session_1", "hello", 0, { page: "single" }, { signal: controller.signal });
    controller.abort();
    await expect(request).rejects.toMatchObject({ code: "AGENT_STREAM_ABORTED" });
  });

  it("sends the selected deterministic Mock Agent scenario", async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      void url;
      capturedInit = init;
      return new Response(JSON.stringify({
        error: {
          code: "TEST_STOP",
          message: "Request captured.",
          details: null,
          retryable: false,
          correlation_id: "corr_test",
        },
      }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(streamAgentMessage(
      "session_1",
      "run the selected scenario",
      0,
      { page: "single" },
      { mockScenario: { catalog_version: 1, id: "tool_failure" } },
    )).rejects.toMatchObject({ code: "TEST_STOP" });

    const body = JSON.parse(String(capturedInit?.body));
    expect(body.mock_scenario).toEqual({
      catalog_version: 1,
      id: "tool_failure",
    });
  });
});
