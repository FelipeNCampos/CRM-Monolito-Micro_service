# INF0463_2026/1 - Arquitetura de Software

## Atividade Supervisionada 02

**Projeto:** Gerenciador de relacionamento com Cliente (CRM) 

| Grupo 8 |
| -- |

|Aluno| Matrícula |
| -- | -- |
| Felipe Nunes Campos | 202403069 |


---

## 1. Contexto do projeto

O projeto do grupo e um CRM com foco no fluxo comercial principal, gestão de acesso, gestão de contatos e contas, oportunidades, pipeline de vendas, atividades, relatorios e auditoria. Pelos requisitos levantados, o sistema precisa:

- proteger dados comerciais e dados de acesso;
- sustentar o trabalho diario de vendedores e gestores;
- responder rapidamente em telas criticas como login, dashboard e pipeline;
- manter disponibilidade e rastreabilidade das operacoes;
- evoluir por fases, com estrutura de monolito modular preparada para migracao incremental a microservicos.

Com base nesse contexto, foi definida a hierarquia de criticidade dos atributos de qualidade da norma ISO/IEC 25010.

---

## 2. Hierarquia de criticidade dos atributos ISO/IEC 25010

Escala adotada: **1 = mais critico** e **8 = menos critico**, sempre no contexto deste projeto.

| Criticidade | Atributo de qualidade | Justificativa no contexto do CRM |
| --- | --- | --- |
| 1 | Seguranca | O CRM lida com credenciais, dados de clientes, oportunidades e trilhas de auditoria. Os requisitos de login, RBAC, recuperacao de senha e auditoria tornam esse o atributo mais sensivel. |
| 2 | Adequacao funcional | Se o sistema nao representar corretamente o processo comercial principal (contatos, contas, oportunidades, pipeline, relatorios), ele perde seu valor para o negocio. |
| 3 | Confiabilidade | O time de vendas depende do CRM para operar e consultar historicos. Indisponibilidade, perda de dados ou comportamento inconsistente comprometem a operacao. |
| 4 | Eficiencia de desempenho | Ha requisitos explicitos de resposta em ate 3 segundos nas telas principais e atualizacao quase em tempo real de dashboard e pipeline. |
| 5 | Manutenibilidade | O projeto sera evoluido por fases, possui modulos distintos e ja nasce com intencao de futura migracao incremental para microservicos. |
| 6 | Usabilidade | O CRM sera usado continuamente por vendedores, gestores e administradores. Fluxos simples, filtros, feedbacks claros e navegacao objetiva impactam a adocao. |
| 7 | Compatibilidade | Integracoes com e-mail, importacao/exportacao CSV e convivencia com outros sistemas sao importantes, mas nao mais urgentes que os atributos acima. |
| 8 | Portabilidade | O sistema deve ser implantavel em ambientes distintos, mas isso ja e relativamente favorecido pelo uso de Docker e configuracao por ambiente, sendo menos critico no momento. |


