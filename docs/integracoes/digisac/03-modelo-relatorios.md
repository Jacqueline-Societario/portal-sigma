# 03 — Modelos de Relatorios Digisac

Relatorios que podem ser solicitados ao Claude em sessoes futuras.
Todos baseados em leitura da API. Nenhuma escrita envolvida.

---

## 1. Relatorio por Cliente / Contato

**Pergunta tipica:** "Quais chamados o cliente X teve nos ultimos 3 meses?"

**Dados necessarios:**
- ID ou nome do contato -> GET /contacts?search=nome
- Chamados do contato -> GET /tickets?contactId={id}
- Mensagens de cada chamado -> GET /messages?ticketId={id}

**Colunas sugeridas:**

| Coluna | Campo API |
|---|---|
| Protocolo | `ticket.protocol` |
| Data de inicio | `ticket.startedAt` |
| Data de encerramento | `ticket.endedAt` |
| Status | `ticket.isOpen` |
| Agente responsavel | `users.name` (via `ticket.userId`) |
| Departamento | `departments.name` (via `ticket.departmentId`) |
| Total de mensagens | contagem de `messages` |
| Audios com transcricao | contagem de `messages.type == audio` com `text != null` |
| Tempo de atendimento (min) | `ticket.metrics.ticketTime / 60` |

---

## 2. Relatorio por Agente

**Pergunta tipica:** "Quantos chamados a agente X atendeu em maio?"

**Dados necessarios:**
- ID do agente -> GET /users
- Chamados do agente -> GET /tickets?userId={id}&startedAt[gte]=data

**Colunas sugeridas:**

| Coluna | Campo API |
|---|---|
| Protocolo | `ticket.protocol` |
| Cliente | `contacts.name` (via `ticket.contactId`) |
| Data de inicio | `ticket.startedAt` |
| Data de encerramento | `ticket.endedAt` |
| Status | `ticket.isOpen` |
| Departamento | `departments.name` |
| Tempo de atendimento (min) | `ticket.metrics.ticketTime / 60` |
| Mensagens enviadas | count de `isFromMe == true` |
| Mensagens recebidas | count de `isFromMe == false` |

**Metricas agregadas:**
- Total de chamados
- Chamados encerrados vs abertos
- Tempo medio de atendimento
- Media de mensagens por chamado

---

## 3. Relatorio por Periodo

**Pergunta tipica:** "Quais chamados foram abertos em abril de 2026?"

**Dados necessarios:**
- GET /tickets?startedAt[gte]=2026-04-01&startedAt[lte]=2026-04-30

**Colunas sugeridas:**

| Coluna | Campo API |
|---|---|
| Protocolo | `ticket.protocol` |
| Data de inicio | `ticket.startedAt` |
| Status | `ticket.isOpen` |
| Cliente | `contacts.name` |
| Agente | `users.name` |
| Departamento | `departments.name` |
| Canal | `services.name` (via `ticket.serviceId`) |
| Tempo de atendimento (min) | `ticket.metrics.ticketTime / 60` |

---

## 4. Relatorio de Chamados Encerrados

**Pergunta tipica:** "Liste todos os chamados encerrados com tempo de atendimento."

**Dados necessarios:**
- GET /tickets?isOpen=false&limit=100&skip=0 (paginado)

**Metricas:**
- `ticket.metrics.ticketTime` -> tempo total (segundos)
- `ticket.metrics.messagingTime` -> tempo de troca de mensagens
- Tempo de resposta = startedAt ate primeira mensagem do agente

---

## 5. Relatorio de Chamados Abertos

**Pergunta tipica:** "Quais chamados estao abertos agora e para quem?"

**Dados necessarios:**
- GET /tickets?isOpen=true&limit=100

**Colunas sugeridas:**

| Coluna | Campo API |
|---|---|
| Protocolo | `ticket.protocol` |
| Cliente | `contacts.name` |
| Agente atual | `users.name` |
| Departamento | `departments.name` |
| Aberto em | `ticket.startedAt` |
| Tempo em aberto (horas) | calculado: agora - startedAt |

---

## 6. Relatorio de Tempo de Atendimento

**Pergunta tipica:** "Qual o tempo medio de atendimento por agente?"

**Calculo:**

```python
# tempo_total_segundos = ticket["metrics"]["ticketTime"]
# tempo_minutos = tempo_total_segundos / 60
# tempo_horas = tempo_total_segundos / 3600

import statistics

tempos = [t["metrics"]["ticketTime"] for t in chamados if t["metrics"]["ticketTime"]]
print(f"Media: {statistics.mean(tempos)/60:.1f} min")
print(f"Mediana: {statistics.median(tempos)/60:.1f} min")
print(f"Maximo: {max(tempos)/60:.1f} min")
```

---

## 7. Relatorio de Mensagens e Audios

**Pergunta tipica:** "Quantas mensagens de audio foram enviadas em maio com transcricao?"

**Dados necessarios:**
- GET /messages?type=audio&limit=100&skip=0 (paginado)
- Filtrar por ticketId se necessario

**Colunas sugeridas:**

| Coluna | Campo API |
|---|---|
| ID da mensagem | `message.id` |
| Chamado | `message.ticketId` |
| Cliente | `contacts.name` (via `message.contactId`) |
| Agente | `users.name` (via `message.ticketUserId`) |
| Data | `message.timestamp` |
| Direcao | `message.isFromMe` |
| Duracao (seg) | `file.data.audioMetadata.duration` |
| Transcricao | `message.text` |
| Transcrito | sim/nao |

---

## 8. Relatorio de Produtividade por Agente

**Pergunta tipica:** "Gere um relatorio de produtividade de toda a equipe de atendimento."

**Estrutura sugerida:**

| Agente | Chamados totais | Abertos | Encerrados | Tempo medio (min) | Mensagens enviadas | Audios respondidos |
|---|---|---|---|---|---|---|
| Nome A | 45 | 3 | 42 | 22 | 189 | 7 |
| Nome B | 31 | 1 | 30 | 18 | 143 | 12 |

**Como gerar:**
1. GET /users -> lista de agentes
2. Para cada agente: GET /tickets?userId={id}&limit=500
3. Para cada chamado: GET /messages?ticketId={id} (opcional, para contagem)
4. Agregar metricas e exportar

---

## 9. Como solicitar relatorios em sessoes futuras

Exemplos de pedidos:

```
"Gere um relatorio de todos os chamados encerrados em maio de 2026,
com protocolo, agente, cliente e tempo de atendimento em minutos."

"Liste todos os chamados do contato [nome] com data, status e agente."

"Qual foi o tempo medio de atendimento de cada agente em abril?"

"Gere um relatorio de todos os audios com transcricao do chamado [protocolo]."

"Quais chamados estao abertos ha mais de 24 horas?"
```
