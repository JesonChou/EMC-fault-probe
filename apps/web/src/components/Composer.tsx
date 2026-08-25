import { ArrowUp, Brain, Check, ChevronDown, FolderOpen, Gauge, Plus, Square } from "lucide-react";
import { FormEvent, KeyboardEvent, useRef, useState } from "react";
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
        <span className="composer-shell__caret">›</span>
        <textarea aria-label="发送消息" rows={2} value={value} placeholder="给 EMC Agent 发送消息…  / 命令 · @ 工作区" onChange={(event) => onChange(event.target.value)} onKeyDown={onKeyDown} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} />
        {running ? (
          <button className="composer-shell__send composer-shell__send--stop" type="button" onClick={onStop} aria-label="停止生成"><Square size={12} fill="currentColor" /></button>
        ) : (
          <button className="composer-shell__send" type="submit" disabled={!value.trim()} aria-label="发送"><ArrowUp size={17} /></button>
        )}
      </div>
      <div className="composer-shell__controls">
        <button type="button" className="composer-control composer-control--square" aria-label="添加上下文"><Plus size={15} /></button>
        <div className="composer-menu-anchor">
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
        <div className="composer-menu-anchor">
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
      </div>
    </form>
  );
}
