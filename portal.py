"""
portal.py — Portal Societário Sigma Contabilidade
Entry point principal. Substitui app.py na porta 5080.

Módulos:
  /               → Dashboard
  /login          → Login individual por usuária
  /contrato/      → Elaboração de Contrato Social (módulo original, sem alterações)
  /procuracoes/   → Elaboração de Procurações
  /declaracoes/   → Elaboração de Declarações e Requerimentos
  /manuais/       → Área de Conhecimentos/Manuais

Rotas especiais (root) para compatibilidade com templates/index.html:
  /upload         → upload de contrato (JS chama diretamente /upload)
  /gerar          → gerar instrumento (JS chama diretamente /gerar)
  /download/<t>/  → download do documento gerado
"""

import os
import sys
import json
from itertools import groupby

# Garante que o diretório do app está no path para importar app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from datetime import timedelta
from flask import Flask, session, redirect, url_for, render_template

# Importar funções de negócio de app.py (sem executar o servidor)
from app import (
    extrair_texto,
    gerar_com_claude,
    gerar_docx,
    gerar_pdf,
    extrair_ordinal_filename,
    allowed_file,
    _DOCS_CACHE,
    APIIndisponivel,
    logger,
    _limpar_cache_antigo,
)

from dotenv import load_dotenv
load_dotenv()

# Blueprints
from blueprints.auth import auth_bp, login_obrigatorio
from blueprints.contrato import contrato_bp
from blueprints.procuracoes import procuracoes_bp
from blueprints.declaracoes import declaracoes_bp
from blueprints.manuais import manuais_bp
from blueprints.empresas import empresas_bp
from blueprints.newsletter import newsletter_bp
from blueprints.conferencia import conferencia_bp
from blueprints.admin import admin_bp
from blueprints.movimentacao import movimentacao_bp
from blueprints.informativos import informativos_bp
from blueprints.diario_oficial import diario_oficial_bp
from blueprints.cnae import cnae_bp
from blueprints.webauthn_bp import webauthn_bp
from blueprints.passkeys import passkeys_bp
from blueprints.processos import processos_bp
from blueprints.anotacoes import anotacoes_bp

import database

# ─── Módulos do Portal — Fonte Única de Verdade ───────────────────────────────
# Adicione/edite módulos aqui: reflete automaticamente em sidebar, Home e busca.

MODULES_CONFIG = [
    # ── Menu ──────────────────────────────────────────────────────────────────
    {
        'id': 'inicio', 'name': 'Início',
        'desc': 'Página inicial do portal.',
        'category': 'menu', 'cat_label': 'Menu',
        'icon': 'house', 'route': 'dashboard',
        'keywords': 'início home dashboard principal',
        'sidebar': True, 'home': False, 'quick': False,
        'blueprint': None, 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    # ── Elaboração ─────────────────────────────────────────────────────────────
    {
        'id': 'contrato', 'name': 'Contrato Social',
        'desc': 'Gestão completa de minutas e atos. Mais de 30 tipos de alteração.',
        'category': 'elaboracao', 'cat_label': 'Elaboração',
        'icon': 'file-text', 'route': 'contrato.index',
        'keywords': 'contrato social alteração minuta elaboração ato instrumento',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'contrato', 'tool_key': 'contrato',
        'admin_only': False, 'enabled': True,
    },
    {
        'id': 'procuracoes', 'name': 'Procurações',
        'desc': 'Gere procurações rapidamente com os modelos disponíveis.',
        'category': 'elaboracao', 'cat_label': 'Elaboração',
        'icon': 'pen-tool', 'route': 'procuracoes.index',
        'keywords': 'procuração documento outorgante poderes representante',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'procuracoes', 'tool_key': 'procuracoes',
        'admin_only': False, 'enabled': True,
    },
    {
        'id': 'declaracoes', 'name': 'Declarações',
        'desc': 'Mais de 25 modelos de declarações e requerimentos.',
        'category': 'elaboracao', 'cat_label': 'Elaboração',
        'icon': 'clipboard-list', 'route': 'declaracoes.index',
        'keywords': 'declaração requerimento carta documento modelo uso solo',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'declaracoes', 'tool_key': 'declaracoes',
        'admin_only': False, 'enabled': True,
    },
    # ── Conferência ────────────────────────────────────────────────────────────
    {
        'id': 'conferencia', 'name': 'Conferência de Contrato',
        'desc': 'Análise jurídica e conferência de contratos sociais.',
        'category': 'conferencia', 'cat_label': 'Conferência',
        'icon': 'search-check', 'route': 'conferencia.index',
        'keywords': 'conferência contrato análise jurídica revisão dados sócios',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'conferencia', 'tool_key': 'conferencia',
        'admin_only': False, 'enabled': True,
    },
    # ── Conhecimento ───────────────────────────────────────────────────────────
    {
        'id': 'manuais', 'name': 'Manuais',
        'desc': 'Base de conhecimento do departamento societário.',
        'category': 'conhecimento', 'cat_label': 'Conhecimento',
        'icon': 'book-open', 'route': 'manuais.index',
        'keywords': 'manual conhecimento base documentação orientação procedimento',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'manuais', 'tool_key': 'manuais',
        'admin_only': False, 'enabled': True,
    },
    {
        'id': 'diario_oficial', 'name': 'Diário Oficial',
        'desc': 'Consulta de publicações oficiais municipais e estaduais.',
        'category': 'conhecimento', 'cat_label': 'Conhecimento',
        'icon': 'newspaper', 'route': 'diario_oficial.index',
        'keywords': 'diário oficial publicação dou goiás goiânia estado município',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'diario_oficial', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    # ── Comunicação ────────────────────────────────────────────────────────────
    {
        'id': 'newsletter', 'name': 'Newsletter',
        'desc': 'Informativos e comunicados para a equipe.',
        'category': 'comunicacao', 'cat_label': 'Comunicação',
        'icon': 'mail', 'route': 'newsletter.index',
        'keywords': 'newsletter informativo comunicado equipe circular aviso',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'newsletter', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    {
        'id': 'informativos', 'name': 'Gerar Informativos',
        'desc': 'Criar informativos personalizados em PDF e apresentação.',
        'category': 'comunicacao', 'cat_label': 'Comunicação',
        'icon': 'zap', 'route': 'informativos.index',
        'keywords': 'informativo gerar pdf apresentação pptx criar personalizado',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'informativos', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    # ── Carteira ───────────────────────────────────────────────────────────────
    {
        'id': 'empresas', 'name': 'Empresas',
        'desc': 'Consulte alvarás, validades, status e carteira de clientes.',
        'category': 'carteira', 'cat_label': 'Carteira',
        'icon': 'building-2', 'route': 'empresas.index',
        'keywords': 'empresa carteira cnpj alvará consulta status cliente carteira ativa',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'empresas', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    {
        'id': 'movimentacao', 'name': 'Movimentação',
        'desc': 'Entradas e saídas de clientes da carteira.',
        'category': 'carteira', 'cat_label': 'Carteira',
        'icon': 'arrow-right-left', 'route': 'movimentacao.index',
        'keywords': 'movimentação entrada saída cliente fluxo carteira transferência',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'movimentacao', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    # ── Formulários ────────────────────────────────────────────────────────────
    {
        'id': 'processos', 'name': 'Processos em Andamento',
        'desc': 'Acompanhe formulários e processos abertos via Google Forms.',
        'category': 'formularios', 'cat_label': 'Formulários',
        'icon': 'inbox', 'route': 'processos.index',
        'keywords': 'processo formulário forms andamento acompanhar abertura alteração',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'processos', 'tool_key': 'processos',
        'admin_only': False, 'enabled': True,
    },
    # ── Consultas ──────────────────────────────────────────────────────────────
    {
        'id': 'cnae', 'name': 'CNAE / Tributação',
        'desc': 'Consulta de CNAE, regime tributário e atividades econômicas.',
        'category': 'consultas', 'cat_label': 'Consultas',
        'icon': 'tag', 'route': 'cnae.index',
        'keywords': 'cnae tributação atividade econômica regime simples presumido lucro real',
        'sidebar': True, 'home': True, 'quick': True,
        'blueprint': 'cnae', 'tool_key': None,
        'admin_only': False, 'enabled': True,
    },
    # ── Administração ──────────────────────────────────────────────────────────
    {
        'id': 'admin', 'name': 'Painel Admin',
        'desc': 'Administração de usuários, permissões e configurações do portal.',
        'category': 'administracao', 'cat_label': 'Administração',
        'icon': 'shield', 'route': 'admin.dashboard',
        'keywords': 'admin administração usuário permissão configuração sistema',
        'sidebar': True, 'home': True, 'quick': False,
        'blueprint': 'admin', 'tool_key': None,
        'admin_only': True, 'enabled': True,
    },
    # ── Produtividade ──────────────────────────────────────────────────────────
    {
        'id': 'anotacoes', 'name': 'Anotações',
        'desc': 'Bloco de notas pessoal com sticky notes para organizar o dia a dia.',
        'category': 'produtividade', 'cat_label': 'Produtividade',
        'icon': 'sticky-note', 'route': 'anotacoes.index',
        'keywords': 'anotações notas lembretes sticky note agenda post-it organizar rotina pessoal',
        'sidebar': True, 'home': False, 'quick': False,
        'blueprint': 'anotacoes', 'tool_key': 'anotacoes',
        'admin_only': False, 'enabled': True,
    },
]


def _get_visible_modules(is_admin=False):
    """Retorna módulos visíveis para o usuário (filtra admin_only se não for admin)."""
    return [
        m for m in MODULES_CONFIG
        if m.get('enabled', True) and (not m.get('admin_only') or is_admin)
    ]


# ─── Criar app ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    raise RuntimeError("SECRET_KEY nao configurada no ambiente. Defina no .env antes de iniciar o portal.")
app.secret_key = _secret_key

# Filtro Jinja2: preview (strip HTML + truncar)
def _jinja_preview(html, length=180):
    import re as _r
    t = _r.sub(r"<[^>]+>", "", html or "")
    t = " ".join(t.split())
    return (t[:length].rsplit(" ", 1)[0] + "…") if len(t) > length else t
app.jinja_env.filters["preview"] = _jinja_preview


# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(contrato_bp)
app.register_blueprint(procuracoes_bp)
app.register_blueprint(declaracoes_bp)
app.register_blueprint(manuais_bp)
app.register_blueprint(empresas_bp)
app.register_blueprint(newsletter_bp)
app.register_blueprint(conferencia_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(movimentacao_bp)
app.register_blueprint(informativos_bp)
app.register_blueprint(diario_oficial_bp)
app.register_blueprint(cnae_bp)
app.register_blueprint(webauthn_bp)
app.register_blueprint(passkeys_bp)
app.register_blueprint(processos_bp)
app.register_blueprint(anotacoes_bp)


# ─── Context processor — Módulos (fonte única de verdade) ─────────────────────

@app.context_processor
def inject_modules_config():
    """Injeta módulos em todos os templates — fonte única de verdade."""
    from flask import session as _sess
    is_admin = _sess.get('is_admin', False)
    visible = _get_visible_modules(is_admin)

    # Grupos por categoria para seção "Todos os módulos" da Home
    home_mods = [m for m in visible if m.get('home')]
    home_groups = []
    for _cat, items in groupby(home_mods, key=lambda m: m['category']):
        items_list = list(items)
        home_groups.append({
            'cat_label': items_list[0]['cat_label'],
            'modulos': items_list,
        })

    return dict(
        modules_config=visible,
        modules_config_json=json.dumps(visible),
        modules_home_groups=home_groups,
    )


# ─── Controle de permissões (before_request) ──────────────────────────────────

# Mapeamento URL prefix → chave de ferramenta
_TOOL_PREFIXES = {
    '/contrato':    'contrato',
    '/upload':      'contrato',
    '/gerar':       'contrato',
    '/download':    'contrato',
    '/procuracoes': 'procuracoes',
    '/declaracoes': 'declaracoes',
    '/manuais':     'manuais',
    '/empresas':    'empresas',
    '/newsletter':  'newsletter',
    '/conferencia':  'conferencia',
    '/informativos': 'informativos',
    '/processos':   'processos',
    '/anotacoes':   'anotacoes',
}

from flask import abort


# ─── Handlers de erro globais (sempre retorna JSON para APIs) ──────────────────

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'erro': f'Requisição inválida: {str(e)}'}), 400

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'erro': 'Arquivo muito grande. Tamanho máximo: 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'erro': 'Erro interno do servidor. Tente novamente.'}), 500


@app.before_request
def verificar_permissao_e_logar():
    """Bloqueia acesso a ferramentas sem permissão e registra atividade."""
    path = request.path
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)

    # Exibir aviso de cadastro de passkey após login sem passkey
    # (apenas uma vez, apenas em GET de dashboard)
    if user_id and session.pop('_avisar_cadastrar_passkey', False):
        # Redirecionar para passkeys ao invés do dashboard? Não — apenas mostrar o aviso na sessão
        session['_flash_passkey'] = True

    # Identificar se a rota corresponde a uma ferramenta
    tool = next((t for prefix, t in _TOOL_PREFIXES.items() if path.startswith(prefix)), None)

    if tool and user_id:
        # Verificar permissão (admin sempre passa)
        if not is_admin and not database.get_user_permission(user_id, tool):
            # Requisições AJAX/POST esperam JSON — retornar JSON para não quebrar o fetch
            if request.method != 'GET':
                return jsonify({'erro': 'Você não tem permissão para acessar este recurso.'}), 403
            return render_template('acesso_negado.html'), 403

        # Logar atividade apenas em GET (evitar duplicatas em requisições AJAX/POST)
        if request.method == 'GET':
            database.log_activity(user_id, tool, 'acesso', request.remote_addr or '')


@app.before_request
def verificar_stepup_sensivel():
    """
    Intercepta rotas sensíveis (download de documentos, área admin) e exige
    verificação Passkey/WebAuthn se o step-up não foi feito recentemente.
    """
    from security import should_require_stepup_for_session

    path     = request.path
    user_id  = session.get('user_id')
    is_admin = session.get('is_admin', False)

    if not user_id:
        return  # não logado, outros handlers cuidam disso

    # Rotas que não precisam de step-up
    _SKIP_STEPUP = ('/webauthn/', '/passkeys/', '/static/', '/login',
                    '/logout', '/esqueceu-senha', '/redefinir-senha',
                    '/api/notificacoes', '/favicon')
    if any(path.startswith(p) for p in _SKIP_STEPUP):
        return

    # ── Download de documentos ─────────────────────────────────────────────────
    if path.startswith('/download/'):
        required, reason = should_require_stepup_for_session(
            session, 'download_document', is_admin=is_admin
        )
        if required:
            database.security_log('stepup_exigido', user_id=user_id,
                                   ip=request.remote_addr or '',
                                   user_agent=request.headers.get('User-Agent', ''),
                                   details=f'action=download_document reason={reason}')
            # Para GETs de download: redirecionar para verificação
            return redirect(url_for('webauthn.verify_page',
                                    purpose='stepup',
                                    next=path,
                                    reason=reason))

    # ── Área administrativa ────────────────────────────────────────────────────
    if path.startswith('/admin/') and is_admin:
        # Apenas para endpoints de ESCRITA sensíveis no admin
        _ADMIN_SENSITIVE = [
            '/admin/usuarios/',  # criação/edição/exclusão de usuários
            '/admin/toggle',
        ]
        if any(path.startswith(p) for p in _ADMIN_SENSITIVE) and request.method == 'POST':
            required, reason = should_require_stepup_for_session(
                session, 'admin_area', is_admin=True
            )
            if required:
                database.security_log('stepup_exigido', user_id=user_id,
                                       ip=request.remote_addr or '',
                                       user_agent=request.headers.get('User-Agent', ''),
                                       details=f'action=admin_area reason={reason}')
                return jsonify({
                    'stepup_required': True,
                    'next': path,
                    'reason': reason,
                    'verify_url': url_for('webauthn.verify_page',
                                          purpose='stepup', next=path, reason=reason),
                }), 403


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    user_id    = session.get('user_id')
    has_passkey = database.count_webauthn_credentials(user_id) > 0 if user_id else False
    return render_template('dashboard.html', has_passkey=has_passkey)


# ─── API de Notificações ───────────────────────────────────────────────────────

@app.route('/api/notificacoes')
def api_notificacoes():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    data = database.get_notificacoes(user_id)
    return jsonify(data)


@app.route('/api/notificacoes/<int:notif_id>/ler', methods=['POST'])
def api_notificacao_ler(notif_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    database.marcar_notificacao_lida(notif_id, session.get('user_id'))
    return jsonify({'ok': True})


@app.route('/api/notificacoes/ler-todas', methods=['POST'])
def api_notificacoes_ler_todas():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    database.marcar_todas_lidas(session.get('user_id'))
    return jsonify({'ok': True})


@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """KPIs para os cards da Home."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    stats = {'processos': 0, 'movimentacoes': 0, 'empresas': 0, 'manuais': 0}
    try:
        conn = database.get_db()
        cur  = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM processos_formularios WHERE arquivado=0")
            stats['processos'] = cur.fetchone()[0]
        except Exception:
            pass
        try:
            cur.execute(
                "SELECT COUNT(*) FROM movimentacao_empresas "
                "WHERE notificado_em >= datetime('now', '-7 days')"
            )
            stats['movimentacoes'] = cur.fetchone()[0]
        except Exception:
            pass
        try:
            cur.execute("SELECT COUNT(*) FROM empresas_planilha WHERE aba='ATIVAS'")
            stats['empresas'] = cur.fetchone()[0]
        except Exception:
            pass
        try:
            cur.execute("SELECT COUNT(*) FROM manuais")
            stats['manuais'] = cur.fetchone()[0]
        except Exception:
            pass
        conn.close()
    except Exception:
        pass
    return jsonify(stats)


@app.route('/api/anotacoes', methods=['GET'])
def api_anotacoes_list():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    limit   = request.args.get('limit', 0, type=int)
    notas   = database.get_anotacoes(user_id, limit=limit)
    return jsonify(notas)


@app.route('/api/anotacoes', methods=['POST'])
def api_anotacoes_criar():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    dados   = request.get_json(force=True) or {}
    # Calcular posição automática para não sobrepor notas existentes
    notas_existentes = database.get_anotacoes(user_id)
    pos_x = 20 + (len(notas_existentes) % 4) * 20
    pos_y = 20 + (len(notas_existentes) % 4) * 20
    novo_id = database.criar_anotacao(
        user_id  = user_id,
        titulo   = dados.get('titulo', ''),
        conteudo = dados.get('conteudo', ''),
        cor      = dados.get('cor', 'amarelo'),
        pos_x    = dados.get('pos_x', pos_x),
        pos_y    = dados.get('pos_y', pos_y),
        largura  = dados.get('largura', 320),
        altura   = dados.get('altura', 260),
    )
    notas = database.get_anotacoes(user_id)
    nova  = next((n for n in notas if n['id'] == novo_id), {'id': novo_id})
    return jsonify(nova), 201


@app.route('/api/anotacoes/<int:nota_id>', methods=['PUT'])
def api_anotacoes_update(nota_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    dados   = request.get_json(force=True) or {}
    ok = database.atualizar_anotacao(nota_id, user_id, dados)
    if not ok:
        return jsonify({'erro': 'Anotação não encontrada'}), 404
    return jsonify({'ok': True})


@app.route('/api/anotacoes/<int:nota_id>', methods=['DELETE'])
def api_anotacoes_delete(nota_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    ok = database.deletar_anotacao(nota_id, user_id)
    if not ok:
        return jsonify({'erro': 'Anotação não encontrada'}), 404
    return jsonify({'ok': True})


@app.route('/api/continuar-onde-parei')
def api_continuar_onde_parei():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id  = session.get('user_id')
    is_admin = session.get('is_admin', False)
    acessos  = database.get_ultimos_acessos(user_id, limit=3)
    visible  = _get_visible_modules(is_admin)
    tool_map = {m['tool_key']: m for m in visible if m.get('tool_key')}
    result = []
    for row in acessos:
        m = tool_map.get(row['tool'])
        if not m:
            continue
        try:
            rota = url_for(m['route'])
        except Exception:
            rota = '/'
        result.append({
            'name':    m['name'],
            'icon':    m['icon'],
            'url':     rota,
            'last_at': row['last_at'],
        })
    return jsonify(result)


@app.route('/notificacoes')
def pagina_notificacoes():
    """Página completa de notificações (usada pelo bloco 'Fique por dentro')."""
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    user_id = session.get('user_id')
    data    = database.get_notificacoes(user_id)
    return render_template('notificacoes.html', notificacoes=data)


# ─── Webhook Google Forms ──────────────────────────────────────────────────────

@app.route('/webhook/forms/<token>', methods=['POST'])
def webhook_forms(token):
    """
    Recebe respostas de Google Forms via Google Apps Script.
    Cria processo em 'processos_formularios' e notifica usuários no sino.
    """
    import hashlib

    expected = os.getenv('FORMS_WEBHOOK_TOKEN', '')
    if not expected or token != expected:
        return jsonify({'erro': 'Token inválido'}), 401

    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({'erro': 'JSON inválido'}), 400

    form_name        = (data.get('form_name') or 'Formulário').strip()
    form_id          = (data.get('form_id') or '').strip()
    response_id      = (data.get('response_id') or '').strip()
    enviado_por      = (data.get('respondent_email') or '').strip()
    data_envio       = data.get('submitted_at') or None
    respostas        = data.get('responses') or {}
    tipo_processo    = (data.get('tipo_processo') or '').strip()
    link_resposta    = (data.get('response_edit_url') or '').strip()

    # Identificar formulário cadastrado pelo form_id
    formulario_id = None
    if form_id:
        formulario = database.get_formulario_by_form_id(form_id)
        if formulario:
            if not tipo_processo:
                tipo_processo = formulario['tipo_processo']
            formulario_id = formulario['id']
            # Se não veio link_resposta mas temos form_id + response_id reais → gerar URL
            if not link_resposta and response_id and not response_id.startswith(('fallback_', 'sheet_')):
                link_resposta = f'https://docs.google.com/forms/d/{form_id}/edit#response={response_id}'

    # Fallback de tipo e dedup
    if not tipo_processo:
        tipo_processo = form_name

    # Gerar response_id de fallback se não veio (hash de dados únicos)
    if not response_id:
        raw = f"{form_id}|{enviado_por}|{data_envio}"
        response_id = 'fallback_' + hashlib.sha256(raw.encode()).hexdigest()[:20]

    # Criar processo (retorna None se duplicado)
    processo_id = database.criar_processo_formulario(
        form_name=form_name,
        tipo_processo=tipo_processo,
        response_id=response_id,
        enviado_por=enviado_por,
        data_envio=data_envio,
        formulario_id=formulario_id,
        link_resposta=link_resposta,
    )

    if processo_id is None:
        return jsonify({'ok': True, 'duplicata': True}), 200

    # Inserir respostas
    if respostas and isinstance(respostas, dict):
        database.inserir_respostas_processo(processo_id, respostas)

    # Notificar todos os usuários ativos no sino
    descricao = tipo_processo
    if enviado_por:
        descricao += f' — {enviado_por}'
    link = f'/processos/?aba=ativos#processo-{processo_id}'
    database.criar_notificacoes_para_evento(
        modulo='processos',
        tipo_evento='novo_formulario',
        titulo='Novo formulário recebido',
        descricao=descricao,
        link_destino=link,
    )

    print(f'[webhook_forms] Novo processo #{processo_id}: {tipo_processo} de {enviado_por}')
    return jsonify({'ok': True, 'processo_id': processo_id}), 201


# ─── Rotas raiz (compatibilidade com templates/index.html) ──────────────────
# O JS em templates/index.html chama /upload, /gerar, /download sem prefixo.
# Estas rotas ficam na raiz para que o módulo contrato funcione sem modificações.

import io
import tempfile
import uuid
import time
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename


@app.route('/upload', methods=['POST'])
def upload():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if 'contrato' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

    arquivo = request.files['contrato']
    if arquivo.filename == '':
        return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400

    if not allowed_file(arquivo.filename):
        return jsonify({'erro': 'Formato inválido. Use PDF ou DOCX'}), 400

    filename = secure_filename(arquivo.filename)
    extensao = filename.rsplit('.', 1)[1].lower()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{extensao}') as tmp:
            tmp_path = tmp.name
            arquivo.save(tmp.name)
        texto = extrair_texto(tmp_path, extensao)
    except Exception as e:
        print(f'[upload] Erro ao extrair texto: {type(e).__name__}: {e}')
        return jsonify({'erro': f'Erro ao ler o arquivo: {str(e)}'}), 400
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not texto.strip():
        return jsonify({'erro': 'Não foi possível extrair texto do arquivo. Se o PDF for escaneado (imagem), converta para Word (.docx) ou use um PDF criado digitalmente.'}), 400

    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    nome_empresa = linhas[0] if linhas else 'EMPRESA'

    return jsonify({
        'sucesso': True,
        'texto': texto,
        'nome_empresa': nome_empresa,
        'tamanho': len(texto)
    })


@app.route('/gerar', methods=['POST'])
def gerar():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    dados = request.get_json()
    if not dados:
        return jsonify({'erro': 'Dados inválidos'}), 400

    texto_contrato = dados.get('texto_contrato', '')
    alteracoes = dados.get('alteracoes', [])
    nome_empresa = dados.get('nome_empresa', 'EMPRESA')

    if not texto_contrato:
        return jsonify({'erro': 'Contrato não encontrado'}), 400
    if not alteracoes:
        return jsonify({'erro': 'Nenhuma alteração informada'}), 400

    tem_consolidacao = any(a.get('tipo') == 'Consolidação' for a in alteracoes)

    try:
        texto_gerado = gerar_com_claude(texto_contrato, alteracoes, tem_consolidacao)
    except APIIndisponivel as e:
        return jsonify({'erro': str(e)}), 503
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        logger.exception("Erro inesperado em gerar_com_claude (portal.py)")
        return jsonify({'erro': 'Erro interno ao processar o contrato. Tente novamente ou contate o administrador.'}), 500

    try:
        buffer = gerar_docx(texto_gerado, nome_empresa, tem_consolidacao)
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Word: {str(e)}'}), 500

    nome_arquivo = extrair_ordinal_filename(texto_gerado)

    pdf_bytes = None
    try:
        buffer_pdf = gerar_pdf(texto_gerado, nome_empresa, tem_consolidacao)
        pdf_bytes = buffer_pdf.read()
    except Exception as e_pdf:
        pass

    _limpar_cache_antigo()
    token = str(uuid.uuid4())
    _DOCS_CACHE[token] = {
        'docx': buffer.read(),
        'pdf':  pdf_bytes,
        'nome': nome_arquivo,
        'ts':   time.time(),
    }

    return jsonify({'token': token, 'nome': nome_arquivo, 'pdf_ok': pdf_bytes is not None})


@app.route('/download/<token>/<formato>')
def download(token, formato):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    entrada = _DOCS_CACHE.get(token)
    if not entrada:
        return jsonify({'erro': 'Documento expirado. Gere novamente.'}), 404

    nome_base = entrada['nome'].replace('.docx', '')

    if formato == 'docx':
        return send_file(
            io.BytesIO(entrada['docx']),
            as_attachment=True,
            download_name=entrada['nome'],
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    elif formato == 'pdf':
        if not entrada.get('pdf'):
            return jsonify({'erro': 'PDF não disponível para este documento.'}), 500
        return send_file(
            io.BytesIO(entrada['pdf']),
            as_attachment=True,
            download_name=f'{nome_base}.pdf',
            mimetype='application/pdf'
        )
    return jsonify({'erro': 'Formato inválido'}), 400


# ─── Inicialização ────────────────────────────────────────────────────────────

def _iniciar_sheets_sync():
    """Thread: grava DB → Google Sheets a cada hora, seg-sex 8h-18h."""
    import threading
    import time as _time
    from datetime import datetime as _dt

    def _loop():
        _time.sleep(60)  # aguarda portal subir
        while True:
            try:
                agora = _dt.now()
                # Segunda (0) a Sexta (4), 8h às 18h
                if agora.weekday() < 5 and 8 <= agora.hour < 18:
                    from blueprints.empresas import gravar_planilha
                    total, cells = gravar_planilha()
                    print(f'[sheets_sync] {agora.strftime("%H:%M")} — {total} empresas, {cells} células atualizadas')
                else:
                    print(f'[sheets_sync] Fora do horário ({agora.strftime("%a %H:%M")}) — sincronização ignorada')
            except Exception as e:
                print(f'[sheets_sync] Erro: {e}')
            _time.sleep(3600)  # 1 hora

    t = threading.Thread(target=_loop, daemon=True, name='sheets-sync')
    t.start()
    print('[sheets_sync] Thread iniciada (intervalo: 1h, seg-sex 8h-18h)')


def _iniciar_email_checker():
    """Inicia thread em background que verifica e-mails a cada 1 hora."""
    import threading
    import time as _time

    def _loop():
        # Aguarda 15s para o servidor subir completamente
        _time.sleep(15)
        while True:
            try:
                from email_checker import verificar_emails_movimentacao
                verificar_emails_movimentacao()
            except Exception as e:
                print(f'[email_checker] Erro na thread: {e}')
            _time.sleep(3600)  # 1 hora

    t = threading.Thread(target=_loop, daemon=True, name='email-checker')
    t.start()
    print('[email_checker] Thread iniciada (intervalo: 1h, primeira execução em 15s)')


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    database.add_coluna_se_necessario()  # migração segura
    database.init_db()
    _iniciar_email_checker()
    _iniciar_sheets_sync()
    from backup_sheets import iniciar_backup_diario
    iniciar_backup_diario()
    port = int(os.getenv('PORT', 5080))
    print(f'Portal Societário Sigma rodando em http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
