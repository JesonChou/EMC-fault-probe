import { Brain, Check, LayoutPanelLeft, Moon, Settings2, Sun, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ThemeMode } from "./ui-preferences.ts";

type SettingsDialogProps = {
  open: boolean;
  theme: ThemeMode;
  sidebarCollapsed: boolean;
  workspaceOpen: boolean;
  model: string;
  models: string[];
  think: boolean;
  onClose: () => void;
  onThemeChange: (theme: ThemeMode) => void;
  onSidebarCollapsedChange: (collapsed: boolean) => void;
  onWorkspaceOpenChange: (open: boolean) => void;
  onModelChange: (model: string) => void;
  onThinkChange: (enabled: boolean) => void;
};

export function SettingsDialog({ open, theme, sidebarCollapsed, workspaceOpen, model, models, think, onClose, onThemeChange, onSidebarCollapsedChange, onWorkspaceOpenChange, onModelChange, onThinkChange }: SettingsDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    window.requestAnimationFrame(() => dialogRef.current?.querySelector<HTMLElement>("button, input, select")?.focus());
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      previousFocus?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="settings-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
      <section ref={dialogRef} className="settings-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <header className="settings-dialog__header">
          <span><Settings2 size={17} /><strong id="settings-title">设置</strong></span>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭设置"><X size={16} /></button>
        </header>

        <div className="settings-dialog__body">
          <section className="settings-section" aria-labelledby="appearance-title">
            <div className="settings-section__heading"><Sun size={15} /><span><strong id="appearance-title">外观</strong><small>默认使用浅色主题，选择会保存在本机。</small></span></div>
            <div className="theme-options" role="radiogroup" aria-label="主题">
              <button type="button" role="radio" aria-checked={theme === "light"} className={theme === "light" ? "theme-option theme-option--active" : "theme-option"} onClick={() => onThemeChange("light")}><Sun size={16} /><span><strong>浅色</strong><small>清晰、适合日间使用</small></span>{theme === "light" && <Check size={15} />}</button>
              <button type="button" role="radio" aria-checked={theme === "dark"} className={theme === "dark" ? "theme-option theme-option--active" : "theme-option"} onClick={() => onThemeChange("dark")}><Moon size={16} /><span><strong>深色</strong><small>适合暗光环境</small></span>{theme === "dark" && <Check size={15} />}</button>
            </div>
          </section>

          <section className="settings-section" aria-labelledby="layout-title">
            <div className="settings-section__heading"><LayoutPanelLeft size={15} /><span><strong id="layout-title">工作台布局</strong><small>侧栏和工作区面板状态会自动记忆。</small></span></div>
            <label className="settings-row"><span><strong>折叠会话侧栏</strong><small>保留紧凑图标栏</small></span><input type="checkbox" checked={sidebarCollapsed} onChange={(event) => onSidebarCollapsedChange(event.target.checked)} /></label>
            <label className="settings-row"><span><strong>显示工作区面板</strong><small>在右侧展示目录与文件</small></span><input type="checkbox" checked={workspaceOpen} onChange={(event) => onWorkspaceOpenChange(event.target.checked)} /></label>
          </section>

          <section className="settings-section" aria-labelledby="agent-title">
            <div className="settings-section__heading"><Brain size={15} /><span><strong id="agent-title">Agent</strong><small>设置当前会话使用的本地推理模型。</small></span></div>
            <label className="settings-select"><span>默认模型</span><select aria-label="设置默认模型" value={model} onChange={(event) => onModelChange(event.target.value)}>{models.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="settings-row"><span><strong>深度思考</strong><small>呈现流式推理过程</small></span><input type="checkbox" checked={think} onChange={(event) => onThinkChange(event.target.checked)} /></label>
          </section>
        </div>
      </section>
    </div>
  );
}
