import {
  ChevronDown,
  ChevronRight,
  FolderOpen,
  FolderPlus,
  LoaderCircle,
  MessageSquare,
  Plus,
  Settings,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { WorkspaceInfo } from "../lib/api";
import type { SessionSummary } from "../types/ui";
import { BrandMark } from "./BrandMark";

type SidebarProps = {
  sessions: SessionSummary[];
  workspaces: WorkspaceInfo[];
  workspace: WorkspaceInfo;
  activeSessionId: string | null;
  collapsed: boolean;
  workspacePicking: boolean;
  onToggle: () => void;
  onNewSession: () => void;
  onNewWorkspace: () => void;
  onSelectWorkspace: (path: string) => void;
  onSelectSession: (sessionId: string) => void;
  onOpenSettings: () => void;
};

const SESSION_SCROLL_KEY = "emc.ui.sessionListScroll";
const COLLAPSED_WORKSPACE_SESSIONS_KEY = "emc.ui.collapsedWorkspaceSessions";

function readCollapsedWorkspaces(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const value = JSON.parse(window.localStorage.getItem(COLLAPSED_WORKSPACE_SESSIONS_KEY) ?? "[]");
    return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

export function Sidebar({ sessions, workspaces, workspace, activeSessionId, collapsed, workspacePicking, onToggle, onNewSession, onNewWorkspace, onSelectWorkspace, onSelectSession, onOpenSettings }: SidebarProps) {
  const sessionListRef = useRef<HTMLElement | null>(null);
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState(readCollapsedWorkspaces);
  const defaultWorkspacePath = workspaces[0]?.path.toLocaleLowerCase();
  const currentWorkspacePath = workspace.path.toLocaleLowerCase();
  const visibleSessions = sessions.filter((session) => session.workspacePath
    ? session.workspacePath.toLocaleLowerCase() === currentWorkspacePath
    : currentWorkspacePath === defaultWorkspacePath);
  const sessionScrollKey = `${SESSION_SCROLL_KEY}:${currentWorkspacePath}`;
  const sessionsExpanded = !collapsedWorkspaces.has(currentWorkspacePath);
  const displayedWorkspaces = collapsed ? workspaces.filter((item) => item.path === workspace.path) : workspaces;

  useEffect(() => {
    const list = sessionListRef.current;
    if (list) list.scrollTop = Number(window.sessionStorage.getItem(sessionScrollKey) ?? 0);
  }, [sessionScrollKey, sessionsExpanded]);

  useEffect(() => {
    window.localStorage.setItem(COLLAPSED_WORKSPACE_SESSIONS_KEY, JSON.stringify([...collapsedWorkspaces]));
  }, [collapsedWorkspaces]);

  const handleWorkspaceClick = (path: string) => {
    if (collapsed) {
      onToggle();
      return;
    }
    if (path !== workspace.path) {
      onSelectWorkspace(path);
      return;
    }
    const normalizedPath = path.toLocaleLowerCase();
    setCollapsedWorkspaces((current) => {
      const next = new Set(current);
      if (next.has(normalizedPath)) next.delete(normalizedPath);
      else next.add(normalizedPath);
      return next;
    });
  };

  return (
    <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`} aria-label="会话导航">
      <div className="sidebar__brand">
        <BrandMark />
        <div className="sidebar__brand-copy">
          <strong>EMC Probe</strong>
          <span>local diagnostic agent</span>
        </div>
      </div>

      <div className="sidebar__actions sidebar__actions--single">
        <button className="sidebar__action" onClick={onNewWorkspace} disabled={workspacePicking} aria-label="新建工作区" title="选择本机文件夹作为工作区">
          {workspacePicking ? <LoaderCircle className="sidebar__spinner" size={14} /> : <FolderPlus size={15} />}<span>{workspacePicking ? "选择中…" : "新建工作区"}</span>
        </button>
      </div>

      <div className="sidebar__section-head"><span>工作区</span></div>
      <section className="workspace-list" aria-label="工作区列表">
        {displayedWorkspaces.map((item) => (
          <div className={`workspace-group${item.path === workspace.path ? " workspace-group--active" : ""}${item.path === workspace.path && sessionsExpanded && !collapsed ? " workspace-group--expanded" : ""}`} key={item.path}>
            <div className={`workspace-row${item.path === workspace.path ? " workspace-row--active" : ""}`}>
              <button className="workspace-row__select" type="button" onClick={() => handleWorkspaceClick(item.path)} title={collapsed ? `展开 ${item.name}` : item.path} aria-label={collapsed ? `展开会话侧栏：${item.name}` : item.path === workspace.path ? `${sessionsExpanded ? "收起" : "展开"} ${item.name} 的会话` : `切换到工作区 ${item.name}`} aria-expanded={item.path === workspace.path && !collapsed ? sessionsExpanded : undefined}>
                <FolderOpen size={14} />
                <span><strong>{item.name}</strong><small>{item.path}</small></span>
                {item.path === workspace.path && !collapsed && (sessionsExpanded ? <ChevronDown className="workspace-row__disclosure" size={13} /> : <ChevronRight className="workspace-row__disclosure" size={13} />)}
              </button>
              {item.path === workspace.path && <button className="workspace-row__new-session" type="button" onClick={onNewSession} aria-label={`在 ${item.name} 中新建会话`} title="在当前工作区中新建会话 (Ctrl+N)"><Plus size={14} /></button>}
            </div>
            {item.path === workspace.path && sessionsExpanded && !collapsed && (
              <div className="workspace-sessions">
                <div className="workspace-sessions__heading"><span>会话</span><small>{visibleSessions.length}</small></div>
                <nav ref={sessionListRef} className="session-list" aria-label={`${item.name} 中的会话`} onScroll={(event) => window.sessionStorage.setItem(sessionScrollKey, String(event.currentTarget.scrollTop))}>
                  {visibleSessions.map((session) => (
                    <button
                      key={session.id}
                      className={`session-row${session.id === activeSessionId ? " session-row--active" : ""}`}
                      type="button"
                      onClick={() => onSelectSession(session.id)}
                    >
                      <MessageSquare size={14} />
                      <span className="session-row__copy">
                        <span className="session-row__title">{session.title}</span>
                        <span className="session-row__meta">{session.updatedAt}</span>
                      </span>
                      {session.id === activeSessionId && <span className="session-row__current">当前</span>}
                    </button>
                  ))}
                  {visibleSessions.length === 0 && <div className="session-list__empty">此工作区还没有会话</div>}
                </nav>
              </div>
            )}
          </div>
        ))}
      </section>

      <div className="sidebar__footer">
        <button className="sidebar__nav" type="button" onClick={onOpenSettings} aria-label="打开设置" title="设置">
          <Settings size={15} />
          <span>设置</span>
        </button>
      </div>
    </aside>
  );
}
