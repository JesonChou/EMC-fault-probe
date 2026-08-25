import { useState } from "react";
import { Composer } from "../components/Composer";
import { Sidebar } from "../components/Sidebar";
import { TopBar } from "../components/TopBar";
import { Welcome } from "../components/Welcome";
import { WorkspacePanel } from "../components/WorkspacePanel";
import { previewSessions, previewWorkspace } from "../demo";

export function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [workspaceOpen, setWorkspaceOpen] = useState(true);
  const [draft, setDraft] = useState("");

  const usePrompt = (prompt: string) => setDraft(prompt);
  const submit = (prompt: string) => {
    setDraft("");
    // The foundation branch owns the interaction shell. The integration branch
    // connects this boundary to the real SSE session controller.
    window.dispatchEvent(new CustomEvent("emc:submit-preview", { detail: prompt }));
  };

  return (
    <main
      className={`app-shell${sidebarCollapsed ? " app-shell--sidebar-collapsed" : ""}${workspaceOpen ? " app-shell--workspace-open" : ""}`}
    >
      <Sidebar
        sessions={previewSessions}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((value) => !value)}
        onNewSession={() => setDraft("")}
      />
      <section className="chat-pane">
        <TopBar
          title="辐射发射超标排查"
          workspaceName={previewWorkspace.name}
          workspaceOpen={workspaceOpen}
          onToggleWorkspace={() => setWorkspaceOpen((value) => !value)}
        />
        <div className="chat-pane__content">
          <Welcome onSuggestion={usePrompt} />
        </div>
        <div className="composer-dock">
          <Composer
            value={draft}
            model="qwen3.5:9b-q4_K_M"
            workspace={previewWorkspace.name}
            onChange={setDraft}
            onSubmit={submit}
          />
          <div className="statusbar">
            <span><i /> Ollama · 本地</span>
            <span>RAG 已就绪</span>
            <span>0% 上下文</span>
            <span>{previewWorkspace.name}</span>
          </div>
        </div>
      </section>
      {workspaceOpen && <WorkspacePanel workspace={previewWorkspace} onClose={() => setWorkspaceOpen(false)} />}
    </main>
  );
}
