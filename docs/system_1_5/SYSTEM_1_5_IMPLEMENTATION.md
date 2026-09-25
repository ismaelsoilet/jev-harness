# 🛠️ Plano de Implementação — System 1.5 (jev-harness)

[ 🏠 Repositório](../../README.md) | [ 📚 Hub de Documentação](../README.md) | [ 🧠 Plano System 1.5](SYSTEM_1_5_PLAN.md) | [ 🧭 Oportunidades](SYSTEM_1_5_OPPORTUNITIES.md) | [ 🚀 Implementação](SYSTEM_1_5_IMPLEMENTATION.md)

> **Documento companheiro de [`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md) (arquitetura-alvo) e [`SYSTEM_1_5_OPPORTUNITIES.md`](SYSTEM_1_5_OPPORTUNITIES.md) (oportunidades e veredito).**
> Este é o plano **executável**: cada item tem escopo, arquivos, critérios de aceite verificáveis e testes obrigatórios.
> **Isto não é um plano de release.** Nenhum item fixa versão; cada um entra em release quando passar o DoD (§2) pelo protocolo do repositório ([`../../.agents/rules/05_release_and_quad_sync_protocol.md`](../../.agents/rules/05_release_and_quad_sync_protocol.md)).
> **Base:** `v0.2.0` · **H1 entregue** (E0.1–E0.3, E1.1) · 626 testes verdes (432 Python + 99 TS + 95 Rust) · pesquisa datada de 2026-09-23.

---

## Status de entrega

> **Estado do working tree (2026-09-23, não publicado):** H1 está implementado e verificado; parte de H2/H3 também. Nada foi commitado/publicado ainda — a decisão de release é do proprietário (§10).

| Onda | Épico | Estado |
| :--- | :--- | :--- |
| **H1** | E0.1 (paridade Score no live + fixture tri-runtime) | ✅ implementado |
| **H1** | E0.2 (retry/`Retry-After`/fail-open/`--fail-closed`/`--retries`, payload malformado, sem traceback) | ✅ implementado |
| **H1** | E0.3 (modelo fixável + origem no `status`, limites de payload em code points) | ✅ implementado |
| **H1** | E1.1 (shadow mode; precedência do shadow sobre `--fail-closed`) | ✅ implementado |
| **H2** | E1.2 (corpus 160 casos rotulados + `replay` + `docs/REPLAY_REPORT.*` + gate de regressão no CI) | ✅ implementado |
| **H2** | E1.3 (recibos append-only `0600` + comando `receipts` + `--no-receipts`) | ✅ implementado |
| **H2** | E1.4 (tokens/custo medidos no `metrics`, separados da estimativa) | ✅ implementado |
| **H2** | E0.4 (estado estruturado + `--state-json`) | ✅ implementado |
| **H2** | E3.1 (incerteza com guardas + paridade tri-runtime da matemática) | ✅ implementado |
| **H2** | E3.5 (slice focado + contexto causal + redação do `state` nos 3 runtimes) | ✅ implementado |
| **H2** | E3.6 (recuperação estruturada sem auto-execução, com allowlist + flag) | ✅ implementado |
| **H2** | E3.8 (`.jev/` ignorado, retenção, permissões, matriz de privacidade) | ✅ implementado |
| **H2** | E3.9 (probabilidades da mock paritárias + conflito de sinais) | ✅ implementado |
| **H3** | E2.1 (GitHub Action), E2.4 (`doctor`) | ✅ implementado |
| **H3** | E2.2 (plugins Claude Code + Codex/OpenCode), E2.3 (interop + link-checker) | ✅ implementado |
| **H3** | E3.2 (cache por hash + hit-rate), E3.3 (debounce/coalescing) | ✅ implementado |
| **H3** | E3.4 (memória de sessão nos gates), E3.7 (lease persistente + break-glass) | ✅ implementado |
| **WS5** | O4.1–O4.4 | 🚫 Fora de escopo (com gatilhos no §7) |

**Assimetrias declaradas (Python-first, deliberadas):** recibos, cache de decisão e o lease são
estado do lado Python (o CLI, o MCP server e o SDK Python escrevem; TS/Rust permanecem stateless,
como já acontecia com a sessão). Os campos aditivos `recovery` (E3.6) e `uncertainty` (E3.1) são
emitidos pelo runtime Python; a **matemática** da incerteza é paritária nos três (fixture
`tests/fixtures/uncertainty_golden.json`) e a **redação de segredos** roda nos três runtimes.
Nenhum desses campos altera `skip_llm` ou exit codes.

**Pré-requisitos fora da ordem original:** o detector determinístico de injeção (escopo do E3.8/E3.6) entrou junto com o E1.2, porque o gate de CI do E1.2 exige que nenhum caso adversarial seja classificado de forma determinística.

**Correções de paridade encontradas pelo próprio corpus (E1.2):** o gate de paridade
(`tests/fixtures/corpus_parity.json`, 160 casos × 6 gates, lido por TS e Rust) revelou e fechou:
critérios do triage diferentes no Rust, triggers extras, tokenizador ASCII no TypeScript, `^fail`
ancorado na string inteira em vez de por linha, **ordem de iteração não determinística do
`HashMap` de critérios no Rust** (empates mudavam de veredito), fallback de fase divergente e
listas de sinais positivos/negativos desalinhadas. Após a canonicalização: **0 divergências em
160 casos**, e o `verify` subiu de 0.625 para 0.829 de macro-F1 no corpus.

**Fechados na rodada de revisão adversarial (2026-09-23):** a redação de segredos passou para o
cliente (valia só no triage — `route/verify/abort/effort/nudge` transmitiam o segredo cru);
`--state-json` passou a existir de fato (estava documentado e ausente, com `parse_state_json` sem
chamador); a memória do `abort` era calculada e descartada (agora entra no `state`); a allowlist de
recuperação aceitava um pacote apenas **citado em prosa** num manifesto; o break-glass deixava o
lease permanentemente inerte; a contagem de passos do lease reportava o valor anterior ao consumo;
a validação `K >= 2` não era chamada no TS/Rust; a regra de chaves não numéricas da incerteza
divergia entre os runtimes; o renderizador do TS/Rust não ignorava os campos de percepção; o
`uncertainty` não era exposto no MCP; e a matriz de privacidade contradizia a redação do state.
`cargo fmt --check` e `cargo clippy -D warnings` passaram a ser executados na CI (a dívida de
formatação herdada foi zerada).

**Achados medidos e ainda abertos** (ver `docs/REPLAY_REPORT.md` e `tests/corpus/README.md`): a linha `FAILED <nodeid>` de um runner pode dominar uma causa-raiz concreta de ambiente; a sobreposição acidental de tokens com as descrições dos critérios pode inverter uma categoria (direção perigosa: `skip_llm=true` num erro de sintaxe); `502`/broker não estão nas listas de transientes; os gates Noul (`verify`/`nudge`/`effort`) ficam entre 0.5 e 0.7 de macro-F1. Corrigir isso é *calibração* (mudança de heurística com comparação antes/depois no corpus e paridade tri-runtime), deliberadamente fora do épico que mede.

## 0. Como usar este plano (regras para agentes implementadores)

1. **Um épico por vez, na ordem do §6.** Não abra frentes paralelas sem autorização explícita.
2. **Reproduza antes de corrigir:** todo bug/guard começa com um teste que falha (ou um caso de corpus que demonstra o problema).
3. **Paridade tri-runtime é obrigatória** para qualquer mudança semântica de gate: mesma entrada → mesmo veredito em Python, TS e Rust (tolerância numérica documentada onde houver float). Persistência de sessão/lease é Python-first com leitura nos demais runtimes (ver E3.4/E3.7).
4. **Aditivo por padrão:** novos campos/CLI flags/tools MCP **nunca** removem ou renomeiam os existentes; exit codes `0/1/2` e o contrato `skip_llm` permanecem.
5. **Nada de claims sem medição:** toda afirmação de latência/custo/acurácia neste repositório deve ser medida, datada e rotulada (provedor vs harness).
6. **DoD (§2) antes de pedir review.** Sem DoD, o item não entra em release.
7. **Fora de escopo (§7) não se discute sem novo gate** — a decisão já foi tomada com evidência.

---

## 1. Objetivos e princípios

**Objetivo:** tornar o `jev-harness` a **camada de decisão System 1.5 de referência para o ciclo de qualidade de agentes de código**, sem perder os três diferenciais únicos do ecossistema: **offline determinístico**, **tri-runtime com paridade** e **zero dependências de runtime**.

**Princípios de engenharia (herdados do repo + pesquisa):**
- Código determinístico dono das consequências; Jev só no julgamento (docs TypeSafe; padrão "Jev não controla").
- Perguntas atômicas, contexto mínimo por pergunta (jaggedness: context rot).
- Falha do provedor não pode quebrar o pipeline do usuário (padrão fail-open configurável do ecossistema).
- Decisão auditável > decisão opaca (receipts/proveniência do JevRouter; comentário do ecossistema).
- Não copiar escopo de concorrentes (Foreman/JevRouter/Winnow/jev-guard); **integrar**.

---

## 2. Definição de Pronto (DoD)

### DoD global (todo item)
1. Testes novos cobrindo o comportamento e os limites (ver testes por épico).
2. Bateria completa verde: `./scripts/release.sh --check` (3 runtimes, com os testes novos já somados à bateria vigente).
3. Paridade tri-runtime verificada para mudanças de gate (ou divergência documentada e testada); persistência de sessão/lease é Python-first com leitura nos demais (E3.4/E3.7).
4. `./scripts/release.sh --verify-sync` verde.
5. Documentação afetada atualizada (README EN/PT, guia, `.agents/rules/` quando aplicável).
6. Sem novos warnings de clippy; sem dependências de runtime novas.
7. Claims novos medidos e datados.

### DoD por classe de item
| Classe | Exigência adicional |
| :--- | :--- |
| Bug (P0) | Teste de regressão que falhava antes e passa depois; nota semver se mudar tipo público |
| Resiliência | Teste com falha simulada (429/timeout/5xx) provando o comportamento fail-open/fail-closed |
| Calibração | Corpus versionado + relatório de métricas (matriz de confusão, ECE) |
| Distribuição (Action/plugins) | Instalação limpa em ambiente virgem + exemplo reproduzível |
| Segurança | Casos adversariais no corpus (injeção no log, pacote malicioso) |

---

## 3. Visão geral

| WS | Nome | Épicos | Oportunidades/achados cobertos | Horizonte |
| :--- | :--- | :--- | :--- | :--- |
| **WS0** | Confiabilidade | E0.1–E0.4 | O0.1–O0.4, B1 | H1 (E0.4 entra em H2, após E1.2) |
| **WS1** | Confiança & calibração | E1.1–E1.4 | O1.1–O1.4 | H1–H2 |
| **WS2** | Alcance & distribuição | E2.1–E2.4 | O2.1–O2.4 | H3 |
| **WS3** | Decisão, percepção e segurança | E3.1–E3.9 | O3.1–O3.5, B2–B5, B7 | H2–H3 |
| **WS4** | Documentação & apresentação | E4.1–E4.3 | B6, README (overclaims), interop | H1–H3 |
| **WS5** | Fora de escopo (decisão registrada) | — | O4.1–O4.4 | — |

---

## 4. Matriz de rastreabilidade (cobertura completa)

| ID | Origem | Épico | Critério de aceite-resumo |
| :--- | :--- | :--- | :--- |
| B1 / O0.1 | Plano §5 / Oportunidades | E0.1 | Rust live: `severity/viability/rigor/complexity` iguais aos outros runtimes |
| O0.2 | Oportunidades | E0.2 | 429/5xx/timeout → retry com `Retry-After`, depois fallback marcado; política configurável |
| O0.3 | Oportunidades | E0.3 | Versão do modelo fixável; payload > limite avisa/recusa com erro claro |
| O0.4 | Oportunidades | E0.4 | Gates aceitam `state` estruturado (JSON) sem quebrar a API de string |
| O1.1 | Oportunidades | E1.1 | `--shadow` decide, registra e **não** altera exit/ação |
| O1.2 | Oportunidades | E1.2 | Corpus + relatório de calibração por gate (matriz, ECE, regret) |
| O1.3 | Oportunidades | E1.3 | Recibos append-only com hash de entrada e decisão |
| O1.4 | Oportunidades | E1.4 | `metrics` separa real (`usage`/`cost`) de estimativa |
| O2.1 | Oportunidades | E2.1 | GitHub Action triando CI sem bloquear verde, com anotação no PR |
| O2.2 | Oportunidades | E2.2 | Plugin instalável em ≥2 hosts (Claude Code/Codex/OpenCode) |
| O2.3 | Oportunidades | E2.3 | Seção de interop com Foreman/JevRouter/Winnow/jev-guard |
| O2.4 | Oportunidades | E2.4 | `doctor` diagnostica chave/provider/rede/modelo/config |
| O3.1 / B3 | Oportunidades / Plano | E3.1 | Incerteza com distribuições reais + guardas (zeros, K=1, chaves) |
| O3.2 | Oportunidades | E3.2 | Cache por hash do log com TTL e `--no-cache` |
| O3.3 | Oportunidades | E3.3 | Debounce/coalescing para nudge/abort |
| O3.4 | Oportunidades | E3.4 | Memória de sessão alimenta abort/nudge |
| O3.5 / B5 | Oportunidades / Plano | E3.5 | Slices `focused/causal` + redação do state |
| B2 | Plano §5 | E3.6 | Recuperação **sugerida** (argv, sem shell string, sem auto-run) |
| B4 | Plano §5 | E3.7 | Lease persistente com `schema_version` e contrato do chamador |
| B5 | Plano §5 | E3.8 | `.jev/` ignorado, retenção/TTL, redação |
| B7 | Plano §5 | E3.9 | Mock: probabilidades paritárias entre runtimes |
| B6 | Plano §5 | E4.1 | README/pitch sem overclaims; números medidos e datados |
| — | Oportunidades §3 | E4.2 | Documentação de posicionamento + links cruzados |
| — | Oportunidades §5 | E4.3 | Guia do agente com "o que é / o que não é" System 1.5 |
| O4.1–O4.4 | Oportunidades | WS5 | Decisão registrada: não fazer agora (com gatilhos de revisão) |

---

## 5. Épicos detalhados

### WS0 — Confiabilidade

#### E0.1 — P0: corrigir o parser Score do Rust no modo live *(B1 / O0.1)*
**Objetivo:** paridade live real para respostas `Score` (hoje descartadas silenciosamente).
**Escopo:**
- `ScoreAnswer`: `score: f64`; `legend` tolerante (mapa **ou** lista); `probabilities: Option<HashMap<String, f64>>`.
- `parse_api_response`: não descartar silenciosamente; logar/contabilizar falha de parse em modo debug.
**Tarefas:**
1. Fixture com payload live gravado (`tests/fixtures/live_score.json`) — capturado da API real (sanitizado).
2. Teste de contrato Rust: parse do fixture → `score=1.76`, `legend` mapa, `probabilities` presentes.
3. Teste diferencial tri-runtime: mesma pergunta live (ou fixture) → `severity/viability/rigor/complexity` equivalentes.
**Aceite:** `verify` live no Rust deixa de reprovar sempre; valores batem com Python/TS no fixture; nota semver em "What's New" do README (o repositório não mantém um arquivo CHANGELOG separado; a seção de release do README é o changelog oficial).
**Testes:** unit (Rust) + contrato (fixture compartilhado) + integração live opcional (gated).
**Riscos:** quebra de tipo público no crate → documentar e lançar em versão 0.x com nota explícita.
**Esforço:** P. **Deps:** nenhuma (fazer primeiro).

#### E0.2 — Resiliência de provider: retry, `Retry-After` e política de falha *(O0.2)*
**Objetivo:** nenhum erro de rede/rate-limit derruba o pipeline; comportamento explícito e configurável.
**Escopo:**
- Cliente (3 runtimes): retry com backoff exponencial **com teto (jitter-free, para CI determinístico)** para `429`/`5xx`/timeout; respeitar `Retry-After`; limite de tentativas configurável (`--retries`).
- Política de falha: `--fail-open` (**default** para gates) → cai no motor offline e marca `is_mock=true` + `degraded_reason`; `--fail-closed` → erro explícito com exit `2`.
- CLI: `try/except` em todos os comandos de gate (hoje `cmd_test_gate` não tem — `RuntimeError` vaza).
- Documentar e testar a diferença entre `is_mock=true` (decisão offline) e `degraded_reason` (fallback por falha).
**Aceite:** simulações de 429/timeout/5xx provam retry + fallback marcado; nenhum comando imprime traceback; doc atualizada.
**Testes:** testes por runtime com servidor falso (ou mock de transporte); teste de paridade de política.
**Riscos:** retry pode atrasar CI → backoff limitado (ex.: máx. 3 tentativas / ~5s); fail-open nunca mascara `--fail-closed`.
**Esforço:** M. **Deps:** E0.1 (paridade antes de mexer em rede? não bloqueia; pode paralelizar).

#### E0.3 — Versão do modelo e limites de payload *(O0.3)*
**Objetivo:** decisões reproduzíveis e payload válido.
**Escopo:**
- `model` fixável e documentado (`jev-1.13.0` para thresholds calibrados; alias por default com aviso de que o alias muda).
- Validação de limite: aviso/erro claro quando `state + perguntas` > 32k e total > 64k tokens (estimativa por caracteres com fator conservador; sem tokenizer externo).
- `status`/`doctor` mostram o modelo efetivo e a origem (default/`.jev.json`/env). *Entregue no `status` (v0.2.0); a metade `doctor` entra junto com E2.4, que é quem cria o comando.*
**Aceite:** com payload gigante, mensagem clara e exit `2`; com modelo pinado, o campo `model` do request é o pinado.
**Testes:** limites (limite-1, limite, limite+1), resolução de modelo nos 3 runtimes.
**Esforço:** P. **Deps:** —

#### E0.4 — Estado estruturado nas perguntas *(O0.4)*
**Objetivo:** aproveitar a recomendação oficial (estrutura + referência por caminho) em vez de string concatenada.
**Escopo:**
- Gates passam a montar `state` como objeto (`{failure_log, test_command, repo, previous_attempts, ...}`) mantendo o formato textual como fallback aceito.
- CLI: `--state-json <file|json>` opcional para gates que aceitam contexto extra.
- Documentar as chaves estruturadas por gate no guia.
**Aceite:** mesma entrada textual → mesma categoria (não regride); entrada estruturada → referências `` `path` `` funcionam.
**Testes:** regressão de classificação (corpus existente) + casos estruturados novos.
**Riscos:** mudança de prompt pode alterar respostas do provedor → rodar corpus antes/depois e comparar (usar E1.2).
**Esforço:** M. **Deps:** E1.2 (medição) para validar.

---

### WS1 — Confiança & calibração

#### E1.1 — Shadow mode *(O1.1)*
**Objetivo:** permitir adoção segura (decidir sem agir) e medir antes de confiar.
**Escopo:** flag `--shadow` (e chave `.jev.json` `"shadow": true`) nos gates: executa a decisão, grava recibo/telemetria, imprime o que **teria** feito, e **não** altera exit code previsto nem ação; `test-gate` verde continua `no_failure`.
**Aceite:** em shadow, o gate **sempre** retorna exit `0` (pipelines nunca quebram); a saída humana mostra `SHADOW — would exit N`; `test-gate --json` expõe `shadow: true` e `would_exit` (os demais gates reportam no stderr). **Entregue na v0.2.0.**
**Testes:** por comando; garantir que scripts que usam o exit não quebram.
**Esforço:** P. **Deps:** —

#### E1.2 — Corpus + banco de replay e calibração *(O1.2)*
**Objetivo:** medir a qualidade das decisões e calibrar thresholds **com dados**, como as docs do provedor exigem.
**Escopo:**
- `tests/corpus/` versionado: logs reais/sintéticos rotulados (`category` esperada, `skip_llm` esperado), cobrindo pytest/vitest/jest/cargo/go/mocha/rspec/unittest, PT/EN/ES, e casos adversariais (injeção no log).
- **Protocolo de rotulagem:** rótulos fracos determinísticos (resumo do runner + padrão conhecido) para todo o corpus, mais uma **amostra estratificada rotulada à mão** (≥ 30 casos, revisada por um mantenedor) para medir a confiança do próprio rótulo — documentado em `tests/corpus/README.md` com proveniência (sintético vs log real sanitizado).
- CLI `jev-harness replay --corpus <dir> [--engine mock|live] [--json]`: roda o corpus, imprime matriz de confusão por gate, precisão/recall/F1 por categoria, ECE das probabilidades, e custo/registro.
- **Baseline:** a primeira execução verde vira `docs/REPLAY_REPORT.md` (gerado, com data e versão do modelo); releases seguintes comparam contra esse baseline.
- **Gate de CI:** o replay em modo mock falha se o macro-F1 de qualquer gate cair > 2 pontos percentuais vs. o baseline **ou** se qualquer caso adversarial for classificado como `env_missing`/`flaky_transient`/`skip_llm=true`.
- Calibração sugerida de `skip_llm_threshold`/`abort_threshold` a partir da curva; defaults permanecem até dados.
**Aceite:** corpus ≥ 100 casos + amostra manual ≥ 30; relatório reproduzível; os dois critérios do gate de CI verdes.
**Testes:** o próprio replay é o teste; CI roda em modo mock com o gate acima (limiares numéricos explícitos no script).
**Esforço:** M/G. **Deps:** E0.1 (para incluir Rust) — ou começar em Python/TS.

#### E1.3 — Recibos de decisão com proveniência *(O1.3)*
**Objetivo:** auditoria barata e compatível com o padrão do ecossistema.
**Escopo:** registro append-only local (`.jev/receipts.jsonl`, 0600) com `{ts, gate, input_hash, decision, confidence, model, is_mock, degraded_reason, shadow}`; comando `jev-harness receipts [--tail N] [--json]`; flag `--no-receipts`. Retenção/TTL e redação são fechadas no E3.8 (dependência direta).
**Aceite (fase 1):** hash estável (mesma entrada → mesmo hash); nenhum conteúdo sensível bruto no recibo (só hash + metadados). Retenção/TTL configuráveis são critério da fase 2 (E3.8).
**Testes (fase 1):** estabilidade do hash e concorrência (reusar o lock da sessão); rotação/retenção são testadas no E3.8.
**Esforço:** P/M. **Deps:** — (fase 1: recibos + hash; a retenção/TTL e a redação entram no E3.8, que depende deste épico — sem ciclo).

#### E1.4 — Custo e latência reais por decisão *(O1.4)*
**Objetivo:** separar medição de estimativa na telemetria.
**Escopo:** parse de `usage`/`cost` da resposta; `metrics` passa a mostrar `measured_tokens`, `measured_cost` e manter a estimativa rotulada; `--json` expõe ambos.
**Aceite:** em live, tokens reais aparecem; em mock, campo é `null`/rotulado; documentação explica a diferença.
**Testes:** com fixture de resposta real; agregadores (soma, sessão, reset).
**Esforço:** P. **Deps:** —

---

### WS2 — Alcance & distribuição

#### E2.1 — GitHub Action de triagem de CI *(O2.1)*
**Objetivo:** o primeiro gate de qualidade Jev para CI — alcance muito maior que CLI local.
**Escopo:** action (composite) que: captura o log do step que falhou (`if: failure()`), roda `jev-harness test-gate --json`, publica a categoria/ação como anotação no job e (opcional) comentário no PR; **nunca** bloqueia execução verde; modo `shadow` suportado; funciona offline por default (mock) e live com `TYPESAFE_API_KEY`.
**Aceite:** exemplo em repo de teste: job vermelho → anotação com `deep_logic`/ação; job verde → nenhuma anotação e exit 0.
**Testes:** workflow de exemplo no próprio repo (`examples/github-action/`) exercitado em CI com logs sintéticos.
**Esforço:** M. **Deps:** E0.2 (resiliência), **E3.5 e E3.8** (o log de CI não pode ir a live sem redação e política de retenção; modo mock é o default até lá); E1.1 (shadow) opcional.

#### E2.2 — Plugins por host *(O2.2)*
**Objetivo:** instalação de um comando nos hosts mais usados (padrão jev-guard/Winnow).
**Escopo:** pelo menos 2: **Claude Code** (plugin/marketplace com hook de sessão e skill) e **Codex/OpenCode** (plugin/skill). O plugin injeta as regras do guia e registra o MCP; não duplica lógica.
**Aceite:** instalação limpa em host virgem seguindo o README do plugin; `jev-harness doctor` valida a instalação.
**Testes:** validação de manifesto por host + teste manual documentado.
**Esforço:** M. **Deps:** E2.4 (doctor).

#### E2.3 — Interop documentado *(O2.3)*
**Objetivo:** posicionar no ecossistema sem canibalizar.
**Escopo:** seção "Interop" em `SYSTEM_1_5_OPPORTUNITIES.md`/README: quando usar cada um (nós = qualidade/teste/commit; jev-guard = ações; Foreman = runtime; Winnow = contexto; JevRouter = capacidades) + exemplos de convivência (ex.: hook de commit nosso + guarda deles).
**Aceite:** tabela com links e datas; nenhuma afirmação comparativa sem fonte.
**Testes:** link-checker no CI + revisão de que cada afirmação comparativa tem fonte datada.
**Esforço:** P. **Deps:** —

#### E2.4 — `jev-harness doctor` *(O2.4)*
**Objetivo:** autodiagnóstico para humanos e agentes.
**Escopo:** verifica binário/versão, config (`.jev.json`), credenciais encontradas (sem imprimir segredo), conectividade do provider (opcional `--live` com 1 chamada), modelo efetivo, limites, presença do hook de commit, permissões das pastas de estado.
**Aceite:** cada checagem imprime OK/AVISO/FALHA + comando de correção; `--json` para agentes.
**Testes:** cenários: sem chave (offline ok), chave inválida, config corrompida, hook ausente.
**Esforço:** P. **Deps:** E0.3 (modelo efetivo).

---

### WS3 — Decisão, percepção e segurança

#### E3.1 — UncertaintyEngine com guardas *(O3.1 / B3)*
**Objetivo:** usar as distribuições reais (Choice/Score) com matemática segura e contrato claro.
**Escopo:**
- Métricas por resposta: medida primária = `confidence` do provedor (derivada); medida secundária opcional = margem/entropia **com guardas** (ignorar `p≤0`; exigir `K≥2`; normalizar chaves `"0"..K−1"`/`"1"..K"`; Noul não participa de ΔP/H_n).
- Campo universal aditivo `uncertainty: {margin, normalized_entropy, confidence, escalate_to_system2, escalation_reason}` (nomes camelCase no TS/JSON conforme padrão do repo) **sem** alterar `skip_llm`/exit codes; precedência documentada: `no_failure` → neutro; `env_missing`/`flaky_transient` → `skip_llm=true` mantido; `deep_logic` → escalonamento natural.
- `escalate_to_system2` só é `true` para decisões `deep_logic` ou baixa confiança; nunca converte um verde em escalonamento.
**Aceite:** fixtures com zeros, uniformes, bimodais e K=1 (rejeitado com erro claro na criação da pergunta); paridade tri-runtime com tolerância.
**Testes:** tabela de casos de borda; golden vectors por runtime.
**Esforço:** M. **Deps:** E0.1, E1.2.

#### E3.2 — Cache de decisão por hash *(O3.2)*
**Objetivo:** determinismo e custo em reruns (CI repete logs idênticos).
**Escopo:** cache local (`.jev/cache.json`, 0600, TTL configurável) chaveado por `hash(gate + state + modelo + versão)`, com `--no-cache`; nunca cacheia quando `shadow` (ou cacheia separado).
**Aceite:** segunda execução idêntica não faz chamada (verificável por contador/uso); TTL expira; sem cache para `--no-cache`.
**Testes:** unidade + concorrência + expiração.
**Esforço:** P/M. **Deps:** E1.3 (mesma infra de hash).

#### E3.3 — Debounce/coalescing *(O3.3)*
**Objetivo:** evitar martelar o provedor em integrações por turno.
**Escopo:** para `nudge`/`abort`: intervalo mínimo configurável entre avaliações com entrada "materialmente igual" (hash) e avaliação periódica opcional; resultado em cache curto com `debounced: true`.
**Aceite:** N chamadas idênticas em < janela → 1 chamada real; entrada diferente → sempre avalia.
**Testes:** tempo simulado (sem sleep real nos testes).
**Esforço:** P. **Deps:** E3.2.

#### E3.4 — Memória de sessão nos gates *(O3.4)*
**Objetivo:** decisões melhores com histórico real (padrão Foreman).
**Escopo:** sessão passa a guardar as últimas decisões por gate (categoria, ação, ts, hash); `abort` usa isso quando `--history` não é fornecido; `nudge` usa o último nudge real; nada sensível bruto (só metadados + snippet curto já redigido). **Escopo tri-runtime:** a escrita da sessão é Python-first (fonte da verdade, como hoje); TS/Rust continuam consumindo o mesmo `session.json` em modo leitura (como já fazem em `metrics`). Escrita nativa nos 3 runtimes fica como item futuro, com a divergência documentada e testada.
**Aceite:** sem `--history`, o abort detecta repetição usando a sessão; `--history` explícito continua vencendo.
**Testes:** repetição real em sessão; isolamento entre repositórios.
**Esforço:** M. **Deps:** E1.3, E3.8.

#### E3.5 — PerceptionSlicer + redação *(O3.5 / B5)*
**Objetivo:** dar ao System 2 o sinal exato, sem ruído e sem segredo.
**Escopo:** `focused_slice` (teste + asserção, ≤ ~15 linhas), `causal_context` (bloco vizinho, higienizado), `raw_log_ref` (ponteiro local); redação de segredos **também no `state` enviado** (não só em mensagens de erro); preservar o comportamento atual de truncamento quando o slicing não for confiável.
**Aceite:** para corpus multi-runner, o slice contém a linha de asserção em ≥90% dos casos (medido no E1.2); nenhum segredo de fixture vaza.
**Testes:** corpus + fixtures de segredos.
**Esforço:** M. **Deps:** E1.2.

#### E3.6 — Recuperação estruturada **sem auto-execução** *(B2; redesenho do D2)*
**Objetivo:** transformar a recomendação textual em dado seguro e acionável.
**Escopo:** campo aditivo `recovery: {action_type, package_name, package_manager, argv, is_safe_auto_run, rationale}`; **sem** `shell_command`; `is_safe_auto_run=false` por default; validadores por ecossistema (npm `@scope/nome`, PyPI PEP 503, crates); allowlist **obrigatória** para `is_safe_auto_run=true` — o pacote tem de constar em manifesto/lockfile do repositório **e** o chamador precisa passar a flag explícita `--allow-auto-recovery`; sem allowlist ou sem flag, `is_safe_auto_run=false`. Decisões de recovery derivadas de log não confiável **nunca** são executadas automaticamente; as pré-checagens determinísticas (verde → `no_failure`; padrões conhecidos de ambiente/transiente) continuam rodando **antes** da API e não são substituídas pela classificação do provedor.
**Aceite:** corpus adversarial (nomes com `;`, backticks, `../`, flags `-r`, **typosquatting plausível fora do lockfile**) → `is_safe_auto_run=false` e nenhum argv perigoso; nenhuma execução automática sem allowlist + flag; o texto `action_recommendation` permanece para compatibilidade.
**Testes:** corpus de injeção + typosquatting + casos legítimos por ecossistema; teste de que sem `--allow-auto-recovery` nada é auto-executável.
**Esforço:** M. **Deps:** E3.5 (redação) e E1.2 (medição).

#### E3.7 — Lease persistente e contrato do chamador *(B4; D4)*
**Objetivo:** lease de esforço com invalidação real.
**Escopo:** estado de lease na sessão (`{effort, provider_params, steps_remaining, issued_at}`) com `schema_version` e **merge tolerante** (writers antigos não apagam campos); API do chamador para reportar erro de ferramenta (`--tool-error <resumo>` / campo no `turn-gate`); TTL e break-glass. **Escopo tri-runtime:** persistência Python-first; TS/Rust documentados como leitores nesta fase (escrita nativa futura).
**Aceite:** lease retorna em sub-ms; erro reportado zera o lease; writer "antigo" simulado não perde dados.
**Testes:** unidade + migração de schema + concorrência.
**Esforço:** M. **Deps:** E3.4.

#### E3.8 — Privacidade e retenção *(B5)*
**Objetivo:** fechar os vetores de vazamento encontrados na auditoria.
**Escopo:** `.jev/` no `.gitignore` (o repo e o `init`); permissões 0600/0700 (já há precedente); TTL/limite de tamanho para recibos/cache/logs persistidos; redação centralizada; matriz de privacidade atualizada no guia (incluindo o que a nova feature envia).
**Aceite:** `git check-ignore .jev/session.json` retorna ignorado; retenção apaga com o tempo configurado; doc matrix atualizada.
**Testes:** permissões, TTL, gitignore no `init`.
**Esforço:** P/M. **Deps:** E1.3, E3.5.

#### E3.9 — Paridade de probabilidades da mock *(B7)*
**Objetivo:** eliminar divergência silenciosa entre runtimes no offline.
**Escopo:** alinhar as distribuições da mock (hoje Python `0.85`, TS `0.88`; Rust `None`); expor `probabilities` de Score nos 3 runtimes; teste de paridade dedicado com tolerância. A mock também deve derivar incerteza de **conflito de sinais** (ex.: `AssertionError` + `ConnectionResetError` no mesmo log → margem menor), para o CI exercitar `escalate_to_system2=true` deterministicamente.
**Aceite:** mesma entrada → mesmas probabilidades (tolerância 1e-9) nos 3 runtimes.
**Testes:** golden vectors de mock por gate/tipo.
**Esforço:** P. **Deps:** E0.1.

---

### WS4 — Documentação & apresentação

#### E4.1 — Remover overclaims e atualizar números *(B6)*
**Objetivo:** a apresentação do repo não pode afirmar mais do que os fatos.
**Escopo (EN + PT):**
- "90ms ($0.00004)" → **medido**: offline in-process em dezenas de µs; CLI offline ~80–100 ms (cold start); live ~0,5–1,0 s (free tier); custo ~430–530 tokens de input ≈ $0,00002 (a $0,042/Mtok).
- "70ms–300ms" → **claim do provedor** (docs: ~100 ms típico, piso de 70 ms), explicitamente separado do E2E medido do harness.
- "instant startup (< 50ms)" → valor medido (~80–100 ms no modo offline).
- "never crash" → precisão: sem chave e 401/403 caem para offline; outras falhas sobem (e o E0.2 adiciona fail-open configurável).
- "Zero-hallucination" → "probabilidades calibradas (não infalíveis; ver jaggedness do modelo)".
- "122 tests" (seção de release) → a bateria vigente (hoje 626); "210-Test Battery" → idem; exemplos de bump `0.1.6` → versão atual/placeholder.
- Adicionar data de verificação e link do método onde houver benchmark (offline latency): **só manter a tabela se reproduzível** — caso contrário, rotular como "medido na v0.1.7" ou re-medir com script versionado.
**Aceite:** nenhum número/claim sem qualificação; auditoria de claims do README em `docs/` (checklist no E4.3); ambos os idiomas sincronizados.
**Testes:** script de verificação (grep dos padrões proibidos) + revisão.
**Esforço:** M. **Deps:** —

#### E4.2 — Posicionamento System 1.5 e links *(novo)*
**Objetivo:** o README explica onde a ferramenta se encaixa (categoria, não "faz tudo").
**Escopo:** seção "Where it fits: System 1.5 decision layer" com a tabela de ecossistema (Foreman/JevRouter/Winnow/jev-guard/nós), o que somos/não somos, e links para `SYSTEM_1_5_PLAN.md`, `SYSTEM_1_5_OPPORTUNITIES.md`, `SYSTEM_1_5_IMPLEMENTATION.md`; TOC compacto; badges de testes e docs.
**Aceite:** README EN/PT com a seção, links válidos, sem repetir marketing enganoso.
**Testes:** link-checker + auditoria de claims (grep dos padrões proibidos) rodando no CI.
**Esforço:** P/M. **Deps:** —

#### E4.3 — Guia do agente + regras *(novo)*
**Objetivo:** agentes que leem a documentação sabem o que usar quando e o que **não** esperar.
**Escopo:** no `docs/AGENT_INTEGRATION_GUIDE` (EN/PT): caixa "o que este projeto é / não é"; apontar os documentos System 1.5; no `.agents/rules/`: registrar que o roadmap vive nos três docs e que a regra de frescor (30 dias) se aplica à pesquisa.
**Aceite:** guia com links e data; `AGENTS.md` e `AGENTS.pt-BR.md` com entrada para os docs.
**Testes:** link-checker + verificação de que os índices EN/PT são espelhados.
**Esforço:** P. **Deps:** E4.2.

---

## 6. Sequenciamento

```
H1 (1–2 semanas)                     H2 (3–6 semanas)                    H3 (7–12 semanas)
─────────────────                    ─────────────────                   ─────────────────
E0.1 P0 Rust  ──────────────┐        E1.2 corpus/replay ──┐             E2.1 GitHub Action
E0.2 retry/falha            ├──────► E0.4 estado estruturado ├─────────► E2.4 doctor
E0.3 modelo/limites         │        E1.3 recibos         │             E2.2 plugins
E1.1 shadow                 │        E1.4 custos reais     │             E2.3 interop
E4.1 overclaims (docs)      │        E3.1 incerteza        │             E3.2 cache
                            │        E3.9 mock parity      │             E3.3 debounce
                            └──────► E3.5 slices           └───────────► E3.4 sessão
                                     E3.6 recuperação                     E3.7 lease
                                     E3.8 privacidade                     E4.2/E4.3 docs (contínuo)
```

> **Nota de re-sequenciamento (F15):** em relação a `SYSTEM_1_5_OPPORTUNITIES.md` §6, **E3.1 (incerteza) passa para H2** porque depende de E1.2 (medição antes de mexer no contrato) e **E3.2 (cache) passa para H3** para acompanhar os recibos já estabilizados. Os horizontes deste documento prevalecem para implementação.

**Regra de bloqueio:** o E0.1 é pré-requisito de qualquer trabalho que dependa de Score no Rust (E3.1, E3.9, E2.1 com Rust). O E1.2 é pré-requisito de mudanças de prompt/estado (E0.4, E3.1, E3.5, E3.6).

---

## 7. Fora de escopo (decisão registrada)

| Item | Decisão | Gatilho de revisão |
| :--- | :--- | :--- |
| O4.1 `turn-gate`/orquestrador unificado | Adiado | Só após E1.2 provar que a acurácia não regride com estado unificado |
| O4.2 Supervisão contínua de runtime | Não fazer | Parceria/integração com Foreman; reavaliar se houver pedido de usuários |
| O4.3 Tool gating | Não fazer | Integrar com jev-guard; reavaliar se houver pedido |
| O4.4 Peneira de contexto | Não fazer | Integrar com Winnow; reavaliar se houver pedido |

---

## 8. Riscos transversais e mitigação

| Risco | Prob. | Impacto | Mitigação |
| :--- | :--- | :--- | :--- |
| Mudança de prompt/estado degradar classificação | Média | Alto | E1.2 antes/depois; corpus no CI com limite mínimo de métricas |
| Retry mascarar indisponibilidade real | Média | Médio | `degraded_reason` explícito; `--fail-closed` |
| Cache servir decisão obsoleta | Baixa | Médio | TTL curto; hash inclui modelo+versão; `--no-cache` |
| Recibos vazarem dados | Baixa | Alto | Só hash+metadados; 0600; TTL; nunca conteúdo bruto |
| Quebra semver no Rust (E0.1) | Alta | Médio | Nota semver; versão 0.x; fixture de contrato |
| Escopo inflar (virar "faz tudo") | Média | Alto | WS5 travado; interop em vez de absorção |
| Novos claims de latência/custo errados | Média | Alto | DoD §2.7; revisão obrigatória de README a cada release |

---

## 9. Métricas de sucesso

1. **Qualidade:** matriz de confusão e ECE dos gates publicadas em `docs/REPLAY_REPORT.md`; nenhum adversarial classificado como determinístico.
2. **Confiabilidade:** 0 tracebacks em cenários de falha de provider; fallback marcado em 100% dos casos `--fail-open`.
3. **Custo:** tokens/custo medidos por decisão no `metrics`; cache com hit-rate reportado.
4. **Alcance:** GitHub Action instalada em ≥1 repo externo; ≥2 plugins publicados; `doctor` usado no guia.
5. **Regressão:** 626+ testes verdes em 3 runtimes; clippy 0; `--verify-sync` verde.

---

## 10. Governança

- Cada épico vira um PR pequeno (ou uma sequência) com o DoD completo; o `release.sh --check` e `--verify-sync` são obrigatórios antes do push.
- Versões: cada release segue o protocolo do repo; **este plano não define a v0.2.0** — a decisão de o que entra na 0.2.0 é do proprietário, com base nos épicos concluídos.
- Claims: documentação de release só pode citar números medidos neste plano (com data e versão).
- Frescor: pesquisa de mercado/provedores válida até **2026-10-23**.

## 11. Rollback e critérios de aborto

- Todo épico é aditivo e reversível por revert de PR; features novas têm flag/chave de desligamento (`shadow`, `--no-cache`, `--fail-closed`, `receipts off`).
- Abortar/adiar um épico se: métricas do E1.2 piorarem >10% relativo ao baseline; custo por decisão dobrar sem ganho; qualquer regressão de contrato (exit codes, `skip_llm`).

## 12. Anexos

**Comandos de verificação obrigatórios:**
```bash
./scripts/release.sh --check        # 626+ testes, 3 runtimes
./scripts/release.sh --verify-sync  # paridade de manifestos
python3 -m unittest discover -s tests
(cd packages/ts && npm test) && (cd packages/rust && cargo test --quiet)
```

**Referências:** [`SYSTEM_1_5_PLAN.md`](SYSTEM_1_5_PLAN.md) (fatos verificados e fontes) · [`SYSTEM_1_5_OPPORTUNITIES.md`](SYSTEM_1_5_OPPORTUNITIES.md) (ecossistema e oportunidades) · [`AGENT_INTEGRATION_GUIDE.md`](../AGENT_INTEGRATION_GUIDE.md) (integração).
