"""
email_utils.py — Envio de e-mails via Gmail API (societario1@gsigma.com.br)
Usa httpx + OAuth2 diretamente (sem dependência da lib google-auth).
Portal Societário Sigma Contabilidade
"""
import os
import json
import base64
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOKEN_LOCAL = os.path.join(BASE_DIR, 'credentials', 'token.json')
_TOKEN_FALLBACK = os.path.join(BASE_DIR, '..', '..', '..', 'credentials', 'token.json')
_TOKEN_DEFAULT = _TOKEN_LOCAL if os.path.exists(_TOKEN_LOCAL) else _TOKEN_FALLBACK
TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', _TOKEN_DEFAULT)
REMETENTE = 'societario1@gsigma.com.br'
_token_lock = threading.Lock()

_TOKEN_REFRESH_URL = 'https://oauth2.googleapis.com/token'
_GMAIL_SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'


def _load_token() -> dict:
    with open(TOKEN_PATH) as f:
        return json.load(f)


def _save_token(data: dict):
    with open(TOKEN_PATH, 'w') as f:
        json.dump(data, f)


def _get_access_token() -> str:
    """Retorna access_token válido, renovando via refresh_token se necessário."""
    import httpx
    with _token_lock:
        return _get_access_token_locked()


def _get_access_token_locked() -> str:
    """Execução protegida por lock — não chamar diretamente."""
    import httpx
    token = _load_token()

    # Verificar se o token atual ainda é válido (com margem de 60s)
    expiry = token.get('expiry') or token.get('token_expiry') or ''
    access_token = token.get('token') or token.get('access_token', '')

    needs_refresh = True
    if access_token and expiry:
        try:
            # Formato ISO: '2026-04-06T14:30:00.000000Z' ou timestamp
            if isinstance(expiry, (int, float)):
                needs_refresh = time.time() > (expiry - 60)
            else:
                from datetime import datetime, timezone
                exp_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                needs_refresh = datetime.now(timezone.utc).timestamp() > (exp_dt.timestamp() - 60)
        except Exception:
            needs_refresh = True

    if needs_refresh:
        refresh_token = token.get('refresh_token', '')
        client_id = token.get('client_id', '')
        client_secret = token.get('client_secret', '')

        r = httpx.post(_TOKEN_REFRESH_URL, data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }, timeout=15)
        r.raise_for_status()
        new_data = r.json()
        access_token = new_data['access_token']

        # Atualizar token salvo
        token['token'] = access_token
        token['access_token'] = access_token
        if 'expires_in' in new_data:
            from datetime import datetime, timezone, timedelta
            exp = datetime.now(timezone.utc) + timedelta(seconds=new_data['expires_in'] - 60)
            token['expiry'] = exp.isoformat()
        _save_token(token)

    return access_token


def enviar_email(destinatario: str, assunto: str, corpo_html: str) -> bool:
    """Envia e-mail via Gmail API. Retorna True em caso de sucesso."""
    try:
        import httpx
        access_token = _get_access_token()

        msg = MIMEMultipart('alternative')
        msg['From'] = REMETENTE
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        r = httpx.post(
            _GMAIL_SEND_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            json={'raw': raw},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f'[email_utils] Erro ao enviar para {destinatario}: {e}')
        return False


def enviar_codigo(destinatario: str, nome: str, codigo: str, motivo: str = '2fa') -> bool:
    """Envia e-mail com código de 6 dígitos."""
    if motivo == 'recuperacao':
        assunto = 'Portal Sigma — Código de recuperação de senha'
        intro = 'Você solicitou a <strong>recuperação de senha</strong> do Portal Societário.'
        label = 'Código de recuperação:'
    else:
        assunto = 'Portal Sigma — Código de verificação'
        intro = 'Uma tentativa de login foi detectada no <strong>Portal Societário</strong>.'
        label = 'Seu código de verificação:'

    corpo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 16px rgba(0,0,0,0.08);">
    <div style="background:#A72C31;padding:28px 32px 20px;">
      <div style="color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">Sigma Contabilidade</div>
      <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:4px;">Portal Societário</div>
    </div>
    <div style="padding:32px;">
      <p style="font-size:16px;color:#222;margin:0 0 8px;">Olá, <strong>{nome}</strong>!</p>
      <p style="font-size:14px;color:#555;margin:0 0 28px;">{intro}</p>
      <p style="font-size:13px;color:#888;margin:0 0 10px;">{label}</p>
      <div style="background:#fafafa;border:2px dashed #A72C31;border-radius:10px;padding:24px;
                  text-align:center;margin-bottom:24px;">
        <span style="font-size:40px;font-weight:900;letter-spacing:12px;color:#A72C31;
                     font-family:'Courier New',monospace;">{codigo}</span>
      </div>
      <p style="font-size:13px;color:#888;margin:0 0 6px;">
        &#9888; Este código é válido por <strong>30 minutos</strong>.
      </p>
      <p style="font-size:13px;color:#888;margin:0;">Se não foi você, ignore este e-mail.</p>
    </div>
    <div style="background:#fafafa;border-top:1px solid #eee;padding:16px 32px;text-align:center;">
      <span style="font-size:12px;color:#aaa;">Sigma Contabilidade &mdash; Além da Contabilidade</span>
    </div>
  </div>
</body>
</html>"""
    return enviar_email(destinatario, assunto, corpo)
