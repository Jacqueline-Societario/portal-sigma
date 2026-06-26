# Plano de Implementação — Painel de Avisos (versão final cirúrgica)
**Portal Societário Sigma | Consolidado em 26/06/2026**
**Status: PRONTO PARA IMPLEMENTAR**

---

## Decisões tomadas

| # | Decisão |
|---|---------|
| 1 | Badge "NOVO" aparece na primeira vez que a usuária vê o aviso, por qualquer caminho (polling ou sino) |
| 2 | Notificações antigas com `link_destino='/avisos'` → clique no sino não faz nada (silêncio total) |
| 3 | Opção B: todos os cards (novo e rodízio) aguardam os slots fixos — 10h, 13h e 16h (horário de Brasília) |
| 4 | Auto-dismiss: card some sozinho após 2h se a usuária não clicar "Entendi" |
| 5 | "Entendi" e auto-dismiss têm o mesmo comportamento: fecham o card e marcam a notificação do sino como lida |
| 6 | Sino abre aviso desativado (`ativo=0`) não deve abrir card nem redirecionar — silêncio total |
| 7 | Campo `corpo` do aviso renderiza HTML (negrito, itálico, sublinhado, parágrafos) — sanitizado no backend |
| 8 | Abertura pelo sino não consome o contador do rodízio diário |
| 9 | Aviso aberto pelo sino não reaparece no rodízio automático do mesmo dia — usuária já viu, comportamento intencional |

---

## Arquivos alterados (ordem obrigatória)

```
0. requirements.txt  → adicionar bleach
1. database.py       → imports, criar_aviso, editar_aviso, get_aviso_proximo, +2 funções novas
2. portal.py         → nova rota /api/avisos/<id>/ver
3. base.html         → CSS (remover X, adicionar badge) + Script 1 (sino) + Script 2 (card)
```

---

## 0. requirements.txt

### P1 — Adicionar bleach (última linha do arquivo)

```
bleach>=6.1.0
```

`bleach` não está no projeto. Sem esta linha, o `import bleach` em `database.py` derruba o servidor na inicialização. Deve ser instalado antes de qualquer restart do serviço:

```bash
pip install "bleach>=6.1.0"
```

Versão atual no PyPI: 6.4.0. O pin `>=6.1.0` instala a mais recente disponível no ambiente sem travar em uma versão específica.

---

## 1. database.py

### D1 — imports · após linha 10 (após `from werkzeug.security import generate_password_hash`)

Inserir as duas linhas:

```python
import bleach
_TAGS_AVISO = ['b', 'strong', 'i', 'em', 'u', 'br', 'p', 'span']
```

`_TAGS_AVISO` é constante global reutilizada por `criar_aviso` (D2) e `editar_aviso` (D3). Nenhum efeito colateral — `bleach` é biblioteca de sanitização, sem side effects no import.

---

### D2 — `criar_aviso` · linhas 1716–1735 — dois subpontos

**D2a — sanitizar `corpo` antes do INSERT (nova linha antes da linha 1719)**

Inserir após `conn = get_db()`:

```python
corpo = bleach.clean(corpo or '', tags=_TAGS_AVISO, attributes={}, strip=True)
```

O parâmetro `corpo` é sobrescrito pela versão sanitizada. O INSERT na linha 1722 usa automaticamente o valor limpo. `attributes={}` remove qualquer atributo (`style`, `class`, `onclick`) das tags permitidas.

**D2b — corrigir `link_destino` · linha 1732**

```python
# Antes:
link_destino='/avisos',

# Depois:
link_destino=f'/api/avisos/{aviso_id}/ver',
```

`aviso_id` existe a partir da linha 1724 (`cur.lastrowid`). A chamada a `criar_notificacoes_para_evento` está na linha 1727 — após o `lastrowid`. Sem risco de referência nula.

**Observação sobre avisos existentes:** avisos criados antes desta alteração têm `link_destino='/avisos'`. O clique no sino para essas notificações cairá no `else if (link && link !== '/avisos')` → silêncio total (Decisão #2). Sem regressão — comportamento atual já levava a "Acesso Negado".

---

### D3 — `editar_aviso` · linhas 1758–1767 — GAP de segurança

O blueprint `avisos.py` chama `database.editar_aviso(corpo=...)` direto (linha 76 do blueprint). Um aviso criado com corpo limpo pode ser reeditado via `PUT /avisos/api/<id>` com payload XSS, sobrescrevendo o banco com conteúdo não sanitizado.

Inserir após a assinatura da função (linha 1759), antes do `conn = get_db()`:

```python
corpo = bleach.clean(corpo or '', tags=_TAGS_AVISO, attributes={}, strip=True)
```

Mesma lógica do D2a. O UPDATE nas linhas 1761–1765 usa o `corpo` já sanitizado.

---

### D4 — `get_aviso_proximo` · linhas 1791–1844 — substituição completa

Substituir tudo desde `_PRIORIDADE_AVISOS = ...` (linha 1791) até o `return dict(rows_sorted[0])` (linha 1844), inclusive:

```python
def get_aviso_proximo(user_id: int) -> dict:
    """
    Retorna o próximo aviso elegível para o card flutuante do usuário, ou None.
    Etapa 1: avisos nunca vistos (novo) — sem limite de 3/dia, prioridade máxima.
    Etapa 2: rodízio — máx 3/dia, round-robin por ultima_exibicao_data.
    Retorna dict com is_novo e notificacao_id inclusos.
    Parâmetros de cada query documentados em linha para evitar dessincronia.
    """
    hoje = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()

    # Etapa 1 — novos (nenhum registro em avisos_usuarios para este usuário)
    # Params: user_id (notif), hoje (expiracao), user_id (NOT IN)
    row = conn.execute(
        '''SELECT a.*,
                  (SELECT n.id FROM notifications n
                   WHERE n.user_id = ?
                     AND n.link_destino = '/api/avisos/' || a.id || '/ver'
                     AND n.lida = 0
                   LIMIT 1) AS notificacao_id
           FROM avisos a
           WHERE a.ativo = 1
             AND a.rodizio = 1
             AND (a.data_expiracao IS NULL OR a.data_expiracao >= ?)
             AND a.id NOT IN (
                 SELECT aviso_id FROM avisos_usuarios WHERE user_id = ?
             )
           ORDER BY CASE a.tipo
               WHEN 'urgente'      THEN 0 WHEN 'prazo'        THEN 1
               WHEN 'importante'   THEN 2 WHEN 'aviso'         THEN 3
               WHEN 'procedimento' THEN 4 WHEN 'sistema'       THEN 5
               WHEN 'dica'         THEN 6 ELSE 7 END,
               a.criado_em DESC
           LIMIT 1''',
        (user_id, hoje, user_id)
    ).fetchone()

    if row:
        conn.close()
        result = dict(row)
        result['is_novo'] = True
        return result

    # Etapa 2 — rodízio (já vistos, máx 3/dia, round-robin)
    total_hoje = conn.execute(
        '''SELECT COALESCE(SUM(exibicoes_hoje), 0) FROM avisos_usuarios
           WHERE user_id = ? AND ultima_exibicao_data = ?''',
        (user_id, hoje)
    ).fetchone()[0]

    if total_hoje >= 3:
        conn.close()
        return None

    # Params: user_id (notif), user_id (JOIN), hoje (expiracao), hoje (ultima_exibicao)
    row = conn.execute(
        '''SELECT a.*,
                  (SELECT n.id FROM notifications n
                   WHERE n.user_id = ?
                     AND n.link_destino = '/api/avisos/' || a.id || '/ver'
                     AND n.lida = 0
                   LIMIT 1) AS notificacao_id
           FROM avisos a
           LEFT JOIN avisos_usuarios au ON au.aviso_id = a.id AND au.user_id = ?
           WHERE a.ativo = 1
             AND a.rodizio = 1
             AND (a.data_expiracao IS NULL OR a.data_expiracao >= ?)
             AND (au.ultima_exibicao_data IS NULL OR au.ultima_exibicao_data < ?)
           ORDER BY CASE a.tipo
               WHEN 'urgente'      THEN 0 WHEN 'prazo'        THEN 1
               WHEN 'importante'   THEN 2 WHEN 'aviso'         THEN 3
               WHEN 'procedimento' THEN 4 WHEN 'sistema'       THEN 5
               WHEN 'dica'         THEN 6 ELSE 7 END,
               COALESCE(au.ultima_exibicao_data, '0000-00-00') ASC
           LIMIT 1''',
        (user_id, user_id, hoje, hoje)
    ).fetchone()

    conn.close()
    if not row:
        return None
    result = dict(row)
    result['is_novo'] = False
    return result
```

**Compatibilidade com `avisos_usuarios`:**
- Schema real: `PRIMARY KEY (aviso_id, user_id)`, colunas `status`, `exibicoes_hoje`, `ultima_exibicao_data` — todas existentes ✓
- Etapa 1 usa `NOT IN (SELECT aviso_id FROM avisos_usuarios WHERE user_id = ?)` — qualquer registro na tabela (inclusive os criados por `registrar_exibicao_aviso`) exclui o aviso de "novo" ✓
- `notificacao_id` via subquery retorna `NULL` para avisos antigos com `link_destino='/avisos'` — sem dano ✓

**`marcar_aviso_lido` e `registrar_exibicao_aviso` são MANTIDOS** — `registrar_exibicao_aviso` ainda é chamado por `api_avisos_proximo` em `portal.py`; `marcar_aviso_lido` ainda é referenciada por `api_avisos_ler`. Remover causaria `AttributeError`.

---

### D5 — nova função `get_aviso_completo_para_user` · inserir após `registrar_exibicao_aviso` (após linha 1884)

```python
def get_aviso_completo_para_user(aviso_id: int, user_id: int) -> dict:
    """
    Retorna aviso com is_novo e notificacao_id para abertura via sino.
    Filtra ativo=1 — aviso desativado retorna None (card não abre).
    Não filtra por rodizio — sino pode abrir qualquer aviso ativo.
    """
    conn = get_db()
    row = conn.execute(
        '''SELECT a.*,
                  CASE WHEN au.aviso_id IS NULL THEN 1 ELSE 0 END AS is_novo,
                  (SELECT n.id FROM notifications n
                   WHERE n.user_id = ?
                     AND n.link_destino = '/api/avisos/' || a.id || '/ver'
                     AND n.lida = 0
                   LIMIT 1) AS notificacao_id
           FROM avisos a
           LEFT JOIN avisos_usuarios au ON au.aviso_id = a.id AND au.user_id = ?
           WHERE a.id = ? AND a.ativo = 1''',
        (user_id, user_id, aviso_id)
    ).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result['is_novo'] = bool(result['is_novo'])
    return result
```

---

### D6 — nova função `marcar_aviso_visto` · inserir após D5

```python
def marcar_aviso_visto(aviso_id: int, user_id: int):
    """
    Marca aviso como visto pela abertura via sino.
    Remove de 'novo' (insere linha em avisos_usuarios) sem incrementar
    exibicoes_hoje — não consome o limite diário do rodízio.
    INSERT OR IGNORE: se já existe registro, não altera nada (idempotente).
    ultima_exibicao_data=hoje exclui o aviso do rodízio automático do mesmo dia
    (Decisão #9 — intencional: usuária já viu, não precisa ver de novo hoje).
    """
    hoje = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    conn.execute(
        '''INSERT OR IGNORE INTO avisos_usuarios
               (aviso_id, user_id, exibicoes_hoje, ultima_exibicao_data)
           VALUES (?, ?, 0, ?)''',
        (aviso_id, user_id, hoje)
    )
    conn.commit()
    conn.close()
```

`INSERT OR IGNORE` é seguro com `PRIMARY KEY (aviso_id, user_id)` — conflito é silenciado, registro existente não é alterado.

---

## 2. portal.py

### P1 — nova rota `GET /api/avisos/<id>/ver` · inserir após linha 506 (após `api_avisos_ler`)

```python
@app.route('/api/avisos/<int:aviso_id>/ver')
def api_avisos_ver(aviso_id):
    if login_obrigatorio():
        return jsonify({'aviso': None}), 200
    uid = session.get('user_id')
    aviso = database.get_aviso_completo_para_user(aviso_id, uid)
    if aviso:
        database.marcar_aviso_visto(aviso_id, uid)
    return jsonify({'aviso': aviso})
```

Rota existente `api_avisos_ler` (linha 500–506, método POST) é **mantida**. Sem conflito de URL: `/ler` é POST, `/ver` é GET.

---

## 3. templates/base.html

### H1 — CSS: remover `.aviso-float-x` · linhas 340–344

Remover estas 5 linhas:

```css
.aviso-float-x {
  background: none; border: none; cursor: pointer; color: var(--muted, #888);
  font-size: 18px; line-height: 1; padding: 0; flex-shrink: 0;
}
.aviso-float-x:hover { color: var(--text, #333); }
```

Botão X não existe mais no HTML do card (Script 2 novo não o gera). CSS órfão não quebra nada, mas gera confusão.

---

### H2 — CSS: adicionar `.aviso-novo-badge` · após linha 361 (após `.aviso-float-entendi:hover`)

```css
.aviso-novo-badge {
  display: inline-block; padding: 1px 7px;
  background: #A72C31; color: #fff;
  border-radius: 99px; font-size: 9px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .5px;
  flex-shrink: 0; margin-left: 6px;
}
```

---

### H3 — Script 1: expor `fetchNotifs` · linha 748 — inserir 1 linha

Após `setInterval(fetchNotifs, 60000);` (linha 748), adicionar:

```javascript
window._sigmaNotifsRefresh = fetchNotifs;
```

Necessário para que `fecharCard()` no Script 2 (IIFE separado) atualize o badge do sino após marcar notificação como lida. Sem esta bridge, `window._sigmaNotifsRefresh` é `undefined` e o sino não reflete o fechamento do card.

---

### H4 — Script 1: substituir handler de clique do sino · linhas 676–683

```javascript
// Substituir o bloco body.querySelectorAll por:
body.querySelectorAll('.notif-item').forEach(function(el) {
  el.addEventListener('click', function() {
    const id   = parseInt(el.dataset.id);
    const link = el.dataset.link;
    fetch('/api/notificacoes/' + id + '/ler', { method: 'POST' })
      .then(function() { fetchNotifs(); });
    if (link && /^\/api\/avisos\/\d+\/ver$/.test(link)) {
      dropdown.classList.remove('open');
      fetch(link)
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(d) {
          if (d && d.aviso) {
            document.dispatchEvent(new CustomEvent('sigma:abrirAviso', {
              detail: { aviso: d.aviso, notificacao_id: id }
            }));
          }
        })
        .catch(function() {});
    } else if (link && link !== '/avisos') {
      window.location.href = link;
    }
    // link === '/avisos' ou vazio → silêncio total (Decisão #2 e #6)
  });
});
```

Nenhum outro trecho do Script 1 é alterado.

---

### H5 — Script 2: substituição completa · linhas 759–837

Substituir o `<script>(function() { ... })();</script>` inteiro. O `{% endif %}` na linha 838 é **mantido**.

Diferenças em relação ao código atual:

| Atual (linhas 759–837) | Novo |
|------------------------|------|
| `_cardAtivo`, `_avisoAtualId` | + `_avisoNotificacaoId`, `_autoDismissTimer` |
| `fecharCard()` só remove DOM | `fecharCard()` captura `notifId`, chama `/api/notificacoes/ler`, atualiza sino |
| `marcarLido()` chama `/api/avisos/<id>/ler` | Removida — `fecharCard()` centraliza tudo |
| Botão X (`avisoFloatX`) no HTML | Sem X — só "Entendi" |
| "Entendi" chama `marcarLido(aviso.id)` | "Entendi" chama `fecharCard()` direto |
| Sem badge "NOVO" | Badge carmim se `aviso.is_novo` |
| `setTimeout(3s)` + `setInterval(60s)` | Slots 10h/13h/16h, `setInterval(5min)` |
| Sem auto-dismiss | `setTimeout(2h)` chama `fecharCard()` |
| Sem listener `sigma:abrirAviso` | Listener para abertura via sino |
| `_esc(aviso.corpo)` (corpo escapado = HTML visível como texto) | `aviso.corpo` raw (seguro — bleach sanitizou no backend) |
| `aviso.tipo` sem escape | `_esc(aviso.tipo)` |

```html
<script>
(function() {
  const TIPOS = {
    urgente:      { bg: '#fee2e2', color: '#b91c1c' },
    importante:   { bg: '#ffedd5', color: '#ea580c' },
    aviso:        { bg: '#fef9c3', color: '#d97706' },
    dica:         { bg: '#dcfce7', color: '#16a34a' },
    sistema:      { bg: '#dbeafe', color: '#2563eb' },
    procedimento: { bg: '#ede9fe', color: '#7c3aed' },
    prazo:        { bg: '#fce7f3', color: '#db2777' },
  };

  const _SLOTS = [10, 13, 16];  // horários de Brasília
  let _cardAtivo          = false;
  let _avisoAtualId       = null;
  let _avisoNotificacaoId = null;
  let _autoDismissTimer   = null;

  // ── Tempo Brasília (UTC-3, sem horário de verão desde 2019) ──────────────
  function _horaBrasilia() {
    return parseInt(new Intl.DateTimeFormat('pt-BR', {
      timeZone: 'America/Sao_Paulo', hour: 'numeric', hour12: false
    }).format(new Date()), 10);
  }
  function _minutoBrasilia() {
    return parseInt(new Intl.DateTimeFormat('pt-BR', {
      timeZone: 'America/Sao_Paulo', minute: 'numeric'
    }).format(new Date()), 10);
  }
  function _dataHojeBrasilia() {
    return new Intl.DateTimeFormat('sv-SE', {
      timeZone: 'America/Sao_Paulo'
    }).format(new Date());  // retorna YYYY-MM-DD
  }

  // ── Controle de slots (localStorage por dia) ─────────────────────────────
  function _slotKey(hora) {
    return 'sigma_slot_' + _dataHojeBrasilia() + '_' + hora;
  }
  function _marcarSlotAtual() {
    const h = _horaBrasilia();
    if (_SLOTS.includes(h)) localStorage.setItem(_slotKey(h), '1');
  }
  function _deveDispararSlot() {
    const h = _horaBrasilia();
    const m = _minutoBrasilia();
    return _SLOTS.includes(h) && m < 15 && !localStorage.getItem(_slotKey(h));
  }

  // ── Fechamento do card (centraliza tudo: Entendi + auto-dismiss + sino) ──
  function fecharCard() {
    clearTimeout(_autoDismissTimer);
    _autoDismissTimer = null;

    const notifId = _avisoNotificacaoId;  // capturar antes de limpar
    _cardAtivo          = false;
    _avisoAtualId       = null;
    _avisoNotificacaoId = null;

    if (notifId) {
      fetch('/api/notificacoes/' + notifId + '/ler', { method: 'POST' })
        .then(function() {
          if (window._sigmaNotifsRefresh) window._sigmaNotifsRefresh();
        });
    }

    const c = document.getElementById('avisoFloatCard');
    if (!c) return;
    c.style.transition = 'opacity .2s, transform .2s';
    c.style.opacity    = '0';
    c.style.transform  = 'translateY(16px)';
    setTimeout(function() { c && c.remove(); }, 220);
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Renderização do card ─────────────────────────────────────────────────
  function renderAvisoCard(aviso) {
    if (_cardAtivo) return;
    _cardAtivo          = true;
    _avisoAtualId       = aviso.id;
    _avisoNotificacaoId = aviso.notificacao_id || null;

    const t        = TIPOS[aviso.tipo] || { bg: '#f3f4f6', color: '#374151' };
    const badgeNovo = aviso.is_novo
      ? '<span class="aviso-novo-badge">NOVO</span>'
      : '';

    const card = document.createElement('div');
    card.id        = 'avisoFloatCard';
    card.className = 'aviso-float-card';
    card.innerHTML = `
      <div class="aviso-float-topbar" style="background:${t.color};"></div>
      <div class="aviso-float-inner">
        <div class="aviso-float-head">
          <span class="aviso-float-tipo-badge"
                style="background:${t.bg};color:${t.color};">${_esc(aviso.tipo)}</span>
          ${badgeNovo}
        </div>
        <div class="aviso-float-titulo">${_esc(aviso.titulo)}</div>
        ${aviso.corpo ? `<div class="aviso-float-corpo">${aviso.corpo}</div>` : ''}
        <div class="aviso-float-footer">
          ${aviso.link
            ? `<a href="${_esc(aviso.link)}" target="_blank"
                  class="aviso-float-link">Saiba mais</a>`
            : '<span></span>'}
          <button class="aviso-float-entendi" id="avisoFloatEntendi"
                  style="background:${t.color};">Entendi</button>
        </div>
      </div>`;

    document.body.appendChild(card);
    // "Entendi" chama fecharCard diretamente — sem função intermediária
    document.getElementById('avisoFloatEntendi')
      .addEventListener('click', fecharCard);

    // Auto-dismiss: card some sozinho após 2h (mesmas regras do Entendi)
    _autoDismissTimer = setTimeout(fecharCard, 2 * 3600 * 1000);
  }

  // ── Fetch do próximo aviso ───────────────────────────────────────────────
  async function fetchAvisoProximo() {
    if (_cardAtivo) return;
    try {
      const r = await fetch('/api/avisos/proximo');
      const d = await r.json();
      if (d.aviso) {
        _marcarSlotAtual();
        renderAvisoCard(d.aviso);
      }
    } catch(e) {}
  }

  // ── Abertura via clique no sino ──────────────────────────────────────────
  document.addEventListener('sigma:abrirAviso', function(e) {
    const a = Object.assign({}, e.detail.aviso, {
      notificacao_id: e.detail.notificacao_id
    });
    renderAvisoCard(a);
  });

  // ── Disparo por slots ────────────────────────────────────────────────────
  // Verificar na abertura da página (caso esteja dentro de um slot)
  if (_deveDispararSlot()) setTimeout(fetchAvisoProximo, 3000);

  // Verificar a cada 5 minutos
  setInterval(function() {
    if (_deveDispararSlot()) fetchAvisoProximo();
  }, 5 * 60 * 1000);

})();
</script>
{% endif %}
```

---

## Mapa de impacto consolidado

| Arquivo | Ponto | Localização atual | Tipo | Motivo |
|---------|-------|-------------------|------|--------|
| `requirements.txt` | P1 | última linha | +1 linha | `bleach>=6.1.0` |
| `database.py` | D1 | linha 10 (após imports) | +2 linhas | `import bleach` + `_TAGS_AVISO` |
| `database.py` | D2a | `criar_aviso` linha 1718 | +1 linha | `bleach.clean()` no corpo |
| `database.py` | D2b | `criar_aviso` linha 1732 | 1 linha alterada | `link_destino` com aviso_id |
| `database.py` | D3 | `editar_aviso` linha 1759 | +1 linha | `bleach.clean()` no corpo (gap de segurança) |
| `database.py` | D4 | linhas 1791–1844 | Reescrita (~54 linhas) | Lógica novo/rodízio + is_novo + notificacao_id |
| `database.py` | D5 | após linha 1884 | +20 linhas (nova função) | `get_aviso_completo_para_user` |
| `database.py` | D6 | após D5 | +16 linhas (nova função) | `marcar_aviso_visto` |
| `portal.py` | P1 | após linha 506 | +8 linhas (nova rota) | `GET /api/avisos/<id>/ver` |
| `base.html` | H1 | linhas 340–344 | 5 linhas removidas | CSS `.aviso-float-x` (botão X eliminado) |
| `base.html` | H2 | após linha 361 | +7 linhas | CSS `.aviso-novo-badge` |
| `base.html` | H3 | linha 748 | +1 linha | `window._sigmaNotifsRefresh = fetchNotifs` |
| `base.html` | H4 | linhas 676–683 | ~15 linhas alteradas | Handler sino: abre card, silencia `/avisos` |
| `base.html` | H5 | linhas 759–837 | Reescrita (~79 → ~107 linhas) | Slots, auto-dismiss, fecharCard unificado |

---

## Comportamento resultante

```
Slot dispara (10h/13h/16h, dentro de 15min)
  → fetchAvisoProximo()
  → Etapa 1: aviso nunca visto? → retorna is_novo=True
  → Etapa 2: se não → rodízio (máx 3/dia, round-robin por ultima_exibicao_data)
  → card abre → slot marcado no localStorage

Card visível:
  → "Entendi" ou auto-dismiss (2h) → fecharCard()
  → marca notificação sino como lida → atualiza badge do sino

Clique no sino (notificação nova):
  → link = /api/avisos/<id>/ver
  → fetch → renderAvisoCard (is_novo calculado por usuária)
  → marcar_aviso_visto (não consome rodízio, não reaparece no mesmo dia)

Clique no sino (notificação antiga):
  → link = /avisos → silêncio total

Aviso desativado:
  → get_aviso_completo_para_user filtra ativo=1 → retorna None → card não abre
```

---

## Checklist pós-deploy

```
[ ] pip install "bleach>=6.1.0" executado antes do restart
[ ] Criar aviso novo → notificação no sino tem link /api/avisos/<id>/ver
[ ] Abrir portal entre 10h00 e 10h14 → card aparece em 3s
[ ] Abrir portal às 10h16 → card NÃO aparece (slot fechado)
[ ] Card novo → badge carmim "NOVO" visível
[ ] "Entendi" → card fecha + badge do sino diminui imediatamente
[ ] Não clicar "Entendi" → card some após 2h + badge do sino diminui
[ ] Recarregar página após ver card das 10h → slot 10h não dispara de novo
[ ] Clicar notificação nova no sino → card abre (não navega)
[ ] Clicar notificação antiga (link=/avisos) → nada acontece
[ ] Abrir 3 avisos diferentes pelo sino → rodízio automático ainda funciona no mesmo dia
[ ] Desativar aviso → clique no sino não abre card
[ ] Aviso com negrito/itálico → renderiza formatado no card
[ ] Aviso com <script> no corpo → não executa (bleach removeu na criação e na edição)
[ ] Três cards de rodízio vistos no mesmo dia → 16h não mostra nada (limite atingido)
[ ] Editar aviso com corpo XSS → corpo sanitizado ao salvar (testar via PUT /avisos/api/<id>)
```
