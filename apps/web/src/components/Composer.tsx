import { ArrowUp, Brain, ChevronDown, FolderOpen, Gauge, Plus } from "lucide-react";
import { FormEvent, KeyboardEvent, useRef, useState } from "react";

type ComposerProps = {
  value: string;
  model: string;
  workspace: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
};

export function Composer({ value, model, workspace, onChange, onSubmit }: ComposerProps) {
  const [focused, setFocused] = useState(false);
  const composing = useRef(false);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const next = value.trim();
    if (next) onSubmit(next);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !composing.current) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form className={`composer-shell${focused ? " composer-shell--focused" : ""}`} onSubmit={submit}>
      <div className="composer-shell__input-row">
        <span className="composer-shell__caret">›</span>
        <textarea
          aria-label="发送消息"
          rows={2}
          value={value}
          placeholder="给 EMC Agent 发送消息…  / 命令 · @ 工作区"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          onCompositionStart={() => { composing.current = true; }}
          onCompositionEnd={() => { composing.current = false; }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        <button className="composer-shell__send" type="submit" disabled={!value.trim()} aria-label="发送">
          <ArrowUp size={17} />
        </button>
      </div>
      <div className="composer-shell__controls">
        <button type="button" className="composer-control composer-control--square" aria-label="添加上下文">
          <Plus size={15} />
        </button>
        <button type="button" className="composer-control">
          <FolderOpen size={13} />
          <span>{workspace}</span>
          <ChevronDown size={11} />
        </button>
        <span className="composer-shell__divider" />
        <button type="button" className="composer-control">
          <Brain size={13} />
          <span>{model}</span>
          <ChevronDown size={11} />
        </button>
        <button type="button" className="composer-control composer-control--quiet">
          <Gauge size={13} />
          <span>思考</span>
        </button>
        <span className="composer-shell__shortcut">Enter 发送</span>
      </div>
    </form>
  );
}
