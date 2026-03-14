import { demoSnapshot } from "./mockData";
import type {
  AccountRow,
  ActivityRow,
  AdminRow,
  ContactRow,
  OpportunityRow,
  ReportCard,
  SessionState,
  StageColumn,
  TimelineEvent,
  WorkspaceSnapshot,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
};

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type ContactApi = {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  lead_source?: string | null;
  owner_id?: string | null;
  is_active: boolean;
};

type AccountApi = {
  id: string;
  name: string;
  segment?: string | null;
  size?: string | null;
  owner_id?: string | null;
  is_active: boolean;
};

type OpportunityApi = {
  id: string;
  title: string;
  value?: number | string | null;
  status: string;
  owner_id?: string | null;
  account_id: string;
  stage_id: string;
};

type PipelineStageApi = {
  id: string;
  name: string;
  probability: number | string;
};

type PipelineViewApi = {
  columns: Array<{
    stage: PipelineStageApi;
    opportunities: OpportunityApi[];
    total_value: number | string;
    count: number;
  }>;
};

type ActivityApi = {
  id: string;
  title: string;
  kind: string;
  status: string;
  due_at?: string | null;
  scheduled_at?: string | null;
  priority?: string | null;
  owner_id?: string | null;
  is_overdue: boolean;
};

type SalesDashboardApi = {
  generated_at: string;
  active_opportunities_count: number;
  active_opportunities_value: number | string;
  forecast_revenue: number | string;
  won_deals_count: number;
  won_deals_value: number | string;
  conversion_rate: number | string;
  stage_breakdown: Array<{
    stage_id: string;
    stage_name: string;
    count: number;
    total_value: number | string;
  }>;
};

type PipelineReportApi = {
  generated_at: string;
  total_count: number;
  total_value: number | string;
  rows: Array<{
    stage_id: string;
    stage_name: string;
    count: number;
    total_value: number | string;
  }>;
};

type ActivitiesReportApi = {
  generated_at: string;
  indicators: {
    total_activities: number;
    total_tasks: number;
    completed_tasks: number;
    task_completion_rate: number | string;
    activities_per_opportunity: number | string;
  };
  rows: Array<{
    owner_id?: string | null;
    owner_name: string;
    activity_type_id: string;
    activity_type_name: string;
    activities_count: number;
    tasks_count: number;
    completed_tasks_count: number;
  }>;
};

type RoleApi = {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  permissions: Array<{
    module: string;
    can_create: boolean;
    can_read: boolean;
    can_update: boolean;
    can_delete: boolean;
  }>;
};

type UserApi = {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  roles: RoleApi[];
};

type AuditApi = {
  id: string;
  entity_type: string;
  action: string;
  created_at: string;
};

function toCurrency(value: number | string | null | undefined): string {
  const numeric = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(numeric) ? numeric : 0);
}

function toPercent(value: number | string | null | undefined): string {
  const numeric = Number(value ?? 0);
  return `${numeric.toFixed(1).replace(".", ",")}%`;
}

function toWhenLabel(value?: string | null): string {
  if (!value) {
    return "Sem agenda";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Sem agenda";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function shortOwner(ownerId?: string | null): string {
  if (!ownerId) {
    return "Nao atribuido";
  }

  return `Owner ${ownerId.slice(0, 6)}`;
}

function statusLabel(
  active: boolean,
  positive = "Ativo",
  negative = "Inativo",
): string {
  return active ? positive : negative;
}

async function fetchJson<T>(path: string, token: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Falha ao carregar ${path}`);
  }

  return (await response.json()) as T;
}

function buildTimeline(
  audit: PaginatedResponse<AuditApi>,
  activities: PaginatedResponse<ActivityApi>,
): TimelineEvent[] {
  const fromAudit = audit.items.slice(0, 2).map((item) => ({
    title: `${item.entity_type} ${item.action}`.replace("_", " "),
    subtitle: "Evento auditado no backend.",
    stamp: toWhenLabel(item.created_at),
    status: "neutral" as const,
  }));

  const overdue = activities.items.find((item) => item.is_overdue);

  if (!overdue) {
    return [
      ...fromAudit,
      {
        title: "Operacao sem tarefas vencidas",
        subtitle: "Nenhum follow-up marcado como atrasado nesta leitura.",
        stamp: "Visao atual",
        status: "success",
      },
    ];
  }

  return [
    {
      title: overdue.title,
      subtitle: "Ha atividade vencida exigindo priorizacao da operacao.",
      stamp: overdue.due_at ? toWhenLabel(overdue.due_at) : "Sem horario",
      status: "warning",
    },
    ...fromAudit,
  ];
}

function mapContacts(payload: PaginatedResponse<ContactApi>): ContactRow[] {
  return payload.items.map((contact) => ({
    id: contact.id,
    name: contact.name,
    email: contact.email,
    phone: contact.phone ?? "-",
    source: contact.lead_source ?? "Nao informado",
    owner: shortOwner(contact.owner_id),
    status: statusLabel(contact.is_active),
  }));
}

function mapAccounts(payload: PaginatedResponse<AccountApi>): AccountRow[] {
  return payload.items.map((account) => ({
    id: account.id,
    name: account.name,
    segment: account.segment ?? "Nao informado",
    size: account.size ?? "Nao informado",
    owner: shortOwner(account.owner_id),
    status: statusLabel(account.is_active, "Ativa", "Inativa"),
  }));
}

function mapOpportunities(
  payload: PaginatedResponse<OpportunityApi>,
  stageLookup: Map<string, string>,
  accountLookup: Map<string, string>,
): OpportunityRow[] {
  return payload.items.map((opportunity) => ({
    id: opportunity.id,
    title: opportunity.title,
    stage: stageLookup.get(opportunity.stage_id) ?? "Sem etapa",
    account: accountLookup.get(opportunity.account_id) ?? "Conta vinculada",
    owner: shortOwner(opportunity.owner_id),
    value: toCurrency(opportunity.value),
    status: opportunity.status,
  }));
}

function mapStages(
  payload: PipelineViewApi,
  accountLookup: Map<string, string>,
): StageColumn[] {
  return payload.columns.map((column) => ({
    id: column.stage.id,
    name: column.stage.name,
    probability: toPercent(column.stage.probability),
    count: column.count,
    totalValue: toCurrency(column.total_value),
    opportunities: column.opportunities.map((opportunity) => ({
      id: opportunity.id,
      title: opportunity.title,
      stage: column.stage.name,
      account: accountLookup.get(opportunity.account_id) ?? "Conta vinculada",
      owner: shortOwner(opportunity.owner_id),
      value: toCurrency(opportunity.value),
      status: opportunity.status,
    })),
  }));
}

function mapActivities(payload: PaginatedResponse<ActivityApi>): ActivityRow[] {
  return payload.items.map((activity) => ({
    id: activity.id,
    title: activity.title,
    kind: activity.kind,
    status: activity.status,
    owner: shortOwner(activity.owner_id),
    dueLabel: activity.is_overdue
      ? `Atrasada desde ${toWhenLabel(activity.due_at)}`
      : toWhenLabel(activity.due_at ?? activity.scheduled_at),
    priority: activity.priority ?? "Sem prioridade",
  }));
}

function buildReports(
  sales: SalesDashboardApi,
  pipeline: PipelineReportApi,
  activities: ActivitiesReportApi,
): ReportCard[] {
  return [
    {
      title: "Sales dashboard",
      summary: "Forecast, oportunidades ativas e negocios ganhos no periodo.",
      value: toPercent(sales.conversion_rate),
      footnote: `${sales.won_deals_count} negocios ganhos somando ${toCurrency(sales.won_deals_value)}.`,
    },
    {
      title: "Pipeline por estagio",
      summary: "Visao consolidada do funil com capacidade de exportacao.",
      value: toCurrency(pipeline.total_value),
      footnote: `${pipeline.total_count} oportunidades distribuidas em ${pipeline.rows.length} etapas.`,
    },
    {
      title: "Produtividade de atividades",
      summary: "Volume operacional por owner e taxa de conclusao de tarefas.",
      value: toPercent(activities.indicators.task_completion_rate),
      footnote: `${activities.indicators.total_tasks} tarefas e ${activities.indicators.total_activities} atividades no periodo.`,
    },
  ];
}

function buildAdministration(
  users: PaginatedResponse<UserApi>,
  roles: RoleApi[],
  audit: PaginatedResponse<AuditApi>,
): AdminRow[] {
  const modules = new Set(
    roles.flatMap((role) => role.permissions.map((permission) => permission.module)),
  );

  return [
    {
      title: "Usuarios e papeis",
      description: "Controle de acesso por perfil com base nas rotas administrativas.",
      detail: `${users.total} usuarios e ${roles.length} papeis ativos na leitura atual.`,
      status: "ok",
    },
    {
      title: "Cobertura RBAC",
      description: "Permissoes preparadas para crescer junto das fases 3 e 4.",
      detail: `${modules.size} modulos mapeados por permissao.`,
      status: "ok",
    },
    {
      title: "Rastro de auditoria",
      description: "Ultimas alteracoes administrativas e operacionais.",
      detail: `${audit.total} eventos auditados disponiveis para consulta.`,
      status: audit.total > 0 ? "ok" : "attention",
    },
  ];
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<SessionState> {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  if (!response.ok) {
    throw new Error("Nao foi possivel autenticar com as credenciais informadas.");
  }

  const payload = (await response.json()) as LoginResponse;
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    email,
  };
}

export async function loadWorkspaceSnapshot(
  token: string,
): Promise<WorkspaceSnapshot> {
  try {
    const [
      contacts,
      accounts,
      stages,
      opportunities,
      pipelineView,
      activities,
      salesDashboard,
      pipelineReport,
      activitiesReport,
      users,
      roles,
      audit,
    ] = await Promise.all([
      fetchJson<PaginatedResponse<ContactApi>>("/contacts?page=1&per_page=6", token),
      fetchJson<PaginatedResponse<AccountApi>>("/accounts?page=1&per_page=6", token),
      fetchJson<PipelineStageApi[]>("/pipeline/stages", token),
      fetchJson<PaginatedResponse<OpportunityApi>>(
        "/opportunities?page=1&per_page=6",
        token,
      ),
      fetchJson<PipelineViewApi>("/pipeline", token),
      fetchJson<PaginatedResponse<ActivityApi>>("/activities?page=1&per_page=6", token),
      fetchJson<SalesDashboardApi>("/reports/sales-dashboard", token),
      fetchJson<PipelineReportApi>("/reports/pipeline", token),
      fetchJson<ActivitiesReportApi>("/reports/activities", token),
      fetchJson<PaginatedResponse<UserApi>>("/admin/users?page=1&per_page=6", token),
      fetchJson<RoleApi[]>("/admin/roles", token),
      fetchJson<PaginatedResponse<AuditApi>>("/audit?page=1&per_page=6", token),
    ]);

    const accountLookup = new Map(accounts.items.map((item) => [item.id, item.name]));
    const stageLookup = new Map(stages.map((item) => [item.id, item.name]));

    return {
      mode: "live",
      heroTitle: "Operacao comercial integrada com leitura em tempo real.",
      heroCopy:
        "A base da Fase 2 esta conectada a API do CRM e organizada para evoluir com marketing, segmentacao, campanhas e suporte nas fases seguintes.",
      heroHighlights: [
        `${contacts.total} contatos e ${accounts.total} contas ativos sincronizados com o backend.`,
        `${activities.total} atividades monitoradas com relatorios operacionais ja disponiveis.`,
        "Arquitetura de frontend preparada para novos dominios sem reescrever a shell principal.",
      ],
      metrics: [
        {
          label: "Contatos ativos",
          value: `${contacts.total}`,
          trend: `${accounts.total} contas na carteira atual`,
        },
        {
          label: "Pipeline aberto",
          value: toCurrency(salesDashboard.active_opportunities_value),
          trend: `${salesDashboard.active_opportunities_count} oportunidades ativas`,
        },
        {
          label: "Forecast",
          value: toCurrency(salesDashboard.forecast_revenue),
          trend: `${salesDashboard.won_deals_count} ganhos no recorte atual`,
        },
        {
          label: "Tarefas concluidas",
          value: `${activitiesReport.indicators.completed_tasks}`,
          trend: `${toPercent(activitiesReport.indicators.task_completion_rate)} de conclusao`,
        },
      ],
      timeline: buildTimeline(audit, activities),
      contacts: mapContacts(contacts),
      accounts: mapAccounts(accounts),
      opportunities: mapOpportunities(opportunities, stageLookup, accountLookup),
      stages: mapStages(pipelineView, accountLookup),
      activities: mapActivities(activities),
      reports: buildReports(salesDashboard, pipelineReport, activitiesReport),
      administration: buildAdministration(users, roles, audit),
    };
  } catch {
    return demoSnapshot;
  }
}
