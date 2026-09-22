# 🧠 Princípios Fundamentais de Engenharia de Software no Jev Harness

> **Documento Oficial de Engenharia — Versão: v0.1.6**  
> *Regras inegociáveis para agentes de IA e desenvolvedores.*

---

## 1. Princípios Karpathy para Agentes de Codificação

Baseados nas formulações de Andrej Karpathy para agentes autônomos, estes quatro princípios têm precedência sobre qualquer hábito genérico de geração de código.

### Princípio 1: Pense Antes de Codificar (*Think Before Coding*)
* **Regra**: Nunca assuma requisitos ambíguos silenciosamente. Exponha trade-offs e confirme antes de agir.
* **Prática**:
  - Declare suas premissas técnicas antes de alterar arquivos.
  - Se um pedido tiver múltiplas interpretações, apresente as opções de forma concisa.
  - Se uma solução mais simples for possível, proponha-a antes de implementar padrões desnecessários.

### Princípio 2: Simplicidade em Primeiro Lugar (*Simplicity First*)
* **Regra**: Entregue a quantidade mínima de código que resolva o problema atual com perfeição. Zero código especulativo.
* **Prática**:
  - Não crie abstrações prematuras (Strategy, Factory, camadas indesejadas) para um único caso de uso.
  - Não adicione funcionalidades extras não solicitadas (ex: cache ad-hoc, notificações, parâmetros decorativos).
  - Se a solução exigir 200 linhas, pause, revise e procure reduzi-la para a essência.
  - Bom código resolve o problema de hoje com elegância, não o problema hipotético de amanhã.

### Princípio 3: Alterações Cirúrgicas (*Surgical Changes*)
* **Regra**: Toque apenas no que for estritamente necessário. Limpe apenas a sua própria bagunça.
* **Prática**:
  - **Proibido** refatorar ou reformatar código adjacente fora do escopo da solicitação.
  - **Proibido** trocar aspas, mudar quebras de linha ou adicionar docstrings em funções não relacionadas.
  - **Obrigatório** mimetizar a indentação, convenções de tipagem e nomenclatura existentes no arquivo.
  - Todo byte modificado no diff deve ser diretamente justificável pelo objetivo do commit.

### Princípio 4: Execução Guiada por Metas (*Goal-Driven Execution*)
* **Regra**: Transforme pedidos em critérios de sucesso verificáveis e itere até cumpri-los.
* **Prática**:
  - Ao corrigir um bug: escreva um teste que reproduza a falha com precisão antes de tocar no código; aplique o patch; confirme que o teste agora passa e que a suíte existente não sofreu regressão.
  - Nunca declare uma tarefa como concluída sem executar o comando de teste ou verificação real.

---

## 2. Metodologia Fable: Verificação Adversarial e Honestidade

Inspirada no protocolo Fable de orquestração de agentes autônomos:

1. **Defina "Concluído" por Observação Direta**: O critério de conclusão não é "o código parece certo", mas a observação empírica da saída de um comando de validação (`cargo test`, `npm test`, `python3 -m unittest`).
2. **Postura Zero-Trust com o Próprio Trabalho**: Trate as alterações feitas como suspeitas. Audite o `git diff` antes de submeter. Pergunte-se: *"Onde essa implementação pode falhar silenciosamente?"*.
3. **Proibição de Falsas Alegações de Conclusão**: Nunca afirme que algo está funcionando sem ter a evidência de execução no terminal da sessão ativa. Se um teste falhou ou se há ressalvas técnicas, relate-as no topo do relatório (*Outcome-First*).

---

## 3. Paradigma Cognitivo Kahneman: Sistema 1 vs. Sistema 2

O `jev-harness` existe para sanar a maior ineficiência da engenharia agentic moderna: **usar raciocínio deliberativo caro (Sistema 2) para decisões mecânicas imediatas (Sistema 1)**.

| Dimensão | Jev System One (Fast / Intuitive) | Frontier LLM (Slow / Deliberative) |
| :--- | :--- | :--- |
| **Modelos** | TypeSafe Jev System One, OpenCode Zen, Heurística Local | GPT-6 Astra, Claude Fable 5.1 / Claude Opus 5, DeepSeek-V4-Pro |
| **Latência** | **< 500µs local / 70ms–150ms remote** | 10.000ms a 30.000ms |
| **Custo de Entrada** | **$0.042 / 1M tokens** (~238x mais barato) | $10.00 / 1M tokens |
| **Custo de Saída** | **$0.00 (Gratuito — não-autorregressivo)** | $50.00 / 1M tokens |
| **Natureza da Saída**| Decisão tipada estrita (Choice, Score, Noul) | Texto livre em streaming estocástico |
| **Função** | Triagem, aborto de loops, roteamento, modulação de reasoning | Resolução de bugs lógicos profundos e geração de código |

---

## 4. Filosofia Unix e Composição de Ferramentas

O `jev-harness` respeita estritamente os princípios Unix:

1. **Streams de Texto Padronizados**: Aceita entrada via `stdin` ou arquivos, permitindo pipes naturais:
   ```bash
   pytest | jev-harness test-gate
   npm test 2>&1 | npx @ismaelsoilet/jev-harness triage
   cargo test 2>&1 | jev test-gate
   ```
2. **Códigos de Saída Semânticos**:
   - `0`: Sucesso, verificação aprovada, ou `skip_llm=true` (ação determinística segura identificada).
   - `1`: Falha de teste que requer escalonamento ao LLM (`skip_llm=false`), ou recomendação de aborto (`should_abort=true`).
   - `2`: Erro de sintaxe, argumentos inválidos ou parâmetros incorretos no CLI.

---

## 5. Princípio Anti-Frankenstein: Por que NÃO Adotamos Proxies HTTP no Core

Durante a concepção do Astra-Jev, foi levantada a hipótese de colocar um servidor proxy HTTP reverso rodando em background dentro do `jev-harness` para interceptar chamadas da biblioteca `openai` ou `anthropic`.

Essa abordagem foi **veementemente rejeitada** pelos seguintes motivos arquiteturais:
* **Quebra de SSE (Server-Sent Events) e Streaming**: Proxies reversos intermediários frequentemente bufferizam chunks de streaming, destruindo a latência interativa de terminal.
* **Corrupção de Multi-Turn Tool Calling**: Modelos como DeepSeek V4.1 exigem a preservação estrita do campo `reasoning_content` entre chamadas consecutivas de ferramentas. Um proxy opaco que reescreve payloads no meio do caminho corrompe o histórico de chamadas.
* **Vazamento de Portas e Concorrência**: Rodar listeners HTTP em background gera colisões de portas em ambientes concorrentes de CI/CD e contêineres compartilhados.
* **Violação do Contrato de Zero Dependências**: Um proxy robusto exigiria bibliotecas pesadas de rede, violando a promessa de biblioteca padrão pura.

**Solução Adotada**: Compilador de dialetos estático e puro (`build_provider_params`) que retorna os parâmetros exatos para o agente injetar nativamente no seu próprio cliente LLM.
