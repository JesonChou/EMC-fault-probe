import { ArrowRight, AtSign, Database, Search, ShieldCheck } from "lucide-react";
import { BrandMark } from "./BrandMark";

const suggestions = [
  {
    eyebrow: "辐射发射",
    title: "200 MHz 附近超标，应该从哪里开始排查？",
  },
  {
    eyebrow: "静电放电",
    title: "检索设备复位案例，并给出分步整改建议",
  },
  {
    eyebrow: "传导骚扰",
    title: "分析开关电源常见耦合路径与验证方法",
  },
];

export function Welcome({ onSuggestion }: { onSuggestion: (value: string) => void }) {
  return (
    <section className="welcome">
      <BrandMark large />
      <h1>今天想解决什么 EMC 问题？</h1>
      <p>描述现象、测试条件或超标频点。Agent 会按需检索本地案例，再给出可验证的诊断路径。</p>
      <div className="welcome__capabilities" aria-label="支持的输入能力">
        <span><Search size={13} /> 检索案例</span>
        <span><AtSign size={13} /> 引用工作区</span>
        <span><ShieldCheck size={13} /> 本地推理</span>
      </div>
      <div className="suggestion-list">
        {suggestions.map((item) => (
          <button type="button" key={item.title} onClick={() => onSuggestion(item.title)}>
            <Database size={15} />
            <span>
              <small>{item.eyebrow}</small>
              <strong>{item.title}</strong>
            </span>
            <ArrowRight size={15} />
          </button>
        ))}
      </div>
    </section>
  );
}
