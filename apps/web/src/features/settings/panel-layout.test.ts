import { describe, expect, it } from "vitest";
import { clampPanelWidth } from "./panel-layout.ts";

describe("resizable panel layout", () => {
  it("clamps panel widths to their continuous desktop ranges", () => {
    expect(clampPanelWidth("sidebar", 180, 1440, 356)).toBe(210);
    expect(clampPanelWidth("sidebar", 338.4, 1440, 356)).toBe(338);
    expect(clampPanelWidth("workspace", 600, 1440, 264)).toBe(520);
  });

  it("always reserves the minimum center conversation width", () => {
    expect(clampPanelWidth("workspace", 520, 1100, 264)).toBe(356);
    expect(clampPanelWidth("sidebar", 420, 1000, 310)).toBe(210);
  });
});
