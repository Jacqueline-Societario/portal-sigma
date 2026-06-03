"""
blueprints/empresas.py — Consulta de Empresas
Carrega dados da planilha Google Sheets de Controle de Processos.
Cada aba tem estrutura de colunas diferente.
"""
import json
import os
import re
import sqlite3
import unicodedata
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file, flash

from blueprints.auth import login_obrigatorio
import database

empresas_bp = Blueprint('empresas', __name__, url_prefix='/empresas')

# Planilha de backup (fonte única de importação/exportação)
BACKUP_SHEET_ID = '1siFTiFhEkge-8EoNlykI9QOF8kN6fQTgtBdsUPhIUBE'

# Aba principal de sincronização (deve coincidir com backup_sheets.ABA_CONSOLIDADA)
ABA_CONSOLIDADA = 'Consolidada'

# Caminho relativo ao diretório do projeto (funciona local e na VPS)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(_BASE_DIR, 'credentials', 'token.json')

# Abas válidas do banco (usadas nos filtros da interface)
ABAS_LISTA = ['ATIVAS', 'INATIVAS', 'NÃO MENSAIS']

# Campos com filtros dinâmicos (gerados a partir dos valores reais do banco)
CAMPOS_FILTRO = [
    'municipio', 'responsavel', 'atuacao', 'escritorio',
    'procuracao', 'cnes', 'visa', 'tpi', 'publicidade',
    'licenca_ambiental', 'alvara_funcionamento',
    'venc_bombeiro', 'prot_bombeiro', 'certificado_digital',
]

LABELS_FILTRO = {
    'municipio':            'Município',
    'responsavel':          'Responsável',
    'atuacao':              'Atuação',
    'escritorio':           'Escritório',
    'procuracao':           'Procuração',
    'cnes':                 'CNES',
    'visa':                 'VISA',
    'tpi':                  'TPI',
    'publicidade':          'Publicidade',
    'licenca_ambiental':    'Lic. Ambiental',
    'alvara_funcionamento': 'Alvará',
    'venc_bombeiro':        'Bombeiro — Vencimento',
    'prot_bombeiro':        'Bombeiro — Protocolo',
    'certificado_digital':  'Certificado Digital',
}

# Campos sem contador (para preservar privacidade da equipe)
SEM_CONTADOR = {'responsavel'}

# Campos documentais (usados para classificação e relatório)
CAMPOS_DOCUMENTAIS = [
    'alvara_funcionamento', 'visa', 'cnes', 'licenca_ambiental',
    'publicidade', 'tpi', 'procuracao', 'venc_bombeiro', 'prot_bombeiro',
    'certificado_digital',
]

# Campos principais para avaliar completude
CAMPOS_PRINCIPAIS = ['nome_empresa', 'cnpj_cpf', 'municipio', 'escritorio', 'responsavel', 'atuacao', 'aba']

# Palavras que não são nomes de município (para filtrar dropdown)
_NAO_MUNICIPIO = re.compile(
    r'^\d{1,2}/\d{1,2}/\d{2,4}$|'          # datas
    r'^\d{4}-\d{2}-\d{2}$|'                  # datas ISO
    r'^(VENCIDO|ISENTO|PENDENTE|EM ANDAMENTO|ARQUIVADO|'
    r'FALTA PAGAMENTO|VIDE COMENTÁRIO|NÃO POSSUI|DEFERIDO|'
    r'PAGANTE|OUTUBRO|SETEMBRO|BLOQUEADO|BLOQUEIO|'
    r'EMBARGO IPTU|EMBARGO|SIM|NÃO|NAO|'
    r'JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|'
    r'JULHO|AGOSTO|NOVEMBRO|DEZEMBRO|'
    r'SAÍDA|SAIDA|BAIXADA|BAIXA|PARALISADA|PARALISAÇÃO|'
    r'IRREGULAR|REGULAR|OK|VIGENTE|VENCENDO)$',
    re.IGNORECASE
)


def _normalizar(s: str) -> str:
    """Remove acentos, cedilha e converte para minúsculas para busca."""
    if not s:
        return ''
    nfkd = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')


def _normalizar_cnpj(s: str) -> str:
    """Remove pontos, traços e barras do CNPJ/CPF."""
    return re.sub(r'[.\-/\s]', '', s.strip()) if s else ''


def classificar_campo(nome_campo, valor):
    """Classifica o valor de um campo documental em categoria padronizada.

    Regra fundamental: sem data válida, nunca classifica como Vencido.
    """
    if not valor or not str(valor).strip() or str(valor).strip() in ('—', '-', ''):
        return 'Sem informação'

    v = str(valor).strip()
    vl = v.upper()

    # Isento / Dispensado
    if any(k in vl for k in ('ISENTO', 'DISPENS', 'NÃO APLICA', 'NAO APLICA')):
        return 'Isento'

    # Não possui
    if 'NÃO POSSUI' in vl or 'NAO POSSUI' in vl:
        return 'Não possui'

    # Em andamento / Protocolo — verificar antes de datas
    if any(k in vl for k in ('ANDAMENTO', 'AGUARDANDO', 'PROTOCOLO', 'EMISS')):
        return 'Em andamento'
    if re.search(r'\bprot\.?\b', v, re.IGNORECASE):
        return 'Em andamento'
    # Padrão "XXXXXX/AAAA" típico de protocolo
    if re.match(r'^\d{4,}/\d{4}$', v):
        return 'Em andamento'

    # Válido indeterminado
    if any(k in vl for k in ('INDETERMIN', 'SEM VALIDADE', 'INDEFINID',
                              'VÁLIDO INDET', 'VALIDO INDET', 'SEM VENCIM')):
        return 'Válido indeterminado'
    if any(k in vl for k in ('OK', 'VIGENTE', 'REGULAR', 'VÁLIDO', 'VALIDO', 'DEFERIDO')):
        return 'Válido indeterminado'

    # Verificar data
    hoje = date.today()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(v[:10], fmt).date()
            if dt < hoje:
                return 'Vencido'
            elif dt <= hoje + timedelta(days=30):
                return 'A vencer — 30 dias'
            elif dt <= hoje + timedelta(days=60):
                return 'A vencer — 60 dias'
            elif dt <= hoje + timedelta(days=90):
                return 'A vencer — 90 dias'
            else:
                return 'A vencer'
        except Exception:
            pass

    # Número puro solto sem data clara → não classifica como vencido
    if re.match(r'^\d+$', v):
        return 'Informação não classificada'

    # Texto confuso
    return 'Revisar cadastro'


def _get_token():
    """Obtém token de acesso Google OAuth2 sem depender de google-auth.
    Usa apenas urllib.request (stdlib) para renovar via refresh_token."""
    try:
        with open(TOKEN_PATH) as f:
            data = json.load(f)

        # Verificar se o token atual ainda é válido
        from datetime import timezone
        expiry_str = data.get('expiry') or data.get('token_expiry', '')
        token_valido = False
        if expiry_str and data.get('access_token'):
            try:
                from datetime import datetime
                # Remove microseconds extras se houver
                exp = expiry_str[:26].rstrip('Z')
                if '+' in exp:
                    exp = exp.split('+')[0]
                exp_dt = datetime.fromisoformat(exp).replace(tzinfo=timezone.utc)
                agora = datetime.now(timezone.utc)
                token_valido = exp_dt > agora
            except Exception:
                token_valido = False

        if token_valido:
            return data['access_token']

        # Renovar via refresh_token
        refresh_token = data.get('refresh_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        token_uri = data.get('token_uri', 'https://oauth2.googleapis.com/token')

        if not refresh_token:
            raise RuntimeError('refresh_token ausente no token.json')

        payload = urllib.parse.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }).encode()

        req = urllib.request.Request(token_uri, data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        resp = urllib.request.urlopen(req, timeout=15)
        novo = json.loads(resp.read())

        if 'access_token' not in novo:
            raise RuntimeError(f'Resposta inesperada: {novo}')

        # Salvar token renovado
        data['access_token'] = novo['access_token']
        from datetime import datetime, timedelta, timezone as _tz
        exp_novo = datetime.now(_tz.utc) + timedelta(seconds=novo.get('expires_in', 3600))
        data['expiry'] = exp_novo.isoformat()
        with open(TOKEN_PATH, 'w') as fw:
            json.dump(data, fw, indent=2)

        return novo['access_token']

    except Exception as e:
        raise RuntimeError(f'Erro ao obter token Google: {e}')


def sincronizar_planilha():
    """Importa dados da aba 'Consolidada' da planilha de backup para o SQLite."""
    token = _get_token()

    rng = urllib.parse.quote(f"{ABA_CONSOLIDADA}!A2:X")
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{BACKUP_SHEET_ID}/values/{rng}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req, timeout=20)
    data = json.loads(resp.read())
    rows = data.get('values', [])

    # Proteção: nunca apagar o banco se a planilha retornou vazia ou com muito poucos dados.
    if not rows:
        raise RuntimeError(
            'Planilha retornou 0 linhas — importação cancelada para proteger os dados do banco.'
        )
    if len(rows) < 5:
        raise RuntimeError(
            f'Planilha retornou apenas {len(rows)} linha(s). '
            'Mínimo de 5 linhas exigido para prosseguir com a importação.'
        )

    conn = database.get_db()
    cur = conn.cursor()
    try:
        cur.execute('BEGIN')
        cur.execute('DELETE FROM empresas_planilha')

        total = 0
        for row in rows:
            def g(i, _row=row):
                return _row[i].strip() if i < len(_row) and _row[i] else ''

            nome = g(1)
            if not nome:
                continue

            cnpj = g(2)
            aba = g(3) or 'ATIVAS'

            cur.execute('''INSERT INTO empresas_planilha
                (fluxo, cnpj_cpf, nome_empresa, atuacao, escritorio, municipio,
                 visa, cnes, venc_bombeiro, prot_bombeiro, licenca_ambiental,
                 alvara_funcionamento, publicidade, tpi, procuracao, motivo_inativa,
                 codigo_dominio, responsavel, observacoes,
                 nome_normalizado, cnpj_normalizado, aba,
                 atualizado_em, editado_em, editado_por, certificado_digital)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                ('', cnpj, nome,
                 g(4), g(5), g(6),
                 g(10), g(11), g(12), g(13), g(14),
                 g(15), g(16), g(17), g(9), g(18),
                 g(7), g(8), g(19),
                 _normalizar(nome), _normalizar_cnpj(cnpj), aba,
                 g(20) or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 g(21) or None, g(22), g(23))
            )
            total += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return total, []


def _status_cor(valor):
    """Retorna classe CSS baseada no valor do campo."""
    if not valor or valor.strip() == '':
        return 'vazio'
    v = valor.upper().strip()
    if v in ('ISENTO', 'NÃO POSSUI', 'NÃO APLICÁVEL', '-'):
        return 'isento'
    if 'VENCID' in v or 'IRREGULAR' in v or 'PENDENTE' in v:
        return 'vencido'
    if 'ANDAMENTO' in v or 'AGUARDANDO' in v or 'TEM TAREFA' in v:
        return 'andamento'
    # Verificar se é data e se está vencida
    for fmt in ('%d/%m/%Y', '%d/%m/%y'):
        try:
            dt = datetime.strptime(v, fmt).date()
            hoje = date.today()
            if dt < hoje:
                return 'vencido'
            if dt <= hoje + timedelta(days=90):
                return 'vencendo'
            return 'ok'
        except Exception:
            pass
    return 'ok'


def _build_query(q, aba, filtros):
    """Constrói SQL e params para consulta de empresas.

    filtros: dict campo -> lista de valores (strings, podendo incluir '__vazio__').
    """
    sql = 'SELECT * FROM empresas_planilha WHERE 1=1'
    params = []

    if aba:
        sql += ' AND aba = ?'
        params.append(aba)

    if q:
        q_norm = _normalizar(q)
        q_cnpj = _normalizar_cnpj(q)
        sql += (' AND (nome_normalizado LIKE ? OR cnpj_normalizado LIKE ?'
                ' OR nome_empresa LIKE ? OR municipio LIKE ?'
                ' OR responsavel LIKE ? OR codigo_dominio LIKE ?)')
        params += [f'%{q_norm}%', f'%{q_cnpj}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%']

    for campo in CAMPOS_FILTRO:
        valores = filtros.get(campo, [])
        if not valores:
            continue
        tem_vazio = '__vazio__' in valores
        valores_reais = [v for v in valores if v and v != '__vazio__']

        partes = []
        if tem_vazio:
            partes.append(f'({campo} = "" OR {campo} IS NULL)')
        if len(valores_reais) == 1:
            partes.append(f'{campo} = ?')
            params.append(valores_reais[0])
        elif len(valores_reais) > 1:
            placeholders = ','.join('?' * len(valores_reais))
            partes.append(f'{campo} IN ({placeholders})')
            params.extend(valores_reais)

        if partes:
            sql += ' AND (' + ' OR '.join(partes) + ')'

    return sql, params


# ─── Rotas ────────────────────────────────────────────────────────────────────

@empresas_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    q = request.args.get('q', '').strip()
    aba_param = request.args.get('aba')  # None se ausente da URL, '' se ?aba=
    aba = (aba_param if aba_param is not None else 'ATIVAS').strip()

    # Filtros dinâmicos — agora aceitam múltiplos valores via getlist
    filtros = {c: request.args.getlist(c) for c in CAMPOS_FILTRO}

    # Se há busca de texto, pesquisa em todas as abas por padrão
    if q and aba_param is None:
        aba = ''

    conn = database.get_db()

    total_row = conn.execute('SELECT COUNT(*) FROM empresas_planilha').fetchone()
    total = total_row[0] if total_row else 0

    ultima_sync = None
    sync_row = conn.execute(
        'SELECT atualizado_em FROM empresas_planilha ORDER BY atualizado_em DESC LIMIT 1'
    ).fetchone()
    if sync_row:
        ultima_sync = sync_row[0][:16]

    # Opções dinâmicas: valores distintos do banco
    opcoes = {}
    opcoes_tem_vazio = {}
    contadores = {}
    for campo in CAMPOS_FILTRO:
        rows = conn.execute(
            f'SELECT DISTINCT {campo} FROM empresas_planilha ORDER BY {campo}'
        ).fetchall()
        vals = []
        tem_vazio = False
        for r in rows:
            v = r[0]
            if v is None or v == '':
                tem_vazio = True
            else:
                vals.append(v)
        opcoes[campo] = vals
        opcoes_tem_vazio[campo] = tem_vazio

        # Contadores: número de empresas por valor (exceto 'responsavel')
        if campo not in SEM_CONTADOR:
            cnt_rows = conn.execute(
                f'SELECT {campo}, COUNT(*) FROM empresas_planilha '
                f'WHERE {campo} IS NOT NULL AND {campo} != "" GROUP BY {campo}'
            ).fetchall()
            contadores[campo] = {r[0]: r[1] for r in cnt_rows}
        else:
            contadores[campo] = {}

    n_filtros = sum(1 for vals in filtros.values() if vals)

    # Filtros de classificação (class_*) — aplicados em memória após SQL
    active_class = {}
    for campo in CAMPOS_DOCUMENTAIS:
        val = request.args.get(f'class_{campo}', '').strip()
        if val:
            active_class[campo] = val

    # tem_filtros: True se algum filtro explícito está ativo (para mostrar Resumo da Seleção)
    tem_filtros = (bool(q) or n_filtros > 0
                   or bool(active_class)
                   or (aba_param is not None and bool(aba_param.strip())))

    # Busca: TODOS os resultados filtrados (base para resumo, total real e paginação)
    sql, params = _build_query(q, aba, filtros)
    sql += ' ORDER BY nome_empresa'
    empresas_todas = conn.execute(sql, params).fetchall()
    conn.close()

    # Filtro class_* em memória (classificação calculada no Python)
    if active_class:
        def _pass_class(e):
            for campo, cat in active_class.items():
                try:
                    val = e[campo]
                except Exception:
                    val = ''
                if classificar_campo(campo, val) != cat:
                    return False
            return True
        empresas_todas = [e for e in empresas_todas if _pass_class(e)]

    total_filtrado = len(empresas_todas)

    # Paginação — 150 por página; busca e filtros já aplicados acima
    PER_PAGE = 150
    try:
        page = max(1, int(request.args.get('page', 1) or 1))
    except (ValueError, TypeError):
        page = 1
    total_pages = (total_filtrado + PER_PAGE - 1) // PER_PAGE if total_filtrado > 0 else 1
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE
    empresas = empresas_todas[offset:offset + PER_PAGE]

    # URL base para links de paginação (todos os params atuais, exceto 'page')
    base_params = [(k, v) for k in request.args if k != 'page' for v in request.args.getlist(k)]
    base_query = urllib.parse.urlencode(base_params)

    # Resumo documental por campo (calculado sobre TODA a seleção filtrada, não só a página)
    resumo = {}
    if tem_filtros:
        for campo in CAMPOS_DOCUMENTAIS:
            cnt = {}
            for e in empresas_todas:
                try:
                    val = e[campo]
                except Exception:
                    val = ''
                cat = classificar_campo(campo, val)
                cnt[cat] = cnt.get(cat, 0) + 1
            if cnt:
                resumo[campo] = cnt

    # Data/hora do último backup bem-sucedido
    ultimo_backup_ok = None
    try:
        _cfg_path = os.path.join(_BASE_DIR, 'backup_config.json')
        with open(_cfg_path) as _f:
            _cfg = json.load(_f)
        if _cfg.get('ultimo_backup_status') == 'sucesso':
            ultimo_backup_ok = _cfg.get('ultimo_backup', '')
    except Exception:
        pass

    return render_template('empresas/index.html',
        empresas=empresas,
        q=q,
        aba=aba,
        filtros=filtros,
        opcoes=opcoes,
        opcoes_tem_vazio=opcoes_tem_vazio,
        contadores=contadores,
        sem_contador=SEM_CONTADOR,
        labels=LABELS_FILTRO,
        campos_filtro=CAMPOS_FILTRO,
        n_filtros=n_filtros,
        total=total,
        total_filtrado=total_filtrado,
        page=page,
        total_pages=total_pages,
        per_page=PER_PAGE,
        base_query=base_query,
        ultima_sync=ultima_sync,
        ultimo_backup_ok=ultimo_backup_ok,
        abas=ABAS_LISTA,
        status_cor=_status_cor,
        classificar=classificar_campo,
        badge_cls=_badge_cls,
        tem_filtros=tem_filtros,
        resumo=resumo,
        campos_documentais=CAMPOS_DOCUMENTAIS,
        active_class=active_class,
    )


@empresas_bp.route('/sincronizar', methods=['POST'])
def sincronizar():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if not session.get('is_admin'):
        return jsonify({'erro': 'Apenas administradores podem importar da planilha'}), 403
    try:
        total, erros = sincronizar_planilha()
        msg = f'{total} empresas sincronizadas.'
        if erros:
            msg += ' Erros: ' + '; '.join(erros)
        return jsonify({'sucesso': True, 'mensagem': msg, 'total': total})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@empresas_bp.route('/nova', methods=['GET', 'POST'])
def nova():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    if not session.get('is_admin') and not database.get_user_permission(
        session.get('user_id'), 'empresas_editar'
    ):
        return redirect(url_for('empresas.index'))

    erro = None
    dados = None

    if request.method == 'POST':
        dados = request.form.to_dict()
        nome = dados.get('nome_empresa', '').strip()
        if not nome:
            erro = 'O nome da empresa é obrigatório.'
        else:
            criado_por = session.get('user_nome', str(session.get('user_id', '')))
            empresa_id = database.criar_empresa(dados, criado_por=criado_por)
            database.criar_notificacoes_para_evento(
                modulo='empresas',
                tipo_evento='empresa_nova',
                titulo=f'Nova empresa cadastrada — {nome}',
                link_destino=f'/empresas/{empresa_id}',
                excluir_user_id=session.get('user_id'),
            )
            return redirect(url_for('empresas.detalhe', empresa_id=empresa_id))

    return render_template('empresas/nova.html', erro=erro, dados=dados)


@empresas_bp.route('/<int:empresa_id>')
def detalhe(empresa_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    conn = database.get_db()
    empresa = conn.execute(
        'SELECT * FROM empresas_planilha WHERE id = ?', (empresa_id,)
    ).fetchone()
    conn.close()
    if not empresa:
        return redirect(url_for('empresas.index'))
    pode_editar = session.get('is_admin') or database.get_user_permission(
        session.get('user_id'), 'empresas_editar'
    )
    return render_template('empresas/detalhe.html', empresa=empresa,
                           status_cor=_status_cor, pode_editar=pode_editar,
                           abas_lista=['ATIVAS', 'INATIVAS', 'NÃO MENSAIS'])


@empresas_bp.route('/<int:empresa_id>/editar', methods=['POST'])
def editar(empresa_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    if not session.get('is_admin') and not database.get_user_permission(user_id, 'empresas_editar'):
        return jsonify({'erro': 'Sem permissão para editar'}), 403

    dados = request.get_json() or {}

    # Detectar mudança de classificação (aba) para notificação
    aba_antiga = None
    nome_empresa = None
    if 'aba' in dados:
        conn = database.get_db()
        emp = conn.execute(
            'SELECT nome_empresa, aba FROM empresas_planilha WHERE id=?', (empresa_id,)
        ).fetchone()
        conn.close()
        if emp:
            aba_antiga = emp['aba']
            nome_empresa = emp['nome_empresa']

    editado_por = session.get('user_nome', str(user_id))
    ok = database.update_empresa(empresa_id, dados, editado_por=editado_por)
    if not ok:
        return jsonify({'erro': 'Nenhum campo para atualizar'}), 400

    # Notificar mudança de classificação
    if aba_antiga and dados.get('aba') and dados['aba'] != aba_antiga and nome_empresa:
        database.criar_notificacoes_para_evento(
            modulo='empresas',
            tipo_evento='classificacao_alterada',
            titulo=f'Classificação alterada — {nome_empresa}',
            descricao=f'{aba_antiga} → {dados["aba"]}',
            link_destino=f'/empresas/{empresa_id}',
            excluir_user_id=user_id,
        )

    return jsonify({'sucesso': True})


def gravar_planilha():
    """Exporta dados do banco para a aba 'Consolidada' da planilha de backup."""
    from backup_sheets import executar_backup
    ok, _sid, total = executar_backup()
    if not ok:
        raise RuntimeError('Falha ao executar backup — verifique backup.log')
    return total, 0


@empresas_bp.route('/gravar-sheets', methods=['POST'])
def gravar_sheets():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if not session.get('is_admin'):
        return jsonify({'erro': 'Apenas administradores podem gravar na planilha'}), 403
    try:
        total, cells = gravar_planilha()
        return jsonify({'sucesso': True, 'mensagem': f'{total} empresas exportadas para a planilha.', 'total': total})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ─── Exportação Excel ─────────────────────────────────────────────────────────


def _badge_cls(classificacao):
    """Retorna classe CSS para badge de classificação documental no template."""
    cl = classificacao or ''
    if cl == 'Vencido':
        return 'dbadge-vencido'
    if 'A vencer — 30' in cl:
        return 'dbadge-avencer30'
    if 'A vencer — 60' in cl or 'A vencer — 90' in cl:
        return 'dbadge-avencer'
    if 'A vencer' in cl:
        return 'dbadge-valido'
    if 'Válido' in cl or 'indetermin' in cl.lower():
        return 'dbadge-valido'
    if 'andamento' in cl.lower():
        return 'dbadge-andamento'
    if cl in ('Isento', 'Não possui'):
        return 'dbadge-isento'
    if cl in ('Revisar cadastro', 'Informação não classificada'):
        return 'dbadge-revisar'
    return 'dbadge-vazio'


def _badge_color(classificacao):
    """Retorna cor hex para célula Excel baseada na classificação."""
    mapa = {
        'Vencido':            'FEE2E2',
        'A vencer — 30 dias': 'FEF3C7',
        'A vencer — 60 dias': 'FEF9C3',
        'A vencer — 90 dias': 'FEFCE8',
        'A vencer':           'D1FAE5',
        'Válido indeterminado': 'DBEAFE',
        'Em andamento':       'DBEAFE',
        'Isento':             'F3F4F6',
        'Não possui':         'F3F4F6',
        'Sem informação':     'F9FAFB',
        'Revisar cadastro':   'FFF7ED',
        'Informação não classificada': 'FFF7ED',
    }
    return mapa.get(classificacao, 'FFFFFF')


@empresas_bp.route('/exportar-excel')
def exportar_excel():
    """Exporta lista simples das empresas filtradas para Excel.
    Disponível para qualquer usuário autenticado.
    """
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    try:
        import xlsxwriter
        from io import BytesIO
    except ImportError:
        return redirect(url_for('empresas.index'))

    q = request.args.get('q', '').strip()
    aba = request.args.get('aba', '').strip()
    filtros = {c: request.args.getlist(c) for c in CAMPOS_FILTRO}

    # Filtros de classificação (class_*) — aplicados em memória após SQL
    active_class_exp = {}
    for campo in CAMPOS_DOCUMENTAIS:
        val = request.args.get(f'class_{campo}', '').strip()
        if val:
            active_class_exp[campo] = val

    conn = database.get_db()
    sql, params = _build_query(q, aba, filtros)
    sql += ' ORDER BY nome_empresa'
    empresas_raw = conn.execute(sql, params).fetchall()
    conn.close()

    if active_class_exp:
        def _pass_ce(e):
            for campo, cat in active_class_exp.items():
                try:
                    v = e[campo]
                except Exception:
                    v = ''
                if classificar_campo(campo, v) != cat:
                    return False
            return True
        empresas = [e for e in empresas_raw if _pass_ce(e)]
    else:
        empresas = empresas_raw

    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet('Empresas')

    hdr_fmt = wb.add_format({
        'bold': True, 'font_color': 'FFFFFF', 'bg_color': 'A72C31',
        'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        'border': 1, 'border_color': 'CCCCCC',
    })
    cell_fmt = wb.add_format({'valign': 'vcenter', 'border': 1, 'border_color': 'E5E7EB'})

    _color_fmts = {}
    for hex_c in ['FEE2E2', 'FEF3C7', 'FEF9C3', 'FEFCE8', 'D1FAE5',
                  'DBEAFE', 'F3F4F6', 'F9FAFB', 'FFF7ED']:
        _color_fmts[hex_c] = wb.add_format({
            'bg_color': hex_c, 'valign': 'vcenter', 'border': 1, 'border_color': 'E5E7EB',
        })

    headers = [
        'Empresa', 'CNPJ/CPF', 'Município', 'Escritório', 'Responsável',
        'Atuação', 'Situação', 'Alvará', 'Classif. Alvará',
        'VISA', 'Classif. VISA', 'CNES', 'Classif. CNES',
        'Lic. Ambiental', 'Classif. Lic. Ambiental',
        'Publicidade', 'Classif. Publicidade',
        'TPI', 'Classif. TPI', 'Procuração', 'Classif. Procuração',
        'Bombeiro — Venc.', 'Classif. Bombeiro Venc.',
        'Bombeiro — Prot.', 'Classif. Bombeiro Prot.',
        'Cert. Digital', 'Classif. Cert. Digital',
        'Observações',
    ]
    col_widths = [40, 18, 20, 18, 20, 15, 12] + [20, 22] * 10 + [30]
    ws.set_row(0, 30)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        ws.set_column(i, i, w)
        ws.write(0, i, h, hdr_fmt)

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, 0, len(headers) - 1)

    campos_doc_mapa = [
        'alvara_funcionamento', 'visa', 'cnes', 'licenca_ambiental',
        'publicidade', 'tpi', 'procuracao', 'venc_bombeiro', 'prot_bombeiro',
        'certificado_digital',
    ]

    def _safe(e, campo):
        try:
            return e[campo] or ''
        except Exception:
            return ''

    for row_i, e in enumerate(empresas, 1):
        ws.write(row_i, 0, _safe(e, 'nome_empresa'), cell_fmt)
        ws.write(row_i, 1, _safe(e, 'cnpj_cpf'), cell_fmt)
        ws.write(row_i, 2, _safe(e, 'municipio'), cell_fmt)
        ws.write(row_i, 3, _safe(e, 'escritorio'), cell_fmt)
        ws.write(row_i, 4, _safe(e, 'responsavel'), cell_fmt)
        ws.write(row_i, 5, _safe(e, 'atuacao'), cell_fmt)
        ws.write(row_i, 6, _safe(e, 'aba'), cell_fmt)

        col_i = 7
        for campo in campos_doc_mapa:
            val = _safe(e, campo)
            c_val = classificar_campo(campo, val)
            cor = _badge_color(c_val)
            ws.write(row_i, col_i, val, cell_fmt)
            ws.write(row_i, col_i + 1, c_val, _color_fmts.get(cor, cell_fmt))
            col_i += 2

        ws.write(row_i, col_i, _safe(e, 'observacoes'), cell_fmt)

    wb.close()
    buf.seek(0)

    nome_arquivo = f'empresas_{date.today().strftime("%Y%m%d")}.xlsx'
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nome_arquivo,
    )


@empresas_bp.route('/relatorio-excel')
def relatorio_excel():
    """Gera relatório completo em Excel com múltiplas abas.

    Regras de permissão:
    - Usuário comum: só pode gerar relatório do PRÓPRIO responsável (exatamente um selecionado).
    - Admin: pode gerar relatório de qualquer seleção, incluindo gestão geral.
    """
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    try:
        import xlsxwriter
        from io import BytesIO
    except ImportError:
        return redirect(url_for('empresas.index'))

    is_admin = bool(session.get('is_admin'))
    user_nome = session.get('user_nome', '')
    filtros = {c: request.args.getlist(c) for c in CAMPOS_FILTRO}
    q = request.args.get('q', '').strip()
    aba = request.args.get('aba', '').strip()

    responsaveis_filtro = filtros.get('responsavel', [])

    # ── Validação de permissão ────────────────────────────────────────────────
    _MSG_PERMISSAO = ('Para gerar o relatório de controle, selecione no filtro '
                      'Responsável apenas o seu próprio nome.')
    if not is_admin:
        if len(responsaveis_filtro) != 1:
            flash(_MSG_PERMISSAO, 'warning')
            return redirect(url_for('empresas.index'))
        resp_sel = _normalizar(responsaveis_filtro[0])
        user_norm = _normalizar(user_nome)
        if resp_sel != user_norm:
            flash(_MSG_PERMISSAO, 'warning')
            return redirect(url_for('empresas.index'))

    # ── Buscar dados ──────────────────────────────────────────────────────────
    active_class_rel = {}
    for campo in CAMPOS_DOCUMENTAIS:
        val = request.args.get(f'class_{campo}', '').strip()
        if val:
            active_class_rel[campo] = val

    conn = database.get_db()
    sql, params = _build_query(q, aba, filtros)
    empresas_raw = conn.execute(sql + ' ORDER BY nome_empresa', params).fetchall()
    conn.close()

    if active_class_rel:
        def _pass_rel(e):
            for campo, cat in active_class_rel.items():
                try:
                    v = e[campo]
                except Exception:
                    v = ''
                if classificar_campo(campo, v) != cat:
                    return False
            return True
        empresas_lista = [e for e in empresas_raw if _pass_rel(e)]
    else:
        empresas_lista = empresas_raw

    if not empresas_lista:
        return jsonify({'erro': 'Nenhuma empresa encontrada com os filtros aplicados.'}), 404

    # Pré-calcular classificações
    dados_empresas = []
    for e in empresas_lista:
        classifs = {campo: classificar_campo(campo, e[campo] if campo in e.keys() else '')
                    for campo in CAMPOS_DOCUMENTAIS}
        dados_empresas.append({'empresa': e, 'classifs': classifs})

    # ── Criar workbook ────────────────────────────────────────────────────────
    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})

    # ── Formatos ──────────────────────────────────────────────────────────────
    _fmt_cache = {}
    def _f(bg=None, bold=False, wrap=False, align='left', font_color=None,
           font_size=None, border=True, valign='vcenter'):
        key = (bg, bold, wrap, align, font_color, font_size, border, valign)
        if key not in _fmt_cache:
            props = {'valign': valign, 'align': align}
            if border:
                props['border'] = 1
                props['border_color'] = 'E5E7EB'
            if bg:
                props['bg_color'] = bg
            if bold:
                props['bold'] = True
            if wrap:
                props['text_wrap'] = True
            if font_color:
                props['font_color'] = font_color
            if font_size:
                props['font_size'] = font_size
            _fmt_cache[key] = wb.add_format(props)
        return _fmt_cache[key]

    hdr_fmt = wb.add_format({
        'bold': True, 'font_color': 'FFFFFF', 'bg_color': 'A72C31',
        'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        'border': 1, 'border_color': 'CCCCCC',
    })
    sub_hdr_fmt = wb.add_format({
        'bold': True, 'font_color': 'FFFFFF', 'bg_color': '6B7280',
        'align': 'center', 'valign': 'vcenter', 'font_size': 9,
        'border': 1,
    })
    title_fmt   = wb.add_format({'bold': True, 'font_size': 14, 'font_color': 'A72C31', 'valign': 'vcenter'})
    subtitle_fmt= wb.add_format({'bold': True, 'font_size': 12, 'font_color': 'A72C31', 'valign': 'vcenter'})
    plain_fmt   = wb.add_format({'valign': 'vcenter'})
    section_fmt = wb.add_format({'bold': True, 'valign': 'vcenter'})

    BADGE_COLORS = {
        'Vencido':            'FEE2E2',
        'A vencer — 30 dias': 'FEF3C7',
        'A vencer — 60 dias': 'FEF9C3',
        'A vencer — 90 dias': 'FEFCE8',
        'A vencer':           'D1FAE5',
        'Válido indeterminado': 'DBEAFE',
        'Em andamento':       'DBEAFE',
        'Isento':             'F3F4F6',
        'Não possui':         'F3F4F6',
        'Sem informação':     'F9FAFB',
        'Revisar cadastro':   'FFF7ED',
        'Informação não classificada': 'FFF7ED',
    }

    def _bc(classif):
        return BADGE_COLORS.get(classif, 'FFFFFF')

    def _c(ws, row, col, val, bg=None, bold=False, wrap=False, align='left'):
        """Escreve célula (row/col 1-indexados para compatibilidade)."""
        ws.write(row - 1, col - 1, val if val is not None else '', _f(bg=bg, bold=bold, wrap=wrap, align=align))

    def _safe(e, campo):
        try:
            return e[campo] or ''
        except Exception:
            return ''

    # ── ABA 1: Resumo Geral ───────────────────────────────────────────────────
    ws_resumo = wb.add_worksheet('Resumo Geral')
    ws_resumo.set_column(0, 0, 35)
    ws_resumo.set_column(1, 1, 20)
    ws_resumo.set_column(2, 7, 14)

    row = 1
    ws_resumo.write(row - 1, 0, 'RELATÓRIO DE CONTROLE — SOCIETÁRIO SIGMA', title_fmt)
    row += 1
    ws_resumo.write(row - 1, 0, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', plain_fmt)
    row += 1
    ws_resumo.write(row - 1, 0, f'Gerado por: {user_nome}', plain_fmt)
    row += 2

    ws_resumo.write(row - 1, 0, 'FILTROS APLICADOS', section_fmt)
    row += 1
    if aba:
        ws_resumo.write(row - 1, 0, f'Situação: {aba}', plain_fmt)
        row += 1
    for campo in CAMPOS_FILTRO:
        vals = filtros.get(campo, [])
        if vals:
            ws_resumo.write(row - 1, 0, f'{LABELS_FILTRO[campo]}: {", ".join(vals)}', plain_fmt)
            row += 1
    if not aba and not any(filtros.values()):
        ws_resumo.write(row - 1, 0, 'Nenhum filtro aplicado — relatório geral', plain_fmt)
        row += 1
    row += 1

    ws_resumo.write(row - 1, 0, 'TOTAIS GERAIS', section_fmt)
    row += 1
    _c(ws_resumo, row, 1, 'Total de empresas no relatório', bold=True)
    _c(ws_resumo, row, 2, len(empresas_lista), align='center')
    row += 1
    ativas     = sum(1 for d in dados_empresas if d['empresa']['aba'] == 'ATIVAS')
    inativas   = sum(1 for d in dados_empresas if d['empresa']['aba'] == 'INATIVAS')
    nao_mens   = sum(1 for d in dados_empresas if d['empresa']['aba'] == 'NÃO MENSAIS')
    _c(ws_resumo, row, 1, 'Ativas');           _c(ws_resumo, row, 2, ativas,   align='center'); row += 1
    _c(ws_resumo, row, 1, 'Inativas');         _c(ws_resumo, row, 2, inativas, align='center'); row += 1
    _c(ws_resumo, row, 1, 'Não mensais/Avulso'); _c(ws_resumo, row, 2, nao_mens, align='center'); row += 2

    ws_resumo.write(row - 1, 0, 'RESUMO DOCUMENTAL', section_fmt)
    row += 1
    resumo_hdr_row = row - 1  # 0-indexed para chart
    hdr_doc = [
        ('Campo', 'F3F4F6'), ('Vencidos', 'FEE2E2'), ('A vencer', 'FEF9C3'),
        ('Válidos', 'D1FAE5'), ('Em andamento', 'DBEAFE'),
        ('Isento/N.possui', 'F3F4F6'), ('Sem info', 'F9FAFB'), ('Revisar', 'FFF7ED'),
    ]
    for col_i, (h, bg) in enumerate(hdr_doc):
        _c(ws_resumo, row, col_i + 1, h, bold=True, bg=bg, align='center' if col_i > 0 else 'left')
    row += 1

    for campo in CAMPOS_DOCUMENTAIS:
        label = LABELS_FILTRO.get(campo, campo)
        cnt = {'Vencido': 0, 'a_vencer': 0, 'valido': 0, 'andamento': 0,
               'isento': 0, 'sem_info': 0, 'revisar': 0}
        for d in dados_empresas:
            cl = d['classifs'].get(campo, 'Sem informação')
            if cl == 'Vencido':                   cnt['Vencido'] += 1
            elif 'vencer' in cl.lower():           cnt['a_vencer'] += 1
            elif 'válido' in cl.lower() or 'indetermin' in cl.lower(): cnt['valido'] += 1
            elif 'andamento' in cl.lower():        cnt['andamento'] += 1
            elif cl in ('Isento', 'Não possui'):   cnt['isento'] += 1
            elif cl == 'Sem informação':           cnt['sem_info'] += 1
            else:                                  cnt['revisar'] += 1
        _c(ws_resumo, row, 1, label)
        _c(ws_resumo, row, 2, cnt['Vencido'],   bg='FEE2E2' if cnt['Vencido']   else None, align='center')
        _c(ws_resumo, row, 3, cnt['a_vencer'],  bg='FEF9C3' if cnt['a_vencer']  else None, align='center')
        _c(ws_resumo, row, 4, cnt['valido'],    bg='D1FAE5' if cnt['valido']    else None, align='center')
        _c(ws_resumo, row, 5, cnt['andamento'], align='center')
        _c(ws_resumo, row, 6, cnt['isento'],    align='center')
        _c(ws_resumo, row, 7, cnt['sem_info'],  align='center')
        _c(ws_resumo, row, 8, cnt['revisar'],   bg='FFF7ED' if cnt['revisar']   else None, align='center')
        row += 1
    resumo_last_row = row - 2  # 0-indexed

    # Gráfico Resumo Geral
    try:
        chart_res = wb.add_chart({'type': 'bar'})
        for col_i, name in [(1, 'Vencidos'), (2, 'A vencer'), (3, 'Válidos')]:
            chart_res.add_series({
                'name': name,
                'categories': ['Resumo Geral', resumo_hdr_row + 1, 0, resumo_last_row, 0],
                'values':     ['Resumo Geral', resumo_hdr_row + 1, col_i, resumo_last_row, col_i],
            })
        chart_res.set_title({'name': 'Situação Documental Geral'})
        chart_res.set_y_axis({'name': 'Empresas'})
        chart_res.set_size({'width': 480, 'height': 350})
        ws_resumo.insert_chart('J3', chart_res)
    except Exception:
        pass

    # ── ABA 2: Empresas Filtradas ─────────────────────────────────────────────
    ws_emp = wb.add_worksheet('Empresas Filtradas')
    ws_emp.freeze_panes(1, 0)
    cols_emp_def = [
        ('Empresa', 40), ('CNPJ/CPF', 18), ('Município', 20), ('Escritório', 18),
        ('Responsável', 20), ('Atuação', 15), ('Situação', 12),
    ] + sum([[(f, 20), (f'Class. {f}', 22)] for f in
              ['Alvará', 'VISA', 'CNES', 'Lic. Ambiental',
               'Publicidade', 'TPI', 'Procuração', 'Bombeiro Venc.', 'Bombeiro Prot.',
               'Cert. Digital']], []) + \
        [('Observações', 30)]

    ws_emp.set_row(0, 30)
    for col_i, (h, w) in enumerate(cols_emp_def):
        ws_emp.set_column(col_i, col_i, w)
        ws_emp.write(0, col_i, h, hdr_fmt)
    ws_emp.autofilter(0, 0, 0, len(cols_emp_def) - 1)

    for row_i, d in enumerate(dados_empresas, 1):
        e = d['empresa']
        cl = d['classifs']
        for col_i, campo in enumerate(['nome_empresa', 'cnpj_cpf', 'municipio',
                                        'escritorio', 'responsavel', 'atuacao', 'aba']):
            ws_emp.write(row_i, col_i, _safe(e, campo), _f())
        col_i = 7
        for campo in CAMPOS_DOCUMENTAIS:
            val = _safe(e, campo)
            c_val = cl.get(campo, '')
            cor = _bc(c_val)
            ws_emp.write(row_i, col_i,     val,   _f())
            ws_emp.write(row_i, col_i + 1, c_val, _f(bg=cor) if cor != 'FFFFFF' else _f())
            col_i += 2
        ws_emp.write(row_i, col_i, _safe(e, 'observacoes'), _f())

    # ── ABAs documentais ──────────────────────────────────────────────────────
    categorias_order = [
        'Vencido', 'A vencer — 30 dias', 'A vencer — 60 dias', 'A vencer — 90 dias',
        'A vencer', 'Válido indeterminado', 'Em andamento', 'Isento', 'Não possui',
        'Sem informação', 'Informação não classificada', 'Revisar cadastro',
    ]
    campos_abas = [
        ('alvara_funcionamento', 'Alvará'),
        ('visa', 'VISA'),
        ('cnes', 'CNES'),
        ('licenca_ambiental', 'Lic. Ambiental'),
        ('publicidade', 'Publicidade'),
        ('tpi', 'TPI'),
        ('procuracao', 'Procuração'),
        ('venc_bombeiro', 'Bomb. Vencimento'),
        ('prot_bombeiro', 'Bomb. Protocolo'),
        ('certificado_digital', 'Cert. Digital'),
    ]

    for campo, aba_nome in campos_abas:
        ws_doc = wb.add_worksheet(aba_nome[:31])
        for col_i, w in enumerate([6, 40, 18, 22, 18, 20]):
            ws_doc.set_column(col_i, col_i, w)

        grupos = {}
        for d in dados_empresas:
            cat = d['classifs'].get(campo, 'Sem informação')
            grupos.setdefault(cat, []).append(d)

        row_doc = 1
        ws_doc.write(row_doc - 1, 0, f'{aba_nome} — Detalhamento por situação', subtitle_fmt)
        row_doc += 2

        for cat in categorias_order:
            grupo = grupos.get(cat, [])
            if not grupo:
                continue
            bg_cat = _bc(cat)
            cat_fmt = _f(bg=bg_cat if bg_cat != 'FFFFFF' else None, bold=True)
            ws_doc.merge_range(row_doc - 1, 0, row_doc - 1, 5, f'{cat} ({len(grupo)})', cat_fmt)
            row_doc += 1

            for col_i, h in enumerate(['#', 'Empresa', 'CNPJ', 'Valor do campo', 'Responsável', 'Município']):
                ws_doc.write(row_doc - 1, col_i, h, sub_hdr_fmt)
            row_doc += 1

            for idx, d in enumerate(grupo, 1):
                e2 = d['empresa']
                _c(ws_doc, row_doc, 1, idx, align='center')
                _c(ws_doc, row_doc, 2, _safe(e2, 'nome_empresa'))
                _c(ws_doc, row_doc, 3, _safe(e2, 'cnpj_cpf'))
                _c(ws_doc, row_doc, 4, _safe(e2, campo), bg=bg_cat if bg_cat != 'FFFFFF' else None)
                _c(ws_doc, row_doc, 5, _safe(e2, 'responsavel'))
                _c(ws_doc, row_doc, 6, _safe(e2, 'municipio'))
                row_doc += 1
            row_doc += 1

    # ── ABA: Revisar Cadastro ─────────────────────────────────────────────────
    ws_rev = wb.add_worksheet('Revisar Cadastro')
    for col_i, w in enumerate([40, 18, 25, 20, 20]):
        ws_rev.set_column(col_i, col_i, w)
    ws_rev.write(0, 0, 'Empresas com pendências de cadastro', subtitle_fmt)

    row_rev = 3
    for col_i, h in enumerate(['Empresa', 'CNPJ', 'Campo com pendência', 'Situação atual', 'Responsável']):
        ws_rev.write(row_rev - 1, col_i, h, hdr_fmt)
    ws_rev.set_row(row_rev - 1, 25)
    row_rev += 1

    pendencias_cats = {'Revisar cadastro', 'Informação não classificada', 'Sem informação'}
    for d in dados_empresas:
        e = d['empresa']
        for campo in CAMPOS_DOCUMENTAIS:
            cat = d['classifs'].get(campo, 'Sem informação')
            if cat in pendencias_cats:
                cor = _bc(cat)
                _c(ws_rev, row_rev, 1, _safe(e, 'nome_empresa'))
                _c(ws_rev, row_rev, 2, _safe(e, 'cnpj_cpf'))
                _c(ws_rev, row_rev, 3, LABELS_FILTRO.get(campo, campo))
                _c(ws_rev, row_rev, 4, f'{_safe(e, campo)} → {cat}',
                   bg=cor if cor != 'FFFFFF' else None)
                _c(ws_rev, row_rev, 5, _safe(e, 'responsavel'))
                row_rev += 1

    # ── ABA: Gestão por Responsável (somente admin sem responsavel filtrado) ──
    if is_admin and not responsaveis_filtro:
        ws_gest = wb.add_worksheet('Gestão por Responsável')
        for col_i, w in enumerate([25, 12, 12, 12, 12, 12]):
            ws_gest.set_column(col_i, col_i, w)
        ws_gest.write(0, 0, 'Gestão por Responsável — Visão Administrativa', subtitle_fmt)

        por_resp = {}
        for d in dados_empresas:
            resp = _safe(d['empresa'], 'responsavel') or '(Sem responsável)'
            por_resp.setdefault(resp, []).append(d)

        row_gest = 3
        for col_i, h in enumerate(['Responsável', 'Total', 'Vencidos', 'A vencer', 'Sem info', 'Revisar']):
            ws_gest.write(row_gest - 1, col_i, h, hdr_fmt)
        ws_gest.set_row(row_gest - 1, 25)
        row_gest += 1

        gest_data_start = row_gest - 1  # 0-indexed
        for resp, grupo in sorted(por_resp.items(), key=lambda x: x[0]):
            vencidos = sum(1 for d in grupo for c in CAMPOS_DOCUMENTAIS if d['classifs'].get(c) == 'Vencido')
            a_vencer = sum(1 for d in grupo for c in CAMPOS_DOCUMENTAIS if 'vencer' in (d['classifs'].get(c, '') or '').lower())
            sem_info = sum(1 for d in grupo for c in CAMPOS_DOCUMENTAIS if d['classifs'].get(c) == 'Sem informação')
            revisar  = sum(1 for d in grupo for c in CAMPOS_DOCUMENTAIS if d['classifs'].get(c) in ('Revisar cadastro', 'Informação não classificada'))
            _c(ws_gest, row_gest, 1, resp, bold=True)
            _c(ws_gest, row_gest, 2, len(grupo), align='center')
            _c(ws_gest, row_gest, 3, vencidos, bg='FEE2E2' if vencidos else None, align='center')
            _c(ws_gest, row_gest, 4, a_vencer, bg='FEF9C3' if a_vencer else None, align='center')
            _c(ws_gest, row_gest, 5, sem_info, align='center')
            _c(ws_gest, row_gest, 6, revisar,  bg='FFF7ED' if revisar  else None, align='center')
            row_gest += 1
        gest_data_end = row_gest - 2  # 0-indexed

        try:
            chart = wb.add_chart({'type': 'column'})
            chart.add_series({
                'name': 'Total',
                'categories': ['Gestão por Responsável', gest_data_start, 0, gest_data_end, 0],
                'values':     ['Gestão por Responsável', gest_data_start, 1, gest_data_end, 1],
            })
            chart.set_title({'name': 'Empresas por Responsável'})
            chart.set_y_axis({'name': 'Quantidade'})
            chart.set_size({'width': 480, 'height': 300})
            ws_gest.insert_chart('H3', chart)
        except Exception:
            pass

    # ── Salvar e retornar ─────────────────────────────────────────────────────
    wb.close()
    buf.seek(0)

    tipo = 'gestao' if (is_admin and not responsaveis_filtro) else _normalizar(responsaveis_filtro[0] if responsaveis_filtro else 'geral')
    nome_arquivo = f'relatorio_societario_{tipo}_{date.today().strftime("%Y%m%d")}.xlsx'

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nome_arquivo,
    )
