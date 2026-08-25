import type { AgentEvent, ChatMessage, ChatState, ToolTrace } from "./types.ts";

export const emptyChatState = (): ChatState => ({
  sessionId: null,
  messages: [],
  running: false,
  step: 0,
});

export function beginTurn(state: ChatState, content: string, id: string = crypto.randomUUID()): ChatState {
  const user: ChatMessage = { id: `${id}-user`, role: "user", content };
  const assistant: ChatMessage = {
    id: `${id}-assistant`,
    role: "assistant",
    content: "",
    reasoning: "",
    reasoningComplete: false,
    reasoningOpen: true,
    tools: [],
    status: "streaming",
  };
  return { ...state, messages: [...state.messages, user, assistant], running: true };
}

function updateAssistant(
  state: ChatState,
  update: (message: ChatMessage) => ChatMessage,
): ChatState {
  let index = -1;
  for (let current = state.messages.length - 1; current >= 0; current -= 1) {
    if (state.messages[current].role === "assistant") {
      index = current;
      break;
    }
  }
  if (index < 0) return state;
  const messages = state.messages.slice();
  messages[index] = update(messages[index]);
  return { ...state, messages };
}

function updateTool(tools: ToolTrace[], callId: string, data: Record<string, unknown>): ToolTrace[] {
  return tools.map((tool) => {
    if (tool.id !== callId) return tool;
    const error = data.error ? String(data.error) : undefined;
    return {
      ...tool,
      status: error ? "failed" : "completed",
      output: data.output,
      error,
    };
  });
}

export function applyAgentEvent(state: ChatState, event: AgentEvent): ChatState {
  let next: ChatState = {
    ...state,
    sessionId: event.session_id || state.sessionId,
    step: Math.max(state.step, event.step),
  };

  switch (event.type) {
    case "turn.started":
      return { ...next, running: true };
    case "assistant.thinking.delta":
      return updateAssistant(next, (message) => ({
        ...message,
        reasoning: `${message.reasoning ?? ""}${String(event.data.delta ?? "")}`,
        reasoningOpen: true,
        reasoningComplete: false,
      }));
    case "assistant.content.delta":
      return updateAssistant(next, (message) => ({
        ...message,
        content: `${message.content}${String(event.data.delta ?? "")}`,
        reasoningOpen: false,
        reasoningComplete: Boolean(message.reasoning),
      }));
    case "tool.requested":
      return updateAssistant(next, (message) => ({
        ...message,
        tools: [
          ...(message.tools ?? []),
          {
            id: String(event.data.call_id ?? ""),
            name: String(event.data.tool_name ?? "tool"),
            arguments: event.data.arguments && typeof event.data.arguments === "object"
              ? event.data.arguments as Record<string, unknown>
              : {},
            status: "running",
          },
        ],
      }));
    case "tool.completed":
      return updateAssistant(next, (message) => ({
        ...message,
        tools: updateTool(message.tools ?? [], String(event.data.call_id ?? ""), event.data),
      }));
    case "assistant.completed":
    case "turn.completed":
      next = updateAssistant(next, (message) => ({
        ...message,
        content: message.content || String(event.data.content ?? ""),
        reasoningOpen: false,
        reasoningComplete: Boolean(message.reasoning),
        status: "completed",
      }));
      return { ...next, running: event.type !== "turn.completed" };
    case "turn.failed": {
      const reason = String(event.data.reason ?? "未知错误");
      next = updateAssistant(next, (message) => ({
        ...message,
        reasoningOpen: false,
        reasoningComplete: Boolean(message.reasoning),
        status: reason === "cancelled" ? "cancelled" : "failed",
        error: reason,
      }));
      return { ...next, running: false };
    }
    default:
      return next;
  }
}

export function setReasoningOpen(state: ChatState, messageId: string, open: boolean): ChatState {
  return {
    ...state,
    messages: state.messages.map((message) => (
      message.id === messageId ? { ...message, reasoningOpen: open } : message
    )),
  };
}
