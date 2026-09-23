# 📝 Convenções de Código e Padrões por Linguagem

> **Documento Oficial de Engenharia — Versão: v0.1.12**  
> *Guia de Estilo Estrito para Python, TypeScript, Rust e Git.*

---

## 1. Padrões Python (`src/jev_harness/`)

* **Versões Suportadas**: Python 3.9 até 3.13.
* **Dependências de Runtime**: **ESTRITAMENTE ZERO**. É proibido importar qualquer pacote que não faça parte da biblioteca padrão do Python (`urllib.request`, `json`, `re`, `dataclasses`, `time`, `os`, `sys`, `argparse`, `typing`).
* **Tipagem Estática**: Todas as funções públicas devem conter type hints completos (`Optional`, `Dict`, `List`, `Union`).
* **Resiliência de Rede**: Todas as chamadas de rede com `urllib.request` devem utilizar o helper de fallback IPv4 `_urlopen_with_ipv4_fallback` para evitar travamentos silenciosos em conexões instáveis ou com problemas de rota IPv6.
* **Testes Unitários**: Utilizar o framework padrão `unittest`. Nenhuma dependência de `pytest` pode ser exigida para executar a suíte em ambientes mínimos (`python3 -m unittest discover -v tests`).

---

## 2. Padrões TypeScript (`packages/ts/`)

* **Módulos**: **ES Modules (ESM)** puros (`"type": "module"` no `package.json`).
* **Imports Relativos**: Todos os imports locais devem incluir explicitamente a extensão `.js` (ex: `import { JevClient } from "./client.js";`), em conformidade estrita com a resolução ESM do Node.js e TypeScript `NodeNext`.
* **Zero Runtime Dependencies**: O `package.json` **não deve conter** a seção `dependencies`. Qualquer código de utilidade deve usar APIs nativas do Node (`node:fs`, `node:path`, `node:http`, `node:url`) ou JavaScript padrão.
* **Testes**: Suíte executada com o runner nativo do Node.js (`node --test dist-test/tests/*.js`). Zero dependências de frameworks pesados como Jest ou Vitest no runtime.

---

## 3. Padrões Rust (`packages/rust/`)

* **Edition**: Rust 2021 edition.
* **Tratamento de Erros**: Nunca use `.unwrap()` ou `.expect()` em código de produção ou bibliotecas públicas. Todas as funções expostas devem retornar `Result<T, JevError>`.
* **Segurança UTF-8**: Manipulações de substrings em tracebacks brutos ou logs devem respeitar limites de caracteres UTF-8 usando `s.is_char_boundary(idx)` (veja `safe_truncate_head_tail`), prevenindo panics ao truncar emojis ou caracteres multi-byte.
* **Async Runtime**: Baseado em `tokio` (features `full` ou `rt-multi-thread`, `macros`, `time`).
* **Clippy e Lints**: O código deve compilar limpo sem warnings com `cargo check` e `cargo clippy`.

---

## 4. Convenções Git e Higiene de Repositório

* **Repositório Sempre Organizado**:
  - Arquivos temporários, logs de debug (`*.log`), caches de teste (`__pycache__`, `target/`, `node_modules/`, `dist-test/`) devem estar estritamente no `.gitignore`.
  - Exemplos executáveis pertencem à pasta `examples/`.
  - Documentações e regras pertencem a `.agents/rules/` ou `README.md`.
* **Mensagens de Commit Semântico**:
  - `feat: <descrição>`: Adição de novas capacidades ou gates.
  - `fix: <descrição>`: Correção de bugs, classificações de regex ou lógicas de escape.
  - `chore: <descrição>`: Bumps de versão, atualizações de lockfiles e tarefas de manutenção.
  - `docs: <descrição>`: Atualizações e expansões de documentação.
  - `test: <descrição>`: Adição de novos casos de teste unitários ou adversariais.
