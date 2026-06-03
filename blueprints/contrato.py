"""
blueprints/contrato.py — Módulo Elaboração de Contrato Social
Serve a interface existente (index.html) sem nenhuma modificação.
As rotas /upload, /gerar, /download ficam no portal.py (root).
"""
from flask import Blueprint, render_template, session, redirect, url_for
from blueprints.auth import login_obrigatorio

contrato_bp = Blueprint('contrato', __name__, url_prefix='/contrato')


@contrato_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    return render_template('index.html')
