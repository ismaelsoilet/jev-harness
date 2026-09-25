# 📚 Central de Documentação do Jev Harness

**[ 🇬🇧 English ](README.md) | [ 🇧🇷 Português ](README.pt-BR.md)**

> **Bem-vindo ao catálogo central de documentação do `jev-harness`** — a camada de decisão determinística System 1.5, otimizador de tokens e barreira de proteção semântica para agentes autônomos de codificação.

---

## 🧭 Navegação por Papel e Objetivo

Encontre exatamente o que precisa com base no que você está construindo:

| Quero... | Documento Recomendado | Idioma | Descrição |
| :--- | :--- | :--- | :--- |
| **Plugar o Jev na minha IDE / agente** | [Guia Universal de Integração](AGENT_INTEGRATION_GUIDE.pt-BR.md) | [🇧🇷](AGENT_INTEGRATION_GUIDE.pt-BR.md) · [🇬🇧](AGENT_INTEGRATION_GUIDE.md) | Configuração pronta em 2 minutos para Cursor, Claude Code, Antigravity, OpenCode, Zed, Windsurf via MCP ou CLI. |
| **Entender a arquitetura System 1.5** | [Plano de Arquitetura System 1.5](system_1_5/SYSTEM_1_5_PLAN.md) | 🇧🇷 | Fatos auditados, modelo cognitivo (Kahneman Sistema 1 → 1.5 → 2) e fontes primárias. |
| **Comparar ferramentas do ecossistema** | [Ecossistema e Oportunidades](system_1_5/SYSTEM_1_5_OPPORTUNITIES.md) | 🇧🇷 | Comparativo direto com Foreman, JevRouter, Winnow e jev-guard. 21 oportunidades priorizadas. |
| **Inspecionar o roadmap de implementação** | [Plano de Implementação System 1.5](system_1_5/SYSTEM_1_5_IMPLEMENTATION.md) | 🇧🇷 | Horizontes faseados (H1 entregue na v0.2.0, H2, H3), critérios de aceite e contratos de teste. |
| **Supervisionar agentes com o Foreman** | [Guia de Integração com o Foreman](integrations/foreman.pt-BR.md) | [🇧🇷](integrations/foreman.pt-BR.md) · [🇬🇧](integrations/foreman.md) | Supervisão dual-loop, ponto de extensão nativo, detecção de estagnação e bundle de operador. |
| **Verificar benchmarks e calibração** | [Relatório de Replay e Benchmark](REPLAY_REPORT.md) | 🇬🇧 | Corpus rotulado de 160 casos, matriz de confusão, precisão/recall/F1 e calibração ECE. |
| **Conferir histórico de versões** | [Notas de Release v0.2.0](RELEASE_NOTES_v0.2.0.md) | 🇬🇧 | Entregas da versão v0.2.0 sincronizada nos 4 registries oficiais. |
| **Operar como agente neste repositório** | [Constituição do Agente de IA](../AGENTS.pt-BR.md) | [🇧🇷](../AGENTS.pt-BR.md) · [🇬🇧](../AGENTS.md) | Protocolo mandatório, postura de testes, registro de fronteira e regras de release Quad-Sync. |

---

## 📂 Estrutura de Documentação do Repositório

```
jev-harness/
├── README.md                          # 🏠 Visão geral e início rápido em inglês
├── README.pt-BR.md                    # 🇧🇷 Visão geral e início rápido em português
├── AGENTS.md                          # 🤖 Manual operacional para agentes de IA
├── AGENTS.pt-BR.md                    # 🇧🇷 Constituição de agentes em português
│
├── docs/                              # 📚 Esta Central de Documentação
│   ├── README.md                      # 🇬🇧 Mapa da documentação em inglês
│   ├── README.pt-BR.md                # 🇧🇷 Mapa da documentação em português (este arquivo)
│   ├── AGENT_INTEGRATION_GUIDE.md     # 🤖 Guia universal de integração (inglês)
│   ├── AGENT_INTEGRATION_GUIDE.pt-BR.md # 🇧🇷 Guia universal de integração (português)
│   ├── RELEASE_NOTES_v0.2.0.md        # 🚀 Notas de release e entregas
│   ├── NOTORIETY_PR_STRATEGY.md       # 📢 Estratégia de notoriedade e ecossistema
│   ├── REPLAY_REPORT.md               # 📊 Benchmark de calibração e matriz de confusão
│   ├── REPLAY_REPORT.json             # 🔢 Dataset bruto do replay
│   │
│   ├── system_1_5/                    # 🧠 Trilogia de Arquitetura System 1.5
│   │   ├── README.md                  # 🧭 Visão geral da trilogia e modelo cognitivo
│   │   ├── SYSTEM_1_5_PLAN.md         # 🏛️ Arquitetura-alvo e fatos verificados
│   │   ├── SYSTEM_1_5_OPPORTUNITIES.md # 🔭 Comparativo de ecossistema e 21 oportunidades
│   │   └── SYSTEM_1_5_IMPLEMENTATION.md # 🛠️ Plano de implementação faseado (H1–H3)
│   │
│   └── integrations/                  # 🔌 Integrações com Hosts e Runtimes
│       ├── foreman.md                 # 🏭 Integração com o supervisor Foreman (inglês)
│       └── foreman.pt-BR.md           # 🇧🇷 Integração com o Foreman (português)
│
└── .agents/rules/                     # 🛡️ Padrões Modulares de Engenharia
    ├── 01_project_blueprint.md        # Planta estrutural e layout tri-runtime
    ├── 02_software_engineering_principles.md # Princípios Karpathy, Fable, Kahneman
    ├── 03_model_governance_and_frontier_registry.md # Catálogo 2026 e safeguards
    ├── 04_testing_and_truthfulness.md # Zero-trust e bateria de 626 testes
    ├── 05_release_and_quad_sync_protocol.md # Protocolo de release nos 4 registries
    ├── 06_code_style_and_conventions.md # Padrões para Python, TypeScript e Rust
    └── 07_mcp_quality_and_tdqs_standards.md # Diretrizes MCP Glama TDQS A+ (5.0)
```

---

## 🏛️ O Paradigma System 1.5 em Resumo

O repositório implementa o paradigma cognitivo de Daniel Kahneman adaptado à engenharia de agentes autônomos:

- **System 1 (Rápido, Intuitivo, Tipado, Não-Autorregressivo)**: O **TypeSafe Jev System One** responde micro-decisões semânticas em 70–150ms remotos ou < 500µs locais, a um custo irrisório de **$0.042 por milhão de tokens**.
- **System 1.5 (Tecido Conjuntivo Determinístico e Governança Executiva)**: O **`jev-harness`** sanitiza tracebacks (redação de credenciais, corte em ≤15 linhas), detecta causas determinísticas instantaneamente, quebra doom loops circulares e calibra a incerteza para acionar o System 2 apenas quando necessário.
- **System 2 (Lento, Deliberativo, Generativo)**: Modelos de fronteira caros de 2026 (**GPT-6 Astra, Claude Fable 5.1, Claude Opus 5**) que projetam código e resolvem defeitos lógicos profundos. O System 1.5 garante economia de até **80% a 90% dos tokens de fronteira**.

---

## 🛠️ Referência dos Gates Semânticos de Decisão

O `jev-harness` expõe 6 gates semânticos nos 3 runtimes (Python, TypeScript e Rust), na CLI e via MCP:

| Nome do Gate | Comando CLI | Ferramenta MCP | Propósito Principal |
| :--- | :--- | :--- | :--- |
| **`triage_test_failure`** | `test-gate` | `jev_triage_test_failure` | Analisa falhas de testes e logs. Recomenda correção determinística (`skip_llm = true`) ou envia fatia filtrada para o LLM. |
| **`should_abort_trajectory`** | `abort-check` | `jev_check_abort` | Detecta loops destrutivos circulares e repetições mecânicas. Sai com código `1` para interromper o desperdício de tokens. |
| **`route_model_tier`** | `route` | `jev_route_task` | Direciona a complexidade da tarefa para o menor tier suficiente (script local → modelo flash → modelo de fronteira). |
| **`verify_step_completion`** | `verify` | `jev_verify_completion` | Avalia evidências e saídas contra critérios de aceite para impedir falsas alegações de conclusão. |
| **`modulate_reasoning_effort`** | `reasoning-effort` | `jev_modulate_reasoning_effort` | Modula dinamicamente o esforço de pensamento (`low` a `high`) por geração com base na complexidade e em leases multi-turn. |
| **`should_nudge_continuation`** | `nudge` | `jev_evaluate_nudge` | Avalia se um agente em fluxo multi-passos deve ser incentivado a continuar ou se deve encerrar com segurança. |

---

## 📜 Política de Manutenção e Frescor

Conforme a constituição do repositório ([`../AGENTS.pt-BR.md`](../AGENTS.pt-BR.md)):
1. **Garantia de Frescor**: Fatos comparativos, endpoints e métricas de ecossistema são auditados em no máximo 30 dias. Data da auditoria atual: **2026-09-23**.
2. **Verificação Automatizada de Links**: O repositório executa checagem de links offline determinística (`python3 scripts/check_links.py --root .`) integrada ao CI para assegurar zero links quebrados.
3. **Paridade Tri-Runtime Estrita**: Qualquer comportamento ou API documentado se aplica com idêntica semântica a Python, TypeScript e Rust.
