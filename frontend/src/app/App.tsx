import anime from "animejs";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useState,
} from "react";
import type { FormEvent, ReactNode } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { loadWorkspaceSnapshot, loginRequest } from "./api";
import { demoSnapshot } from "./mockData";
import type {
  ActivityRow,
  AdminRow,
  Metric,
  ModuleKey,
  OpportunityRow,
  SessionState,
  StageColumn,
  TimelineEvent,
  WorkspaceSnapshot,
} from "./types";

const SESSION_KEY = "crm.frontend.session";

const modules: Array<{
  key: ModuleKey;
  path: string;
  title: string;
  description: string;
}> = [
  {
    key: "overview",
    path: "/",
    title: "Visao geral",
    description: "Painel executivo da operacao.",
  },
  {
    key: "contacts",
    path: "/contacts",
    title: "Contatos",
    description: "Leads, owners e origem comercial.",
  },
  {
    key: "accounts",
    path: "/accounts",
    title: "Contas",
    description: "Carteira, segmentos e hierarquia.",
  },
  {
    key: "pipeline",
    path: "/pipeline",
    title: "Pipeline",
    description: "Funil, forecast e prioridades.",
  },
  {
    key: "activities",
    path: "/activities",
    title: "Atividades",
    description: "Follow-ups e produtividade.",
  },
  {
    key: "reports",
    path: "/reports",
    title: "Relatorios",
    description: "Analise operacional da Fase 2.",
  },
  {
    key: "administration",
    path: "/administration",
    title: "Administracao",
    description: "RBAC, auditoria e evolucao futura.",
  },
];

function restoreSession(): SessionState | null {
  const raw = window.localStorage.getItem(SESSION_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as SessionState;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function useReveal(trigger: string): void {
  useEffect(() => {
    const targets = document.querySelectorAll(".reveal-stagger");
    if (!targets.length) {
      return;
    }

    anime({
      targets,
      opacity: [0, 1],
      translateY: [18, 0],
      easing: "easeOutQuart",
      duration: 650,
      delay: anime.stagger(55),
    });
  }, [trigger]);
}

function badgeTone(value: string): string {
  const normalized = value.toLowerCase();

  if (
    normalized.includes("won") ||
    normalized.includes("conclu") ||
    normalized.includes("ativo") ||
    normalized.includes("ok")
  ) {
    return "badge";
  }

  if (
    normalized.includes("attention") ||
    normalized.includes("warning") ||
    normalized.includes("planejada") ||
    normalized.includes("pendente")
  ) {
    return "badge warning";
  }

  if (
    normalized.includes("lost") ||
    normalized.includes("atras") ||
    normalized.includes("danger") ||
    normalized.includes("inativo")
  ) {
    return "badge danger";
  }

  return "badge";
}

function matchesSearch(query: string, ...values: Array<string | number>): boolean {
  if (!query) {
    return true;
  }

  const normalizedQuery = query.trim().toLowerCase();
  return values.some((value) =>
    String(value).toLowerCase().includes(normalizedQuery),
  );
}

function currentTitle(pathname: string): string {
  const match = modules.find((item) => item.path === pathname);
  return match?.title ?? "CRM Workspace";
}

export function App() {
  const [session, setSession] = useState<SessionState | null>(() => restoreSession());
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(demoSnapshot);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (session) {
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      return;
    }

    window.localStorage.removeItem(SESSION_KEY);
  }, [session]);

  useEffect(() => {
    if (!session) {
      setSnapshot(demoSnapshot);
      setWorkspaceLoading(false);
      setFeedback(null);
      return;
    }

    if (session.accessToken === "demo-token") {
      setSnapshot(demoSnapshot);
      setWorkspaceLoading(false);
      setFeedback("Modo demonstracao ativo para navegacao do frontend.");
      return;
    }

    let cancelled = false;
    setWorkspaceLoading(true);
    setFeedback(null);

    void loadWorkspaceSnapshot(session.accessToken)
      .then((nextSnapshot) => {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setSnapshot(nextSnapshot);
        });

        setFeedback(
          nextSnapshot.mode === "live"
            ? "Workspace conectado ao backend da Fase 2."
            : "Algumas rotas nao responderam; exibindo modo demonstracao.",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setWorkspaceLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [session]);

  async function handleLogin(email: string, password: string) {
    const nextSession = await loginRequest(email, password);
    startTransition(() => {
      setSession(nextSession);
    });
  }

  function handleDemoAccess() {
    startTransition(() => {
      setSnapshot(demoSnapshot);
      setSession({
        accessToken: "demo-token",
        refreshToken: "demo-refresh",
        email: "demo@crm.local",
      });
    });
  }

  function handleLogout() {
    startTransition(() => {
      setSession(null);
      setSnapshot(demoSnapshot);
    });
  }

  if (!session) {
    return <LoginPage onLogin={handleLogin} onDemoAccess={handleDemoAccess} />;
  }

  return (
    <AppShell
      session={session}
      snapshot={snapshot}
      feedback={feedback}
      workspaceLoading={workspaceLoading}
      onLogout={handleLogout}
    />
  );
}

function LoginPage(props: {
  onLogin: (email: string, password: string) => Promise<void>;
  onDemoAccess: () => void;
}) {
  const [email, setEmail] = useState("admin@gmail.com");
  const [password, setPassword] = useState("Coto1423");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useReveal("login");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await props.onLogin(email, password);
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Nao foi possivel entrar agora.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <section className="reveal-stagger">
          <div className="eyebrow">CRM Workspace</div>
          <h1>Operacao comercial pronta para crescer ate as Fases 3 e 4.</h1>
          <p className="muted">
            Shell executiva em React com integracao real da Fase 2, identidade
            visual neutra e base preparada para marketing, campanhas, suporte e
            novos paineis analiticos.
          </p>
          <div className="support-grid" style={{ marginTop: 22 }}>
            <FutureCard
              title="Fase 2 ativa"
              copy="Contatos, contas, pipeline, atividades, relatorios e governanca em um unico fluxo."
            />
            <FutureCard
              title="Fase 3 habilitada"
              copy="Arquitetura pronta para leads, segmentacao e campanhas sem romper a shell atual."
            />
            <FutureCard
              title="Fase 4 preparada"
              copy="Espaco reservado para suporte, SLAs, base de conhecimento e monitoracao operacional."
            />
          </div>
        </section>

        <aside className="login-side reveal-stagger">
          <div className="eyebrow">Acesso</div>
          <h2 style={{ marginTop: 8 }}>Entre no workspace</h2>
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <input
                id="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="admin@gmail.com"
              />
            </div>
            <div className="field">
              <label htmlFor="password">Senha</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Sua senha"
              />
            </div>
            {error ? <p className="muted">{error}</p> : null}
            <div className="auth-actions">
              <button className="button" disabled={submitting} type="submit">
                {submitting ? "Entrando..." : "Entrar com API"}
              </button>
              <button
                className="ghost-button"
                type="button"
                onClick={props.onDemoAccess}
              >
                Explorar modo demo
              </button>
            </div>
          </form>
          <p className="muted" style={{ marginTop: 18 }}>
            Links uteis:{" "}
            <a href="http://localhost:8000/api/v1/docs" target="_blank" rel="noreferrer">
              Swagger
            </a>{" "}
            e{" "}
            <a
              href="http://localhost:8000/api/v1/postman-collection.json"
              target="_blank"
              rel="noreferrer"
            >
              collection Postman
            </a>
            .
          </p>
        </aside>
      </div>
    </div>
  );
}

function AppShell(props: {
  session: SessionState;
  snapshot: WorkspaceSnapshot;
  feedback: string | null;
  workspaceLoading: boolean;
  onLogout: () => void;
}) {
  const location = useLocation();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);

  useReveal(`${location.pathname}-${props.snapshot.mode}`);

  const contacts = props.snapshot.contacts.filter((item) =>
    matchesSearch(deferredSearch, item.name, item.email, item.source, item.owner),
  );
  const accounts = props.snapshot.accounts.filter((item) =>
    matchesSearch(deferredSearch, item.name, item.segment, item.owner, item.status),
  );
  const opportunities = props.snapshot.opportunities.filter((item) =>
    matchesSearch(
      deferredSearch,
      item.title,
      item.stage,
      item.account,
      item.owner,
      item.status,
    ),
  );
  const stages = props.snapshot.stages.filter((item) =>
    matchesSearch(deferredSearch, item.name, item.totalValue, item.count),
  );
  const activities = props.snapshot.activities.filter((item) =>
    matchesSearch(
      deferredSearch,
      item.title,
      item.kind,
      item.status,
      item.owner,
      item.priority,
    ),
  );
  const reports = props.snapshot.reports.filter((item) =>
    matchesSearch(deferredSearch, item.title, item.summary, item.footnote, item.value),
  );
  const administration = props.snapshot.administration.filter((item) =>
    matchesSearch(deferredSearch, item.title, item.description, item.detail, item.status),
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block reveal-stagger">
          <span className="brand-mark">CRM</span>
          <h2 className="brand-title">Workspace Fase 2</h2>
          <p className="brand-copy">
            Shell corporativa pronta para absorver marketing, analytics,
            atendimento e novos modulos sem quebrar a navegacao principal.
          </p>
        </div>

        <nav className="nav-list">
          {modules.map((item) => (
            <NavLink
              key={item.key}
              className={({ isActive }) =>
                isActive ? "nav-link active reveal-stagger" : "nav-link reveal-stagger"
              }
              to={item.path}
            >
              <strong>{item.title}</strong>
              <span>{item.description}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content-shell">
        <div className="topbar reveal-stagger">
          <div>
            <div className="eyebrow">Workspace atual</div>
            <h1 style={{ margin: "6px 0 0", fontSize: "2rem" }}>
              {currentTitle(location.pathname)}
            </h1>
          </div>
          <div className="topbar-actions" style={{ width: "min(100%, 560px)" }}>
            <input
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Busque por owner, conta, oportunidade ou status"
            />
            <span className="pill">
              {props.snapshot.mode === "live" ? "Live API" : "Demo mode"}
            </span>
            <button className="ghost-button" onClick={props.onLogout} type="button">
              Sair
            </button>
          </div>
        </div>

        {props.feedback ? (
          <div className="panel reveal-stagger" style={{ marginBottom: 22 }}>
            <div className="split-row">
              <div>
                <div className="eyebrow">Status do ambiente</div>
                <p className="muted" style={{ margin: "8px 0 0" }}>
                  {props.feedback}
                </p>
              </div>
              <span className="pill">{props.session.email}</span>
            </div>
          </div>
        ) : null}

        <Routes>
          <Route
            path="/"
            element={
              <OverviewPage
                snapshot={props.snapshot}
                loading={props.workspaceLoading}
              />
            }
          />
          <Route path="/contacts" element={<ContactsPage rows={contacts} />} />
          <Route path="/accounts" element={<AccountsPage rows={accounts} />} />
          <Route
            path="/pipeline"
            element={
              <PipelinePage opportunities={opportunities} stages={stages} />
            }
          />
          <Route path="/activities" element={<ActivitiesPage rows={activities} />} />
          <Route
            path="/reports"
            element={
              <ReportsPage
                rows={reports}
                token={
                  props.snapshot.mode === "live" ? props.session.accessToken : null
                }
              />
            }
          />
          <Route
            path="/administration"
            element={<AdministrationPage rows={administration} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function OverviewPage(props: {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
}) {
  return (
    <div className="section-stack">
      <section className="hero-card reveal-stagger">
        <div>
          <div className="eyebrow">Fases 1 e 2 operacionais</div>
          <h1>{props.snapshot.heroTitle}</h1>
          <p className="muted">{props.snapshot.heroCopy}</p>
          <div className="list" style={{ marginTop: 18 }}>
            {props.snapshot.heroHighlights.map((item) => (
              <div className="list-item" key={item}>
                {item}
              </div>
            ))}
          </div>
          <div className="hero-actions" style={{ marginTop: 18 }}>
            <a className="button" href="http://localhost:8000/api/v1/docs" target="_blank" rel="noreferrer">
              Abrir docs
            </a>
            <a
              className="ghost-button"
              href="http://localhost:8000/api/v1/postman-collection.json"
              target="_blank"
              rel="noreferrer"
            >
              Baixar Postman
            </a>
          </div>
        </div>

        <div className="hero-grid">
          <Panel
            eyebrow="Status"
            title="Leitura operacional"
            copy={
              props.loading
                ? "Atualizando dados do backend..."
                : "Snapshot pronto para decisao, governanca e proxima expansao do produto."
            }
          />
          <Panel
            eyebrow="Roadmap"
            title="Expansao futura"
            copy="A shell atual ja separa os dominios que vao receber marketing, analytics, atendimento e automacoes."
          />
        </div>
      </section>

      <MetricGrid metrics={props.snapshot.metrics} />

      <div className="panel-grid">
        <TimelinePanel items={props.snapshot.timeline} />
        <FutureModulesPanel />
      </div>
    </div>
  );
}

function ContactsPage(props: {
  rows: WorkspaceSnapshot["contacts"];
}) {
  return (
    <div className="section-stack">
      <TableCard
        title="Leads e contatos"
        eyebrow="Fase 1"
        copy="Base de relacionamento usada por pipeline, atividades e futuras campanhas de marketing."
      >
        <table>
          <thead>
            <tr>
              <th>Contato</th>
              <th>Canal</th>
              <th>Origem</th>
              <th>Owner</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {props.rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                  <div className="muted">{row.email}</div>
                </td>
                <td>{row.phone}</td>
                <td>{row.source}</td>
                <td>{row.owner}</td>
                <td>
                  <span className={badgeTone(row.status)}>{row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCard>
    </div>
  );
}

function AccountsPage(props: {
  rows: WorkspaceSnapshot["accounts"];
}) {
  return (
    <div className="section-stack">
      <TableCard
        title="Contas e carteira"
        eyebrow="Fase 1"
        copy="Organizacao de empresas, segmentos e ownership com base pronta para scoring e segmentacao."
      >
        <table>
          <thead>
            <tr>
              <th>Conta</th>
              <th>Segmento</th>
              <th>Porte</th>
              <th>Owner</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {props.rows.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.segment}</td>
                <td>{row.size}</td>
                <td>{row.owner}</td>
                <td>
                  <span className={badgeTone(row.status)}>{row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCard>
    </div>
  );
}

function PipelinePage(props: {
  opportunities: OpportunityRow[];
  stages: StageColumn[];
}) {
  return (
    <div className="section-stack">
      <TableCard
        title="Oportunidades"
        eyebrow="Fase 1"
        copy="Pipeline comercial com visualizacao por negocio e resumo financeiro por etapa."
      >
        <table>
          <thead>
            <tr>
              <th>Negocio</th>
              <th>Etapa</th>
              <th>Conta</th>
              <th>Owner</th>
              <th>Valor</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {props.opportunities.map((row) => (
              <tr key={row.id}>
                <td>{row.title}</td>
                <td>{row.stage}</td>
                <td>{row.account}</td>
                <td>{row.owner}</td>
                <td>{row.value}</td>
                <td>
                  <span className={badgeTone(row.status)}>{row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCard>

      <section className="panel reveal-stagger">
        <header>
          <div>
            <div className="eyebrow">Kanban executivo</div>
            <h2>Etapas do pipeline</h2>
          </div>
          <span className="pill">{props.stages.length} colunas monitoradas</span>
        </header>
        <div className="kanban-grid">
          {props.stages.map((stage) => (
            <article className="stage-card" key={stage.id}>
              <div className="split-row">
                <strong>{stage.name}</strong>
                <span className="pill">{stage.probability}</span>
              </div>
              <p className="muted">
                {stage.count} negocios somando {stage.totalValue}
              </p>
              <div className="list">
                {stage.opportunities.slice(0, 3).map((opportunity) => (
                  <div className="list-item" key={opportunity.id}>
                    <strong>{opportunity.title}</strong>
                    <div className="muted">
                      {opportunity.account} - {opportunity.value}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function ActivitiesPage(props: {
  rows: ActivityRow[];
}) {
  const overdueCount = props.rows.filter((row) =>
    row.dueLabel.toLowerCase().includes("atras"),
  ).length;

  return (
    <div className="section-stack">
      <div className="panel-grid">
        <Panel
          eyebrow="Operacao"
          title="Agenda e follow-ups"
          copy={`${props.rows.length} itens carregados para acompanhamento operacional.`}
        />
        <Panel
          eyebrow="Prioridade"
          title="Itens vencidos"
          copy={`${overdueCount} registros exigem acao imediata do time.`}
        />
      </div>

      <TableCard
        title="Atividades"
        eyebrow="Fase 2"
        copy="Modulo operacional de tarefas e atividades preparado para automacoes futuras."
      >
        <table>
          <thead>
            <tr>
              <th>Titulo</th>
              <th>Tipo</th>
              <th>Status</th>
              <th>Owner</th>
              <th>Prazo</th>
              <th>Prioridade</th>
            </tr>
          </thead>
          <tbody>
            {props.rows.map((row) => (
              <tr key={row.id}>
                <td>{row.title}</td>
                <td>{row.kind}</td>
                <td>
                  <span className={badgeTone(row.status)}>{row.status}</span>
                </td>
                <td>{row.owner}</td>
                <td>{row.dueLabel}</td>
                <td>{row.priority}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCard>
    </div>
  );
}

function ReportsPage(props: {
  rows: WorkspaceSnapshot["reports"];
  token: string | null;
}) {
  const [downloadState, setDownloadState] = useState<string | null>(null);

  async function downloadReport(path: string, filename: string) {
    if (!props.token) {
      setDownloadState("Exports autenticados ficam disponiveis quando a shell estiver em modo live.");
      return;
    }

    setDownloadState("Preparando arquivo...");

    try {
      const response = await fetch(`http://localhost:8000/api/v1${path}`, {
        headers: {
          Authorization: `Bearer ${props.token}`,
        },
      });

      if (!response.ok) {
        throw new Error();
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      window.URL.revokeObjectURL(url);
      setDownloadState("Arquivo exportado com sucesso.");
    } catch {
      setDownloadState("Nao foi possivel exportar o relatorio agora.");
    }
  }

  return (
    <div className="section-stack">
      <div className="support-grid">
        {props.rows.map((row) => (
          <article className="metric-card reveal-stagger" key={row.title}>
            <div className="eyebrow">{row.title}</div>
            <div className="metric-value">{row.value}</div>
            <p className="muted">{row.summary}</p>
            <div className="metric-trend">{row.footnote}</div>
          </article>
        ))}
      </div>

      <section className="panel reveal-stagger">
        <header>
          <div>
            <div className="eyebrow">Exports</div>
            <h2>Consumo executivo</h2>
          </div>
        </header>
        <div className="hero-actions">
          <button
            className="button"
            type="button"
            onClick={() =>
              void downloadReport("/reports/pipeline/export", "pipeline-report.csv")
            }
          >
            Exportar pipeline CSV
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() =>
              void downloadReport(
                "/reports/activities/export",
                "activities-report.csv",
              )
            }
          >
            Exportar atividades CSV
          </button>
        </div>
        {downloadState ? <p className="muted">{downloadState}</p> : null}
      </section>
    </div>
  );
}

function AdministrationPage(props: {
  rows: AdminRow[];
}) {
  return (
    <div className="section-stack">
      <div className="panel-grid">
        {props.rows.map((row) => (
          <article className="panel reveal-stagger" key={row.title}>
            <div className="eyebrow">Governanca</div>
            <h2>{row.title}</h2>
            <p className="muted">{row.description}</p>
            <div className="split-row">
              <span>{row.detail}</span>
              <span className={badgeTone(row.status)}>{row.status}</span>
            </div>
          </article>
        ))}
      </div>
      <section className="panel reveal-stagger">
        <header>
          <div>
            <div className="eyebrow">Expansao administrativa</div>
            <h2>Base pronta para fases seguintes</h2>
          </div>
        </header>
        <div className="support-grid">
          <FutureCard
            title="Campos customizados"
            copy="Espaco visual reservado para ADM-002 e catalogos mais ricos de configuracao."
          />
          <FutureCard
            title="Marketing ops"
            copy="Usuarios e permissoes poderao absorver automacoes, segmentos e campanhas."
          />
          <FutureCard
            title="Suporte e atendimento"
            copy="A mesma shell pode incorporar tickets, filas e SLAs sem reestruturar a navegacao."
          />
        </div>
      </section>
    </div>
  );
}

function MetricGrid(props: {
  metrics: Metric[];
}) {
  return (
    <section className="metric-grid">
      {props.metrics.map((item) => (
        <article className="metric-card reveal-stagger" key={item.label}>
          <div className="metric-label">{item.label}</div>
          <div className="metric-value">{item.value}</div>
          <div className="metric-trend">{item.trend}</div>
        </article>
      ))}
    </section>
  );
}

function TimelinePanel(props: {
  items: TimelineEvent[];
}) {
  return (
    <section className="panel reveal-stagger">
      <header>
        <div>
          <div className="eyebrow">Timeline</div>
          <h2>Ultimos sinais da operacao</h2>
        </div>
      </header>
      <div className="list">
        {props.items.map((item) => (
          <article className="timeline-item" key={`${item.title}-${item.stamp}`}>
            <div className="split-row">
              <strong>{item.title}</strong>
              <span className={badgeTone(item.status)}>{item.status}</span>
            </div>
            <p className="muted">{item.subtitle}</p>
            <div className="eyebrow">{item.stamp}</div>
          </article>
        ))}
      </div>
    </section>
  );
}

function FutureModulesPanel() {
  return (
    <section className="panel reveal-stagger">
      <header>
        <div>
          <div className="eyebrow">Roadmap</div>
          <h2>Preparacao para Fases 3 e 4</h2>
        </div>
      </header>
      <div className="support-grid">
        <FutureCard
          title="Marketing e leads"
          copy="Slot reservado para importacao, segmentacao, campanhas e medicao de origem."
        />
        <FutureCard
          title="Analytics operacional"
          copy="Estrutura pronta para dashboards transversais, cohorts e health score de pipeline."
        />
        <FutureCard
          title="Suporte e servicos"
          copy="A nave principal acomoda tickets, onboarding, SLAs e historico multicanal."
        />
      </div>
    </section>
  );
}

function Panel(props: {
  eyebrow: string;
  title: string;
  copy: string;
}) {
  return (
    <article className="panel reveal-stagger">
      <div className="eyebrow">{props.eyebrow}</div>
      <h2>{props.title}</h2>
      <p className="muted">{props.copy}</p>
    </article>
  );
}

function FutureCard(props: {
  title: string;
  copy: string;
}) {
  return (
    <article className="future-card">
      <strong>{props.title}</strong>
      <p className="muted">{props.copy}</p>
    </article>
  );
}

function TableCard(props: {
  title: string;
  eyebrow: string;
  copy: string;
  children: ReactNode;
}) {
  return (
    <section className="table-card reveal-stagger">
      <header>
        <div>
          <div className="eyebrow">{props.eyebrow}</div>
          <h2>{props.title}</h2>
          <p className="muted">{props.copy}</p>
        </div>
      </header>
      <div className="table-wrap">{props.children}</div>
    </section>
  );
}
