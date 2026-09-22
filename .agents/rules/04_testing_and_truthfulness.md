# 🛡️ Testes Exaustivos, Verificação Adversarial e Honestidade Absoluta

> **Documento Oficial de Engenharia — Versão: v0.1.11**  
> *Diretrizes Inegociáveis de Qualidade para Agentes de IA.*

---

## 1. Postura Epistêmica: Nunca Confie Cegamente, Sempre Teste e Verifique

> [!IMPORTANT]
> **O lema do Jev Harness é:** *NUNCA CONFIE CEGAMENTE, SEMPRE TESTE E VERIFIQUE. SE ACHAR ALGO ESTRANHO, INVESTIGUE IMEDIATAMENTE ATÉ A RAIZ.*

Nenhum agente ou desenvolvedor tem permissão para:
1. Assumir que um código recém-escrito compila ou funciona sem rodar o compilador e os testes.
2. Considerar uma tarefa concluída com base em intuição ou raciocínio puramente teórico.
3. Mascarar erros de teste alterando asserções válidas para que fiquem fracas (enfraquecimento de teste).

---

## 2. Proibição de Testes Tautológicos (*Paper Tigers*)

Um **teste tautológico** é um teste que passa unicamente porque o mock local foi instruído a retornar uma resposta que satisfaz a asserção, sem testar a regra de negócio real.

### Regras Anti-Paper-Tiger:
* **Testes de Integração Real com Logs Brutos**: Os testes em [tests/test_real_tracebacks.py](file:///home/ismaelsoilet/jev-harness/tests/test_real_tracebacks.py) utilizam tracebacks reais e complexos extraídos de execuções de pytest, cargo, npm, go test e nodemon.
* **Precedência de Asserção Lógica sobre Nomes de Módulos**:
  Se um log de teste Jest contiver:
  ```text
  FAIL src/plugin.test.ts
    Expected: "READY"
    Received: "ModuleNotFoundError: No module named 'foo'"
  ```
  O `jev-harness` **DEVE** classificar isso como `deep_logic` (`skip_llm=false`). Um falso positivo que classificasse isso como `env_missing` porque encontrou a palavra `ModuleNotFoundError` no meio do diff cometeria um erro crítico, tentando rodar `pip install` e pulando o LLM.
* **Respeito à Negação**:
  Um plano que diz *"Do NOT abort, proceed with migration"* jamais pode acionar o abort gate apenas pela presença da palavra `abort`. A semântica não-autorregressiva do Jev deve respeitar a negação explícita.

---

## 3. Bateria Oficial Tri-Runtime (197 Testes)

O repositório mantém **197 testes exaustivos** com 100% de taxa de aprovação através dos três runtimes:

```bash
# Executa a bateria completa unificada:
./scripts/release.sh --check
```

### Distribuição dos Testes:
1. **Python (`tests/`)**: **107 testes**
   * `test_gates.py`: Testes unitários dos 6 gates semânticos.
   * `test_config.py`: Carregamento e honra do `.jev.json` (modelo, thresholds, clamp, arquivo corrompido) com isolamento de diretório de trabalho.
   * `test_adversarial.py`: Casos de concorrência com `fcntl.flock`, paridade de esquemas JSON, negação em português/inglês, truncamento UTF-8 com emojis de 4 bytes, domínio de palavras-chave arquiteturais sobre typos, telemetria de doom loop e dialeto limpo Anthropic.
   * `test_real_tracebacks.py`: Logs reais de Python, Go, Node.js, Rust e TypeScript.
   * `test_cli.py`: Códigos de saída (0, 1, 2), flags de modo `--mock`, `--json`, `--status`, prevenção de hang em stdin pipes e tratamento de SIGPIPE/BrokenPipeError.
   * `test_mcp.py`: Protocolo JSON-RPC 2.0 do MCP Server (`jev-mcp`).
2. **Rust (`packages/rust/tests/`)**: **47 testes**
   * Testes assíncronos Tokio cobrindo todos os gates semânticos, simulação local, decodificação JSON, compilação de dialetos de reasoning effort, servidor MCP stdio nativo (`mcp.rs`) e safeguards de modelos direct.
3. **TypeScript (`packages/ts/tests/`)**: **43 testes**
   * Testes nativos Node.js (`node --test`) cobrindo tipos, resolução de provedores (TypeSafe, OpenCode Zen, OpenRouter), gates, segurança de surrogate pairs UTF-16, detecção de edições não testadas no Nudge Gate e servidor MCP stdio nativo sem dependências externas.

---

## 4. Política de Honestidade Absoluta (*Outcome-First Reporting*)

Ao relatar resultados de auditoria, execução ou teste:
* **Relate o resultado no topo**: Diga imediatamente se os testes passaram, se falharam ou se há ressalvas.
* **Nunca esconda regressões**: Se uma alteração causou a quebra de um único teste dos 197, pare imediatamente, não faça commit e investigue a causa raiz.
* **Transparência em Modo Mock**: Sempre evidencie se uma resposta foi gerada via simulação heurística local (`is_mock=true`) ou via chamada real ao Jev System One.
