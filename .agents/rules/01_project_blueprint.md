# 🏛️ Planta Arquitetural Completa: Jev Harness

> **Documento Oficial de Engenharia — Versão do Projeto: v0.2.0**  
> *Obrigatório para todos os agentes autônomos e desenvolvedores que operam no repositório.*

---

## 1. Visão Geral do Sistema

O `jev-harness` é um **harness de decisão não-autorregressiva (System One), otimizador de tokens e barreira de proteção semântica** para agentes autônomos de codificação (OpenCode, Command Code, Cursor, Claude Code, Antigravity IDE, Windsurf, Zed e Pi).

Ele aplica o paradigma cognitivo de Daniel Kahneman à engenharia de agentes:
* **System 1 (Rápido, Intuitivo, Tipado, Não-Autorregressivo)**: O Jev toma micro-decisões semânticas em **< 500µs localmente** ou **70ms a 150ms remotamente**, com custo de **$0.042 por 1 milhão de tokens de entrada e $0.00 por tokens de saída**.
* **System 2 (Lento, Deliberativo, Generativo)**: Modelos de fronteira caros e pesados de 2026 (**GPT-6 Astra**, **Claude Fable 5.1 / Claude Opus 5**, **DeepSeek-V4-Pro**, **Qwen 3.8 Max**) que geram código e resolvem problemas de arquitetura profunda.

```
       ┌────────────────────────────────────────────────────────┐
       │                 AI Coding Agent Loop                   │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                       Command/Test Execution
                                  │
                                  ▼
                         [Test / Step Output]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
   [PASS: Continue]                                 [FAIL: Error Log]
                                                           │
                                                           ▼
                                               ┌───────────────────────┐
                                               │   jev-harness gate    │
                                               │ (Jev System One 70ms) │
                                               └───────────┬───────────┘
                                                           │
                        ┌──────────────────────────────────┴──────────────────────────────────┐
                        ▼                                                                     ▼
             [skip_llm = True]                                                         [skip_llm = False]
      (Env missing / Flaky / Trivial)                                                    (Deep Logic Bug)
                        │                                                                     │
                        ▼                                                                     ▼
           Deterministic Shell Action                                                 Dispatch Targeted
        (pip/npm install or fast retry)                                            Trace to Frontier LLM
     ⚡ 0 Frontier Tokens / Instant Fix                                          💸 Cost Reduced by ~80%
```

---

## 2. Mapa Estrutural do Repositório (Árvore de Código)

O repositório é estritamente organizado em uma arquitetura monorepo unificada com **paridade tri-runtime** (Python, TypeScript e Rust):

```
jev-harness/
├── .agents/                          # Diretrizes e convenções obrigatórias para agentes de IA
│   └── rules/
│       ├── 01_project_blueprint.md                 # Esta planta arquitetural
│       ├── 02_software_engineering_principles.md    # Princípios Karpathy, Fable, Kahneman
│       ├── 03_model_governance_and_frontier_registry.md # Registro oficial de modelos 2026 e safeguards
│       ├── 04_testing_and_truthfulness.md          # Postura anti-viés e política de testes exaustivos
│       ├── 05_release_and_quad_sync_protocol.md    # Protocolo de 4 locais (GitHub, PyPI, npm, Crates.io)
│       └── 06_code_style_and_conventions.md        # Estilo de código e convenções por linguagem
├── .github/                          # Workflows do GitHub Actions
│   └── workflows/
│       ├── ci.yml                    # CI multi-runtime (Python 3.9-3.13, Node 18-22, Rust stable)
│       └── release.yml               # CD automatizado para PyPI, npm (OIDC Sigstore) e Crates.io
├── examples/                         # Exemplos executáveis e receitas de integração
│   └── astra_jev/
│       ├── codex_recipe.py           # Receita para OpenAI Codex / GPT-6 Astra
│       └── deepseek_qwen_recipe.py   # Receita para DeepSeek e Alibaba Qwen
├── packages/
│   ├── rust/                         # Crate oficial e CLI nativa em Rust (`jev` e `jev-harness`)
│   │   ├── Cargo.toml                # Manifesto do pacote Rust
│   │   ├── Cargo.lock
│   │   ├── README.md                 # Documentação oficial do crate no docs.rs e crates.io
│   │   ├── src/
│   │   │   ├── bin/
│   │   │   │   ├── jev.rs            # Binário CLI ultra-leve `jev`
│   │   │   │   └── jev_harness.rs    # Binário CLI alias `jev-harness`
│   │   │   ├── cli.rs                # Parser CLI standalone em Rust
│   │   │   ├── client.rs             # Cliente HTTP Tokio e simulação heurística local
│   │   │   ├── config.rs             # Carregador do .jev.json (modelo, thresholds e cache)
│   │   │   ├── gates.rs              # Implementação de todos os gates semânticos
│   │   │   ├── lib.rs                # Ponto de exportação público da biblioteca Rust
│   │   │   ├── mcp.rs                # Servidor MCP stdio nativo em Rust
│   │   │   └── types.rs              # Tipos estruturados e respostas tipadas
│   │   └── tests/
│   │       ├── gates_test.rs         # Gates semânticos, dialetos e safeguards (49 testes, 100% pass)
│   │       ├── live_payload_parity_test.rs  # Fixture live compartilhado (parser Score; 2 testes)
│   │       ├── mock_golden_test.rs          # Vetores golden da mock (paridade 1e-9 com Python/TS)
│   │       ├── triage_parity_test.rs        # Trava de paridade de veredito sobre o corpus (112 casos)
│   │       ├── model_resolution_test.rs     # Pin/origem de modelo e precedência do shadow (6 testes)
│   │       ├── provider_resilience_test.rs  # Retry/Retry-After e payload malformado, TCP real (12 testes)
│   │       └── shadow_and_limits_test.rs    # Shadow mode e limites de payload (4 testes)
│   └── ts/                           # Pacote oficial npm (`@ismaelsoilet/jev-harness`)
│       ├── package.json              # Manifesto do pacote npm
│       ├── package-lock.json
│       ├── tsconfig.json             # Configuração TypeScript de produção
│       ├── tsconfig.test.json        # Configuração de testes Node.js nativos
│       ├── bin/
│       │   └── cli.js                # Entrypoint executável via `npx`
│       ├── src/
│       │   ├── cli.ts                # Parser CLI em TypeScript
│       │   ├── client.ts             # Cliente fetch nativo e simulação heurística
│       │   ├── config.ts             # Carregador do .jev.json (modelo, thresholds e cache)
│       │   ├── gates.ts              # Implementação dos gates semânticos
│       │   ├── index.ts              # Exportações do pacote
│       │   ├── mcp.ts                # Servidor MCP stdio nativo em TypeScript
│       │   └── types.ts              # Interfaces TypeScript tipadas
│       └── tests/
│           ├── gates.test.ts         # Gates semânticos, provedores e safeguards (45 testes, 100% pass)
│           ├── live_payload.test.ts  # Fixture live compartilhado (parser Score; 1 teste)
│           ├── mock_golden.test.ts   # Vetores golden da mock (paridade 1e-9 com Python/Rust)
│           ├── triage_parity.test.ts # Trava de paridade de veredito sobre o corpus (112 casos)
│           ├── resilience.test.ts    # Retry/Retry-After, fail-open/fail-closed, payload malformado (16 testes)
│           └── shadow_and_limits.test.ts  # Shadow mode, limites, pin de modelo (10 testes)
├── src/
│   └── jev_harness/                  # Pacote oficial Python (`pip install jev-harness`)
│       ├── __init__.py               # Metadados e exports públicos
│       ├── cli.py                    # CLI em Python com argparse
│       ├── client.py                 # Cliente urllib (zero dependências) e simulação
│       ├── config.py                 # Carregador do .jev.json (modelo, thresholds e cache)
│       ├── cache.py                  # Cache de decisão por hash + debounce (E3.2/E3.3)
│       ├── doctor.py                 # Autodiagnóstico OK/AVISO/FALHA com correção (E2.4)
│       ├── gates.py                  # Gates semânticos (triage, abort, route, verify, reasoning-effort, nudge)
│       ├── mcp_server.py             # Servidor MCP stdio universal (`jev-mcp`)
│       ├── receipts.py               # Trilha de auditoria append-only + higiene do `.jev/` (E1.3/E3.8)
│       ├── replay.py                 # Corpus, matriz de confusão, ECE e gate de regressão (E1.2)
│       └── session.py                # Telemetria, persistência de sessão e lock de concorrência
├── tests/                            # Bateria de testes Python (393 testes, 100% pass)
│   ├── corpus/                       # Corpus rotulado de calibração (160 casos; ver README do diretório)
│   ├── test_adversarial.py           # Testes adversariais, concorrência, negação, emojis UTF-8
│   ├── test_config.py                # Testes do .jev.json (modelo, thresholds, clamp, corrompido)
│   ├── test_cli.py                   # Testes de argumentos CLI e códigos de saída
│   ├── test_client.py                # Testes de cliente e perguntas tipadas
│   ├── test_gates.py                 # Testes unitários dos gates semânticos
│   ├── test_live_payload_parity.py   # Fixture live compartilhado com TS/Rust (parser Score)
│   ├── test_mcp.py                   # Testes do protocolo MCP Server
│   ├── test_provider_resilience.py   # Retry/Retry-After, fail-open/fail-closed, payload malformado
│   ├── test_real_tracebacks.py       # Testes com tracebacks reais (Python, Go, Node, Rust)
│   ├── test_cache.py                 # Cache por hash, debounce, hit-rate e shadow nunca cacheia
│   ├── test_doctor.py                # Diagnóstico: config, credenciais, estado, hook, --live
│   ├── test_github_action.py         # Action de CI: verde nunca bloqueia, fail-on opt-in
│   ├── test_measured_usage.py        # Custo/tokens medidos vs estimativa heurística
│   ├── test_mock_golden.py           # Vetores golden da mock (paridade 1e-9 com TS/Rust)
│   ├── test_receipts.py              # Recibos, retenção e higiene de .gitignore
│   ├── test_replay.py                # Corpus, métricas e o gate de regressão
│   ├── test_shadow_and_limits.py     # Shadow mode, limites de payload e pin de modelo
│   └── fixtures/                     # Payloads live gravados (contrato tri-runtime)
├── pyproject.toml                    # Configuração de build Python Hatchling
├── README.md                         # Documentação global oficial do repositório
├── AGENTS.md                         # Ponto de entrada obrigatório para agentes de IA
├── LICENSE                           # Licença MIT
└── scripts/
    ├── jev_test_gate_hook.sh         # Wrapper do hook pre-commit (runner decide, Jev aconselha)
    └── release.sh                    # Script mestre de release, check (569 testes) e sync
```

---

## 3. Os 5 Gates Semânticos do Jev Harness

| Gate | Função Principal | Saída Típica | Benefício Chave |
| :--- | :--- | :--- | :--- |
| **`triage_test_failure`** (`test-gate`) | Triagem de falhas de teste ou execução em logs de terminal | `skip_llm: bool`, `category`, `action_recommendation` | Evita gastar tokens de LLM em `ModuleNotFoundError`, pacotes ausentes ou erros transitórios de rede. |
| **`should_abort_trajectory`** (`abort-check`) | Guardião contra loops destrutivos e repetições circulares | `should_abort: bool`, `action`, `abort_probability` | Detecta doom loops e aciona `exit 1` no CI ou agente antes de queimar orçamento. |
| **`route_model_tier`** (`route`) | Roteamento de inteligência para o menor tier suficiente | `selected_tier`, `recommended_model`, `complexity_score` | Envia tarefas triviais para scripts locais/determínicos e reserva modelos de fronteira para arquitetura. |
| **`verify_step_completion`** (`verify`) | Verificação formal de evidências contra critérios de aceite | `is_verified: bool`, `needs_rework: bool`, `confidence` | Impede falsas alegações de conclusão de tarefa por agentes. |
| **`modulate_reasoning_effort`** (`reasoning-effort` / `astra-jev`) | Modulação dinâmica de reasoning effort por geração (Astra-Jev) | `effort`, `provider_params`, `cache_safe_recommendation` | Economiza até $1.20 por passo mecânico em modelos ocidentais e corta até 4 minutos de latência em modelos chineses. |

---

## 4. O Contrato Sagrado: Zero Dependências Externas no Core

Para que o `jev-harness` possa ser injetado em qualquer contêiner Docker, pipeline de CI minimalista ou ambiente de agente sem conflito de dependências:
1. **Python**: Usa estritamente a biblioteca padrão (`urllib.request`, `json`, `re`, `dataclasses`, `time`, `os`, `sys`, `argparse`). **Nenhum `requests`, `httpx` ou `pydantic` é permitido no core.**
2. **TypeScript**: Usa módulos nativos de `node:` (`node:http`, `node:https`, `node:fs`, `node:path`, `node:url`) e `fetch` padrão. **Zero dependências de runtime no `package.json`.**
3. **Rust**: Usa apenas crates essenciais de infraestrutura (`tokio`, `serde`, `serde_json`, `regex`). Compila para binário nativo estático com startup de **< 500µs**.
