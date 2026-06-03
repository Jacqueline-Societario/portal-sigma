"""
blueprints/diario_oficial.py — Módulo Diário Oficial
Consulta e monitoramento de publicações no Diário Oficial.
"""
from flask import Blueprint, render_template, session, redirect, url_for
from blueprints.auth import login_obrigatorio

diario_oficial_bp = Blueprint('diario_oficial', __name__, url_prefix='/diario-oficial')


@diario_oficial_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    return render_template('diario_oficial/index.html')
