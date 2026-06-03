# 07 — Seguranca e Privacidade

Regras obrigatorias para qualquer uso da API Digisac.

---

## 1. Token de API

**Regra absoluta:** o token nunca deve aparecer em:
- codigo versionado (.py, .js, .env commitado)
- logs de sistema ou aplicacao
- respostas de API expostas ao usuario
- arquivos de documentacao (incluindo este)
- mensagens de erro exibidas na tela

**Onde deve ficar:**
- variavel de ambiente: `DIGISAC_API_TOKEN`
- arquivo `.env` local, com `chmod 600`
- `.env` listado no `.gitignore`

**Como usar em Python:**
```python
import os
TOKEN = os.environ["DIGISAC_API_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
```

**Como gerar novo token:**
Interface Digisac > Menu do usuario > Token de Acesso Pessoal.
O token atual e invalidado ao gerar um novo.

---

## 2. URLs presigned de audio

As URLs de audio (campo `file.url`) contem assinatura criptografica embutida.
Sao validas por 24 horas.

**Nao fazer:**
- salvar em banco de dados
- incluir em logs
- exibir ao usuario final
- compartilhar por mensagem ou email

**Fazer:**
- solicitar fresh a cada uso via API
- usar somente para download imediato
- nao armazenar apos o uso

---

## 3. Dados pessoais de clientes

Mensagens, transcricoes e dados de contato sao dados pessoais sujeitos a LGPD.

**Regras:**
- nao logar payload completo de conversas
- nao armazenar historico de mensagens fora da necessidade especifica
- audios baixados devem ser deletados imediatamente apos processamento
- transcricoes geradas externamente (Whisper API) enviam audio a terceiros —
  avaliar necessidade e base legal antes de usar
- nao exibir conteudo de conversas em dashboards sem controle de acesso

---

## 4. Logs seguros

**O que nao deve aparecer em logs:**
- token de API
- URLs presigned
- texto de mensagens de clientes
- numeros de telefone em formato raw
- nomes de clientes associados a conteudo de conversa

**Formato seguro de log:**
```python
import logging

logging.info("GET /tickets status=200 total=%d", chamados["total"])
logging.info("Audio processado id=%s duracao=%ds transcrito=%s",
             audio_id[:8], duracao, "sim" if transcricao else "nao")
# NUNCA: logging.info("Transcricao: %s", texto_da_conversa)
```

---

## 5. Operacoes de escrita — restricoes absolutas

A integracao atual e somente de leitura. As operacoes abaixo sao proibidas
sem autorizacao explicita documentada:

| Operacao | Endpoint | Risco |
|---|---|---|
| Enviar mensagem | POST /messages | Mensagem enviada ao cliente real |
| Fechar chamado | PUT ou DELETE /tickets/{id} | Encerra atendimento real |
| Transferir chamado | POST /tickets/{id}/transfer | Redireciona atendimento |
| Criar contato | POST /contacts | Cria registro real |
| Editar contato | PUT /contacts/{id} | Altera dados reais |
| Disparar campanha | POST /campaigns/{id}/send | Envia mensagem em massa |
| Excluir qualquer dado | DELETE qualquer endpoint | Irreversivel |

**Antes de qualquer escrita futura:**
1. Documentar o objetivo da operacao
2. Obter autorizacao explicita
3. Testar em ambiente separado
4. Criar log de auditoria da operacao

---

## 6. Controle de acesso ao portal

Se a integracao for implantada no portal-sigma:

- apenas usuarios autenticados devem acessar dados do Digisac
- dados de conversas de clientes so devem ser visiveis para usuarios autorizados
- implementar log de auditoria de quem consultou quais chamados
- nao cachear dados sensiveis sem controle de TTL

---

## 7. Download de audios em massa

**Nao fazer:**
- baixar todos os 55.666 audios em loop sem controle
- processar multiplos audios simultaneamente sem pausa
- manter copia local de audios de clientes

**Fazer:**
- processar somente o necessario para a tarefa especifica
- implementar pausa entre requisicoes (min. 500ms entre chamadas)
- verificar campo `text` antes de baixar — economiza bandwidth e custo
- apagar arquivo de audio imediatamente apos processamento

---

## 8. Checklist de seguranca antes de implementar

```
[ ] .env esta no .gitignore
[ ] Token nao aparece em nenhum arquivo versionado
[ ] Logs nao incluem token, URL presigned ou conteudo de conversa
[ ] Operacoes de escrita estao bloqueadas ou nao implementadas
[ ] Dados de clientes nao sao exibidos sem autenticacao
[ ] Audios temporarios sao deletados apos uso
[ ] Rate limiting ou pausa entre requisicoes esta implementado
[ ] Nao ha cache de URLs presigned alem de 1h
```

---

## 9. Rate limiting

**Status:** nao documentado pelo Digisac ate 23/05/2026.

**Recomendacao conservadora:**
- maximo de 60 requisicoes por minuto
- pausa de 1s entre chamadas em lote
- implementar retry com backoff exponencial em caso de 429

```python
import time

def get_seguro(url, headers, params=None, max_tentativas=3):
    for tentativa in range(max_tentativas):
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            espera = 2 ** tentativa
            time.sleep(espera)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception(f"Falha apos {max_tentativas} tentativas")
```
