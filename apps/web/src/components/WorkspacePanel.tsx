import {
  ChevronDown,
  ChevronRight,
  File,
  FileCode2,
  Folder,
  GitBranch,
  MoreHorizontal,
  Search,
  X,
} from "lucide-react";
import type { WorkspaceFile, WorkspaceSummary } from "../types/ui";

function FileRow({ entry, depth = 0 }: { entry: WorkspaceFile; depth?: number }) {
  const Icon = entry.kind === "directory" ? Folder : entry.name.endsWith(".md") ? File : FileCode2;
  return (
    <>
      <button
        type="button"
        className={`file-row${entry.active ? " file-row--active" : ""}`}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
      >
        {entry.kind === "directory" ? <ChevronDown size={12} /> : <span className="file-row__spacer" />}
        <Icon size={14} />
        <span>{entry.name}</span>
      </button>
      {entry.children?.map((child) => <FileRow key={child.name} entry={child} depth={depth + 1} />)}
    </>
  );
}

export function WorkspacePanel({ workspace, onClose }: { workspace: WorkspaceSummary; onClose: () => void }) {
  return (
    <aside className="workspace-panel" aria-label="工作区">
      <header className="workspace-panel__header">
        <div>
          <strong>工作区</strong>
          <span>{workspace.name}</span>
        </div>
        <div>
          <button className="icon-button" type="button" aria-label="更多操作"><MoreHorizontal size={16} /></button>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭工作区"><X size={15} /></button>
        </div>
      </header>
      <button type="button" className="workspace-picker">
        <Folder size={15} />
        <span>
          <strong>{workspace.name}</strong>
          <small>{workspace.path}</small>
        </span>
        <ChevronRight size={14} />
      </button>
      <label className="workspace-search">
        <Search size={14} />
        <input type="search" placeholder="筛选文件…" />
      </label>
      <div className="workspace-panel__tabs">
        <button type="button" className="workspace-panel__tab workspace-panel__tab--active">文件</button>
        <button type="button" className="workspace-panel__tab">改动 <span>0</span></button>
      </div>
      <div className="file-tree">
        {workspace.files.map((entry) => <FileRow key={entry.name} entry={entry} />)}
      </div>
      <footer className="workspace-panel__footer">
        <span><GitBranch size={13} /> {workspace.branch ?? "main"}</span>
        <span>5 个顶层项目</span>
      </footer>
    </aside>
  );
}
