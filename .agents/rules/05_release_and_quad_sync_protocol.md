# 🚀 Protocolo de Release e Sincronização nos 4 Registries (Quad-Sync)

> **Documento Oficial de Engenharia — Versão: v0.2.0**  
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

## 2. Checklist Obrigatório de Release em 6 Passos

Toda nova versão, build ou correção que mereça lançamento deve seguir estritamente estes 6 passos sequenciais:

### Passo 1: Execução da Bateria Completa de 626 Testes
Antes de qualquer alteração de versão, todos os 626 testes devem passar nos 3 runtimes:
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

### Passo 4: Verificação Rígida Pré-Push de Paridade Quad-Manifest
> [!CAUTION]
> **Bloqueio Obrigatório:** Nunca faça push antes de validar que os 4 manifestos estão em 100% de paridade.
```bash
./scripts/release.sh --verify-sync
```
O Git pre-push hook local (`.git/hooks/pre-push`) e a Action no GitHub (`ci.yml`) abortam automaticamente se qualquer versão divergir.

### Passo 5: Commit Detalhado e Criação da Git Tag
> [!IMPORTANT]
> **Proibição de Bumps Órfãos:** Nunca envie um commit de bump de versão para a `main` sem criar a respectiva tag `v<versao>`.
```bash
git add -A
git commit -m "chore: release v0.1.6 across all runtimes, docs, and manifests"
git tag -a v0.1.6 -m "Release v0.1.6: AGENTS Constitution, Modular Rules & 2026 Frontier Governance"
git push origin main
git push origin v0.1.6
```

### Passo 6: Criação, Higiene Editorial do Release e Monitoramento Ativo
1. **Criação do GitHub Release**:
   ```bash
   gh release create v0.1.6 --title "v0.1.6: AGENTS Constitution, Modular Rules & 2026 Frontier Governance" --notes-file <arquivo_notas>
   ```
2. **Higiene Editorial das Notas de Release**:
   - Proibido formatação descuidada (ex: espaços duplos antes e depois de crases de código).
   - Registrar expressamente a data da pesquisa de modelos de fronteira (ex: *Pesquisa web em 22 de setembro de 2026*).
   - Listar claramente comandos de instalação nos 4 ecossistemas.
3. **Acompanhamento Ativo dos Workflows**:
   - Monitore a execução do `.github/workflows/release.yml` até que todos os jobs concluam com sucesso (`gh run list --workflow=release.yml`).
   - Não finalize a tarefa antes de certificar que o GitHub exibe a release mais recente como "Latest" e os badges refletem a nova versão.

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
