import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("Reasonix-inspired workbench foundation", () => {
  it("renders the three primary workbench regions", () => {
    render(<App />);

    expect(screen.getByRole("complementary", { name: "会话导航" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "工作区列表" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建工作区" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "在 EMC-fault-probe 中新建会话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今天想解决什么 EMC 问题？" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "工作区" })).toBeInTheDocument();
    expect(screen.getByRole("separator", { name: "调整会话侧栏宽度" })).toHaveAttribute("aria-valuenow", "264");
    expect(screen.getByRole("separator", { name: "调整工作区侧栏宽度" })).toHaveAttribute("aria-valuenow", "356");
  });

  it("supports continuous keyboard resizing and persists panel widths", () => {
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1440 });
    render(<App />);

    const sidebarHandle = screen.getByRole("separator", { name: "调整会话侧栏宽度" });
    fireEvent.keyDown(sidebarHandle, { key: "ArrowRight", shiftKey: true });
    expect(sidebarHandle).toHaveAttribute("aria-valuenow", "265");
    expect(window.localStorage.getItem("emc.ui.sidebarWidth")).toBe("265");

    const workspaceHandle = screen.getByRole("separator", { name: "调整工作区侧栏宽度" });
    fireEvent.keyDown(workspaceHandle, { key: "ArrowLeft", shiftKey: true });
    expect(workspaceHandle).toHaveAttribute("aria-valuenow", "357");
    expect(window.localStorage.getItem("emc.ui.workspaceWidth")).toBe("357");
    Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth });
  });

  it("places a suggestion in the composer and can close the workspace", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /200 MHz/ }));
    expect(screen.getByRole("textbox", { name: "发送消息" })).toHaveValue(
      "200 MHz 附近超标，应该从哪里开始排查？",
    );

    fireEvent.click(screen.getByRole("button", { name: "关闭工作区" }));
    expect(screen.queryByRole("complementary", { name: "工作区" })).not.toBeInTheDocument();
  });

  it("uses light mode by default and makes sidebar settings functional", () => {
    render(<App />);

    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    fireEvent.click(screen.getByRole("button", { name: "打开设置" }));
    expect(screen.getByRole("dialog", { name: "设置" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: /深色/ }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("emc.ui.theme")).toBe("dark");

    fireEvent.click(screen.getByRole("button", { name: "关闭设置" }));
    const sidebarToggle = screen.getByRole("button", { name: "折叠会话侧栏" });
    expect(sidebarToggle.closest("header")).toHaveClass("topbar");
    fireEvent.click(sidebarToggle);
    expect(screen.getByRole("button", { name: "展开会话侧栏" })).toBeInTheDocument();
  });
});
