import { ChevronDown, ChevronRight, File, FileCode2, Folder, FolderSearch2, GitBranch, LoaderCircle, MoreHorizontal, Search, X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type { WorkspaceEntry, WorkspaceInfo } from "../lib/api";

function FileRow({ entry, depth = 0 }: { entry: WorkspaceEntry; depth?: number }) {
  const Icon = entry.kind === "directory" ? Folder : entry.name.endsWith(".md") ? File : FileCode2;
  return (
    <>
      <button type="button" className="file-row" style={{ paddingLeft: `${12 + depth * 16}px` }} title={entry.path}>
        {entry.kind === "directory" ? <ChevronDown size={12} /> : <span className="file-row__spacer" />}
        <Icon size={14} /><span>{entry.name}</span>
      </button>
      {entry.children.map((child) => <FileRow key={child.path} entry={child} depth={depth + 1} />)}
    </>
  );
}

function filterEntries(entries: WorkspaceEntry[], query: string): WorkspaceEntry[] {
  if (!query) return entries;
  const normalized = query.toLocaleLowerCase();
  return entries.flatMap((entry) => {
    const children = filterEntries(entry.children, query);
    return entry.name.toLocaleLowerCase().includes(normalized) || children.length ? [{ ...entry, children }] : [];
  });
}

type WorkspacePanelProps = {
  workspace: WorkspaceInfo;
  workspaces: WorkspaceInfo[];
  files: WorkspaceEntry[];
  loading: boolean;
  picking: boolean;
  onSelect: (path: string) => Promise<void> | void;
  onBrowse: () => Promise<boolean>;
  onClose: () => void;
};

export function WorkspacePanel({ workspace, workspaces, files, loading, picking, onSelect, onBrowse, onClose }: WorkspacePanelProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [path, setPath] = useState(workspace.path);
  const [query, setQuery] = useState("");
  const visibleFiles = useMemo(() => filterEntries(files, query.trim()), [files, query]);

  const select = async (event: FormEvent) => {
    event.preventDefault();
    if (!path.trim()) return;
    await onSelect(path.trim());
    setPickerOpen(false);
  };

  const browse = async () => {
    if (await onBrowse()) setPickerOpen(false);
  };

  return (
    <aside className="workspace-panel" aria-label="工作区">
      <header className="workspace-panel__header">
        <div><strong>工作区</strong><span>{workspace.name}</span></div>
        <div><button className="icon-button" type="button" aria-label="更多操作"><MoreHorizontal size={16} /></button><button className="icon-button" type="button" onClick={onClose} aria-label="关闭工作区"><X size={15} /></button></div>
      </header>
      <div className="workspace-picker-wrap">
        <button type="button" className="workspace-picker" onClick={() => { setPath(workspace.path); setPickerOpen(!pickerOpen); }} aria-expanded={pickerOpen}>
          <Folder size={15} /><span><strong>{workspace.name}</strong><small>{workspace.path}</small></span><ChevronRight size={14} />
        </button>
        {pickerOpen && (
          <form className="workspace-popover" onSubmit={select}>
            <button type="button" className="workspace-popover__browse" disabled={picking} onClick={() => { void browse(); }}>
              {picking ? <LoaderCircle className="workspace-popover__spinner" size={14} /> : <FolderSearch2 size={14} />}
              <span><strong>{picking ? "等待系统选择…" : "浏览本机文件夹"}</strong><small>打开系统目录选择器</small></span>
            </button>
            <div className="workspace-popover__divider"><span>或输入路径</span></div>
            <label>工作区绝对路径</label>
            <div><input aria-label="工作区绝对路径" value={path} onChange={(event) => setPath(event.target.value)} /><button type="submit">打开</button></div>
            {workspaces.map((item) => <button key={item.path} type="button" className="workspace-popover__recent" onClick={() => { setPath(item.path); void onSelect(item.path); setPickerOpen(false); }}><Folder size={12} /><span><strong>{item.name}</strong><small>{item.path}</small></span></button>)}
          </form>
        )}
      </div>
      <label className="workspace-search"><Search size={14} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="筛选文件…" /></label>
      <div className="workspace-panel__tabs"><button type="button" className="workspace-panel__tab workspace-panel__tab--active">文件</button><button type="button" className="workspace-panel__tab">改动 <span>0</span></button></div>
      <div className="file-tree">
        {loading && <div className="file-tree__empty">正在读取工作区…</div>}
        {!loading && visibleFiles.map((entry) => <FileRow key={entry.path} entry={entry} />)}
        {!loading && visibleFiles.length === 0 && <div className="file-tree__empty">没有匹配的文件</div>}
      </div>
      <footer className="workspace-panel__footer"><span><GitBranch size={13} /> local</span><span>{files.length} 个顶层项目</span></footer>
    </aside>
  );
}
