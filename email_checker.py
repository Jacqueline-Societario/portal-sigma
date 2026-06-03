"""
email_checker.py — Leitura de e-mails de movimentação de empresas.
Gmail API (societario1@gsigma.com.br), SEM modificar e-mails.
Não marca como lido, não move, não exclui, apenas lê.
"""
import os
import re
import json
import base64
import database

GMAIL_MESSAGES_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
GMAIL_MESSAGE_URL  = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/{}'
ASSUNTO_ENTRADA    = 'FICHA NOVA EMPRESA'
ASSUNTO_SAIDA      = 'SAÍDA DE EMPRESA'


def _get_token():
    from email_utils import _get_access_token
    return _get_access_token()


def _listar_mensagens(token, assunto, max_results=100):
    """Lista IDs de mensagens com o assunto (somente leitura)."""
    import httpx
    r = httpx.get(
        GMAIL_MESSAGES_URL,
        headers={'Authorization': f'Bearer {token}'},
        params={'q': f'subject:"{assunto}" newer_than:3m', 'maxResults': max_results},
        timeout=20,
    )
    r.raise_for_status()
    return [m['id'] for m in r.json().get('messages', [])]


def _get_mensagem(token, msg_id):
    """Busca o conteúdo completo de uma mensagem (somente leitura)."""
    import httpx
    r = httpx.get(
        GMAIL_MESSAGE_URL.format(msg_id),
        headers={'Authorization': f'Bearer {token}'},
        params={'format': 'full'},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _extrair_texto(msg_data):
    """Extrai texto plano do payload do e-mail."""
    def _decode(part):
        mime = part.get('mimeType', '')
        if mime == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                padded = data + '=' * (4 - len(data) % 4)
                return base64.urlsafe_b64decode(padded).decode('utf-8', errors='replace')
        if mime.startswith('multipart/'):
            for sub in part.get('parts', []):
                t = _decode(sub)
                if t:
                    return t
        return ''
    return _decode(msg_data.get('payload', {}))


def _preparar_body(body: str) -> str:
    """
    Prepara o corpo do e-mail para parsing:
    - Remove \r
    - Remove > de linhas citadas (respostas encadeadas)
    - Remove asteriscos de formatação (negrito do Gmail)
    """
    linhas = []
    for linha in body.replace('\r', '').split('\n'):
        linha = re.sub(r'^>+\s*', '', linha)   # remove > de respostas
        linha = linha.replace('*', '')           # remove asteriscos de formatação
        linhas.append(linha)
    return '\n'.join(linhas)


def _limpar(texto: str) -> str:
    """Remove asteriscos e espaços extras de um valor extraído."""
    return texto.strip().strip('*').strip()


def _parse_entrada(body):
    """
    Extrai dados de FICHA NOVA EMPRESA.
    Retorna None se SOCIETÁRIO não estiver nos serviços contratados.

    Formato real do e-mail:
      *Razão Social: *NOME DA EMPRESA
      *Código Domínio: 869*
      *Primeira Competência Apurações: *04/2026
      *Serviços Contratados:*
      - ... / SOCIETÁRIO
      *Contatos:*
      Nome  (62) 9 9999-9999 - email@email.com
      *Grupo: *Nome do Grupo
    """
    body_limpo = _preparar_body(body)

    def campo(pattern):
        m = re.search(pattern, body_limpo, re.IGNORECASE)
        return _limpar(m.group(1)) if m else ''

    # [^\n\r]+ garante que o campo para na quebra de linha (não vaza para o próximo)
    razao_social   = campo(r'Razão Social:\s*([^\n\r]+)')
    codigo_dominio = campo(r'Código Domínio:\s*(\S+)')
    primeira_comp  = campo(r'Primeira Competência Apurações:\s*(\S+)')
    grupo          = campo(r'Grupo:\s*([^\n\r]+)')

    # Verificar se SOCIETÁRIO está nos serviços contratados
    m_serv = re.search(
        r'Serviços Contratados:(.*?)(?:\n\s*\n|\nContatos:|\Z)',
        body_limpo, re.DOTALL | re.IGNORECASE
    )
    servicos = m_serv.group(1).upper() if m_serv else ''
    if 'SOCIETÁRIO' not in servicos and 'SOCIETARIO' not in servicos:
        return None

    # Contatos: entre "Contatos:" e "Grupo:" (ou fim do texto)
    m_cont = re.search(
        r'Contatos:\s*\n(.*?)(?:\nGrupo:|\Z)',
        body_limpo, re.DOTALL | re.IGNORECASE
    )
    contatos_raw = m_cont.group(1).strip() if m_cont else ''
    contatos = [
        l.strip() for l in contatos_raw.splitlines()
        if l.strip() and not re.match(r'^<https?://', l.strip())
    ]

    if not razao_social:
        return None

    return {
        'razao_social':         razao_social,
        'codigo_dominio':       codigo_dominio,
        'primeira_competencia': primeira_comp,
        'grupo':                grupo,
        'contatos':             json.dumps(contatos, ensure_ascii=False),
    }


def _parse_saida(body):
    """
    Extrai dados de SAÍDA DE EMPRESA.

    Formato real do e-mail (após normalização):
      empresa 247 - ILM CIRURGIA PLÁSTICA LTDA finalizar todos os serviços
      competência 03/2026.
      Motivo: Solicitação do Cliente.

    Obs: o nome pode quebrar em duas linhas no original — a normalização une tudo.
    """
    body_limpo = _preparar_body(body)

    # Unir em uma única linha para capturar nomes que quebram entre linhas
    body_linha = ' '.join(body_limpo.split())

    # Código e nome: "empresa 247 - NOME DA EMPRESA finalizar"
    m_emp = re.search(
        r'empresa\s+(\d+)\s*[-–]\s*(.+?)\s+finalizar',
        body_linha, re.IGNORECASE
    )
    # Fim de competência
    m_comp = re.search(r'competência\s+(\d{2}/\d{4})', body_linha, re.IGNORECASE)
    # Motivo (buscar no body por linha para pegar só a primeira linha)
    m_mot = re.search(r'Motivo:\s*(.+)', body_limpo, re.IGNORECASE)

    if not m_emp:
        return None

    codigo = m_emp.group(1).strip()
    nome   = m_emp.group(2).strip().rstrip(',').strip()

    return {
        'codigo_dominio':  codigo,
        'nome_empresa':    f'{codigo} - {nome}',
        'fim_competencia': m_comp.group(1) if m_comp else '',
        'motivo':          _limpar(m_mot.group(1)) if m_mot else '',
    }


def verificar_emails_movimentacao():
    """
    Verifica e-mails e salva novas movimentações.
    NÃO modifica nada no Gmail — apenas leitura.
    Retorna número de novos registros salvos.
    """
    try:
        token = _get_token()
    except Exception as e:
        print(f'[email_checker] Erro ao obter token: {e}')
        database.registrar_verificacao_email(0)
        return 0

    novos = 0

    for assunto, tipo, parser in [
        (ASSUNTO_ENTRADA, 'entrada', _parse_entrada),
        (ASSUNTO_SAIDA,   'saida',   _parse_saida),
    ]:
        try:
            ids = _listar_mensagens(token, assunto)
        except Exception as e:
            print(f'[email_checker] Erro ao listar "{assunto}": {e}')
            continue

        for msg_id in ids:
            if database.email_ja_processado(msg_id):
                continue

            try:
                msg  = _get_mensagem(token, msg_id)
                body = _extrair_texto(msg)
                dados = parser(body)

                if dados:
                    # Data real do e-mail (internalDate em ms → ISO timestamp)
                    internal_ms = msg.get('internalDate')
                    if internal_ms:
                        from datetime import datetime, timezone
                        dados['email_data'] = datetime.fromtimestamp(
                            int(internal_ms) / 1000, tz=timezone.utc
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    database.salvar_movimentacao(tipo, **dados)
                    novos += 1

                    # Notificação de movimentação
                    nome_mov = dados.get('razao_social') or dados.get('nome_empresa', '')
                    if tipo == 'entrada':
                        titulo_notif = f'Nova entrada na carteira — {nome_mov}'
                    else:
                        titulo_notif = f'Saída da carteira — {nome_mov}'
                    database.criar_notificacoes_para_evento(
                        modulo='movimentacao',
                        tipo_evento=f'movimentacao_{tipo}',
                        titulo=titulo_notif,
                        link_destino='/movimentacao/',
                    )

                # Sempre marcar como processado (mesmo sem dados relevantes)
                database.marcar_email_processado(msg_id)

            except Exception as e:
                print(f'[email_checker] Erro ao processar mensagem {msg_id}: {e}')

    database.registrar_verificacao_email(novos)
    print(f'[email_checker] Verificação concluída. {novos} novo(s) registro(s).')
    return novos
