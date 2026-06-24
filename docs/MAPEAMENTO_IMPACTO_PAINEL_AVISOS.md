# Mapeamento de Impacto — Painel de Avisos | Portal Societário

**Data:** 24/06/2026
**Status:** Pronto para implementação
**Plano completo:** `docs/PLANO_PAINEL_AVISOS.md`
**Mockup:** `docs/mockup_painel_avisos.html`

---

## 1. `database.py` — 4 pontos de inserção

### Ponto 1.1 — Tabelas novas em `init_db()` — linha 297
Posição: entre o fechamento da tabela `anotacoes` (linha 296) e o `conn.commit()` (linha 298).
Inserir duas tabelas:

- `avisos` — campos: id, titulo, corpo, tipo, link, data_expiracao, ativo, rodizio, criado_por, criado_em, atualizado_em
- `avisos_usuarios` — campos: aviso_id, user_id, status, exibicoes_hoje, ultima_exibicao_data. Constraint: UNIQUE(aviso_id, user_id)

### Ponto 1.2 — Migração idempotente em `add_coluna_se_necessario()` — após linha 482
Posição: dentro da lista `migracoes[]`, após o último item (`anotacoes`, linha 482), antes do fechamento `]` (linha 483).
Inserir os dois `CREATE TABLE IF NOT EXISTS` acima no mesmo formato da lista (envoltos em `'''...'''`).
Finalidade: garantir criação das tabelas em bancos já existentes na VPS.

### Ponto 1.3 — Dict `TOOLS` — linha 614
Posição: após a última entrada do dict (`'cnae': 'Consulta CNAE / Regime Tributário'`, linha 614).
Inserir:
```python
'avisos': 'Painel de Avisos',
```
Finalidade: conecta ao sistema de permissões — botão "+" visível apenas para usuários com `avisos` habilitado no painel admin.

### Ponto 1.4 — Novas funções CRUD — após linha 1664 (fim do arquivo)
Funções a adicionar:
- `criar_aviso(titulo, corpo, tipo, link, data_expiracao, rodizio, user_id)` → INSERT + chama `criar_notificacoes_para_evento(modulo='avisos', ...)` para notificar sino de todos
- `listar_avisos()` → SELECT todos com contagem de lidos por aviso
- `get_aviso(aviso_id)` → SELECT por ID
- `editar_aviso(aviso_id, campos)` → UPDATE
- `deletar_aviso(aviso_id)` → DELETE + limpa `avisos_usuarios`
- `toggle_aviso(aviso_id, campo, valor)` → UPDATE `ativo` ou `rodizio`
- `get_aviso_proximo(user_id)` → SELECT com filtros: ativo=1, não expirado, rodizio=1, não lido, não exibido hoje, máx 3 exibições/dia, prioridade urgente→prazo→importante→aviso→procedimento→sistema→dica
- `marcar_aviso_lido(aviso_id, user_id)` → INSERT OR REPLACE em `avisos_usuarios` com status='lido'
- `registrar_exibicao_aviso(aviso_id, user_id)` → UPDATE exibicoes_hoje+1, ultima_exibicao_data=hoje

**Dependência crítica:** `criar_aviso()` deve chamar `criar_notificacoes_para_evento()` (linha 1078).
`get_user_permission()` retorna True por padrão se não há registro → todos recebem notificação automaticamente.

---

## 2. `portal.py` — 6 pontos de inserção/alteração

### Ponto 2.1 — Import do blueprint — após linha 65
```python
from blueprints.avisos import avisos_bp
```
Inserir após `from blueprints.anotacoes import anotacoes_bp` (linha 65).

### Ponto 2.2 — Entrada no `MODULES_CONFIG` — após linha 232, antes do `]` na linha 233
```python
{
    'id': 'avisos', 'name': 'Painel de Avisos',
    'desc': 'Gestão de comunicados e avisos para a equipe.',
    'category': 'administracao', 'cat_label': 'Administração',
    'icon': 'megaphone', 'route': 'avisos.index',
    'keywords': 'aviso comunicado painel informação urgente prazo',
    'sidebar': False, 'home': False, 'quick': False,
    'blueprint': 'avisos', 'tool_key': 'avisos',
    'admin_only': False, 'enabled': True,
},
```
`sidebar: False` → não aparece no menu lateral.
`home: False` → não aparece nos cards da Home.
`tool_key: 'avisos'` → conecta ao sistema de permissões.

### Ponto 2.3 — Registro do blueprint — após linha 281
```python
app.register_blueprint(avisos_bp)
```
Inserir após `app.register_blueprint(anotacoes_bp)` (linha 281).

### Ponto 2.4 — `_SKIP_STEPUP` — linha 392
Adicionar `'/api/avisos'` à tupla `_SKIP_STEPUP` (mesma linha que `/api/notificacoes`).
Sem isso, o middleware de step-up Passkey pode interceptar as chamadas do card flutuante.

### Ponto 2.5 — Rotas da API de avisos — após linha 474
Posição: após `api_notificacoes_ler_todas()` (linha 474), antes de `api_dashboard_stats()` (linha 477).
Rotas a inserir no portal.py (acesso público — todos os usuários logados):
```python
# GET  /api/avisos/proximo   → próximo aviso para o card flutuante
# POST /api/avisos/<id>/ler  → marca como lido (botão Entendi)
```
As rotas de gestão CRUD ficam exclusivamente no blueprint `avisos_bp`.

### Ponto 2.6 — `_labelModulo` no JS do sino (base.html, ponto 3.3)
O `_labelModulo()` em base.html (linha 520) precisa de entrada para `'avisos'`. Tratado no ponto 3.3.

---

## 3. `templates/base.html` — 3 pontos de alteração

### Ponto 3.1 — CSS do botão "+" e card flutuante — após linha 308
Posição: após `.notif-empty { ... }` (linha 308), antes do fechamento `</style>`.
CSS a inserir:
- `.avisos-btn` — botão circular vermelho Sigma, 34×34px, `border-radius: 50%`
- `.avisos-badge` — badge branco com borda vermelha, `position: absolute; top:-3px; right:-3px`
- `.aviso-float-card` — `position:fixed; bottom:30px; right:28px; width:340px; border-radius:14px; box-shadow` profunda
- `.aviso-float-topbar` — faixa de cor no topo, 4px de altura, cor dinâmica por tipo
- `.aviso-float-tipo-badge` — badge de tipo no cabeçalho do card
- `.aviso-float-titulo`, `.aviso-float-corpo` — tipografia interna
- `.aviso-float-entendi` — botão primário, cor dinâmica por tipo
- `.aviso-float-x` — botão X no canto superior direito, apenas fecha visualmente

### Ponto 3.2 — Botão "+" na topbar — linha 394
Posição: dentro de `{% if session.get('user_nome') %}` (linha 393), ANTES de `<div class="notif-wrapper"` (linha 395).
```html
{% if 'avisos' in (modules_config | map(attribute='id') | list) %}
<div class="avisos-wrapper">
  <a href="{{ url_for('avisos.index') }}" class="avisos-btn" title="Painel de Avisos">
    <!-- SVG ícone megaphone ou plus -->
  </a>
</div>
{% endif %}
```
`modules_config` já é injetado pelo `inject_modules_config()` existente — filtra por permissão automaticamente.

### Ponto 3.3 — JS do card flutuante — após linha 564
Posição: após o `})();` que fecha o bloco JS do sino (linha 564), antes do `{% endif %}` (linha 566).
Manter dentro do bloco `{% if session.get('user_nome') %}`.
JS a inserir:
- Paleta `TIPOS` com 7 entradas (urgente, importante, aviso, dica, sistema, procedimento, prazo — cores do plano)
- `fetchAvisoProximo()` → GET `/api/avisos/proximo` a cada 60s
- `renderAvisoCard(aviso)` → constrói e exibe o card flutuante
- `fecharCard()` → fade-out + translateY, sem nenhuma chamada de API
- `marcarLido(avisoId)` → POST `/api/avisos/<id>/ler` + fecharCard()
- Event listeners: X → fecharCard() | Entendi → marcarLido()
- Extensão de `_labelModulo`: adicionar `if(m==='avisos')return 'Aviso';`

---

## 4. `blueprints/avisos.py` — arquivo novo

```python
from flask import Blueprint
avisos_bp = Blueprint('avisos', __name__, url_prefix='/avisos', template_folder='../templates')
```

Rotas (gestão admin):
- `GET  /avisos/`           → página de gestão (requer permissão `avisos`)
- `GET  /api/avisos`        → lista avisos (admin)
- `POST /api/avisos`        → cria aviso (admin)
- `PUT  /api/avisos/<id>`   → edita aviso (admin)
- `DELETE /api/avisos/<id>` → exclui aviso (admin)
- `POST /api/avisos/<id>/toggle` → alterna ativo/rodizio (admin)

Rotas (todos os usuários logados — registradas em portal.py, ponto 2.5):
- `GET  /api/avisos/proximo`    → próximo aviso para o card
- `POST /api/avisos/<id>/ler`   → marca como lido (Entendi)

---

## 5. `templates/avisos/index.html` — arquivo novo

Herda de `base.html` (`{% extends 'base.html' %}`).
Padrão idêntico ao `templates/admin/index.html`.
Conteúdo:
- Tabela de avisos: Tipo (badge colorido), Título, Ativo (toggle AJAX), Rodízio (toggle AJAX), Expira em, Ações (editar/excluir)
- Formulário de criação/edição: título, corpo (textarea), tipo (select 7 opções), link, data_expiracao (date), toggles ativo e rodízio
- Todas as interações via fetch/AJAX — sem reload de página

---

## Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Banco na VPS já existe — tabelas não criadas via `init_db()` | Ponto 1.2: `add_coluna_se_necessario()` garante criação idempotente |
| `_SKIP_STEPUP` sem `/api/avisos` — step-up bloqueia card flutuante | Ponto 2.4 resolve |
| `get_user_permission(uid, 'avisos')` sem registro → retorna True por padrão | Todos recebem notificação no sino automaticamente — comportamento desejado |
| `url_for('avisos.index')` sem blueprint registrado quebra todas as páginas | Template usa `{% if %}` antes de chamar url_for — erro isolado |

---

## Sequência segura de implementação

```
1. database.py            → tabelas + CRUD (sem impacto no app em produção)
2. blueprints/avisos.py   → arquivo novo (sem impacto até ser registrado)
3. templates/avisos/      → pasta + index.html novos (sem impacto)
4. portal.py              → import + register + MODULES_CONFIG + rotas API
                             (único ponto de reinício do serviço)
5. base.html              → CSS + botão "+" + JS do card flutuante
                             (apenas visual — não afeta lógica de negócio)
```
