# Portal Societário Sigma

Portal interno da Sigma Contabilidade para gestão do departamento societário.
Desenvolvido em Flask, rodando na VPS em `societario.gsigma.com.br` (porta 5080).

---

## Stack

- Python 3.12
- Flask 3.1 + Werkzeug
- SQLite (banco local via portal.db)
- Jinja2 (templates HTML)
- WebAuthn / passkeys (webauthn 2.7)
- python-docx, python-pptx, reportlab (geração de documentos)
- pdfplumber (leitura de PDF)
- openai, anthropic (IA em módulos específicos)
- openpyxl (planilhas)
- python-dotenv (variáveis de ambiente)

---

## Entry point

```
python portal.py
```

Porta padrão: `5080` (configurável via variável de ambiente `PORT`).

---

## Estrutura de pastas

```
portal-sigma/
  portal.py                  # entry point principal
  app.py                     # entry point alternativo (manter sincronizado)
  database.py                # modelos e inicialização do banco
  security.py                # configurações de segurança e WebAuthn
  email_utils.py             # envio de email
  email_checker.py           # verificação de email recebido
  backup_sheets.py           # backup para Google Sheets
  requirements.txt

  blueprints/                # módulos Flask (um por funcionalidade)
    auth.py                  # autenticação e sessão
    admin.py                 # painel administrativo
    empresas.py              # cadastro de empresas
    conferencia.py           # conferência de contratos
    declaracoes.py           # declarações societárias
    procuracoes.py           # procurações
    informativos.py          # informativos
    manuais.py               # manuais internos
    newsletter.py            # newsletter
    processos.py             # processos societários
    movimentacao.py          # movimentação de sócios
    diario_oficial.py        # consulta ao diário oficial
    cnae.py                  # consulta de CNAE
    anotacoes.py             # anotações internas
    passkeys.py              # gerenciamento de passkeys
    webauthn_bp.py           # fluxo WebAuthn

  templates/                 # templates Jinja2 por módulo
  static/                    # assets estáticos
    modelos_procuracao/      # modelos DOCX de procuração
    templates/               # templates DOCX e formulários
    quill/                   # editor rich text
    sigma_logo.png

  scripts/
    atualizar_base_cnae_concla.py  # atualiza base CNAE local

  docs/                      # documentação técnica
    ESPECIFICACAO_TECNICA_CONFERENCIA_V2.md
    empresas_module.md
    integracoes/digisac/     # integração Digisac (planejada)
```

---

## Arquivos que nunca devem ser versionados

Os itens abaixo estão cobertos pelo `.gitignore` e nunca devem entrar em commit:

- `.env` — variáveis de ambiente com credenciais reais
- `portal.db` — banco de dados SQLite com dados reais de clientes
- `credentials/` — tokens OAuth e chaves de API
- `uploads/` — arquivos enviados por usuários
- `logs/` — logs operacionais
- `backups/` — backups gerados automaticamente
- `static/data/` — dados CNAE gerados (arquivo grande, regenerável)
- `backup_config.json` — estado operacional de backup (IDs de planilha, último backup)
- `*.xlsx`, `SNAPSHOT_*.xlsx` — planilhas e relatórios gerados

Ver `.env.example` para lista de variáveis necessárias.

---

## Ambientes

- **VPS (producao):** `/home/jacqueline-benedito/projetos/portal-sigma/`
  Servico: `portal-sigma.service` (systemd do usuario)
  URL: `https://societario.gsigma.com.br`

- **WSL/local (desenvolvimento):** `/home/jacqueline_benedito/claude/clientes/sigma/projetos/portal-sigma/`
  Git proprio nesta pasta. Fonte de verdade formal a ser definida.

---

## Fluxo de trabalho e deploy

O fluxo seguro de desenvolvimento e implantacao segue tres ambientes:

- WSL/local → origem de todos os commits
- GitHub privado (`https://github.com/Jacqueline-Societario/portal-sigma`) → ponte e historico oficial
- VPS → ambiente de producao; recebe apenas commits publicados no GitHub

Regra principal: nenhum codigo vai para a VPS sem ter passado pelo GitHub primeiro.

Documentacao completa:
- `DEPLOY.md` — procedimento oficial, fonte de verdade, fluxo de deploy, rollback, arquivos protegidos
- `CHECKLIST_DEPLOY.md` — checklist pratico antes, durante e apos cada deploy

---

## Status do repositorio

- Git proprio criado em `main` em 02/06/2026
- GitHub privado conectado em 03/06/2026: `https://github.com/Jacqueline-Societario/portal-sigma`
- Branch `main` sincronizada com `origin/main` (commit atual: `04e53bc`)
- Remote na VPS: ainda nao configurado — etapa planejada
- Deploy automatico: nao existe — ver DEPLOY.md
- Fonte de verdade: WSL para desenvolvimento, GitHub para historico, VPS para producao
