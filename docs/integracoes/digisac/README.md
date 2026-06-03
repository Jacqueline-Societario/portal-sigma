# Integracao Digisac — Base de Conhecimento

**Projeto:** Portal Sigma (portal societario)
**Cliente:** Sigma Contabilidade
**Plataforma:** Digisac — omnichannel de atendimento
**URL base da API:** `https://gsigma.digisac.me/api/v1`
**Data do diagnostico:** 23/05/2026
**Status:** Documentacao — sem implementacao ativa

---

## O que e esta base

Esta pasta reune todo o conhecimento tecnico levantado sobre a API do Digisac
para uso futuro em:

- buscas e analises de chamados;
- relatorios por agente, cliente, periodo ou departamento;
- exportacao de planilhas;
- criacao de dashboards;
- leitura e transcricao de mensagens de audio;
- futura implantacao em portal, se decidido.

Nenhuma integracao ativa foi criada. Nenhum codigo do portal foi alterado.

---

## Escopo confirmado (somente leitura)

| Funcionalidade | Status |
|---|---|
| Listar chamados/tickets | CONFIRMADO |
| Filtrar chamados por agente | CONFIRMADO |
| Filtrar chamados por contato/cliente | CONFIRMADO |
| Abrir chamado especifico por ID | CONFIRMADO |
| Listar mensagens de um chamado | CONFIRMADO |
| Identificar mensagens de audio | CONFIRMADO |
| Acessar URL do arquivo de audio | CONFIRMADO |
| Baixar audio via GET | CONFIRMADO |
| Ler transcricao existente (campo text) | CONFIRMADO |
| Buscar contatos por nome, telefone, ID | CONFIRMADO |
| Listar usuarios/agentes | CONFIRMADO |
| Listar departamentos | CONFIRMADO |
| Listar canais/conexoes (services) | CONFIRMADO |

## Fora do escopo (nao documentado aqui)

- Envio de mensagens
- Criacao ou edicao de contatos
- Abertura ou fechamento de chamados
- Transferencia de atendimentos
- Campanhas
- Qualquer operacao de escrita

---

## Indice dos documentos

| Arquivo | Conteudo |
|---|---|
| `01-mapa-api-digisac.md` | Endpoints, autenticacao, paginacao, estruturas de dados |
| `02-guia-consultas.md` | Como fazer buscas por agente, cliente, periodo, audio |
| `03-modelo-relatorios.md` | Modelos de relatorios prontos para solicitar |
| `04-modelo-planilhas.md` | Estrutura de planilhas para exportacao |
| `05-modelo-dashboards.md` | Indicadores e estrutura de dashboards |
| `06-audios-e-transcricoes.md` | Identificacao, acesso, metadados e transcricao de audios |
| `07-seguranca-e-privacidade.md` | Regras de seguranca e privacidade |
| `08-plano-futuro-implantacao.md` | Arquitetura para futura implantacao em portal |
| `09-prompts-futuros.md` | Prompts prontos para reutilizacao em sessoes futuras |
| `10-resumo-para-proxima-sessao.md` | Resumo completo para handoff entre sessoes |

---

## Como usar esta base em sessoes futuras

1. Abra qualquer arquivo desta pasta conforme a necessidade.
2. Passe o conteudo relevante para o Claude junto com o contexto da tarefa.
3. Use os prompts prontos em `09-prompts-futuros.md` para agilizar.
4. Consulte `10-resumo-para-proxima-sessao.md` para retomar sem perda de contexto.

---

## Credenciais

Token nao salvo aqui.
Consultar variavel DIGISAC_API_TOKEN no .env do portal
ou gerar novo token na interface do Digisac:
Menu do usuario > Configuracoes > Token de Acesso Pessoal.
