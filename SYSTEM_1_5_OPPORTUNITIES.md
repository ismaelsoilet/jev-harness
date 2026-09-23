# 🔭 SYSTEM 1.5 — Oportunidades, Comparativo de Ecossistema e Veredito "Podemos ser 1.5?"

> **Documento companheiro de [`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md).**
> Responde a três perguntas: (1) que oportunidades temos para melhorar o `jev-harness` conforme a pesquisa? (2) trata-se de outra ferramenta? (3) podemos ser System 1.5 — sim ou não?
> **Data da pesquisa: 2026-09-23** (válida por 30 dias — re-verificar após 2026-10-23).
> **Base do produto: v0.1.14** (211 testes verdes, 4 canais publicados). **H1 entregue na v0.2.0** (H1 completo + E1.2–E1.4, E2.1, E2.4, E3.2/E3.3, E3.8, E3.9, E0.4, E3.1, E3.4–E3.7, E2.2, E2.3; 569 testes).

---

## 1. Sumário executivo

1. **Não é "outra ferramenta" — é um papel diferente na mesma categoria.** Em menos de 7 dias, o ecossistema Jev/System One se fragmentou em **5 papéis especializados**: supervisão de runtime ([Foreman](https://github.com/thruwire/foreman), 517★), roteamento de capacidades ([JevRouter](https://github.com/BillionsBobby/JevRouter), 173★), peneira de contexto ([Winnow](https://github.com/GhalebDweikat/winnow), 68★), segurança de tool calls ([jev-guard](https://github.com/leepokai/jev-guard), 26★) e **qualidade/testes (o nosso, 4★)**. Fundir tudo num só produto seria um Frankenstein técnico (stacks e loops incompatíveis) e competiria com MIT já maduro.
2. **Sim, podemos ser System 1.5** — como **a camada de decisão System 1.5 do ciclo de qualidade de código** (triagem de falha → veto de conclusão prematura → verificação → quebra de loop → esforço). Já somos uma implementação legítima e parcial. **Não** podemos ser "a System 1.5 inteira": isso é uma **categoria**, não uma ferramenta.
3. **Encontramos 4 oportunidades Tier-0 de confiabilidade** que nenhum concorrente ignora: tratamento de `429`/`Retry-After`, política de falha explícita (fail-open/fail-closed), pin de versão do modelo e estado estruturado. Hoje, um erro de rede no gate vira **exceção não tratada** (evidência na §4-O0.2).
4. **O maior gap de maturidade é confiança/calibração** — o Winnow já tem *shadow mode*, *replay* offline, curvas de calibração (ECE/ROC) e medição de *regret*; nós temos thresholds default sem dados. É a oportunidade de maior alavancagem depois do Tier-0.
5. **Dois diferenciais nossos são únicos no ecossistema**: (a) **offline determinístico de verdade** (todos os outros exigem chave para uso real) e (b) **tri-runtime Python/TS/Rust com paridade** (Foreman é Python; jev-guard/Winnow/JevRouter são Python ou TS). Somados ao foco em **teste/commit/CI**, definem o nosso espaço defensável.

---

## 2. O ecossistema em 2026-09-23 (fatos verificados)

| | **Foreman** | **JevRouter** | **Winnow** | **jev-guard** | **jev-harness** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Papel** | Supervisor de workers de código | Roteador de capacidades | Peneira de contexto | Guardrail de tool calls | Gates de qualidade/testes |
| **Stack** | Python 3.11 asyncio | Node 20 / TS | Python sidecar + TS hook | Node zero-dep | Python + TS + Rust |
| **Licença** | MIT | MIT | MIT | MIT | MIT |
| **★ / criado** | 517 / 17-09 | 173 / 18-09 | 68 / 16-09 | 26 / 17-09 | 4 / 21-09 |
| **Como decide** | 10 Noul em 1 chamada + árbitro determinístico | 1 Choice (+ `plan` serial/batch/decompose) | 1 Noul por bloco de output | risk(Score)+approval+user_requested+from_untrusted (Noul) | 6 gates: Choice/Score/Noul |
| **Ações** | continue / steer / stop / retry / verify / finish / escalate | decision-only (nada executa; médio/alto exige confirmação) | esconde blocos com recall key | deny / ask / allow | exit 0/1/2 + ação recomendada |
| **Persistência** | `.foreman/runs/` (state+events) | `.jevrouter/decisions` + receipts com hash | cache + `decisions.jsonl` | `~/.jev-guard/sessions` + cache | `.jev/session.json` + telemetria |
| **Calibração** | thresholds em TOML (defaults) | política + no_decision por confiança | **shadow mode, replay, ECE/ROC, labels, regret** | thresholds por env + cache por hash | **thresholds default, sem replay** |
| **Falha do provider** | retenta 429/5xx; tolera 3 falhas | cache opt-in; fallback registrado | pass-through | **fail-open por default**; fail-closed opcional | **exceção não tratada** (hoje) |
| **Offline real** | só demo determinística | demo provider | não | não | **sim, motor determinístico** |
| **Multi-host** | Codex + OpenCode | Codex/Claude/Cursor/MCP/HTTP | Claude Code (function hooks) | 8 hosts + ACP | CLI/MCP/hook + init |
| **Distribuição** | repo | npm/github | repo/marketplace | npm/marketplace | **PyPI + npm + crates + GitHub** |

**Benchmark do JevRouter (único número comparativo público do ecossistema, 2026-09-21):** em 10 tarefas Toolathlon, Jev acertou 38% dos primeiros 5 tool calls ordenados (DeepSeek V4.1 Flash: 24%), com 1,58s vs 8,65s por tarefa e $0,0058 vs ~$0,0407 por 10 tarefas. É medição de roteamento, não de tarefa completa — mas é evidência de que a camada Jev ganha de um LLM em custo/latência para decisões estreitas.

**Latências medidas pelo ecossistema (corroboram as nossas):** jev-guard mediu **~0,58s** (via gateway) e **~0,75s** (direto) por chamada; nós medimos **~0,8s** live e **0,08–0,10s** no offline. O "~100ms" oficial é o piso do provedor, não o E2E do harness.

---

## 3. Onde jogamos: sobreposição e defesa

| Sobreposição real | Risco | Nossa defesa |
| :--- | :--- | :--- |
| Foreman julga conclusão/verificação/stuck | Foreman é o "dono" da supervisão de runtime | Nós não rodamos o worker; somos chamáveis por qualquer agente/hook/CI e funcionamos **offline** |
| Winnow tem `done-ness gate on Stop` no roadmap | Pode encostar no nosso `nudge`/`verify` | Nosso foco é **falha de teste + commit + CI**, não janela de contexto do Claude Code |
| JevRouter roteia modelo/capacidade | Encosta no nosso `route`/`effort` | Nosso roteamento é acoplado ao **ciclo de qualidade** (tier por erro/falha), não a catálogo de capacidades |
| jev-guard decide tool calls | Não competimos | **Interop**: recomendar jev-guard para ações, nós para qualidade |
| Todos exigem chave para uso real | — | **Offline-first** é nosso diferencial estrutural (CI, air-gapped, repos sensíveis) |
| Todos são single-runtime | — | **Tri-runtime com paridade** é único |

> **Conclusão:** o certo é **focar no nicho de qualidade** e **interoperar**, não expandir para o escopo dos outros. A categoria tem espaço para o "gate de qualidade" de referência — e ninguém o ocupou ainda.

---

## 3.1 Interop: quando usar cada peça (verificado em 2026-09-23)

Cinco papéis, cinco ferramentas MIT — nenhuma delas cobre o espaço da outra, e o certo é
compor em vez de competir. A regra de frescor de 30 dias do `AGENTS.md` vale para esta tabela:
re-verifique endpoints, estrelas e escopo após **2026-10-23**.

| Papel no ciclo | Ferramenta | Quando é ela que você quer | Fonte (datada) |
| :--- | :--- | :--- | :--- |
| **Qualidade, teste, commit** (nós) | **jev-harness** | Triagem de falha, veto de conclusão prematura, quebra de doom loop, esforço e roteamento dentro do **ciclo de trabalho de código**; offline determinístico; tri-runtime | este repositório (`v0.2.0`, 2026-09-23) |
| **Ações de ferramenta** | [jev-guard](https://github.com/leepokai/jev-guard) (26★, criado 2026-09-17) | Antes de executar um tool call perigoso: `deny`/`ask`/`allow` com policy por risco. Nós julgamos *trabalho*, eles julgam *ações* | repositório/README do projeto (inspeção 2026-09-23) |
| **Supervisão de runtime** | [Foreman](https://github.com/thruwire/foreman) (517★, criado 2026-09-17) | Orquestrar workers de código de ponta a ponta (Codex/OpenCode), decidir `continue`/`steer`/`stop` em tempo real | repositório/README do projeto (inspeção 2026-09-23) |
| **Peneira de contexto** | [Winnow](https://github.com/GhalebDweikat/winnow) (68★, criado 2026-09-16) | Reduzir o que entra na janela do Claude Code, com shadow mode/replay/ECE para calibrar | repositório/README do projeto (inspeção 2026-09-23) |
| **Roteamento de capacidades** | [JevRouter](https://github.com/BillionsBobby/JevRouter) (173★, criado 2026-09-18) | Escolher *qual modelo/ferramenta* resolve uma tarefa, com política e `no_decision` por confiança | repositório/README do projeto (inspeção 2026-09-23) |

**Como conviver na prática**

1. **Hook de commit nosso + guarda deles.** `.git/hooks/pre-commit` chama `jev-harness test-gate`
   (bloqueia apenas vermelho real); o mesmo agente registra `jev-guard` como gate de tool call.
   Os dois rodam sem se ver: um julga o resultado do trabalho, o outro a intenção da ação.
2. **Foreman dirigindo, nós aconselhando.** O Foreman decide o fluxo do worker; ele pode chamar
   `jev-harness abort-check` no ponto de decisão "insisto ou paro?" e usar a categoria como
   evidência — sem entregar o controle do loop para nós.
3. **Winnow filtra, nós triamos.** O Winnow escolhe que trechos do contexto entram; quando um
   teste falha, `jev-harness test-gate` decide se aquela falha é resolvível sem um modelo caro.
4. **JevRouter roteia o modelo, nós roteamos o *tier* de qualidade.** `route` responde "quanto de
   raciocínio este trabalho merece"; o JevRouter responde "qual capacidade executa isso".
5. **Nunca empilhe dois juízes no mesmo ponto.** Cada gancho tem um dono: se o Foreman já decidiu
   abortar, não passe a mesma decisão por nós — escolha o dono do veredito e registre o outro
   como evidência.

**O que não fazemos (e não devemos passar a fazer sem um novo gate):** interceptar tool calls
(jev-guard), supervisionar workers em tempo real (Foreman), selecionar contexto de agente
(Winnow) ou catalogar capacidades de modelo (JevRouter). Ver §6 (WS5) para os gatilhos de revisão.

**Verificação desta seção:** `python scripts/check_links.py --root .` valida os links internos e
inventaria os externos; cada afirmação comparativa acima cita a fonte e a data de inspeção.

## 4. Catálogo de oportunidades (priorizado)

Legenda: **E** = esforço (P/M/G), **R** = risco (baixo/médio/alto), **Encaixe** = aderência ao nosso nicho.

### Tier 0 — Confiabilidade (antes de qualquer feature nova)

| ID | Oportunidade | Evidência / por quê | E | R | Encaixe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **O0.1** | **Corrigir o parser Score do Rust (P0)** — score float, legend mapa, probabilities | Bug de produção: `severity` live = 3.0 default no Rust vs 0.96/1.01 em Python/TS; `verify` sempre reprovado | P | Médio | Total (já no plano) |
| **O0.2** | **Retry/backoff + `Retry-After` + política de falha explícita** (`--fail-open` default, `--fail-closed` opcional) com fallback offline **marcado** (`is_mock` + motivo) | Teste de hoje: `base_url` inválida → **`RuntimeError` não tratada** no `cmd_test_gate` (sem try/except). Foreman retenta 429/5xx e tolera 3 falhas; jev-guard é fail-open com opção `FAIL_CLOSED`; Winnow faz pass-through. Os limites do provedor são **dinâmicos** (429 documentado) | M | Baixo | Total |
| **O0.3** | **Pin de versão do modelo + validação de payload** (`jev-1.13.0` quando thresholds calibrados; avisar >32k/64k) | Docs oficiais: thresholds calibrados devem fixar a versão; limites 64k total / 32k state+maior pergunta | P | Baixo | Total |
| **O0.4** | **Estado estruturado (JSON) nas perguntas** em vez de string concatenada | Docs oficiais e JevRouter (`{request, actor, context}`) usam JSON; nós enviamos `str(state)` — perde estrutura e referência por caminho (`` `path` ``) | M | Baixo | Total |

### Tier 1 — Confiança e calibração (maior gap de maturidade)

| ID | Oportunidade | Evidência / por quê | E | R | Encaixe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **O1.1** | **Shadow mode** (`--shadow`): decide, registra e **não** altera exit/ação; relatório do que "teria decidido" | Winnow recomenda rodar 1 semana em shadow antes de confiar; nós aplicamos thresholds direto | P | Baixo | Total |
| **O1.2** | **Replay/eval offline com corpus rotulado** de logs (pytest/vitest/cargo) + métricas (matriz de confusão, ECE, ROC) para calibrar `skip_llm_threshold`/`abort_threshold` | Winnow tem `replay {extract,judge,score,label}` com labels fracos e manuais; nossos thresholds são defaults (`config.py:24`) sem dados — as docs oficiais mandam calibrar com os seus dados | M/G | Baixo | Total |
| **O1.3** | **Recibos de decisão append-only com hash de entrada** (`{gate, input_hash, decisão, confiança, modelo, is_mock, timestamp}`) | JevRouter: "receipts by default" com `provenance.candidate_snapshot_hash`; o próprio ecossistema pede "provenance for all those micro-decisions"; ThruWire vive disso | P/M | Baixo | Total |
| **O1.4** | **Custo/latência reais por decisão** (parse de `usage`/`cost` da resposta; comparar com a estimativa do `metrics`) | A resposta traz `usage` e `cost`; hoje só temos estimativa rotulada. jev-guard mostra custo por chamada; com $0,042/Mtok, 1.000 gates ≈ $0,04 | P | Baixo | Total |

### Tier 2 — Alcance e distribuição

| ID | Oportunidade | Evidência / por quê | E | R | Encaixe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **O2.1** | **GitHub Action** de triagem de falha de CI (log do job → `test-gate` → anotação no PR com categoria + ação determinística; nunca bloqueia verde) | **Ninguém no ecossistema oferece isso.** Encaixa no offline-first, no pre-commit e no guia; alcance de adoção muito maior que CLI | M | Baixo | Total |
| **O2.2** | **Plugins oficiais por host** (Claude Code marketplace, Codex plugin, OpenCode plugin/skill) usando o padrão do jev-guard/Winnow | jev-guard instala com `/plugin marketplace add` em 8 hosts; nós dependemos de MCP + guia manual | M | Médio | Alto |
| **O2.3** | **Interop documentado** (pairing recomendado: jev-guard para tool calls + `jev-harness` para qualidade + Foreman para runtime) | Evita canibalização e posiciona o produto no ecossistema, não contra ele | P | Baixo | Total |
| **O2.4** | **`jev-harness doctor`** (chaves, provider, endpoint, modelo, rede, limites, config) | jev-guard e Winnow têm `doctor`/`install` guiado; reduz fricção de agentes (nosso guia já mostra que isso importa) | P | Baixo | Total |

### Tier 3 — Qualidade de decisão e percepção

| ID | Oportunidade | Evidência / por quê | E | R | Encaixe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **O3.1** | **UncertaintyEngine corrigida** (D1 do plano): usar as distribuições reais, precedência explícita, guardas (zeros, K=1, chaves), Noul sem ΔP/H_n | Distribuições existem no live (medido); hoje ignoramos; thresholds do provedor derivam `confidence` da distribuição | M | Médio | Total |
| **O3.2** | **Cache de decisão por hash do log** (opt-in, TTL, ignorando `--no-cache`) | jev-guard cacheia scans por hash; JevRouter tem cache opt-in; reruns de CI repetem logs idênticos — custo zero no Zen, mas **não** no TypeSafe direto | P/M | Baixo | Total |
| **O3.3** | **Debounce/coalescing** para `nudge`/`abort` (intervalo mínimo + avaliação periódica) | Foreman usa 5s mínimo / 30s periódico para não martelar o Jev; integrações por turno podem chamar a cada passo | P | Baixo | Total |
| **O3.4** | **Memória de decisões por sessão** (histórico real para abort/nudge, não só o que o chamador envia) | Foreman passa o resultado anterior; nós dependemos do chamador. Sessão já existe — falta alimentar os gates | M | Baixo | Total |
| **O3.5** | **PerceptionSlicer + redação**: `focused_slice`/`causal_context` + redigir segredos **no state** enviado | Jaggedness documenta context rot; hoje truncamos 6000 chars sem recorte semântico e redigimos só erros | M | Baixo | Total |

### Tier 4 — Expansões (cautela; avaliar contra o nicho)

| ID | Oportunidade | Veredito |
| :--- | :--- | :--- |
| **O4.1** | `turn-gate` / orquestrador unificado (D3) | **Adiar** até ter O1.2 (medição) — risco de context rot e de degradar gates que hoje funcionam |
| **O4.2** | Supervisão contínua de runtime (estilo Foreman) | **Não fazer** — integrar/documentar parceria |
| **O4.3** | Tool gating / guardrail de ações | **Não fazer** — jev-guard já cobre com 8 hosts |
| **O4.4** | Peneira de contexto de agente | **Não fazer** — Winnow já cobre |

---

## 5. "Podemos ser 1.5?" — veredito com rubrica

**Definição operacional em 3 níveis:**

| Nível | Definição | Resposta |
| :--- | :--- | :--- |
| **N1 — Usar Jev como camada de decisão** | Chamar o System 1 para julgamentos estreitos e compor em código | ✅ **Sim, já fazemos** (6 gates, política determinística, offline fallback) |
| **N2 — Ser o tecido conjuntivo System 1.5 de um domínio** | Ser a camada que conecta o System 1 ao System 2 com contratos, evidência e política, num domínio específico | ✅ **Sim — no domínio de qualidade de código**; já somos parcialmente (triage/abort/nudge/verify/effort/route + hook + MCP). Tier-0/1 fecham o restante |
| **N3 — Ser "a" System 1.5 completa** | Substituir a categoria inteira (runtime + roteamento + contexto + segurança + qualidade + artefatos) | ❌ **Não.** É uma categoria, não uma ferramenta: 5 papéis já ocupados por projetos MIT ativos (517★/173★/68★/26★). Tentar seria anti-Karpathy e anti-Frankenstein |

**Scorecard pelos 5 pilares (0–5, com base nos fatos auditados):**

| Pilar | Nota | Justificativa |
| :--- | :---: | :--- |
| 1. Cola fast↔deep | **3/5** | `effort` (8 níveis) + 7 dialetos + lease passivo; falta lease ativo/break-glass |
| 2. Decisões tipadas que escalam | **3/5** | Gates + `skip_llm` + categorias; distribuições reais disponíveis mas não usadas; thresholds sem calibração |
| 3. Roteamento, gates e recuperação | **4/5** | 6 gates + exit codes + ação determinística; falta recuperação estruturada segura (sem auto-run) |
| 4. Percepção e atenção | **3/5** | Truncamento UTF-8 + priorização de asserções; falta slices semânticos e redação do state |
| 5. Máquinas de estado com julgamento | **3/5** | Fases + nudge/waiting/progress; consultivo, sem veto com evidência |
| **Total** | **16/25** | **System 1.5 em formação, com base sólida e dois diferenciais únicos** |

**Frases que podemos afirmar (defensáveis):**
- *"O `jev-harness` é uma camada de decisão System 1.5 para o ciclo de qualidade de agentes de código: Jev para julgamento semântico, software determinístico para as consequências."*
- *"É o único gate de qualidade tri-runtime (Python/TS/Rust), offline-first e com ROI telemetry do ecossistema Jev."*

**Frases que não podemos afirmar:**
- *"É o control plane completo de software factories."*
- *"Supervisiona agentes em tempo real"* (isso é o Foreman) / *"Bloqueia ações perigosas"* (jev-guard) / *"Seleciona contexto"* (Winnow).

---

## 6. Estratégia recomendada (3 horizontes, sem vínculo com versão)

> Princípio: **não copiar escopo — copiar práticas.** O ecossistema já provou quais práticas funcionam (retry, fail-open configurável, shadow, replay, receipts, cache, plugins). Nosso diferencial (offline-first, tri-runtime, zero-dep, qualidade) permanece.

| Horizonte | Foco | Itens |
| :--- | :--- | :--- |
| **H1 — Confiabilidade** (1–2 semanas) | Não corromper decisões em produção | O0.1 (P0 Rust) → O0.2 (retry/falha) → O0.3 (pin/limites) → O1.1 (shadow) |
| **H2 — Confiança** (3–6 semanas) | Tornar as decisões auditáveis e calibradas | O1.2 (replay/labels) → O1.3 (recibos) → O1.4 (custo real) → O3.2 (cache) → O3.5 (slices) |
| **H3 — Alcance** (7–12 semanas) | Distribuição e adoção | O2.1 (GitHub Action) → O2.4 (doctor) → O2.2 (plugins) → O3.1 (incerteza) → O3.3/O3.4 |
| **Contínuo** | Governança | Quad-sync, 211+ testes, paridade tri-runtime, regra de frescor de 30 dias |

**Métrica de sucesso do H2:** publicar uma curva de calibração dos nossos gates (acurácia das categorias e regret dos thresholds) em um corpus de logs reais — algo que **nenhum projeto do ecossistema fez para triagem de testes**.

---

## 7. Fontes e método

Toda a §2–§4 foi construída com: (a) inspeção direta dos repositórios e READMEs em 2026-09-23; (b) API do GitHub para estrelas/datas/licença; (c) documentação oficial da TypeSafe (Introdução, System One, Confidence, Patterns, Fan-out, Models, Jaggedness, Coding agents, Agent skill); (d) artigos de Josh Rosen (18–22/09/2026); (e) medições próprias no `v0.1.14` (latência, falha de provider, thresholds, parser Rust). Fontes detalhadas com URLs em [`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md) §2.

## 8. O que não foi verificado

- Estrelas/atividade são uma fotografia de 2026-09-23 (projetos com <7 dias; rankings mudam rápido).
- O benchmark do JevRouter é auto-reportado no repositório dele (método e dados públicos na issue #2), não reproduzido por nós.
- Não avaliamos a fundo o código dos concorrentes (apenas READMEs/estrutura); conclusões de sobreposição são baseadas em escopo declarado e funcionalidades documentadas.
- O roadmap do Winnow (done-ness gate) é uma intenção declarada no README, não uma funcionalidade entregue.
