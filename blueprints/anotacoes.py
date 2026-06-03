"""
blueprints/anotacoes.py — Módulo de Anotações Pessoais
Sticky notes draggáveis e redimensionáveis, privados por usuário.
"""
from flask import Blueprint, render_template, session, redirect, url_for
from blueprints.auth import login_obrigatorio

anotacoes_bp = Blueprint('anotacoes', __name__, url_prefix='/anotacoes')


@anotacoes_bp.route('/', methods=['GET'])
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    return render_template('anotacoes/index.html')
