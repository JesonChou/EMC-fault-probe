import { expect, test } from "vitest";
import { applyAgentEvent, beginTurn, emptyChatState, setReasoningOpen } from "./chat-state.ts";
import { readAgentEvents } from "./event-stream.ts";
import type { AgentEvent } from "./types.ts";

const event = (type: AgentEvent["type"], data: Record<string, unknown> = {}): AgentEvent => ({
  type,
  session_id: "session-1",
  step: 1,
  data,
});

test("reasoning follows the streaming lifecycle and stays user-toggleable", () => {
  let state = beginTurn(emptyChatState(), "怎么排查？", "turn-1");
  state = applyAgentEvent(state, event("assistant.thinking.delta", { delta: "先定位频点。" }));
  let assistant = state.messages[1];
  expect(assistant.reasoning).toBe("先定位频点。");
  expect(assistant.reasoningOpen).toBe(true);

  state = applyAgentEvent(state, event("assistant.content.delta", { delta: "建议检查时钟。" }));
  assistant = state.messages[1];
  expect(assistant.reasoningComplete).toBe(true);
  expect(assistant.reasoningOpen).toBe(false);
  expect(assistant.content).toBe("建议检查时钟。");

  state = setReasoningOpen(state, assistant.id, true);
  expect(state.messages[1].reasoningOpen).toBe(true);
});

test("tool calls transition from running to completed", () => {
  let state = beginTurn(emptyChatState(), "检索案例", "turn-2");
  state = applyAgentEvent(state, event("tool.requested", {
    call_id: "call-1",
    tool_name: "search_cases",
    arguments: { query: "ESD reset" },
  }));
  expect(state.messages[1].tools?.[0].status).toBe("running");
  state = applyAgentEvent(state, event("tool.completed", {
    call_id: "call-1",
    output: [{ id: 1 }, { id: 2 }],
    error: null,
  }));
  expect(state.messages[1].tools?.[0].status).toBe("completed");
});

test("SSE parser keeps events intact across transport chunks", async () => {
  const encoder = new TextEncoder();
  const chunks = [
    'data: {"type":"turn.started","session_id":"session-1",',
    '"step":0,"data":{}}\n\ndata: {"type":"assistant.content.delta",',
    '"session_id":"session-1","step":1,"data":{"delta":"ok"}}\n\n',
  ];
  const response = new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  }));
  const events: AgentEvent[] = [];
  for await (const item of readAgentEvents(response)) events.push(item);
  expect(events.map((item) => item.type)).toEqual(["turn.started", "assistant.content.delta"]);
  expect(events[1].data.delta).toBe("ok");
});
