import { useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "../components/Composer";
import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";
import { Welcome } from "../components/Welcome";
import { WorkspacePanel } from "../components/WorkspacePanel";
import { previewSessions, previewWorkspace } from "../demo";
import { chatApi } from "../features/chat/chat-api.ts";
import { applyAgentEvent, beginTurn, emptyChatState, setReasoningOpen } from "../features/chat/chat-state.ts";
import { Transcript } from "../features/chat/Transcript.tsx";
import type { AgentEvent, ChatState } from "../features/chat/types.ts";
import { api } from "../lib/api";
import type { SessionResponse, SessionSummaryResponse, WorkspaceEntry, WorkspaceInfo } from "../lib/api";
import type { SessionSummary, WorkspaceFile } from "../types/ui";

const fallbackWorkspace: WorkspaceInfo = { name: previewWorkspace.name, path: previewWorkspace.path, current: true };

function fallbackEntry(entry: WorkspaceFile, parent: string): WorkspaceEntry {
  const path = `${parent}/${entry.name}`;
  return { name: entry.name, path, kind: entry.kind, children: (entry.children ?? []).map((child) => fallbackEntry(child, path)) };
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

function previewChat(): ChatState {
  if (!new URLSearchParams(window.location.search).has("preview")) return emptyChatState();
  return {
    sessionId: "preview",
    running: false,
    step: 3,
    messages: [
      { id: "preview-user", role: "user", content: "200 MHz 附近辐射发射超标，应该从哪里开始排查？" },
      {
        id: "preview-assistant",
        role: "assistant",
        content: "建议先确认 200 MHz 是否与板上时钟的整数倍对应，再沿着时钟源、走线回流和外接线缆三条路径排查。\n\n1. 用近场探头定位主辐射区域。\n2. 对可疑时钟做频率微调，观察峰值是否同步移动。\n3. 检查连接器附近的共模电流和机壳搭接。",
        reasoning: "先识别频点与已知时钟的倍频关系。200 MHz 常见于 25 MHz、40 MHz、50 MHz 或 100 MHz 时钟的谐波。接下来需要把空间辐射与传导路径区分开，并利用频率微调建立因果关系。若峰值随时钟移动，优先检查回流不连续与边沿过快；若不移动，则检查 DC/DC、外部环境和测量布置。",
        reasoningOpen: true,
        reasoningComplete: true,
        tools: [{ id: "preview-tool", name: "search_emc_cases", arguments: { frequency_mhz: 200 }, status: "completed", output: "找到 12 个相关案例" }],
        status: "completed",
      },
    ],
  };
}

export function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [workspaceOpen, setWorkspaceOpen] = useState(true);
  const [draft, setDraft] = useState("");
  const [chat, setChat] = useState<ChatState>(previewChat);
  const [sessions, setSessions] = useState<SessionSummary[]>(previewSessions);
  const [workspace, setWorkspace] = useState<WorkspaceInfo>(fallbackWorkspace);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([fallbackWorkspace]);
  const [files, setFiles] = useState<WorkspaceEntry[]>(previewWorkspace.files.map((entry) => fallbackEntry(entry, previewWorkspace.path)));
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspacePicking, setWorkspacePicking] = useState(false);
  const [models, setModels] = useState(["qwen3.5:9b-q4_K_M"]);
  const [model, setModel] = useState("qwen3.5:9b-q4_K_M");
  const [think, setThink] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const activeTitle = useMemo(() => sessions.find((item) => item.id === chat.sessionId)?.title ?? "新会话", [chat.sessionId, sessions]);

  const refreshSessions = async () => {
    const values = await chatApi.listSessions<SessionSummaryResponse[]>();
    setSessions(values.map((item) => ({ id: item.session_id, title: item.title, updatedAt: formatUpdatedAt(item.updated_at), turns: item.turns })));
  };

  const refreshTree = async () => {
    setWorkspaceLoading(true);
    try { setFiles(await api.workspaceTree()); } finally { setWorkspaceLoading(false); }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      const [healthResult, modelResult, workspaceResult, sessionResult] = await Promise.allSettled([
        api.health(), api.models(), api.workspaces(), chatApi.listSessions<SessionSummaryResponse[]>(),
      ]);
      if (!active) return;
      if (healthResult.status === "fulfilled") setConnected(healthResult.value.ollama.available && healthResult.value.ollama.chat_model_installed);
      if (modelResult.status === "fulfilled") {
        const candidates = modelResult.value.chat_candidates.length ? modelResult.value.chat_candidates : [modelResult.value.default_chat_model];
        setModels(candidates);
        setModel(candidates.includes(modelResult.value.default_chat_model) ? modelResult.value.default_chat_model : candidates[0]);
      }
      if (workspaceResult.status === "fulfilled") {
        setWorkspace(workspaceResult.value.current);
        setWorkspaces(workspaceResult.value.items);
        try { await refreshTree(); } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : String(reason)); }
      }
      if (sessionResult.status === "fulfilled") setSessions(sessionResult.value.map((item) => ({ id: item.session_id, title: item.title, updatedAt: formatUpdatedAt(item.updated_at), turns: item.turns })));
      if ([healthResult, modelResult, workspaceResult, sessionResult].every((result) => result.status === "rejected")) setError("后端尚未连接；当前保留界面预览，启动 FastAPI 后会自动接入本地 Agent。");
    })();
    return () => { active = false; abortRef.current?.abort(); };
  }, []);

  useEffect(() => {
    const viewport = scrollRef.current;
    if (viewport) viewport.scrollTop = viewport.scrollHeight;
  }, [chat.messages, chat.running]);

  useEffect(() => {
    const newSession = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "n") { event.preventDefault(); setChat(emptyChatState()); setDraft(""); }
    };
    window.addEventListener("keydown", newSession);
    return () => window.removeEventListener("keydown", newSession);
  }, []);

  const selectWorkspace = async (path: string) => {
    setError(null);
    try {
      const selected = await api.selectWorkspace(path);
      setWorkspace(selected);
      setWorkspaces((current) => [selected, ...current.filter((item) => item.path !== selected.path)]);
      await refreshTree();
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };

  const browseWorkspace = async (): Promise<boolean> => {
    setError(null);
    setWorkspacePicking(true);
    try {
      const selected = await api.pickWorkspace();
      if (!selected) return false;
      setWorkspace(selected);
      setWorkspaces((current) => [selected, ...current.filter((item) => item.path !== selected.path)]);
      await refreshTree();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      return false;
    } finally { setWorkspacePicking(false); }
  };

  const loadSession = async (sessionId: string) => {
    if (chat.running) return;
    setError(null);
    try {
      const session = await chatApi.getSession<SessionResponse>(sessionId);
      setChat({
        sessionId,
        running: false,
        step: session.messages.length,
        messages: session.messages.filter((message) => message.role !== "system").map((message) => ({
          id: message.message_id,
          role: message.role as "user" | "assistant",
          content: message.content,
          reasoning: message.thinking ?? undefined,
          reasoningComplete: Boolean(message.thinking),
          reasoningOpen: false,
          status: "completed",
        })),
      });
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };

  const submit = async (prompt: string) => {
    if (chat.running) return;
    setDraft("");
    setError(null);
    let sessionId = chat.sessionId;
    try {
      if (!sessionId || sessionId === "preview") {
        const created = await chatApi.createSession<SessionResponse>();
        sessionId = created.session_id;
      }
      const activeSessionId = sessionId;
      setChat((current) => beginTurn({ ...current, sessionId: activeSessionId }, prompt));
      const controller = new AbortController();
      abortRef.current = controller;
      for await (const event of chatApi.send(activeSessionId, prompt, { model, think, workspace_path: workspace.path }, controller.signal)) {
        setChat((current) => applyAgentEvent(current, event));
      }
      await refreshSessions();
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        const message = reason instanceof Error ? reason.message : String(reason);
        setError(message);
        if (sessionId) {
          const failed: AgentEvent = { type: "turn.failed", session_id: sessionId, step: chat.step + 1, data: { reason: message } };
          setChat((current) => applyAgentEvent(current, failed));
        }
      }
    } finally { abortRef.current = null; }
  };

  const stop = () => {
    abortRef.current?.abort();
    if (chat.sessionId && chat.sessionId !== "preview") void chatApi.cancel(chat.sessionId).catch(() => undefined);
    if (chat.sessionId) setChat((current) => applyAgentEvent(current, { type: "turn.failed", session_id: chat.sessionId ?? "", step: current.step + 1, data: { reason: "cancelled" } }));
  };

  return (
    <main className={`app-shell${sidebarCollapsed ? " app-shell--sidebar-collapsed" : ""}${workspaceOpen ? " app-shell--workspace-open" : ""}`}>
      <Sidebar sessions={sessions} activeSessionId={chat.sessionId} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} onNewSession={() => { setChat(emptyChatState()); setDraft(""); }} onSelectSession={(sessionId) => { void loadSession(sessionId); }} />
      <section className="chat-pane">
        <TopBar title={activeTitle} workspaceName={workspace.name} connected={connected} workspaceOpen={workspaceOpen} onToggleWorkspace={() => setWorkspaceOpen((value) => !value)} />
        <div className="chat-pane__content" ref={scrollRef}>
          {error && <div className="connection-banner" role="status"><span>{error}</span><button type="button" onClick={() => setError(null)}>关闭</button></div>}
          {chat.messages.length === 0 ? <Welcome onSuggestion={setDraft} /> : <Transcript messages={chat.messages} onReasoningToggle={(messageId, open) => setChat((current) => setReasoningOpen(current, messageId, open))} />}
        </div>
        <div className="composer-dock">
          <Composer value={draft} model={model} models={models} workspace={workspace} workspaces={workspaces} think={think} running={chat.running} onChange={setDraft} onModelChange={setModel} onWorkspaceChange={(path) => { void selectWorkspace(path); }} onThinkChange={setThink} onSubmit={(value) => { void submit(value); }} onStop={stop} />
          <div className="statusbar"><span><i className={connected ? "" : "statusbar__offline"} /> {connected ? "Ollama · 本地" : "Ollama · 离线"}</span><span>RAG 已就绪</span><span>{chat.messages.length} 条消息</span><span>{workspace.name}</span></div>
        </div>
      </section>
      {workspaceOpen && <WorkspacePanel workspace={workspace} workspaces={workspaces} files={files} loading={workspaceLoading} picking={workspacePicking} onSelect={selectWorkspace} onBrowse={browseWorkspace} onClose={() => setWorkspaceOpen(false)} />}
    </main>
  );
}
