"""
blueprints/auth.py — Autenticação individual por usuária
Inclui: login com verificação adaptativa (Passkey/WebAuthn), logout
e redefinição de senha (e-mail apenas para recuperação, não para login).
"""
from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_user_by_email, get_user_by_id, atualizar_senha, criar_otp, verificar_otp
from database import record_failed_attempt, security_log
from email_utils import enviar_codigo

auth_bp = Blueprint('auth', __name__)


def login_obrigatorio():
    """Retorna True se a usuária NÃO está autenticada."""
    return not session.get('user_id')


# ─── Login com verificação adaptativa ─────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        ip    = request.remote_addr or ''
        ua    = request.headers.get('User-Agent', '')

        user = get_user_by_email(email)
        if user and check_password_hash(user['senha_hash'], senha):
            # Credenciais OK — avaliar se precisa de passkey
            from security import evaluate_trusted_device
            from database import count_webauthn_credentials

            device_token = request.cookies.get('trusted_device', '')
            status, reason = evaluate_trusted_device(user, device_token, ip, ua)

            has_passkeys = count_webauthn_credentials(user['id']) > 0

            if status == 'ok':
                # Dispositivo confiável válido — login direto
                security_log('login_direto', user_id=user['id'], ip=ip, user_agent=ua,
                             details='trusted_device')
                session.permanent  = True
                session['user_id']   = user['id']
                session['user_nome'] = user['nome']
                session['is_admin']  = bool(user['is_admin'])
                if user['primeiro_acesso']:
                    return redirect(url_for('auth.redefinir_senha'))
                return redirect(url_for('dashboard'))

            elif not has_passkeys:
                # Sem passkeys cadastradas → login direto + aviso para cadastrar
                security_log('login_sem_passkey', user_id=user['id'], ip=ip, user_agent=ua)
                session.permanent  = True
                session['user_id']   = user['id']
                session['user_nome'] = user['nome']
                session['is_admin']  = bool(user['is_admin'])
                session['_avisar_cadastrar_passkey'] = True
                if user['primeiro_acesso']:
                    return redirect(url_for('auth.redefinir_senha'))
                return redirect(url_for('dashboard'))

            else:
                # Precisa verificar com passkey
                security_log('login_requer_passkey', user_id=user['id'], ip=ip,
                             user_agent=ua, details=reason)
                session['_webauthn_user_id'] = user['id']
                return redirect(url_for('webauthn.verify_page',
                                        purpose='login', reason=reason))
        else:
            record_failed_attempt(ip, None, 'login')
            security_log('login_falhou', ip=ip, user_agent=ua,
                         details=f'email={email}')
            erro = 'E-mail ou senha incorretos. Tente novamente.'

    return render_template('login_portal.html', erro=erro)


# ─── Logout ───────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# ─── Recuperação de senha com código por e-mail ───────────────────────────────

@auth_bp.route('/esqueceu-senha', methods=['GET', 'POST'])
def esqueceu_senha():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    erro = None
    sucesso = None
    etapa = request.form.get('etapa', '1')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = get_user_by_email(email)

        if etapa == '1':
            # Etapa 1: informar e-mail → enviar código
            if not user:
                # Por segurança, não revelar se e-mail existe — fingir que enviou
                etapa = '2'
                session['_rec_email'] = email
            else:
                codigo = criar_otp(user['id'], motivo='recuperacao')
                ok = enviar_codigo(user['email'], user['nome'], codigo, motivo='recuperacao')
                if not ok:
                    erro = 'Não foi possível enviar o código. Tente novamente.'
                    etapa = '1'
                else:
                    session['_rec_email'] = email
                    etapa = '2'

        elif etapa == '2':
            # Etapa 2: verificar código → avançar para nova senha
            email = session.get('_rec_email', email)
            user = get_user_by_email(email)
            codigo = request.form.get('codigo', '').strip()

            if not user:
                erro = 'Sessão expirada. Tente novamente.'
                etapa = '1'
            elif not codigo or len(codigo) != 6 or not codigo.isdigit():
                erro = 'Informe o código de 6 dígitos recebido por e-mail.'
                etapa = '2'
            elif not verificar_otp(user['id'], codigo, motivo='recuperacao'):
                erro = 'Código inválido ou expirado. Solicite um novo código.'
                etapa = '2'
            else:
                session['_rec_user_id'] = user['id']
                etapa = '3'

        elif etapa == '3':
            # Etapa 3: definir nova senha
            user_id_rec = session.get('_rec_user_id')
            nova_senha = request.form.get('nova_senha', '')
            confirmar = request.form.get('confirmar_senha', '')

            if not user_id_rec:
                erro = 'Sessão expirada. Tente novamente.'
                etapa = '1'
            elif len(nova_senha) < 6:
                erro = 'A nova senha deve ter pelo menos 6 caracteres.'
                etapa = '3'
            elif nova_senha != confirmar:
                erro = 'As senhas não coincidem.'
                etapa = '3'
            else:
                atualizar_senha(user_id_rec, generate_password_hash(nova_senha))
                session.pop('_rec_email', None)
                session.pop('_rec_user_id', None)
                sucesso = 'Senha redefinida com sucesso! Você já pode fazer login.'
                etapa = 'ok'

    email_rec = session.get('_rec_email', request.form.get('email', ''))
    email_mascarado = _mascarar_email(email_rec)

    return render_template('esqueceu_senha.html',
                           erro=erro, sucesso=sucesso,
                           etapa=etapa,
                           email=email_rec,
                           email_mascarado=email_mascarado)


# ─── Redefinir senha (usuária logada) ─────────────────────────────────────────

@auth_bp.route('/redefinir-senha', methods=['GET', 'POST'])
def redefinir_senha():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    erro = None
    sucesso = None

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmar = request.form.get('confirmar_senha', '')
        user = get_user_by_id(session['user_id'])

        if not check_password_hash(user['senha_hash'], senha_atual):
            erro = 'Senha atual incorreta.'
        elif len(nova_senha) < 6:
            erro = 'A nova senha deve ter pelo menos 6 caracteres.'
        elif nova_senha != confirmar:
            erro = 'A confirmação de senha não coincide.'
        else:
            atualizar_senha(session['user_id'], generate_password_hash(nova_senha))
            session['primeiro_acesso'] = False
            sucesso = 'Senha alterada com sucesso!'

    return render_template('redefinir_senha.html', erro=erro, sucesso=sucesso)


# ─── Utilitários ─────────────────────────────────────────────────────────────

def _mascarar_email(email: str) -> str:
    """Ex: 'societario3@gsigma.com.br' → 's**********3@gsigma.com.br'"""
    if '@' not in email:
        return email
    local, dominio = email.split('@', 1)
    if len(local) <= 2:
        return email
    mascarado = local[0] + '*' * (len(local) - 2) + local[-1]
    return f'{mascarado}@{dominio}'
