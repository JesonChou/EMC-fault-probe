import { Check, PanelLeft, PanelLeftClose, PanelRight, PanelRightClose } from "lucide-react";

type TopBarProps = {
  title: string;
  workspaceName: string;
  connected: boolean;
  sidebarCollapsed: boolean;
  workspaceOpen: boolean;
  onToggleSidebar: () => void;
  onToggleWorkspace: () => void;
};

export function TopBar({ title, workspaceName, connected, sidebarCollapsed, workspaceOpen, onToggleSidebar, onToggleWorkspace }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar__leading">
        <button className="icon-button" type="button" onClick={onToggleSidebar} aria-label={sidebarCollapsed ? "展开会话侧栏" : "折叠会话侧栏"} title={`${sidebarCollapsed ? "展开" : "折叠"}会话侧栏 (Ctrl+B)`}>
          {sidebarCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
        <div className="topbar__copy">
          <strong>{title}</strong>
          <span>EMC Agent · {workspaceName}</span>
        </div>
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
