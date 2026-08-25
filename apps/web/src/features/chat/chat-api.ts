import { readAgentEvents } from "./event-stream.ts";
import type { AgentEvent, TurnOptions } from "./types.ts";

const API_BASE = "/api/v1";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export const chatApi = {
  listSessions: <T>() => json<T>("/sessions"),
  getSession: <T>(sessionId: string) => json<T>(`/sessions/${encodeURIComponent(sessionId)}`),
  createSession: <T>() => json<T>("/sessions", { method: "POST", body: "{}" }),
  cancel: (sessionId: string) => json<{ cancelled: boolean }>(
    `/sessions/${encodeURIComponent(sessionId)}/cancel`,
    { method: "POST", body: "{}" },
  ),
  async *send(
    sessionId: string,
    content: string,
    options: TurnOptions,
    signal?: AbortSignal,
  ): AsyncGenerator<AgentEvent> {
    const response = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ content, ...options }),
      signal,
    });
    yield* readAgentEvents(response, signal);
  },
};
