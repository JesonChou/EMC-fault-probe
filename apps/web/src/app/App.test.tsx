import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("Reasonix-inspired workbench foundation", () => {
  it("renders the three primary workbench regions", () => {
    render(<App />);

    expect(screen.getByRole("complementary", { name: "会话导航" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今天想解决什么 EMC 问题？" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "工作区" })).toBeInTheDocument();
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
});
