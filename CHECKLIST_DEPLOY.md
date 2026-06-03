# Checklist de Deploy — Portal Societário Sigma

Executar cada item antes, durante e apos qualquer atualizacao em producao.
Nao pular etapas. Em caso de duvida em qualquer item: pausar e verificar.

---

## ANTES DO DEPLOY (no WSL/local)

### Repositorio

- [ ] `git status` esta limpo no WSL (sem alteracoes nao commitadas)
- [ ] Commit criado com mensagem clara e descritiva
- [ ] Arquivos alterados revisados (diff confirmado)
- [ ] Apenas arquivos versionaveis no commit (nenhum sensivel)

### Dependencias

- [ ] `requirements.txt` foi atualizado se novas bibliotecas foram adicionadas
- [ ] Versoes das dependencias nao foram rebaixadas sem motivo

### Dados e credenciais

- [ ] `.env` nao foi alterado (se precisou alterar, registrar o que mudou)
- [ ] `portal.db` nao foi alterado
- [ ] `uploads/` nao foi alterado
- [ ] `credentials/` nao foi alterado
- [ ] `static/data/` nao foi alterado (regenerar na VPS se necessario)
- [ ] `backup_config.json` nao foi alterado

### Risco e impacto

- [ ] Alteracao em banco avaliada (mudanca de schema exige migracao?)
- [ ] Modulos afetados identificados
- [ ] Rollback planejado (qual commit reverter se der errado?)

---

## NA VPS (durante o deploy)

### Verificacao inicial

- [ ] Pasta correta confirmada: `/home/jacqueline-benedito/projetos/portal-sigma/`
- [ ] Commit/versao atual em producao anotado
- [ ] Servico esta ativo antes de comecar: `systemctl --user status portal-sigma.service`
- [ ] Espaco em disco verificado (> 200 MB livres)

### Aplicacao

- [ ] Apenas arquivos versionados foram transferidos
- [ ] `.env` da VPS NAO foi sobrescrito
- [ ] `portal.db` da VPS NAO foi sobrescrito
- [ ] `uploads/` da VPS NAO foi sobrescrito
- [ ] `credentials/` da VPS NAO foi sobrescrito
- [ ] `static/data/` da VPS NAO foi sobrescrito (regenerar se necessario)

### Reinicio (somente se necessario)

- [ ] Reinicio necessario? (Python alterado = sim / so HTML/CSS = nao)
- [ ] `systemctl --user restart portal-sigma.service`
- [ ] Servico voltou: `systemctl --user status portal-sigma.service`

### Verificacao pos-reinicio

- [ ] Login funciona (usuario e senha corretos)
- [ ] Recuperacao de senha funciona
- [ ] Dashboard principal carrega
- [ ] Modulo alterado funciona conforme esperado
- [ ] Sem erros 500 no browser
- [ ] Sem crash do servico nos primeiros 30 segundos

---

## APOS O DEPLOY

### Registro

- [ ] Commit implantado anotado (hash + data) em DEPLOY.md
- [ ] Resultado registrado (sucesso / falha / rollback)
- [ ] Sessao de deploy documentada se houver alteracao estrutural

### Se houve falha

- [ ] Servico restaurado com versao anterior
- [ ] Rollback registrado
- [ ] Causa identificada antes de nova tentativa

---

## Referencia rapida

```bash
# Status do servico
systemctl --user status portal-sigma.service

# Reiniciar
systemctl --user restart portal-sigma.service

# Ultimas linhas de log (sem expor dados de clientes)
journalctl --user -u portal-sigma.service -n 20 --no-pager
```

SSH VPS: `ssh jacqueline-benedito@129.121.54.101 -p 22022 -i ~/.ssh/id_sigma_jacqueline`
Pasta VPS: `/home/jacqueline-benedito/projetos/portal-sigma/`
