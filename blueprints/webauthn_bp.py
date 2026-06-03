"""
blueprints/webauthn_bp.py — Portal Societário Sigma
Endpoints WebAuthn/Passkey: registro e autenticação.

Fluxos:
  Registro:
    POST /webauthn/register-begin      → gera PublicKeyCredentialCreationOptions
    POST /webauthn/register-complete   → verifica resposta, salva credencial

  Autenticação (login ou step-up):
    GET  /webauthn/verify              → página de verificação (UI)
    POST /webauthn/auth-begin          → gera PublicKeyCredentialRequestOptions
    POST /webauthn/auth-complete       → verifica resposta, conclui login ou step-up
"""

import json
from datetime import datetime, timedelta

from flask import (
    Blueprint, request, session, redirect, url_for,
    render_template, jsonify, make_response
)

import webauthn
from webauthn.helpers import options_to_json, bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse

import database as db
from security import (
    RP_ID, RP_ORIGIN, RP_NAME,
    generate_device_token,
    get_trusted_device_days,
    should_require_stepup,
    evaluate_trusted_device,
)
from blueprints.auth import login_obrigatorio

webauthn_bp = Blueprint('webauthn', __name__, url_prefix='/webauthn')

# ─── Utilitários ───────────────────────────────────────────────────────────────

def _get_ip():
    return request.remote_addr or ''


def _get_ua():
    return request.headers.get('User-Agent', '')


def _current_user_id():
    """Retorna user_id da sessão (login completo ou em andamento)."""
    return session.get('user_id') or session.get('_2fa_user_id') or session.get('_webauthn_user_id')


def _current_user():
    user_id = _current_user_id()
    if not user_id:
        return None
    return db.get_user_by_id(user_id)


# ─── Página de verificação (UI) ───────────────────────────────────────────────

@webauthn_bp.route('/verify')
def verify_page():
    """
    Exibida quando é necessária verificação por passkey.
    Usada tanto no login (purpose=login) quanto em ações sensíveis (purpose=stepup).
    """
    purpose = request.args.get('purpose', 'login')   # 'login' | 'stepup'
    next_url = request.args.get('next', '/')
    reason  = request.args.get('reason', '')

    # Se login: precisa de user em trânsito
    if purpose == 'login':
        user_id = session.get('_webauthn_user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
    # Se stepup: precisa estar logado
    elif purpose == 'stepup':
        if login_obrigatorio():
            return redirect(url_for('auth.login'))
        user_id = session.get('user_id')
    else:
        return redirect(url_for('auth.login'))

    user = db.get_user_by_id(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    has_passkeys = db.count_webauthn_credentials(user_id) > 0

    return render_template(
        'webauthn/verificar.html',
        purpose=purpose,
        next_url=next_url,
        reason=reason,
        has_passkeys=has_passkeys,
        user_nome=user['nome'],
    )


# ─── Registro de Passkey ──────────────────────────────────────────────────────

@webauthn_bp.route('/register-begin', methods=['POST'])
def register_begin():
    """Gera opções de registro WebAuthn."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    user_id = session['user_id']
    user    = db.get_user_by_id(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    # Credenciais já cadastradas (para exclude_credentials — não re-registrar)
    existing_creds = db.get_webauthn_credentials(user_id)
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c['credential_id']))
        for c in existing_creds
    ]

    options = webauthn.generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_name=user['email'],
        user_display_name=user['nome'],
        user_id=str(user_id).encode(),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude,
        timeout=120_000,
    )

    # Guardar challenge na sessão (server-side, anti-replay)
    session['_webauthn_reg_challenge'] = bytes_to_base64url(options.challenge)

    db.security_log('passkey_register_begin', user_id=user_id,
                    ip=_get_ip(), user_agent=_get_ua())

    return jsonify(json.loads(options_to_json(options)))


@webauthn_bp.route('/register-complete', methods=['POST'])
def register_complete():
    """Verifica resposta de registro e salva a passkey."""
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    user_id = session['user_id']
    challenge_b64 = session.pop('_webauthn_reg_challenge', None)
    if not challenge_b64:
        return jsonify({'erro': 'Challenge expirado. Tente novamente.'}), 400

    credential_data = request.get_json()
    if not credential_data:
        return jsonify({'erro': 'Dados inválidos'}), 400

    name = credential_data.pop('friendly_name', 'Minha passkey') or 'Minha passkey'
    name = name.strip()[:80]  # limitar tamanho

    try:
        verified = webauthn.verify_registration_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=RP_ORIGIN,
            require_user_verification=False,
        )
    except InvalidRegistrationResponse as e:
        db.security_log('passkey_register_fail', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(), details=str(e))
        return jsonify({'erro': f'Verificação falhou: {str(e)}'}), 400
    except Exception as e:
        db.security_log('passkey_register_error', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(), details=str(e))
        return jsonify({'erro': 'Erro interno ao verificar passkey.'}), 500

    credential_id = bytes_to_base64url(verified.credential_id)
    public_key    = bytes_to_base64url(verified.credential_public_key)
    sign_count    = verified.sign_count
    aaguid        = str(verified.aaguid) if verified.aaguid else ''

    # Verificar se já existe
    if db.get_webauthn_credential_by_id(credential_id):
        return jsonify({'erro': 'Esta passkey já está cadastrada.'}), 409

    db.save_webauthn_credential(
        user_id=user_id,
        credential_id=credential_id,
        public_key=public_key,
        sign_count=sign_count,
        aaguid=aaguid,
        name=name,
    )

    db.security_log('passkey_register_ok', user_id=user_id,
                    ip=_get_ip(), user_agent=_get_ua(),
                    details=f'name={name} aaguid={aaguid}')

    return jsonify({'ok': True, 'nome': name})


# ─── Autenticação com Passkey ─────────────────────────────────────────────────

@webauthn_bp.route('/auth-begin', methods=['POST'])
def auth_begin():
    """
    Gera opções de autenticação WebAuthn.
    Funciona tanto para login (user_id em _webauthn_user_id) como para step-up (sessão ativa).
    """
    data    = request.get_json() or {}
    purpose = data.get('purpose', 'login')

    if purpose == 'login':
        user_id = session.get('_webauthn_user_id')
        if not user_id:
            return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    elif purpose == 'stepup':
        if login_obrigatorio():
            return jsonify({'erro': 'Não autorizado'}), 401
        user_id = session['user_id']
    else:
        return jsonify({'erro': 'Propósito inválido'}), 400

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    creds = db.get_webauthn_credentials(user_id)
    if not creds:
        return jsonify({'erro': 'Nenhuma passkey cadastrada. Cadastre uma antes de continuar.'}), 400

    allow_creds = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c['credential_id']))
        for c in creds
    ]

    options = webauthn.generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_creds,
        user_verification=UserVerificationRequirement.PREFERRED,
        timeout=120_000,
    )

    session['_webauthn_auth_challenge'] = bytes_to_base64url(options.challenge)
    session['_webauthn_auth_purpose']   = purpose

    return jsonify(json.loads(options_to_json(options)))


@webauthn_bp.route('/auth-complete', methods=['POST'])
def auth_complete():
    """
    Verifica resposta de autenticação WebAuthn.
    Conclui login ou libera step-up conforme o propósito.
    """
    challenge_b64 = session.pop('_webauthn_auth_challenge', None)
    purpose       = session.pop('_webauthn_auth_purpose', 'login')

    if not challenge_b64:
        return jsonify({'erro': 'Challenge expirado. Tente novamente.'}), 400

    credential_data = request.get_json()
    if not credential_data:
        return jsonify({'erro': 'Dados inválidos'}), 400

    # Identificar o usuário
    if purpose == 'login':
        user_id = session.get('_webauthn_user_id')
    else:
        user_id = session.get('user_id')

    if not user_id:
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    # Localizar a credencial usada
    raw_id = credential_data.get('rawId') or credential_data.get('id')
    if not raw_id:
        return jsonify({'erro': 'Credencial inválida'}), 400

    cred_record = db.get_webauthn_credential_by_id(raw_id)
    if not cred_record or cred_record['user_id'] != user_id:
        db.record_failed_attempt(_get_ip(), user_id, 'webauthn')
        db.security_log('passkey_auth_fail', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(),
                        details='credential_not_found')
        return jsonify({'erro': 'Passkey não reconhecida.'}), 400

    try:
        verified = webauthn.verify_authentication_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=RP_ORIGIN,
            credential_public_key=base64url_to_bytes(cred_record['public_key']),
            credential_current_sign_count=cred_record['sign_count'],
            require_user_verification=False,
        )
    except InvalidAuthenticationResponse as e:
        db.record_failed_attempt(_get_ip(), user_id, 'webauthn')
        db.security_log('passkey_auth_fail', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(), details=str(e))
        return jsonify({'erro': 'Verificação falhou. Tente novamente.'}), 400
    except Exception as e:
        db.security_log('passkey_auth_error', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(), details=str(e))
        return jsonify({'erro': 'Erro interno ao verificar passkey.'}), 500

    # Atualizar sign_count (anti-replay)
    db.update_webauthn_sign_count(cred_record['credential_id'], verified.new_sign_count)

    db.security_log('passkey_auth_ok', user_id=user_id,
                    ip=_get_ip(), user_agent=_get_ua(),
                    details=f'purpose={purpose}')

    # ── Concluir conforme propósito ────────────────────────────────────────────

    mark_trusted = credential_data.get('mark_trusted', True)
    is_admin     = bool(user['is_admin'])
    days         = get_trusted_device_days(is_admin)

    response_data = {'ok': True, 'purpose': purpose}

    if purpose == 'login':
        # Limpar sessão temporária de login
        session.pop('_webauthn_user_id', None)
        session.pop('_2fa_user_id', None)
        session.pop('_2fa_email', None)

        # Estabelecer sessão autenticada
        session.permanent = True
        session['user_id']    = user_id
        session['user_nome']  = user['nome']
        session['is_admin']   = is_admin

        if user['primeiro_acesso']:
            response_data['redirect'] = url_for('auth.redefinir_senha')
        else:
            response_data['redirect'] = url_for('dashboard')

    elif purpose == 'stepup':
        # Marcar step-up na sessão
        session['_stepup_verified_at'] = datetime.utcnow().isoformat()
        next_url = request.args.get('next') or '/'
        response_data['redirect'] = next_url

    # Criar dispositivo confiável se solicitado
    resp = make_response(jsonify(response_data))
    if mark_trusted:
        device_token = generate_device_token()
        expires_at   = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        ua = _get_ua()
        db.create_trusted_device(
            user_id=user_id,
            device_token=device_token,
            device_name=_detect_device_name(ua),
            ip=_get_ip(),
            user_agent=ua,
            expires_at=expires_at,
        )
        db.security_log('trusted_device_created', user_id=user_id,
                        ip=_get_ip(), user_agent=_get_ua(),
                        details=f'expires={expires_at}')
        resp.set_cookie(
            'trusted_device',
            device_token,
            max_age=days * 86400,
            httponly=True,
            secure=True,
            samesite='Lax',
        )

    return resp


# ─── Utilitários internos ─────────────────────────────────────────────────────

def _detect_device_name(ua: str) -> str:
    """Detecta nome amigável do dispositivo pelo User-Agent."""
    ua_lower = ua.lower()
    if 'iphone' in ua_lower:
        return 'iPhone'
    if 'ipad' in ua_lower:
        return 'iPad'
    if 'android' in ua_lower:
        if 'mobile' in ua_lower:
            return 'Android (celular)'
        return 'Android (tablet)'
    if 'macintosh' in ua_lower or 'mac os' in ua_lower:
        return 'Mac'
    if 'windows' in ua_lower:
        return 'Windows'
    if 'linux' in ua_lower:
        return 'Linux'
    return 'Dispositivo desconhecido'
