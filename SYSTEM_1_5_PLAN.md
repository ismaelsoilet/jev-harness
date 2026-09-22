# 🧠 PLANO ARQUITETURAL: `jev-harness` como Motor de **System 1.5**

> **Referência Conceitual:** Josh Rosen (`@JoshARosen`, TypeSafe AI) — Definição dos 5 Pilares do **System 1.5**  
> **Escopo:** Alinhamento Técnico Estrito, Verificação de Claims Reais (`v0.1.9`) e Blueprint de Evolução para o Orquestrador Unificado **System 1.5 (`v0.2.0`)**.

---

## 1. O Que é o **System 1.5** e Por Que Ele Existe?

Na arquitetura de agentes de codificação autônomos, existe um abismo entre dois extremos cognitivos:

1. **System 1 Puro (Classificadores Isolados / Heurísticas Simples):**
   - Toma micro-decisões rápidas (`< 100ms`, não-autorregressivo), como responder uma pergunta `Choice`, `Score` ou `Noul` isolada via API `systemone`.
   - **Limitação:** O modelo System 1 sozinho não tem estado de sessão, não executa ações de recuperação no terminal, não constrói dialetos de provedores e não controla o ciclo de vida do agente.
2. **System 2 Puro (LLMs Generativos de Fronteira: GPT-6 Astra, Claude Fable 5.1, DeepSeek V4-Pro, Qwen 3.8 Max):**
   - Capaz de raciocínio algorítmico profundo e síntese multi-arquivo.
   - **Limitação:** Quando deixado no controle direto do loop do agente (`while (!done)`), queima `50.000+` tokens em erros mecânicos triviais (`ModuleNotFoundError`, `ECONNRESET`), entra em *doom loops* circulares repetindo a mesma tentativa fracassada, desperdiça `reasoning_effort="high"` em comandos `git status`, ou para prematuramente sem rodar testes.

### A Definição Oficial de **System 1.5** (Josh Rosen):
> *"What you all think System 1.5 means:*
> 1. *glue between fast and deep reasoning*
> 2. *cheap typed decisions that escalate when unsure*
> 3. *deterministic routing, gates, and recovery*
> 4. *perception and attention for agents*
> 5. *state machines with judgment*
>
> *Yes, it's all of the above."*

O **System 1.5** é exatamente a **camada executiva intermediária (o Harness)**: uma máquina de estados determinística acoplada a decisões probabilísticas tipadas e calibradas (`ChoiceQuestion`, `ScoreQuestion`, `NoulQuestion`) que governa **quando**, **como**, **com qual orçamento de raciocínio** e **com qual foco de atenção** o System 2 deve operar.

---

## 2. Auditoria de Claims Atuais (`v0.1.9`): O Que o `jev-harness` Já Faz Hoje vs. O Que Falta

Para manter **100% de honestidade técnica (Zero False Claims)**, a tabela abaixo separa rigorosamente o que **já está implementado e testado hoje (`v0.1.9`)** nos 3 runtimes (Python, TypeScript e Rust) do que **será construído na evolução `v0.2.0` (`System 1.5 Engine`)**:

| Pilar do System 1.5 | O Que Já Existe e Funciona Hoje no `jev-harness` (`v0.1.9`) | O Que Ainda Falta Construir para Completar o Pilar (`v0.2.0`) |
| :--- | :--- | :--- |
| **1. Glue between fast and deep reasoning** *(Cola entre raciocínio rápido e profundo)* | - Gate `modulate_reasoning_effort` (`reasoning-effort`): usa o System 1 para escolher entre 8 níveis de esforço (`none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra`) e *stability leases* (`1, 2, 5, 10` gerações).<br>- Compilador estático `build_provider_params` gera os payloads exatos para OpenAI/Codex, Anthropic, DeepSeek, Alibaba Qwen, Google Gemini, Moonshot Kimi e Xiaomi MiMo.<br>- Safeguard automático (`is_reasoning_supported = False`) para modelos *single-pass* (`gpt-4o`, `claude-3-5-haiku`, etc.). | - **Auto-Lease Tracker Persistente**: Hoje o `modulate_reasoning_effort` calcula `lease_steps` (ex: `5` gerações), mas cabe ao chamador decrementar o contador. Falta um estado de sessão (`active_lease_remaining`) que, enquanto o lease estiver válido e sem falha de ferramenta, retorne instantaneamente o esforço em `0ms` sem sequer chamar a rede. |
| **2. Cheap typed decisions that escalate when unsure** *(Decisões tipadas baratas que escalam quando incertas)* | - Gate `triage_test_failure` (`test-gate`): avalia `category` (`Choice`), `severity` (`Score`) e `skip_llm` (`Noul`).<br>- Só recomenda pular o LLM (`skip_llm = True`) se `category in ("env_missing", "flaky_transient")` **E** `skip_prob > 0.65`. Caso contrário (`deep_logic` ou dúvida), escala para o System 2 (`skip_llm = False`). | - **Entropia de Distribuição & Flag Universal `escalate_when_unsure`**: Nas respostas `ChoiceAnswer` e `ScoreAnswer`, a API Jev retorna o mapa `probabilities` de todas as opções. Hoje olhamos `confidence` e `noul`. Podemos calcular a **margem de separação (`top1_prob - top2_prob`)** em todos os 6 gates: se `confidence < 0.65` ou `margin < 0.20`, marcar explicitamente `uncertain_escalation = True` para forçar escalonamento seguro ao System 2. |
| **3. Deterministic routing, gates, and recovery** *(Roteamento determinístico, gates e recuperação)* | - 6 Gates Semânticos (`test-gate`, `abort-check`, `route`, `verify`, `reasoning-effort`, `nudge-gate`) com *exit codes* Unix estritos (`0`, `1`, `2`).<br>- Recomendações determinísticas de recuperação (`AUTO-ACTION: Install missing dependency`, `AUTO-ACTION: Retry flaky test once`) e disjuntor de *doom loops* (`should_abort_trajectory`). | - **Catálogo Estruturado de Comandos de Auto-Recovery (`recovery_command`)**: Hoje `triage_test_failure` retorna uma string legível em `action_recommendation`. Podemos extrair e retornar um campo estruturado `suggested_shell_command` (ex: `"pip install pandas"`, `"npm install axios"`, `"cargo add serde"`) extraído diretamente do traceback para execução determinística segura. |
| **4. Perception and attention for agents** *(Percepção e atenção para agentes)* | - `safe_truncate_head_tail`: preserva os primeiros `1500` e últimos `2500` caracteres de logs gigantes sem quebrar fronteiras UTF-8.<br>- Priorização de falhas reais (`AssertionError`, `panic!`, `deadlock`) sobre *warnings* transientes.<br>- Aviso de proteção de KV Cache (`cache_safe_recommendation`) quando `session_context_tokens > 30000`. | - **Extrator de Sinal Crítico (`focused_evidence_slice`)**: Quando `skip_llm = False` (o erro precisa ir para o System 2), em vez de o agente enviar 500 linhas de log bruto ao GPT-6/Claude, o `test-gate` deve devolver um campo `focused_traceback` contendo apenas os ~15 frames/linhas onde a falha real ocorreu, reduzindo em 85% os tokens de entrada enviados ao System 2. |
| **5. State machines with judgment** *(Máquinas de estado com julgamento)* | - Gate `should_nudge_continuation` (`nudge-gate`): avalia a fase atual do fluxo de trabalho (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) combinada com 3 perguntas `Noul` calibradas (`nudge`, `waiting`, `progress`) para decidir se o agente parou prematuramente ou se deve ceder a vez ao usuário. | - **Transições de Estado Validadas (`StateMachineTransition`)**: Formalizar uma função/comando unificado `step-fsm` (`evaluate_turn_state_machine`) que recebe `(previous_phase, transcript_tail, last_command_output)` e aplica regras formais de transição de estado (ex: proibir transição `execute -> complete` sem passar por `verify` com evidência de testes passando). |

---

## 3. Especificação Técnica da Evolução `v0.2.0` (Unificando o System 1.5)

Quando formos implementar esta evolução, faremos em **4 entregas cirúrgicas** mantendo **zero dependências externas** e **paridade tri-runtime (Python, TypeScript e Rust)**:

### Entrega 1: `Uncertainty & Escalation Contract` (Pilar 2)
Em todos os 6 gates (`gates.py`, `gates.ts`, `gates.rs`):
- Adicionar cálculo de margem probabilística:
  $$\text{margin} = P(\text{choice}_1) - P(\text{choice}_2)$$
- Se `confidence < 0.65` ou `margin < 0.20`, definir `escalate_to_system2 = True`, garantindo matematicamente o princípio *"cheap typed decisions that escalate when unsure"*.

### Entrega 2: `Perception & Attention Slicer` + `Structured Recovery Command` (Pilares 3 e 4)
No `triage_test_failure` (`test-gate`):
1. **`recovery_command: Optional[str]`**:
   - Regex determinístico seguro (sem injeção de shell, validando apenas identificadores de pacotes `[a-zA-Z0-9_@/-]+`) para extrair o pacote exato:
     - `ModuleNotFoundError: No module named 'foo'` $\to$ `pip install foo`
     - `Cannot find module 'bar'` / `TS2307` $\to$ `npm install bar`
     - `can't find crate for 'baz'` / `E0463` $\to$ `cargo add baz`
2. **`focused_slice: str`**:
   - Extrai automaticamente apenas as linhas contendo o cabeçalho do teste falho, a linha exata do arquivo/linha (`File "...", line X`) e a mensagem de `AssertionError` / `panic!`, permitindo que o agente envie apenas `~200` tokens ao System 2 em vez de `10.000` tokens.

### Entrega 3: `Judgment State Machine Orchestrator` (`evaluate_agent_turn` / CLI `turn-gate`) (Pilares 1 e 5)
Um único ponto de entrada System 1.5 que consolida a decisão de fim/início de turno em **uma única requisição HTTP System One** (enviando todas as perguntas tipadas no mesmo dicionário `questions` para aproveitar a inferência paralela não-autorregressiva do Jev):
- Entrada: `transcript_tail`, `last_tool_output`, `current_phase`, `provider`, `model`.
- Perguntas combinadas em 1 só passe (`~80ms`):
  - `workflow_phase` (`ChoiceQuestion`: `research` | `ask` | `plan` | `execute` | `verify` | `complete`)
  - `nudge` (`NoulQuestion`)
  - `waiting` (`NoulQuestion`)
  - `abort` (`NoulQuestion`)
  - `effort` (`ChoiceQuestion`: `none` .. `ultra`)
  - `lease` (`ChoiceQuestion`: `1` | `2` | `5` | `10`)
- Regra Inviolável da State Machine:
  - Se o agente tentar transicionar de `execute` para `complete` sem evidência verificada no `last_tool_output`, a máquina de estados força `workflow_phase = "verify"` e `should_nudge = True`.

### Entrega 4: Paridade Tri-Runtime Absoluta (Checklist de Qualidade)
1. Garantir que o servidor MCP (`jev-mcp`) e todos os subcomandos CLI estejam 100% alinhados entre Python, TypeScript e Rust.
2. Garantir escrita atômica (`tempfile` + `os.replace`) no `session_metrics.json` para segurança em execução concorrente multi-agente.
3. Atualizar o diagrama principal do `README.md` e `README.pt-BR.md` apresentando a **Arquitetura System 1.5**.

---

## 4. Status de Higienização Pré-`v0.2.0`

- ✅ **[CONCLUÍDO & SINCRONIZADO]** **Remoção Completa de Menções a Skills Internas e Padronização Estrita em `workflow_phase` (`v0.1.11`)**:
  - Todas as referências a nomes de skills internas foram 100% removidas da documentação (`README.md`, `README.pt-BR.md`, `AGENTS.md`, `AGENTS.pt-BR.md`), das notas de release do GitHub (`v0.1.9`..`v0.1.11`), dos servidores MCP, das CLIs, dos SDKs e das suítes de testes nos 3 runtimes (Python, TypeScript e Rust).
  - O contrato público e interno do `NudgeGateResult` (`should_nudge_continuation` / `nudge-gate`) utiliza exclusivamente `workflow_phase` (Python/Rust/JSON) e `workflowPhase` (`WorkflowPhase` em TypeScript).

