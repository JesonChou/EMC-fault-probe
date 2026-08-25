import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "./types.ts";
import { ReasoningPanel } from "./ReasoningPanel.tsx";
import { ToolTraceCard } from "./ToolTraceCard.tsx";

type TranscriptProps = {
  messages: ChatMessage[];
  onReasoningToggle: (messageId: string, open: boolean) => void;
};

export function Transcript({ messages, onReasoningToggle }: TranscriptProps) {
  return (
    <div className="transcript" role="log" aria-label="会话内容">
      {messages.map((message) => message.role === "user" ? (
        <article className="message message--user" key={message.id}>
          <div>{message.content}</div>
        </article>
      ) : (
        <article className="message message--assistant" key={message.id}>
          <div className="assistant-avatar" aria-hidden="true"><img src="./emc_fault_probe.ico" alt="" /></div>
          <div className="assistant-turn">
            <span className="assistant-turn__name">EMC Agent</span>
            <ReasoningPanel
              text={message.reasoning ?? ""}
              running={message.status === "streaming" && !message.reasoningComplete}
              complete={Boolean(message.reasoningComplete)}
              open={Boolean(message.reasoningOpen)}
              onToggle={() => onReasoningToggle(message.id, !message.reasoningOpen)}
            />
            {message.tools?.map((tool) => <ToolTraceCard key={tool.id} tool={tool} />)}
            {message.content && <div className="assistant-answer"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>}
            {message.status === "failed" && <div className="turn-error">运行失败：{message.error}</div>}
            {message.status === "cancelled" && <div className="turn-cancelled">已停止生成</div>}
          </div>
        </article>
      ))}
    </div>
  );
}
