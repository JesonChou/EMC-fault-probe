import { BrainCircuit, ChevronRight } from "lucide-react";

type ReasoningPanelProps = {
  text: string;
  running: boolean;
  complete: boolean;
  open: boolean;
  onToggle: () => void;
};

export function ReasoningPanel({ text, running, complete, open, onToggle }: ReasoningPanelProps) {
  if (!text) return null;
  const summary = text.replace(/\s+/g, " ").trim().slice(0, 96);
  return (
    <section className={`reasoning${running ? " reasoning--running" : ""}`}>
      <button type="button" className="reasoning__head" onClick={onToggle} aria-expanded={open}>
        <span className="reasoning__icon"><BrainCircuit size={13} /></span>
        <span>{running ? "正在思考" : complete ? "思考过程" : "分析中"}</span>
        {running && <span className="reasoning__pulse" aria-hidden="true" />}
        {!open && <span className="reasoning__summary">{summary}{text.length > 96 ? "…" : ""}</span>}
        <ChevronRight className={open ? "reasoning__chevron reasoning__chevron--open" : "reasoning__chevron"} size={13} />
      </button>
      {open && (
        <div className="reasoning__body" aria-live={running ? "polite" : "off"}>
          <pre>{text}</pre>
          {running && <span className="stream-caret" aria-hidden="true" />}
        </div>
      )}
    </section>
  );
}
