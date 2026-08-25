import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, UIEvent, WheelEvent } from "react";

export const NEAR_BOTTOM_PX = 24;
const STORAGE_KEY = "emc.ui.conversationScroll.v1";

export type ScrollSnapshot = {
  scrollTop: number;
  distanceFromBottom: number;
  following: boolean;
};

type ScrollPositionMap = Record<string, ScrollSnapshot>;

export function distanceFromBottom(element: Pick<HTMLElement, "scrollHeight" | "clientHeight" | "scrollTop">): number {
  return Math.max(0, element.scrollHeight - element.clientHeight - element.scrollTop);
}

export function isNearBottom(element: Pick<HTMLElement, "scrollHeight" | "clientHeight" | "scrollTop">, threshold = NEAR_BOTTOM_PX): boolean {
  return distanceFromBottom(element) <= threshold;
}

export function parseScrollPositions(value: string | null): ScrollPositionMap {
  if (!value) return {};
  try {
    const parsed = JSON.parse(value) as ScrollPositionMap;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function restoredScrollTop(snapshot: ScrollSnapshot, maxScrollTop: number): number {
  return snapshot.following ? maxScrollTop : Math.max(0, maxScrollTop - snapshot.distanceFromBottom);
}

function loadPositions(): ScrollPositionMap {
  if (typeof window === "undefined") return {};
  return parseScrollPositions(window.sessionStorage.getItem(STORAGE_KEY));
}

function savePositions(positions: ScrollPositionMap) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(positions));
}

function positionKey(sessionId: string | null): string {
  return sessionId ?? "__new__";
}

type ConversationScrollOptions = {
  sessionId: string | null;
  contentVersion: string;
  hasMessages: boolean;
};

/**
 * Codex-style scroll following for a normal top-to-bottom transcript.
 * Streaming follows only while the reader remains near the bottom; moving away
 * pauses following, and every session keeps its own viewport position.
 */
export function useConversationScroll({ sessionId, contentVersion, hasMessages }: ConversationScrollOptions) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const positionsRef = useRef<ScrollPositionMap>(loadPositions());
  const activeKeyRef = useRef(positionKey(sessionId));
  const followingRef = useRef(true);
  const userIntentRef = useRef(false);
  const intentTimerRef = useRef<number | null>(null);
  const [atBottom, setAtBottom] = useState(true);

  const persist = useCallback((element: HTMLElement, following = followingRef.current) => {
    positionsRef.current[activeKeyRef.current] = {
      scrollTop: element.scrollTop,
      distanceFromBottom: distanceFromBottom(element),
      following,
    };
    savePositions(positionsRef.current);
  }, []);

  const setFollowing = useCallback((following: boolean) => {
    followingRef.current = following;
    setAtBottom(following);
  }, []);

  const jumpToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const element = viewportRef.current;
    if (!element) return;
    setFollowing(true);
    element.scrollTo({ top: element.scrollHeight, behavior });
    persist(element, true);
  }, [persist, setFollowing]);

  const markUserIntent = useCallback(() => {
    userIntentRef.current = true;
    if (intentTimerRef.current !== null) window.clearTimeout(intentTimerRef.current);
    intentTimerRef.current = window.setTimeout(() => {
      userIntentRef.current = false;
      intentTimerRef.current = null;
    }, 1000);
  }, []);

  const onWheel = useCallback((event: WheelEvent<HTMLDivElement>) => {
    markUserIntent();
    if (event.deltaY < 0) setFollowing(false);
  }, [markUserIntent, setFollowing]);

  const onPointerDown = useCallback((_event: ReactPointerEvent<HTMLDivElement>) => {
    markUserIntent();
  }, [markUserIntent]);

  const onKeyDown = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
    const scrollKeys = new Set(["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "]);
    if (!scrollKeys.has(event.key)) return;
    markUserIntent();
    if (["ArrowUp", "PageUp", "Home"].includes(event.key)) setFollowing(false);
  }, [markUserIntent, setFollowing]);

  const onScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    const element = event.currentTarget;
    const nearBottom = isNearBottom(element);
    if (userIntentRef.current) {
      setFollowing(nearBottom);
    } else if (nearBottom && !followingRef.current) {
      setFollowing(true);
    }
    persist(element, followingRef.current);
  }, [persist, setFollowing]);

  useLayoutEffect(() => {
    const element = viewportRef.current;
    if (!element) return;
    const nextKey = positionKey(sessionId);
    const changedSession = activeKeyRef.current !== nextKey;

    if (changedSession) {
      activeKeyRef.current = nextKey;
      userIntentRef.current = false;
      const saved = positionsRef.current[nextKey];
      const shouldFollow = saved?.following ?? true;
      followingRef.current = shouldFollow;
      const maxScrollTop = Math.max(0, element.scrollHeight - element.clientHeight);
      element.scrollTop = saved ? restoredScrollTop(saved, maxScrollTop) : element.scrollHeight;
      setAtBottom(shouldFollow || isNearBottom(element));
      persist(element, shouldFollow);
      return;
    }

    if (followingRef.current) {
      element.scrollTop = element.scrollHeight;
      setAtBottom(true);
      persist(element, true);
    }

    const frame = window.requestAnimationFrame(() => {
      if (!followingRef.current) return;
      element.scrollTop = element.scrollHeight;
      persist(element, true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [contentVersion, persist, sessionId]);

  useLayoutEffect(() => {
    const element = viewportRef.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    let frame = 0;
    const observer = new ResizeObserver(() => {
      if (!followingRef.current) {
        persist(element, false);
        return;
      }
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight;
        persist(element, true);
      });
    });
    observer.observe(element);
    for (const child of element.children) observer.observe(child);
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [persist]);

  useEffect(() => () => {
    if (intentTimerRef.current !== null) window.clearTimeout(intentTimerRef.current);
  }, []);

  return {
    viewportRef,
    atBottom: !hasMessages || atBottom,
    scrollToBottom: () => jumpToBottom("smooth"),
    viewportProps: {
      onScroll,
      onWheel,
      onPointerDown,
      onTouchStart: markUserIntent,
      onKeyDown,
      tabIndex: 0,
    },
  };
}
