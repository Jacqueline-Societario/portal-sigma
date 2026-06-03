"""
blueprints/movimentacao.py — Painel de Movimentação de Empresas
Exibe entradas e saídas alimentadas via e-mail (leitura Gmail API).
"""
import json
from flask import Blueprint, render_template, redirect, url_for, jsonify
from blueprints.auth import login_obrigatorio
import database

movimentacao_bp = Blueprint('movimentacao', __name__, url_prefix='/movimentacao')


@movimentacao_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    entradas_raw = database.get_movimentacoes('entrada')
    saidas       = database.get_movimentacoes('saida')
    ultima       = database.get_ultima_verificacao_email()

    # Decodificar JSON de contatos para cada entrada
    entradas = []
    for e in entradas_raw:
        e = dict(e)
        try:
            e['contatos_list'] = json.loads(e.get('contatos', '[]'))
        except Exception:
            e['contatos_list'] = []
        entradas.append(e)

    novos_total = ultima['novos'] if ultima else 0

    return render_template('movimentacao/index.html',
                           entradas=entradas,
                           saidas=saidas,
                           ultima_verificacao=ultima,
                           novos_total=novos_total)


@movimentacao_bp.route('/verificar-agora', methods=['POST'])
def verificar_agora():
    """Dispara verificação manual de e-mails (somente leitura no Gmail)."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    try:
        from email_checker import verificar_emails_movimentacao
        novos = verificar_emails_movimentacao()
        return jsonify({'ok': True, 'novos': novos})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
