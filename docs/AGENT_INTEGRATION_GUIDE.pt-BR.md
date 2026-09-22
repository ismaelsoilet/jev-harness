# 🤖 Jev Harness: Guia Universal de Integração para Agentes de IA

**[ 🇬🇧 English ](AGENT_INTEGRATION_GUIDE.md) | [ 🇧🇷 Português ](AGENT_INTEGRATION_GUIDE.pt-BR.md)**

> **Manual de implementação pronta para uso (turnkey) para agentes autônomos de codificação com IA (Claude Code, OpenAI Codex, Pi, Oh My Pi, CommandCode, Cursor, Antigravity, OpenCode, Windsurf, Zed, Devin, Aider) e engenheiros equipando fluxos de agentes em QUALQUER projeto.**

---

## 🧭 Visão Geral: Por que Integrar o Jev Harness?

Agentes autônomos de codificação com IA desperdiçam de **70% a 80% do seu orçamento de tokens e tempo de execução** em falhas mecânicas e previsíveis:
1. **Pacotes ausentes e erros de ambiente** (`ModuleNotFoundError`, `Cannot find module`, `E0463`). Agentes rotineiramente enviam 500 linhas de traceback para modelos de fronteira (GPT-6 Astra, Claude Fable 5.1), gastando entre $0,50 e $2,50 apenas para responder `npm install` ou `pip install`.
2. **Loops circulares da desgraça (Doom Loops)**: O agente tentando a mesma refatoração incorreta 4 vezes seguidas, queimando mais de 200 mil tokens antes de falhar.
3. **Latência interna de raciocínio**: Modelos de raciocínio (DeepSeek V4.1-Flash, Qwen 3.8 Max, o3-mini) entrando em loops de pensamento interno de 3 minutos apenas para executar um `git status` ou ler um arquivo de 10 linhas.

**O `jev-harness` é o reflexo cognitivo do Sistema 1 para agentes de IA**:
- **Latência de 70ms remota / <500µs local** (motor de decisão não-autorregressivo e tipado).
- **$0,042 por 1 milhão de tokens de entrada / $0,00 tokens de saída** (até **238x mais barato** que modelos de fronteira).
- **Zero dependências externas de runtime** em Python (stdlib pura), TypeScript (zero dependências) e Rust (Tokio/Serde).
- **Simulação heurística offline instantânea**: executa localmente mesmo sem chave de API ou conexão à internet.

---

## ⚡ Início Rápido: 4 Modos Universais de Integração

Escolha o modo mais adequado para o ambiente de execução do seu agente:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 REPOSITÓRIO DO SEU PROJETO             │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
     [Modo 1: Servidor MCP]         [Modo 2: Pipe Shell / CLI]      [Modo 3: SDK Nativo]
    Claude Code, Cursor,             Pi, Oh My Pi, Codex,            Python / TS / Rust
   CommandCode, Antigravity           pytest | jev-harness           Loops Customizados
```

---

### Modo 1: Servidor MCP Universal (Zero Código, Máxima Capacidade)

Se o seu agente roda em um ambiente compatível com MCP (**Claude Code, CommandCode, Cursor, Claude Desktop, Antigravity IDE, Windsurf, Zed, OpenCode**), exponha as ferramentas do Jev via entrada/saída padrão (stdio) em 30 segundos.

#### 1. Configuração Rápida

**Para o Claude Code (`claude` CLI da Anthropic):**
```bash
# Registre o MCP do Jev Harness diretamente no Claude Code
claude mcp add jev-harness -- npx -y @ismaelsoilet/jev-harness mcp

# Ou via Python:
claude mcp add jev-harness -- jev-mcp
```

**Para o CommandCode (`.commandcode/config.json`):**
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

**Para o Cursor (`.cursor/mcp.json` na raiz do projeto ou `~/.cursor/mcp.json` global):**
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
*(Ou se tiver Python instalado: `"command": "jev-mcp"`)*

**Para o Claude Desktop (`claude_desktop_config.json`):**
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

**Para a IDE Google Antigravity (`mcp_config.json`):**
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

#### 2. Ferramentas Disponíveis para o Agente via MCP:
- `jev_triage_test_failure`: Analisa o log de erro bruto. Retorna se deve pular o LLM e qual comando shell determinístico executar.
- `jev_should_abort_trajectory`: Avalia se o plano proposto repete falhas anteriores (disjuntor contra loops circulares).
- `jev_route_model_tier`: Sugere se deve usar script local, tier rápido (Gemini 3.8 Flash) ou tier de fronteira (Claude Fable 5.1 / GPT-6 Astra).
- `jev_verify_step_completion`: Avalia de forma determinística se os critérios do passo foram cumpridos.
- `jev_modulate_reasoning_effort`: Modula dinamicamente o esforço de raciocínio por geração (`low`, `medium`, `high`) e compila payloads para OpenAI, Anthropic, Gemini, DeepSeek e Qwen.
- `jev_get_telemetry`: Exibe economia de tokens da sessão, dólares economizados e loops circulares interrompidos.

---

### Modo 2: Pipelines Shell & CLI (Agnóstico à Linguagem)

Se o seu agente executa comandos via terminal (bash, zsh, pwsh), encadeie os comandos de teste com pipes Unix:

```bash
# Python / Pytest
pytest 2>&1 | jev-harness test-gate

# Node.js / Jest / Vitest / npm
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate

# Rust / Cargo
cargo test 2>&1 | jev test-gate
```

#### Códigos de Saída Semânticos:
- `0`: **Seguro para agir deterministicamente** (`skip_llm = true`). O Jev imprime a ação exata (ex: `pip install pytest-mock`).
- `1`: **Falha lógica profunda** (`skip_llm = false`) ou **Aborto Recomendado**. Apenas neste momento o agente deve acionar o modelo de fronteira.
- `2`: Erro de sintaxe ou de invocação.

#### Disjuntor de Trajetória Automatizado (Checar antes de repetir passos):
```bash
jev-harness abort-check \
  --plan "Rodar migração de banco com reset forçado de schema" \
  --history "Tentativa 1 falhou com timeout. Tentativa 2 falhou em foreign key constraint."
```
*Se retornar código `1`, o agente DEVE abortar a trajetória e solicitar alinhamento com o usuário.*

---

### Modo 3: Integração com SDK Nativo (Para Frameworks de Agentes)

Se você está desenvolvendo um loop autônomo customizado (LangChain, LlamaIndex, CrewAI, AutoGen ou código próprio em Python/TypeScript/Rust):

#### Python (`pip install jev-harness`)
```python
from jev_harness import JevClient, triage_test_failure, should_abort_trajectory, modulate_reasoning_effort

client = JevClient()

# 1. Triagem do traceback antes de chamar o LLM
triage = triage_test_failure(raw_traceback, client=client)
if triage.skip_llm:
    # Executa a ação determinística sem queimar tokens de fronteira
    execute_shell_command(triage.action_recommendation)
else:
    # Apenas falhas lógicas reais vão para o modelo de fronteira
    call_frontier_llm(triage.action_recommendation)

# 2. Verificar loops circulares antes de repetir passos
abort = should_abort_trajectory(proposed_step, history_summary, client=client)
if abort.should_abort:
    notify_user_dead_end(abort.reasoning_summary)

# 3. Modular esforço de raciocínio (Astra-Jev)
effort = modulate_reasoning_effort(
    context="git diff para inspecionar arquivos alterados",
    provider="deepseek",
    model="deepseek-v4.1-flash",
    client=client,
)
# Injetar effort.provider_params no payload da API
```

#### TypeScript / Node.js (`npm install @ismaelsoilet/jev-harness`)
```typescript
import { triageTestFailure, shouldAbortTrajectory, modulateReasoningEffort } from "@ismaelsoilet/jev-harness";

// 1. Triagem
const triage = await triageTestFailure(errorOutput);
if (triage.skipLlm) {
  await runShell(triage.actionRecommendation);
}

// 2. Verificação de aborto
const abort = await shouldAbortTrajectory(nextAction, pastAttempts);
if (abort.shouldAbort) {
  throw new Error(`Trajetória interrompida pelo Jev: ${abort.reasoningSummary}`);
}

// 3. Modulação dinâmica de raciocínio (Astra-Jev)
const effort = await modulateReasoningEffort("Renomeação mecânica de arquivos", "anthropic");
// Repassar effort.providerParams ao SDK da Anthropic
```

#### Rust (`cargo add jev-harness`)
```rust
use jev_harness::gates::{triage_test_failure, should_abort_trajectory, modulate_reasoning_effort};

let triage = triage_test_failure(error_log, None).await?;
if triage.skip_llm {
    apply_deterministic_fix(&triage.action_recommendation);
}
```

---

### Modo 4: Guardrails em Git & CI/CD

Proteja o repositório automaticamente antes de commits ou runs de CI:

**Em `.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.1.6
    hooks:
      - id: jev-test-gate
```

**No GitHub Actions (`.github/workflows/ci.yml`):**
```yaml
- name: Executar Testes com Proteção Jev
  run: |
    npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
```

---

## 🧠 O Protocolo de Decisão do Agente (Regras Operacionais)

Para tornar seu agente completamente autônomo e econômico, injete estas 3 regras operacionais nas instruções de sistema:

```
                          [Agente Encontra Falha em Teste/Build]
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   jev-harness test-gate   │
                               │  (Decisão Rápida Sistema 1)│
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
             [skip_llm = true]                             [skip_llm = false]
       (Pacote Ausente / Flaky / Trivial)                   (Erro Lógico Profundo)
                      │                                             │
                      ▼                                             ▼
         Executa Ação Determinística                   Envia Log Filtrado ao
       (ex: npm install / retry imediato)            Modelo de Fronteira (Sistema 2)
       ⚡ 0 Tokens Queimados / Resolução              💸 Tokens Economizados em ~80%
```

### Regra 1: Triagem Zero-LLM em Falhas
- **NUNCA** repasse tracebacks brutos (>20 linhas) diretamente para um modelo de raciocínio de fronteira.
- Sempre passe pelo `jev-harness test-gate` (ou ferramenta MCP `jev_triage_test_failure`) primeiro.
- Se `skip_llm == true`, execute a ação determinística descrita em `action_recommendation`.

### Rule 2: Disjuntor em Ações Repetitivas
- Se uma operação falhar duas vezes consecutivas, o agente **DEVE** executar `jev-harness abort-check` (ou `jev_should_abort_trajectory`).
- Se `should_abort == true`, o agente deve **PARAR**, explicar o beco sem saída ao usuário e solicitar direcionamento em vez de queimar mais tokens em loop.

### Regra 3: Modulação de Raciocínio por Geração (Astra-Jev)
- Para operações mecânicas (`git status`, ler arquivos, formatação, edições pontuais), defina o esforço de raciocínio como `low` ou desative o thinking para eliminar latência de 3 minutos e economizar até $1,15 por chamada.
- Reserve raciocínio `high` apenas para arquitetura, condições de corrida distribuídas ou algoritmos complexos.

---

## 🔌 Receitas Detalhadas por Harness de Agente

### 1. Claude Code (`claude` CLI da Anthropic)
O Claude Code é a ferramenta agentic de linha de comando oficial da Anthropic. Ele conecta diretamente a servidores MCP locais e executa comandos bash de forma autônoma.

#### Registro Rápido:
```bash
# Registre via npm/npx
claude mcp add jev-harness -- npx -y @ismaelsoilet/jev-harness mcp

# Ou via Python CLI
claude mcp add jev-harness -- jev-mcp
```

#### Como funciona dentro do Claude Code:
1. Quando o Claude Code executa uma suíte de testes ou comando de compilação via bash e ele falha, o Claude Code chama a ferramenta MCP `jev_triage_test_failure`.
2. Se `skip_llm == true`, o Claude Code imediatamente executa `triage.action_recommendation` (ex: `pip install pytest-mock` ou `npm install -D vitest`) **sem gerar um único token de raciocínio de fronteira**.
3. Para falhas repetitivas em refatorações multi-turnos, o Claude Code invoca `jev_should_abort_trajectory` antes de insistir em uma 3ª tentativa fracassada.

---

### 2. OpenAI Codex / Astra-Codex
Fluxos com OpenAI Codex (executores CLI, scripts autônomos e implementações do Astra-Codex) operam em loops rápidos de ferramentas multi-turnos.

#### Modulação de Raciocínio por Geração (Astra-Jev):
Conforme demonstrado por Vechen ([@miu21590](https://x.com/miu21590)), modelos de fronteira como o GPT-6 Astra queimam tempo e dólares excessivos quando tarefas puramente mecânicas rodam em esforço máximo de raciocínio.
```bash
# No passo anterior à geração do seu Codex:
jev-harness reasoning-effort \
  --context "Inspecionar diff do git e identificar imports modificados" \
  --target-provider openai \
  --model gpt-6-astra \
  --json
```

#### Integração com Zero Invalidação de Cache (KV Cache Preservado):
Injete o parâmetro resultante diretamente no payload raiz da API da OpenAI:
```python
effort = modulate_reasoning_effort(task_step, provider="openai", model="gpt-6-astra")

# A injeção na raiz do payload preserva 100% do prefixo do KV-cache na GPU por mais de 50 turnos:
response = openai_client.chat.completions.create(
    model="gpt-6-astra",
    messages=session_history,     # NUNCA altere o prefixo das mensagens!
    **effort.provider_params       # Injeta reasoning_effort: "low" | "medium" | "high"
)
```

---

### 3. Pi & Oh My Pi (`pi` / `oh-my-pi`)
O agente minimalista de terminal de Mario Zechner (`pi`) e harnesses comunitários como `oh-my-pi` foram desenhados para velocidade máxima e composição Unix nativa.

#### Execução via Pipes com Códigos de Saída Semânticos:
No Pi, comandos de teste e verificação são encadeados diretamente no `jev-harness test-gate`:
```bash
# Execução no terminal pelo Pi:
pytest 2>&1 | jev-harness test-gate
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
cargo test 2>&1 | jev test-gate
```

#### Lógica de Bifurcação Autônoma:
- **Código de Saída `0`** (`skip_llm = true`): O Jev identificou que o erro é uma dependência ausente, teste instável ou erro de ambiente. O Pi executa o comando determinístico automaticamente sem mandar o log para o LLM.
- **Código de Saída `1`** (`skip_llm = false`): Erro lógico profundo ou loop circular detectado. O Pi repassa o log filtrado de alto sinal para o modelo.

#### Hook de Shell para `oh-my-pi` (`~/.config/oh-my-pi/plugins/jev.sh`):
```bash
# Envolva comandos no Oh My Pi
jev_guard() {
  local cmd="$*"
  eval "$cmd" 2>&1 | jev-harness test-gate
  return ${PIPESTATUS[1]}
}
```

---

### 4. CommandCode
O CommandCode é um assistente autônomo de terminal focado em linha de comando. Ele suporta servidores MCP e hooks pré-comando.

#### Configuração (`.commandcode/config.json`):
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

#### Regras para CommandCode (`COMMANDCODE.md` na raiz do repositório):
```markdown
# Regras Autônomas para CommandCode
- Sempre passe saídas de build/testes por `jev-harness test-gate`.
- Se o código de saída for 0 com skip_llm=true, execute a recomendação de ação imediatamente.
- Execute `jev-harness abort-check` antes de tentar novamente qualquer comando que falhou uma vez.
```

---

## 📋 Snippets de Regras Prontos para Copiar e Colar

Copie o snippet adequado diretamente no arquivo de configuração do seu agente no projeto:

### Para o Claude Code (`CLAUDE.md`):
```markdown
# Protocolo Jev Harness para Claude Code
- Faça a triagem de erros de testes com `jev-harness test-gate --log <arquivo>` ou use a ferramenta MCP `jev_triage_test_failure`.
- Quando `skip_llm` for true, execute o comando determinístico (ex: instalação de pacote) imediatamente. Não delibere.
- Previna loops circulares checando passos de recuperação com `jev-harness abort-check`.
- Para comandos mecânicos no terminal ou leitura de arquivos, use `jev_modulate_reasoning_effort` com effort="low".
```

### Para o OpenAI Codex / Astra-Codex (`CODEX.md` ou `AGENTS.md`):
```markdown
# Protocolo de Raciocínio Dinâmico Astra-Jev
- Module o esforço de raciocínio por geração: use `reasoning_effort="low"` para inspeções mecânicas e `"high"` para arquitetura.
- Mantenha o prefixo das mensagens intacto: passe parâmetros no payload raiz da API para preservar 100% do prompt cache.
- Filtre falhas de compilação com `jev-harness test-gate` antes de reenviar para o GPT-6 Astra.
```

### Para o Pi & Oh My Pi (`PI.md` ou `~/.pi_rules`):
```markdown
# Regras Econômicas para Pi / Oh My Pi
- Encadeie execuções de testes: `npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate` (ou `pytest 2>&1 | jev-harness test-gate`).
- Se o código de saída for 0, auto-aplique o comando recomendado.
- Se o código de saída for 1, resuma a falha com alto sinal para o modelo.
```

### Para o CommandCode (`COMMANDCODE.md`):
```markdown
# Salvaguardas e Gate de Tokens no CommandCode
- Chame `jev_triage_test_failure` em comandos com código de saída diferente de zero.
- Siga estritamente o veredito `skip_llm` para preservar cotas de API.
- Aborte loops circulares quando `jev_should_abort_trajectory` retornar true.
```

### Para o Cursor (`.cursorrules` ou `.cursor/rules/jev.mdc`):
```markdown
# Protocolo de Otimização de Tokens com Jev Harness

Antes de gastar tokens com falhas de compilação ou testes:
1. Sempre passe a saída do teste por `jev-harness test-gate` ou use a ferramenta MCP `jev_triage_test_failure`.
2. Se `skip_llm` for true, execute a ação recomendada imediatamente sem consultar o modelo.
3. Se uma tarefa falhar em 2 tentativas seguidas, invoque `jev_should_abort_trajectory` antes de propor a terceira.
4. Se `should_abort` for true, interrompa a execução e relate o bloqueio ao usuário.
```

### Para a IDE Google Antigravity (`GEMINI.md` ou `.agents/rules/`):
```markdown
# Economia de Tokens & Salvaguardas de Decisão
- Sempre filtre erros de compilação e teste com `jev-harness test-gate`.
- Respeite estritamente o veredito `skip_llm` para preservar cotas.
- Proteja trajetórias longas contra loops circulares com `jev-harness abort-check`.
```

---

## 📊 Economia e Impacto Comprovado

| Situação | Loop de Agente Padrão | Agente com Jev Harness | Impacto |
| :--- | :--- | :--- | :--- |
| **Erro de Módulo Ausente** | Envia 300 linhas ao Claude Fable 5.1 (~50k tokens, ~$0,80) | Jev faz triagem em 80ms (`$0,00004`). Instala pacote. | **99,9% economia de custo, 15s poupados** |
| **Flaky / Instabilidade de Rede** | Reescreve conexões ou alucina refatoração | Jev detecta falha efêmera. Tenta de novo 1 vez. | **Zero alterações de código desnecessárias** |
| **Loop Circular de 3 Tentativas** | Gasta mais de 180k tokens e corrompe o código | Jev aborta na 2ª tentativa (`exit 1`). Para o loop. | **Economiza ~$5,00 e previne bugs** |
| **Latência de Thinking em Tool Calls** | DeepSeek/Qwen espera 180s em CoT interno para `git status` | Astra-Jev define `effort="low"`. Responde em 1,5s. | **178s de espera eliminados** |

---

## 🔗 Recursos Relacionados

- 🏛️ [Planta Arquitetural & Constituição](../AGENTS.md)
- 🌐 [Governança de Modelos de Fronteira (2026)](../.agents/rules/03_model_governance_and_frontier_registry.md)
- 📦 [Repositório no GitHub](https://github.com/ismaelsoilet/jev-harness)
- 🐍 [Pacote no PyPI](https://pypi.org/project/jev-harness/)
- 🟦 [Pacote no npm](https://www.npmjs.com/package/@ismaelsoilet/jev-harness)
- 🦀 [Pacote no crates.io](https://crates.io/crates/jev-harness)
