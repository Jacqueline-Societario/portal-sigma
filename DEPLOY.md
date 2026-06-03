# Fluxo de Deploy — Portal Societário Sigma

Documento de referencia para atualizacao do portal em producao.

---

## Aviso importante: fluxo atual ainda nao automatizado

Nao existe pipeline de CI/CD nem deploy automatico configurado.
Todo deploy e feito manualmente, seguindo este fluxo.
Nao presumir automacao onde nao existe.

---

## Ambientes

| Ambiente  | Caminho                                                                 | Observacao               |
|-----------|-------------------------------------------------------------------------|--------------------------|
| WSL/local | `/home/jacqueline_benedito/claude/clientes/sigma/projetos/portal-sigma/` | Desenvolvimento e Git    |
| VPS       | `/home/jacqueline-benedito/projetos/portal-sigma/`                      | Producao (sempre ativo)  |

SSH VPS: `jacqueline-benedito@129.121.54.101 -p 22022`
Chave: `~/.ssh/id_sigma_jacqueline`

---

## Fluxo recomendado

### 1. Desenvolver no WSL/local

Alterar arquivos no WSL.
Testar localmente se possivel.
Nao alterar producao diretamente.

### 2. Commitar no Git proprio

```bash
cd /home/jacqueline_benedito/claude/clientes/sigma/projetos/portal-sigma/
git status
git add [arquivos alterados]
git commit -m "tipo: descricao clara da alteracao"
```

Usar commits atomicos: uma funcionalidade ou correcao por commit.

### 3. Transferir para VPS

Metodo atual: transferencia manual de arquivos via SSH.
Usar apenas arquivos versionados — nunca transferir `.env`, `portal.db`, `credentials/`, `uploads/`.

Metodo de transferencia validado (subprocess Python com base64):
```python
# Ver feedback_ssh_vps_transfer_method.md na memoria do assistente
# Chunks de 900 chars, decode na VPS, sem pipe|ssh ou process substitution
```

Futuramente: `git pull` direto na VPS apos configurar remote GitHub.

### 4. Aplicar na VPS

Antes de aplicar qualquer alteracao:
- Confirmar pasta correta na VPS
- Confirmar qual commit esta em producao
- Confirmar que o servico esta ativo

Aplicar apenas arquivos versionados.
Nao sobrescrever `.env`, `portal.db`, `credentials/` da VPS.

### 5. Reiniciar servico (somente se necessario)

```bash
systemctl --user restart portal-sigma.service
systemctl --user status portal-sigma.service
```

Reiniciar somente apos alteracoes em Python (blueprints, portal.py, database.py).
Alteracoes apenas em templates HTML ou assets estaticos nao exigem reinicio.

### 6. Verificar apos deploy

- Login funciona
- Dashboard carrega
- Modulo alterado funciona
- Sem erros no log (sem expor dados sensiveis)

### 7. Registrar commit implantado

Anotar qual commit foi implantado e quando.
Usar o arquivo de sessao ou o PROJETO_STATUS.md.

---

## Regras de seguranca

- Nunca versionar `.env`, `portal.db`, `credentials/`, `uploads/`, `static/data/`, `backup_config.json`
- Nunca editar producao diretamente sem registrar o que foi alterado
- Nunca sobrescrever o `.env` da VPS — ele tem credenciais de producao
- Nunca subir dados reais de clientes para repositorio
- Em caso de duvida: pausar, diagnosticar, perguntar antes de agir

---

## Rollback

Se algo der errado apos deploy:

1. Identificar o commit anterior estavel (`git log --oneline`)
2. Transferir os arquivos da versao anterior para a VPS
3. Reiniciar servico
4. Verificar funcionamento
5. Registrar o rollback

---

## Historico de commits implantados

| Data       | Commit  | Descricao resumida                       | Responsavel    |
|------------|---------|------------------------------------------|----------------|
| 02/06/2026 | e9fda46 | Commit inicial — Git proprio criado      | Jacqueline / Yuzu |
