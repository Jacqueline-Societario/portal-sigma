# 04 — Modelo de Planilhas Digisac

Estruturas de planilhas para exportacao de dados da API Digisac.
Geradas com openpyxl ou pandas. Nenhuma escrita na API.

---

## 1. Planilha de Chamados

**Aba:** Chamados
**Fonte:** GET /tickets (paginado)

| Coluna | Campo API | Tipo | Exemplo |
|---|---|---|---|
| Protocolo | `protocol` | texto | 2026041516 |
| Status | `isOpen` | booleano | Aberto / Encerrado |
| Origem | `origin` | texto | automatic / manual |
| Data Inicio | `startedAt` | datetime | 2026-04-15 18:20 |
| Data Encerramento | `endedAt` | datetime | 2026-04-17 13:23 |
| Tempo Total (min) | `metrics.ticketTime / 60` | numero | 2583 |
| Tempo Mensagens (min) | `metrics.messagingTime / 60` | numero | 1516 |
| ID Chamado | `id` | uuid | — |
| ID Contato | `contactId` | uuid | — |
| ID Agente | `userId` | uuid | — |
| ID Departamento | `departmentId` | uuid | — |

**Recomendacao:** complementar com lookup de nomes (ver aba Agentes e aba Contatos).

---

## 2. Planilha de Contatos / Clientes

**Aba:** Contatos
**Fonte:** GET /contacts (paginado)

| Coluna | Campo API | Tipo | Exemplo |
|---|---|---|---|
| ID | `id` | uuid | — |
| Nome | `name` | texto | Joao da Silva |
| Nome interno | `internalName` | texto | — |
| Numero WhatsApp | `idFromService` | texto | 5562999990000 |
| Status | `status` | texto | — |
| Criado em | `createdAt` | datetime | — |
| Ultimo contato | `lastContactMessageAt` | datetime | — |
| Chamado atual | `currentTicketId` | uuid | — |

---

## 3. Planilha de Usuarios / Agentes

**Aba:** Agentes
**Fonte:** GET /users

| Coluna | Campo API | Tipo | Exemplo |
|---|---|---|---|
| ID | `id` | uuid | — |
| Nome | `name` | texto | Maria Fernanda |
| Email | `email` | texto | maria@sigma.com |
| Telefone | `phoneNumber` | texto | — |
| Status | `status` | texto | — |
| Ativo no chat interno | `isActiveInternalChat` | booleano | — |
| Criado em | `createdAt` | datetime | — |

---

## 4. Planilha de Mensagens

**Aba:** Mensagens
**Fonte:** GET /messages?ticketId={id}

| Coluna | Campo API | Tipo | Exemplo |
|---|---|---|---|
| ID Mensagem | `id` | uuid | — |
| Protocolo Chamado | via tickets | texto | 2026041516 |
| ID Chamado | `ticketId` | uuid | — |
| Tipo | `type` | texto | chat / audio / ticket |
| Direcao | `isFromMe` | booleano | Enviado / Recebido |
| Data/Hora | `timestamp` | datetime | 2026-05-06 16:53 |
| Texto | `text` | texto | — |
| E bot? | `isFromBot` | booleano | — |
| E comentario interno? | `isComment` | booleano | — |
| ID Contato | `contactId` | uuid | — |
| ID Agente | `userId` | uuid | — |

---

## 5. Planilha de Audios

**Aba:** Audios
**Fonte:** GET /messages?type=audio&include=file

| Coluna | Campo API | Tipo | Exemplo |
|---|---|---|---|
| ID Mensagem | `id` | uuid | — |
| ID Chamado | `ticketId` | uuid | — |
| Protocolo | via tickets | texto | — |
| Data/Hora | `timestamp` | datetime | — |
| Direcao | `isFromMe` | booleano | Enviado / Recebido |
| Duracao (seg) | `file.data.audioMetadata.duration` | inteiro | 35 |
| Bitrate | `file.data.audioMetadata.bitRate` | inteiro | 64 |
| Formato | `file.extension` | texto | mp3 |
| Transcricao | `text` | texto | — |
| Tem transcricao | campo calculado | booleano | Sim / Nao |
| Erro transcricao | `transcribeError` | texto | — |
| ID Contato | `contactId` | uuid | — |
| ID Agente | `ticketUserId` | uuid | — |

---

## 6. Planilha de Metricas Consolidadas

**Aba:** Metricas
Agregacao por agente e/ou periodo.

| Coluna | Calculo | Tipo |
|---|---|---|
| Agente | `users.name` | texto |
| Periodo | mes/ano selecionado | texto |
| Total Chamados | count tickets | inteiro |
| Chamados Encerrados | count isOpen=false | inteiro |
| Chamados Abertos | count isOpen=true | inteiro |
| Tempo Medio Atendimento (min) | mean(ticketTime/60) | decimal |
| Tempo Total Atendimento (h) | sum(ticketTime/3600) | decimal |
| Total Mensagens | sum de mensagens | inteiro |
| Mensagens Enviadas | count isFromMe=true | inteiro |
| Mensagens Recebidas | count isFromMe=false | inteiro |
| Total Audios | count type=audio | inteiro |
| Audios Transcritos | count text!=null | inteiro |

---

## 7. Codigo base para exportar planilha

```python
import openpyxl
import requests
from datetime import datetime

BASE = "https://gsigma.digisac.me/api/v1"
HEADERS = {"Authorization": f"Bearer {DIGISAC_API_TOKEN}"}

def buscar_todos(endpoint, params=None):
    """Pagina automaticamente e retorna todos os registros."""
    todos = []
    skip = 0
    limit = 100
    p = {**(params or {}), "limit": limit, "skip": skip}

    while True:
        p["skip"] = skip
        resp = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, params=p)
        dados = resp.json()
        todos.extend(dados["data"])
        if len(todos) >= dados["total"]:
            break
        skip += limit

    return todos

def exportar_chamados_xlsx(caminho_saida, filtros=None):
    chamados = buscar_todos("tickets", filtros)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chamados"

    cabecalho = [
        "Protocolo", "Status", "Data Inicio", "Data Encerramento",
        "Tempo Total (min)", "ID Agente", "ID Contato", "ID Departamento"
    ]
    ws.append(cabecalho)

    for t in chamados:
        ws.append([
            t.get("protocol"),
            "Aberto" if t.get("isOpen") else "Encerrado",
            t.get("startedAt"),
            t.get("endedAt"),
            round(t.get("metrics", {}).get("ticketTime", 0) / 60, 1),
            t.get("userId"),
            t.get("contactId"),
            t.get("departmentId"),
        ])

    wb.save(caminho_saida)
    print(f"Exportado: {caminho_saida} ({len(chamados)} registros)")
```

---

## 8. Destino dos arquivos exportados

Salvar em:
```
~/claude/clientes/sigma/projetos/alteracao-contratual/exports/digisac/
```

Nunca salvar em `/tmp/` como destino final.
Nomear com data: `chamados_2026_05.xlsx`, `audios_2026_05.xlsx`.
