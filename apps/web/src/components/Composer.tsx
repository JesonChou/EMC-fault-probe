import { ArrowUp, Brain, Check, ChevronDown, FolderOpen, Gauge, Plus, Square } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import type { WorkspaceInfo } from "../lib/api";

type ComposerProps = {
  value: string;
  model: string;
  models: string[];
  workspace: WorkspaceInfo;
  workspaces: WorkspaceInfo[];
  think: boolean;
  running: boolean;
  onChange: (value: string) => void;
  onModelChange: (model: string) => void;
  onWorkspaceChange: (path: string) => void;
  onThinkChange: (enabled: boolean) => void;
  onSubmit: (value: string) => void;
  onStop: () => void;
};

export function Composer({ value, model, models, workspace, workspaces, think, running, onChange, onModelChange, onWorkspaceChange, onThinkChange, onSubmit, onStop }: ComposerProps) {
  const [focused, setFocused] = useState(false);
  const [menu, setMenu] = useState<"model" | "workspace" | null>(null);
  const composing = useRef(false);
  const addContextRef = useRef<HTMLButtonElement | null>(null);
  const workspaceMenuRef = useRef<HTMLDivElement | null>(null);
  const modelMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menu) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      const activeBoundary = menu === "workspace" ? workspaceMenuRef.current : modelMenuRef.current;
      if (activeBoundary?.contains(target)) return;
      if (menu === "workspace" && addContextRef.current?.contains(target)) return;
      setMenu(null);
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setMenu(null);
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menu]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const next = value.trim();
    if (next && !running) onSubmit(next);
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
        <textarea aria-label="发送消息" rows={3} value={value} placeholder="向 EMC Agent 提问…" onChange={(event) => onChange(event.target.value)} onKeyDown={onKeyDown} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} />
      </div>
      <div className="composer-shell__controls">
        <button ref={addContextRef} type="button" className="composer-control composer-control--square" aria-label="添加工作区上下文" aria-haspopup="menu" aria-expanded={menu === "workspace"} onClick={() => setMenu(menu === "workspace" ? null : "workspace")}><Plus size={16} /></button>
        <div ref={workspaceMenuRef} className="composer-menu-anchor">
          <button type="button" className="composer-control" aria-haspopup="menu" aria-expanded={menu === "workspace"} onClick={() => setMenu(menu === "workspace" ? null : "workspace")}><FolderOpen size={13} /><span>{workspace.name}</span><ChevronDown size={11} /></button>
          {menu === "workspace" && (
            <div className="composer-menu" role="menu" aria-label="选择工作区">
              <div className="composer-menu__label">最近工作区</div>
              {workspaces.map((item) => (
                <button key={item.path} type="button" role="menuitem" onClick={() => { onWorkspaceChange(item.path); setMenu(null); }}><FolderOpen size={13} /><span><strong>{item.name}</strong><small>{item.path}</small></span>{item.path === workspace.path && <Check size={12} />}</button>
              ))}
            </div>
          )}
        </div>
        <span className="composer-shell__divider" />
        <div ref={modelMenuRef} className="composer-menu-anchor">
          <button type="button" className="composer-control" aria-haspopup="menu" aria-expanded={menu === "model"} onClick={() => setMenu(menu === "model" ? null : "model")}><Brain size={13} /><span>{model}</span><ChevronDown size={11} /></button>
          {menu === "model" && (
            <div className="composer-menu composer-menu--model" role="menu" aria-label="选择模型">
              <div className="composer-menu__label">本地 Ollama 模型</div>
              {models.length === 0 && <div className="composer-menu__empty">未检测到可用模型</div>}
              {models.map((item) => (
                <button key={item} type="button" role="menuitem" onClick={() => { onModelChange(item); setMenu(null); }}><Brain size={13} /><span><strong>{item}</strong><small>本地推理</small></span>{item === model && <Check size={12} />}</button>
              ))}
            </div>
          )}
        </div>
        <button type="button" aria-pressed={think} className={`composer-control composer-control--quiet${think ? " composer-control--active" : ""}`} onClick={() => onThinkChange(!think)}><Gauge size={13} /><span>{think ? "深度思考" : "快速回答"}</span></button>
        <span className="composer-shell__shortcut">{running ? "生成中" : "Enter 发送"}</span>
        {running ? (
          <button className="composer-shell__send composer-shell__send--stop" type="button" onClick={onStop} aria-label="停止生成"><Square size={12} fill="currentColor" /></button>
        ) : (
          <button className="composer-shell__send" type="submit" disabled={!value.trim()} aria-label="发送"><ArrowUp size={17} /></button>
        )}
      </div>
    </form>
  );
}
