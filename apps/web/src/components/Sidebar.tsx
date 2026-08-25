import {
  BookOpenText,
  ChevronsLeft,
  MessageSquare,
  Plus,
  Settings,
  Sparkles,
} from "lucide-react";
import type { SessionSummary } from "../types/ui";
import { BrandMark } from "./BrandMark";

type SidebarProps = {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
};

export function Sidebar({ sessions, activeSessionId, collapsed, onToggle, onNewSession, onSelectSession }: SidebarProps) {
  return (
    <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`} aria-label="会话导航">
      <div className="sidebar__brand">
        <BrandMark />
        <div className="sidebar__brand-copy">
          <strong>EMC Probe</strong>
          <span>local diagnostic agent</span>
        </div>
        <button className="icon-button sidebar__collapse" onClick={onToggle} aria-label="折叠侧栏">
          <ChevronsLeft size={15} />
        </button>
      </div>

      <button className="sidebar__new" onClick={onNewSession}>
        <Plus size={16} />
        <span>新建会话</span>
        <kbd>Ctrl N</kbd>
      </button>

      <div className="sidebar__section-head">
        <span>会话</span>
        <button type="button">全部</button>
      </div>
      <nav className="session-list" aria-label="最近会话">
        {sessions.map((session) => (
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
      </nav>

      <div className="sidebar__footer">
        <button className="sidebar__nav" type="button">
          <Sparkles size={15} />
          <span>Agent 能力</span>
        </button>
        <button className="sidebar__nav" type="button">
          <BookOpenText size={15} />
          <span>EMC 案例库</span>
          <small>151</small>
        </button>
        <button className="sidebar__nav" type="button">
          <Settings size={15} />
          <span>设置</span>
        </button>
      </div>
    </aside>
  );
}
