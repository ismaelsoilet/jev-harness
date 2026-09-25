# Integração com o Foreman (thruwire/foreman)

**[ 🇬🇧 English ](foreman.md) | [ 🇧🇷 Português ](foreman.pt-BR.md)**

O `jev-harness` disponibiliza uma superfície de adapter determinística e um bundle de operador para
fábricas de software baseadas no [thruwire/foreman](https://github.com/thruwire/foreman), além da classe de
responsabilidade acompanhante (*companion responsibility class*) para o caminho API-1 existente. Uma extensão
nativa API-2 ainda não está disponível: ela exige uma wheel `foreman-factory` API-2 revisada, publicada e fixada.
Este documento serve como guia de arquitetura e operação; os artefatos de mudança em
`openspec/changes/foreman-integration/` e `openspec/changes/foreman-evolution/` são os designs de registro oficial.

---

## 🏛️ Arquitetura: O Paradigma de Loop Duplo

Como observou o criador do Foreman, Josh Rosen, os loops de agentes combinam perfeitamente com um
modelo de decisão rápido como o Jev: o agente ganha liberdade para trabalhar enquanto um modelo independente
avalia continuamente o que está acontecendo.
O Foreman e o `jev-harness` desempenham papéis complementares e distintos nesse ecossistema:

```
                      ┌──────────────────────────────────────────────┐
                      │          thruwire/foreman (Runtime)          │
                      │  • Supervisiona workers (Codex/OpenCode)     │
                      │  • Decide: CONTINUE, STEER, RETRY, STOP      │
                      │  • É dono do loop de execução e dos hooks    │
                      └──────────────────────┬───────────────────────┘
                                             │
                               Caminho API-2  │ [foreman.extensions] (PR #24)
                               planejado       │ ou Hook Adapter (PR #23)
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │          jev-harness (Adapter Layer)         │
                      └──────┬───────────────────────┬───────────────┘
                             │                       │
         1. Triagem de Falhas│                       │ 2. Circuit Breaker
            de Testes        │                       │    Determinístico
            (test_results)   │                       │    (worker_stuck)
                             ▼                       ▼
          ┌────────────────────────────┐   ┌───────────────────────────┐
          │ extract_test_results       │   │ evaluate_worker_health    │
          │ • env_missing (skip_llm)   │   │ • Output sem ruído        │
          │ • flaky_transient          │   │ • Fingerprint de Git diff │
          │ • deep_logic               │   │ • Estagnação de dois      │
          │ • asserção de causa-raiz   │   │   sinais                  │
          │ • lista argv de reparo     │   │   (STAGNANT_EVIDENCE)     │
          └────────────────────────────┘   └───────────────────────────┘
```

### Como o `jev-harness` Agrega Valor ao Foreman

| Problema na Supervisão de Agentes | Como o Foreman Opera Isolado | Como o `jev-harness` Potencializa o Foreman |
| :--- | :--- | :--- |
| **Falhas de Teste Não Estruturadas** | Saídas de workers e verificadores ficam salvas como caudas brutas (12.000 caracteres em `latest_worker_output`); `test_results` fica vazio (`[]`). | Preenche `test_results` com registros estruturados (`category`, `skip_llm`, argv de `recovery`) e um `assertion_slice` isolado de até 500 caracteres. |
| **Abortos Falso-Positivos do Worker** | `worker_stuck` é avaliado via perguntas semânticas do Jev (`min_threshold = 0.80`), sujeitas a falsos positivos sem calibração. | Provê fingerprint determinístico de output sem ruído e do git diff em janela de 5 passos. Declina abortar se o código estiver em mutação. |
| **Doom Loops em Falhas Triviais** | Workers podem queimar mais de 50.000 tokens de raciocínio tentando corrigir um pacote ausente (`ModuleNotFoundError`) ou porta ocupada. | Retorna `skip_llm: true` com comando determinístico de reparo (`recovery.argv: ["pip", "install", "..."]`), contornando chamadas a LLMs. |
| **Sessões Interativas de Assistentes** | Workers iniciados em ferramentas interativas (Codex, Claude) emitem falhas dentro de tool calls de terminal (`PostToolUse`). | Provê parsing ciente de hooks para triar erros de execução de ferramentas em tempo real, antes do assistente queimar tokens de raciocínio no próximo turno. |
| **Integração de Zero Sobrecarga** | Não exige dependências externas pesadas (`pydantic`, `httpx`, `requests`) em tempo de execução. | Implementação pura da biblioteca padrão em Python (< 500µs em heurísticas offline ou Jev System One ao vivo). |

---

## 1. O que é entregue e onde reside

| Componente | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `ForemanTriageObserver.extract_test_results` (`extractTestResults`) | ✅ | ✅ | ✅ |
| `ForemanCircuitBreaker.evaluate_worker_health` (`evaluateWorkerHealth`) | ✅ | ✅ | ✅ |
| Preset `FOREMAN_RESPONSIBILITY_TOML` | ✅ | ✅ | ✅ |
| `recovery` dentro do registro de triagem (E3.6) | ✅ (lista argv segura) | declarado `null` | declarado `None` |
| `jev-harness export foreman` | ✅ | ✅ | ✅ |
| Extensão Nativa do Foreman (`foreman.extensions` entry point) | ⛔ Indisponível até a release de uma wheel API-2 fixada | N/A (específico Python) | N/A |

| Campo | Python | TypeScript | Rust |
| :--- | :--- | :--- | :--- |
| `category`, `severity_score`, `confidence`, `skip_llm`, `action_recommendation` | ✅ | ✅ | ✅ |
| `assertion_slice` | ✅ | ✅ | ✅ |
| `recovery` | ✅ (lista argv, nunca string de shell) | declarado `null` | declarado `None` |

A matriz de capacidade é **testada, nunca acidental**: o fixture compartilhado
`tests/fixtures/foreman_cases.json` alimenta as três suítes de teste e qualquer divergência não declarada
quebra os testes imediatamente.

---

## 2. O que faz (e o que ainda não pode fazer)

- **Registros de triagem.** Um registro por log de worker/verificador, moldado para
  `FactoryObservation.test_results: list[dict[str, Any]]`: a categoria da falha, a linha da asserção
  da causa-raiz, o veredito determinístico `skip_llm` e (no Python) o objeto estruturado de recuperação
  (`argv`, `is_safe_auto_run`, rationale).
- **Evidência de estagnação.** `evaluate_worker_health` compara um fingerprint de saída normalizada
  com um fingerprint de diff; ele recomenda abortar **apenas quando ambos permanecem inalterados** ao longo
  da janela (`STAGNANT_EVIDENCE`) e **declina** (`complete_signals: false`) quando nenhum diff está disponível.
  É evidência consultiva para a política do Foreman — o jev-harness nunca decide parar um trabalhador por conta própria.
- **Efeito nos tokens: aditivo.** `test_results` é um campo adicional; o Foreman mantém
  `latest_worker_output` (sua cauda de 12.000 caracteres) e o `git_diff` delimitado (20.000 caracteres). O
  registro adiciona cerca de 250 tokens por falha, preservando a linha da asserção e tornando a falha
  acionável por máquina.
- **Inerte até a abertura da costura no upstream.** O Foreman mantém `test_results=[]` hardcoded
  (`src/foreman/observation.py`) e seu único canal de estado para o prompt do Jev é a observação
  em si (`src/foreman/foreman/jev.py` envia `state=observation.model_dump(...)`). Os registros atuais
  entram em vigor pela **classe API-1 acompanhante** e pelo bundle de operador, não por uma extensão
  nativa API-2 ou diretamente pelo prompt do supervisor.

---

## 3. Caminhos de Ativação

### Caminho A — Extensão Nativa do Foreman (API-2; Ainda Indisponível)

A release atual do `foreman-factory` suporta apenas a API 1. A integração API-2 planejada está
bloqueada até que exista uma wheel API-2 revisada, publicada e fixada. Não adicione um entry point
`foreman.extensions` nem espere `activate()` automático no pacote atual.

### Caminho B — Classe Acompanhante API-1 Existente

Disponibilize a classe acompanhante no ambiente e passe-a explicitamente:

```python
from jev_harness.integrations.foreman_responsibility import JevTriageResponsibility

responsibilities = configured_registry(
    config,
    config_dir="/etc/foreman/responsibilities",
    additional=[JevTriageResponsibility()],
)
```

```bash
pip install jev-harness
foreman run --repo ./meu-projeto --job "..." --responsibilities-dir /etc/foreman/responsibilities
```

### Caminho C — Exportação de Bundle de Operador (Standalone / Ambientes Isolados)

```bash
jev-harness export foreman [--out-dir ./foreman-responsibilities]
```

Três arquivos são gerados — em todos os runtimes, com bytes rigorosamente idênticos:

| Arquivo | Função |
| :--- | :--- |
| `quality.jev-triage.toml` | Configuração central da responsabilidade (roteamento + checagens + `[settings]`). |
| `quality_jev_triage.py` | A classe acompanhante (`JevTriageResponsibility`). |
| `README.md` | Instruções de ativação junto aos arquivos. |

> **Nunca coloque esses arquivos dentro do diretório `.foreman/` de um repositório gerenciado.** Aquele
> diretório é estado de execução. O Foreman lê as configurações de responsabilidade a partir da *instalação*:
> `--responsibilities-dir <dir>` ou `FOREMAN_RESPONSIBILITIES_DIR`.

---

## 4. O que a classe propõe

- `RETRY_WORKER` (prioridade 700, abaixo das diretivas críticas de segurança de runtime; o limite
  de iteração do runtime é 950 e o neutro `CONTINUE` é 0) quando, **e somente quando a janela
  de evidência contém `window` avaliações**:
  * o circuit breaker retorna `should_abort` (estagnação comprovada), ou
  * a triagem classifica a falha como `env_missing` / `flaky_transient` com `skip_llm: true`;
- filtrado por suas próprias checagens Jev do preset: `deterministic_recovery_available` deve superar seu
  `min_threshold`, e `assertion_failure_critical` **veta o retry de recuperação de ambiente** quando uma
  regressão lógica genuína é provável (um trabalhador comprovadamente estagnado é reiniciado de qualquer forma — o
  veredito de estagnação já é a evidência suficiente);
- nada em caso contrário (fail-open): sem evidência, janela incompleta, timeout de diff ou `git`
  ausente significam "abstenção", nunca um palpite.

O campo `reason` da diretiva serve como **evidência de auditoria** (visível em `foreman inspect` e nos
eventos `FOREMAN_INTERVENED`). O Foreman constrói o texto de steering a partir das probabilidades das checagens,
portanto a razão não instrui o trabalhador diretamente.

---

## 5. Ressalvas de determinismo (leia antes de confiar em limiares)

- **O CWD do processo afeta o `skip_llm`.** `load_repo_config()` sobe 4 níveis a partir do diretório de
  trabalho do *processo* procurando por `.jev.json`, fazendo com que `skip_llm_threshold` possa variar entre máquinas.
  Passe `repo_root=<repositório-alvo>` para isolar a descoberta de configurações do CWD do processo do supervisor.
- **`repo_root` delimita a justificativa de recuperação.** Passe `repo_root=<repositório-alvo>` para que
  `is_safe_auto_run` e a justificativa sejam avaliadas contra os manifestos *daquele* repositório, em vez do CWD.
- **A leitura de diff é delimitada e não-bloqueante.** A classe acompanhante executa
  `git -C <repo> diff --no-ext-diff` através de um executor injetável com timeout rígido
  (`[settings] diff_timeout_seconds = 5`). Em loops assíncronos, o subprocesso é delegado para evitar travamentos;
  em caso de timeout ele falha aberto (diff `null` → declínio → abstenção).
- **Offline por padrão.** O adapter usa o motor heurístico determinístico offline
  (`is_mock: true` no registro). Injete um cliente live se desejar julgamentos neurais do Jev — isso adiciona uma
  chamada remota por avaliação (o piso de debounce é de 5s, e a avaliação periódica de 30s).

---

## 6. Fatos verificados do upstream (inspecionado em 25/09/2026 · revalidar até 25/10/2026)

| Fato | Fonte primária |
| :--- | :--- |
| Repositório `thruwire/foreman`: 552★ (verificado em 25/09/2026) | `github.com/thruwire/foreman` |
| `test_results: list[dict[str, Any]]` existe e `build()` fixa `test_results=[]` | `src/foreman/observation.py` |
| Resumo do verificador é cauda bruta: `summary=(record.stdout or record.stderr)[-output_limit:]` | `src/foreman/runtime.py` |
| `worker_stuck` / `work_off_track` são perguntas Noul a `min_threshold = 0.80`; `meaningful_progress` não declara nenhum | `src/foreman/responsibilities/definitions/core.worker-health.toml` |
| Configuração de responsabilidade é central; repositórios-alvo não a fornecem; `.foreman/` é estado | `docs/routing.md`, `README.md` |
| Um TOML configura uma classe instalada; ambos os casos faltantes saem com código 2 | `src/foreman/responsibilities/configuration.py` |
| Extensões de terceiros são aceitas via `[project.entry-points."foreman.extensions"]` e habilitadas em `config.toml` | `docs/extensions.md`, `src/foreman/extensions.py` (PR #24) |
| Hooks de assistentes interativos (`foreman hook --client <adapter>`) avaliam em `PreToolUse`, `PostToolUse`, `Stop` | `docs/hooks.md`, `src/foreman/hooks.py` (PR #23) |
| Worktrees git vinculadas isolam o rastreamento do `.foreman/` | `src/foreman/persistence.py` (PR #26) |
| O único canal de estado para o prompt do Jev é a observação (`state=observation.model_dump(mode="json")`) | `src/foreman/foreman/jev.py`, `src/foreman/steering.py` |
| Diretivas são ranqueadas por `(priority, confidence)` com travas (`max_retries=1`, `max_workers=3`) | `src/foreman/policy.py` |
| Dependências do Foreman v0.3.0+: `pydantic`, `python-dotenv`, `rich`, `typer`, `typesafe-sdk` | `pyproject.toml` |

---

## 7. Perguntas Frequentes (FAQ Técnico para Mantenedores)

### P: Por que empacotar isso como extensão externa em vez de embutir no core do Foreman?
O Foreman é um supervisor agnóstico e extensível. Manter parsing de testes de linguagens específicas e heurísticas de percepção regex fora do core evita inchaço de dependências e permite que o Foreman se concentre no ciclo de vida, live steering e delegação de checkpoints (ThruWire). A fundação de extensões do Foreman (PR #24) foi concebida exatamente para isso.

### P: Como o circuit breaker evita abortos falsos?
Um sinal isolado (como repetir um comando de teste ou um score semântico de estagnação) gera falso positivo com frequência quando o agente está em um ciclo legítimo de tentar corrigir um teste. O `ForemanCircuitBreaker` exige que **tanto** a saída normalizada (sem ruídos de tempo de execução) **quanto** o diff do Git permaneçam 100% idênticos ao longo de uma janela completa de 5 passos. Se o agente alterar qualquer linha de código, o diff muda e o breaker recusa o aborto.

### P: A leitura do diff do Git trava o event loop do asyncio no Foreman?
Não. O runner de diff possui timeout rígido de 5 segundos e política fail-open (retorna `null`, recusando a interrupção). Em contextos assíncronos, o processo é descarregado para threadpool (`asyncio.to_thread`), garantindo que o supervisor não sofra engasgos.

### P: É obrigatório ter chave de API da TypeSafe?
Não. O `jev-harness` é offline-first por padrão. Ele executa heurísticas locais determinísticas em menos de 500µs sem exigir credenciais. Caso uma chave seja fornecida, ele consulta o modelo neural System One ao vivo para casos ambíguos.

---

## 8. Verificação

```bash
python -m unittest tests.test_foreman_integration      # 37 testes (4 ignorados sem o Foreman)
cd packages/ts  && npm test                            # inclui 10 testes do Foreman
cd packages/rust && cargo test                         # inclui 8 testes do Foreman
python scripts/check_links.py --root .                 # verificação de links (parte da bateria)
```

Os três runtimes exportam bundles idênticos em bytes (verificado: TOML 1.952 B, companion class 11.598 B, README 2.813 B).
