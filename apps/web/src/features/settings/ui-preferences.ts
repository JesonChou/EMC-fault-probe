export type ThemeMode = "light" | "dark";

export const preferenceKeys = {
  theme: "emc.ui.theme",
  sidebarCollapsed: "emc.ui.sidebarCollapsed",
  workspaceOpen: "emc.ui.workspaceOpen",
} as const;

export function readBooleanPreference(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(key);
  return value === null ? fallback : value === "true";
}

export function readThemePreference(): ThemeMode {
  if (typeof window === "undefined") return "light";
  return window.localStorage.getItem(preferenceKeys.theme) === "dark" ? "dark" : "light";
}
