# Release v0.2.0 — System 1.5 Architecture, Provider Resilience & Tri-Runtime Parity

> **Data da pesquisa e calibração:** 23 de setembro de 2026  
> **Suíte de verificação:** 569 testes verdes (393 Python + 89 TypeScript + 87 Rust) · 100% paridade tri-runtime  

---

## 🌟 O que há de novo na v0.2.0

Esta versão consolida o `jev-harness` como a camada de decisão **System 1.5** para o ciclo de qualidade de agentes autônomos de código, elevando robustez, rastreabilidade e calibração empírica.

### 🦀 Paridade Rust Live & Quebra Semver Controlada (0.x)
- Correção no parser live de `Score`: suporte completo a floats (`f64`), mapas de legenda e probabilidades em respostas do provedor.
- Assinatura pública ajustada: `JevClient::retry_delay_ms(Option<f64>)` (suporte a frações em `Retry-After`) e retorno de erro explícito em `parse_api_response`.

### 🔁 Resiliência de Provedor & Degradação Fail-Open
- Política de retry com backoff exponencial suave e leitura rigorosa de headers `Retry-After` (429, 5xx e timeouts).
- Política padrão **fail-open** com marcação clara da causa de degradação (`degraded_reason`: `auth_401`, `http_429`, `http_500`, `timeout`, `connection`, `invalid_response`).
- Suporte a `--fail-closed` para pipelines rígidos e flag `--retries N`.
- Respostas malformadas HTTP 200 tratadas como falhas de primeira classe sem traces não tratados.

### 🛡️ Limites de Payload, Redação de Segredos & Detecção de Injeção
- Validação prévia de payload (128.000 code points para estado, 256.000 total) nos 3 runtimes.
- Redação automática de credenciais e tokens sensíveis em todos os campos de saída e requisições de rede.
- Detector determinístico de injeção em logs de teste não confiáveis, forçando escalonamento de julgamento (nunca `skip_llm=true`).

### 👻 Shadow Mode & Auditoria Completa
- Flag `--shadow` (ou `"shadow": true` em `.jev.json`): avalia e reporta `[SHADOW] would exit N` sem bloquear pipelines.
- Ferramenta de diagnóstico `jev-harness doctor` (inspeção de credenciais mascaradas, permissões de diretórios, hooks e limites).
- Trilha de auditoria append-only com `jev-harness receipts` (permissões restritas `0600`, TTL e hashes de integridade).
- Separação entre métricas medidas em tempo real e estimativas heurísticas no `jev-harness metrics`.
- Cache de decisão local baseado em hash de entrada com relatório de hit-rate (`--no-cache`).

### 📊 Calibração Empírica & Paridade 100% Travada
- Corpus com 160 casos rotulados (`tests/corpus`) e comando `replay` integrado para cálculo de acurácia, macro-F1 e ECE.
- Fixture de paridade tri-runtime (`tests/fixtures/corpus_parity.json`) garantindo decisões idênticas em Python, TypeScript e Rust.
- Exemplos prontos de GitHub Action (`examples/github-action/`) para triagem de CI em runners Linux, macOS e Windows.

---

## 📦 Comandos de Instalação nos 4 Canais

### 1. Python (PyPI)
```bash
pip install --upgrade jev-harness
```

### 2. TypeScript / JavaScript (npm)
```bash
npm install -g @ismaelsoilet/jev-harness
# ou executar via npx
npx @ismaelsoilet/jev-harness --help
```

### 3. Rust (Crates.io)
```bash
cargo install jev-harness
# ou como dependência em Cargo.toml:
# jev-harness = "0.2.0"
```

### 4. GitHub Releases & Standalone Binaries
Baixe os binários e códigos fontes diretamente da release oficial no GitHub:  
`https://github.com/ismaelsoilet/jev-harness/releases/tag/v0.2.0`
