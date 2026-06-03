# 08 — Plano Futuro de Implantacao em Portal

Arquitetura e passos para implantar a integracao Digisac no portal-sigma,
quando a decisao for tomada. Nada implementado ainda.

---

## 1. Decisao de arquitetura

**Recomendacao:** modulo dentro do portal-sigma existente (nao projeto separado).

**Justificativa:**
- Portal ja tem infraestrutura: Flask, autenticacao, deploy na VPS, Git
- A integracao e somente leitura e complementar ao portal existente
- Separar em projeto independente exigiria nova porta, novo PM2, nova autenticacao
- Nao ha volume de requisicoes que justifique microsservico separado

**Excecao que justificaria separacao:**
- se houver recepcao de webhooks em alta frequencia
- se houver processamento assincrono de audio em fila (Celery/Redis)
- decisao futura, nao urgente

---

## 2. Variaveis de ambiente necessarias

Adicionar ao arquivo `.env` do portal:

```env
# Digisac API
DIGISAC_BASE_URL=https://gsigma.digisac.me/api/v1
DIGISAC_API_TOKEN=<token_gerado_na_interface>

# Seguranca de webhook (se implementado no futuro)
DIGISAC_WEBHOOK_SECRET=<string_aleatoria_forte>

# Comportamento
DIGISAC_REQUEST_TIMEOUT=10
DIGISAC_MAX_RETRIES=3
DIGISAC_DEFAULT_LIMIT=100
```

O `.env` ja esta no `.gitignore` do portal. Confirmar antes de adicionar.

---

## 3. Estrutura de arquivos sugerida

```
alteracao-contratual/
├── blueprints/
│   └── digisac.py          <- NOVO: rotas /digisac/*
│
├── lib/
│   ├── digisac_client.py   <- NOVO: wrapper da API (GET apenas)
│   ├── digisac_models.py   <- NOVO: dataclasses dos recursos
│   └── digisac_reports.py  <- NOVO: funcoes de relatorio e exportacao
│
├── templates/
│   └── digisac/
│       ├── index.html      <- NOVO: tela inicial da integracao
│       ├── chamados.html   <- NOVO: listagem de chamados
│       ├── chamado.html    <- NOVO: detalhe de um chamado
│       └── relatorio.html  <- NOVO: relatorio gerado
│
├── .env                    <- EXISTENTE: adicionar variaveis Digisac
└── app.py                  <- EXISTENTE: registrar novo blueprint
```

Nenhum arquivo existente sera sobrescrito. Apenas adicoes.

---

## 4. Modulo digisac_client.py

Responsabilidades:
- encapsular todas as chamadas HTTP a API Digisac
- nao expor token fora do modulo
- implementar retry com backoff
- implementar paginacao automatica
- retornar apenas dados necessarios (sem expor payload completo)

Interface publica minima:
```python
def listar_usuarios() -> list
def listar_departamentos() -> list
def listar_chamados(filtros: dict) -> dict  # com paginacao
def buscar_chamado(ticket_id: str) -> dict
def buscar_contato(contact_id: str) -> dict
def buscar_contatos(query: str) -> list
def listar_mensagens(ticket_id: str) -> list
def buscar_mensagem_com_arquivo(message_id: str) -> dict
```

---

## 5. Blueprint digisac.py

Rotas sugeridas (somente leitura):

```python
# Todas protegidas por autenticacao do portal
@digisac_bp.route("/digisac/")                     # index
@digisac_bp.route("/digisac/chamados")              # listagem com filtros
@digisac_bp.route("/digisac/chamados/<ticket_id>")  # detalhe
@digisac_bp.route("/digisac/relatorio")             # relatorio por periodo/agente
@digisac_bp.route("/digisac/exportar")              # exportar planilha
```

Nenhuma rota de escrita.

---

## 6. Autenticacao

Usar o mesmo mecanismo de autenticacao ja existente no portal-sigma.
Nao criar autenticacao paralela.
Verificar qual decorator de login esta sendo usado atualmente (ex: `@login_required`).

---

## 7. Logs seguros

```python
import logging

logger = logging.getLogger("digisac")

# OK
logger.info("GET /tickets user=%s total=%d", current_user.id, total)

# PROIBIDO
logger.debug("Response: %s", json.dumps(payload))  # expoe dados de clientes
logger.info("Token: %s", token)                    # expoe credencial
```

---

## 8. Registro do blueprint em app.py

Adicionar apenas estas linhas, sem alterar nada existente:

```python
# Digisac (integracao de leitura)
from blueprints.digisac import digisac_bp
app.register_blueprint(digisac_bp)
```

Antes de alterar app.py:
- Ler o arquivo completo
- Identificar onde outros blueprints sao registrados
- Adicionar no mesmo padrao
- Nao remover nenhum blueprint existente
- Testar que todas as rotas existentes continuam funcionando

---

## 9. Deploy na VPS

O portal ja esta deployado. Para adicionar o modulo Digisac:

1. Criar os arquivos localmente e commitar
2. Fazer deploy via base64+chunks (padrao do portal-sigma)
3. Adicionar variaveis ao `.env` da VPS
4. Reiniciar o processo Flask (PM2 ou systemd)
5. Testar rotas de leitura
6. Verificar logs

Nao abrir novas portas. Nao criar novo PM2. Usar o processo existente.

---

## 10. Testes antes de produção

```
[ ] Todas as rotas existentes do portal continuam funcionando
[ ] Rotas Digisac retornam dados corretos em leitura
[ ] Token nao aparece em logs
[ ] Nenhuma operacao de escrita acessivel
[ ] Autenticacao bloqueia acesso nao autenticado
[ ] Erro de API Digisac e tratado graciosamente (sem crash do portal)
[ ] Timeout configurado (10s padrao)
[ ] .env com variaveis Digisac sem commitar
```

---

## 11. Checklist final antes de producao

```
[ ] Blueprint registrado corretamente
[ ] Todas as rotas anteriores do portal testadas
[ ] Variaveis de ambiente na VPS (nao em codigo)
[ ] Logs sem dados sensiveis
[ ] Rate limiting ou pausa implementada
[ ] Operacoes de escrita inexistentes ou bloqueadas
[ ] Documentacao desta pasta atualizada
```
