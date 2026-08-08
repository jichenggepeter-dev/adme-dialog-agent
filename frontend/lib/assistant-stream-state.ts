import type {
  AgentActivityItem,
  AgentMessage,
  AgentResponse,
  AgentStreamEvent,
  StructuredPayload,
  ToolActivity,
} from "./agent-types";
import { appendActivityFromEvent } from "./agent-activity-trace";

export type StreamedAssistantMessage = AgentMessage & {
  payloads?: StructuredPayload[];
  tools?: ToolActivity[];
  activity?: AgentActivityItem[];
  stream_correlation_id?: string;
};

function placeholder(event: AgentStreamEvent): StreamedAssistantMessage {
  return {
    message_id: event.message_id,
    session_id: event.session_id,
    role: "assistant",
    content: "",
    created_at: new Date().toISOString(),
    metadata: {},
    stream_correlation_id: event.correlation_id,
  };
}

export function applyStreamEvent(
  messages: StreamedAssistantMessage[],
  event: AgentStreamEvent,
): StreamedAssistantMessage[] {
  const current = messages.some((message) =>
    message.message_id === event.message_id
      && message.session_id === event.session_id
      && message.stream_correlation_id === event.correlation_id)
    ? messages
    : [...messages, placeholder(event)];

  return current.map((message) => {
    if (
      message.message_id !== event.message_id
      || message.session_id !== event.session_id
      || message.stream_correlation_id !== event.correlation_id
    ) return message;
    const activity = appendActivityFromEvent(message.activity ?? [], event);
    if (event.type === "message_delta") {
      return { ...message, content: message.content + event.delta, activity };
    }
    if (event.type === "tool_completed") {
      return { ...message, tools: [...(message.tools ?? []), event.tool_activity], activity };
    }
    return { ...message, activity };
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
  const index = messages.findIndex((message) =>
    message.message_id === response.message_id && message.session_id === sessionId);
  if (index < 0) return [...messages, completed];
  return messages.map((message, messageIndex) =>
    messageIndex === index
      ? {
          ...completed,
          created_at: message.created_at,
          activity: message.activity,
          stream_correlation_id: message.stream_correlation_id,
        }
      : message,
  );
}
