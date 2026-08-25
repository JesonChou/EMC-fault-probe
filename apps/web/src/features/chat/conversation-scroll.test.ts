import { describe, expect, it } from "vitest";
import { distanceFromBottom, isNearBottom, parseScrollPositions, restoredScrollTop } from "./conversation-scroll.ts";

describe("conversation scroll policy", () => {
  it("uses the same 24px near-bottom threshold as Codex", () => {
    expect(isNearBottom({ scrollHeight: 1000, clientHeight: 400, scrollTop: 576 })).toBe(true);
    expect(isNearBottom({ scrollHeight: 1000, clientHeight: 400, scrollTop: 575 })).toBe(false);
  });

  it("measures position from the bottom without returning negatives", () => {
    expect(distanceFromBottom({ scrollHeight: 1000, clientHeight: 400, scrollTop: 250 })).toBe(350);
    expect(distanceFromBottom({ scrollHeight: 200, clientHeight: 400, scrollTop: 0 })).toBe(0);
  });

  it("ignores corrupt session scroll state", () => {
    expect(parseScrollPositions("not json")).toEqual({});
    expect(parseScrollPositions(null)).toEqual({});
  });

  it("restores a session by its distance from the bottom after layout changes", () => {
    expect(restoredScrollTop({ scrollTop: 1200, distanceFromBottom: 180, following: false }, 980)).toBe(800);
    expect(restoredScrollTop({ scrollTop: 1200, distanceFromBottom: 0, following: true }, 980)).toBe(980);
  });
});
