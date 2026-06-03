"""
security.py — Portal Societário Sigma
Lógica de verificação adaptativa (Passkey/WebAuthn).

Decide quando exigir verificação extra, gerencia dispositivos confiáveis,
logs de segurança e tentativas falhas.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta

# ─── Configuração de Segurança ─────────────────────────────────────────────────

# Nível de segurança: 1 (prático), 2 (recomendado), 3 (rigoroso)
SECURITY_LEVEL = int(os.getenv('SECURITY_LEVEL', '2'))

# Configurações para administradores
ADMIN_REQUIRE_PASSKEY_EVERY_LOGIN  = os.getenv('ADMIN_REQUIRE_PASSKEY_EVERY_LOGIN', 'false').lower() == 'true'
ADMIN_TRUSTED_DEVICE_DAYS          = int(os.getenv('ADMIN_TRUSTED_DEVICE_DAYS', '15'))
ADMIN_STEP_UP_TTL_MINUTES          = int(os.getenv('ADMIN_STEP_UP_TTL_MINUTES', '15'))
ADMIN_REQUIRE_PASSKEY_SENSITIVE    = os.getenv('ADMIN_REQUIRE_PASSKEY_FOR_SENSITIVE_ACTIONS', 'true').lower() == 'true'

# Configurações para usuários comuns
USER_TRUSTED_DEVICE_DAYS           = int(os.getenv('TRUSTED_DEVICE_DAYS', '30'))
USER_STEP_UP_TTL_MINUTES           = int(os.getenv('STEP_UP_TTL_MINUTES', '15'))

# RP WebAuthn
RP_ID     = os.getenv('WEBAUTHN_RP_ID', 'societario.gsigma.com.br')
RP_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', 'https://societario.gsigma.com.br')
RP_NAME   = 'Portal Societário Sigma'

# Ações sensíveis — exigem step-up recente
SENSITIVE_ACTIONS = {
    'download_document',
    'change_password',
    'change_email',
    'change_permissions',
    'admin_area',
    'delete_file',
    'change_client_data',
    'reset_passkey',
}

# Rate limit de tentativas falhas
MAX_FAILED_ATTEMPTS           = 5
FAILED_ATTEMPT_WINDOW_MINUTES = 15


# ─── Utilitários ───────────────────────────────────────────────────────────────

def _ip_prefix(ip: str) -> str:
    """Primeiros 3 octetos do IPv4 ou primeiros 4 grupos do IPv6."""
    if not ip:
        return ''
    parts = ip.split('.')
    if len(parts) == 4:
        return '.'.join(parts[:3])
    return ':'.join(ip.split(':')[:4])


def _ua_fingerprint(ua: str) -> str:
    """Fingerprint simplificado do User-Agent."""
    return hashlib.md5(ua[:200].encode()).hexdigest()[:12] if ua else ''


def get_trusted_device_days(is_admin: bool = False) -> int:
    return ADMIN_TRUSTED_DEVICE_DAYS if is_admin else USER_TRUSTED_DEVICE_DAYS


def generate_device_token() -> str:
    """Token seguro para cookie de dispositivo confiável."""
    return secrets.token_urlsafe(32)


# ─── Verificação adaptativa — login ───────────────────────────────────────────

def should_require_stepup(user: dict, current_ip: str, current_ua: str, action: str = 'login') -> tuple:
    """
    Decide se deve exigir verificação Passkey/WebAuthn no momento do login.

    Args:
        user: dict com id, is_admin, senha_alterada_em (opcional)
        current_ip: IP do request atual
        current_ua: User-Agent do request atual
        action: 'login' ou nome de ação sensível

    Returns:
        (required: bool, reason: str)
    """
    import database as db

    is_admin = bool(user['is_admin'])
    user_id  = user['id']

    # ── Ação sensível ──────────────────────────────────────────────────────────
    if action in SENSITIVE_ACTIONS:
        if is_admin and ADMIN_REQUIRE_PASSKEY_SENSITIVE:
            return True, 'acao_sensivel_admin'
        if SECURITY_LEVEL >= 1:
            return True, 'acao_sensivel'

    # ── Admin exige passkey em todo login? ─────────────────────────────────────
    if is_admin and ADMIN_REQUIRE_PASSKEY_EVERY_LOGIN and action == 'login':
        return True, 'admin_toda_sessao'

    # ── Muitas tentativas falhas (rate limit) ──────────────────────────────────
    if db.count_failed_attempts(current_ip, user_id) >= MAX_FAILED_ATTEMPTS:
        return True, 'muitas_tentativas'

    # ── Verificar dispositivo confiável ────────────────────────────────────────
    # Não temos acesso ao cookie aqui — o caller passa device_token se houver
    # O check de cookie é feito no blueprint antes de chamar esta função.
    # Se chegou aqui sem dispositivo confiável validado = novo dispositivo.
    return True, 'novo_dispositivo'


def evaluate_trusted_device(user: dict, device_token: str, current_ip: str, current_ua: str) -> tuple:
    """
    Avalia se o cookie de dispositivo confiável é válido e se o contexto bate.

    Returns:
        ('ok', '') — dispositivo válido, não exige passkey
        ('fail', reason) — exige passkey com motivo
    """
    import database as db

    if not device_token:
        return 'fail', 'sem_dispositivo'

    is_admin = bool(user['is_admin'])
    user_id  = user['id']

    device_info = db.get_trusted_device_info(user_id, device_token)
    if not device_info:
        return 'fail', 'dispositivo_invalido'

    # Expiração
    expires_at = datetime.fromisoformat(device_info['expires_at'])
    if expires_at <= datetime.utcnow():
        return 'fail', 'dispositivo_expirado'

    # Revogado
    if device_info.get('revoked'):
        return 'fail', 'dispositivo_revogado'

    # Nível 2+: verificar mudança de IP e User-Agent
    if SECURITY_LEVEL >= 2:
        stored_ip = _ip_prefix(device_info.get('ip', ''))
        curr_ip   = _ip_prefix(current_ip)
        if stored_ip and curr_ip and stored_ip != curr_ip:
            return 'fail', 'mudanca_de_ip'

        stored_ua = _ua_fingerprint(device_info.get('user_agent', ''))
        curr_ua   = _ua_fingerprint(current_ua)
        if stored_ua and curr_ua and stored_ua != curr_ua:
            return 'fail', 'mudanca_de_navegador'

    # Rate limit mesmo em dispositivo confiável
    if db.count_failed_attempts(current_ip, user_id) >= MAX_FAILED_ATTEMPTS:
        return 'fail', 'muitas_tentativas'

    # Atualizar last_seen
    db.update_trusted_device_last_seen(device_token)
    return 'ok', ''


# ─── Step-up em sessão já logada ──────────────────────────────────────────────

def should_require_stepup_for_session(session: dict, action: str, is_admin: bool = False) -> tuple:
    """
    Verifica se deve pedir step-up durante sessão ativa.
    Usa _stepup_verified_at para não pedir a cada clique.

    Returns: (required: bool, reason: str)
    """
    if action not in SENSITIVE_ACTIONS:
        return False, 'acao_nao_sensivel'

    ttl = ADMIN_STEP_UP_TTL_MINUTES if is_admin else USER_STEP_UP_TTL_MINUTES
    verified_at_str = session.get('_stepup_verified_at')

    if verified_at_str:
        try:
            verified_dt = datetime.fromisoformat(verified_at_str)
            if datetime.utcnow() - verified_dt < timedelta(minutes=ttl):
                return False, 'stepup_recente'
        except (ValueError, TypeError):
            pass

    return True, 'stepup_necessario'
