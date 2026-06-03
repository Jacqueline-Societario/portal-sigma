"""
blueprints/manuais.py — Módulo Área de Conhecimentos/Manuais
Permite criar, editar e consultar manuais internos do departamento.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from blueprints.auth import login_obrigatorio
import database

manuais_bp = Blueprint('manuais', __name__, url_prefix='/manuais')

CATEGORIAS = [
    'Abertura de Empresa',
    'Alteração Contratual',
    'Encerramento de Empresa',
    'Licenciamento',
    'Documentos e Emissões',
    'Procurações',
    'Legislação',
    'Órgãos e Entidades',
    'Procedimentos Internos',
    'Geral',
]


@manuais_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    search = request.args.get('search', '').strip()
    manuais = database.listar_manuais(search=search if search else None)
    # Agrupar por categoria
    agrupados = {}
    for m in manuais:
        cat = m['categoria'] or 'Geral'
        agrupados.setdefault(cat, []).append(m)
    return render_template('manuais/index.html', agrupados=agrupados, categorias=CATEGORIAS, search=search)


@manuais_bp.route('/novo', methods=['GET', 'POST'])
def novo():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        categoria = request.form.get('categoria', 'Geral')
        conteudo = request.form.get('conteudo', '').strip()
        if not titulo or not conteudo:
            return render_template('manuais/form.html',
                                   categorias=CATEGORIAS,
                                   erro='Título e conteúdo são obrigatórios.',
                                   manual=None)
        manual_id = database.criar_manual(titulo, categoria, conteudo, session['user_id'])
        database.criar_notificacoes_para_evento(
            modulo='manuais',
            tipo_evento='manual_novo',
            titulo=f'Novo manual publicado — {titulo}',
            link_destino=f'/manuais/{manual_id}',
        )
        return redirect(url_for('manuais.ver', manual_id=manual_id))
    return render_template('manuais/form.html', categorias=CATEGORIAS, erro=None, manual=None)


@manuais_bp.route('/<int:manual_id>')
def ver(manual_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    manual = database.get_manual(manual_id)
    if not manual:
        return redirect(url_for('manuais.index'))
    return render_template('manuais/ver.html', manual=manual)


@manuais_bp.route('/<int:manual_id>/editar', methods=['GET', 'POST'])
def editar(manual_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    manual = database.get_manual(manual_id)
    if not manual:
        return redirect(url_for('manuais.index'))
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        categoria = request.form.get('categoria', 'Geral')
        conteudo = request.form.get('conteudo', '').strip()
        if not titulo or not conteudo:
            return render_template('manuais/form.html',
                                   categorias=CATEGORIAS,
                                   erro='Título e conteúdo são obrigatórios.',
                                   manual=manual)
        database.atualizar_manual(manual_id, titulo, categoria, conteudo)
        database.criar_notificacoes_para_evento(
            modulo='manuais',
            tipo_evento='manual_editado',
            titulo=f'Manual atualizado — {titulo}',
            link_destino=f'/manuais/{manual_id}',
        )
        return redirect(url_for('manuais.ver', manual_id=manual_id))
    return render_template('manuais/form.html', categorias=CATEGORIAS, erro=None, manual=manual)


@manuais_bp.route('/<int:manual_id>/excluir', methods=['POST'])
def excluir(manual_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    database.deletar_manual(manual_id)
    return redirect(url_for('manuais.index'))
