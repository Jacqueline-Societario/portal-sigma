# Fluxo de Deploy — Portal Societário Sigma

Documento de referencia para atualizacao do portal em producao.

---

## Aviso importante: fluxo atual ainda nao automatizado

Nao existe pipeline de CI/CD nem deploy automatico configurado.
Todo deploy e feito manualmente, seguindo este fluxo.
Nao presumir automacao onde nao existe.

---

## Ambientes

- WSL/local: `/home/jacqueline_benedito/claude/clientes/sigma/projetos/portal-sigma/`
  Funcao: desenvolvimento e origem de todos os commits
- GitHub privado: `https://github.com/Jacqueline-Societario/portal-sigma`
  Funcao: repositorio remoto oficial, ponte entre WSL e VPS
- VPS: `/home/jacqueline-benedito/projetos/portal-sigma/`
  Funcao: producao (sempre ativo, porta 5080)

SSH VPS: `ssh jacqueline-benedito@129.121.54.101 -p 22022 -i ~/.ssh/id_sigma_jacqueline`

---

## Fonte de verdade

- **WSL** e a origem de desenvolvimento. Todo codigo novo nasce aqui.
- **GitHub** e a fonte de verdade remota oficial. Nenhum commit vai para a VPS sem antes passar pelo GitHub.
- **VPS** e o ambiente de producao. Recebe apenas commits ja publicados no GitHub.
- **Regra de emergencia**: se for inevitavel editar codigo direto na VPS, registrar o que foi alterado, qual arquivo, qual linha, e transferir a alteracao para o WSL na sessao seguinte.

---

## Alerta: historicos divergentes (estado em 03/06/2026)

A VPS tem um git local proprio com historico independente do WSL/GitHub.
Os dois historicos sao divergentes — nao compartilham commits.

Ao conectar o remote do GitHub na VPS sera necessario:
```bash
git fetch origin
git merge origin/main --allow-unrelated-histories
```
Ou alternativamente, substituir o historico local da VPS pelo do GitHub (mais limpo, exige planejamento).
Essa etapa e separada e exige checklist proprio antes de executar.

---

## Fluxo de desenvolvimento (WSL → GitHub)

### 1. Desenvolver no WSL

Alterar arquivos no WSL.
Testar localmente se possivel.
Nao alterar producao diretamente, salvo emergencia documentada.

### 2. Revisar antes de commitar

```bash
git status
git diff [arquivo]
```

Confirmar que nenhum arquivo sensivel esta no staging.

### 3. Commitar

```bash
git add [arquivos especificos — nunca git add .]
git commit -m "tipo: descricao clara"
```

Tipos de commit: `feat`, `fix`, `chore`, `docs`, `refactor`, `style`.
Usar commits atomicos: uma alteracao por commit.

### 4. Push para GitHub

```bash
git push origin main
```

Confirmar que o push foi concluido antes de qualquer deploy.

---

## Fluxo de deploy (GitHub → VPS)

### Etapa 1 — Pre-deploy (no WSL antes de conectar na VPS)

- Confirmar que o commit alvo ja esta no GitHub
- Identificar qual commit esta em producao na VPS
- Identificar quais arquivos Python foram alterados (determina se reinicio e necessario)
- Planejar rollback: saber qual commit anterior funciona

### Etapa 2 — Pre-deploy (na VPS)

```bash
# Confirmar pasta e servico
cd /home/jacqueline-benedito/projetos/portal-sigma/
systemctl --user status portal-sigma.service

# Confirmar espaco em disco
df -h ~

# Anotar commit atual em producao
git log --oneline -3
```

### Etapa 3 — Aplicar alteracoes

**Metodo atual (enquanto remote GitHub nao estiver conectado na VPS):**
Transferencia manual de arquivos via SSH com base64.
Usar apenas arquivos versionados.
Nunca transferir `.env`, `portal.db`, `credentials/`, `uploads/`.

**Metodo futuro (apos conectar remote na VPS):**
```bash
git fetch origin
git diff HEAD origin/main --name-only   # revisar o que vai mudar
git pull origin main
```

### Etapa 4 — Instalar dependencias (somente se requirements.txt mudou)

```bash
cd /home/jacqueline-benedito/projetos/portal-sigma/
pip install -r requirements.txt --quiet
```

### Etapa 5 — Reiniciar servico (somente se Python foi alterado)

```bash
systemctl --user restart portal-sigma.service
systemctl --user status portal-sigma.service
```

Reiniciar quando qualquer um dos itens abaixo for alterado:
- Arquivos Python: blueprints, portal.py, database.py, security.py
- Templates HTML (ver aviso abaixo)

**Atencao — templates .html (licao aprendida em 08/06/2026):**
Em producao com Flask `debug=False`, o Jinja2 mantem templates compilados em cache/memoria
enquanto o processo estiver rodando. Substituir o arquivo `.html` em disco nao e suficiente.
O servico precisa ser reiniciado para que o template corrigido seja carregado.

```bash
systemctl --user restart portal-sigma.service
systemctl --user is-active portal-sigma.service
curl -s -o /dev/null -w '%{http_code}' http://localhost:5080/login
```

Assets estaticos (CSS, JS, imagens em `static/`) nao exigem reinicio — sao servidos direto do disco.

### Etapa 6 — Testar apos deploy

- Login funciona com usuario e senha validos
- Recuperacao de senha funciona
- Dashboard principal carrega sem erro
- Modulo alterado se comporta conforme esperado
- Consulta CNAE funciona (se cnae.py foi alterado)
- Upload funciona (se procuracoes.py ou outros blueprints de upload foram alterados)
- Nenhum erro 500 no browser
- Servico estavel 30 segundos apos reinicio

### Etapa 7 — Registrar

Anotar em DEPLOY.md, secao "Historico de commits implantados":
- data do deploy
- hash do commit
- descricao resumida
- resultado

---

## Regras de seguranca

- Nunca versionar `.env`, `portal.db`, `credentials/`, `uploads/`, `static/data/`, `backup_config.json`, `logs/`, `backups/`, arquivos `.xlsx` gerados, tokens ou chaves
- Nunca usar `git add .` — sempre adicionar arquivos especificos
- Nunca sobrescrever o `.env` da VPS em deploy
- Nunca sobrescrever `portal.db`, `uploads/`, `credentials/` da VPS em deploy
- Nunca editar producao diretamente sem registrar
- Nunca subir dados reais de clientes para repositorio
- Em caso de duvida: pausar, diagnosticar, perguntar antes de agir

---

## Rollback

Se algo der errado apos deploy:

1. Identificar o commit anterior estavel: `git log --oneline`
2. Transferir os arquivos desse commit para a VPS (metodo base64 ou git checkout)
3. Reiniciar servico: `systemctl --user restart portal-sigma.service`
4. Testar login e dashboard
5. Registrar o rollback no historico abaixo
6. Nunca apagar `portal.db` ou `uploads/` para reverter codigo

---

## Historico de commits implantados

- 02/06/2026 | e9fda46 | Commit inicial — Git proprio criado | Jacqueline / Yuzu
- 03/06/2026 | 04e53bc | Normalizar permissoes de assets binarios | Yuzu (nao implantado na VPS ainda)
- 08/06/2026 | 4a55953 | fix: corrigir ids f_nome/f_cnpj em detalhe.html — campos Nome e CNPJ nao salvavam | Yuzu (implantado + restart servico)
