const API_BASE = "/api/v1";

export type HealthResponse = {
  status: string;
  ollama: { available: boolean; chat_model: string; chat_model_installed: boolean };
};

export type ModelCatalog = {
  ollama_available: boolean;
  default_chat_model: string;
  chat_candidates: string[];
};

export type WorkspaceInfo = { path: string; name: string; current: boolean };
export type WorkspaceList = { current: WorkspaceInfo; items: WorkspaceInfo[] };
export type WorkspaceEntry = {
  name: string;
  path: string;
  kind: "file" | "directory";
  children: WorkspaceEntry[];
};

export type SessionSummaryResponse = {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turns: number;
};

export type SessionMessageResponse = {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  thinking: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SessionResponse = {
  session_id: string;
  created_at: string;
  messages: SessionMessageResponse[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  models: () => request<ModelCatalog>("/models"),
  workspaces: () => request<WorkspaceList>("/workspaces"),
  workspaceTree: () => request<WorkspaceEntry[]>("/workspaces/tree?depth=3"),
  selectWorkspace: (path: string) => request<WorkspaceInfo>("/workspaces/select", {
    method: "POST",
    body: JSON.stringify({ path }),
  }),
  async pickWorkspace(): Promise<WorkspaceInfo | null> {
    const response = await fetch(`${API_BASE}/workspaces/pick`, { method: "POST" });
    if (response.status === 204) return null;
    if (!response.ok) {
      const body = await response.text();
      throw new Error(body || `HTTP ${response.status}`);
    }
    return response.json() as Promise<WorkspaceInfo>;
  },
};
