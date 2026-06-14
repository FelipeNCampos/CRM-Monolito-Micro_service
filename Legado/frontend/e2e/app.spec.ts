import { expect, test } from "@playwright/test";

const livePayloads = {
  token: {
    access_token: "live-token",
    refresh_token: "refresh-token",
    token_type: "bearer",
  },
  contacts: {
    items: [
      {
        id: "c-100",
        name: "Marina Farias",
        email: "marina@northwave.com",
        phone: "+55 11 97777-9080",
        lead_source: "Inbound",
        owner_id: "11111111-1111-1111-1111-111111111111",
        is_active: true,
      },
      {
        id: "c-101",
        name: "Roberto Nunes",
        email: "roberto@altacorp.com",
        phone: "+55 21 98888-1200",
        lead_source: "Evento",
        owner_id: "22222222-2222-2222-2222-222222222222",
        is_active: true,
      },
    ],
    total: 2,
    page: 1,
    per_page: 6,
    pages: 1,
  },
  accounts: {
    items: [
      {
        id: "a-100",
        name: "Northwave Holdings",
        segment: "Industria",
        size: "Enterprise",
        owner_id: "11111111-1111-1111-1111-111111111111",
        is_active: true,
      },
      {
        id: "a-101",
        name: "AltaCorp",
        segment: "Servicos",
        size: "Media",
        owner_id: "22222222-2222-2222-2222-222222222222",
        is_active: true,
      },
    ],
    total: 2,
    page: 1,
    per_page: 6,
    pages: 1,
  },
  stages: [
    {
      id: "s-100",
      name: "Diagnostico",
      probability: 25,
    },
    {
      id: "s-101",
      name: "Proposta",
      probability: 80,
    },
  ],
  opportunities: {
    items: [
      {
        id: "o-100",
        title: "Expansao Northwave",
        value: 420000,
        status: "active",
        owner_id: "11111111-1111-1111-1111-111111111111",
        account_id: "a-100",
        stage_id: "s-100",
      },
      {
        id: "o-101",
        title: "Renovacao AltaCorp",
        value: 180000,
        status: "won",
        owner_id: "22222222-2222-2222-2222-222222222222",
        account_id: "a-101",
        stage_id: "s-101",
      },
    ],
    total: 2,
    page: 1,
    per_page: 6,
    pages: 1,
  },
  pipeline: {
    columns: [
      {
        stage: {
          id: "s-100",
          name: "Diagnostico",
          probability: 25,
        },
        opportunities: [
          {
            id: "o-100",
            title: "Expansao Northwave",
            value: 420000,
            status: "active",
            owner_id: "11111111-1111-1111-1111-111111111111",
            account_id: "a-100",
            stage_id: "s-100",
          },
        ],
        total_value: 420000,
        count: 1,
      },
      {
        stage: {
          id: "s-101",
          name: "Proposta",
          probability: 80,
        },
        opportunities: [
          {
            id: "o-101",
            title: "Renovacao AltaCorp",
            value: 180000,
            status: "won",
            owner_id: "22222222-2222-2222-2222-222222222222",
            account_id: "a-101",
            stage_id: "s-101",
          },
        ],
        total_value: 180000,
        count: 1,
      },
    ],
  },
  activities: {
    items: [
      {
        id: "ac-100",
        title: "Follow-up Northwave",
        kind: "task",
        status: "pending",
        due_at: "2026-03-10T10:00:00Z",
        scheduled_at: null,
        priority: "high",
        owner_id: "11111111-1111-1111-1111-111111111111",
        is_overdue: true,
      },
      {
        id: "ac-101",
        title: "Reuniao AltaCorp",
        kind: "activity",
        status: "completed",
        due_at: null,
        scheduled_at: "2026-03-14T15:00:00Z",
        priority: "medium",
        owner_id: "22222222-2222-2222-2222-222222222222",
        is_overdue: false,
      },
    ],
    total: 2,
    page: 1,
    per_page: 6,
    pages: 1,
  },
  salesDashboard: {
    generated_at: "2026-03-14T12:00:00Z",
    filters: {},
    active_opportunities_count: 2,
    active_opportunities_value: 600000,
    forecast_revenue: 480000,
    won_deals_count: 1,
    won_deals_value: 180000,
    conversion_rate: 50,
    stage_breakdown: [
      {
        stage_id: "s-100",
        stage_name: "Diagnostico",
        count: 1,
        total_value: 420000,
      },
      {
        stage_id: "s-101",
        stage_name: "Proposta",
        count: 1,
        total_value: 180000,
      },
    ],
  },
  pipelineReport: {
    generated_at: "2026-03-14T12:00:00Z",
    filters: {},
    total_count: 2,
    total_value: 600000,
    rows: [
      {
        stage_id: "s-100",
        stage_name: "Diagnostico",
        count: 1,
        total_value: 420000,
      },
      {
        stage_id: "s-101",
        stage_name: "Proposta",
        count: 1,
        total_value: 180000,
      },
    ],
  },
  activitiesReport: {
    generated_at: "2026-03-14T12:00:00Z",
    filters: {},
    indicators: {
      total_activities: 2,
      total_tasks: 1,
      completed_tasks: 0,
      task_completion_rate: 0,
      activities_per_opportunity: 1,
    },
    rows: [
      {
        owner_id: "11111111-1111-1111-1111-111111111111",
        owner_name: "Seller 01",
        activity_type_id: "at-100",
        activity_type_name: "Follow-up",
        activities_count: 1,
        tasks_count: 1,
        completed_tasks_count: 0,
      },
    ],
  },
  users: {
    items: [
      {
        id: "u-100",
        name: "Administrador",
        email: "admin@gmail.com",
        is_active: true,
        roles: [
          {
            id: "r-100",
            name: "admin",
            description: "Administrador",
            is_active: true,
            permissions: [
              {
                module: "admin",
                can_create: true,
                can_read: true,
                can_update: true,
                can_delete: true,
              },
            ],
          },
        ],
      },
    ],
    total: 1,
    page: 1,
    per_page: 6,
    pages: 1,
  },
  roles: [
    {
      id: "r-100",
      name: "admin",
      description: "Administrador",
      is_active: true,
      permissions: [
        {
          module: "admin",
          can_create: true,
          can_read: true,
          can_update: true,
          can_delete: true,
        },
        {
          module: "reports",
          can_create: false,
          can_read: true,
          can_update: false,
          can_delete: false,
        },
      ],
    },
  ],
  audit: {
    items: [
      {
        id: "ad-100",
        entity_type: "opportunity",
        action: "update",
        created_at: "2026-03-14T13:10:00Z",
      },
      {
        id: "ad-101",
        entity_type: "activity",
        action: "create",
        created_at: "2026-03-14T12:05:00Z",
      },
    ],
    total: 2,
    page: 1,
    per_page: 6,
    pages: 1,
  },
};

async function mockLiveApi(page: import("@playwright/test").Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === "POST" && url.pathname === "/api/v1/auth/login") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.token),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/contacts") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.contacts),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/accounts") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.accounts),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/pipeline/stages") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.stages),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/opportunities") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.opportunities),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/pipeline") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.pipeline),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/activities") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.activities),
      });
      return;
    }

    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/reports/sales-dashboard"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.salesDashboard),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/reports/pipeline") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.pipelineReport),
      });
      return;
    }

    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/reports/activities"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.activitiesReport),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/admin/users") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.users),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/admin/roles") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.roles),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/audit") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(livePayloads.audit),
      });
      return;
    }

    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/reports/pipeline/export"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "text/csv",
        body: "stage,count,total\nDiagnostico,1,420000\nProposta,1,180000\n",
      });
      return;
    }

    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/reports/activities/export"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "text/csv",
        body: "owner,activities,tasks\nSeller 01,1,1\n",
      });
      return;
    }

    await route.abort();
  });
}

test("permite navegar no workspace em modo demonstracao", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "Operacao comercial centralizada em um unico workspace.",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Explorar modo demo" }).click();

  await expect(page.getByText("Demo mode")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Visao geral" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Central operacional pronta para o dia a dia do CRM." }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Contatos Leads, owners e origem comercial." }).click();
  await expect(page.getByRole("heading", { name: "Leads e contatos" })).toBeVisible();
  await expect(page.getByText("Marina Farias")).toBeVisible();

  await page.getByPlaceholder("Busque por owner, conta, oportunidade ou status").fill("Montana");
  await expect(page.getByText("Marina Farias")).not.toBeVisible();

  await page.getByRole("link", { name: "Pipeline Funil, forecast e prioridades." }).click();
  await expect(page.getByRole("heading", { name: "Etapas do pipeline" })).toBeVisible();
  await expect(page.getByText("Piloto Montana")).toBeVisible();

  await page.getByPlaceholder("Busque por owner, conta, oportunidade ou status").fill("");
  await page.getByRole("link", { name: "Relatorios Analise operacional do CRM." }).click();
  await expect(page.getByText("Volume de atividades")).toBeVisible();

  await page.getByRole("link", { name: "Administracao RBAC, auditoria e evolucao futura." }).click();
  await expect(page.getByText("Base pronta para expansao")).toBeVisible();
});

test("redireciona para login ao acessar rota protegida sem sessao", async ({ page }) => {
  await page.goto("/reports");

  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", {
      name: "Operacao comercial centralizada em um unico workspace.",
    }),
  ).toBeVisible();
});

test("consome a API em modo live e permite exportacao de relatorios", async ({
  page,
}) => {
  await mockLiveApi(page);
  await page.goto("/");

  await page.getByLabel("E-mail").fill("admin@gmail.com");
  await page.getByLabel("Senha").fill("Coto1423");
  await page.getByRole("button", { name: "Entrar com API" }).click();

  await expect(page.getByText("Live API")).toBeVisible();
  await expect(
    page.getByText("Workspace conectado ao backend do CRM."),
  ).toBeVisible();
  await expect(page.getByText("R$ 600.000")).toBeVisible();

  await page.getByRole("link", { name: "Atividades Follow-ups e produtividade." }).click();
  await expect(page.getByText("Follow-up Northwave")).toBeVisible();
  await expect(page.getByText(/Atrasada desde/)).toBeVisible();

  await page.getByRole("link", { name: "Relatorios Analise operacional do CRM." }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar pipeline CSV" }).click();
  const download = await downloadPromise;

  expect(await download.suggestedFilename()).toBe("pipeline-report.csv");
  await expect(page.getByText("Arquivo exportado com sucesso.")).toBeVisible();
});
