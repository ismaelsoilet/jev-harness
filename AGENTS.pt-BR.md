# 🤖 AGENTS.md: Constituição e Manual Operacional para Agentes de IA

**[ 🇬🇧 English ](AGENTS.md) | [ 🇧🇷 Português ](AGENTS.pt-BR.md)**

> **ATENÇÃO:** TODO agente autônomo de inteligência artificial (Claude Code, OpenAI Codex / Astra-Codex, Pi, Oh My Pi, CommandCode, Cursor, Antigravity IDE, OpenCode, Windsurf, Zed, Devin, Aider) que abrir este repositório **DEVE LER ESTE DOCUMENTO OBRIGATORIAMENTE** antes de planejar, modificar código ou executar alterações.
> 
> *Versão do Projeto: v0.1.6 — Sincronizado nos 4 registries oficiais.*

---

## 🧭 Índice Rápido de Convenções e Regras Modulares

Este documento é o portal de entrada. O repositório organiza suas convenções em documentos especializados e auto-contidos no diretório [`.agents/rules/`](.agents/rules/):

1. 🏛️ **[Planta Arquitetural Completa](.agents/rules/01_project_blueprint.md)**: Mapeamento de pastas, runtimes (Python, TS, Rust), fluxos de dados e contratos de zero dependências.
2. 🧠 **[Princípios Essenciais de Engenharia](.agents/rules/02_software_engineering_principles.md)**: Princípios Karpathy, Fable Loop, Kahneman Sistema 1 vs 2, Filosofia Unix e Arquitetura Anti-Frankenstein.
3. 🌐 **[Governança de Modelos e Catálogo de Fronteira 2026](.agents/rules/03_model_governance_and_frontier_registry.md)**: Regra de ouro contra modelos obsoletos, pesquisa web mandatória diária, dialetos e safeguards para modelos direct.
4. 🛡️ **[Testes Exaustivos e Honestidade Absoluta](.agents/rules/04_testing_and_truthfulness.md)**: Postura de zero-trust, proibição de testes tautológicos, bateria de 109 testes.
5. 🚀 **[Protocolo de Release e Sincronização Quad-Sync](.agents/rules/05_release_and_quad_sync_protocol.md)**: Pipeline síncrono nos 4 registries (GitHub, PyPI, npm, Crates.io).
6. 📝 **[Convenções de Código por Linguagem](.agents/rules/06_code_style_and_conventions.md)**: Padrões estritos para Python (stdlib pura), TypeScript (ESM nativo) e Rust (Tokio 2021).
7. 🤖 **[Guia de Implementação Rápida para Agentes em Qualquer Projeto](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md)** ([English](docs/AGENT_INTEGRATION_GUIDE.md)): Como plugar o Jev Harness via MCP, CLI ou SDK nativo no seu projeto em 2 minutos.

---

## 🏛️ 1. Planta de Todo o Projeto (System Blueprint)

O `jev-harness` resolve o problema mais custoso da computação com agentes: **o desperdício de tokens de fronteira em problemas mecânicos triviais e em loops circulares**.

### Arquitetura Tri-Runtime com Paridade Semântica Estrita:
* **Python Core (`src/jev_harness/`)**:
  - `client.py`: Cliente HTTP ultra-resiliente com biblioteca padrão pura (`urllib.request`), timeout dinâmico e simulação heurística offline em **< 500µs**.
  - `gates.py`: Implementação dos 5 gates de decisão semântica (`triage_test_failure`, `should_abort_trajectory`, `route_model_tier`, `verify_step_completion`, `modulate_reasoning_effort`).
  - `mcp_server.py`: Servidor stdio MCP universal para integração direta com Cursor, Claude Desktop e Antigravity IDE.
  - `cli.py`: Interface de linha de comando (`jev-harness`) em conformidade estrita com pipes Unix.
  - `session.py`: Telemetria de sessão, cálculo de ROI e proteção de cache.
* **Rust Crate (`packages/rust/`)**:
  - Implementação de alta performance em Rust estável (Tokio + Serde), provendo a biblioteca `jev_harness` e os binários CLI standalone `jev` e `jev-harness`.
* **TypeScript Package (`packages/ts/`)**:
  - Pacote npm nativo `@ismaelsoilet/jev-harness` com suporte a Node.js, Bun e Deno, exportando SDK tipado e CLI executável via `npx`.

---

## 🧠 2. Princípios Essenciais da Engenharia de Software

Todo agente que operar neste repositório deve pautar suas decisões por cinco pilares inegociáveis:

### 1. Princípios Karpathy para Codificação com LLMs
* **Pense Antes de Codificar (*Think Before Coding*)**: Não assuma. Não esconda confusões. Declare suposições e trade-offs antes de aplicar edições.
* **Simplicidade em Primeiro Lugar (*Simplicity First*)**: Código mínimo que resolve o problema atual com excelência. Zero código especulativo. Sem padrões complexos (Factory, Strategy) para um único caso de uso.
* **Alterações Cirúrgicas (*Surgical Changes*)**: Toque estritamente no que foi solicitado. Proibido refatorar, reformatar ou trocar aspas em código adjacente fora de escopo.
* **Execução Guiada por Metas (*Goal-Driven*)**: Transforme tarefas em critérios de sucesso verificáveis. Ao corrigir um bug, reproduza-o com um teste antes de implementar o patch.

### 2. Honestidade Absoluta e Postura Zero-Trust
* **NUNCA CONFIE CEGAMENTE, SEMPRE TESTE E VERIFIQUE.**
* **SE ACHAR ALGO ESTRANHO, VERIFIQUE E INVESTIGUE ATÉ A RAIZ.**
* Proibição total de alegações de conclusão falsas ou infladas (*Zero False Completion Claims*). Relate os resultados observados nos comandos reais antes de qualquer conclusão.

### 3. Filosofia Unix e Composição de Ferramentas
* Códigos de saída semânticos:
  - `0`: Sucesso / Ação determinística identificada (`skip_llm = true`).
  - `1`: Falha lógica profunda (`skip_llm = false`) ou aborto recomendado (`should_abort = true`).
  - `2`: Erro de sintaxe ou uso incorreto de argumentos no CLI.

### 4. Zero Dependências Externas no Core (Princípio Anti-Frankenstein)
* O core de `jev-harness` **NUNCA** deve incorporar dependências de runtime pesadas no Python (`requests`, `pydantic`, `httpx` são proibidos) ou no TypeScript (zero `dependencies`).
* **Nenhum proxy HTTP reverso** deve ser incluído no core. A compilação de parâmetros do Astra-Jev é limpa, tipada e estática via `build_provider_params`.

---

## 🌐 3. Regra Mandatória de Modelos de IA: Proibição de Dados Defasados

> [!CAUTION]
> **REGRA MANDATÓRIA DE FRONTEIRA:** É terminantemente proibido citar ou usar modelos antigos/defasados (GPT-3.5, GPT-4, Gemini 1.0/1.5, Claude 2/3.0) como referências de modelos de ponta.

1. **Pesquisa Web Ativa Obrigatória com Data Registrada**: Modelos de IA e seus parâmetros mudam semanalmente. Sempre pesquise na web (`search_web`) antes de citar qualquer modelo e registre explicitamente a **data da pesquisa** na documentação. Informações sem 100% de verificação ou projeções de lançamentos futuros que ainda não ocorreram (como supostas versões Opus 5.2 ou 5.5) são **terminantemente proibidas** de serem listadas como ativas.
2. **Catálogo Oficial de Fronteira (Verificado via Pesquisa Web em 22 de setembro de 2026)**:
   * **OpenAI / Codex**: `gpt-6-astra`, `o3-mini`, `codex` (`reasoning_effort: "low" | "medium" | "high"`).
   * **Anthropic**: `claude-fable-5.1` (lançado em 01/09/2026), `claude-opus-5` (lançado em 24/07/2026) (`thinking: { type: "adaptive" }`). *(Nota de Governança: Claude Opus 5 é o modelo mais recente lançado da linha Opus; versões 5.2 e 5.5 ainda não foram lançadas e não devem ser listadas como disponíveis)*.
   * **DeepSeek**: `deepseek-v4.1-flash`, `deepseek-v4-pro`, `r1` (`extra_body.thinking: enabled`, preservando `reasoning_content`).
   * **Alibaba DashScope**: `qwen-3.8-max` (2.4T MoE), `qwen-3.8-omni-flash` (`enable_thinking: false` vs `true`).
   * **Google Gemini**: `gemini-3.8-flash-thinking`, `gemini-3.5-pro` (`thinking_config.thinking_level`).
   * **Moonshot**: `kimi-k3` (`extra_body: { thinking: false }` modo instantâneo).
   * **Xiaomi**: `mimo-v2.6-pro`, `mimo-v2-flash` (`thinking: { type: "disabled" | "enabled" }`).
3. **Safeguard para Modelos Direct**: Modelos single-pass (`gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `claude-3-5-haiku`, `llama-3.3`, etc.) que rejeitam parâmetros com HTTP 400 são detectados automaticamente, gerando `{}` e `is_reasoning_supported = false`.
4. **Governança do Prompt Cache (KV Cache)**: Não altere o histórico de mensagens para injetar metadados de raciocínio. Injete estritamente no nível raiz do payload da API para preservar o cache de prefixo das GPUs.

---

## 🚀 4. Protocolo Rígido de Release e Verificação Pré-Push (Quad-Sync)

> [!CAUTION]
> **REGRA DE OURO INVIOLÁVEL DE PRÉ-PUSH:** É expressamente proibido a qualquer agente ou desenvolvedor realizar `git push` (de commits ou tags) sem antes executar a verificação obrigatória de paridade de versões:
> ```bash
> ./scripts/release.sh --verify-sync
> ```
> Se houver qualquer divergência entre `pyproject.toml`, `packages/ts/package.json`, `packages/rust/Cargo.toml` ou `src/jev_harness/__init__.py`, o push é **sumariamente abortado**.

### Fluxo Completo de Release em 6 Etapas:

```
[Alteração de Código ou Docs]
        │
        ▼
[1. Executar 109 Testes: ./scripts/release.sh --check]
        │ (Se 100% OK)
        ▼
[2. Bump Síncrono de Versão: ./scripts/release.sh --bump <versao>]
        │
        ▼
[3. Recompilar Artefatos: npm run build (TS) & cargo build --release (Rust)]
        │
        ▼
[4. Verificação Rígida de Paridade: ./scripts/release.sh --verify-sync]
        │ (Se 100% OK)
        ▼
[5. Commit Detalhado + Git Tag + Git Push origin main --tags]
        │
        ▼
[6. Criação e Polimento do GitHub Release + Monitoramento Ativo]:
    - Criar Release via `gh release create v<versao>` com notas limpas e profissionais
    - Proibição de espaçamentos defeituosos em markdown ou textos descuidados
    - Acompanhar GitHub Actions (`gh run list --workflow=release.yml`) até conclusão verde
    - Validar disponibilidade nos 4 canais:
        1. GitHub: https://github.com/ismaelsoilet/jev-harness/releases
        2. PyPI: https://pypi.org/project/jev-harness/
        3. npm: https://www.npmjs.com/package/@ismaelsoilet/jev-harness
        4. Crates.io: https://crates.io/crates/jev-harness
```

> [!IMPORTANT]
> **PROIBIÇÃO DE BUMPS ÓRFÃOS E BADGES DESALINHADOS:**
> 1. É proibido alterar versão em arquivos manifestos sem criar a tag git (`vX.Y.Z`) e o respectivo release no GitHub. O repositório nunca deve exibir commits de versão nova com a release anterior marcada como "Latest".
> 2. Os badges no topo do `README.md` devem refletir com precisão e elegância o estado publicado nos 4 registries. Nunca permita badges quebrados, com versões antigas em cache ou links inválidos.

---

## 🧹 5. Manutenção e Higiene do Repositório

O repositório deve permanecer impecavelmente limpo:
* **Zero arquivos temporários**: Nunca faça commit de `*.log`, `*.tmp`, diretórios de cache ou arquivos de rascunho.
* **Exemplos atualizados**: Mantenha as receitas em `examples/` sincronizadas com as versões atuais das APIs.
* **Documentação Viva**: Ao alterar qualquer assinatura de função nos gates semânticos, atualize imediatamente a documentação em todos os READMEs e nas regras de `.agents/rules/`.

---

## 🤖 7. Como Implementar o Jev Harness no Seu Projeto (Playbook para Agentes)

Para implementar o `jev-harness` em **qualquer projeto externo** e impedir que agentes de IA queimem 50.000+ tokens em erros triviais ou travem em loops circulares:

Consulte o nosso guia completo pronto para cópia e cola:
* 📖 **[Guia de Integração Universal para Agentes (Português)](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md)**
* 📖 **[Universal AI Agent Integration Guide (English)](docs/AGENT_INTEGRATION_GUIDE.md)**

### Resumo em 3 Passos para Qualquer Projeto:
1. **Configurar o Servidor MCP**: Adicione `"jev-harness": { "command": "npx", "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"] }` no seu `.cursor/mcp.json` ou `claude_desktop_config.json`.
2. **Encadear Testes no Shell**: Execute `pytest 2>&1 | jev-harness test-gate` ou `npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate`. Se o código de saída for `0` (`skip_llm = true`), aplique a correção determinística sem consultar o LLM.
3. **Injetar Regras no Agente**: Cole as instruções de `.cursorrules`, `CLAUDE.md` ou `AGENTS.md` fornecidas no guia para tornar a disciplina de tokens automática.
