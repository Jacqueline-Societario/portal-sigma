# 02 — Guia de Consultas Digisac

**Base URL:** `https://gsigma.digisac.me/api/v1`
**Autenticacao:** `Authorization: Bearer {DIGISAC_API_TOKEN}`

Todos os exemplos abaixo sao de leitura (GET). Nenhuma operacao de escrita.

---

## 1. Consultas por Usuario / Agente

### Listar todos os agentes

```python
import requests

BASE = "https://gsigma.digisac.me/api/v1"
HEADERS = {"Authorization": f"Bearer {DIGISAC_API_TOKEN}"}

resp = requests.get(f"{BASE}/users", headers=HEADERS, params={"limit": 100})
agentes = resp.json()["data"]

for a in agentes:
    print(a["id"], a["name"], a["email"])
```

### Chamados de um agente especifico

```python
# Obter o ID do agente primeiro (via /users ou /me)
USER_ID = "uuid-do-agente"

resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={
        "userId": USER_ID,
        "limit": 50,
        "skip": 0
    }
)
chamados = resp.json()
print(f"Total de chamados do agente: {chamados['total']}")
```

### Chamados abertos de um agente

```python
resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={"userId": USER_ID, "isOpen": "true", "limit": 50}
)
```

### Chamados encerrados de um agente em um periodo

```python
resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={
        "userId": USER_ID,
        "isOpen": "false",
        "startedAt[gte]": "2026-05-01T00:00:00Z",
        "limit": 100
    }
)
```

---

## 2. Consultas por Contato / Cliente

### Buscar contato por nome ou telefone

```python
resp = requests.get(
    f"{BASE}/contacts",
    headers=HEADERS,
    params={"search": "nome do cliente", "limit": 10}
)
contatos = resp.json()["data"]
```

### Buscar contato por numero de telefone (WhatsApp)

```python
# Formato: DDI + DDD + numero (ex: 5562999990000)
resp = requests.get(
    f"{BASE}/contacts",
    headers=HEADERS,
    params={"phone": "5562999990000", "limit": 5}
)
```

### Chamados de um contato especifico

```python
CONTACT_ID = "uuid-do-contato"

resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={"contactId": CONTACT_ID, "limit": 50, "skip": 0}
)
chamados = resp.json()
print(f"Total de chamados do contato: {chamados['total']}")
```

---

## 3. Consultas por Chamado / Ticket

### Buscar chamado por ID

```python
TICKET_ID = "uuid-do-chamado"

resp = requests.get(f"{BASE}/tickets/{TICKET_ID}", headers=HEADERS)
chamado = resp.json()

print("Protocolo:", chamado["protocol"])
print("Aberto:", chamado["isOpen"])
print("Iniciado em:", chamado["startedAt"])
print("Encerrado em:", chamado["endedAt"])
print("Agente ID:", chamado["userId"])
print("Contato ID:", chamado["contactId"])
print("Departamento ID:", chamado["departmentId"])
print("Tempo total (seg):", chamado["metrics"]["ticketTime"])
```

### Buscar chamado por protocolo

```python
resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={"protocol": "2026041516"}
)
```

### Listar chamados por periodo

```python
resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={
        "startedAt[gte]": "2026-05-01T00:00:00Z",
        "isOpen": "false",
        "limit": 100,
        "skip": 0
    }
)
```

### Paginar todos os chamados

```python
def listar_todos_chamados(status_aberto=None):
    todos = []
    skip = 0
    limit = 100

    while True:
        params = {"limit": limit, "skip": skip}
        if status_aberto is not None:
            params["isOpen"] = "true" if status_aberto else "false"

        resp = requests.get(f"{BASE}/tickets", headers=HEADERS, params=params)
        dados = resp.json()
        todos.extend(dados["data"])

        if len(todos) >= dados["total"]:
            break
        skip += limit

    return todos
```

---

## 4. Consultas de Mensagens de um Chamado

### Listar todas as mensagens de um chamado

```python
TICKET_ID = "uuid-do-chamado"

resp = requests.get(
    f"{BASE}/messages",
    headers=HEADERS,
    params={"ticketId": TICKET_ID, "limit": 100, "skip": 0}
)
mensagens = resp.json()["data"]
print(f"Total de mensagens: {resp.json()['total']}")
```

### Separar mensagens por tipo

```python
textos = [m for m in mensagens if m["type"] == "chat"]
audios = [m for m in mensagens if m["type"] == "audio"]
eventos = [m for m in mensagens if m["type"] == "ticket"]

print(f"Textos: {len(textos)} | Audios: {len(audios)} | Eventos: {len(eventos)}")
```

### Separar por direcao (enviado pelo agente ou pelo cliente)

```python
enviados_pelo_agente = [m for m in mensagens if m["isFromMe"]]
enviados_pelo_cliente = [m for m in mensagens if not m["isFromMe"]]
```

---

## 5. Consultas de Mensagens de Audio

### Listar audios de um chamado especifico

```python
resp = requests.get(
    f"{BASE}/messages",
    headers=HEADERS,
    params={"ticketId": TICKET_ID, "type": "audio", "limit": 50}
)
audios = resp.json()["data"]
```

### Identificar se audio ja tem transcricao

```python
for audio in audios:
    if audio.get("text"):
        print(f"[TRANSCRITO] {audio['id']}: {audio['text']}")
    elif audio.get("isTranscribing"):
        print(f"[EM TRANSCRICAO] {audio['id']}")
    elif audio.get("transcribeError"):
        print(f"[ERRO] {audio['id']}: {audio['transcribeError']}")
    else:
        print(f"[SEM TRANSCRICAO] {audio['id']}")
```

### Obter URL de download do audio

```python
resp = requests.get(
    f"{BASE}/messages/{audio['id']}",
    headers=HEADERS,
    params={"include": "file"}
)
msg = resp.json()
file_info = msg.get("file", {})

url_audio = file_info.get("url")         # URL presigned, valida por 24h
mimetype  = file_info.get("mimetype")    # audio/mpeg
extensao  = file_info.get("extension")   # mp3
duracao   = file_info.get("data", {}).get("audioMetadata", {}).get("duration")

print(f"Duracao: {duracao}s | Tipo: {mimetype}")
# Nao imprimir a URL — e uma URL assinada com credenciais embutidas
```

### Listar todos os audios da conta com include=file

```python
resp = requests.get(
    f"{BASE}/messages",
    headers=HEADERS,
    params={"type": "audio", "include": "file", "limit": 50, "skip": 0}
)
print(f"Total de audios na conta: {resp.json()['total']}")
```

---

## 6. Consultas por Departamento

### Listar todos os departamentos

```python
resp = requests.get(f"{BASE}/departments", headers=HEADERS, params={"limit": 100})
departamentos = resp.json()["data"]

for d in departamentos:
    print(d["id"], d["name"])
```

### Chamados de um departamento especifico

```python
DEPT_ID = "uuid-do-departamento"

resp = requests.get(
    f"{BASE}/tickets",
    headers=HEADERS,
    params={"departmentId": DEPT_ID, "limit": 50}
)
```

---

## 7. Consultas combinadas

### Resumo completo de um chamado (ticket + contato + agente + mensagens)

```python
def resumo_chamado(ticket_id):
    # 1. Dados do chamado
    ticket = requests.get(f"{BASE}/tickets/{ticket_id}", headers=HEADERS).json()

    # 2. Dados do contato
    contato = requests.get(f"{BASE}/contacts/{ticket['contactId']}", headers=HEADERS).json()

    # 3. Dados do agente
    agente = requests.get(f"{BASE}/users/{ticket['userId']}", headers=HEADERS).json() \
        if ticket.get("userId") else None

    # 4. Mensagens do chamado
    msgs_resp = requests.get(
        f"{BASE}/messages",
        headers=HEADERS,
        params={"ticketId": ticket_id, "limit": 200}
    ).json()
    mensagens = msgs_resp["data"]

    # 5. Audios com transcricao
    audios_transcritos = [
        m for m in mensagens
        if m["type"] == "audio" and m.get("text")
    ]

    return {
        "ticket": ticket,
        "contato_nome": contato.get("name"),
        "agente_nome": agente.get("name") if agente else None,
        "total_mensagens": msgs_resp["total"],
        "audios_transcritos": len(audios_transcritos),
        "transcricoes": [m["text"] for m in audios_transcritos]
    }
```

---

## 8. Boas praticas de consulta

- Sempre usar `limit` explicito (evitar depender do padrao 15).
- Implementar paginacao com `skip` para conjuntos grandes.
- Solicitar `include=file` somente para mensagens de audio que precisem de download.
- Verificar o campo `text` antes de tentar baixar o audio.
- Nao logar URLs presigned de audio.
- Nao armazenar payloads completos de conversas.
- Usar filtros de data para evitar carregar historico completo desnecessariamente.
