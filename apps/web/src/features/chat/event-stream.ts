import type { AgentEvent } from "./types.ts";

export function parseEventBlock(block: string): AgentEvent | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;

  const parsed: unknown = JSON.parse(data);
  if (!parsed || typeof parsed !== "object") return null;
  const record = parsed as Record<string, unknown>;
  if (typeof record.type !== "string" || typeof record.session_id !== "string") return null;
  return {
    type: record.type as AgentEvent["type"],
    session_id: record.session_id,
    step: typeof record.step === "number" ? record.step : 0,
    data: record.data && typeof record.data === "object"
      ? record.data as Record<string, unknown>
      : {},
  };
}

export async function* readAgentEvents(
  response: Response,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败：HTTP ${response.status}`);
  }
  if (!response.body) throw new Error("浏览器未提供可读取的事件流");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) throw new DOMException("已停止生成", "AbortError");
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });

      let boundary = buffer.search(/\r?\n\r?\n/);
      while (boundary >= 0) {
        const separator = buffer.slice(boundary).match(/^\r?\n\r?\n/)?.[0] ?? "\n\n";
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + separator.length);
        const event = parseEventBlock(block);
        if (event) yield event;
        boundary = buffer.search(/\r?\n\r?\n/);
      }
      if (done) break;
    }
    const finalEvent = parseEventBlock(buffer);
    if (finalEvent) yield finalEvent;
  } finally {
    reader.releaseLock();
  }
}
