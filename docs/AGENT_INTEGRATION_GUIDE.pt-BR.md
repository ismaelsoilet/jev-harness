# 🤖 Jev Harness: Guia Universal de Integração para Agentes de IA

**[ 🇬🇧 English ](AGENT_INTEGRATION_GUIDE.md) | [ 🇧🇷 Português ](AGENT_INTEGRATION_GUIDE.pt-BR.md)**

> **Nota para integradores:** o `AGENTS.md` do repositório jev-harness é o ficheiro de governança *daquele* repositório (protocolo de release, registro de modelos). Você **não** precisa dele para integrar a ferramenta no seu projeto — este guia é autossuficiente.

> **Manual de implementação pronta para uso (turnkey) para agentes autônomos de codificação com IA (Claude Code, OpenAI Codex, Pi, Oh My Pi, CommandCode, Cursor, Antigravity, OpenCode, Windsurf, Zed, Devin, Aider) e engenheiros equipando fluxos de agentes em QUALQUER projeto.**

> **Onde isto se encaixa:** o `jev-harness` é a camada de decisão de qualidade System 1.5 (triagem de testes, quebra de doom loops, veto de conclusão). Arquitetura, comparativo de ecossistema e roadmap: [Plano System 1.5](../SYSTEM_1_5_PLAN.md) · [Oportunidades](../SYSTEM_1_5_OPPORTUNITIES.md) · [Plano de implementação](../SYSTEM_1_5_IMPLEMENTATION.md).

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

> **📅 Validade do documento: verificado em 22/09/2026.**
> IDs de modelos, endpoints, tiers gratuitos e preços mudam semanalmente. **Se você é um agente de IA lendo isto e já se passaram mais de 30 dias desde 22/09/2026, re-verifique cada ID de modelo, endpoint e preço nos links de [Acesso a Provedores e Chaves de API](#-acesso-a-provedores-e-chaves-de-api) antes de confiar neles, e registre a data da sua própria verificação na documentação do projeto.** O modo offline `--mock` não precisa de verificação nem de chave.

---

## 🔑 Acesso a Provedores e Chaves de API

O `jev-harness` funciona de duas formas: **offline** (motor determinístico local, sem chave e sem rede) e **live** (decisão System One tipada via HTTPS). Escolha um provedor, obtenha a chave, exporte a variável e confirme com `jev-harness status`.

| Provedor | Como obter acesso | Ambiente | Endpoint | Custo |
| :--- | :--- | :--- | :--- | :--- |
| **Simulação offline (padrão)** | Nada a fazer — ativa quando não há credenciais configuradas | — | nenhum (100% local) | **Grátis** |
| **OpenCode Zen (tier gratuito)** | Entre em <https://opencode.ai/auth>, adicione dados de pagamento e copie sua API key. Modelo gratuito: `jev-1.13-free` (por tempo limitado) | `JEV_PROVIDER=opencode` + `OPENCODE_API_KEY=<chave>` | `https://opencode.ai/zen/v1/systemone` | `jev-1.13-free` grátis; `jev-1.13` $0,042/1M de entrada, saída grátis |
| **TypeSafe AI (direto)** | Crie conta em <https://console.typesafe.ai/> e gere uma API key. Docs: <https://docs.typesafe.ai/> (agentes podem buscar <https://docs.typesafe.ai/llms.txt>) | `TYPESAFE_API_KEY=<chave>` | `https://api.typesafe.ai/v1/systemone` | $42 por bilhão de tokens de entrada ($0,042/1M); saída grátis |
| **Command Code** | Cadastre-se em <https://commandcode.ai/signup> e rode `npm i -g command-code && cmd login` (guarda a chave em `~/.commandcode/auth.json`) | `CMD_API_KEY=<chave>` | `https://api.commandcode.ai/provider/v1/systemone` | Tier gratuito para dev solo; planos pagos a partir de $1/mês |
| **OpenRouter (alpha)** | Exige acesso alpha aprovado. ⚠️ `typesafe/jev-1.13` **não** está no catálogo público do OpenRouter e o endpoint retorna `401` sem credenciais alpha | `OPENROUTER_API_KEY=<chave>` | `https://openrouter.ai/api/alpha/decisions` | $0,042/1M quando disponível |
| **Vercel AI Gateway** | Credenciais de gateway da sua conta Vercel | `AI_GATEWAY_API_KEY=<chave>` | `https://ai-gateway.vercel.sh/v1/evaluate` | Depende do gateway |

**Ordem de resolução de credenciais:** variáveis de ambiente → `.jev.json` / `.env` do repositório → `~/.config/jev/credentials.env` global → `~/.commandcode/auth.json` → simulação offline.

### Verifique seu acesso em 5 segundos

```bash
jev-harness status                                        # provedor + modo LIVE/MOCK
echo "ModuleNotFoundError: No module named 'x'" | jev-harness test-gate --json
```

`"is_mock": true` significa que a resposta veio do motor determinístico local (sem rede). `"is_mock": false` significa que uma chamada System One real foi feita — veja **Privacidade** abaixo.

### 🔒 Privacidade: o que sai da sua máquina

| Modo | Tráfego de rede | Dados transmitidos |
| :--- | :--- | :--- |
| Offline (`--mock`, ou sem credenciais) | **Nenhum** | Nada |
| Live (qualquer provedor) | HTTPS até o endpoint do provedor | `model`, suas `questions` tipadas e o **log de falha cru** (cabeça 2.000 + cauda 4.000 caracteres, ~6 KB máx.) |
| Estado local (`<repo>/.jev/` ou `~/.config/jev`) | **Nenhum** | Contadores de sessão, **recibos de decisão** (apenas hashes + metadados, nunca logs brutos), o cache de decisões e o `usage` medido que o provedor reportou. Arquivos `0600`, diretório `0700`, limitados por TTL (`receipts_ttl_days`, `cache_ttl_seconds`) e tamanho (`receipts_max_entries`); o `init` adiciona `.jev/` ao `.gitignore`. Desligue os recibos com `"receipts": false`, `JEV_RECEIPTS=0` ou `--no-receipts`; ignore o cache com `--no-cache` |
| GitHub Action (`examples/github-action`) | Depende do engine escolhido | Offline (padrão) não transmite nada; `engine: live` envia o log capturado ao seu provedor — ver a linha acima para o que isso implica |

O triage live envia o log no campo `state`, e desde a v0.2.0 esse state é **redigido em todos os runtimes antes de ser transmitido**: material com cara de credencial (chaves de API, JWTs, tokens do GitHub/AWS, URLs de banco, chaves privadas) vira `[REDACTED]`, tanto no state quanto nas mensagens de erro. É higiene por forma, não uma camada de DLP — dados que não pareçam credencial (registros de clientes, identificadores internos) ainda trafegam — então mantenha `--mock` em repositórios com dados regulados.
**Regra prática:** logs de repositórios com dados regulados ou de clientes → rode agentes com `--mock` (100% local), ou confirme antes a política de retenção do provedor. O arquivo de telemetria `~/.config/jev/session.json` guarda trechos de erro e é gravado com permissão `0600`.

---

## ⚡ Início Rápido: 4 Modos Universais de Integração

> **Comece aqui:** nenhuma chave de API é necessária. Siga com o modo offline e adicione uma chave de provedor depois, apenas se quiser decisões live do modelo.

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

### Ferramentas MCP expostas pelo servidor (verified for the current release)

O servidor expõe **seis** ferramentas. Chame `tools/list` se precisar do schema ao vivo — os nomes de argumento abaixo são os que devem ser passados em `tools/call`:

| Ferramenta | Argumentos obrigatórios | Retorna |
| :--- | :--- | :--- |
| `jev_triage_test_failure` | `failure_log` | categoria, `skip_llm`, recomendação (execuções verdes retornam `no_failure`) |
| `jev_abort_check` | `proposed_step` (opcional: `recent_attempts_summary`) | `should_abort`, ação, viabilidade, resumo |
| `jev_route_task` | `task_description` | tier de modelo, modelo recomendado, justificativa |
| `jev_verify_completion` | `acceptance_criteria`, `produced_output` | `is_verified`, rigor, probabilidade |
| `jev_modulate_reasoning_effort` | `context` (opcional: `provider`, `model`, `session_context_tokens`, `supported_efforts`, `max_lease_steps`) | nível de esforço + parâmetros do provedor |
| `jev_should_nudge_continuation` | `transcript_tail` (opcional: `previous_nudge_summary`, `threshold`) | `should_nudge`, fase do workflow, justificativa |

#### Smoke test do MCP em 20 segundos (qualquer runtime)

```bash
# Python (instalado com o pacote)
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | jev-mcp

# Virtualenv do projeto (sem ativar; use o caminho absoluto)
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | ./.venv/bin/jev-mcp

# Node (sem instalação)
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | npx -y @ismaelsoilet/jev-harness mcp | head -2
```

Uma chamada real tem este formato (a resposta é JSON em `result.content[0].text`):

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"jev_triage_test_failure","arguments":{"failure_log":"ModuleNotFoundError: No module named scipy"}}}' \
  | jev-mcp
```

> Nota de quoting no shell: sequências como `\'` dentro de aspas simples **não** são válidas em shell nem em JSON. Para payloads com aspas, quebras de linha ou texto não-ASCII, escreva um pequeno cliente stdio (ou use a CLI com `--log <arquivo>`), em vez de embutir o log no `printf`.

#### Cliente MCP stdio mínimo (para logs com aspas, quebras de linha ou texto não-ASCII)

Embutir um traceback real no `printf` é frágil. Salve como `mcp_triage.py` e chame `python3 mcp_triage.py caminho/para/falha.log`:

```python
import json, subprocess, sys

log = open(sys.argv[1], encoding="utf-8", errors="replace").read()
messages = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "jev_triage_test_failure", "arguments": {"failure_log": log}}},
]
payload = "".join(json.dumps(m) + "\n" for m in messages)
proc = subprocess.run([sys.executable, "-m", "jev_harness.mcp_server"], input=payload,
                      capture_output=True, text=True)
for line in proc.stdout.splitlines():
    msg = json.loads(line)
    if msg.get("id") == 2:
        print(msg["result"]["content"][0]["text"])
```

> **Nota sobre virtualenv.** Um cliente MCP não herda o seu shell: ele inicia o servidor com um ambiente mínimo. Se o `jev-harness` estiver instalado dentro de um virtualenv do projeto, aponte o cliente para o caminho absoluto (`"command": "/caminho/absoluto/.venv/bin/jev-mcp"`), ou use a forma `npx`, que não precisa de Python.

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

**Para o OpenCode (`.opencode.json`, no projeto ou global):**
```json
{
  "mcp": {
    "jev-harness": {
      "type": "local",
      "command": ["npx", "-y", "@ismaelsoilet/jev-harness", "mcp"],
      "enabled": true
    }
  }
}
```
*(Confira o schema da sua versão do OpenCode; a forma `npx` não precisa de Python.)*

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

#### 2. Ferramentas disponíveis para o agente via MCP:

Os nomes e argumentos exatos estão na tabela no topo deste guia. Resumo:

- `jev_triage_test_failure` (`failure_log`): tria a saída de erro; informa se a chamada ao LLM pode ser evitada e qual ação determinística executar.
- `jev_abort_check` (`proposed_step`, `recent_attempts_summary`): quebra loops de repetição ou planos inviáveis.
- `jev_route_task` (`task_description`): sugere script, tier rápido ou tier de fronteira.
- `jev_verify_completion` (`acceptance_criteria`, `produced_output`): avalia se os critérios foram satisfeitos.
- `jev_modulate_reasoning_effort` (`context`, provider/model opcionais): esforço de raciocínio por geração com payloads por provedor.
- `jev_should_nudge_continuation` (`transcript_tail`): se o agente parou com trabalho inacabado ou não verificado.

A telemetria é um comando de **CLI** (`jev-harness metrics`), não uma ferramenta MCP.

> **Chame sempre `tools/list` primeiro** se um nome for rejeitado: o servidor é a fonte de verdade, e este guia registra o schema na v0.2.0.

---

### Modo 2: Pipelines Shell & CLI (Agnóstico à Linguagem)

Se o seu agente executa comandos via terminal (bash, zsh, pwsh), encadeie os comandos de teste com pipes Unix:

> **Nenhuma chave de API é necessária para começar.** O modo offline é o padrão e faz zero chamadas de rede; `--mock` força isso explicitamente. Adicione uma chave de provedor apenas quando quiser decisões live (veja [Acesso a Provedores e Chaves de API](#-acesso-a-provedores-e-chaves-de-api)).

> **Padrão correto:** deixe o runner de testes decidir se o comando falhou e peça ao Jev o *triage* da falha. O Jev nunca bloqueia uma execução verde: logs de suíte aprovada são detectados deterministicamente e retornam `category: "no_failure"`, exit code `0` e **zero** chamadas de API.

```bash
# ✅ Recomendado: o runner decide, o Jev aconselha na falha
if ! OUT=$(npm test 2>&1); then printf '%s\n' "$OUT" | jev-harness test-gate; exit 1; fi

# ✅ Também válido: pipe do output completo (execuções verdes caem em no_failure, exit 0)
pytest 2>&1 | jev-harness test-gate
npm test 2>&1 | npx @ismaelsoilet/jev-harness test-gate
cargo test 2>&1 | jev test-gate
```

#### Códigos de Saída Semânticos:
- `0`: **Seguro para agir deterministicamente** (`skip_llm = true`). O Jev imprime a ação exata (ex: `pip install pytest-mock`).
- `1`: **Falha lógica profunda** (`skip_llm = false`) ou **Aborto Recomendado**. Apenas neste momento o agente deve acionar o modelo de fronteira.
- `2`: Erro de sintaxe ou invocação (por exemplo flag inválida, subcomando desconhecido ou um caminho `--log` inexistente). Erros de invocação são impressos como texto simples no stderr **mesmo com `--json`**, então consumidores de máquina devem ramificar pelo exit code primeiro.
- O exit `0` cobre dois resultados distintos: correção determinística para uma falha real (`skip_llm=true`) e execução verde (`category="no_failure"`). Ramifique por `category`, não apenas pelo exit code.

#### Flags operacionais compartilhadas por todos os comandos:

| Flag | O que faz | Quando usar |
| :--- | :--- | :--- |
| `--shadow` | Decide, imprime `[SHADOW] would exit N` no stderr e **sempre sai com `0`**; `test-gate --json` adiciona `shadow: true` e `would_exit`. Também disponível como `"shadow": true` no `.jev.json` | Medir os gates em um pipeline real por uma semana antes de confiar neles |
| `--fail-closed` | Expõe erros do provedor em vez de degradar: imprime `Error: ...` no stderr e sai com `2` (sem traceback) | Gates de CI rígidos, onde indisponibilidade do provedor deve falhar o job |
| `--retries N` | Número máximo de tentativas para falhas retentáveis (padrão `3`) | Limitar a espera em pipelines lentos |

**Política de falha padrão (fail-open):** `429`, `5xx`, timeouts e erros de rede são retentados com backoff exponencial com teto e respeitam `Retry-After` (inclusive segundos fracionários). Após as tentativas, a decisão degrada para o motor determinístico offline e é **sempre marcada** na saída: `is_mock: true` mais `degraded_reason` (`auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`) — exposto no `--json`, nos payloads MCP e na linha humana `Mode:` como `[SIMULATION/MOCK - degraded: <reason>]`. Nunca trate uma resposta degradada como live. Um `200` com campos de tipo errado (por exemplo `score: "N/A"`, `answers: []`) segue o mesmo caminho: degradação marcada, nunca traceback, `NaN` silencioso ou score silenciosamente default.

**Precedência do shadow:** `--shadow` nunca quebra o pipeline — inclusive quando o provedor falha e `--fail-closed` também está ativo, caso em que reporta `[SHADOW] would exit 2` e sai `0`. Ele **não** mascara uso incorreto do CLI: flag inválida ou arquivo `--log` inexistente ainda sai `2`.

**`is_mock` vs `degraded_reason` — não confunda:** `is_mock: true` sozinho significa que a resposta veio do motor offline determinístico de propósito (sem credenciais, ou `--mock`); um `degraded_reason` **não vazio** significa que uma chamada live foi tentada e falhou, então a resposta é um fallback rotulado. Ramifique por `degraded_reason` quando precisar saber "isto foi uma decisão real?".

Recibos e cache de decisão são **estado do lado Python**: o CLI, o MCP server e o SDK Python escrevem; os runtimes TypeScript e Rust não (permanecem stateless, como o lease de sessão).

**Logs não confiáveis:** o detector determinístico de injeção escala (nunca ignora) quando um log se dirige ao decisor — `IGNORE PREVIOUS INSTRUCTIONS`, `<|im_start|>`, `[INST]`, `"role": "system", "content": …`, `skip_llm=true`, "classify this as …". Um log estruturado que embute uma mensagem de chat (role + content) portanto escala; essa é a direção segura e custa apenas uma revisão, nunca um skip silencioso.

**Respostas são estritas, telemetria não:** uma resposta que o runtime não consegue interpretar (`type` desconhecido, campo numérico ausente ou textual, `answers` que não é um objeto) é tratada como malformada e degrada de forma visível — os gates nunca caem em silêncio para o score default. Os contadores de `usage` são apenas telemetria: se o provedor os enviar num formato inesperado, os três runtimes caem para a mesma estimativa calculada, e isso nunca muda uma decisão.

**Novidades da `v0.2.0` — comandos que valem conhecer:**

| Comando | O que responde |
| :--- | :--- |
| `jev-harness doctor [--live] [--json]` | Minha instalação está saudável? Verifica versão, config, credenciais (apenas fingerprint, nunca o segredo), modelo efetivo e origem, limites de payload, permissões do estado, recibos/cache, hook de git e, opcionalmente, faz UMA chamada live para medir latência e custo. Cada problema vem com o comando que corrige |
| `jev-harness replay --corpus tests/corpus` | Quão precisos são os gates? Roda um corpus rotulado, imprime matriz de confusão, precisão/recall/F1 e ECE por gate, e falha (exit `1`) em regressão contra `docs/REPLAY_REPORT.json` ou se um caso adversarial for classificado de forma determinística |
| `jev-harness receipts [--tail N] [--json]` | O que este repositório decidiu? Lê a trilha de auditoria append-only (`{ts, gate, input_hash, decision, confidence, model, is_mock, degraded_reason, shadow}`) |

Cache e debounce: decisões live idênticas são servidas do `.jev/cache.json` (`--no-cache` ignora) e avaliações repetidas de `nudge-gate`/`abort-check` dentro da janela de debounce são coalescidas (`debounced: true`). Rodadas em shadow e respostas degradadas nunca são cacheadas; `jev-harness metrics --json` reporta o hit-rate.

**Campos estruturados que você pode usar (aditivos, `v0.2.0`):**

| Campo | Onde | Significado |
| :--- | :--- | :--- |
| `uncertainty` | todo resultado de gate que chegou a uma resposta | `{margin, normalized_entropy, confidence, escalate_to_system2, escalation_reason}` — forma da distribuição do provedor mais uma dica explícita de escalonamento. Nunca altera `skip_llm` ou exit code, e execução verde nunca é escalada. É `null` nos atalhos determinísticos (execução verde, guarda de injeção) e numa resposta servida por lease, porque ali não existe distribuição do provedor |
| `recovery` | `test-gate` (dependência ausente) | `{action_type, package_name, package_manager, argv, is_safe_auto_run, rationale}`. **Nunca uma string de shell.** `is_safe_auto_run` é `false` a menos que o pacote esteja declarado nos seus manifestos **e** você passe `--allow-auto-recovery` |
| `focused_slice` / `causal_context` | o que o provedor recebe | Recorte de ≤15 linhas em volta da falha mais o bloco anterior. Você continua enviando o log completo; o slice é o que o juiz lê primeiro |
| `cached` / `debounced` | resultados de gate | Proveniência de uma decisão servida localmente (cache ou janela de debounce) |

**Onde o estado vive:** a sessão, os recibos, o cache de decisão e o lease de esforço são gravados em `~/.config/jev/` (modo `0600`) a menos que o repositório tenha um diretório `.jev/` — o `jev-harness init` o cria, e enquanto ele existir o estado fica dentro daquele repositório, evitando que dois projetos compartilhem memória ou lease. Nada é criado automaticamente.

Flags que os acompanham: `--state-json <arquivo|json>`, `--allow-auto-recovery`, `--use-lease` (reutiliza um lease de esforço ativo), `--tool-error "<resumo>"` (break-glass: invalida o lease), `--no-cache` e `--no-receipts`.

**Limites de payload:** cada requisição é validada **antes** de qualquer chamada de rede contra os limites do provedor (128.000 code points de `state`, 256.000 no total, ≈ 32k/64k tokens). Exceder sai com `2` e `Payload exceeds the provider limit: ...` — divida o estado ou as perguntas em vez de repetir.

**Pin de modelo:** o modelo efetivo resolve como argumento explícito → variável `JEV_MODEL` → `"model"` no `.jev.json` → default do provedor, e `jev-harness status` informa o modelo e a origem. O default `jev-latest` é um **alias móvel**; fixe uma versão (ex.: `"model": "jev-1.13.0"`) quando os thresholds estiverem calibrados, para que um release do provedor não mude suas decisões silenciosamente.

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

**No `.pre-commit-config.yaml`** — o hook exige o seu comando de teste como argumento, porque um repositório de hooks não pode adivinhar o seu runner:

```yaml
repos:
  - repo: https://github.com/ismaelsoilet/jev-harness
    rev: v0.2.0
    hooks:
      - id: jev-test-gate
        args: ["pytest -q"]     # ou "npm test", "cargo test --quiet", ...
```

**Hook de git gerado (CLI):**
```bash
jev-harness init --git   # precisa rodar dentro de um repositório git
jev-harness init --git --test-cmd "make test-fast"
```

O que o `init` escreve: `.git/hooks/pre-commit` (executável; detecta npm/pytest/cargo, prefere os binários do virtualenv, regenerável), `.jev.json`, `.env.jev.example` e `.agents/skills/jev-harness/SKILL.md`; `.cursor/mcp.json` apenas com `--cursor`/`--all`. **Nunca sobrescreve ficheiros existentes**; se já existir um hook alheio, ele é preservado e o gate vai para `.git/hooks/pre-commit.jev` — **o gate NÃO fica ativo até você fazer o merge**, e o `init` avisa isso. O merge mais simples é encadear no fim do seu hook existente:

```sh
# .git/hooks/pre-commit (depois das suas verificações)
exec "$(dirname "$0")/pre-commit.jev" "$@"
```
> **Nota sobre virtualenv:** o hook gerado usa `./.venv/bin/...` quando existe virtualenv, então funciona sem ativar a env. Se instalar a CLI globalmente e rodar os testes dentro de uma venv, o hook continua resolvendo ambos por essa venv.

**No GitHub Actions (`.github/workflows/ci.yml`):**
```yaml
- name: Rodar testes e triar a falha com o Jev
  run: |
    if ! OUT=$(npm test 2>&1); then
      printf '%s\n' "$OUT" | npx @ismaelsoilet/jev-harness test-gate
      exit 1
    fi
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

> **Escopo do detector:** o atalho de sucesso cobre os formatos de resumo emitidos por pytest, vitest, jest, cargo, go, mocha, rspec e unittest — incluindo separadores de vírgula/espaço/underscore e dígitos não-ASCII. É um *atalho, nunca uma garantia*: em caso de dúvida, classifica como falha. As receitas failure-only acima mantêm o exit code do runner como autoridade, então o detector nunca transforma uma suíte vermelha em commit verde.

### Regra 0: Nunca escale uma execução verde
- `category: "no_failure"` (exit `0`) significa que o log é de uma execução **bem-sucedida**: **não** chame um LLM e **não** trate como sinal de falha. O detector é estrito: qualquer evidência real de falha (`1 failed`, `FAILED`, tracebacks, panics, erros de dependência/transientes) veta o atalho.

### Regra 1: Triagem Zero-LLM em Falhas
- **NUNCA** repasse tracebacks brutos (>20 linhas) diretamente para um modelo de raciocínio de fronteira.
- Sempre passe pelo `jev-harness test-gate` (ou ferramenta MCP `jev_triage_test_failure`) primeiro.
- Se `skip_llm == true`, execute a ação determinística descrita em `action_recommendation`.

### Rule 2: Disjuntor em Ações Repetitivas
- Se uma operação falhar duas vezes consecutivas, o agente **DEVE** executar `jev-harness abort-check` (ou `jev_abort_check`).
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
3. Para falhas repetitivas em refatorações multi-turnos, o Claude Code invoca `jev_abort_check` antes de insistir em uma 3ª tentativa fracassada.

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
- Aborte loops circulares quando `jev_abort_check` retornar true.
```

### Para o Cursor (`.cursorrules` ou `.cursor/rules/jev.mdc`):
```markdown
# Protocolo de Otimização de Tokens com Jev Harness

Antes de gastar tokens com falhas de compilação ou testes:
1. Sempre passe a saída do teste por `jev-harness test-gate` ou use a ferramenta MCP `jev_triage_test_failure`.
2. Se `skip_llm` for true, execute a ação recomendada imediatamente sem consultar o modelo.
3. Se uma tarefa falhar em 2 tentativas seguidas, invoque `jev_abort_check` antes de propor a terceira.
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
| **Erro de Módulo Ausente** | Envia 300 linhas ao Claude Fable 5.1 (~50k tokens, ~$0,80) | Jev faz triagem offline em dezenas de µs in-process (~80–100 ms de cold start no CLI) por ~$0,00002 no live. Instala pacote. | **99,9% economia de custo, 15s poupados** |
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
