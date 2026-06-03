# 06 — Audios e Transcricoes Digisac

Documento especifico sobre identificacao, acesso, metadados e transcricao de audios.
Tudo confirmado por testes em 23/05/2026.

---

## 1. Identificando mensagens de audio

Uma mensagem de audio tem o campo `type == "audio"`.

```python
# Ao listar mensagens de um chamado
mensagens = requests.get(
    f"{BASE}/messages",
    headers=HEADERS,
    params={"ticketId": ticket_id, "limit": 100}
).json()["data"]

audios = [m for m in mensagens if m["type"] == "audio"]
```

**Observacao importante:** mensagens do tipo `ticket` tambem podem aparecer
com `data.ticketOpen`, `data.ticketClose` ou `data.ticketTransfer`.
Elas representam eventos internos do sistema, nao mensagens de audio real.
Filtrar sempre por `type == "audio"` antes de processar.

---

## 2. Campos relevantes da mensagem de audio

| Campo | Tipo | Descricao | Sempre presente? |
|---|---|---|---|
| `id` | uuid | ID unico da mensagem | Sim |
| `type` | string | Sempre "audio" para audios | Sim |
| `isFromMe` | bool | true = enviado pelo agente | Sim |
| `timestamp` | datetime | Data/hora da mensagem | Sim |
| `ticketId` | uuid | Chamado ao qual pertence | Sim |
| `contactId` | uuid | Contato (cliente) | Sim |
| `userId` | uuid | Usuario que enviou (se agente) | Sim se agente |
| `ticketUserId` | uuid | Agente responsavel no momento | Sim |
| `ticketDepartmentId` | uuid | Departamento no momento | Sim |
| `isComment` | bool | Se e comentario interno | Sim |
| `isFromBot` | bool | Se veio de robô | Sim |
| `isTranscribing` | bool/null | Transcricao em andamento | Null quando inativo |
| `transcribeError` | string/null | Erro na transcricao automatica | Null quando ok |
| `text` | string/null | Transcricao do audio (quando existe) | Null se nao transcrito |
| `data.hasAudioMetadata` | bool | Tem metadados de audio | Quando disponivel |
| `data.fileDownload` | objeto | Info de download pelo Digisac | Quando disponivel |

---

## 3. Campo text — transcricao existente

O campo `text` pode conter a transcricao automatica feita pelo proprio Digisac.

**Status confirmado em 23/05/2026:**
- 55.666 mensagens de audio na conta
- Muitas ja possuem `text` preenchido (ex: "Tá bom, vou fechar então e enviar por e-mail")
- A transcricao e feita pelo modulo interno de IA do Digisac
- Nao existe endpoint para solicitar transcricao via API (somente leitura do campo)

**Logica de verificacao:**

```python
def status_transcricao(msg):
    if msg.get("text"):
        return "TRANSCRITO", msg["text"]
    elif msg.get("isTranscribing"):
        return "EM_ANDAMENTO", None
    elif msg.get("transcribeError"):
        return "ERRO", msg["transcribeError"]
    else:
        return "SEM_TRANSCRICAO", None
```

---

## 4. Campo file — dados do arquivo de audio

Disponivel apenas com `?include=file` na requisicao.

```python
resp = requests.get(
    f"{BASE}/messages/{message_id}",
    headers=HEADERS,
    params={"include": "file"}
)
msg = resp.json()
file_info = msg.get("file", {})
```

**Campos do objeto file:**

| Campo | Exemplo | Descricao |
|---|---|---|
| `file.id` | uuid | ID do arquivo no Digisac |
| `file.name` | 933e2939.mp3 | Nome do arquivo |
| `file.extension` | mp3 | Extensao |
| `file.mimetype` | audio/mpeg | Tipo MIME |
| `file.checksum` | sha1 hash | Verificacao de integridade |
| `file.publicFilename` | 933e2939.mp3 | Nome publico |
| `file.url` | https://... | URL presigned para download |
| `file.createdAt` | datetime | Data de criacao |
| `file.updatedAt` | datetime | Data de atualizacao |

**Metadados de audio (dentro de file.data.audioMetadata):**

| Campo | Tipo | Exemplo |
|---|---|---|
| `duration` | inteiro (segundos) | 35 |
| `bitRate` | inteiro (kbps) | 64 |
| `channels` | inteiro | 1 (mono) |
| `sampleRate` | inteiro (Hz) | 48000 |
| `peaks` | array de floats | [0.57, 0.98, ...] |

---

## 5. URL de download do audio

**Tipo:** Presigned URL (Oracle Cloud Object Storage)
**Validade:** 86400 segundos (24 horas)
**Metodo suportado:** GET (HEAD retorna 403)
**Autenticacao:** nao necessaria (a assinatura esta na URL)
**Formato:** `https://axvaplbwrlcl.compat.objectstorage.sa-vinhedo-1.oraclecloud.com/...`

**IMPORTANTE:**
- A URL expira em 24h. Solicitar fresh a cada uso.
- Nao salvar a URL em banco ou log — contem dados de assinatura.
- Nao usar HEAD — usar GET com Range para verificar.
- Usar `Range: bytes=0-255` para verificar sem baixar o arquivo completo.

**Confirmado em teste:**
```
GET {url_presigned} com Range: bytes=0-255
Resposta: HTTP 206, content-type: audio/mpeg
Conteudo: MP3 real (ID3 header confirmado)
```

---

## 6. Como baixar o audio

```python
import requests, tempfile, os

def baixar_audio(file_url: str, sufixo=".mp3") -> str:
    """
    Baixa o audio da URL presigned e salva em arquivo temporario.
    Retorna o caminho do arquivo.
    A URL deve ser obtida fresca via API antes de chamar esta funcao.
    """
    resp = requests.get(file_url, stream=True)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
        for chunk in resp.iter_content(chunk_size=8192):
            tmp.write(chunk)
        return tmp.name
```

**Apagar o arquivo apos processar** — nao manter copias de audios de clientes:

```python
try:
    caminho = baixar_audio(file_url)
    transcricao = transcrever(caminho)
finally:
    if os.path.exists(caminho):
        os.unlink(caminho)
```

---

## 7. Como transcrever o audio (opcoes)

### Opcao A — Usar transcricao ja existente (preferida, custo zero)

```python
if msg.get("text"):
    transcricao = msg["text"]
    # Usar diretamente, sem download
```

### Opcao B — Whisper API (OpenAI)

Custo: ~U$0,006 por minuto de audio.
Requer: chave OPENAI_API_KEY no ambiente.

```python
import openai

def transcrever_com_whisper_api(caminho_mp3: str) -> str:
    with open(caminho_mp3, "rb") as f:
        resp = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="pt"
        )
    return resp.text
```

### Opcao C — Whisper local (sem custo, sem API externa)

Requer: `pip install openai-whisper` + ffmpeg no sistema.
Modelo small (~244MB): bom para portugues, rapido.
Modelo medium (~769MB): mais preciso, mais lento.

```python
import whisper

modelo = whisper.load_model("small")

def transcrever_local(caminho_mp3: str) -> str:
    resultado = modelo.transcribe(caminho_mp3, language="pt")
    return resultado["text"]
```

**Recomendacao:** Opcao A sempre que disponivel. Opcao B para audios sem text
e quando privacidade for aceitavel. Opcao C quando privacidade for critica
(dados de clientes nao devem sair da VPS).

---

## 8. Fluxo completo recomendado

```python
def processar_audios_de_chamado(ticket_id: str) -> list:
    resultados = []

    # 1. Listar audios do chamado
    resp = requests.get(
        f"{BASE}/messages",
        headers=HEADERS,
        params={"ticketId": ticket_id, "type": "audio", "limit": 100}
    )
    audios = resp.json()["data"]

    for audio in audios:
        item = {
            "id": audio["id"],
            "timestamp": audio["timestamp"],
            "isFromMe": audio["isFromMe"],
            "transcricao": None,
            "fonte_transcricao": None,
        }

        # 2. Verificar transcricao existente
        if audio.get("text"):
            item["transcricao"] = audio["text"]
            item["fonte_transcricao"] = "digisac"

        else:
            # 3. Obter URL do arquivo
            resp2 = requests.get(
                f"{BASE}/messages/{audio['id']}",
                headers=HEADERS,
                params={"include": "file"}
            ).json()

            file_info = resp2.get("file", {})
            item["duracao_seg"] = file_info.get("data", {}).get(
                "audioMetadata", {}
            ).get("duration")

            # 4. Transcrever se necessario (somente se decisao for transcrever)
            # url = file_info.get("url")
            # caminho = baixar_audio(url)
            # item["transcricao"] = transcrever_com_whisper_api(caminho)
            # item["fonte_transcricao"] = "whisper"
            # os.unlink(caminho)

        resultados.append(item)

    return resultados
```

---

## 9. Limites e riscos

| Limite / Risco | Detalhe |
|---|---|
| URL expira em 24h | Solicitar fresh a cada uso |
| HEAD retorna 403 | Usar somente GET |
| Audio armazenado temporariamente | Apagar imediatamente apos processar |
| Transcricao Whisper API envia audio a terceiros | Avaliar LGPD para dados de clientes |
| Download em massa pode ser lento | Processar em lotes com pausa entre requisicoes |
| Nem todos os audios tem transcricao no campo text | Implementar fallback |
