import type { SessionSummary, WorkspaceSummary } from "./types/ui";

export const previewSessions: SessionSummary[] = [
  { id: "1", title: "辐射发射超标排查", updatedAt: "刚刚" },
  { id: "2", title: "静电放电导致设备复位", updatedAt: "昨天" },
  { id: "3", title: "电源端传导骚扰整改", updatedAt: "8 月 21 日" },
  { id: "4", title: "CAN 总线抗扰度分析", updatedAt: "8 月 18 日" },
];

export const previewWorkspace: WorkspaceSummary = {
  name: "EMC-fault-probe",
  path: "D:\\BUAA\\EMC-fault-probe",
  branch: "main",
  files: [
    {
      name: "apps",
      kind: "directory",
      children: [
        { name: "backend", kind: "directory" },
        { name: "desktop-agent", kind: "directory" },
        { name: "web", kind: "directory", active: true },
      ],
    },
    { name: "packages", kind: "directory" },
    { name: "integrations", kind: "directory" },
    { name: "README.md", kind: "file" },
    { name: "pyproject.toml", kind: "file" },
  ],
};
