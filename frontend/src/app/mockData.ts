import type { WorkspaceSnapshot } from "./types";

export const demoSnapshot: WorkspaceSnapshot = {
  mode: "demo",
  heroTitle: "Central operacional preparada para a Fase 2.",
  heroCopy:
    "Um workspace unico para vendas, operacao e governanca, com estrutura pronta para crescer com marketing, suporte e observabilidade nas fases 3 e 4.",
  heroHighlights: [
    "Navegacao organizada por dominio e preparada para novos modulos.",
    "Camada de dados desacoplada para alternar entre API real e modo demonstracao.",
    "Superficie neutra e executiva, com animacoes sutis usando Anime.js."
  ],
  metrics: [
    { label: "Contatos ativos", value: "148", trend: "+12 na semana" },
    { label: "Contas em carteira", value: "63", trend: "9 com hierarquia ativa" },
    { label: "Pipeline aberto", value: "R$ 2,48 mi", trend: "4 estagios com forecast" },
    { label: "Atividades pendentes", value: "27", trend: "8 follow-ups atrasados" }
  ],
  timeline: [
    {
      title: "Relatorio de pipeline consolidado",
      subtitle: "Exportacao pronta para lideranca comercial.",
      stamp: "Atualizado agora",
      status: "success"
    },
    {
      title: "Follow-ups com atraso",
      subtitle: "Priorize os 8 itens vencidos do time seller.",
      stamp: "Ha 12 minutos",
      status: "warning"
    },
    {
      title: "Roadmap da Fase 3",
      subtitle: "Estrutura pronta para marketing, segmentacao e campanhas.",
      stamp: "Planejamento ativo",
      status: "neutral"
    }
  ],
  contacts: [
    {
      id: "c-01",
      name: "Marina Farias",
      email: "marina@northwave.com",
      phone: "+55 11 97777-9080",
      source: "Inbound",
      owner: "Equipe Comercial",
      status: "Ativo"
    },
    {
      id: "c-02",
      name: "Roberto Nunes",
      email: "roberto@altacorp.com",
      phone: "+55 21 98888-1200",
      source: "Evento",
      owner: "Gestor",
      status: "Qualificado"
    },
    {
      id: "c-03",
      name: "Camila Torres",
      email: "camila@montana.io",
      phone: "+55 31 96666-4401",
      source: "Importacao",
      owner: "SDR",
      status: "Nutrir"
    }
  ],
  accounts: [
    {
      id: "a-01",
      name: "Northwave Holdings",
      segment: "Industria",
      size: "Enterprise",
      owner: "Equipe Comercial",
      status: "Ativa"
    },
    {
      id: "a-02",
      name: "AltaCorp",
      segment: "Servicos",
      size: "Media",
      owner: "Gestor",
      status: "Ativa"
    },
    {
      id: "a-03",
      name: "Montana Labs",
      segment: "Tecnologia",
      size: "Pequena",
      owner: "SDR",
      status: "Expansao"
    }
  ],
  opportunities: [
    {
      id: "o-01",
      title: "Expansao Northwave",
      stage: "Diagnostico",
      account: "Northwave Holdings",
      owner: "Equipe Comercial",
      value: "R$ 420.000",
      status: "Active"
    },
    {
      id: "o-02",
      title: "Renovacao AltaCorp",
      stage: "Proposta",
      account: "AltaCorp",
      owner: "Gestor",
      value: "R$ 180.000",
      status: "Won"
    },
    {
      id: "o-03",
      title: "Piloto Montana",
      stage: "Validacao",
      account: "Montana Labs",
      owner: "SDR",
      value: "R$ 75.000",
      status: "Active"
    }
  ],
  stages: [
    {
      id: "s-01",
      name: "Diagnostico",
      probability: "25%",
      count: 2,
      totalValue: "R$ 495.000",
      opportunities: [
        {
          id: "o-01",
          title: "Expansao Northwave",
          stage: "Diagnostico",
          account: "Northwave Holdings",
          owner: "Equipe Comercial",
          value: "R$ 420.000",
          status: "Active"
        },
        {
          id: "o-04",
          title: "Discovery Atlas",
          stage: "Diagnostico",
          account: "Atlas Group",
          owner: "Seller 02",
          value: "R$ 75.000",
          status: "Active"
        }
      ]
    },
    {
      id: "s-02",
      name: "Validacao",
      probability: "55%",
      count: 1,
      totalValue: "R$ 75.000",
      opportunities: [
        {
          id: "o-03",
          title: "Piloto Montana",
          stage: "Validacao",
          account: "Montana Labs",
          owner: "SDR",
          value: "R$ 75.000",
          status: "Active"
        }
      ]
    },
    {
      id: "s-03",
      name: "Proposta",
      probability: "80%",
      count: 1,
      totalValue: "R$ 180.000",
      opportunities: [
        {
          id: "o-02",
          title: "Renovacao AltaCorp",
          stage: "Proposta",
          account: "AltaCorp",
          owner: "Gestor",
          value: "R$ 180.000",
          status: "Won"
        }
      ]
    }
  ],
  activities: [
    {
      id: "ac-01",
      title: "Ligacao de qualificacao",
      kind: "Atividade",
      status: "Concluida",
      owner: "Equipe Comercial",
      dueLabel: "Hoje, 10:00",
      priority: "Media"
    },
    {
      id: "ac-02",
      title: "Follow-up de proposta",
      kind: "Tarefa",
      status: "Pendente",
      owner: "Gestor",
      dueLabel: "Atrasada ha 1 dia",
      priority: "Alta"
    },
    {
      id: "ac-03",
      title: "Envio de recap",
      kind: "Tarefa",
      status: "Planejada",
      owner: "SDR",
      dueLabel: "Amanha, 09:00",
      priority: "Baixa"
    }
  ],
  reports: [
    {
      title: "Sales dashboard",
      summary: "Leitura executiva de pipeline, forecast e conversao.",
      value: "50,0%",
      footnote: "Taxa de conversao de negocios fechados."
    },
    {
      title: "Pipeline por estagio",
      summary: "Distribuicao do funil com exportacao para CSV.",
      value: "R$ 2,48 mi",
      footnote: "Valor total mapeado no pipeline ativo."
    },
    {
      title: "Volume de atividades",
      summary: "Acompanhamento de tarefas, concluidas e produtividade por owner.",
      value: "3,6",
      footnote: "Atividades por oportunidade no periodo."
    }
  ],
  administration: [
    {
      title: "Usuarios e papeis",
      description: "RBAC e governanca operacional para toda a equipe.",
      detail: "4 perfis padrao com seeds e auditoria.",
      status: "ok"
    },
    {
      title: "Estagios do pipeline",
      description: "Configuracao administrativa da operacao comercial.",
      detail: "Criacao, reordenacao e desativacao controlada.",
      status: "ok"
    },
    {
      title: "Campos personalizados",
      description: "Preparado para a proxima entrega administrativa.",
      detail: "ADM-002 ainda em backlog tecnico.",
      status: "attention"
    }
  ]
};
