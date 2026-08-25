export type SessionSummary = {
  id: string;
  title: string;
  updatedAt: string;
  active?: boolean;
};

export type WorkspaceFile = {
  name: string;
  kind: "file" | "directory";
  active?: boolean;
  children?: WorkspaceFile[];
};

export type WorkspaceSummary = {
  name: string;
  path: string;
  branch?: string;
  files: WorkspaceFile[];
};
