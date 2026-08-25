export type AgentEventType =
  | "turn.started"
  | "assistant.thinking.delta"
  | "assistant.content.delta"
  | "tool.requested"
  | "tool.completed"
  | "assistant.completed"
  | "turn.completed"
  | "turn.failed";

export type AgentEvent = {
  type: AgentEventType;
  session_id: string;
  step: number;
  data: Record<string, unknown>;
};

export type ToolTrace = {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "running" | "completed" | "failed";
  output?: unknown;
  error?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  reasoningComplete?: boolean;
  reasoningOpen?: boolean;
  tools?: ToolTrace[];
  status?: "streaming" | "completed" | "failed" | "cancelled";
  error?: string;
};

export type ChatState = {
  sessionId: string | null;
  messages: ChatMessage[];
  running: boolean;
  step: number;
};

export type TurnOptions = {
  model?: string;
  think?: boolean;
  workspace_path?: string;
};
