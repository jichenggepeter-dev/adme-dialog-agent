import type {
  AgentMessage,
  AgentResponse,
  AgentStreamEvent,
  StructuredPayload,
  ToolActivity,
} from "./agent-types";

export type StreamedAssistantMessage = AgentMessage & {
  payloads?: StructuredPayload[];
  tools?: ToolActivity[];
};

function placeholder(event: AgentStreamEvent): StreamedAssistantMessage {
  return {
    message_id: event.message_id,
    session_id: event.session_id,
    role: "assistant",
    content: "",
    created_at: new Date().toISOString(),
    metadata: {},
  };
}

export function applyStreamEvent(
  messages: StreamedAssistantMessage[],
  event: AgentStreamEvent,
): StreamedAssistantMessage[] {
  const current = messages.some((message) => message.message_id === event.message_id)
    ? messages
    : [...messages, placeholder(event)];

  if (event.type !== "message_delta" && event.type !== "tool_completed") {
    return current;
  }

  return current.map((message) => {
    if (message.message_id !== event.message_id) return message;
    if (event.type === "message_delta") {
      return { ...message, content: message.content + event.delta };
    }
    return { ...message, tools: [...(message.tools ?? []), event.tool_activity] };
  });
}

export function finalizeStreamedMessage(
  messages: StreamedAssistantMessage[],
  sessionId: string,
  response: AgentResponse,
): StreamedAssistantMessage[] {
  const completed: StreamedAssistantMessage = {
    message_id: response.message_id,
    session_id: sessionId,
    role: "assistant",
    content: response.text,
    created_at: new Date().toISOString(),
    metadata: {},
    payloads: response.structured_payloads,
    tools: response.tool_activity,
  };
  const index = messages.findIndex(
    (message) => message.message_id === response.message_id,
  );
  if (index < 0) return [...messages, completed];
  return messages.map((message, messageIndex) =>
    messageIndex === index ? { ...completed, created_at: message.created_at } : message,
  );
}
