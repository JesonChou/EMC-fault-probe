import { Check, Database, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ToolTrace } from "./types.ts";

export function ToolTraceCard({ tool }: { tool: ToolTrace }) {
  const query = typeof tool.arguments.query === "string" ? tool.arguments.query : "";
  const count = Array.isArray(tool.output) ? tool.output.length : null;
  const label = tool.name === "search_cases" ? "检索 EMC 案例" : `调用 ${tool.name}`;
  return (
    <div className={`tool-trace tool-trace--${tool.status}`}>
      <span className="tool-trace__icon"><Database size={14} /></span>
      <span className="tool-trace__copy">
        <strong>{label}</strong>
        <small>
          {tool.status === "running" && (query ? `正在检索：${query}` : "工具正在运行")}
          {tool.status === "completed" && (count === null ? "工具调用完成" : `找到 ${count} 条相关资料`)}
          {tool.status === "failed" && (tool.error || "工具调用失败")}
        </small>
      </span>
      <span className="tool-trace__status">
        {tool.status === "running" && <LoaderCircle size={13} />}
        {tool.status === "completed" && <Check size={13} />}
        {tool.status === "failed" && <TriangleAlert size={13} />}
      </span>
    </div>
  );
}
