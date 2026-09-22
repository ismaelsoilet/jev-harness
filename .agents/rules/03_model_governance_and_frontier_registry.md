# 🌐 Governança Estrita de Modelos de IA e Registro de Fronteira (2026)

> **Documento Oficial de Engenharia — Versão: v0.1.11**  
> *Regra Mandatória de Pesquisa e Atualização para Agentes de IA.*

---

## 1. Regra Fundamental: Proibição de Modelos Obsoletos e Pesquisa Obrigatória

> [!CAUTION]
> **REGRA ZERO:** É terminantemente proibido a qualquer agente citar modelos obsoletos ou descontinuados (ex: GPT-3.5, GPT-4, Gemini 1.0/1.5, Claude 2/3.0) como modelos ativos de ponta em documentações, exemplos, testes ou raciocínios arquiteturais.

### Diretriz de Pesquisa Atualizada e Carimbo de Data Obrigatório:
1. **Não confie apenas no conhecimento pré-treinado estático**: O ecossistema de modelos de fronteira evolui em ritmo diário.
2. **Pesquisa Web Obrigatória com Data Registrada**: Antes de tomar decisões arquiteturais sobre modelos ou adicioná-los à documentação, o agente **DEVE** utilizar ferramentas de busca (`search_web`) para obter as especificações e datas oficiais mais recentes dos provedores. É mandatório registrar a data da pesquisa (ex: *Data da pesquisa: 22 de setembro de 2026*).
3. **Proibição Estrita de Projeções Não Lançadas**: É expressamente proibido listar versões especulativas ou futuras não confirmadas comercialmente como se estivessem ativas (ex: Claude Opus 5.2 ou 5.5 ainda não foram lançados; o modelo oficial mais recente da linha Opus é o **Claude Opus 5**, lançado em julho de 2026).
4. **Se encontrar algo estranho, verifique**: Se a documentação interna ou código fizer menção a modelos que pareçam desatualizados ou incoerentes em relação ao mercado, audite, faça pesquisa web, refatore e alinhe com os fatos 100% comprovados.

---

## 2. Catálogo Oficial de Modelos de Fronteira (Verificado via Pesquisa Web em 22 de setembro de 2026)

| Família / Provedor | Modelos Oficiais de Fronteira (2026) | Dialeto Exato do Astra-Jev | Comportamento de Raciocínio |
| :--- | :--- | :--- | :--- |
| **OpenAI / Codex** | `gpt-6-astra`, `o3-mini`, `codex` | `{"reasoning_effort": "low"\|"medium"\|"high"}` | Parâmetro de nível raiz no payload. Não altera array de `messages`, preservando 100% do Prompt Cache (KV Cache). |
| **Anthropic** | `claude-fable-5.1` (01/09/2026), `claude-opus-5` (24/07/2026) | `{"thinking": {"type": "adaptive"}, "output_config": {"effort": "low"\|"medium"\|"max"}}` | Suporte nativo ao Adaptive Thinking. *Nota: Claude Opus 5 é o modelo topo de linha oficial; Opus 5.2/5.5 ainda não foram lançados e não devem constar como ativos.* |
| **Google Gemini** | `gemini-3.8-flash-thinking`, `gemini-3.5-pro` | `{"thinking_config": {"thinking_level": "minimal"\|"medium"\|"high"}}` | Nível fino de pensamento ajustado no payload de configuração. |
| **DeepSeek AI** | `deepseek-v4.1-flash`, `deepseek-v4-pro`, `r1` | `{"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"\|"high"}` | Obrigatório preservar `reasoning_content` em sessões multi-turn de tool calling para evitar corrupção de estado. |
| **Alibaba (DashScope)** | `qwen-3.8-max` (2.4T MoE), `qwen-3.8-omni-flash` | `{"enable_thinking": false}` / `{"enable_thinking": true, "thinking_budget": 4096\|16384}` | No cliente OpenAI wrapper, envolver em `extra_body`. Desativa CoT em passos mecânicos para cortar latência de ~240s para 1.5s. |
| **Moonshot AI** | `kimi-k3` | `{"extra_body": {"thinking": false}}` / `{"reasoning_effort": "low"\|"high"}` | Modo instantâneo sem CoT para geração imediata com latência zero de raciocínio. |
| **Xiaomi** | `mimo-v2.6-pro`, `mimo-v2-flash` | `{"thinking": {"type": "disabled"}}` / `{"thinking": {"type": "enabled"}, "reasoning": {"effort": ...}}` | Desativa scratchpad em comandos mecânicos, liberando inferência de GPU. |

---

## 3. Blindagem de Modelos Single-Pass Direct (Prevenção de HTTP 400)

Modelos sem motor interno de Chain-of-Thought (ou modelos legados como `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, `gemini-2.0-flash`, `claude-3-5-haiku`, `qwen-2.5-coder`, `llama-3.3`) retornam erro fatal **HTTP 400 Bad Request** caso parâmetros como `reasoning_effort` ou `thinking` sejam injetados em seus payloads.

O `jev-harness` implementa um safeguard automático:
```python
# Se o modelo for identificado como direct single-pass:
res = modulate_reasoning_effort("git status", provider="openai", model="gpt-4o")
# res.is_reasoning_supported -> False
# res.provider_params -> {}  (Payload limpo e vazio, 0 risco de HTTP 400!)
# res.rationale -> "Model 'gpt-4o' is a direct single-pass model without internal reasoning CoT. Do NOT inject reasoning parameters."
```

---

## 4. Governança do Prompt Cache (KV Cache) e Histerese em Contextos Longos

O Astra-Codex de Vechen ([@miu21590](https://x.com/miu21590)) provou que é possível modular o esforço de raciocínio sem quebrar o cache de prefixo da OpenAI, desde que o histórico de mensagens não seja alterado.

Contudo, para sessões longas com mais de 30.000 tokens ativos, oscilar o esforço a cada turno consecutivo pode degradar a estabilidade da inferência. O `jev-harness` introduz a regra de **Histerese de Contexto**:
1. **Passos Mecânicos Puros**: Se a ação for um comando determinístico de terminal (`git status`, `npm install`, `pytest`), priorize o gate `triage_test_failure` com `skip_llm=true` — resolva no shell sem chamar o LLM!
2. **Contextos > 30.000 Tokens**: O `jev-harness` emite o alerta:
   `HIGH CACHE RISK (45000 tokens active): Modulating reasoning effort across turns may invalidate prefix KV cache. Hysteresis recommended: preserve stable reasoning effort across active sub-steps.`
