# 🚀 Protocolo de Release e Sincronização nos 4 Registries (Quad-Sync)

> **Documento Oficial de Engenharia — Versão: v0.1.6**  
> *Procedimento Obrigatório para Releases, Builds e Sincronização.*

---

## 1. O Desafio dos 4 Registries Independentes

O `jev-harness` é distribuído simultaneamente para três ecossistemas de linguagens, além do repositório de código fonte:
1. **GitHub** (Código-fonte e CI/CD): `https://github.com/ismaelsoilet/jev-harness`
2. **PyPI** (Python): `https://pypi.org/project/jev-harness/`
3. **npm** (TypeScript / JavaScript): `https://www.npmjs.com/package/@ismaelsoilet/jev-harness`
4. **Crates.io** (Rust): `https://crates.io/crates/jev-harness`

> [!WARNING]
> **Registries são imutáveis e independentes.** Um `git push` atualiza apenas o GitHub. Ele **NÃO** atualiza magicamente o PyPI, npm ou Crates.io sem a execução do pipeline de release correspondente.

---

## 2. Checklist Obrigatório de Release em 5 Passos

Toda nova versão, build ou correção que mereça lançamento deve seguir estritamente estes 5 passos sequenciais:

### Passo 1: Execução da Bateria Completa de 109 Testes
Antes de qualquer alteração de versão, todos os 109 testes devem passar nos 3 runtimes:
```bash
./scripts/release.sh --check
```
*Critério de parada: Se 1 teste falhar, o release está bloqueado.*

### Passo 2: Bump Síncrono de Versão nos Manifestos e Fontes
O script oficial atualiza simultaneamente todos os arquivos necessários:
```bash
./scripts/release.sh --bump <nova_versao>
# Exemplo:
./scripts/release.sh --bump 0.1.6
```

**Arquivos atualizados pelo bump síncrono:**
1. `pyproject.toml` (`project.version`)
2. `src/jev_harness/__init__.py` (`__version__`)
3. `src/jev_harness/client.py` (`DEFAULT_USER_AGENT`)
4. `packages/ts/package.json` (`version`)
5. `packages/ts/package-lock.json` (`version`)
6. `packages/ts/src/client.ts` (`DEFAULT_USER_AGENT`)
7. `packages/ts/src/cli.ts` (`getPackageVersion()`)
8. `packages/rust/Cargo.toml` (`package.version`)
9. `README.md` (exemplos de instalação e notas da release)
10. `packages/rust/README.md` (dependência Cargo e docs)
11. `scripts/release.sh` (exemplos e contadores de teste)

### Passo 3: Recompilação dos Artefatos de Distribuição
```bash
# 1. Compilar pacote TypeScript (gera pasta dist/)
cd packages/ts && npm run build && cd ../..

# 2. Compilar binário de release em Rust
cd packages/rust && cargo build --release && cd ../..
```

### Passo 4: Commit Detalhado e Criação da Git Tag
```bash
git add -A
git commit -m "chore: release v0.1.6 across all runtimes and docs"
git tag -a v0.1.6 -m "Release v0.1.6: Astra-Jev reasoning effort governance, expanded direct safeguards, and quad-registry sync"
git push origin main
git push origin v0.1.6
```

### Passo 5: Disparo de Publicação nos Registries e Verificação Quad-Sync
A tag `v*.*.*` aciona o workflow automatizado `.github/workflows/release.yml`, ou a publicação pode ser realizada via script:

```bash
# Publicação individual via script (quando com credenciais locais):
./scripts/release.sh --publish python  # Gera wheel/sdist e envia ao PyPI
./scripts/release.sh --publish npm     # Publica via npm com Sigstore OIDC
./scripts/release.sh --publish rust    # Executa cargo publish no crates.io
```

---

## 3. Matriz de Verificação de Sincronização (Como Validar os 4 Locais)

Após o disparo da release, o agente ou engenheiro deve inspecionar os 4 locais e confirmar que a mesma versão exata está ativa:

| Destino | Comando de Verificação no Terminal | URL Pública de Validação |
| :--- | :--- | :--- |
| **GitHub** | `git log -1 --oneline && git tag -l "v*"` | `https://github.com/ismaelsoilet/jev-harness/releases` |
| **PyPI** | `pip index versions jev-harness` (ou `curl -s https://pypi.org/pypi/jev-harness/json \| jq -r .info.version`) | `https://pypi.org/project/jev-harness/` |
| **npm** | `npm view @ismaelsoilet/jev-harness version` | `https://www.npmjs.com/package/@ismaelsoilet/jev-harness` |
| **Crates.io**| `cargo search jev-harness --limit 1` | `https://crates.io/crates/jev-harness` e `https://docs.rs/jev-harness` |

---

## 4. Segurança e Proveniência Criptográfica (npm Sigstore)

O pacote npm `@ismaelsoilet/jev-harness` é publicado utilizando **Trusted Publishing via OpenID Connect (OIDC)** com proveniência assinada criptograficamente pela Sigstore (`--provenance`).
* **Zero Tokens Estáticos**: Nenhum token permanente do npm fica exposto no GitHub Secrets.
* **Transparência Pública**: Qualquer desenvolvedor pode inspecionar o log de transparência público no Sigstore para verificar que o pacote publicado no npm foi construído estritamente a partir do commit correspondente no GitHub Actions.
