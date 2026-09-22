# ⚡ Jev Harness: Otimizador de Tokens e Decision Gate para Agentes de Codificação com IA

<p align="center">
  <a href="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml"><img src="https://github.com/ismaelsoilet/jev-harness/actions/workflows/ci.yml/badge.svg" alt="Status da CI"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=0" alt="Versão no PyPI"></a>
  <a href="https://www.npmjs.com/package/@ismaelsoilet/jev-harness"><img src="https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white" alt="Versão no npm"></a>
  <a href="https://crates.io/crates/jev-harness"><img src="https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white" alt="Versão no crates.io"></a>
  <a href="https://docs.rs/jev-harness"><img src="https://docs.rs/jev-harness/badge.svg" alt="docs.rs"></a>
  <a href="https://pypi.org/project/jev-harness/"><img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab.svg?logo=python&logoColor=white" alt="Versões do Python"></a>
  <a href="https://search.sigstore.dev/?logIndex=2908239242"><img src="https://img.shields.io/badge/provenance-Sigstore-blue?logo=npm" alt="npm Provenance"></a>
  <a href="https://github.com/ismaelsoilet/jev-harness/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="Licença MIT"></a>
  <a href="https://typesafe.ai"><img src="https://img.shields.io/badge/powered%20by-TypeSafe%20Jev%20System%20One-orange.svg" alt="TypeSafe Jev"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-purple.svg" alt="Compatível com MCP"></a>
  <a href="#"><img src="https://img.shields.io/badge/dependencies-0%20(pure%20stdlib)-success.svg" alt="Zero Dependências"></a>
</p>

<p align="center">
  <b><a href="README.md">🇬🇧 English</a> | <a href="README.pt-BR.md">🇧🇷 Português</a></b>
</p>

> **Pare de queimar 50.000 tokens de fronteira com pacotes ausentes, instabilidades de rede efêmeras e loops circulares da desgraça (doom loops).**
>
> `jev-harness` é um otimizador de tokens ultra-rápido com zero dependências externas, porta de triagem de erros de testes e guardrail semântico para agentes autônomos de codificação com IA (OpenCode, Command Code, Claude Code, Cursor, Antigravity IDE, Windsurf, Zed e Pi). Desenvolvido sobre o modelo de decisão não-autorregressivo **TypeSafe AI Jev System One**.
>
> 🤖 **Operando como Agente de IA?** Você **DEVE** ler o [`AGENTS.md`](AGENTS.md) ([Português](AGENTS.pt-BR.md)) antes de executar tarefas, e consultar o nosso [**Guia de Integração Universal para Agentes**](docs/AGENT_INTEGRATION_GUIDE.pt-BR.md) para plugar o harness no seu projeto em 2 minutos.

---

## 🎯 O Problema

Quando um agente autônomo de codificação encontra uma falha em testes ou um erro de compilação, o comportamento padrão é enviar 500 linhas de traceback bruto para um modelo de raciocínio de fronteira extremamente caro (GPT-6 Astra, Claude Fable 5.1).

| Cenário de Falha | Sem Jev Harness | Com Jev Harness |
| :--- | :--- | :--- |
| **Dependência ausente** (`ModuleNotFoundError`, `Cannot find module`, `TS2307`, `E0463`) | 💸 **50.000 tokens de LLM queimados** (~$0,50 - $2,50) + 15s de espera para sugerir `pip/npm install ...` | ⚡ **Triagem do Jev em 90ms ($0,00004)** → Ação: instalar dependência deterministicamente. **0 tokens de LLM**. |
| **Falha efêmera / Flaky** (timeout de rede, porta ocupada, ECONNREFUSED) | 💸 LLM alucina refatorações arquiteturais para "corrigir" uma falha passageira | ⚡ **Jev detecta erro transiente** → Retry automático único. **0 alterações no código**. |
| **Refatoração circular** (Doom Loop: tentando a mesma correção 3+ vezes) | 💸 **200.000+ tokens queimados** em ciclos infinitos | 🛑 **Disjuntor do Jev dispara** (`exit 1`) → Interrompe o loop e alerta o desenvolvedor. |
| **Erro de digitação / Formatação** | 💸 Modelo de raciocínio pesado usado para regex ou typo simples | ⚡ **Jev Route** direciona para script local ou Gemini 3.8 Flash. |

---

## 🏗️ Como Funciona: Sistema 1 vs. Sistema 2

O paradigma cognitivo de Daniel Kahneman aplicado à engenharia de agentes:
- **Sistema 1 (Rápido, Intuitivo, Calibrado):** O **Jev** toma decisões paralelas, não-autorregressivas e tipadas em **70ms a 300ms** a **$0,042 por 1M de tokens** ($0 tokens de saída).
- **Sistema 2 (Lento, Deliberativo, Generativo):** LLMs de fronteira (GPT-6 Astra, Claude Fable 5.1) escrevem código e resolvem problemas lógicos complexos.

```
       ┌────────────────────────────────────────────────────────┐
       │             Loop do Agente de Codificação              │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                      Execução de Comando/Teste
                                  │
                                  ▼
                         [Saída do Teste / Passo]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
   [PASSOU: Continua]                               [FALHA: Log de Erro]
                                                           │
                                                           ▼
                                               ┌───────────────────────┐
                                               │   Gate jev-harness    │
                                               │ (Jev System One 70ms) │
                                               └───────────┬───────────┘
                                                           │
                        ┌──────────────────────────────────┴──────────────────────────────────┐
                        ▼                                                                     ▼
             [skip_llm = True]                                                         [skip_llm = False]
       (Ambiente / Flaky / Trivial)                                                    (Erro Lógico Profundo)
                        │                                                                     │
                        ▼                                                                     ▼
           Ação Shell Determinística                                                  Encaminha Traceback
        (pip/npm install ou retry rápido)                                           ao Modelo de Fronteira
     ⚡ 0 Tokens de Fronteira / Solução Imediata                                    💸 Custo Reduzido em ~80%
```

---

## ✨ Recursos

- 🛡️ **Zero Dependências Externas:** Construído 100% com a biblioteca padrão do Python (`urllib.request`, `dataclasses`, `json`). Sem inchaço de pacotes, inicialização instantânea (< 50ms).
- 🔌 **Servidor MCP Universal:** Expõe ferramentas de decisão via stdio (`jev-mcp` ou `npx @ismaelsoilet/jev-harness mcp`) para Cursor, Claude Desktop, Antigravity, Windsurf, Zed e OpenCode.
- 🚦 **Conforme com a Filosofia UNIX:** Códigos de saída semânticos (`0` para sucesso/skip_llm, `1` para abort/defeito lógico, `2` para erro de sintaxe) permitem pipes limpos: `pytest | jev-harness test-gate`.
- 🔄 **Simulação Heurística Offline:** Sem internet ou sem chave de API, o motor heurístico local assume instantaneamente (< 500µs) para garantir que sua CI e agentes nunca quebrem.
- 🌐 **Múltiplos Provedores:** Suporte integrado a TypeSafe AI direto, OpenCode Zen e OpenRouter.

---

## 🚀 Início Rápido

### 1. Instalação nos 3 Ecossistemas
Disponível nos três principais registries sem dependências externas de runtime:

| Ecossistema | Registry | Pacote / Comando | Status |
| :--- | :--- | :--- | :--- |
| **Python** | [PyPI](https://pypi.org/project/jev-harness/) | `pip install jev-harness` | [![PyPI](https://img.shields.io/pypi/v/jev-harness.svg?color=blue&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/jev-harness/) |
| **TypeScript / Node** | [npm](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) | `npm install @ismaelsoilet/jev-harness` | [![npm](https://img.shields.io/npm/v/@ismaelsoilet/jev-harness.svg?color=cb3837&logo=npm&logoColor=white)](https://www.npmjs.com/package/@ismaelsoilet/jev-harness) |
| **Rust** | [crates.io](https://crates.io/crates/jev-harness) | `cargo add jev-harness` | [![crates.io](https://img.shields.io/crates/v/jev-harness.svg?color=dea584&logo=rust&logoColor=white)](https://crates.io/crates/jev-harness) |

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

Prioridade de resolução de credenciais:
1. Variáveis de ambiente (`TYPESAFE_API_KEY`, `CMD_API_KEY`, `COMMAND_CODE_API_KEY`, `OPENCODE_API_KEY`, `OPENROUTER_API_KEY` ou `AI_GATEWAY_API_KEY`)
2. Arquivo `.jev.json`, `.env` na raiz do repositório ou `~/.commandcode/auth.json`
3. Configuração global `~/.config/jev/credentials.env`
4. **Fallback para Simulação Autônoma**: ativo quando não há credenciais configuradas e em falhas de autenticação HTTP `401`/`403` de **qualquer** provedor. O motor imprime `[JEV WARNING]` no stderr e todo resultado degradado é sinalizado com `is_mock=true`. Outras falhas (ex.: HTTP 500) continuam gerando erro, para que indisponibilidades reais permaneçam visíveis.

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
| `api_key` / `provider` | string | — | Credenciais opcionais. Variáveis de ambiente têm precedência. |

Os valores são limitados a `[0, 1]`, e um arquivo corrompido degrada para os padrões em vez de quebrar a CI. As mesmas chaves funcionam de forma idêntica em Python, TypeScript e Rust.

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

Em vez de prender uma sessão inteira de agente em raciocínio pesado e lento (ou arriscar bugs rodando exclusivamente em raciocínio baixo), o Astra-Jev avalia a demanda cognitiva do próximo passo em **< 500µs localmente (70ms remoto)**.

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
- Se uma tarefa falhar 2 vezes seguidas sem progresso, execute `jev_should_abort_trajectory` para quebrar loops circulares.
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
Injete o parâmetro `reasoning_effort: "low" | "medium" | "high"` no nível raiz do payload da API. Zero mutação no histórico de mensagens = 100% do cache de prefixo preservado ao longo de 50+ turnos.

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
jev-harness = "0.1.11"
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
```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.1.11
    hooks:
      - id: jev-test-gate
```

### Hook do Husky (`.husky/pre-commit`)
```bash
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate || exit 1
```

---

## 📊 Economia e Benchmarks (Fronteira Setembro de 2026)

### Economia de Tokens e Custos

| Métrica | Raciocínio de Fronteira 2026 (GPT-6 Astra, Claude Fable 5.1) | Tier de Agentes Rápidos (Gemini 3.8 Flash) | TypeSafe Jev System One (`jev-harness`) |
| :--- | :--- | :--- | :--- |
| **Preço de Entrada** | $10,00 / 1M tokens | $0,75 / 1M tokens | **$0,042 / 1M tokens (~238x mais barato)** |
| **Preço de Saída** | $50,00 / 1M tokens | $3,75 / 1M tokens | **$0,00 (Grátis - Não-autorregressivo)** |
| **Latência** | 10.000ms – 30.000ms | 1.500ms – 4.000ms | **70ms – 300ms (~100x mais rápido)** |
| **Estrutura de Saída**| Prosa livre & streaming de tokens | Chamadas estruturadas de ferramentas | **Estritamente tipado: Choice, Score, Noul** |
| **Determinismo** | Raciocínio estocástico | Geração estocástica | **Limites calibrados com zero alucinação** |

### Benchmarks Heurísticos Offline Tri-Runtime (Garantia Local < 500µs)

Quando em modo de simulação offline (`--mock` ou durante partições de rede), o `jev-harness` executa os gates de decisão System One localmente sem latência externa de rede. Todos os gates satisfazem rigorosamente o contrato **$p99 < 500\mu\text{s}$** em todos os três ambientes de execução ($N = 1.000$ iterações medidas empiricamente):

| Runtime | Gate de Decisão | $p50$ | $p95$ | $p99$ | Média | Conformidade |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Rust** (`packages/rust`) | `triage_test_failure` | **10.3 µs** | **22.0 µs** | **37.5 µs** | 13.5 µs | ✅ **PASS** (< 38 µs) |
| | `should_abort_trajectory` | **6.2 µs** | **10.0 µs** | **22.9 µs** | 7.0 µs | ✅ **PASS** (< 23 µs) |
| | `modulate_reasoning_effort` | **5.1 µs** | **7.1 µs** | **15.3 µs** | 5.6 µs | ✅ **PASS** (< 16 µs) |
| | *puro `simulate_system_one`* | **0.7 µs** | **0.9 µs** | **1.3 µs** | 1.0 µs | ✅ **PASS** (< 2 µs) |
| **TypeScript** (`packages/ts`) | `triageTestFailure` | **13.6 µs** | **37.5 µs** | **213.9 µs** | 26.9 µs | ✅ **PASS** (< 214 µs) |
| | `shouldAbortTrajectory` | **7.8 µs** | **21.6 µs** | **93.7 µs** | 10.5 µs | ✅ **PASS** (< 94 µs) |
| | `modulateReasoningEffort` | **6.3 µs** | **17.1 µs** | **89.4 µs** | 9.0 µs | ✅ **PASS** (< 90 µs) |
| **Python** (`src/jev_harness`) | `triage_test_failure` | **53.5 µs** | **95.0 µs** | **135.6 µs** | 63.1 µs | ✅ **PASS** (< 136 µs) |
| | `should_abort_trajectory` | **37.0 µs** | **67.1 µs** | **88.8 µs** | 42.3 µs | ✅ **PASS** (< 89 µs) |
| | `modulate_reasoning_effort` | **33.7 µs** | **62.6 µs** | **103.7 µs** | 41.0 µs | ✅ **PASS** (< 104 µs) |

> ⚡ **Garantia de Zero-Overhead:** Como as verificações heurísticas operam na escala de dezenas de microssegundos, canalizar os executores de teste ou hooks pré-execução via `jev-harness` introduz overhead imperceptível nos ciclos do agente, evitando queimas fúteis de tokens e loops circulares de falha.

---

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
- 🧪 **Bateria de 184 Testes**: 100% de aprovação em 184 testes (102 Python, 43 Rust, 39 TypeScript).

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

## 🙏 Agradecimentos

- **[Astra-Ares](https://github.com/miuuyy/Astra-Ares)** por Vechen ([@miu21590](https://x.com/miu21590)): Inspiração para a governança dinâmica de esforço de raciocínio por geração, leasing multi-geração (`lease_steps`), compilação de dialetos de provedores e redação de segredos zero-trust em mensagens de erro.
- **TypeSafe AI**: Criadores da arquitetura de decisão Jev System One.

---

## 📄 Licença

Distribuído sob a **Licença MIT**. Consulte [`LICENSE`](LICENSE) para mais informações.
