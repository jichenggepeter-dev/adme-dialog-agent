import { API_BASE_URL } from "./constants";
import { agentErrorSchema, agentResponseSchema, confirmationSchema, messagePageSchema, predictionResourceSchema, resourceResponseSchema, sessionSchema } from "./agent-schemas";
import type { AgentResponse, Confirmation, PageContext } from "./agent-types";
import type { z } from "zod";
import type { PredictionResponse } from "./types";

export class AgentApiError extends Error { constructor(public code: string, message: string, public retryable = false, public correlationId?: string) { super(message); } }

async function request<T extends z.ZodTypeAny>(path: string, schema: T, init?: RequestInit, timeout = 45_000): Promise<z.infer<T>> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  const correlationId = crypto.randomUUID();
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal, headers: { "Content-Type": "application/json", "X-Correlation-ID": correlationId, ...init?.headers } });
    const payload: unknown = await response.json();
    if (!response.ok) {
      const parsed = agentErrorSchema.safeParse(payload);
      if (parsed.success) throw new AgentApiError(parsed.data.error.code, parsed.data.error.message, parsed.data.error.retryable, parsed.data.error.correlation_id);
      throw new AgentApiError("AGENT_RESPONSE_INVALID", "The Agent returned an invalid error response.", false, correlationId);
    }
    const parsed = schema.safeParse(payload);
    if (!parsed.success) throw new AgentApiError("AGENT_RESPONSE_INVALID", "The Agent returned data that did not match the client contract.", false, correlationId);
    return parsed.data;
  } catch (error) {
    if (error instanceof AgentApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new AgentApiError("AGENT_TIMEOUT", "The Assistant request timed out. Check its status before retrying confirmations.", true, correlationId);
    throw new AgentApiError("AGENT_OFFLINE", "The ADME Assistant is not reachable.", true, correlationId);
  } finally { window.clearTimeout(timer); }
}

export const createAgentSession = () => request("/agent/sessions", sessionSchema, { method: "POST" }, 10_000);
export const getAgentSession = (id: string) => request(`/agent/sessions/${encodeURIComponent(id)}`, sessionSchema, undefined, 10_000);
export const getAgentMessages = (id: string) => request(`/agent/sessions/${encodeURIComponent(id)}/messages`, messagePageSchema, undefined, 10_000);
export const sendAgentMessage = (sessionId: string, message: string, stateVersion: number, pageContext: PageContext): Promise<AgentResponse> => request("/agent/chat", agentResponseSchema, { method: "POST", body: JSON.stringify({ session_id: sessionId, message, expected_state_version: stateVersion, page_context: pageContext }) });
export const decideConfirmation = (sessionId: string, confirmationId: string, decision: "approve" | "reject", stateVersion: number): Promise<AgentResponse> => request("/agent/confirm", agentResponseSchema, { method: "POST", body: JSON.stringify({ session_id: sessionId, confirmation_id: confirmationId, decision, expected_state_version: stateVersion }) }, 120_000);
export const decidePendingAction = (sessionId: string, actionId: string, decision: "approve" | "reject", stateVersion: number): Promise<AgentResponse> => request("/agent/actions/decide", agentResponseSchema, { method: "POST", body: JSON.stringify({ session_id: sessionId, action_id: actionId, decision, expected_state_version: stateVersion }) }, 120_000);
export const getConfirmationStatus = (sessionId: string, confirmationId: string): Promise<Confirmation> => request(`/agent/confirmations/${encodeURIComponent(confirmationId)}?session_id=${encodeURIComponent(sessionId)}`, confirmationSchema, undefined, 10_000);
export async function getPredictionResource(sessionId: string, resourceId: string): Promise<PredictionResponse> {
  const resource = await request(`/agent/resources/${encodeURIComponent(resourceId)}?session_id=${encodeURIComponent(sessionId)}`, resourceResponseSchema, undefined, 15_000);
  const parsed = predictionResourceSchema.safeParse(resource.data);
  if (!parsed.success) throw new AgentApiError("AGENT_RESPONSE_INVALID", "The prediction resource did not match the client contract.");
  return parsed.data as unknown as PredictionResponse;
}
