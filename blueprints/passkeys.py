"""
blueprints/passkeys.py — Portal Societário Sigma
Gerenciamento de passkeys e dispositivos confiáveis pelo usuário.

Rotas:
  GET  /passkeys/                   → listar passkeys e dispositivos confiáveis
  POST /passkeys/renomear           → renomear passkey
  POST /passkeys/remover            → remover passkey
  POST /passkeys/dispositivos/revogar   → revogar dispositivo confiável
"""

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from blueprints.auth import login_obrigatorio
import database as db
from security import should_require_stepup_for_session, SENSITIVE_ACTIONS

passkeys_bp = Blueprint('passkeys', __name__, url_prefix='/passkeys')


@passkeys_bp.route('/')
def index():
    """Lista passkeys cadastradas e dispositivos confiáveis."""
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    user_id  = session['user_id']
    is_admin = session.get('is_admin', False)

    passkeys  = db.get_webauthn_credentials(user_id)
    devices   = db.list_trusted_devices(user_id)

    return render_template(
        'passkeys/index.html',
        passkeys=passkeys,
        devices=devices,
        is_admin=is_admin,
    )


@passkeys_bp.route('/renomear', methods=['POST'])
def renomear():
    """Renomeia uma passkey."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    data    = request.get_json() or {}
    cred_id = data.get('id')
    name    = (data.get('name') or '').strip()[:80]

    if not cred_id or not name:
        return jsonify({'erro': 'Parâmetros inválidos'}), 400

    db.rename_webauthn_credential(int(cred_id), session['user_id'], name)
    return jsonify({'ok': True})


@passkeys_bp.route('/remover', methods=['POST'])
def remover():
    """
    Remove uma passkey. Exige step-up se for a operação de reset de passkey de outro usuário
    (admin) ou se o usuário for admin (ação sensível).
    """
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    user_id  = session['user_id']
    is_admin = session.get('is_admin', False)

    data    = request.get_json() or {}
    cred_id = data.get('id')

    if not cred_id:
        return jsonify({'erro': 'ID da passkey não informado'}), 400

    # Verificar step-up para ação sensível
    if is_admin:
        required, reason = should_require_stepup_for_session(session, 'reset_passkey', is_admin=True)
        if required:
            return jsonify({
                'stepup_required': True,
                'next': url_for('passkeys.index'),
                'reason': reason,
            }), 403

    # Garantir que não está removendo a última passkey sem ter outra
    count = db.count_webauthn_credentials(user_id)
    if count <= 1:
        return jsonify({'erro': 'Você deve manter pelo menos uma passkey cadastrada.'}), 400

    db.delete_webauthn_credential(int(cred_id), user_id)
    db.security_log('passkey_removed', user_id=user_id,
                    ip=request.remote_addr or '',
                    user_agent=request.headers.get('User-Agent', ''),
                    details=f'cred_id={cred_id}')

    return jsonify({'ok': True})


@passkeys_bp.route('/dispositivos/revogar', methods=['POST'])
def revogar_dispositivo():
    """Revoga um dispositivo confiável."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    data      = request.get_json() or {}
    device_id = data.get('id')

    if not device_id:
        return jsonify({'erro': 'ID do dispositivo não informado'}), 400

    db.revoke_trusted_device(int(device_id), session['user_id'])
    db.security_log('trusted_device_revoked', user_id=session['user_id'],
                    ip=request.remote_addr or '',
                    user_agent=request.headers.get('User-Agent', ''),
                    details=f'device_id={device_id}')

    return jsonify({'ok': True})
