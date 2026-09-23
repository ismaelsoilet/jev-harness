# ⚡ Jev Harness: Otimizador de Tokens e Decision Gate para Agentes de Codificação com IA

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="Status da CI"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/tests-569%20passed-brightgreen.svg?logo=githubactions&logoColor=white" alt="Testes Passando"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/releases"><img src="https://img.shields.io/github/v/release/ismaelsoilet/jev-harness?color=teal&logo=github&logoColor=white&cacheSeconds=0" alt="Versão no GitHub Release"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=0" alt="Versão no PyPI"></a>
  <a href="https://www.npmjs.com/package/@ismaelsoilet/jev-harness"><img src="https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white&cacheSeconds=0" alt="Versão no npm"></a>
  <a href="https://crates.io/crates/jev-harness"><img src="https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white&cacheSeconds=0" alt="Versão no crates.io"></a>
  <a href="https://docs.rs/jev-harness"><img src="https://docs.rs/jev-harness/badge.svg" alt="docs.rs"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab.svg?logo=python&logoColor=white" alt="Versões do Python"></a>
  <a href="https://search.sigstore.dev/?logIndex=2908239242"><img src="https://img.shields.io/badge/provenance-Sigstore-blue?logo=npm" alt="npm Provenance"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="Licença MIT"></a>
  <a href="https://typesafe.ai"><img src="https://img.shields.io/badge/powered%20by-TypeSafe%20Jev%20System%20One-orange.svg" alt="TypeSafe Jev"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-purple.svg" alt="Compatível com MCP"></a>
  <a href="#"><img src="https://img.shields.io/badge/dependencies-0%20(pure%20stdlib)-success.svg" alt="Zero Dependências"></a>
  <a href="SYSTEM_1_5_IMPLEMENTATION.md"><img src="https://img.shields.io/badge/architecture-System%201.5%20Layer-8A2BE2.svg" alt="Arquitetura System 1.5"></a>
</p>

<p align="center">
  <b><a href="README.md">🇬🇧 English</a> | <a href="README.pt-BR.md">🇧🇷 Português</a></b>
</p>

> **Pare de queimar 50.000 tokens de fronteira com pacotes ausentes, instabilidades de rede efêmeras e loops circulares da desgraça (doom loops).**
>
> `jev-harness` é um otimizador de tokens ultra-rápido com zero dependências externas, porta de triagem de erros de testes e guardrail semântico para agentes autônomos de codificação com IA (OpenCode, Command Code, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed e Pi). Desenvolvido sobre o modelo de decisão não-autorregressivo **TypeSafe AI Jev System One**.
>
> 🤖 **Operando como Agente de IA?** Você **DEVE** ler o [`AGENTS.md`](AGENTS.md) ([Português](AGENTS.pt-BR.md)) antes de executar tarefas, e consultar o nosso [**Guia de Integração Universal para Agentes**](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md) para plugar o harness no seu projeto em 2 minutos.
>
> **O que é:** uma **camada de decisão System 1.5** deterministic-first para o ciclo de qualidade de código — triagem de falhas de teste, quebra de doom loops, veto de conclusão prematura, governança de esforço e roteamento de modelos — utilizável como CLI, servidor MCP, hook de git/CI e SDKs tipados em **três runtimes (Python, TypeScript, Rust)**.
> **O que não é:** um agente de código; um supervisor de runtime ([Foreman](https://github.com/thruwire/foreman)); um guardrail de tool calls ([jev-guard](https://github.com/leepokai/jev-guard)); uma peneira de contexto ([Winnow](https://github.com/GhalebDweikat/winnow)); ou um roteador de capacidades ([JevRouter](https://github.com/BillionsBobby/JevRouter)). Veja [Onde Ele se Encaixa](#-onde-ele-se-encaixa-a-camada-de-decisão-system-15).

<details>
<summary><b>📑 Índice</b></summary>

- [O Problema](#-o-problema) · [Como Funciona](#-como-funciona-sistema-1--sistema-15--sistema-2) · [Onde se Encaixa](#-onde-ele-se-encaixa-a-camada-de-decisão-system-15) · [Recursos](#-recursos) · [Início Rápido](#-início-rápido) · [CLI](#-uso-da-linha-de-comando-cli) · [Astra-Jev](#-astra-jev-governança-dinâmica-de-esforço-de-raciocínio-modelos-de-fronteira-2026) · [Integrações](#-integrações-universais-com-agentes-e-ides) · [SDKs](#-python-sdk) ([TS](#-typescript--javascript-sdk--cli), [Rust](#-rust-crate--standalone-cli)) · [Git & CI](#-guardrails-para-git--cicd) · [Economia e Benchmarks](#-economia-e-benchmarks-fronteira-setembro-de-2026) · [Arquitetura & Roadmap](#-arquitetura--roadmap) · [Changelog](#-o-que-há-de-novo-na-v020)

</details>

---

## 🎯 O Problema

Quando um agente autônomo de codificação encontra uma falha em testes ou um erro de compilação, o comportamento padrão é enviar 500 linhas de traceback bruto para um modelo de raciocínio de fronteira extremamente caro (GPT-6 Astra, Claude Fable 5.1).

| Cenário de Falha | Sem Jev Harness | Com Jev Harness |
| :--- | :--- | :--- |
| **Dependência ausente** (`ModuleNotFoundError`, `Cannot find module`, `TS2307`, `E0463`) | 💸 **~50.000 tokens de LLM (estimativa)** (~$0,50 - $2,50) + 15s de espera para sugerir `pip/npm install ...` | ⚡ **Triagem do Jev** (medido: < 1 ms offline in-process, ~80–100 ms CLI offline, ~0,5–1 s live; ≈ **$0,00002/chamada** com ~470 tokens de entrada) → Ação: instalar dependência deterministicamente. **0 tokens de LLM**. |
| **Falha efêmera / Flaky** (timeout de rede, porta ocupada, ECONNREFUSED) | 💸 LLM alucina refatorações arquiteturais para "corrigir" uma falha passageira | ⚡ **Jev detecta erro transiente** → Retry automático único. **0 alterações no código**. |
| **Refatoração circular** (Doom Loop: tentando a mesma correção 3+ vezes) | 💸 **200.000+ tokens queimados** em ciclos infinitos | 🛑 **Disjuntor do Jev dispara** (`exit 1`) → Interrompe o loop e alerta o desenvolvedor. |
| **Erro de digitação / Formatação** | 💸 Modelo de raciocínio pesado usado para regex ou typo simples | ⚡ **Jev Route** direciona para script local ou Gemini 3.8 Flash. |

---

## 🏗️ Como Funciona: Sistema 1 → Sistema 1.5 → Sistema 2

O paradigma cognitivo de Daniel Kahneman aplicado à engenharia de agentes, com este harness atuando como a **camada executiva de governança System 1.5** entre a percepção do Sistema 1 e a deliberação do Sistema 2:
- **Sistema 1 (Rápido, Intuitivo, Calibrado):** O **TypeSafe Jev System One** fornece micro-decisões paralelas, não-autorregressivas e tipadas. Latência: 70–300 ms (medido: **~80–100 ms** no CLI offline e **~0,5–1,0 s** live no tier gratuito). Preço: **$0,042 por 1M de tokens de entrada** ($0 tokens de saída). Responde perguntas fechadas específicas (`triage_category`, `severity_score`, `should_abort`, `target_tier`, `completion_status`) sem alucinações generativas.
- **Sistema 1.5 (Tecido Conectivo Determinístico e Camada Executiva):** O **`jev-harness`** é a camada executiva de decisão que coordena o Sistema 1 e o Sistema 2 em um ciclo de feedback autônomo, seguro e limitado (paradigma cognitivo para agentes de Josh Rosen):
  - **Sanitização de estado zero-trust e percepção focada:** Redige credenciais e segredos confidenciais, bloqueia injeções de prompt em logs de erro e extrai fatias focadas de asserção (≤15 linhas) em vez de inundar os modelos com 500 linhas de terminal bruto.
  - **Curto-circuitos determinísticos e recuperação estruturada:** Diagnostica instantaneamente dependências ausentes (`pip`, `npm`, `cargo`) e instabilidades efêmeras de rede/porta em < 500 µs locais sem gastar nenhum token de LLM.
  - **Calibração de incerteza e envelopes de entropia:** Calcula margem de confiança e entropia normalizada para proteger contra decisões limítrofes, escalando casos ambíguos para o Sistema 2.
  - **Leasing de esforço de raciocínio e quebra de doom loops:** Regula tiers de esforço cognitivo (`low` a `extra_high`) para modelos de fronteira e aciona o disjuntor semântico (`exit 1`) quando o agente entra em ciclos circulares de repetição.
  - **Paridade nativa entre runtimes:** Implementado nativamente em Python, TypeScript e Rust com zero dependências externas de runtime e fallback offline completo.
- **Sistema 2 (Lento, Deliberativo, Generativo):** LLMs de fronteira de alto raciocínio (**GPT-6 Astra**, **Claude Fable 5.1**, **Claude Opus 5**) escrevem código, realizam refatorações multi-arquivos e solucionam defeitos lógicos profundos. O Sistema 1.5 garante que o Sistema 2 **só seja acionado quando estritamente necessário**, reduzindo o gasto de tokens em até ~80–90%.

```
       ┌────────────────────────────────────────────────────────────────────────┐
       │             Loop de Execução do Agente de Codificação                  │
       │     (OpenCode / Claude Code / Cursor / Windsurf / Antigravity IDE)     │
       └───────────────────────────────────┬────────────────────────────────────┘
                                           │
                               [Execução de Comando/Teste]
                                           │
                                           ▼
                                   [Saída da Execução]
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼                                                   ▼
         [✅ PASSOU: Continua]                                [❌ FALHA: Traceback]
                                                                     │
 ════════════════════════════════════════════════════════════════════╪══════════════════════════════════
 🧠 SISTEMA 1.5: CAMADA EXECUTIVA DE DECISÃO E GOVERNANÇA (jev-harness)│
 ────────────────────────────────────────────────────────────────────┼──────────────────────────────────
                                                                     ▼
                                                     ┌───────────────────────────────┐
                                                     │ 1. Percepção e Sanitização    │
                                                     │  • Redação de credenciais     │
                                                     │  • Fatia focada da asserção   │
                                                     │  • Triagem contra injeção     │
                                                     └───────────────┬───────────────┘
                                                                     │
                                                                     ▼
                                                     ┌───────────────────────────────┐
                                                     │ 2. Heurísticas Determinísticas│
                                                     │    Rápidas (< 500 µs locais)  │
                                                     │  • Dependência ausente (regex)│
                                                     │  • Erros de rede efêmeros     │
                                                     │  • Padrão de doom loop        │
                                                     └───────────────┬───────────────┘
                                                                     │
                                                 ┌───────────────────┴───────────────────┐
                                                 ▼ (Match / Certeza)                     ▼ (Ambíguo)
 ┌──────────────────────────────────────────────────────────────┐        ┌───────────────────────────────┐
 │ 3. Cache de Decisão e Recibos                                │        │ ⚡ SISTEMA 1 (TypeSafe Jev)   │
 │  • Deduplicação via .jev/cache.json                          │        │  • Modelo não-autorregressivo │
 │  • Recibos de auditoria append-only (SHA-256)                │        │  • Micro-decisões sub-segundo │
 │  • Gestão de lease de esforço de raciocínio                  │        │  • Score e distribuição tipada│
 └──────────────────────────────┬───────────────────────────────┘        └───────────────┬───────────────┘
                                │                                                        │
                                └───────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                                             ┌───────────────────────────────┐
                                             │ 4. Gate de Incerteza e Política│
                                             │  • Margem e entropia norm.    │
                                             │  • Modulação de esforço       │
                                             │  • Fail-open / fail-closed    │
                                             └──────────────┬────────────────┘
                                                            │
 ═══════════════════════════════════════════════════════════╪═══════════════════════════════════════════
                         ┌──────────────────────────────────┴──────────────────────────────────┐
                         ▼                                                                     ▼
         [skip_llm = True / Acionável]                                         [skip_llm = False / Escalado]
                         │                                                                     │
                         ▼                                                                     ▼
           Recuperação Shell Determinística                                      🧠 SISTEMA 2 (LLM de Fronteira)
          • pip/npm/cargo install pacote                                          (GPT-6 Astra / Claude Fable)
          • Retry com backoff exponencial                                         • Depuração algorítmica profunda
          • Disjuntor semântico (exit 1)                                          • Refatoração multi-arquivos
                         │                                                        • Esforço de raciocínio calibrado
                         ▼                                                                     │
             ⚡ 0 Tokens de Fronteira Gastos                                          💸 Custo reduzido em ~80%
```

---

## ✨ Recursos

- 🛡️ **Zero Dependências Externas:** Construído 100% com a biblioteca padrão do Python (`urllib.request`, `dataclasses`, `json`). Sem inchaço de pacotes; cold start medido do CLI offline ~80–100 ms e gates in-process na casa de dezenas de microssegundos.
- 🔌 **Servidor MCP Universal:** Expõe ferramentas de decisão via stdio (`jev-mcp` ou `npx @ismaelsoilet/jev-harness mcp`) para Cursor, Claude Desktop, Antigravity, Windsurf, Zed e OpenCode.
- 🚦 **Conforme com a Filosofia UNIX:** Códigos de saída semânticos (`0` para sucesso/skip_llm, `1` para abort/defeito lógico, `2` para erro de sintaxe) permitem pipes limpos: `pytest | jev-harness test-gate`.
- 🔄 **Fallback Resiliente de Provedor:** falhas retentáveis (`429`, `5xx`, timeouts, erros de rede) são retentadas com backoff exponencial com teto e respeitam `Retry-After`; após as tentativas, a política padrão **fail-open** degrada para o motor determinístico e marca a resposta (`is_mock=true` + `degraded_reason`: `auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`). Um `200` que o runtime não consegue interpretar — tipo de campo errado (`score: "N/A"`), tipo de resposta desconhecido, campo obrigatório ausente ou `answers: []` — segue o mesmo caminho nos três runtimes: degradação marcada, nunca crash, `NaN` silencioso ou score silenciosamente default. `--fail-closed` expõe o erro (exit `2`) e `--retries N` ajusta as tentativas.
- 👻 **Shadow Mode:** `--shadow` (ou `"shadow": true` no `.jev.json`) decide e reporta `[SHADOW] would exit N` saindo sempre `0`, de modo que o pipeline continua rodando enquanto você mede os gates em tráfego real. Uso incorreto do CLI (arquivo `--log` inexistente, flag inválida) ainda sai `2`.
- 🧾 **Trilha de auditoria e autodiagnóstico:** `jev-harness doctor` verifica config, credenciais (apenas fingerprint), origem do modelo, limites, permissões do estado, recibos/cache e o hook de git — cada problema vem com o comando de correção. `jev-harness receipts` lê a trilha de decisões append-only (hashes + metadados, nunca logs brutos; `0600`, TTL e tamanho limitados, `--no-receipts` para desligar).
- 🧪 **Corpus de calibração e gate de replay:** `jev-harness replay --corpus tests/corpus` roda 160 casos rotulados por todos os gates, imprime matriz de confusão, precisão/recall/F1 e ECE por gate, e falha a CI em regressão contra `docs/REPLAY_REPORT.json` ou quando um log adversarial é classificado de forma determinística.
- ⚡ **Cache de decisão e debounce:** decisões live idênticas são servidas do `.jev/cache.json` (`--no-cache` ignora) e avaliações repetidas de `nudge-gate`/`abort-check` na janela de debounce são coalescidas (`debounced: true`). Rodadas em shadow e respostas degradadas nunca são cacheadas; o hit-rate aparece no `metrics`.
- 🤖 **Action de triagem para CI:** uma GitHub Action composta transforma um step falho em anotação categorizada com a próxima ação determinística — offline por padrão (sem chave, sem rede), nunca bloqueia execução verde, e o bloqueio é opt-in via `fail-on`.
- 🎯 **Envelope de incerteza:** cada resultado de gate carrega um bloco aditivo `uncertainty` (`margin`, `normalized_entropy`, `confidence`, `escalate_to_system2`, `escalation_reason`) derivado da distribuição real do provedor — zeros e perguntas de opção única protegidos, as duas convenções de chave aceitas, e uma execução verde nunca é escalada. Nunca altera `skip_llm` nem exit codes.
- ✂️ **Percepção focada e redação do state:** o gate de triage envia ao provedor um `focused_slice` (a linha da asserção e vizinhas, ≤15 linhas) mais `causal_context` em vez de apenas o log bruto, e **redige material com cara de credencial do próprio state** — nos três runtimes.
- 🧩 **Recuperação estruturada, nunca auto-executada:** dependência ausente vira dado (`{action_type, package_name, package_manager, argv, is_safe_auto_run, rationale}`) — sem string de shell, validação de nome por ecossistema, e `is_safe_auto_run` exige o pacote nos seus manifestos **e** `--allow-auto-recovery`.
- 🧠 **Memória de sessão e lease de esforço:** os gates reutilizam as decisões recentes deste repositório (um `--history` explícito continua vencendo), e uma decisão abre um lease limitado de esforço que responde em sub-milissegundos com `--use-lease` — invalidado na hora por `--tool-error` (break-glass).
- 🔌 **Plugins por host e interop:** bundles prontos para **Claude Code** (`plugins/claude-code`) e **Codex/OpenCode** (`plugins/codex`), além de uma seção de interop com a tabela datada do ecossistema e um link-checker offline na CI.
- 🌐 **Múltiplos Provedores:** TypeSafe AI direto, OpenCode Zen, Command Code, Vercel AI Gateway e OpenRouter (acesso alpha).

---

## 🧭 Onde Ele se Encaixa: A Camada de Decisão System 1.5

O `jev-harness` é um papel na categoria emergente **System 1.5**: conectar um modelo de decisão System One rápido (**Jev**) aos modelos de fronteira System 2 através de software determinístico. A categoria já tem ferramentas especializadas — use cada uma onde ela pertence (snapshot: 23/09/2026):

| Ferramenta | Papel | Funciona offline? |
| :--- | :--- | :--- |
| **jev-harness** (este repo) | Gates de qualidade: triagem de testes, quebra de doom loops, veto de conclusão, governança de esforço, roteamento | ✅ Motor determinístico, sem chave |
| [Foreman](https://github.com/thruwire/foreman) | Roda e supervisiona workers de código (steer / stop / retry / verify / finish) | ❌ Exige chave |
| [JevRouter](https://github.com/BillionsBobby/JevRouter) | Roteia capacidades (modelo / subagente / skill / MCP) com política e recibos | ❌ Exige chave |
| [Winnow](https://github.com/GhalebDweikat/winnow) | Filtra o que entra na janela de contexto do agente | ❌ Exige chave |
| [jev-guard](https://github.com/leepokai/jev-guard) | Guardrails para tool calls (deny / ask / allow) e triagem de prompt injection | ❌ Exige chave |

**Nossa combinação única:** a única ferramenta do conjunto que (1) funciona **totalmente offline** com um motor determinístico, (2) entrega **três runtimes com paridade semântica de veredito** (Python / TypeScript / Rust — divergência conhecida nas probabilidades da mock é rastreada como E3.9) e (3) é dona do **gate de qualidade de teste / commit / CI**.

📚 Arquitetura e roadmap: [Plano System 1.5](SYSTEM_1_5_PLAN.md) · [Ecossistema e oportunidades](SYSTEM_1_5_OPPORTUNITIES.md) · [Plano de implementação](SYSTEM_1_5_IMPLEMENTATION.md).

---

## 🚀 Início Rápido

### 1. Instalação nos 3 Ecossistemas
Disponível nos três principais registries sem dependências externas de runtime:

| Ecossistema | Registry | Pacote / Comando | Status |
| :--- | :--- | :--- | :--- |
| **Python** | [PyPI](https://pypi.org/project/jev-harness/) | `pip install jev-harness` | [![PyPI](https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=0)](https://pypi.org/project/jev-harness/) |
| **TypeScript / Node** | [npm](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) | `npm install @ismaelsoilet/jev-harness` | [![npm](https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white&cacheSeconds=0)](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) |
| **Rust** | [crates.io](https://crates.io/crates/jev-harness) | `cargo add jev-harness` | [![crates.io](https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white&cacheSeconds=0)](https://crates.io/crates/jev-harness) |
| **GitHub Releases** | [Releases](https://github.com/ismaelsoilet/jev-harness/releases) | Binários pré-compilados e assets | [![Versão no GitHub Release](https://img.shields.io/github/v/release/ismaelsoilet/jev-harness?color=teal&logo=github&logoColor=white&cacheSeconds=0)](https://github.com/ismaelsoilet/jev-harness/releases) |

```bash
# Python (CLI + SDK)
pip install jev-harness
# ou CLI global isolado
pipx install jev-harness

# TypeScript / Node.js (CLI + SDK)
npm install @ismaelsoilet/jev-harness
# ou executar diretamente via npx
npx @ismaelsoilet/jev-harness --version

# Rust (Crate + CLI Standalone)
cargo add jev-harness
# ou instalar o binário standalone 'jev'
cargo install jev-harness
```

### 2. Configuração e Múltiplos Provedores

O Jev Harness suporta diversos backends e detecta credenciais automaticamente:

| Provedor | Endpoint | Custo | Configuração |
| :--- | :--- | :--- | :--- |
| **Command Code (Tier Gratuito)** | `https://api.commandcode.ai/provider/v1/systemone` | **$0,00 / Grátis** | `export CMD_API_KEY=sua-chave` ou `cmd login` (`~/.commandcode/auth.json`) |
| **OpenCode Zen (Tier Gratuito)** | `https://opencode.ai/zen/v1/systemone` | **$0,00 / Grátis** | `export OPENCODE_API_KEY=zen` ou selecionado automaticamente |
| **TypeSafe AI (Direto)** | `https://api.typesafe.ai/v1/systemone` | $0,042 / 1M | `export TYPESAFE_API_KEY=sua-chave` |
| **OpenRouter (Alpha)** ⚠️ | `https://openrouter.ai/api/alpha/decisions` | $0,042 / 1M | `export OPENROUTER_API_KEY=sua-chave` — exige acesso alpha aprovado; o endpoint e o modelo `typesafe/jev-1.13` **ainda não são públicos** |
| **Vercel AI Gateway** | `https://ai-gateway.vercel.sh/v1/evaluate` | $0,042 / 1M | `export AI_GATEWAY_API_KEY=sua-chave` |
| **Simulação Autônoma** | Heurística Local (< 500µs) | **$0,00** | Ativa por padrão se offline ou sem chave |

> **📅 Data de verificação dos provedores: 22/09/2026.** IDs de modelos, tiers gratuitos e preços mudam semanalmente — agentes e engenheiros devem re-verificá-los (e registrar a própria data) se passaram mais de 30 dias. Passo a passo para obter chaves de cada provedor: **[Guia Universal de Integração para Agentes](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md#-acesso-a-provedores-e-chaves-de-api)**.
>
> **🔒 Privacidade:** o modo offline (`--mock`, ou sem credenciais) faz **zero chamadas de rede**. O modo live transmite as perguntas tipadas e o log de falha (cabeça 2.000 + cauda 4.000 caracteres) ao endpoint do provedor. Desde a v0.2.0 o **próprio state é redigido** nos três runtimes: material com cara de credencial (chaves de API, JWTs, tokens do GitHub/AWS, URLs de banco, chaves privadas) é mascarado antes de sair do processo — em todos os gates e também via MCP/SDK. É higiene por forma, **não** uma camada de DLP: dados de clientes que não pareçam credencial ainda são transmitidos, então use `--mock` em repositórios com dados regulados.

Prioridade de resolução de credenciais:
1. Variáveis de ambiente (`TYPESAFE_API_KEY`, `CMD_API_KEY`, `COMMAND_CODE_API_KEY`, `OPENCODE_API_KEY`, `OPENROUTER_API_KEY` ou `AI_GATEWAY_API_KEY`)
2. Arquivo `.jev.json`, `.env` na raiz do repositório ou `~/.commandcode/auth.json`
3. Configuração global `~/.config/jev/credentials.env`
4. **Fallback Resiliente**: ativo quando não há credenciais configuradas e em falhas retentáveis do provedor (`429`/`5xx`/timeouts/rede) ou `401`/`403` de **qualquer** provedor. As retentativas usam backoff com teto + `Retry-After`; o motor imprime `[JEV WARNING]` no stderr e todo resultado degradado é sinalizado com `is_mock=true` e um `degraded_reason`. Use `--fail-closed` para expor esses erros (exit `2`, sem traceback).

```bash
# Verificar status da conexão e provedor ativo a qualquer momento
jev-harness status
```

### Configuração do Repositório (`.jev.json`)

O `jev-harness init` cria um `.jev.json` local. Chaves honradas:

| Chave | Tipo | Padrão | Efeito |
| :--- | :--- | :--- | :--- |
| `model` | string | padrão do provedor | Sobrescreve o modelo enviado ao provedor. O placeholder `jev-latest` do scaffold significa "usar o padrão otimizado do provedor", portanto nunca sobrescreve IDs de modelo exigidos pelo provedor. |
| `skip_llm_threshold` | float `0`-`1` | `0.65` | Confiança mínima para o `test-gate` definir `skip_llm=true` (um veredito `deep_logic` nunca é ignorado). |
| `abort_threshold` | float `0`-`1` | `0.70` | Probabilidade mínima de beco sem saída para o `abort-check` abortar uma trajetória. |
| `shadow` | bool | `false` | Decide e reporta, mas nunca altera o exit code (ver [Shadow Mode](#-recursos)). |
| `api_key` / `provider` | string | — | Credenciais opcionais. Variáveis de ambiente têm precedência. |

Os valores são limitados a `[0, 1]`, e um arquivo corrompido degrada para os padrões em vez de quebrar a CI. As mesmas chaves funcionam de forma idêntica em Python, TypeScript e Rust.

**Fixando o modelo.** O modelo efetivo resolve como argumento explícito → variável `JEV_MODEL` → `model` no `.jev.json` → padrão do provedor (rode `jev-harness status` para ver o modelo e de onde ele veio). O alias `jev-latest` **muda**: o provedor pode alterar para onde ele aponta. Quando seu `skip_llm_threshold` estiver calibrado contra uma versão do modelo, fixe-a — por exemplo `"model": "jev-1.13.0"` — para que um release do provedor não mude suas decisões silenciosamente.

---

## 🛠️ Uso da Linha de Comando (CLI)

### 1. Triagem de Falhas em Testes (`test-gate`)
Encaminhe logs via pipe diretamente ou aponte para um arquivo:

```bash
# Pipe direto do seu executor de testes
npm test | jev-harness test-gate
pytest | jev-harness test-gate

# Ou analisar um arquivo salvo
jev-harness test-gate --log error.log

# Ou saída em JSON para parsing de scripts
jev-harness test-gate --log error.log --json

# Observe decisões sem bloquear um pipeline (sempre sai 0)
jev-harness test-gate --shadow --log error.log

# Falhe duro em indisponibilidade do provedor em vez de degradar
jev-harness test-gate --fail-closed --log error.log

# Limite quanto tempo falhas retentáveis são repetidas (padrão: 3 tentativas)
jev-harness test-gate --retries 1 --log error.log
```

**Exemplo de Saída:**
```text
--- JEV TEST TRIAGE VERDICT ---
Category:        ENV_MISSING
Confidence:      92.0%
Skip LLM Call:   YES (Save Tokens!)
Skip Probability: 96.0%
Severity Score:  1.0 / 4.0
Recommendation:  AUTO-ACTION: Install missing dependency or check environment configuration (Do NOT call LLM).
--------------------------------
```

### 2. Proteção Contra Doom Loops & Becos Sem Saída (`abort-check`)
Verifique se o plano proposto pelo agente está repetindo um caminho fracassado:

```bash
jev-harness abort-check \
  --plan "Tentar novamente reescrever todo o schema do banco sem backup" \
  --history "Tentativa 1 falhou por timeout. Tentativa 2 falhou por foreign key circular."
```
*Retorna código de saída `1` se o aborto for recomendado, permitindo interrupções automáticas em CI e loops de agentes.*

### 3. Roteamento de Modelos por Complexidade (`route`)
Selecione o modelo mais econômico capaz de resolver a tarefa:

```bash
jev-harness route --task "Corrigir erro de digitação na docstring e formatar com black"
# -> TIER: DETERMINISTIC | Modelo: Script Python/Bash Direto (0 Tokens de LLM)

jev-harness route --task "Refatorar árvore de supervisão de atores distribuídos em 14 módulos"
# -> TIER: HEAVY_SYSTEM2 | Modelo: Claude Fable 5.1 / GPT-6 Astra (~$10.00 in / $50.00 out)
```

### 4. Verificação de Conclusão de Passos (`verify`)
Avalia evidências contra critérios com confiança calibrada:

```bash
jev-harness verify \
  --criteria "Deve exportar a função format_date e passar em todos os 10 testes unitários" \
  --output "Todos os 10 testes passaram em 0.02s. format_date exportada em index.ts."
```

### 5. Governança Dinâmica de Esforço de Raciocínio (`reasoning-effort` / `astra-jev`)
Module o esforço de raciocínio dinamicamente a cada geração (inspirado por Vechen @miu21590) para eliminar latência e economizar milhares de tokens em passos mecânicos:

```bash
# Avaliar passo imediato para DeepSeek (ex: DeepSeek V4.1-Flash / V4-Pro)
jev-harness reasoning-effort \
  --context "git status e verificar arquivos alterados no commit recente" \
  --target-provider deepseek

# Saída:
# Effort: LOW | Dialeto: {"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"}
# Latência eliminada: ~200s de CoT interno reduzidos para 1.5s!

# Avaliar tarefa arquitetural para Anthropic (Claude Fable 5.1 / Claude Opus 5)
jev-harness reasoning-effort \
  --context "Arquitetar árvore de supervisão distribuída com consenso raft" \
  --target-provider anthropic --json

# Salvaguarda automática para modelos direct (retorna parâmetros vazios e alerta para modelos sem raciocínio interno)
jev-harness reasoning-effort \
  --context "Executar comando bash" \
  --target-provider openai \
  --model gpt-5.6-luna
```

### 6. Gate de Continuação & Jev Nudge (`nudge-gate` / `nudge`)
Inspirado no [`CommandCodeAI/cmd-mod-jev-nudge`](https://github.com/CommandCodeAI/cmd-mod-jev-nudge), o `nudge-gate` combina fases de fluxo de trabalho (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) com probabilidades `Noul` calibradas (`nudge`, `waiting`, `progress`) para avaliar se um agente autônomo parou prematuramente com código não verificado ou tarefas incompletas (`should_nudge = true`, exit code `0`), aplicando vetos automáticos caso o agente esteja aguardando resposta do usuário (`waiting >= 0.5` ou `phase == "ask"`), sem progresso após o nudge anterior (`progress < 0.5`) ou com tarefa 100% concluída (`phase == "complete"`):

```bash
# Avaliar se o agente parou após editar código sem rodar a bateria de testes
jev-harness nudge-gate \
  --transcript "Assistant: Edited src/auth.py. Now I need to run pytest to verify." \
  --json
# -> should_nudge: true | workflow_phase: "verify" | exit code 0

# Avaliar quando o agente aguarda decisão do usuário (vetado automaticamente)
jev-harness nudge-gate \
  --transcript "Assistant: Which AWS region should I deploy to? Would you like me to proceed?"
# -> should_nudge: false | workflow_phase: "ask" | exit code 1
```

### 7. Telemetria de ROI e Economia de Tokens (`metrics`)
Inspecione tokens acumulados poupados, dólares economizados e loops circulares interrompidos:

```bash
# Visualizar telemetria da sessão
jev-harness metrics

# Resetar contadores de telemetria
jev-harness metrics --reset
```

**Exemplo de Saída:**
```text
============================================================
              JEV HARNESS TELEMETRY & ROI
============================================================
Total Triage Interceptions:      14 calls
LLM Frontier Calls Skipped:      11 calls (78.6%)
Abort Guard Stops Triggered:     2 doom loops killed
Deterministic Routes:            6 tasks
Reasoning Effort Modulations:    8 steps (6 low, 2 high)
Estimated Tokens Saved:          422,200 tokens (estimativa heurística)
Estimated Frontier Dollars Saved: $6.12 USD (estimativa heurística)
Assumption Model:                26,200 tokens/$0.31 per intercepted triage; 80,000 tokens/$1.20 per aborted doom loop
============================================================
```

> 📊 **Estes números são uma estimativa de planejamento, não medição real.** As premissas por evento são constantes fixas (26.200 tokens/$0,31 por triagem interceptada, 80.000 tokens/$1,20 por loop abortado). O `--json` expõe `estimates_are_heuristic: true` para que ferramentas downstream possam rotulá-los corretamente.

### 8. Autodiagnóstico, auditoria e calibração (`doctor` / `receipts` / `replay`)

```bash
# Minha instalação está saudável? (nunca imprime segredos; --live gasta UMA requisição)
jev-harness doctor
jev-harness doctor --live --json

# O que este repositório decidiu? (append-only, apenas hashes + metadados)
jev-harness receipts --tail 10
jev-harness receipts --json

# Quão precisos são os gates? (matriz de confusão, P/R/F1, ECE por gate; falha em regressão)
jev-harness replay --corpus tests/corpus
```

### 7. Configuração Automatizada de Agentes com Um Comando (`init`)
Gera automaticamente a configuração de MCP para o seu editor ou agente:

```bash
# Configuração para o Cursor
jev-harness init --cursor

# Configuração para a IDE Antigravity
jev-harness init --antigravity

# Configuração de hook de pre-commit do Git
jev-harness init --git

# Configurar todas as ferramentas suportadas de uma vez
jev-harness init --all
```

---

## ⚡ Astra-Jev: Governança Dinâmica de Esforço de Raciocínio (Modelos de Fronteira 2026)

Inspirado pelo trabalho pioneiro de Vechen ([@miu21590](https://x.com/miu21590)) com *Astra-Codex* e o framework **[Astra-Ares](https://github.com/miuuyy/Astra-Ares)**, o **Astra-Jev** introduz modulação de esforço de raciocínio por geração, governada pelo TypeSafe Jev System One.

Em vez de prender uma sessão inteira de agente em raciocínio pesado e lento (ou arriscar bugs rodando exclusivamente em raciocínio baixo), o Astra-Jev avalia a demanda cognitiva do próximo passo em **< 500µs localmente** (in-process; a latência live depende do provedor — medido ~0,5–1,0 s no tier gratuito).

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 Loop do Agente Autônomo                │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                   Próxima Ação Proposta
                     ("git status", "ler arquivo" ou "arquitetar kernel")
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │       Gate Astra-Jev          │
                             │  (Jev System One Micro-Eval)  │
                             └───────────────┬───────────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            ▼                                ▼                                ▼
    [Trivial / Mecânico]             [Feature Padrão]               [Arquitetura Profunda]
    Profundidade: LOW                Profundidade: MED              Profundidade: HIGH
            │                                │                                │
            ▼                                ▼                                ▼
     Compila Dialeto                  Compila Dialeto                  Compila Dialeto
(ex: enable_thinking: false)     (ex: reasoning_effort: med)    (ex: thinking: adaptive max)
            │                                │                                │
            ▼                                ▼                                ▼
  ⚡ 1.5s resposta (~0 CoT)        🎯 Equilibrado ~4k CoT           🧠 Análise Profunda 32k CoT
  Ocidentais: Poupa ~$0.80 USD     Ocidentais: Preço normal         Ocidentais: Raciocínio máx.
  Chineses: Poupa ~240s espera     Chineses: Thinking normal        Chineses: Exploração profunda
```

### ROI Duplo: Por que Modular o Esforço de Raciocínio em 2026?

O impacto da modulação depende fundamentalmente da arquitetura do provedor:

| Ecossistema de Provedores | Problema Resolvido | Sem Astra-Jev | Com Astra-Jev |
| :--- | :--- | :--- | :--- |
| **Fronteira Ocidental**<br>(*GPT-6 Astra*, *Claude Fable 5.1*) | **Custo Financeiro**<br>($10/1M in, $50/1M out) | O agente queima ~8.000 tokens de raciocínio ($0,40 - $1,20) só para inspecionar `git status` ou ler um arquivo | Injeta `effort="low"`, gastando apenas ~300 tokens. **Economiza até $1,15 por geração mecânica.** |
| **Fronteira Chinesa**<br>(*DeepSeek V4.1-Flash*, *Qwen 3.8 Max*, *Kimi-k3*, *MiMo*) | **Latência e Espera de GPU**<br>(Tokens baratos, mas o CoT interno leva 3–5 minutos) | O agente entra em loop interno de reflexão de 200–300 segundos antes de rodar um simples comando bash | Desativa o thinking ou define `effort="low"`. Resposta entregue em **1,5s em vez de 240s**. |

### 🛡️ Salvaguardas Críticas Integradas no Astra-Jev

1. **Salvaguarda para Modelos Direct Single-Pass:** Modelos que não suportam raciocínio interno (ex: `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `claude-3-5-haiku`, `llama-3.3`) retornam **HTTP 400 Bad Request** fatal se receberem parâmetros de thinking. O Astra-Jev detecta esses alvos automaticamente, define `is_reasoning_supported = False` e retorna payloads vazios `{}`.
2. **Preservação de `reasoning_content` (DeepSeek multi-turn):** Nas APIs do DeepSeek V4.1-Flash/Pro, remover o `reasoning_content` em chamadas multi-turn de ferramentas pode corromper o fluxo. O Astra-Jev preserva estritamente a estrutura de pensamento entre turnos.
3. **Aviso de Trade-off no Prompt Cache (KV Cache):** Alternar parâmetros de raciocínio bruscamente em contextos longos (>100k tokens) pode invalidar o cache de prefixo das GPUs. O Astra-Jev fornece avisos de `cache_safe_recommendation` para preservar a taxa de cache hit.

---

## 🤖 Integrações Universais com Agentes e IDEs

> 📖 **Procurando configuração pronta para o seu projeto?** Leia o [**Guia Universal de Integração para Agentes**](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md) com modelos de copiar e colar para Claude Code, Codex, Pi, Oh My Pi, CommandCode, Cursor e CI/CD.

### 1. Claude Code (CLI `claude` da Anthropic)
Conecte o Jev ao Claude Code em 5 segundos via MCP nativo:
```bash
# Registre o MCP do Jev Harness no Claude Code
claude mcp add jev-harness -- npx -y @ismaelsoilet/jev-harness mcp

# Ou usando Python:
claude mcp add jev-harness -- jev-mcp
```
Adicione ao arquivo `CLAUDE.md` do seu projeto:
```markdown
## Governança de Tokens com Jev Harness
- Antes de consultar LLMs em falhas de teste ou build, execute `jev_triage_test_failure`. Se `skip_llm=true`, execute a correção determinística diretamente no shell.
- Se uma tarefa falhar 2 vezes seguidas sem progresso, execute `jev_abort_check` para quebrar loops circulares.
- Para comandos mecânicos ou busca de arquivos, chame `jev_modulate_reasoning_effort` com effort="low".
```

### 2. OpenAI Codex / Astra-Codex
Module dinamicamente o esforço de raciocínio do GPT-6 Astra a cada geração dentro do Codex sem invalidar o cache de prefixo (como destacado no X):
```bash
# Em scripts de automação do Codex ou pre-hooks:
jev-harness reasoning-effort \
  --context "$TASK_STEP_DESCRIPTION" \
  --target-provider openai --json
```
Injete o parâmetro `reasoning_effort: "low" | "medium" | "high"` no nível raiz do payload da API. O harness nunca reescreve o seu histórico de mensagens, portanto não invalida o cache de prefixo do provedor por construção.

### 3. Pi & Oh My Pi (`pi` / `oh-my-pi`)
Equipe o agente de terminal minimalista de Mario Zechner (`pi`) e fluxos do `oh-my-pi`:
```bash
# No seu prompt de terminal ou tarefa do Pi:
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
pytest 2>&1 | jev-harness test-gate
```
Se o código de saída for `0` (`skip_llm=true`), o Pi aplica a instalação determinística do pacote ou comando de retry sem chamar modelos caros.

### 4. CommandCode
No arquivo `.commandcode/config.json` ou pré-gatilhos de CLI:
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 5. IDE Cursor (`.cursor/mcp.json`)
Adicione ao `.cursor/mcp.json` (ou execute `jev-harness init --cursor`):
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 6. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "npx",
      "args": ["-y", "@ismaelsoilet/jev-harness", "mcp"]
    }
  }
}
```

### 7. IDE Google Antigravity (`mcp_config.json` e `hooks.json`)
Conecte como servidor MCP:
```json
{
  "mcpServers": {
    "jev-harness": {
      "command": "jev-mcp",
      "args": []
    }
  }
}
```
Ou vincule diretamente ao ciclo de vida em `~/.gemini/config/hooks.json`:
```json
{
  "jev-guard": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "echo '{\"injectSteps\": [{\"ephemeralMessage\": \"[JEV ACTIVE] Faça a triagem de erros com jev-harness test-gate antes de chamar LLMs. Se skip_llm=true, resolva deterministicamente.\"}]}'"
      }
    ]
  }
}
```

### 8. OpenCode, Windsurf & Zed
- **OpenCode:** Adicione o gate de triagem do Jev ao `.opencode/config.json`.
- **Windsurf:** Adicione ao `~/.codeium/windsurf/mcp_config.json`.
- **Zed:** Adicione ao `~/.config/zed/settings.json` em `context_servers`.

---

## 🐍 Python SDK

```python
from jev_harness import (
    JevClient,
    triage_test_failure,
    should_abort_trajectory,
    route_model_tier,
    verify_step_completion,
    modulate_reasoning_effort,
)

client = JevClient()

# 1. Triagem de traceback
res = triage_test_failure("ModuleNotFoundError: No module named 'scipy'", client=client)
if res.skip_llm:
    print(f"Seguro para corrigir deterministicamente: {res.action_recommendation}")

# 2. Verificação de trajetória contra doom loops
abort_decision = should_abort_trajectory(
    proposed_step="Tentar novamente a mesma abordagem",
    recent_attempts_summary="Tentativa 1 falhou com timeout",
    client=client,
)
if abort_decision.should_abort:
    print("Trajetória abortada! Realinhe com o usuário.")

# 3. Modulação de esforço de raciocínio dinâmico (Astra-Jev)
effort_res = modulate_reasoning_effort(
    context="git status e inspecionar diff de arquivos alterados",
    provider="deepseek",
    model="deepseek-v4.1-flash",
    client=client,
)
print(f"Esforço: {effort_res.effort}")  # low
print(f"Parâmetros: {effort_res.provider_params}")
```

---

## 🟦 TypeScript / JavaScript SDK & CLI

```typescript
import {
  triageTestFailure,
  shouldAbortTrajectory,
  modulateReasoningEffort,
  JevClient,
} from "@ismaelsoilet/jev-harness";

// 1. Triagem em < 2ms localmente
const triage = await triageTestFailure(rawErrorOutput);
if (triage.skipLlm) {
  console.log("Ação recomendada:", triage.actionRecommendation);
}

// 2. Prevenir loops circulares da desgraça
const abortCheck = await shouldAbortTrajectory(
  "Repetir passo anterior de refatoração",
  "Passo falhou com: TypeError: undefined is not a function"
);
if (abortCheck.shouldAbort) {
  console.error("Agente preso em loop! Abortando.");
}
```

---

## 🦀 Rust Crate & Standalone CLI

Latência ultra-baixa (< 500µs local, zero-overhead) para Tauri, ferramentas de terminal e backends sem dependências de Python ou Node.js:

```toml
[dependencies]
jev-harness = "0.2.0"
tokio = { version = "1", features = ["full"] }
```

```rust
use jev_harness::gates::{triage_test_failure, should_abort_trajectory, modulate_reasoning_effort};

#[tokio::main]
async fn main() {
    let triage = triage_test_failure("error[E0463]: can't find crate for 'serde'", None).await.unwrap();
    if triage.skip_llm {
        println!("Ação: {}", triage.action_recommendation);
    }
}
```

---

## 📦 Guardrails para Git & CI/CD

### Pre-commit Hook (`.pre-commit-config.yaml`)
O hook exige o seu comando de teste como argumento (um repositório de hooks não pode adivinhar o seu runner):

```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.2.0
    hooks:
      - id: jev-test-gate
        args: ["pytest -q"]     # ou "npm test", "cargo test --quiet", ...
```

### Hook de Git gerado (`jev-harness init --git`)
Detecta o seu runner (`npm`/`pytest`/`cargo`), escreve um hook failure-only e nunca sobrescreve um existente (salva `pre-commit.jev`). É **compatível com virtualenv**: quando existe `.venv`/`venv`, o hook usa os binários dessa env (ex.: `./.venv/bin/python`, `./.venv/bin/jev-harness`), funcionando com ou sem a env ativada.

```bash
jev-harness init --git
jev-harness init --git --test-cmd "make test-fast"   # sobrescreve o comando detectado
```

O `init` também cria `.jev.json`, `.env.jev.example` (todos os provedores), `.agents/skills/jev-harness/SKILL.md` e, com `--cursor`, `.cursor/mcp.json`. **Nunca sobrescreve ficheiros existentes nem hooks alheios**; reexecutar regenera apenas o hook que ele próprio gerou (reconhecido pelo marcador, incluindo variantes anteriores à v0.1.13).

### Hook do Husky (`.husky/pre-commit`)
Deixe o runner decidir; peça ao Jev apenas o triage da falha:

```bash
if ! OUT=$(npm test 2>&1); then printf '%s\n' "$OUT" | jev-harness test-gate; exit 1; fi
```

> Execuções verdes são detectadas deterministicamente (`category: "no_failure"`, exit `0`, zero chamadas de API), então `npm test 2>&1 | jev-harness test-gate` também é seguro — mas a forma failure-only acima é mais explícita e não depende de parsing do resumo.
>
> ⚠️ **`.git/hooks/` não é versionado.** Um hook gerado existe apenas na sua máquina; para equipas, faça commit de um script de hook (ou use o framework `pre-commit` com `id: jev-test-gate`) para que todos tenham o mesmo gate.

---

## 📊 Economia e Benchmarks (Fronteira Setembro de 2026)

### Economia de Tokens e Custos

| Métrica | Raciocínio de Fronteira 2026 (GPT-6 Astra, Claude Fable 5.1) | Tier de Agentes Rápidos (Gemini 3.8 Flash) | TypeSafe Jev System One (`jev-harness`) |
| :--- | :--- | :--- | :--- |
| **Preço de Entrada** | $10,00 / 1M tokens | $0,75 / 1M tokens | **$0,042 / 1M tokens (~238x mais barato)** |
| **Preço de Saída** | $50,00 / 1M tokens | $3,75 / 1M tokens | **$0,00 (Grátis - Não-autorregressivo)** |
| **Latência** | 10.000ms – 30.000ms | 1.500ms – 4.000ms | **Claim do provedor: ~100 ms típicos (piso de 70 ms). Medido E2E no harness: ~0,5–1,0 s live (tier gratuito), < 1 ms offline in-process** |
| **Estrutura de Saída**| Prosa livre & streaming de tokens | Chamadas estruturadas de ferramentas | **Estritamente tipado: Choice, Score, Noul** |
| **Determinismo** | Raciocínio estocástico | Geração estocástica | **Probabilidades calibradas — não infalíveis (ver [jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) do modelo)** |

### Latência Offline Tri-Runtime (medida em 23/09/2026, mock in-process)

Quando o `--mock` (ou nenhuma credencial) está ativo, todos os gates rodam localmente com zero rede. Orçamento: **p99 < 500µs** — assegurado em CI no Rust e medido nos três runtimes em 23/09/2026 (`N = 1000` para triagem, `N = 500` para abort/esforço, host Linux padrão):

| Runtime | Gate de Decisão | p50 | p95 | p99 | Média |
| :--- | :--- | ---: | ---: | ---: | ---: |
| **Rust** (`packages/rust`) | `triage_test_failure` | 22.0 µs | 38.7 µs | 58.5 µs | 26.1 µs |
| | `should_abort_trajectory` | 14.6 µs | 30.3 µs | 43.1 µs | 16.8 µs |
| | `modulate_reasoning_effort` | 15.5 µs | 29.9 µs | 40.5 µs | 17.6 µs |
| | *puro `simulate_system_one`* | 1.9 µs | 1.9 µs | 2.8 µs | 1.9 µs |
| **TypeScript** (`packages/ts`) | `triageTestFailure` | 39.5 µs | 143.2 µs | 340.3 µs | 57.2 µs |
| | `shouldAbortTrajectory` | 37.1 µs | 106.0 µs | 234.4 µs | 47.3 µs |
| | `modulateReasoningEffort` | 21.9 µs | 77.2 µs | 338.4 µs | 34.1 µs |
| **Python** (`src/jev_harness`) | `triage_test_failure` | 124.9 µs | 208.1 µs | 295.5 µs | 140.4 µs |
| | `should_abort_trajectory` | 112.4 µs | 181.3 µs | 229.2 µs | 125.0 µs |
| | `modulate_reasoning_effort` | 78.1 µs | 131.3 µs | 162.0 µs | 86.8 µs |

> ⚡ **Reproduzir / zero-overhead:** o Rust assegura o orçamento em `packages/rust/tests/gates_test.rs` (`cargo test --test gates_test -- --nocapture`); Os valores de Python e TypeScript são uma **amostra pontual** (23/09/2026, este host, cliente mock forçado in-process), não uma asserção de CI. Re-meça no seu hardware antes de citar; o **orçamento**, não o microssegundo exato, é o contrato. Canalizar executores de teste pelos gates continua adicionando overhead muito abaixo da percepção humana.

---

## 🌟 O que há de Novo na v0.2.0

- 🦀 **Paridade live do Rust corrigida (breaking para quem usa o crate direto)**: respostas `Score` no modo live eram descartadas silenciosamente porque o parser esperava score inteiro e legend em lista, enquanto o provedor retorna float e um mapa de níveis. Agora `ScoreAnswer.score` é `f64`, `legend` aceita mapa ou lista e `probabilities` são parseadas — `severity`, `viability`, `rigor` e `complexity` batem com Python/TypeScript no live. O crate é pré-1.0, então isto sai como release minor.
- 🔁 **Resiliência de provedor**: retry com backoff exponencial com teto (sem jitter, para CI determinístico) e suporte a `Retry-After` (`429`/`5xx`/timeouts, inclusive segundos fracionários); após as tentativas, a política padrão **fail-open** degrada para o motor determinístico offline e marca a resposta (`is_mock=true` + `degraded_reason`: `auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`). `--fail-closed` expõe o erro (exit `2`, sem traceback); `--retries N` ajusta as tentativas.
- 🧩 **Payload malformado do provedor é falha de primeira classe**: um `200` com campos de tipo errado (`score: "N/A"`, `answers: []`, numéricos `null`), `type` de resposta desconhecido ou campo obrigatório ausente antes derrubava o Python com traceback, produzia `NaN` silencioso no TypeScript e descartava a resposta em silêncio no Rust — três semânticas para a mesma entrada, com o gate caindo em silêncio para o score default. Agora os três tratam como `invalid_response`, repetem como um status ruim, degradam no fail-open e falham no fail-closed, e o `degraded_reason` finalmente **aparece** no `--json`, nos payloads MCP e na linha humana `Mode:`.
- 📦 **Guarda de payload**: `state` e perguntas são validados contra os limites do provedor (128k caracteres de state / 256k total, ~32k/64k tokens) antes de qualquer chamada de rede, contando code points de forma consistente nos três runtimes.
- 📌 **Pin e origem do modelo**: o modelo efetivo resolve como argumento explícito → `JEV_MODEL` → `"model"` no `.jev.json` → padrão do provedor, e o `status` agora informa **de onde ele veio** (`Model origin: repository .jev.json`), avisando que `jev-latest` é um alias móvel. Fixe uma versão quando os thresholds estiverem calibrados.
- 🐛 **Sem traceback em entrada literal longa**: uma task, state ou valor de `--log` maior que o limite de path do SO derrubava `route`/`verify`/`effort` com `[Errno 36] File name too long` (exit `1` com traceback); esse valor agora é tratado como texto literal (ou reportado como "log file not found"), e um payload live grande demais sai com `2` e mensagem clara.
- 👻 **Shadow mode**: `--shadow` (ou `"shadow": true` no `.jev.json`) decide e reporta `[SHADOW] would exit N` no stderr saindo sempre `0` — nos três runtimes, inclusive quando o provedor falha, caso em que reporta `[SHADOW] would exit 2` em vez de quebrar o pipeline. Uso incorreto do CLI ainda sai `2`; `test-gate --json` expõe `shadow` e `would_exit`.
- 🧪 **Bateria de 569 Testes**: 393 Python + 89 TypeScript + 87 Rust, incluindo fixture live compartilhado, servidores HTTP/TCP reais de retry, probes de payload malformado e paridade de shadow/limites/pin de modelo.
- 🧾 **Confiança, auditoria e autodiagnóstico**: `doctor` (OK/AVISO/FALHA + comando de correção, `--json` para agentes), `receipts` (trilha de auditoria append-only com hash estável de entrada, apenas hashes, `0600`, TTL/tamanho limitados), `.jev/` ignorado pelo git no repo e no `init`, `usage`/custo medidos separados das estimativas heurísticas no `metrics`, e cache de decisões com hit-rate reportado (`--no-cache` para ignorar).
- 🧪 **Calibração medida em vez de acurácia presumida**: corpus rotulado de 160 casos (`tests/corpus`, 84 rotulados à mão) mais `replay`, que imprime matriz de confusão, precisão/recall/F1 e ECE por gate e falha a CI em regressão ou quando um log adversarial é classificado deterministicamente. O primeiro baseline e seus achados abertos estão em `docs/REPLAY_REPORT.md`.
- 🛡️ **Logs não confiáveis tratados como não confiáveis**: um detector determinístico de injeção escala (nunca ignora o LLM) quando o log se dirige ao decisor, nos três runtimes — exigido pelo gate adversarial do corpus.
- 🤖 **Action de triagem para CI** (`examples/github-action`): anota um job falho com a categoria e a ação determinística, offline por padrão e sem nunca bloquear execução verde.
- 🎯 **Qualidade de decisão explícita**: `uncertainty` por resultado, `recovery` como dado estruturado com flag de segurança baseada em allowlist, slice focado em vez de log bruto para o provedor, redação de segredos no state, memória de sessão nos gates e lease de esforço com break-glass. Tudo aditivo: nenhum exit code ou `skip_llm` mudou.
- 🔀 **Paridade tri-runtime agora é imposta, não declarada**: `tests/fixtures/corpus_parity.json` trava 160 casos × 6 gates entre Python, TypeScript e Rust. Construí-lo expôs e corrigiu divergências reais, incluindo ordem de iteração não determinística do `HashMap` na mock do Rust.
- 📦 **Distribuição**: bundles de plugin por host (Claude Code, Codex/OpenCode), seção de interop com datas de fonte e link-checker de documentação offline na CI.
- 🧭 **Documentação System 1.5**: arquitetura, comparativo de ecossistema e plano de implementação linkados no README (`SYSTEM_1_5_*.md`).
- 🔒 **Privacidade/operação inalteradas**: o modo offline continua sem nenhuma chamada de rede; respostas live degradadas são sempre rotuladas, nunca silenciosas.

## 🌟 O que há de Novo na v0.1.14

- 🐛 **Um caminho `--log` errado deixa de ser triado como se fosse o texto do log.** `jev-harness test-gate --log /arquivo/inexistente` antes produzia um veredito fabricado `ENV_MISSING` / `skip_llm=true` com exit `0`; agora sai `2` com uma dica clara (use argumento posicional, `--sample` ou stdin). Corrigido nos três runtimes.
- 🪝 **Fim da falsa sensação de proteção após `init --git`.** Quando um hook `pre-commit` alheio é preservado, a CLI deixa de imprimir uma mensagem de sucesso simples: informa que **o gate não está ativo até você fazer o merge de `.git/hooks/pre-commit.jev`**.
- 📖 **Ajustes no guia a partir de uma execução com agente novo**: o smoke test MCP mostra o caminho absoluto do virtualenv do projeto, o `init` documenta exatamente o que escreve e que precisa rodar dentro de um repositório git, e o exit code `2` agora tem exemplo concreto.
- 🧪 **Bateria de 211 Testes**: 100% de aprovação em 211 testes (117 Python, 49 Rust, 45 TypeScript).

## 🌟 O que há de Novo na v0.1.13

- 🔌 **Integração MCP funciona de imediato**: o guia agora lista os nomes **reais** das ferramentas e seus argumentos (`jev_triage_test_failure`, `jev_abort_check`, `jev_route_task`, `jev_verify_completion`, `jev_modulate_reasoning_effort`, `jev_should_nudge_continuation`), um smoke test de 20 segundos, um exemplo válido de `tools/call`, nota de virtualenv para configs de cliente e snippet do OpenCode. Os nomes anteriores (`jev_should_abort_trajectory`, `jev_route_model_tier`, `jev_verify_step_completion`, `jev_get_telemetry`) não existiam.
- 🪝 **`init --git` é compatível com virtualenv**: o hook gerado usa os binários da env do projeto (`./.venv/bin/python`, `./.venv/bin/jev-harness`) quando existem, então uma suíte verde deixa de ser bloqueada com a env desativada, e `--test-cmd "<comando>"` sobrescreve o runner detectado.
- 🛡️ **`init` nunca destrói nada**: skills existentes são preservadas (como `.jev.json` e `.env.jev.example`), e apenas o hook gerado por ele próprio (marcador, incluindo variantes anteriores à v0.1.13) é regenerado.
- 📋 **Paridade de saída MCP/CLI**: o servidor MCP em Python agora retorna `action_recommendation` junto de `recommendation` (e `summary` junto de `reasoning_summary`), igual ao runtime TypeScript.
- 🧭 **Onboarding mais claro**: o Início Rápido informa que **nenhuma chave de API é necessária** (o modo offline é grátis e faz zero chamadas de rede), as instruções do `status` estão em inglês, o `.env.jev.example` lista todos os provedores e o README delimita o `AGENTS.md` a quem trabalha no próprio repositório.
- 🧪 **Bateria de 211 Testes**: 100% de aprovação em 211 testes (117 Python, 49 Rust, 45 TypeScript). Um agente de IA novo, sem contexto, reproduziu a integração completa duas vezes a partir dos docs publicados; cada lacuna que encontrou está corrigida aqui.

## 🌟 O que há de Novo na v0.1.12

- ✅ **Execuções verdes nunca bloqueiam nem escalam**: um detector determinístico e estrito reconhece resumos aprovados de pytest, vitest, jest, cargo, go, mocha, rspec e unittest, retornando `category: "no_failure"` com exit `0` e **zero chamadas de API**. Falhas reais sempre vetam o atalho (`1 failed`, `FAILED`, tracebacks, panics, erros de dependência/transientes). Isso corrige as falsas falhas nas receitas de pre-commit/husky em projetos JS e Rust.
- 🪝 **Integração pre-commit funcional**: o `jev-test-gate` agora recebe o comando de teste via `args` (o runner decide, o Jev aconselha) através de um console entry point que funciona de qualquer diretório do consumidor (um wrapper shell continua disponível para quem não usa pre-commit), e o `jev-harness init --git` gera um hook que detecta o runner (npm/pytest/cargo), usa `python3`, nunca sobrescreve um hook existente e registra o comando detectado.
- 🔐 **Arquivos de estado endurecidos**: `~/.config/jev` é criado `0700` e `session.json` / o lock são gravados `0600` (POSIX), então trechos de erro deixam de ser legíveis por outros usuários.
- 📖 **Documentação**: obtenção de acesso e chaves para cada backend (console TypeSafe, OpenCode Zen, Command Code, OpenRouter alpha, Vercel AI Gateway) com **data de verificação** e instruções de re-checagem para agentes, além de uma matriz explícita de privacidade (o que sai da máquina em live vs offline).
- 🧪 **Bateria de 207 Testes**: 100% de aprovação em 207 testes (113 Python, 49 Rust, 45 TypeScript).

## 🌟 O que há de Novo na v0.1.11

- 🐛 **Corrigida uma regressão de classificação da v0.1.10**: uma linha crua `RuntimeError:` / `ValueError:` / `TypeError:` não mascara mais uma causa raiz concreta de dependência ou transitória. Logs como `RuntimeError: ... Caused by: ModuleNotFoundError` e `RuntimeError: ... Timeout` voltam a ser triados como `env_missing` / `flaky_transient` (`skip_llm=true`), enquanto exceções de lógica real sem causa raiz de ambiente/transiente continuam escalando como `deep_logic`.
- 🌐 **Porta ocupada é flaky**: `Address already in use` / `EADDRINUSE` / `port already in use` (EN, PT-BR, ES) agora classificam como `flaky_transient`, alinhado ao comportamento documentado.
- ⚙️ **`.jev.json` é honrado de ponta a ponta**: `model`, `skip_llm_threshold` e `abort_threshold` passam a ter efeito em Python, TypeScript e Rust (antes o arquivo era criado mas silenciosamente ignorado).
- 🔐 **Fim dos crashes de autenticação na CI**: HTTP `401`/`403` de *qualquer* provedor degrada para simulação offline com aviso no stderr e `is_mock=true`, em vez de gerar traceback. Outras falhas (ex.: HTTP `500`) continuam gerando erro.
- 📊 **Métricas de ROI honestas**: os contadores de economia são rotulados como estimativas heurísticas, o modelo de premissas é impresso e o `--json` expõe `estimates_are_heuristic`.
- 📖 **OpenRouter documentado como alpha**: exige acesso alpha aprovado; o endpoint e o modelo `typesafe/jev-1.13` não são públicos, então ele deixou de ser apresentado como provedor turnkey.
- 🧩 **Paridade de contrato**: Padronização da chave `workflow_phase` (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) na CLI, SDK e ferramentas MCP do `nudge-gate`.
- 🚦 **Gate de release endurecido**: o `release.yml` agora exige toda a matriz de CI (Linux/macOS/Windows, Python 3.9-3.13, Node 18-22, Rust) via workflow reutilizável antes de publicar no PyPI, npm ou crates.io — uma CI vermelha não consegue mais publicar uma release.
- 🧹 **Zero avisos de clippy** em todo o workspace Rust.
- 🧩 **Paridade heurística tri-runtime**: o motor TypeScript agora pontua uma asserção explícita exatamente como Python e Rust, então o snippet de precedência da regra 04 (`FAIL` + `Expected:`/`Received:` em linhas separadas contendo nome de módulo) é `deep_logic`/`skip_llm=false` em todos os runtimes. Asserções em múltiplas linhas são detectadas, e mensagens como `Port 8080 is already in use` são `flaky_transient`.
- 🧪 **Bateria de 197 Testes**: 100% de aprovação em 197 testes (107 Python, 47 Rust, 43 TypeScript) na v0.1.11; substituída pela bateria de 211 testes na v0.1.12.

## 🌟 O que há de Novo na v0.1.10

- 🛡️ **Servidor MCP Nativo em Rust (`packages/rust/src/mcp.rs`)**: Servidor MCP stdio JSON-RPC 2.0 de alto desempenho para o runtime Rust (`jev mcp` / `jev-harness mcp`), garantindo paridade funcional total com Python e TypeScript nos 6 gates de decisão.
- ⚡ **Lock Atômico de Concorrência em Sessão (`fcntl.flock`)**: Bloqueio transacional seguro em `session.py` garantindo 0% de corrupção ou perda de contadores sob execução simultânea massiva de processos de agentes.
- 🔄 **Fallback Seguro no Provedor OpenCode Zen**: Fallback automático e transparente para simulação heurística offline em caso de HTTP 401/403 com chaves comunitárias default (`zen`), eliminando quebras silenciosas.
- 🛠️ **Unificação de Subcomandos CLI (`init` e `metrics`)**: Disponibilidade uniforme dos comandos `init` (scaffolding de repositório e adaptadores) e `metrics` (telemetria de ROI e economia de tokens) em Python, TypeScript e Rust.
- 📐 **Paridade Rígida de Esquemas JSON**: Disponibilidade simultânea de `action_recommendation` + `recommendation` e `reasoning_summary` + `summary` nas saídas JSON e ferramentas MCP nos 3 runtimes.
- 🧪 **Bateria Oficial de 149 Testes**: 100% de aprovação em 149 testes (86 Python, 34 Rust, 29 TypeScript) com latência abaixo de 100µs em Rust.

---

## 🌟 O que há de Novo na v0.1.9

- 🆓 **Integração com Provedor Gratuito Command Code**: Inferência gratuita via Command Code (Acordo de $0.00/M - modelo `typesafe/jev`) com detecção automática em `~/.commandcode/auth.json` (`CMD_API_KEY`).
- 🚪 **6º Gate de Decisão Semântica (Continuation Nudge)**: Avalia se o agente pausou prematuramente com trabalho pendente ou arquivos modificados sem teste, aplicando nudges inteligentes e respeitando permissões do usuário.
- 🔌 **Suporte Completo em CLI & MCP**: Subcomando `nudge-gate` (alias: `nudge`) e ferramenta MCP `jev_should_nudge_continuation`.

---

## 🌟 O que há de Novo na v0.1.8

- 🏛️ **Paridade com Contratos Astra-Ares v0.2.1**: Endpoints nativos e modelos padrão para OpenRouter (`https://openrouter.ai/api/alpha/decisions`, `typesafe/jev-1.13`), Vercel AI Gateway (`https://ai-gateway.vercel.sh/v1/evaluate`, `typesafe-ai/jev`, aceitando `VERCEL_API_KEY`, `AI_GATEWAY_API_KEY`, `VERCEL_AI_GATEWAY_API_KEY`), TypeSafe AI direto (`https://api.typesafe.ai/v1/systemone`) e OpenCode Zen (`https://opencode.ai/zen/v1/systemone`).
- ⚡ **Escala de 8 Níveis de Raciocínio & Dialetos**: Suporte a `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra` via `--supported-efforts` / `supportedEfforts`. Mapeamento correto de desativação de CoT (`none` / `minimal`) para DeepSeek (`extra_body.thinking.type: disabled`), Qwen (`enable_thinking: false`), Anthropic (`thinking.type: disabled`), Kimi (`extra_body.thinking: false`) e MiMo (`thinking.type: disabled`).
- 🔄 **Effort Leasing Multi-Geração**: Leasing de estabilidade multi-passo (`lease_steps` / `leaseSteps`: 1, 2, 5, 10 gerações) com clamp seguro (`max_lease_steps >= 1`), alocando 5 para passos mecânicos, 1 para erros/exceções e 2 para passos padrão.
- 🔒 **Redação de Segredos Zero-Trust**: Ocultamento automático (`[REDACTED]`) de `Bearer ...`, `sk-...`, `vck_...` e chaves configuradas em todas as mensagens de erro HTTP nos 3 runtimes.
- 🌐 **Paridade Poliglota e Multilíngue**: Classificação semântica idêntica para 9 linguagens de programação (Python, TypeScript/Node, Rust, Go, Java, C#, Ruby, C++) e 3 idiomas naturais (EN, PT-BR, ES).
- 🛡️ **Defesa Reforçada contra Vetores Adversariais (Red-Team)**: Resistência a colisão em `verify_step_completion` (nunca valida falhas reais mesmo com termos positivos) e `should_abort_trajectory` (não aborta progresso legítimo), além de proteção contra prompt injection em `modulate_reasoning_effort`.
- 🔌 **Evolução de CLI & Ferramental MCP**: Suporte a `--supported-efforts` e `--max-lease-steps` em todos os binários CLI e schemas MCP, com `lease_steps` presente no JSON de retorno.
- 🧪 **Bateria Expandida de 138 Testes**: 100% de aprovação em 138 testes (79 Python, 31 Rust, 28 TypeScript) com latência $p99 < 90\mu\text{s}$ no Rust.

---

## 🌟 O que há de Novo na v0.1.7

- 📊 **Benchmarks Empíricos Tri-Runtime & Garantia < 500µs Comprovada**: Adicionada tabela de benchmarks de latência empírica ($p50$, $p95$, $p99 < 500\mu\text{s}$) nos três runtimes (Python, TypeScript e Rust), com 1.000 iterações em suíte automatizada.
- ⚡ **Otimização do Engine em Rust**: Cache de expressões regulares com `std::sync::LazyLock` e clientes fallback zero-allocation nos gates, reduzindo o $p99$ da triagem em Rust para **37.5µs** e a simulação pura System One para **1.3µs**.
- 🛠️ **Paridade Total da CLI TypeScript & MCP Nativo**: Hardening no tratamento de códigos de saída Unix (código `2` para comando ausente ou argumentos inválidos) e suporte a campos duplos em camelCase + snake_case em todos os comandos JSON da CLI e ferramentas MCP nativas (`skip_llm`, `should_abort`, `provider_params`, `is_reasoning_supported`).
- 🚀 **Aceleração Heurística em Memória**: Adicionado parâmetro `record_session: bool = False` para desacoplar verificações em memória no SDK de operações de I/O em disco, atingindo latência $p99$ sub-150µs em Python sem perder a telemetria completa nas execuções via CLI.
- 🧪 **Bateria Completa de 123 Testes**: 100% de aprovação em 123 testes (73 Python, 26 Rust, 24 TypeScript) com zero avisos de compilação.

---

## 🌟 O que há de Novo na v0.1.6

- 🛡️ **Salvaguardas Expandidas para Modelos Direct**: Identifica automaticamente modelos single-pass (`gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `claude-3-5-haiku`, `llama-3.3`), injetando `{}` para evitar erros fatais de HTTP 400 nos 3 runtimes.
- 🧠 **Aviso de Risco de Cache no Contexto da Sessão**: Novo parâmetro `--session-context-tokens` na CLI e ferramenta MCP emite alerta preventivo de `HIGH CACHE RISK` quando o contexto excede 30.000 tokens.
- 💻 **CLI TypeScript `reasoning-effort` & Servidor MCP Nativo Zero-Dependency**: Suporte nativo completo na linha de comando TypeScript via `npx @ismaelsoilet/jev-harness reasoning-effort` e servidor MCP stdio nativo via `npx @ismaelsoilet/jev-harness mcp`.
- 🧪 **Heurísticas Adversariais Reforçadas & Bateria de 122 Testes**: 100% de aprovação em 122 testes (73 Python, 25 Rust, 24 TypeScript).

---

## 🗺️ Arquitetura & Roadmap

| Documento | O que responde |
| :--- | :--- |
| [System 1.5 — Arquitetura e fatos verificados](SYSTEM_1_5_PLAN.md) | Onde a ferramenta se posiciona entre o System 1 (Jev) e o System 2; o que está verificado hoje (v0.2.0) e o que falta |
| [System 1.5 — Ecossistema e oportunidades](SYSTEM_1_5_OPPORTUNITIES.md) | Comparação com Foreman, JevRouter, Winnow e jev-guard; 21 oportunidades priorizadas; o veredito "podemos ser 1.5?" |
| [System 1.5 — Plano de implementação](SYSTEM_1_5_IMPLEMENTATION.md) | Épicos, critérios de aceite, testes e sequenciamento (H1–H3) |
| [Guia Universal de Integração para Agentes](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md) | Configuração copy-paste de MCP, CLI, hooks e CI em qualquer projeto |

---

## 🙏 Agradecimentos

- **[Astra-Ares](https://github.com/miuuyy/Astra-Ares)** por Vechen ([@miu21590](https://x.com/miu21590)): Inspiração para a governança dinâmica de esforço de raciocínio por geração, leasing multi-geração (`lease_steps`), compilação de dialetos de provedores e redação de segredos zero-trust em mensagens de erro.
- **TypeSafe AI**: Criadores da arquitetura de decisão Jev System One.

---

## 📄 Licença

Distribuído sob a **Licença MIT**. Consulte [`LICENSE`](LICENSE) para mais informações.
