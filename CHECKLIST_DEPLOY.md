# Checklist de Deploy — Portal Societário Sigma

Executar cada item antes, durante e apos qualquer atualizacao em producao.
Nao pular etapas. Em caso de duvida em qualquer item: pausar e verificar.
Procedimento completo em DEPLOY.md.

---

## ANTES DO DEPLOY — WSL/local

### Codigo e commits

- [ ] `git status` esta limpo (sem alteracoes nao commitadas)
- [ ] Commit criado com mensagem clara e semantica
- [ ] `git diff HEAD~1` revisado — confirmar o que realmente mudou
- [ ] Nenhum arquivo sensivel no commit (`.env`, `portal.db`, `credentials/`, `uploads/`, etc.)
- [ ] Push para GitHub concluido: `git push origin main`
- [ ] Commit alvo confirmado no GitHub antes de prosseguir

### Dependencias

- [ ] `requirements.txt` atualizado se novas bibliotecas foram adicionadas
- [ ] Versoes nao foram rebaixadas sem motivo

### Dados e credenciais

- [ ] `.env` nao foi alterado (se precisou alterar, registrar separadamente o que mudou)
- [ ] `portal.db` nao foi alterado
- [ ] `uploads/` nao foi alterado
- [ ] `credentials/` nao foi alterado
- [ ] `static/data/` nao foi alterado
- [ ] `backup_config.json` nao foi alterado

### Avaliacao de risco

- [ ] Identificado se `requirements.txt` mudou (instalar deps na VPS?)
- [ ] Identificado se arquivos Python foram alterados (reinicio necessario?)
- [ ] Alteracao em banco avaliada (mudanca de schema exige migracao?)
- [ ] Rollback planejado: qual commit anterior usar se der errado?

---

## NA VPS — durante o deploy

### Verificacao inicial

- [ ] Pasta correta: `/home/jacqueline-benedito/projetos/portal-sigma/`
- [ ] Commit atual em producao anotado: `git log --oneline -1`
- [ ] Servico ativo: `systemctl --user status portal-sigma.service`
- [ ] Espaco em disco: `df -h ~` (> 200 MB livres)

### Aplicacao (metodo atual: transferencia manual base64)

- [ ] Apenas arquivos versionados transferidos
- [ ] `.env` da VPS NAO foi sobrescrito
- [ ] `portal.db` da VPS NAO foi sobrescrito
- [ ] `uploads/` da VPS NAO foi sobrescrito
- [ ] `credentials/` da VPS NAO foi sobrescrito
- [ ] `static/data/` da VPS NAO foi sobrescrito

### Aplicacao (metodo futuro: git pull — apos remote configurado na VPS)

- [ ] `git fetch origin` executado
- [ ] `git diff HEAD origin/main --name-only` revisado antes de aplicar
- [ ] `git pull origin main` executado
- [ ] Confirmar que `.env`, `portal.db`, `uploads/`, `credentials/` nao foram alterados pelo pull

### Dependencias (somente se requirements.txt mudou)

- [ ] `pip install -r requirements.txt --quiet` executado na VPS

### Reinicio (somente se Python foi alterado)

- [ ] Reinicio necessario? Python alterado = sim / apenas HTML ou CSS = nao
- [ ] `systemctl --user restart portal-sigma.service`
- [ ] `systemctl --user status portal-sigma.service` mostra `active (running)`
- [ ] Aguardar 30 segundos e confirmar servico estavel

---

## APOS O DEPLOY — testes

- [ ] Login funciona com usuario e senha validos
- [ ] Recuperacao de senha funciona
- [ ] Dashboard principal carrega sem erro
- [ ] Modulo alterado funciona conforme esperado
- [ ] Consulta CNAE funciona (se cnae.py foi alterado)
- [ ] Upload funciona (se blueprint de upload foi alterado)
- [ ] Sem erros 500 no browser
- [ ] `journalctl --user -u portal-sigma.service -n 20 --no-pager` sem erros criticos

---

## REGISTRO

- [ ] Commit implantado anotado em DEPLOY.md (hash + data + resultado)
- [ ] Sessao documentada se houver alteracao estrutural

---

## SE HOUVE FALHA — rollback

- [ ] Identificar commit anterior funcional: `git log --oneline`
- [ ] Transferir arquivos da versao anterior para VPS
- [ ] Reiniciar servico: `systemctl --user restart portal-sigma.service`
- [ ] Testar login e dashboard
- [ ] Registrar rollback em DEPLOY.md
- [ ] Nao apagar `portal.db` ou `uploads/` para reverter codigo

---

## Referencia rapida

```bash
# Status do servico
systemctl --user status portal-sigma.service

# Reiniciar
systemctl --user restart portal-sigma.service

# Log recente (sem expor dados de clientes)
journalctl --user -u portal-sigma.service -n 20 --no-pager

# Commit atual na VPS
git -C /home/jacqueline-benedito/projetos/portal-sigma log --oneline -3
```

SSH VPS: `ssh jacqueline-benedito@129.121.54.101 -p 22022 -i ~/.ssh/id_sigma_jacqueline`
Pasta VPS: `/home/jacqueline-benedito/projetos/portal-sigma/`
Procedimento completo: DEPLOY.md
