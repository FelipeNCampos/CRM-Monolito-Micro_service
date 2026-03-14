export type WorkspaceMode = "live" | "demo";

export type SessionState = {
  accessToken: string;
  refreshToken: string;
  email: string;
};

export type ModuleKey =
  | "overview"
  | "contacts"
  | "accounts"
  | "pipeline"
  | "activities"
  | "reports"
  | "administration";

export type Metric = {
  label: string;
  value: string;
  trend: string;
};

export type TimelineEvent = {
  title: string;
  subtitle: string;
  stamp: string;
  status: "success" | "warning" | "neutral";
};

export type ContactRow = {
  id: string;
  name: string;
  email: string;
  phone: string;
  source: string;
  owner: string;
  status: string;
};

export type AccountRow = {
  id: string;
  name: string;
  segment: string;
  size: string;
  owner: string;
  status: string;
};

export type OpportunityRow = {
  id: string;
  title: string;
  stage: string;
  account: string;
  owner: string;
  value: string;
  status: string;
};

export type StageColumn = {
  id: string;
  name: string;
  probability: string;
  count: number;
  totalValue: string;
  opportunities: OpportunityRow[];
};

export type ActivityRow = {
  id: string;
  title: string;
  kind: string;
  status: string;
  owner: string;
  dueLabel: string;
  priority: string;
};

export type ReportCard = {
  title: string;
  summary: string;
  value: string;
  footnote: string;
};

export type AdminRow = {
  title: string;
  description: string;
  detail: string;
  status: "ok" | "attention";
};

export type WorkspaceSnapshot = {
  mode: WorkspaceMode;
  heroTitle: string;
  heroCopy: string;
  heroHighlights: string[];
  metrics: Metric[];
  timeline: TimelineEvent[];
  contacts: ContactRow[];
  accounts: AccountRow[];
  opportunities: OpportunityRow[];
  stages: StageColumn[];
  activities: ActivityRow[];
  reports: ReportCard[];
  administration: AdminRow[];
};
