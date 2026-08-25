import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "./Composer";
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

  it("exposes the native directory picker as the primary workspace action", async () => {
    const browse = vi.fn().mockResolvedValue(true);
    render(
      <WorkspacePanel workspace={workspace} workspaces={[workspace]} files={[]} loading={false} picking={false} onSelect={vi.fn()} onBrowse={browse} onClose={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /EMC-fault-probe D:/ }));
    fireEvent.click(screen.getByRole("button", { name: /浏览本机文件夹/ }));
    await waitFor(() => expect(browse).toHaveBeenCalledOnce());
  });
});
