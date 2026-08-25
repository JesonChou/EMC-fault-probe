import { Check, PanelRight, PanelRightClose } from "lucide-react";

type TopBarProps = {
  title: string;
  workspaceName: string;
  connected: boolean;
  workspaceOpen: boolean;
  onToggleWorkspace: () => void;
};

export function TopBar({ title, workspaceName, connected, workspaceOpen, onToggleWorkspace }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar__copy">
        <strong>{title}</strong>
        <span>EMC Agent · {workspaceName}</span>
      </div>
      <div className="topbar__actions">
        <span className={`status-pill${connected ? "" : " status-pill--offline"}`}>
          <span className="status-pill__dot" />
          {connected ? "Ollama 已连接" : "Ollama 未连接"}
          {connected && <Check size={12} />}
        </span>
        <button className="icon-button" type="button" onClick={onToggleWorkspace} aria-label="切换工作区面板">
          {workspaceOpen ? <PanelRightClose size={16} /> : <PanelRight size={16} />}
        </button>
      </div>
    </header>
  );
}
