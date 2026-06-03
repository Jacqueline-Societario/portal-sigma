# 05 — Modelo de Dashboards Digisac

Estrutura e indicadores para dashboards futuros.
Dados via API Digisac (somente leitura). Sem implementacao neste momento.

---

## 1. Indicadores Principais (KPIs)

| Indicador | Calculo | Fonte |
|---|---|---|
| Total de chamados no periodo | count tickets com filtro de data | /tickets |
| Chamados abertos agora | count isOpen=true | /tickets?isOpen=true |
| Chamados encerrados no dia | count isOpen=false com startedAt=hoje | /tickets |
| Tempo medio de atendimento | mean(ticketTime) / 60 | /tickets (metrics) |
| Total de mensagens | sum de messages por chamado | /messages |
| Total de audios | count type=audio | /messages?type=audio |
| Audios com transcricao | count text != null | /messages?type=audio |
| Agentes ativos (com chamado aberto) | agrupamento por userId em isOpen=true | /tickets?isOpen=true |
| Chamados sem agente | count userId=null | /tickets |

---

## 2. Painel por Agente

**Visao:** card por agente com metricas do periodo

```
+---------------------------+
| Maria Fernanda            |
| Chamados: 12              |
| Abertos: 2                |
| Encerrados: 10            |
| Tempo medio: 18 min       |
| Mensagens enviadas: 87    |
+---------------------------+
```

**Dados necessarios:**
- GET /users -> lista de agentes
- GET /tickets?userId={id}&isOpen=true -> chamados abertos
- GET /tickets?userId={id}&isOpen=false&startedAt[gte]=inicio -> chamados encerrados no periodo

---

## 3. Painel por Departamento

**Visao:** tabela com chamados por departamento

| Departamento | Abertos | Encerrados | Tempo medio (min) |
|---|---|---|---|
| Suporte | 5 | 28 | 22 |
| Vendas | 2 | 15 | 11 |
| Societario | 1 | 8 | 35 |

**Dados necessarios:**
- GET /departments -> lista de departamentos
- GET /tickets?departmentId={id}&isOpen=true/false

---

## 4. Painel por Cliente

**Visao:** historico de interacoes do cliente

```
Cliente: Joao da Silva
Total de chamados: 7
Ultimo chamado: 15/05/2026
Status atual: Encerrado
Agente habitual: Maria Fernanda
Audios enviados: 4
```

**Dados necessarios:**
- GET /contacts?search=nome -> encontrar contato
- GET /tickets?contactId={id} -> historico de chamados

---

## 5. Painel de Chamados por Periodo (timeline)

**Visao:** grafico de barras com chamados abertos por dia/semana/mes

```
Mai 2026
01 |##| 3
02 |####| 7
03 |###| 5
04 |######| 11
...
```

**Dados necessarios:**
- GET /tickets com filtros de data
- Agrupar por data de startedAt

---

## 6. Painel de Audios e Transcricoes

**Visao:** status de transcricao de audios

| Status | Quantidade |
|---|---|
| Transcritos (campo text preenchido) | 38.420 |
| Sem transcricao | 17.246 |
| Em transcricao | 0 |
| Erro de transcricao | 0 |

**Dados necessarios:**
- GET /messages?type=audio&limit=100 (paginado)
- Agrupar por estado do campo text / isTranscribing / transcribeError

---

## 7. Painel de Tempo de Atendimento

**Visao:** distribuicao de tempo de atendimento

| Faixa | Chamados |
|---|---|
| Ate 10 min | 45 |
| 10 a 30 min | 78 |
| 30 min a 1h | 32 |
| 1h a 3h | 15 |
| Acima de 3h | 7 |

**Calculo:** `ticket.metrics.ticketTime` em segundos

---

## 8. Tecnologias sugeridas para dashboard futuro

| Tecnologia | Cenario |
|---|---|
| HTML + Chart.js | Dashboard estatico simples, sem backend |
| Flask + Jinja2 + Chart.js | Dentro do portal-sigma existente |
| Streamlit (Python) | Dashboard de analise rapida, local |
| Jupyter Notebook | Analise exploratoria e relatorios ad-hoc |
| Google Sheets + Apps Script | Dashboard no Sheets com atualizacao manual |
| Plotly Dash | Dashboard interativo em Python |

**Recomendacao para curto prazo:** HTML estatico gerado por script Python
(sem servidor necessario, resultado compartilhavel por arquivo).

---

## 9. Estrutura de dados para dashboard

```python
# Estrutura de dicionario para alimentar um dashboard

painel = {
    "periodo": {"inicio": "2026-05-01", "fim": "2026-05-31"},
    "resumo": {
        "total_chamados": 145,
        "chamados_abertos": 8,
        "chamados_encerrados": 137,
        "tempo_medio_min": 22.4,
        "total_mensagens": 3820,
        "total_audios": 412,
        "audios_transcritos": 389,
    },
    "por_agente": [
        {
            "id": "uuid",
            "nome": "Maria Fernanda",
            "chamados_total": 45,
            "chamados_abertos": 2,
            "tempo_medio_min": 18.2,
        },
    ],
    "por_departamento": [
        {
            "id": "uuid",
            "nome": "Suporte",
            "chamados_total": 80,
            "tempo_medio_min": 25.1,
        },
    ],
}
```

---

## 10. Como solicitar dashboard em sessoes futuras

Exemplos de pedidos:

```
"Gere um dashboard HTML com os chamados de maio de 2026 por agente."

"Crie um relatorio visual com tempo medio de atendimento por departamento."

"Monte um painel com todos os audios com transcricao do mes passado."

"Gere um grafico de chamados por dia em abril de 2026."
```
