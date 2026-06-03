"""
blueprints/admin.py — Painel Administrativo (apenas Jacqueline Benedito / is_admin=1)
Controle de permissões por ferramenta e dashboard de atividade.
"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from blueprints.auth import login_obrigatorio
import database

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required():
    """Retorna True se o usuário NÃO é admin (bloquear acesso)."""
    if login_obrigatorio():
        return True
    return not session.get('is_admin')


@admin_bp.route('/')
def dashboard():
    if admin_required():
        return redirect(url_for('auth.login'))

    users      = database.get_all_users_active()
    all_users  = database.get_all_users()       # inclui inativos (para seção gerenciamento)
    all_perms  = database.get_all_permissions()
    last_access = database.get_last_access_per_user()
    activity   = database.get_activity_summary(50)
    tools      = database.TOOLS

    # Montar estrutura de dados para o template:
    # user_data = [{id, nome, email, is_admin, permissions: {tool: bool}, last_seen: str}]
    user_data = []
    for u in users:
        uid = u['id']
        user_perms = all_perms.get(uid, {})
        # Permissões efetivas por ferramenta (padrão True se não registrado)
        perms = {tool: user_perms.get(tool, True) for tool in tools}
        # Último acesso geral (qualquer ferramenta)
        user_last = last_access.get(uid, {})
        last_seen = max(user_last.values()) if user_last else None
        user_data.append({
            'id':       uid,
            'nome':     u['nome'],
            'email':    u['email'],
            'is_admin': bool(u['is_admin']),
            'perms':    perms,
            'last_seen': last_seen,
        })

    security_logs = database.get_security_logs(50)

    return render_template('admin/dashboard.html',
                           users=user_data,
                           all_users=[dict(u) for u in all_users],
                           tools=tools,
                           activity=activity,
                           security_logs=security_logs)


@admin_bp.route('/toggle', methods=['POST'])
def toggle_permission():
    """API: toggle permissão de um usuário para uma ferramenta."""
    if admin_required():
        return jsonify({'erro': 'Acesso negado'}), 403

    data    = request.get_json()
    user_id = data.get('user_id')
    tool    = data.get('tool')
    allowed = data.get('allowed')  # True ou False

    if not user_id or not tool or allowed is None:
        return jsonify({'erro': 'Parâmetros inválidos'}), 400

    if tool not in database.TOOLS:
        return jsonify({'erro': 'Ferramenta inválida'}), 400

    # Admin não pode ter permissões bloqueadas
    from database import get_user_by_id
    user = get_user_by_id(user_id)
    if user and user['is_admin']:
        return jsonify({'erro': 'Não é possível restringir acesso do administrador'}), 400

    database.set_user_permission(int(user_id), tool, bool(allowed))
    return jsonify({'ok': True, 'user_id': user_id, 'tool': tool, 'allowed': allowed})


# ─── Backup diário ─────────────────────────────────────────────────────────────

@admin_bp.route('/backup/status')
def backup_status():
    """Retorna status do último backup (JSON)."""
    if admin_required():
        return jsonify({'erro': 'Não autorizado'}), 403
    import os, json as _json
    from backup_sheets import BACKUP_CONFIG_PATH, BACKUP_LOG_PATH
    cfg = {}
    if os.path.exists(BACKUP_CONFIG_PATH):
        with open(BACKUP_CONFIG_PATH) as f:
            cfg = _json.load(f)
    log_lines = []
    if os.path.exists(BACKUP_LOG_PATH):
        with open(BACKUP_LOG_PATH, encoding='utf-8') as f:
            log_lines = f.readlines()[-30:]
    sid = cfg.get('backup_spreadsheet_id', '')
    return jsonify({
        'ultimo_backup':        cfg.get('ultimo_backup', '—'),
        'status':               cfg.get('ultimo_backup_status', '—'),
        'total_empresas':       cfg.get('ultimo_backup_total', 0),
        'spreadsheet_id':       sid,
        'spreadsheet_url':      f'https://docs.google.com/spreadsheets/d/{sid}' if sid else '',
        'log':                  ''.join(log_lines),
    })


# ─── Gerenciamento de Usuários ──────────────────────────────────────────────────

@admin_bp.route('/usuarios/criar', methods=['POST'])
def usuarios_criar():
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    data = request.get_json()
    nome  = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip().lower()
    result = database.criar_usuario(nome, email)
    return jsonify(result)


@admin_bp.route('/usuarios/<int:user_id>/editar', methods=['POST'])
def usuarios_editar(user_id):
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    data = request.get_json()
    nome = (data.get('nome') or '').strip()
    result = database.editar_usuario(user_id, nome)
    return jsonify(result)


@admin_bp.route('/usuarios/<int:user_id>/toggle-ativo', methods=['POST'])
def usuarios_toggle_ativo(user_id):
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    data = request.get_json()
    ativo = bool(data.get('ativo'))
    result = database.toggle_usuario_ativo(user_id, ativo)
    return jsonify(result)


@admin_bp.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def usuarios_excluir(user_id):
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    result = database.excluir_usuario(user_id)
    return jsonify(result)


@admin_bp.route('/usuarios/<int:user_id>/redefinir-senha', methods=['POST'])
def usuarios_redefinir_senha(user_id):
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    result = database.redefinir_senha_usuario(user_id)
    return jsonify(result)


# ─── Backup diário ─────────────────────────────────────────────────────────────

@admin_bp.route('/usuarios/<int:user_id>/passkeys', methods=['GET'])
def usuarios_listar_passkeys(user_id):
    """Retorna passkeys de um usuário (para o painel admin)."""
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403
    passkeys = database.get_webauthn_credentials(user_id)
    return jsonify({'ok': True, 'passkeys': passkeys})


@admin_bp.route('/usuarios/<int:user_id>/passkeys/<int:cred_id>/revogar', methods=['POST'])
def usuarios_revogar_passkey(user_id, cred_id):
    """
    Reset administrativo de passkey. Exige step-up recente do admin.
    Registra log detalhado.
    """
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    from security import should_require_stepup_for_session
    from flask import session as s

    required, reason = should_require_stepup_for_session(s, 'reset_passkey', is_admin=True)
    if required:
        return jsonify({
            'ok': False,
            'stepup_required': True,
            'reason': reason,
            'verify_url': '/webauthn/verify?purpose=stepup&next=/admin/',
        }), 403

    database.delete_webauthn_credential(cred_id, user_id)
    database.security_log(
        'admin_passkey_reset',
        user_id=s.get('user_id'),
        ip=request.remote_addr or '',
        user_agent=request.headers.get('User-Agent', ''),
        details=f'target_user={user_id} cred_id={cred_id}',
    )
    return jsonify({'ok': True})


@admin_bp.route('/usuarios/<int:user_id>/dispositivos/revogar-todos', methods=['POST'])
def usuarios_revogar_dispositivos(user_id):
    """Revoga todos os dispositivos confiáveis de um usuário."""
    if admin_required():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    database.revoke_all_trusted_devices(user_id)
    database.security_log(
        'admin_devices_revoked',
        user_id=session.get('user_id'),
        ip=request.remote_addr or '',
        user_agent=request.headers.get('User-Agent', ''),
        details=f'target_user={user_id}',
    )
    return jsonify({'ok': True})


@admin_bp.route('/seguranca/logs')
def seguranca_logs():
    """Retorna logs de segurança recentes (JSON)."""
    if admin_required():
        return jsonify({'erro': 'Não autorizado'}), 403
    logs = database.get_security_logs(200)
    return jsonify({'logs': logs})


# ─── Backup diário ─────────────────────────────────────────────────────────────

@admin_bp.route('/backup/executar', methods=['POST'])
def backup_executar():
    """Dispara backup manual imediatamente (resposta assíncrona)."""
    if admin_required():
        return jsonify({'erro': 'Não autorizado'}), 403
    import threading
    from backup_sheets import executar_backup
    threading.Thread(target=executar_backup, daemon=True).start()
    return jsonify({'ok': True, 'mensagem': 'Backup iniciado em background. Verifique /admin/backup/status em instantes.'})
