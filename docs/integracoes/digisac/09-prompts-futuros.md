# 09 — Prompts para Sessoes Futuras

Prompts prontos para copiar e usar com o Claude em sessoes futuras.
Substituir os valores entre [colchetes] antes de usar.

---

## 1. Buscar chamados por cliente

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), faca o seguinte:

1. Busque o contato com nome ou telefone: [NOME OU TELEFONE DO CLIENTE]
2. Liste todos os chamados desse contato
3. Para cada chamado, mostre: protocolo, data de inicio, status, agente responsavel
4. Nao envie mensagens, nao altere nada, somente leitura

Consulte docs/integracoes/digisac/01-mapa-api-digisac.md e
02-guia-consultas.md para os endpoints corretos.
```

---

## 2. Buscar chamados por agente

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), faca o seguinte:

1. Liste os usuarios/agentes disponiveis
2. Busque todos os chamados do agente: [NOME DO AGENTE]
3. Filtrar por periodo: [DATA INICIO] ate [DATA FIM] (formato YYYY-MM-DD)
4. Mostrar: total de chamados, chamados abertos, encerrados, tempo medio
5. Somente leitura, sem alteracoes

Consulte docs/integracoes/digisac/02-guia-consultas.md
```

---

## 3. Gerar relatorio de chamados por periodo

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), gere um relatorio com:

Periodo: [MES/ANO ou DATA INICIO ate DATA FIM]
Incluir:
- total de chamados
- chamados por agente
- chamados por status (aberto/encerrado)
- tempo medio de atendimento por agente
- total de mensagens e audios

Formato de saida: tabela no terminal ou exportar para
~/claude/clientes/sigma/projetos/alteracao-contratual/exports/digisac/relatorio_[periodo].xlsx

Somente leitura. Consulte 03-modelo-relatorios.md para estrutura.
```

---

## 4. Gerar planilha exportada

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), exporte uma planilha com:

Aba 1 — Chamados: todos os chamados de [PERIODO]
Aba 2 — Agentes: lista de agentes com metricas do periodo
Aba 3 — Audios: mensagens de audio com transcricao quando disponivel

Salvar em:
~/claude/clientes/sigma/projetos/alteracao-contratual/exports/digisac/

Somente leitura. Consulte 04-modelo-planilhas.md para colunas exatas.
```

---

## 5. Gerar dashboard HTML

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), gere um dashboard HTML com:

Periodo: [MES/ANO]
Indicadores:
- total de chamados
- chamados por agente (grafico de barras)
- tempo medio de atendimento
- chamados abertos x encerrados
- total de audios e transcricoes

Salvar em:
~/claude/clientes/sigma/projetos/alteracao-contratual/exports/digisac/dashboard_[periodo].html

Somente leitura. Consulte 05-modelo-dashboards.md para estrutura.
```

---

## 6. Analisar audios de um chamado

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), faca o seguinte:

1. Busque o chamado com protocolo: [NUMERO DO PROTOCOLO]
   ou ID: [UUID DO CHAMADO]
2. Liste todas as mensagens do chamado
3. Para as mensagens de audio:
   a. Verificar se o campo text ja tem transcricao
   b. Se sim, exibir a transcricao
   c. Se nao, informar duracao e que nao ha transcricao disponivel
4. Nao baixar audios em massa
5. Nao enviar mensagens
6. Nao alterar nada

Consulte 06-audios-e-transcricoes.md para o fluxo correto.
```

---

## 7. Levantamento geral por agente

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), faca um levantamento de:

Agente: [NOME DO AGENTE] (ou "todos os agentes")
Periodo: [MES/ANO]

Incluir para cada agente:
- total de chamados
- chamados abertos
- chamados encerrados
- tempo medio de atendimento (minutos)
- total de mensagens enviadas e recebidas
- total de audios com transcricao disponivel

Formato: tabela ou planilha.
Somente leitura.
```

---

## 8. Levantar dados de um cliente especifico

```
Usando a API do Digisac (base URL: https://gsigma.digisac.me/api/v1,
token na variavel DIGISAC_API_TOKEN), faca o seguinte:

Cliente: [NOME OU TELEFONE DO CLIENTE]

1. Encontrar o contato na API
2. Listar todos os chamados historicos
3. Para o chamado mais recente: mostrar todas as mensagens
4. Identificar audios com transcricao disponivel
5. Calcular tempo total de atendimento historico

Nao alterar dados. Somente leitura.
```

---

## 9. Preparar implantacao no portal

```
Quero implantar a integracao Digisac no portal-sigma.

Portal atual:
- Pasta: ~/claude/clientes/sigma/projetos/alteracao-contratual/
- Framework: Flask
- Ja tem blueprints em: blueprints/

Leia o plano em:
docs/integracoes/digisac/08-plano-futuro-implantacao.md

Execute as seguintes etapas (com confirmacao minha antes de cada uma):
1. Criar lib/digisac_client.py
2. Criar blueprints/digisac.py
3. Criar templates/digisac/
4. Indicar o que adicionar ao app.py (sem alterar ainda)
5. Indicar o que adicionar ao .env (sem salvar token)

Nao altere arquivos existentes sem confirmacao.
Nao implante sem aprovacao explicita.
```

---

## 10. Revisar seguranca antes de deploy

```
Antes de fazer deploy da integracao Digisac no portal-sigma, execute
a revisao de seguranca descrita em:
docs/integracoes/digisac/07-seguranca-e-privacidade.md

Verificar especificamente:
1. O token nao aparece em nenhum arquivo versionado
2. O .env esta no .gitignore
3. Os logs nao expoe dados de clientes
4. Nenhuma operacao de escrita esta implementada ou acessivel
5. Autenticacao do portal protege todas as rotas Digisac
6. Timeout e retry estao configurados
7. Nenhum blueprint existente foi removido ou alterado

Apresentar resultado do checklist antes de prosseguir com deploy.
```

---

## 11. Retomar trabalho anterior (handoff)

```
Estou retomando o trabalho de integracao Digisac com o portal-sigma da Sigma Contabilidade.

Leia o resumo completo em:
docs/integracoes/digisac/10-resumo-para-proxima-sessao.md

Depois informe:
- o que ja foi feito
- o que esta pendente
- qual e o proximo passo recomendado

Aguarde minha instrucao antes de executar qualquer acao.
```
