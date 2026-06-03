# 01 — Mapa Tecnico da API Digisac

**Status:** Confirmado por testes em 23/05/2026
**Base URL:** `https://gsigma.digisac.me/api/v1`
**Autenticacao:** Bearer Token

---

## 1. Autenticacao

Todas as requisicoes exigem o header:

```
Authorization: Bearer {DIGISAC_API_TOKEN}
Content-Type: application/json
```

O token e gerado por usuario na interface do Digisac:
Menu do usuario > Configuracoes > Token de Acesso Pessoal.

- O token e unico por usuario.
- Nao expira automaticamente (ate ser revogado manualmente).
- Nao salvar em codigo versionado. Usar variavel de ambiente DIGISAC_API_TOKEN.
- Status confirmado: GET /me retorna 200 com token valido.

---

## 2. Paginacao

Todos os endpoints de listagem retornam a mesma estrutura:

```json
{
  "data": [...],
  "total": 2515,
  "limit": 15,
  "skip": 0,
  "currentPage": 1,
  "lastPage": 168,
  "from": 0,
  "to": 15
}
```

**Parametros de controle:**

| Parametro | Tipo | Descricao |
|---|---|---|
| `limit` | inteiro | Quantidade de registros por pagina |
| `skip` | inteiro | Quantos registros pular (offset) |

**Limite padrao:** 15 registros quando nao especificado.
**Recomendacao:** sempre usar `limit` e `skip` explicitamente.

---

## 3. Endpoints Confirmados

### 3.1 Autenticacao e usuario logado

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/me` | Dados do usuario autenticado | CONFIRMADO |

**Campos retornados por /me:**
`id`, `name`, `email`, `phoneNumber`, `branch`, `isClientUser`, `accountId`,
`status`, `language`, `preferences`, `timetableId`, `otpAuthActive`

---

### 3.2 Usuarios / Agentes

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/users` | Listar todos os usuarios | CONFIRMADO |
| GET | `/users/{id}` | Buscar usuario por ID | CONFIRMADO |

**Campos do registro de usuario:**
```
id, name, email, phoneNumber, branch, isClientUser,
accountId, status, clientsStatus, language,
isActiveInternalChat, timetableId, otpAuthActive,
createdAt, updatedAt, deletedAt, archivedAt
```

**Filtros disponiveis (confirmados):**
- `limit`, `skip`

---

### 3.3 Departamentos

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/departments` | Listar departamentos | CONFIRMADO |
| GET | `/departments/{id}` | Buscar departamento por ID | CONFIRMADO |

**Campos do registro de departamento:**
```
id, name, accountId, distributionId,
archivedAt, createdAt, updatedAt
```

---

### 3.4 Canais / Conexoes (services)

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/services` | Listar canais ativos | CONFIRMADO |
| GET | `/services/{id}` | Buscar canal por ID | CONFIRMADO |

**Campos relevantes do registro de service:**
```
id, name, type, accountId, botId,
defaultDepartmentId, archivedAt, deletedAt
```

**Campo type observado:** `whatsapp-business`

---

### 3.5 Contatos / Clientes

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/contacts` | Listar contatos | CONFIRMADO |
| GET | `/contacts/{id}` | Buscar contato por ID | CONFIRMADO |

**Filtros confirmados:**

| Parametro | Descricao |
|---|---|
| `search` | Busca geral por nome ou numero |
| `name` | Filtro por nome |
| `phone` | Filtro por numero de telefone |
| `phoneNumber` | Alias de phone |
| `idFromService` | Numero do WhatsApp (ex: 5562...) |
| `document` | Documento do contato |
| `limit` | Paginacao |
| `skip` | Paginacao |

**Total de contatos na conta:** 20.075 (em 23/05/2026)

**Campos do registro de contato:**
```
id, name, internalName, alternativeName,
idFromService, accountId, serviceId, personId,
defaultDepartmentId, defaultUserId,
currentTicketId, status, lastMessageAt,
lastContactMessageAt, hadChat, visible,
isGroup, isBroadcast, isMe, unread,
isSilenced, isMyContact, block,
createdAt, updatedAt, deletedAt, archivedAt,
data (objeto com: number, jidId, lidId, validNumber, etc.)
```

---

### 3.6 Chamados / Tickets

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/tickets` | Listar chamados | CONFIRMADO |
| GET | `/tickets/{id}` | Buscar chamado por ID | CONFIRMADO |

**Filtros confirmados:**

| Parametro | Tipo | Descricao |
|---|---|---|
| `userId` | UUID | Chamados de um agente especifico |
| `contactId` | UUID | Chamados de um contato especifico |
| `isOpen` | boolean | true = abertos, false = encerrados |
| `departmentId` | UUID | Chamados de um departamento |
| `serviceId` | UUID | Chamados de um canal especifico |
| `search` | string | Busca por texto |
| `protocol` | string | Numero do protocolo |
| `sort` | string | Ordenacao (ex: `-createdAt` para decrescente) |
| `startedAt[gte]` | ISO date | Chamados iniciados a partir de data |
| `createdAt[gte]` | ISO date | Chamados criados a partir de data |
| `limit` | inteiro | Paginacao |
| `skip` | inteiro | Paginacao |

**Total de chamados na conta:** 2.515 (em 23/05/2026)

**Campos do registro de ticket:**
```json
{
  "id": "uuid",
  "isOpen": false,
  "protocol": "2026041516",
  "origin": "automatic",
  "accountId": "uuid",
  "departmentId": "uuid",
  "contactId": "uuid",
  "userId": "uuid",
  "firstMessageId": "uuid",
  "lastMessageId": "uuid",
  "currentTicketTransferId": null,
  "startedAt": "2026-04-15T18:20:10Z",
  "endedAt": "2026-04-17T13:23:48Z",
  "metrics": {
    "ticketTime": 155017,
    "messagingTime": 91010,
    "isActiveTicket": true
  },
  "createdAt": "2026-04-15T18:20:10Z",
  "updatedAt": "2026-04-17T13:23:48Z",
  "firstMessage": null,
  "lastMessage": null
}
```

**Relacionamentos chave:**
- `contactId` -> `contacts.id` (identifica o cliente)
- `userId` -> `users.id` (identifica o agente responsavel)
- `departmentId` -> `departments.id`

---

### 3.7 Mensagens

| Metodo | Endpoint | Finalidade | Status |
|---|---|---|---|
| GET | `/messages?ticketId={id}` | Mensagens de um chamado | CONFIRMADO |
| GET | `/messages/{id}` | Mensagem individual | CONFIRMADO |
| GET | `/messages?type=audio` | Todas as mensagens de audio | CONFIRMADO |
| GET | `/messages?include=file` | Mensagens com dados do arquivo | CONFIRMADO |

**Filtros confirmados:**

| Parametro | Descricao |
|---|---|
| `ticketId` | UUID do chamado |
| `type` | Tipo da mensagem: chat, audio, ticket |
| `include=file` | Inclui objeto file com URL e metadados |
| `limit` | Paginacao |
| `skip` | Paginacao |

**Tipos de mensagem encontrados:**
- `chat` — mensagem de texto comum
- `audio` — mensagem de voz
- `ticket` — evento interno do sistema (abertura, fechamento, transferencia)

**Total de mensagens de audio na conta:** 55.666 (em 23/05/2026)

**Campos do registro de mensagem:**
```
id, type, isFromMe, sent, timestamp,
ticketId, contactId, userId,
ticketUserId, ticketDepartmentId,
serviceId, fromId, toId,
quotedMessageId, quotedMessage,
origin, hsmId,
isComment, isFromBot,
isTranscribing, transcribeError,
text, obfuscated,
data (objeto variavel por tipo),
createdAt, updatedAt, deletedAt
```

**Campos exclusivos do include=file:**
```
file.id, file.name, file.extension,
file.mimetype, file.checksum,
file.publicFilename, file.url,
file.accountId, file.createdAt, file.updatedAt,
file.data.audioMetadata.duration,
file.data.audioMetadata.bitRate,
file.data.audioMetadata.channels,
file.data.audioMetadata.sampleRate,
file.data.audioMetadata.peaks
```

---

## 4. Relacionamentos entre entidades

```
users.id
  └── tickets.userId           (agente responsavel pelo chamado)
  └── messages.userId          (agente que enviou a mensagem)
  └── messages.ticketUserId    (agente do chamado no momento da mensagem)

contacts.id
  └── tickets.contactId        (cliente do chamado)
  └── messages.contactId       (cliente da mensagem)

tickets.id
  └── messages.ticketId        (mensagens pertencem ao chamado)

messages.id
  └── messages.file.id         (arquivo associado, via include=file)
```

---

## 5. Endpoints com status pendente de validacao

| Endpoint | Hipotese | Pendencia |
|---|---|---|
| `POST /auth/token` | Autenticacao programatica | Nao testado — verificar se token so e gerado via UI |
| `GET /tickets?startedAt[gte]=` | Filtro por data de inicio | Confirmar encoding do bracket em Python |
| `GET /users?departmentId=` | Filtrar usuarios por departamento | Nao testado |
| `GET /contacts/{id}/tickets` | Historico de chamados do contato | Retornou 404 no teste |

---

## 6. Observacoes tecnicas

- A API nao retorna URL de arquivo no objeto de mensagem padrao.
  E necessario passar `?include=file` para obter o campo `file`.
- URLs de audio sao presigned (Oracle Cloud), validas por 24 horas.
- O metodo HEAD retorna 403 nas URLs presigned. Usar somente GET.
- Paginacao padrao e 15 registros. Usar `limit` explicito.
- O campo `data` dentro de cada mensagem varia conforme o tipo.
- Mensagens do tipo `ticket` sao eventos internos (ex: abertura, fechamento).
  Nao representam mensagens enviadas ao cliente.
