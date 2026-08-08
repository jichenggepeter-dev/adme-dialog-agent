import { API_BASE_URL } from "./constants";
import {
  agentErrorSchema,
  agentResponseSchema,
  agentStreamEventSchema,
  confirmationSchema,
  messagePageSchema,
  predictionResourceSchema,
  resourceResponseSchema,
  sessionSchema,
  sessionDeletionProposalSchema,
  sessionDeletionResultSchema,
  sessionExportProposalSchema,
  sessionExportResultSchema,
} from "./agent-schemas";
import type {
  AgentResponse,
  AgentStreamError,
  AgentStreamEvent,
  AgentStreamResponseCompleted,
  Confirmation,
  PageContext,
  SessionDeletionProposal,
  SessionDeletionResult,
  SessionExportFormat,
  SessionExportProposal,
  SessionExportResult,
} from "./agent-types";
import type { z } from "zod";
import type { PredictionResponse } from "./types";
import type { MockScenarioSelection } from "./review-mode";

export class AgentApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryable = false,
    public correlationId?: string,
  ) {
    super(message);
    this.name = "AgentApiError";
  }
}

async function request<T extends z.ZodTypeAny>(
  path: string,
  schema: T,
  init?: RequestInit,
  timeout = 45_000,
): Promise<z.infer<T>> {
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), timeout);
  const correlationId = crypto.randomUUID();
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlationId,
        ...init?.headers,
      },
    });
    const payload: unknown = await response.json();
    if (!response.ok) {
      const parsed = agentErrorSchema.safeParse(payload);
      if (parsed.success) {
        throw new AgentApiError(
          parsed.data.error.code,
          parsed.data.error.message,
          parsed.data.error.retryable,
          parsed.data.error.correlation_id,
        );
      }
      throw new AgentApiError(
        "AGENT_RESPONSE_INVALID",
        "The Agent returned an invalid error response.",
        false,
        correlationId,
      );
    }
    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw new AgentApiError(
        "AGENT_RESPONSE_INVALID",
        "The Agent returned data that did not match the client contract.",
        false,
        correlationId,
      );
    }
    return parsed.data;
  } catch (error) {
    if (error instanceof AgentApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AgentApiError(
        "AGENT_TIMEOUT",
        "The Assistant request timed out. Check its status before retrying confirmations.",
        true,
        correlationId,
      );
    }
    throw new AgentApiError(
      "AGENT_OFFLINE",
      "The ADME Assistant is not reachable.",
      true,
      correlationId,
    );
  } finally {
    globalThis.clearTimeout(timer);
  }
}

export type AgentStreamOptions = {
  signal?: AbortSignal;
  timeoutMs?: number;
  onEvent?: (event: AgentStreamEvent) => void;
  mockScenario?: MockScenarioSelection;
};

type StreamIdentity = {
  sessionId: string;
  correlationId: string;
};

function invalidStream(message: string, correlationId: string): AgentApiError {
  return new AgentApiError("AGENT_STREAM_INVALID", message, false, correlationId);
}

function sequenceError(message: string, correlationId: string): AgentApiError {
  return new AgentApiError("AGENT_STREAM_SEQUENCE", message, false, correlationId);
}

export async function consumeAgentEventStream(
  stream: ReadableStream<Uint8Array>,
  identity: StreamIdentity,
  onEvent?: (event: AgentStreamEvent) => void,
): Promise<AgentResponse> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  const acceptedBySequence = new Map<number, string>();
  let buffer = "";
  let messageId: string | null = null;
  let expectedSequence = 0;
  let text = "";
  const streamState: {
    terminal: AgentStreamResponseCompleted | AgentStreamError | null;
  } = { terminal: null };

  const processLine = (line: string) => {
    const content = line.trim();
    if (!content) return;

    let raw: unknown;
    try {
      raw = JSON.parse(content);
    } catch {
      throw invalidStream(
        "The Assistant stream contained malformed JSON.",
        identity.correlationId,
      );
    }

    const parsed = agentStreamEventSchema.safeParse(raw);
    if (!parsed.success) {
      throw invalidStream(
        "The Assistant stream contained an invalid or unknown event.",
        identity.correlationId,
      );
    }
    const event = parsed.data as AgentStreamEvent;

    if (
      event.session_id !== identity.sessionId ||
      event.correlation_id !== identity.correlationId
    ) {
      throw invalidStream(
        "The Assistant stream identity did not match the request.",
        identity.correlationId,
      );
    }
    if (messageId !== null && event.message_id !== messageId) {
      throw invalidStream(
        "The Assistant stream changed message identity.",
        identity.correlationId,
      );
    }
    if (messageId === null) messageId = event.message_id;

    if (streamState.terminal !== null) {
      throw new AgentApiError(
        "AGENT_STREAM_TERMINAL",
        "The Assistant stream sent data after its terminal event.",
        false,
        identity.correlationId,
      );
    }

    const canonical = JSON.stringify(event);
    if (event.sequence < expectedSequence) {
      const previous = acceptedBySequence.get(event.sequence);
      if (previous === canonical) return;
      throw sequenceError(
        "The Assistant stream sent a stale or conflicting event.",
        identity.correlationId,
      );
    }
    if (event.sequence > expectedSequence) {
      throw sequenceError(
        "The Assistant stream skipped an event sequence.",
        identity.correlationId,
      );
    }

    acceptedBySequence.set(event.sequence, canonical);
    expectedSequence += 1;

    if (event.type === "message_delta") text += event.delta;
    if (event.type === "response_completed" || event.type === "error") {
      streamState.terminal = event;
    }
    onEvent?.(event);
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        processLine(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf("\n");
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) processLine(buffer);
  } finally {
    reader.releaseLock();
  }

  const terminal = streamState.terminal;
  if (terminal === null || messageId === null) {
    throw new AgentApiError(
      "AGENT_STREAM_INCOMPLETE",
      "The Assistant connection ended before a terminal event.",
      true,
      identity.correlationId,
    );
  }
  if (terminal.type === "error") {
    throw new AgentApiError(
      terminal.code,
      terminal.message,
      terminal.retryable,
      terminal.correlation_id,
    );
  }

  return {
    message_id: messageId,
    text,
    structured_payloads: terminal.structured_payloads,
    pending_confirmation: terminal.pending_confirmation,
    pending_action: terminal.pending_action,
    tool_activity: terminal.tool_activity,
    ui_action_proposals: terminal.ui_action_proposals,
    warnings: terminal.warnings,
    state_version: terminal.state_version,
  };
}

export async function streamAgentMessage(
  sessionId: string,
  message: string,
  stateVersion: number,
  pageContext: PageContext,
  options: AgentStreamOptions = {},
): Promise<AgentResponse> {
  const correlationId = crypto.randomUUID();
  const controller = new AbortController();
  let abortKind: "caller" | "timeout" | null = null;
  const abortFromCaller = () => {
    abortKind = "caller";
    controller.abort();
  };
  if (options.signal?.aborted) abortFromCaller();
  else options.signal?.addEventListener("abort", abortFromCaller, { once: true });

  const timer = globalThis.setTimeout(() => {
    abortKind = "timeout";
    controller.abort();
  }, options.timeoutMs ?? 120_000);

  try {
    const response = await fetch(`${API_BASE_URL}/agent/chat/stream`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlationId,
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        expected_state_version: stateVersion,
        page_context: pageContext,
        ...(options.mockScenario
          ? { mock_scenario: options.mockScenario }
          : {}),
      }),
    });

    if (!response.ok) {
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        throw new AgentApiError(
          "AGENT_RESPONSE_INVALID",
          "The Agent returned an invalid error response.",
          false,
          correlationId,
        );
      }
      const parsed = agentErrorSchema.safeParse(payload);
      if (parsed.success) {
        throw new AgentApiError(
          parsed.data.error.code,
          parsed.data.error.message,
          parsed.data.error.retryable,
          parsed.data.error.correlation_id,
        );
      }
      throw new AgentApiError(
        "AGENT_RESPONSE_INVALID",
        "The Agent returned an invalid error response.",
        false,
        correlationId,
      );
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.toLowerCase().startsWith("application/x-ndjson")) {
      throw invalidStream(
        "The Assistant returned an unexpected streaming content type.",
        correlationId,
      );
    }
    if (!response.body) {
      throw invalidStream("The Assistant returned an empty stream.", correlationId);
    }

    return await consumeAgentEventStream(
      response.body,
      { sessionId, correlationId },
      options.onEvent,
    );
  } catch (error) {
    if (error instanceof AgentApiError) throw error;
    if (
      controller.signal.aborted ||
      (error instanceof DOMException && error.name === "AbortError")
    ) {
      if (abortKind === "caller") {
        throw new AgentApiError(
          "AGENT_STREAM_ABORTED",
          "Stopped waiting for the Assistant response. The server may still finish the request; review the session before retrying.",
          true,
          correlationId,
        );
      }
      throw new AgentApiError(
        "AGENT_STREAM_TIMEOUT",
        "The Assistant stream timed out. The server may still finish the request; review the session before retrying.",
        true,
        correlationId,
      );
    }
    throw new AgentApiError(
      "AGENT_STREAM_NETWORK",
      "The Assistant connection was interrupted. The server may still finish the request; review the session before retrying.",
      true,
      correlationId,
    );
  } finally {
    globalThis.clearTimeout(timer);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
}

export const createAgentSession = () =>
  request("/agent/sessions", sessionSchema, { method: "POST" }, 10_000);

export const getAgentSession = (id: string) =>
  request(`/agent/sessions/${encodeURIComponent(id)}`, sessionSchema, undefined, 10_000);

export const getAgentMessages = (id: string) =>
  request(
    `/agent/sessions/${encodeURIComponent(id)}/messages`,
    messagePageSchema,
    undefined,
    10_000,
  );

export const prepareSessionDeletion = (
  sessionId: string,
  stateVersion: number,
): Promise<SessionDeletionProposal> =>
  request(
    `/agent/sessions/${encodeURIComponent(sessionId)}/deletions`,
    sessionDeletionProposalSchema,
    {
      method: "POST",
      body: JSON.stringify({ expected_state_version: stateVersion }),
    },
    15_000,
  );

export const prepareSessionExport = (
  sessionId: string,
  format: SessionExportFormat,
  stateVersion: number,
): Promise<SessionExportProposal> =>
  request(
    `/agent/sessions/${encodeURIComponent(sessionId)}/exports`,
    sessionExportProposalSchema,
    {
      method: "POST",
      body: JSON.stringify({
        format,
        expected_state_version: stateVersion,
        resource_ids: [],
      }),
    },
    15_000,
  );

export const decideSessionDeletion = (
  sessionId: string,
  actionId: string,
  decision: "approve" | "reject",
  stateVersion: number,
): Promise<SessionDeletionResult> =>
  request(
    `/agent/sessions/${encodeURIComponent(sessionId)}/deletions/${encodeURIComponent(actionId)}`,
    sessionDeletionResultSchema,
    {
      method: "POST",
      body: JSON.stringify({ decision, expected_state_version: stateVersion }),
    },
    30_000,
  );

export const decideSessionExport = (
  sessionId: string,
  actionId: string,
  decision: "approve" | "reject",
  stateVersion: number,
): Promise<SessionExportResult> =>
  request(
    `/agent/sessions/${encodeURIComponent(sessionId)}/exports/${encodeURIComponent(actionId)}`,
    sessionExportResultSchema,
    {
      method: "POST",
      body: JSON.stringify({ decision, expected_state_version: stateVersion }),
    },
    30_000,
  );

export const sendAgentMessage = (
  sessionId: string,
  message: string,
  stateVersion: number,
  pageContext: PageContext,
): Promise<AgentResponse> =>
  request("/agent/chat", agentResponseSchema, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      message,
      expected_state_version: stateVersion,
      page_context: pageContext,
    }),
  });

export const decideConfirmation = (
  sessionId: string,
  confirmationId: string,
  decision: "approve" | "reject",
  stateVersion: number,
): Promise<AgentResponse> =>
  request(
    "/agent/confirm",
    agentResponseSchema,
    {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        confirmation_id: confirmationId,
        decision,
        expected_state_version: stateVersion,
      }),
    },
    120_000,
  );

export const decidePendingAction = (
  sessionId: string,
  actionId: string,
  decision: "approve" | "reject",
  stateVersion: number,
): Promise<AgentResponse> =>
  request(
    "/agent/actions/decide",
    agentResponseSchema,
    {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        action_id: actionId,
        decision,
        expected_state_version: stateVersion,
      }),
    },
    120_000,
  );

export const getConfirmationStatus = (
  sessionId: string,
  confirmationId: string,
): Promise<Confirmation> =>
  request(
    `/agent/confirmations/${encodeURIComponent(confirmationId)}?session_id=${encodeURIComponent(sessionId)}`,
    confirmationSchema,
    undefined,
    10_000,
  );

export async function getPredictionResource(
  sessionId: string,
  resourceId: string,
): Promise<PredictionResponse> {
  const resource = await request(
    `/agent/resources/${encodeURIComponent(resourceId)}?session_id=${encodeURIComponent(sessionId)}`,
    resourceResponseSchema,
    undefined,
    15_000,
  );
  const parsed = predictionResourceSchema.safeParse(resource.data);
  if (!parsed.success) {
    throw new AgentApiError(
      "AGENT_RESPONSE_INVALID",
      "The prediction resource did not match the client contract.",
    );
  }
  return parsed.data as unknown as PredictionResponse;
}
