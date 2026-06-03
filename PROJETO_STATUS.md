# PROJETO_STATUS — Sigma / Portal Societário
**Última atualização**: 03/06/2026 | **Responsável**: Yuzu

## STATUS GERAL
Portal web Flask do Departamento Societário da Sigma Contabilidade. Rodando na VPS Sigma (societario.gsigma.com.br, porta 5080). **Novo layout implementado (07/04/2026 noite): sidebar branca, dashboard com saudação + cards, empresas com filter pills + grid de cards.**

## MÓDULOS / ETAPAS
- [x] **Módulo Elaboração de Contrato Social** — app.py intacto, servido em `/contrato/`, renomeado de "Robô de Alteração Contratual"
- [x] **Portal base** — portal.py (entry point), auth individual por usuária (SQLite), dashboard
- [x] **Módulo Procurações** — 20+ tipos, geração via Claude, download Word
- [x] **Módulo Declarações e Requerimentos** — 28+ tipos, geração via Claude, download Word
- [x] **Módulo Manuais/Conhecimentos** — CRUD completo, categorias, editor de texto
- [x] **Auth individual + 2FA por e-mail** — login, código 6 dígitos, verificar_otp, SQLite
- [x] **Email 2FA funcionando na VPS** — bug do token path corrigido (29/04/2026)
- [x] **Banco de dados** — portal.db (users + manuais), usuárias padrão criadas
- [x] **Deploy VPS Sigma** — CONCLUÍDO (societario.gsigma.com.br)
- [x] Traefik: rota `societario.gsigma.com.br` → portal.py (porta 5080)
- [x] Processo ativo na VPS (PID 2149274 — reiniciado 07/04/2026)
- [x] **Empresas: campo Fluxo removido** — badge + campo edição + coletarCampos
- [x] **Empresas: Nova Empresa** — botão + rota /empresas/nova + template + criar_empresa()
- [x] **Novo layout (Stitch design)** — sidebar branca, dashboard com saudação + cards, empresas com filter pills + grid (07/04/2026 noite)
- [x] **Busca ao vivo em Empresas** — debounce 400ms, busca conforme digita nome ou CNPJ (08/04/2026)
- [x] **Requerimento de Uso do Solo - Goiânia** — formulário dedicado em /declaracoes/, campos individuais por CNAE com escritório Sim/Não, gera DOCX padrão Prefeitura/SEPLAM (08/04/2026)
- [x] **Módulo Processos em Andamento** — webhook /webhook/forms/<token>, blueprint /processos/, 3 tabelas SQLite, UI com abas Ativos/Arquivados, 8 status, responsável, observações auditadas, PDF, paginação, deduplicação por response_id, sino de notificação (30/04/2026)
- [x] **Importação histórica** — 29 respostas importadas a partir de 01/09/2025 via Sheets API (16 Abertura + 13 Alteração)
- [x] **PDF estruturado (Processos)** — seções automáticas: Dados do Envio / Empresa / Sócios / Demais; nome de arquivo amigável com razão social (01/05/2026)
- [x] **Botão "Baixar PDF"** — substituiu "Acessar Formulário"; sempre habilitado, sem dependência de link Google Forms (01/05/2026)
- [x] **Fix Alteração Contratual** — subtítulo do card usa "Informe o nome da empresa..."; filtro Respostas: só e-mail + "Haverá alteração de..." (01/05/2026)
- [ ] **Integração direta Google Forms** — client_secret.json com OAuth client deletado (invalid_client). Pendente: recriar cliente OAuth no Google Cloud Console OU configurar polling via Sheets ⚠️
- [ ] **Editor Quill (Manuais/Informativos)** — CDN trocado para jsDelivr mas editor ainda NÃO aparece no browser ⚠️
- [ ] **Upload "Failed to fetch"** — fix de sessão aplicado mas problema persiste ⚠️
- [ ] **Módulo Consulta de Empresas** — Phase 2, integração Gestta

## ✅ O QUE FUNCIONOU
- Portal rodando na VPS (societario.gsigma.com.br, HTTP 200 confirmado)
- PID atualizado: 2149274 (reiniciado 07/04/2026 00:10 BRT)
- Empresas: campo "Fluxo" removido completamente (badge cabeçalho + campo editável + JS coletarCampos)
- Empresas: "+ Nova Empresa" funcionando — rota /empresas/nova + form completo + função criar_empresa() no database.py
- CDN Quill trocado para jsDelivr (mais confiável no Brasil)
- Emoji picker (80 emojis), botão HR separator, botão Anexar adicionados ao editor
- Deploy: SSH ControlMaster + base64 chunks (método estabelecido, 7 arquivos em ~3min)
- **Novo layout Stitch**: base.html sidebar branca + topbar com avatar; dashboard.html com saudação + busca + featured card + grid; empresas/index.html com filter pills + card grid — deployados e HTTP 200 confirmado
- Bug 500 diagnosticado e corrigido: `informativos.index` blueprint não existe na VPS → removido de base.html e dashboard.html

## ❌ O QUE DEU ERRADO / ATENÇÃO
- **"Failed to fetch" no upload de contrato**: AINDA PERSISTE após fix session.permanent=True — causa raiz ainda desconhecida. Hipóteses: (a) Traefik timeout para requests longas; (b) rota /upload no portal.py ainda aponta para lógica com sessão antiga; (c) app.py tem chave secreta diferente de portal.py
- **Editor Quill não aparece**: AINDA NÃO visível no browser mesmo com jsDelivr. Hipóteses: (a) jsDelivr também bloqueado na rede da Sigma; (b) erro JS silencioso na inicialização; (c) div #editor-manual tem height:0 por CSS
- Busca ao vivo via debounce `oninput` 400ms — submete o form GET existente sem precisar de AJAX (mantém filtros ativos)
- Requerimento Uso do Solo: CNAEs como array de `{codigo, escritorio}` enviados ao backend; tabela DOCX com 3 colunas (Código, Descrição, Escritório)
- SSH ControlMaster + base64 chunks é o método de deploy confiável (cat/scp/rsync via stdin travavam)
- Para rodar o portal: `python3 portal.py` (não app.py)
- SSH: `-p 22022 -i ~/.ssh/id_sigma_jacqueline jacqueline-benedito@129.121.54.101`
- ControlMaster: `-o ControlPath=/tmp/ssh-ctrl-sigma2 -o ControlMaster=auto -o ControlPersist=600`

## 📋 CHECKLIST TÉCNICO
- [x] Portal rodando na VPS (porta 5080, HTTP 200)
- [x] ANTHROPIC_API_KEY configurada no .env
- [x] Auth individual funcionando
- [x] Módulo contrato: app.py intacto, servido em /contrato/
- [x] Módulo procurações: /procuracoes/ → gera Word
- [x] Módulo declarações: /declaracoes/ → gera Word
- [x] Módulo manuais: /manuais/ → CRUD completo
- [x] Deploy VPS concluído
- [x] Processo ativo na VPS (PID 2149274)
- [x] Traefik rota societario.gsigma.com.br
- [x] SSL/HTTPS ativo (cert letsencrypt via Traefik)
- [ ] **Upload contrato sem "Failed to fetch"** ← PENDENTE ⚠️
- [ ] **Editor Quill visível no browser** ← PENDENTE ⚠️
- [ ] Teste de acesso por outra colaboradora

## INFRA VPS
- IP: `129.121.54.101` | Porta SSH: `22022`
- Usuário SSH: `jacqueline-benedito` | Chave: `~/.ssh/id_sigma_jacqueline`
- SSH ControlMaster: `ssh -o ControlMaster=auto -o ControlPath=/tmp/ssh-ctrl-sigma2 -o ControlPersist=600 -o ConnectTimeout=10 -p 22022 -i ~/.ssh/id_sigma_jacqueline jacqueline-benedito@129.121.54.101 "echo OK"`
- URL: `https://societario.gsigma.com.br` (Traefik → 172.17.0.1:5080)
- Processo: `/home/jacqueline-benedito/projetos/portal-sigma/.venv/bin/python3 portal.py` (PID 1935340 — reiniciado 29/04/2026 19:47 UTC)
- Logs: `~/logs/portal-sigma.log`
- **Deploy**: SSH ControlMaster + base64 chunks (ver sessão 06/04/2026)
- **Email 2FA**: token.json em `credentials/token.json` DENTRO da pasta do portal (não 3 níveis acima)
- **email_utils.py**: fallback inteligente — `BASE_DIR/credentials/token.json` primeiro, depois `../../../credentials/token.json`
- **NUNCA** usar `cat > arquivo` via SSH (zera se conexão cair) — usar chunks base64 ou python3 -c com escrita direta
- Restart: `pkill -f 'python.*portal.py'; sleep 1; cd ~/projetos/portal-sigma && nohup .venv/bin/python portal.py > ~/logs/portal-sigma.log 2>&1 &`

## CREDENCIAIS PORTAL
- societario1@gsigma.com.br / Sigma@2025 (admin — Jacqueline)
- societario2@gsigma.com.br / Sigma@2025 (Jaqueline Rodrigues)
- societario3@gsigma.com.br / Sigma@2025 (Beatriz)
- societario4@gsigma.com.br / Sigma@2025 (Jessica)

## TAREFAS PENDENTES
- [ ] **PENDENTE: Integração direta Google Forms** — recriar cliente OAuth no Google Cloud Console (habilitar Forms API + baixar novo client_secret.json) OU usar polling via Sheets (fornecer sheet_id de cada formulário)
- [ ] **URGENTE: Diagnosticar e corrigir "Failed to fetch" no upload de contrato** — investigar logs VPS, comparar chaves secretas portal.py x app.py, verificar timeout Traefik
- [ ] **URGENTE: Diagnosticar e corrigir editor Quill não aparece** — testar CDN no browser da Sigma, inspecionar console JS, verificar se div tem height > 0
- [ ] Testar acesso por outra colaboradora (societario2@gsigma.com.br)
- [ ] **Exibir campo `responsavel` na lista e detalhe de empresas no portal** (08/04/2026)
- [ ] Phase 2: Módulo Consulta de Empresas (integração Gestta nightly sync)
- [ ] Adicionar mais usuárias conforme necessário (editar database.py)

## ARQUIVOS DO PORTAL
```
portal.py           ← entry point (substituiu app.py como servidor)
database.py         ← SQLite: users, manuais, criar_empresa()
portal.db           ← banco criado automaticamente ao subir
blueprints/
  auth.py           ← login/logout individual
  contrato.py       ← serve /contrato/ com index.html original
  procuracoes.py    ← /procuracoes/ — geração Claude
  declaracoes.py    ← /declaracoes/ — geração Claude
  manuais.py        ← /manuais/ — CRUD manuais
  empresas.py       ← /empresas/ — consulta + nova empresa + editar
templates/
  base.html
  empresas/
    index.html      ← botão + Nova Empresa
    detalhe.html    ← sem campo Fluxo
    nova.html       ← form criação de empresa (NOVO 07/04/2026)
  manuais/form.html ← Quill jsDelivr + emoji + HR + anexar
  newsletter/form.html ← mesmo padrão
```

## HISTÓRICO DE SESSÕES
| Data | O que foi feito | Status |
|------|-----------------|--------|
| 25/03/2026 | Criação do sistema do zero — Flask, Claude API, Word/PDF, login, porta 5080 | ✅ |
| 26/03/2026 | 7 correções layout (Word/PDF), evento Nome Fantasia, fix tabela Word, deploy VPS tentado e bloqueado por senha expirada | ⚠️ |
| 26/03/2026 | Portal Societário completo: auth individual, dashboard, módulos Procurações + Declarações + Manuais, renomeação Contrato Social | ✅ |
| 06/04/2026 | Fix upload "Failed to fetch" (session.permanent=True + 12h lifetime), Quill.js Manuais+Informativos, remove badge fluxo empresas, deploy VPS | ✅ |
| 07/04/2026 | Empresas: remove campo Fluxo + Nova Empresa; Quill: jsDelivr + emoji + HR + anexar; deploy 7 arquivos — bugs Failed to fetch e Quill ainda persistem | ⚠️ |
| 07/04/2026 (noite) | Novo layout Stitch: sidebar branca, dashboard com saudação+cards, empresas com filter pills+grid; fix bug 500 informativos.index; deploy VPS OK | ✅ |
| 08/04/2026 | Banco VPS: coluna `responsavel` criada + 453/462 empresas com codigo_dominio (Gestta) + 224/462 com responsavel (carteiras Sheets) | ✅ |
| 08/04/2026 | Busca ao vivo /empresas/ (debounce 400ms) + Requerimento Uso do Solo Goiânia em /declaracoes/ (CNAEs individuais com escritório, DOCX padrão Prefeitura) | ✅ |
| 29/04/2026 | Fix crítico: email 2FA não chegava — token.json em caminho errado na VPS; corrigido email_utils.py (fallback); portal reiniciado PID 1935340 | ✅ |
| 30/04/2026 | Módulo Processos em Andamento: blueprint, 3 tabelas, UI, webhook, importação 29 respostas históricas. OAuth Forms falhou (client deletado) | ⚠️ |
| 03/06/2026 | Git/GitHub: SECRET_KEY adicionada ao .env VPS (sem exibir), permissões normalizadas (04e53bc), core.filemode=false, DEPLOY.md+CHECKLIST+README atualizados, commit bc64846 publicado no GitHub | ✅ |
