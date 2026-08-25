import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from "react";

export const panelDefaults = { sidebar: 264, workspace: 356 } as const;
export const panelLimits = {
  sidebar: { min: 210, max: 420 },
  workspace: { min: 260, max: 520 },
  centerMin: 480,
} as const;

const storageKeys = {
  sidebar: "emc.ui.sidebarWidth",
  workspace: "emc.ui.workspaceWidth",
} as const;

type PanelSide = "sidebar" | "workspace";

function readWidth(side: PanelSide): number {
  if (typeof window === "undefined") return panelDefaults[side];
  const stored = window.localStorage.getItem(storageKeys[side]);
  if (stored === null) return panelDefaults[side];
  const parsed = Number(stored);
  if (!Number.isFinite(parsed)) return panelDefaults[side];
  return Math.min(panelLimits[side].max, Math.max(panelLimits[side].min, parsed));
}

export function clampPanelWidth(side: PanelSide, proposed: number, viewportWidth: number, otherPanelWidth: number): number {
  const limits = panelLimits[side];
  const available = Math.max(limits.min, viewportWidth - panelLimits.centerMin - otherPanelWidth);
  return Math.round(Math.min(Math.max(proposed, limits.min), Math.min(limits.max, available)));
}

type ResizablePanelsOptions = {
  sidebarCollapsed: boolean;
  workspaceOpen: boolean;
};

export function useResizablePanels({ sidebarCollapsed, workspaceOpen }: ResizablePanelsOptions) {
  const [sidebarWidth, setSidebarWidth] = useState(() => readWidth("sidebar"));
  const [workspaceWidth, setWorkspaceWidth] = useState(() => readWidth("workspace"));
  const [resizing, setResizing] = useState<PanelSide | null>(null);
  const sidebarWidthRef = useRef(sidebarWidth);
  const workspaceWidthRef = useRef(workspaceWidth);

  useEffect(() => { sidebarWidthRef.current = sidebarWidth; }, [sidebarWidth]);
  useEffect(() => { workspaceWidthRef.current = workspaceWidth; }, [workspaceWidth]);
  useEffect(() => { window.localStorage.setItem(storageKeys.sidebar, String(sidebarWidth)); }, [sidebarWidth]);
  useEffect(() => { window.localStorage.setItem(storageKeys.workspace, String(workspaceWidth)); }, [workspaceWidth]);

  const resizeToPointer = useCallback((side: PanelSide, clientX: number) => {
    if (side === "sidebar") {
      const otherWidth = workspaceOpen ? workspaceWidthRef.current : 0;
      setSidebarWidth(clampPanelWidth("sidebar", clientX, window.innerWidth, otherWidth));
      return;
    }
    const otherWidth = sidebarCollapsed ? 64 : sidebarWidthRef.current;
    setWorkspaceWidth(clampPanelWidth("workspace", window.innerWidth - clientX, window.innerWidth, otherWidth));
  }, [sidebarCollapsed, workspaceOpen]);

  useEffect(() => {
    if (!resizing) return;
    document.body.classList.add("is-resizing-panels");
    const move = (event: PointerEvent) => resizeToPointer(resizing, event.clientX);
    const stop = () => setResizing(null);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
    window.addEventListener("pointercancel", stop, { once: true });
    return () => {
      document.body.classList.remove("is-resizing-panels");
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };
  }, [resizeToPointer, resizing]);

  const startResize = useCallback((side: PanelSide, event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    setResizing(side);
  }, []);

  const resizeWithKeyboard = useCallback((side: PanelSide, event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.shiftKey ? 1 : 12;
    if (side === "sidebar") {
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const otherWidth = workspaceOpen ? workspaceWidthRef.current : 0;
      setSidebarWidth((value) => clampPanelWidth(side, value + direction * step, window.innerWidth, otherWidth));
      return;
    }
    const direction = event.key === "ArrowLeft" ? 1 : -1;
    const otherWidth = sidebarCollapsed ? 64 : sidebarWidthRef.current;
    setWorkspaceWidth((value) => clampPanelWidth(side, value + direction * step, window.innerWidth, otherWidth));
  }, [sidebarCollapsed, workspaceOpen]);

  const resetPanel = useCallback((side: PanelSide) => {
    if (side === "sidebar") setSidebarWidth(panelDefaults.sidebar);
    else setWorkspaceWidth(panelDefaults.workspace);
  }, []);

  return { sidebarWidth, workspaceWidth, resizing, startResize, resizeWithKeyboard, resetPanel };
}
