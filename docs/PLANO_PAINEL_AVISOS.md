# Plano — Painel de Avisos | Portal Societário

**Data:** 24/06/2026
**Status:** Aprovado — aguardando implementação

---

## O que é

Módulo de comunicados internos para a equipe do Societário. Avisos são criados pelo admin e aparecem no sino existente (como notificação) e como card flutuante no canto inferior direito da tela.

---

## Arquivos a criar ou alterar

| # | Arquivo (VPS) | Ação | O que muda |
|---|--------------|------|-----------|
| 1 | `database.py` | Alterar | 2 tabelas novas + funções CRUD |
| 2 | `portal.py` | Alterar | Registrar blueprint + MODULES_CONFIG + rotas API |
| 3 | `blueprints/avisos.py` | Criar | Rotas de gestão (admin) + API |
| 4 | `templates/avisos/index.html` | Criar | Página de gestão dos avisos |
| 5 | `templates/base.html` | Alterar | Botão "+", card flutuante, integração sino, JS de rodízio |

---

## Banco de dados

**Tabela `avisos`**
- `id`, `titulo`, `corpo`, `tipo` (urgente / importante / aviso / dica / sistema / procedimento / prazo)
- `link` (opcional, abre em nova aba)
- `data_expiracao` (opcional — aviso para de aparecer após essa data)
- `ativo` (toggle liga/desliga)
- `rodizio` (toggle inclui/exclui do rodízio do card flutuante)
- `criado_por`, `criado_em`, `atualizado_em`

**Tabela `avisos_usuarios`** — estado por usuário
- `aviso_id`, `user_id`
- `status` → `nao_lido` | `lido`
- `exibicoes_hoje`, `ultima_exibicao_data` → controle de rodízio

---

## Sino (notificações existentes)

- Quando um aviso é criado → entra na lista do sino de todos os usuários como notificação
- Badge do sino já existente passa a incluir avisos não lidos
- Ao clicar "Entendi" no card → marca como lido no sino também

---

## Botão "+"

- Círculo vermelho Sigma, posicionado à esquerda do sino na topbar
- Visível apenas para usuários com módulo `avisos` habilitado no painel admin
- Leva para `/avisos` (página de gestão)
- Sem badge numérico — é só atalho de acesso

---

## Card flutuante

**Qual aviso mostrar** — lógica do backend (`/api/avisos/proximo`):
1. Apenas ativos, não expirados, com `rodizio=1`
2. Excluir avisos que o usuário já marcou como lido
3. Excluir avisos já exibidos hoje para esse usuário
4. Prioridade: urgente → prazo → importante → aviso → procedimento → sistema → dica
5. Máximo 3 exibições por dia por usuário (somando todos os avisos)
6. Se nenhum elegível → card não aparece

**Botões do card:**

| Botão | Comportamento |
|-------|--------------|
| X (canto superior) | Fecha o card visualmente. Aviso continua no sino e pode reaparecer via rodízio. |
| Entendi | Fecha o card + grava `status=lido`. Sai do sino. Não reaparece no card. |

**Visual por tipo** (faixa colorida no topo + badge):

| Tipo | Cor |
|------|-----|
| Urgente | Vermelho `#b91c1c` |
| Importante | Laranja `#ea580c` |
| Aviso | Âmbar `#d97706` |
| Dica | Verde `#16a34a` |
| Sistema | Azul `#2563eb` |
| Procedimento | Roxo `#7c3aed` |
| Prazo | Rosa `#db2777` |

---

## Rotas da API

| Rota | Método | Quem acessa | O que faz |
|------|--------|-------------|-----------|
| `/api/avisos/proximo` | GET | Todos | Retorna próximo aviso elegível para o card |
| `/api/avisos/<id>/ler` | POST | Todos | Marca como lido (Entendi) |
| `/api/avisos` | GET / POST | Admin | Listar / criar aviso |
| `/api/avisos/<id>` | PUT / DELETE | Admin | Editar / excluir aviso |
| `/avisos` | GET | Admin | Página de gestão |

---

## Página de gestão `/avisos`

- Lista de avisos: título, tipo, ativo, rodízio, expiração, ações
- Formulário para criar / editar aviso (título, corpo, tipo, link, expiração, toggles ativo e rodízio)
- Toggle ativo/rodízio atualiza via AJAX sem reload
- Botão excluir com confirmação

---

## Sequência de implementação

1. `database.py` — tabelas + CRUD
2. `blueprints/avisos.py` — rotas admin + API
3. `templates/avisos/index.html` — página de gestão
4. `portal.py` — registrar blueprint + MODULES_CONFIG + rotas
5. `templates/base.html` — botão "+", card flutuante, integração sino, JS
