# 🔌 Padrões de Qualidade MCP e Diretrizes TDQS (Glama A+)

> **Documento Oficial de Engenharia — Versão: v0.2.0**  
> *Diretrizes Estritas para Definição de Ferramentas Model Context Protocol (MCP) e Conformidade com o Tool Definition Quality Score (TDQS).*

---

## 1. Visão Geral e Objetivo

Este padrão estabelece as regras obrigatórias para qualquer ferramenta MCP adicionada ou modificada no `jev-harness`. O objetivo é assegurar nota máxima (**5.0 / Grade A+**) nas avaliações do ecossistema Glama e eliminar falhas de seleção de ferramentas por modelos de IA (Claude, GPT, Gemini, DeepSeek, Qwen).

---

## 2. Nomenclatura Canônica Estrita (`verb_noun`)

Toda ferramenta MCP exposta no manifesto deve seguir estritamente o padrão `verb_noun`:

* **Formato Obrigatório:** `<namespace>_<verbo>_<substantivo>` (ex: `jev_triage_test_failure`, `jev_check_abort`, `jev_route_task`, `jev_verify_completion`, `jev_modulate_reasoning_effort`, `jev_evaluate_nudge`).
* **Proibições:**
  * Não inverter para `substantivo_verbo` (ex: proibido `jev_abort_check` como nome canônico).
  * Não usar prefixos interrogativos ou booleanos como `should_` (ex: proibido `jev_should_nudge_continuation` como nome canônico).
* **Retrocompatibilidade Obrigatória:**
  * Sempre que um nome for refinado, o dispatcher (`tools/call`) **DEVE** manter suporte aos nomes legados via alias transparente, garantindo que nenhum cliente existente seja quebrado.

---

## 3. Anotações Oficiais do Protocolo MCP (`annotations`)

Toda ferramenta registrada no `TOOLS_MANIFEST` **DEVE** incluir o bloco `annotations` conforme a especificação do Model Context Protocol:

```json
"annotations": {
  "readOnlyHint": true,      // true se a ferramenta apenas analisa/lê sem mutar o sistema
  "destructiveHint": false,   // true apenas se houver risco de deleção ou dano a dados
  "idempotentHint": true,     // true se mesmas entradas produzem as mesmas saídas
  "openWorldHint": false      // false para decisões locais ou herméticas; true para web/mundo aberto
}
```

O Glama pontua a dimensão **Behavioral Transparency** diretamente através deste bloco.

---

## 4. Estrutura Obrigatória da `description`

Cada ferramenta deve conter um texto de descrição estruturado com exatamente três seções:

1. **Propósito e Mecanismo:**
   * Frase inicial declarando a ação executada e o tempo de resposta/natureza determinística.
2. **Diretrizes de Uso (`Usage Guidelines`):**
   * `Use when:` Cenários específicos onde o agente **deve** invocar a ferramenta.
   * `Do NOT use when:` Cenários onde o agente **não deve** invocar a ferramenta e qual alternativa deve ser usada.
3. **Especificação de Retorno (`Output Contract`):**
   * `Returns:` Descrição do JSON retornado, listando as chaves primárias e seus tipos.

---

## 5. Tipagem e Restrições Formais no `inputSchema`

O JSON Schema de entrada não pode ser genérico:

* **Valores Enums:** Parâmetros com domínio finito de valores aceitos devem declarar explicitamente `"enum": [...]`.
* **Defaults Claros:** Parâmetros opcionais com valor padrão devem conter `"default": <valor>`.
* **Limites Numéricos:** Números inteiros ou floats devem conter `"minimum": <min>` e/ou `"maximum": <max>`.
* **Descrições de Parâmetros:** 100% dos parâmetros declarados em `properties` devem conter `description` autoexplicativa.

---

## 6. Paridade Tri-Runtime Obrigatória

Qualquer alteração ou inclusão no catálogo de ferramentas MCP deve ser refletida identicamente nos três runtimes:

1. **Python:** `src/jev_harness/mcp_server.py`
2. **TypeScript:** `packages/ts/src/mcp.ts`
3. **Rust:** `packages/rust/src/mcp.rs`

Nenhuma ferramenta pode ser publicada em um runtime sem suporte correspondente e testes nos outros dois.

---

## 7. Critérios de Avaliação TDQS (Coerência do Servidor)

| Dimensão | Meta | Requisito de Implementação |
| :--- | :---: | :--- |
| **Disambiguation** | 5/5 | Cada ferramenta tem um propósito único e sem sobreposição com suas irmãs. |
| **Naming Consistency** | 5/5 | 100% de consistência no padrão `verb_noun`. |
| **Tool Count** | 5/5 | Conjunto conciso e focado (faixa ideal de 3 a 15 ferramentas). |
| **Completeness** | 5/5 | Cobertura completa do ciclo de vida System 1.5 sem lacunas ou dead ends. |
