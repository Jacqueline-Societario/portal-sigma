"""
blueprints/avisos.py — Painel de Avisos
Gestão de comunicados internos para a equipe do Societário.
Rotas de acesso geral (/api/avisos/proximo e /api/avisos/<id>/ler) ficam em portal.py.
"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from blueprints.auth import login_obrigatorio
import database

avisos_bp = Blueprint('avisos', __name__, url_prefix='/avisos')


def _requer_avisos():
    """Verifica login e permissão ao módulo avisos."""
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    uid = session.get('user_id')
    if not database.get_user_permission(uid, 'avisos'):
        return redirect(url_for('acesso_negado'))
    return None


# ── Página de gestão ──────────────────────────────────────────────────────────

@avisos_bp.route('/', methods=['GET'])
def index():
    redir = _requer_avisos()
    if redir:
        return redir
    return render_template('avisos/index.html')


# ── API — gestão (admin / permissão avisos) ───────────────────────────────────

@avisos_bp.route('/api', methods=['GET'])
def api_listar():
    redir = _requer_avisos()
    if redir:
        return jsonify({'erro': 'Não autorizado'}), 403
    return jsonify(database.listar_avisos())


@avisos_bp.route('/api', methods=['POST'])
def api_criar():
    redir = _requer_avisos()
    if redir:
        return jsonify({'erro': 'Não autorizado'}), 403
    d = request.get_json(silent=True) or {}
    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'erro': 'Título obrigatório'}), 400
    aviso_id = database.criar_aviso(
        titulo=titulo,
        corpo=(d.get('corpo') or '').strip(),
        tipo=d.get('tipo', 'aviso'),
        link=(d.get('link') or '').strip(),
        data_expiracao=d.get('data_expiracao') or None,
        rodizio=int(d.get('rodizio', 1)),
        user_id=session.get('user_id'),
    )
    return jsonify({'id': aviso_id}), 201


@avisos_bp.route('/api/<int:aviso_id>', methods=['PUT'])
def api_editar(aviso_id):
    redir = _requer_avisos()
    if redir:
        return jsonify({'erro': 'Não autorizado'}), 403
    d = request.get_json(silent=True) or {}
    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'erro': 'Título obrigatório'}), 400
    database.editar_aviso(
        aviso_id=aviso_id,
        titulo=titulo,
        corpo=(d.get('corpo') or '').strip(),
        tipo=d.get('tipo', 'aviso'),
        link=(d.get('link') or '').strip(),
        data_expiracao=d.get('data_expiracao') or None,
        ativo=int(d.get('ativo', 1)),
        rodizio=int(d.get('rodizio', 1)),
    )
    return jsonify({'ok': True})


@avisos_bp.route('/api/<int:aviso_id>', methods=['DELETE'])
def api_deletar(aviso_id):
    redir = _requer_avisos()
    if redir:
        return jsonify({'erro': 'Não autorizado'}), 403
    database.deletar_aviso(aviso_id)
    return jsonify({'ok': True})


@avisos_bp.route('/api/<int:aviso_id>/toggle', methods=['POST'])
def api_toggle(aviso_id):
    redir = _requer_avisos()
    if redir:
        return jsonify({'erro': 'Não autorizado'}), 403
    d = request.get_json(silent=True) or {}
    campo = d.get('campo')
    valor = d.get('valor')
    if campo not in ('ativo', 'rodizio') or valor not in (0, 1):
        return jsonify({'erro': 'Parâmetros inválidos'}), 400
    database.toggle_aviso(aviso_id, campo, valor)
    return jsonify({'ok': True})
