import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "./Composer";
import { Sidebar } from "./Sidebar";
import { WorkspacePanel } from "./WorkspacePanel";

const workspace = { name: "EMC-fault-probe", path: "D:\\BUAA\\EMC-fault-probe", current: true };

describe("workbench controls", () => {
  it("submits with the send button and switches the selected model", () => {
    const submit = vi.fn();
    const changeModel = vi.fn();
    const { rerender } = render(
      <Composer value="诊断共模电流" model="qwen" models={["qwen", "deepseek"]} workspace={workspace} workspaces={[workspace]} think running={false} onChange={vi.fn()} onModelChange={changeModel} onWorkspaceChange={vi.fn()} onThinkChange={vi.fn()} onSubmit={submit} onStop={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    expect(submit).toHaveBeenCalledWith("诊断共模电流");
    fireEvent.click(screen.getByRole("button", { name: "qwen" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /deepseek/ }));
    expect(changeModel).toHaveBeenCalledWith("deepseek");

    rerender(
      <Composer value="" model="qwen" models={["qwen"]} workspace={workspace} workspaces={[workspace]} think running onChange={vi.fn()} onModelChange={vi.fn()} onWorkspaceChange={vi.fn()} onThinkChange={vi.fn()} onSubmit={submit} onStop={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "停止生成" })).toBeInTheDocument();
  });

  it("dismisses composer menus when clicking outside or pressing Escape", () => {
    render(
      <Composer value="" model="qwen" models={["qwen", "deepseek"]} workspace={workspace} workspaces={[workspace]} think running={false} onChange={vi.fn()} onModelChange={vi.fn()} onWorkspaceChange={vi.fn()} onThinkChange={vi.fn()} onSubmit={vi.fn()} onStop={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "qwen" }));
    expect(screen.getByRole("menu", { name: "选择模型" })).toBeInTheDocument();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("menu", { name: "选择模型" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "EMC-fault-probe" }));
    expect(screen.getByRole("menu", { name: "选择工作区" })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu", { name: "选择工作区" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "添加工作区上下文" }));
    expect(screen.getByRole("menu", { name: "选择工作区" })).toBeInTheDocument();
    fireEvent.pointerDown(screen.getByRole("textbox", { name: "发送消息" }));
    expect(screen.queryByRole("menu", { name: "选择工作区" })).not.toBeInTheDocument();
  });

  it("exposes the native directory picker as the primary workspace action", async () => {
    const browse = vi.fn().mockResolvedValue(true);
    render(
      <WorkspacePanel workspace={workspace} workspaces={[workspace]} files={[]} loading={false} picking={false} onSelect={vi.fn()} onBrowse={browse} onClose={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /EMC-fault-probe D:/ }));
    fireEvent.click(screen.getByRole("button", { name: /浏览本机文件夹/ }));
    await waitFor(() => expect(browse).toHaveBeenCalledOnce());
  });

  it("toggles the selected workspace sessions and reduces a collapsed sidebar to one folder", () => {
    const props = {
      sessions: [{ id: "session-1", title: "辐射发射排查", updatedAt: "刚刚", turns: 1, workspacePath: workspace.path }],
      workspaces: [workspace, { name: "other", path: "D:\\BUAA\\other", current: false }],
      workspace,
      activeSessionId: "session-1",
      workspacePicking: false,
      onToggle: vi.fn(),
      onNewSession: vi.fn(),
      onNewWorkspace: vi.fn(),
      onSelectWorkspace: vi.fn(),
      onSelectSession: vi.fn(),
      onOpenSettings: vi.fn(),
    };
    const { rerender } = render(<Sidebar {...props} collapsed={false} />);

    expect(screen.getByRole("navigation", { name: "EMC-fault-probe 中的会话" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "收起 EMC-fault-probe 的会话" }));
    expect(screen.queryByRole("navigation", { name: "EMC-fault-probe 中的会话" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开 EMC-fault-probe 的会话" })).toHaveAttribute("aria-expanded", "false");

    rerender(<Sidebar {...props} collapsed />);
    expect(screen.queryByRole("navigation", { name: "EMC-fault-probe 中的会话" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开会话侧栏：EMC-fault-probe" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "切换到工作区 other" })).not.toBeInTheDocument();
  });
});
