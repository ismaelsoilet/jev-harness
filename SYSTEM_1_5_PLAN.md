# 🧠 SYSTEM 1.5 — Arquitetura-Alvo e Mapa de Capacidades Verificadas

> **⚠️ Este documento NÃO é o plano de release da `v0.2.0`.**
> Ele descreve a **arquitetura-alvo "System 1.5"** (norte conceitual) e o que a ferramenta **realmente é hoje**, com fatos verificados e pesquisa externa. A próxima versão do produto continua sendo a **`v0.2.0`**, conduzida separadamente pelo protocolo de release do repositório (`.agents/rules/05_release_and_quad_sync_protocol.md`). Nada aqui autoriza implementação nem fixa versão.
>
> **📎 Documento companheiro:** [`SYSTEM_1_5_OPPORTUNITIES.md`](SYSTEM_1_5_OPPORTUNITIES.md) — comparativo do ecossistema (Foreman, JevRouter, Winnow, jev-guard) e catálogo priorizado de oportunidades.

| Metadado | Valor |
| :--- | :--- |
| **Revisão do documento** | v2 — reescrito com fatos verificados e pesquisa externa |
| **Data da verificação** | **2026-09-23** (regra de re-verificação em 30 dias do `AGENTS.md`) |
| **Base auditada** | `v0.1.14` — HEAD `160e28f` (docs) / tag `v0.1.14`, árvore limpa · **H1 entregue na `v0.2.0`** (E0.1–E0.3, E1.1) |
| **Bateria de testes na base** | **211 verdes** (117 Python + 49 Rust + 45 TypeScript), exit 0 |
| **Método desta revisão** | Auditoria estática com file:line + experimentos executáveis contra a API live real + revisão adversarial independente de contexto fresco (SureForge Full) + pesquisa em fontes primárias |
| **Fontes externas** | TypeSafe AI (docs oficiais), Josh Rosen (4 artigos, 18–22/09/2026), arXiv:2505.18962 — todas datadas na §2 |

---

## 0. Resumo executivo (o que respondemos aqui)

1. **System 1.5 é um conceito real e documentado**: é o *tecido conjuntivo determinístico* entre o **System 1** (Jev/TypeSafe, decisões tipadas rápidas) e o **System 2** (LLMs de fronteira). A definição mais direta vem de Josh Rosen (22/09/2026): *"Our job is clear now: build System 1.5 — connect System 1 (Jev) to System 2 (frontier reasoning models) using really good software architecture and deterministic connective tissue."*
2. **A nossa ferramenta já é uma implementação parcial e legítima desse papel** — no nicho de **engenharia de software com agentes**: triagem de falhas de teste, veto de conclusão prematura, quebra de doom loops, verificação de critérios, modulação de esforço e roteamento. Tudo isso com decisões tipadas do Jev + política determinística em código.
3. **Ela não pode ser "tudo isso"** — e não deve tentar. O ecossistema mostra categorias adjacentes (checkpoints/artefatos, context graphs, worker routing, tool gating, context filtering) que são produtos diferentes. Tentar cobrir tudo violaria o próprio princípio anti-Frankenstein do repositório.
4. **A averiguação encontrou 1 bug de produção e 6 lacunas materiais** que condicionam qualquer evolução (detalhados na §5). O gate SureForge desta revisão é **REPAIR**: o documento foi corrigido; a implementação das evoluções exige os pré-requisitos da §6.

---

## 1. O que é o System 1.5 (definição com fontes)

### 1.1 Dois níveis distintos (não confundir)

| Nível | O que é | Fonte | Relevância para nós |
| :--- | :--- | :--- | :--- |
| **Micro-cognitivo / latente** | Modelo autorregressivo que usa *shortcuts* internos (early-exit em camadas, pulo de passos de CoT) para economizar FLOPS | arXiv:2505.18962, *System-1.5 Reasoning: Traversal in Language and Latent Spaces with Dynamic Shortcuts* (Wang et al., v3, 31/05/2025) | **Nenhuma.** É técnica de treino/inferência do modelo; não se aplica a um harness externo |
| **Macro-cognitivo / executivo** | Camada de software que orquestra *quando*, *como* e *com qual orçamento* o System 2 é acionado, usando decisões tipadas do System 1 | Josh Rosen, 18–22/09/2026; TypeSafe docs ("AI-powered software") | **É exatamente o nosso espaço.** `jev-harness` = tecido conjuntivo determinístico |

> **Correção da v1 do plano:** o arXiv:2505.18962 existia e estava corretamente caracterizado no conceito, mas o título citado ("Dynamic Shortcuts & Compute Allocation") não é o título real. Além disso, o paper é sobre inferência latente **dentro do modelo**; ele ilustra o termo, mas **não valida** a arquitetura do harness. A validação para o nível executivo vem dos artigos do ecossistema (Josh Rosen) e da documentação oficial da TypeSafe.

### 1.2 A citação que define o papel (fonte primária)

De *"Jev and AI Checkpoints"* (Josh Rosen, 22/09/2026):

> *"The more I work with Jev, the more convinced I am that the interesting architecture isn't System 1 or System 2 on its own. It's everything we build between them. (…) Our job is clear now: **build System 1.5** — connect System 1 (Jev) to System 2 (frontier reasoning models) using really good software architecture and deterministic connective tissue. The checkpoints, contracts, artifacts, context, policies, feedback loops, and other deterministic connective tissue are what let System 1 and System 2 work together. I suspect a lot of the hard engineering in the next generation of AI systems happens right there."*

E de *"Jev in the Wild"* (22/09/2026), sobre o padrão de uso real:

> *"Unlike Jev's LLM counterparts, which have been at the center of the agentic loop, the common pattern with Jev isn't giving it control. It's inserting Jev at a specific decision point in otherwise conventional software. (…) Jev can make a decision and hand control right back to the software."*
>
> *"None of these systems need Jev to enforce the policy. That's done in deterministic code. (…) Jev just provides the semantic judgment that the policy uses."*

### 1.3 O que a TypeSafe oficialmente diz (e que nos limita)

| Fato oficial | Fonte | Implicação para o plano |
| :--- | :--- | :--- |
| Jev **não** é um LLM de chat/código; é um primitivo de decisão para **usar dentro** de software/agentes | docs: *Jev with coding agents* | O harness é o "software" que usa Jev — posicionamento correto |
| A arquitetura recomendada é **"AI-powered software"**: código dono do control flow; Jev só nos pontos de julgamento | docs: *How to build with TypeSafe* | Valida "gates consultivos + política determinística"; **refuta** a ideia de "bloqueio físico" |
| `confidence` é **derivada da distribuição** de probabilidades; Noul **não tem** confidence | docs: *Confidence* | Não tratar `confidence`, `ΔP` e `H_n` como três sinais independentes; escolher um e documentar |
| Thresholds são **específicos do domínio e da versão do modelo**; "teste com seus próprios dados" | docs: *Confidence* / *Models* | "Hiperparâmetros calibrados" sem dataset é uma afirmação indevida |
| Distribuições completas existem para **Choice e Score**; misturar tipos numa chamada é suportado e **não** altera respostas | docs: *Primitives*, cookbook *Parallel questions* | Habilita a UncertaintyEngine (D1) e o batch (D3) — mas ver limites abaixo |
| Batch de 13 perguntas: **12,2× mais barato e 10× mais rápido** que 13 chamadas | cookbook *Parallel questions* | Justifica o batch por **custo**, não pelos "~80ms" |
| Latência típica oficial: **~100 ms** ("as low as 70ms"); no nosso E2E live medimos **~0,8 s** por chamada (free tier) | docs + medição própria | Números de latência devem ser medidos e rotulados por caminho |
| Limites: **64k tokens** (32k para `state` + maior pergunta); texto apenas; inglês melhor; preço **$0,042/Mtok** de input, output grátis; 1.200 req/min (dinâmico) | docs: *Models* | Restrições reais de payload e de custo a respeitar |
| **Jaggedness documentada** do `jev-1.13`: leitura literal, não conta/não faz matemática, datas como texto, indireção, **context rot com state grande**, **conteúdo adversarial pode desviar a resposta**, invariantes estruturais não garantidas, Score com calibração numérica fraca | docs: *Jev 1.13 jaggedness* (revisado em 17/09/2026) | **Crítico para D2/D3**: logs grande e hostis afetam a decisão; nunca auto-executar com base em decisão de log não confiável |
| Dados de cliente **não** são usados para treino; ZDR para enterprise | docs: *Models* | Manter a matriz de privacidade do guia; live envia o estado ao provedor |

### 1.4 Os "5 Pilares" — o que pudemos e o que não pudemos verificar

A v1 do plano atribui a Josh Rosen uma citação literal com cinco pilares. **Não localizamos essa citação literal em fonte primária.** O que está verificado:

- O conceito "System 1.5" como camada intermediária está **confirmado** nos artigos de 22/09/2026 (citação acima).
- Os **elementos** dos 5 pilares aparecem de forma distribuída e confirmada nas fontes: glue fast/slow (artigo de 18/09), decisões tipadas que escalam (docs de Confidence/Patterns), roteamento/gates/recuperação determinística (artigo do control plane), percepção/atenção (context filtering no artigo "in the Wild"; jaggedness sobre context rot), e máquinas de estado com julgamento (worker supervision/Foreman).
- **Não verificado:** a afiliação de Josh Rosen à TypeSafe AI (as fontes o mostram como comentarista externo que escreve sobre o Jev); a lista literal dos 5 pilares.

> **Regra de honestidade:** o documento mantém os 5 pilares como *framework de organização*, não como citação verificada. A referência corrigida é: "Josh Rosen — ensaios sobre System One/System 1.5 (2026), não afiliado à TypeSafe segundo as fontes consultadas".

---

## 2. Base de pesquisa (datada — re-verificar após 30 dias)

| # | Fonte | Data | O que usamos dela |
| :--- | :--- | :--- | :--- |
| S1 | [TypeSafe docs — Introduction](https://docs.typesafe.ai/introduction) | consultado 2026-09-23 | Definição de System One; primitivos; "your code can branch, sort, and route" |
| S2 | [TypeSafe docs — System One](https://docs.typesafe.ai/concepts/system-one) | 2026-09-23 | Diferença para LLM; calibração; "decidir quando agir e quando escalar" |
| S3 | [TypeSafe docs — Confidence](https://docs.typesafe.ai/confidence) | 2026-09-23 | `confidence` derivada; Noul sem confidence; thresholds por domínio/dados |
| S4 | [TypeSafe docs — How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) | 2026-09-23 | "AI-powered software"; decomposição atômica; combinar em código; escalar incertos |
| S5 | [TypeSafe docs — Patterns](https://docs.typesafe.ai/patterns) | 2026-09-23 | Fan-out especulativo, confidence-gated routing, composite scoring, intent routing |
| S6 | [TypeSafe docs — Parallel questions (cookbook)](https://docs.typesafe.ai/cookbooks/parallel_questions) | 2026-09-23 | 13 perguntas em 1 chamada: **12,2× mais barato, 10× mais rápido**, respostas idênticas |
| S7 | [TypeSafe docs — Models](https://docs.typesafe.ai/models) | 2026-09-23 | `jev-1.13.0`; 64k/32k; $0,042/Mtok; 1.200 req/min; texto; ZDR enterprise |
| S8 | [TypeSafe docs — Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | revisado 2026-09-17 | Limites reais: context rot, adversarial, matemática, invariantes |
| S9 | [TypeSafe docs — Jev with coding agents](https://docs.typesafe.ai/introduction/coding-agents) | 2026-09-23 | Jev **não** substitui o cérebro do agente; é primitivo dentro do software |
| S10 | Josh Rosen — *System One Models: What Comes After Agentic Software* (LinkedIn, 18/09/2026) | 2026-09-23 | "Micro-inference layer": batch, cache, thresholds de confiança, escalonamento, roteamento; "reasoning model como caminho de escalação"; Doom a ~10 chamadas/s |
| S11 | Josh Rosen — *Jev and AI Checkpoints* (22/09/2026) | 2026-09-23 | **Definição de System 1.5**; checkpoints, contratos, artefatos, proveniência |
| S12 | Josh Rosen — *Jev in the Intelligent Control Plane* (22/09/2026) | 2026-09-23 | Worker routing, supervisão contínua, policy enforcement (enforcement é do código), escalação humana, "decision layer" como diferencial |
| S13 | Josh Rosen — *Jev in the Wild* (22/09/2026) | 2026-09-23 | Padrões do ecossistema: routing, context filtering, **tool gating (allow/ask/deny)**, worker supervision (Foreman), fast control loops, fuzzy data queries; "Jev não controla; o código decide" |
| S14 | arXiv:2505.18962 (v3) | publicado 31/05/2025 | Nível latente; **não** valida o nível executivo |
| S15 | Ecossistema citado em S13: Foreman, JevRouter, agent-router, Jev Guard, pi-warden, Jev Shield, Winnow, jev-sift, fast-jev-compaction, Browser Use Jev Ultrafast, pg-jev | 2026-09-23 | Prior art e limites de escopo: não somos únicos e não precisamos ser tudo |

---

## 3. Fatos concretos da ferramenta (auditoria v0.1.14; H1 entregue na v0.2.0) — o que já é verdade

### 3.1 Inventário verificado

| Item | Fato | Evidência |
| :--- | :--- | :--- |
| Versão/base | `v0.1.14` publicado nos 4 canais (PyPI, npm, crates.io, GitHub Latest) | APIs dos registries + `gh release list` |
| Testes | **211 verdes** (117 Python + 49 Rust + 45 TS) | `./scripts/release.sh --check` (2026-09-23) |
| Gates semânticos | **6**: triage, abort, route, verify, effort, nudge | `src/jev_harness/gates.py` (`def` x6) |
| Contrato de saída | exit `0` (ação determinística ou nada a fazer), `1` (defeito real / abortar), `2` (erro de invocação) | `cli.py`; guia §códigos semânticos |
| Effort | 8 níveis `none..ultra` (default 3: low/medium/high) | `gates.py:572-581`, `:602` |
| Dialetos de provedor | 7 grupos (openai/codex/azure, deepseek, qwen, anthropic, gemini, kimi, mimo) | `gates.py:435-569` |
| Lease | `lease_steps ∈ {1,2,5,10}` **passivo** (nenhum estado em sessão) | `gates.py:607`; `grep lease session.py` = 0 |
| Truncamento | 6000 chars (2000 início + 4000 fim), UTF-8 seguro nos 3 runtimes | `gates.py:158-159`; testes de paridade |
| KV-cache alert | dispara com `session_context_tokens > 30000` | `gates.py:667-671` |
| Offline | mock determinístico, **zero rede**, sem chave | `--mock`; `is_mock: true` |
| Dependências | Python stdlib; TS sem runtime deps | `pip show`, `package.json` |
| Sessão | lock `fcntl` + `msvcrt`, permissões 0700/0600, concorrência testada 20 processos | `session.py:86-133` |
| Privacidade | live envia o `state` (log truncado) ao provedor; `--mock` não sai da máquina | guia de integração + código |

### 3.2 O que a API live realmente devolve (medido em 2026-09-23)

| Tipo | Retorno real | Consequência para o plano |
| :--- | :--- | :--- |
| Choice | `choice` + `probabilities` (distribuição completa) + `confidence` | D1 é **viável no live** (Python/TS; Rust ver §5-B1) |
| Score | `score` (float) + `probabilities` (chaves `"0".."K−1"`) + `legend` (mapa) + `confidence` | D1 viável; **normalização de chaves é obrigatória** |
| Noul | apenas `noul` (0–1), sem distribuição e sem confidence | ΔP/H_n não se aplicam a Noul; usar o próprio `noul` |
| Exemplo real | `category: {deep_logic: 0.63, flaky_transient: 0.37, ...}`, `confidence: 0.51` | Existem distribuições suaves de verdade; escalonamento tem sinal |

### 3.3 Latência e custo medidos (não os do marketing)

| Caminho | Medição 2026-09-23 | Observação |
| :--- | :--- | :--- |
| CLI mock (cold start) | **0,08–0,10 s** (5 amostras) | é o "~80ms" real do harness |
| Mock in-process | **0,11–0,22 ms** | decisão local |
| Live, 1 pergunta | **721–1.137 ms** (média ~0,8 s) | free tier; oficial do provedor: ~100 ms típico |
| Live, batch de 4 perguntas | **~848 ms** | 4/4 respostas; 1 chamada |
| Custo live | input **$0,042/Mtok**; output grátis | exemplo real: 429–534 tokens de input por chamada |

> **Correção da v1:** "~80ms para o orquestrador em lote" é o **cold start do harness em modo mock**, não o E2E live. "Preservar GPU KV-cache" com payload <3000 chars não tem suporte: o Jev é um sampler não-autorregressivo paralelo e o `usage` não expõe cache; além disso, o provedor documenta **context rot** com state grande — ou seja, compactar *ajuda a acurácia*, não uma "KV-cache".

### 3.4 O que a ferramenta NÃO faz hoje (e o plano anterior assumia)

| Suposição da v1 | Realidade verificada |
| :--- | :--- |
| "Estado base v0.1.11" | Base real é **v0.1.14**; faltam no doc: `no_failure`/short-circuit verde (0.1.12), `--log` file-only (0.1.14), hook venv-aware, matriz de privacidade revisada |
| "S-DFA bloqueia fisicamente execute→complete" | O harness é **consultivo**. Só o hook de pre-commit bloqueia commit; nunca "conclusão" |
| "Risco atual de CWE-78" | Hoje **não existe** extração de pacote nem geração de comando; o risco seria **introduzido** pela Entrega 2 |
| "Lease invalida no erro" | Não existe superfície de "erro de ferramenta"; ninguém reporta ao harness — requer contrato novo |
| "Thresholds calibrados" | Sem dataset nem procedimento; o provedor recomenda calibrar por domínio e fixar a versão do modelo |
| "Um único payload <3000 chars para tudo" | Contraria a jaggedness documentada (context rot) e a recomendação oficial de **dar a cada pergunta só o contexto necessário** |

---

## 4. Averiguação: a ferramenta "pode ser tudo isso"?

### 4.1 Mapa por padrão de ecossistema (o que o mercado está construindo)

| Categoria (fontes S10–S13) | Exemplos no ecossistema | O `jev-harness` é? | Veredito |
| :--- | :--- | :--- | :--- |
| **Model/worker routing** | JevRouter, agent-router, jev-codex-router | Já faz **roteamento de modelo** (`route`, `effort`); **não** faz worker routing | **Pode ser** (extensão natural do `route`) |
| **Tool gating / guardrails** | Jev Guard (allow/ask/deny), pi-warden, Jev Shield | **Não** intercepta tool calls; os gates julgam *trabalho*, não *ações de ferramenta* | **Pode ser** (o MCP/hook pode virar gate de ação), mas é outro produto |
| **Context filtering / atenção** | Winnow, jev-sift, fast-jev-compaction | **Parcialmente**: trunca e prioriza logs; não seleciona contexto de agente | **Pode ser** (nossa "Percepção" = recorte do log, não do contexto do agente) |
| **Worker supervision** | **Foreman** (Jev + Codex), control plane | **Sim, é o nosso núcleo**: triage, abort, nudge, verify = julgar o trabalho sem fazer o trabalho | **Já somos** — é a nossa diferenciação |
| **Checkpoints / artefatos / proveniência** | ThruWire (checkpoints, artefatos, receipts) | **Não** temos artefatos duráveis nem proveniência de decisão | **Não devemos ser**; podemos **integrar** (emitir recibos das nossas decisões) |
| **Context graphs** | Port (Context Lake) | **Não** temos grafo de contexto | **Não devemos ser** |
| **Fast control loops / games / browser** | Browser Use Jev Ultrafast, computer-use | **Não**; nosso loop é o ciclo de trabalho de um agente de código | **Não devemos ser** |
| **Fuzzy data queries** | pg-jev, duckdb-jev, neo4jev | **Não**; não somos camada de dados | **Não devemos ser** |

### 4.2 Mapa pelos 5 pilares (framework de organização)

| Pilar | O que já temos (fato) | O que falta para o "System 1.5 completo" | Podemos? |
| :--- | :--- | :--- | :--- |
| 1. Glue fast↔deep | `effort` (8 níveis + lease passivo) + 7 dialetos de payload + `route` (tiers) | Lease ativo com break-glass; cache de decisão; política de escalação | **Sim**, com contrato novo do chamador (D4) |
| 2. Decisões tipadas que escalam | 6 gates + exit codes + `skip_llm`/categorias; distribuições **existem** no live | Usar distribuição (ΔP/H_n) com guardas; Noul sem distribuição; thresholds calibráveis | **Sim**, mas D1 depende do parser Rust (§5-B1) e de regras por tipo (§6) |
| 3. Roteamento, gates e recuperação determinística | `route`, gates, `action_recommendation` textual | Recuperação **estruturada e segura** sem auto-exec; detecção de gerente de pacotes | **Sim**, com o redesenho obrigatório (§6-D2) |
| 4. Percepção e atenção | Truncamento UTF-8 6000; priorização de asserções; alerta KV-cache | Recorte `focused/causal` + persistência com retenção/redação | **Sim** (baixo risco), desde que `log_id` tenha retenção e `.jev/` seja ignorado |
| 5. Máquinas de estado com julgamento | Fases (`research..complete`) + nudge/waiting/progress | S-DFA **consultiva** com evidências; enforcement fica no hook/CI | **Sim como veto consultivo**; "bloqueio físico" é falso |

### 4.3 Veredito da averiguação

> **Sim, podemos ser o System 1.5 — para o ciclo de trabalho de agentes de código — e já somos uma parte funcional dele.**
> Não podemos ser (nem devemos tentar ser) o control plane completo de software factories, o sistema de checkpoints/artefatos, o context graph ou o gate de ferramentas. O valor e a diferenciação estão em ser o **tecido conjuntivo determinístico do ciclo de qualidade de código**: triagem de falhas → veto de conclusão prematura → verificação de critérios → quebra de loop → alocação de esforço, com decisões tipadas do Jev, offline-first, tri-runtime e integração por CLI/MCP/hook.
>
> **A frase que podemos defender (com fatos):** *"O `jev-harness` é uma camada de decisão System 1.5 para agentes de código: usa o Jev (System 1) para julgamentos semânticos e software determinístico para as consequências, entre o agente e o System 2."*
>
> **A frase que NÃO podemos defender:** *"É o control plane completo de uma software factory / o harness que governa qualquer agente / bloqueia fisicamente agentes."*

---

## 5. Achados materiais (gate SureForge: **REPAIR**)

Os itens abaixo foram confirmados por auditoria do dono + revisão adversarial independente (contexto fresco, 5 métodos). São pré-requisitos para qualquer evolução.

| ID | Achado | Severidade | Evidência |
| :--- | :--- | :--- | :--- |
| **B1** | **Rust descarta respostas Score no modo live** (`score: i32` vs float; `legend: Vec` vs mapa) → `severity`/`viability`/`rigor`/`complexity` caem no default. No live: Python `severity=0.96`, TS `1.01`, **Rust `3.0`**; `verify` fica **sempre reprovado** (rigor default 2.0 < 2.5) | **Bloqueante** (bug de produção atual) | `packages/rust/src/types.rs:49-54`; teste funcional nos 3 runtimes contra a API real; `gates.rs:143,246,341,417` |
| **B2** | **D2 não mitiga o vetor que afirma mitigar**: as duas regex do doc são inconsistentes (uma rejeita `@scope/pkg`; a outra aceita `-rrequirements.txt`, `-e.`, `../../../etc/passwd`); regex não resolve typosquatting/supply-chain, e `is_safe_auto_run` empurra a decisão de segurança para o consumidor | **Bloqueante para D2** | Teste das duas regex (2026-09-23); docs de recoverability não existem |
| **B3** | **Matemática de incerteza sem guardas**: distribuições live contêm zeros (todas as amostras) → `0·ln 0`; `K=1` → divisão por `ln 1`; chaves `"0"..K−1"` (live Score) vs `"1"..K"` (mock Python); mock TS/Rust sem probabilidades de Score; mock nunca escala (conf ≥0.85) | **Alta** | Provas de execução; `client.py:717,769,790,831,859`; `packages/ts/src/client.ts:637-642` |
| **B4** | **D4 inobservável como especificado**: não existe superfície de "erro de ferramenta"; `session.json` não tem `schema_version` e `save_session` **descarta** campos desconhecidos (lease perdido por writer antigo) | **Alta** | Simulação direta; `session.py:136-183` |
| **B5** | **Privacidade/segurança de dados**: `.jev/` não está no `.gitignore`; `log_id` persistiria log bruto sem retenção/redação; payload unificado amplia o dado enviado; a jaggedness documenta que **conteúdo adversarial no state pode desviar a decisão** (injeção via log) | **Alta** | `git check-ignore`; docs TypeSafe S8; matriz de privacidade do guia |
| **B6** | **Números e base do plano v1**: base "v0.1.11", "~80ms", "preserva KV-cache", "fisicamente bloqueia", "thresholds calibrados", citação literal dos 5 pilares | **Média/Alta** | Corrigidos neste documento (§3.3, §4.2, §1.4) |
| **B7** | **Divergência de mock entre runtimes** (Choice 0.85 Python vs 0.88 TS; Rust `probabilities: None`) — viola a paridade tri-runtime exigida pelo próprio plano | **Média** | Execução lado a lado (2026-09-23) |

---

## 6. Especificação corrigida (evolução pós-pré-requisitos)

> Sem compromisso de versão. Cada item só entra em uma release quando passar a bateria vigente (hoje 626 testes) + os novos testes exigidos e a paridade tri-runtime — pelo protocolo normal do repositório.

### Pré-requisito P0 — Corrigir o parser Score do Rust (hotfix)

- `ScoreAnswer`: `score: f64`, `legend` tolerante (mapa **ou** lista), `probabilities: Option<HashMap<String, f64>>`.
- Teste de contrato com payload live gravado; comparar `severity/viability/rigor/complexity` entre os 3 runtimes.
- Nota semver explícita (mudança de tipo público no crate em versão 0.x).
- **Sem isso, D1 nasce quebrado no Rust e o `verify` live do Rust é inútil.**

### Evolução 1 — Incerteza com guardas (`UncertaintyEngine`)

- Usar as **distribuições reais** (Choice/Score) quando existirem; Noul recebe tratamento próprio (sem ΔP/H_n).
- Guardas obrigatórias: `p ≤ 0` ignorado na entropia; `K ≥ 2` exigido; normalização de chaves (`"0"..K−1"`/`"1"..K"`); tolerância numérica na paridade.
- **Não duplicar sinais**: `confidence` é derivada da distribuição; escolher a medida primária (sugestão: `confidence` do provedor + uma medida de forma) e documentar a precedência.
- Thresholds: **configuráveis e rotulados como defaults**, com procedimento de calibração por dados do usuário; nunca "calibrados" sem dataset.
- Precedência explícita com as regras atuais (`no_failure`, `env_missing`, `flaky_transient`).
- **Mock**: gerar incerteza por **conflito de sinais** (ex.: `AssertionError` + `ConnectionResetError` → margem menor), para o CI exercitar o escalonamento.
- Alinhar as probs da mock entre runtimes (ou documentar a divergência e testá-la).

### Evolução 2 — Recuperação estruturada **sem auto-execução**

- **Remover** `shell_command: str` do design. Saída: `{action_type, package_name, package_manager, argv: [...], is_safe_auto_run, rationale}`.
- `is_safe_auto_run` **default `false`**; auto-run exige opt-in explícito (`--allow-auto-recovery`) e allowlist de pacotes já presentes nos manifestos/lockfiles do repositório.
- Validadores **por ecossistema** (npm: `@scope/nome`; PyPI: PEP 503; crates: `nome`), sem `/`, sem `..`, sem flags iniciando por `-`.
- Reconhecer o gerenciador pelo lockfile (**incluindo o binário do virtualenv**, ex.: `./.venv/bin/python -m pip`), nunca por string de shell.
- **Documentar o risco de injeção semântica**: um log adversarial pode tentar desviar a categoria/decisão (jaggedness S8). Decisões vindas de log não confiável **não** podem gerar execução automática.

### Evolução 3 — `evaluate_agent_turn` (batch), com expectativa correta

- Batch já é suportado pelo provedor **e já é usado** pelo client (`system_one` com múltiplas perguntas).
- Ganho real é **custo**, não latência: 12,2× mais barato no exemplo oficial; medimos ~0,8 s live para 4 perguntas vs ~0,8 s para 1. Não prometer "~80ms" no live.
- **Cuidado com context rot**: cada gate deve receber **só o contexto que precisa**; um payload único e grande tende a reduzir acurácia (jaggedness S8). Preferir chamadas por gate (ou estado segmentado) e medir a acurácia antes/depois.
- Remover a justificativa "preserva KV-cache".
- Respeitar limites: 64k tokens totais, 32k para `state` + maior pergunta; fixar a versão do modelo (`jev-1.13.0`) quando thresholds forem calibrados.

### Evolução 4 — Lease persistente com contrato explícito

- `schema_version` no arquivo de sessão + **merge tolerante** (não descartar campos desconhecidos) ou arquivo separado de lease.
- Contrato do chamador definido: quem reporta erro de ferramenta (ex.: `turn-gate --tool-error <resumo>` ou campo `tool_error`), TTL do lease, e break-glass disparado por esse reporte.
- "Sub-milissegundo" em vez de "0ms"; medir e documentar.

### Evolução 5 — Percepção e proveniência

- `focused_slice` (asserção/teste) + `causal_context` (setup/stdout) + `log_ref`.
- Redação de segredos também no `state` enviado; `.jev/` no `.gitignore`; retenção/TTL e permissões 0600 para logs persistidos.
- **Proveniência das micro-decisões** (sugestão do ecossistema, S13): registrar `{gate, input_hash, decisão, is_mock, modelo, timestamp}` — auditável, sem conteúdo sensível por padrão.

---

## 7. Riscos e regressões a gerenciar

| Risco | Impacto | Mitigação |
| :--- | :--- | :--- |
| Mudança de tipo público no Rust (`ScoreAnswer`) | Quebra de consumidores do crate | Nota semver; teste de contrato; 0.2.0 ou hotfix documentado |
| `escalate_to_system2` interagindo com `skip_llm` | Ambiguidade de contrato; regressão do valor central | Campos aditivos; precedência explícita; exit codes inalterados |
| Payload unificado | Context rot + mais dado sensível ao provedor | Estado segmentado; atualizar matriz de privacidade |
| `.jev/` sem ignore + `log_id` | Vazamento de logs/segredos em commits | `.gitignore`, permissões, retenção, redação |
| Sessão sem `schema_version` | Perda de lease por writer antigo | `schema_version` + merge tolerante |
| Conteúdo adversarial em logs | Decisão desviada (jaggedness S8) | Detector determinístico antes da API; nunca auto-executar; confiança rotulada |
| Mock divergente entre runtimes | Falso verde de paridade em CI | Alinhar probs; teste de paridade dedicado |
| Novo tool MCP | Clientes que contam 6 tools | **Adicionar** sem renomear; atualizar guia/doc/testes |

---

## 8. Roadmap em fases (ordem por dependência, sem vínculo com a 0.2.0)

```
[P0] Hotfix parser Score Rust + teste de contrato tri-runtime
      │  (pré-requisito de tudo; corrige bug live atual)
      ▼
[F1] Percepção (slices) + privacidade (.jev ignorado, retenção, redação) + proveniência
      │
      ▼
[F2] UncertaintyEngine com guardas + calibração configurável + mock por conflito
      │
      ▼
[F3] evaluate_agent_turn (batch por custo, estado segmentado) + S-DFA consultiva
      │
      ▼
[F4] Lease persistente com contrato do chamador + break-glass
```

Cada fase é individualmente lançável e reversível; nenhuma deve começar sem a anterior concluída e verificada. A `v0.2.0` (próxima versão) é decidida à parte: pode conter apenas P0+F1, por exemplo — isso é decisão de release, não deste documento.

---

## 9. Governança (herdada do repositório)

1. **Zero dependências de runtime**: Python stdlib (`urllib`), TS sem deps, Rust em Tokio estável.
2. **Paridade tri-runtime estrita** para matemática e contratos (com tolerância numérica documentada).
3. **Bateria expandida**: guardas matemáticas (zeros, K=1, uniforme/bimodal), injeção em recuperação, concorrência/TTL do lease, contrato de payload live gravado, precedência `skip_llm`×`escalate`.
4. **Quad-sync** antes de qualquer push (`./scripts/release.sh --verify-sync`).
5. **Regra de frescor**: esta pesquisa vale até **2026-10-23**; após isso, re-verificar endpoints, modelos, preços e limitações, registrando a nova data.

---

## 10. O que não foi possível verificar

- Texto literal dos "5 Pilares" de Josh Rosen em fonte primária (o conceito System 1.5 está confirmado; a citação não).
- Afiliação de Josh Rosen à TypeSafe AI (as fontes o mostram como comentarista externo).
- Comportamento real do `msvcrt.locking` no Windows (validado por código + CI, não localmente).
- Latência em outras geografias/planos pagos (medimos no free tier, deste host).
- Números internos de calibração do provedor (`confidence` é derivada; a fórmula exata não é pública — o doc mostra a aproximação `(K·peak − 1)/(K − 1)`).

---

## Apêndice A — Histórico da revisão

| v1 (anterior) | v2 (esta) |
| :--- | :--- |
| Base auditada `v0.1.11` | Base auditada `v0.1.14`, 211 testes |
| "Aprovado para implementação na v0.2.0" | Documento de arquitetura/posicionamento; **não** é o plano da 0.2.0 |
| Citação literal dos 5 pilares | Conceito verificado; citação literal marcada como não verificada |
| "~80ms" como latência do orquestrador | Medido: 0,08–0,10 s mock cold start; ~0,8 s live |
| "Preserva GPU KV-cache" | Removido; o provedor documenta **context rot** |
| S-DFA "bloqueia fisicamente" | Veto **consultivo**; enforcement no hook/CI |
| Risco CWE-78 "atual" | Risco seria introduzido pela Entrega 2; redesenho sem auto-execução |
| Thresholds "calibrados" | Defaults configuráveis; calibração por dados e por versão do modelo |
| Sem fontes | 15 fontes datadas (§2), com data de validade de 30 dias |
