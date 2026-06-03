"""
backup_sheets.py — Backup diário do cadastro de empresas para Google Sheets
Portal Societário Sigma Contabilidade

Executa diariamente às 02:00, criando/atualizando planilha de backup:
  - Aba "Consolidada": sempre contém os dados atuais (sobrescreve)
  - Aba "YYYY-MM-DD": snapshot do dia (mantém os últimos 30 dias)
  - backup.log: registro de cada execução
"""

import os
import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH',
    os.path.join(BASE_DIR, 'credentials', 'token.json'))

BACKUP_CONFIG_PATH = os.path.join(BASE_DIR, 'backup_config.json')
BACKUP_LOG_PATH = os.path.join(BASE_DIR, 'backup.log')

BACKUP_SPREADSHEET_TITLE = 'Portal Sigma — Backup Diário de Empresas'

SHEETS_API = 'https://sheets.googleapis.com/v4/spreadsheets'
DRIVE_API  = 'https://www.googleapis.com/drive/v3/files'

# Aba principal de sincronização (importação e exportação)
ABA_CONSOLIDADA = 'Consolidada'

# Colunas exportadas (exclui campos internos de normalização)
COLUNAS = [
    ('id',                  'ID'),
    ('nome_empresa',        'Nome da Empresa'),
    ('cnpj_cpf',            'CNPJ / CPF'),
    ('aba',                 'Status'),
    ('atuacao',             'Atuação'),
    ('escritorio',          'Escritório'),
    ('municipio',           'Município'),
    ('codigo_dominio',      'Código Domínio'),
    ('responsavel',         'Responsável'),
    ('procuracao',          'Procuração'),
    ('visa',                'VISA'),
    ('cnes',                'CNES'),
    ('venc_bombeiro',       'Bombeiro — Vencimento'),
    ('prot_bombeiro',       'Bombeiro — Protocolo'),
    ('licenca_ambiental',   'Licença Ambiental'),
    ('alvara_funcionamento','Alvará de Funcionamento'),
    ('publicidade',         'Publicidade'),
    ('tpi',                 'TPI'),
    ('motivo_inativa',      'Motivo (Inativa)'),
    ('observacoes',         'Observações'),
    ('atualizado_em',       'Atualizado em'),
    ('editado_em',          'Editado em'),
    ('editado_por',         'Editado por'),
    ('certificado_digital', 'Certificado Digital'),
]

_lock = threading.Lock()


# ─── Logging ──────────────────────────────────────────────────────────────────

def _log(msg: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f'[{ts}] {msg}'
    print(f'[backup_sheets] {msg}')
    try:
        with open(BACKUP_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(linha + '\n')
    except Exception:
        pass


# ─── Token OAuth ──────────────────────────────────────────────────────────────

def _get_token() -> str:
    """Retorna access_token válido, renovando via refresh_token se necessário."""
    with open(TOKEN_PATH) as f:
        data = json.load(f)

    expiry_str = data.get('expiry') or ''
    access_token = data.get('token') or data.get('access_token', '')
    needs_refresh = True

    if access_token and expiry_str:
        try:
            exp_dt = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            needs_refresh = datetime.now(timezone.utc).timestamp() > (exp_dt.timestamp() - 60)
        except Exception:
            needs_refresh = True

    if not needs_refresh:
        return access_token

    payload = urllib.parse.urlencode({
        'grant_type':    'refresh_token',
        'refresh_token': data.get('refresh_token', ''),
        'client_id':     data.get('client_id', ''),
        'client_secret': data.get('client_secret', ''),
    }).encode()

    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token', data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    resp = urllib.request.urlopen(req, timeout=15)
    novo = json.loads(resp.read())

    access_token = novo['access_token']
    data['token'] = access_token
    data['access_token'] = access_token
    exp = datetime.now(timezone.utc) + timedelta(seconds=novo.get('expires_in', 3600) - 60)
    data['expiry'] = exp.isoformat()

    with open(TOKEN_PATH, 'w') as f:
        json.dump(data, f)

    return access_token


def _api(method: str, url: str, body=None, token: str = '') -> dict:
    """Faz chamada à API do Google e retorna o JSON de resposta."""
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type':  'application/json',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code} em {url}: {e.read().decode()[:300]}')


# ─── Planilha de backup ────────────────────────────────────────────────────────

def _carregar_config() -> dict:
    if os.path.exists(BACKUP_CONFIG_PATH):
        with open(BACKUP_CONFIG_PATH) as f:
            return json.load(f)
    return {}


def _salvar_config(cfg: dict):
    with open(BACKUP_CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)


def _planilha_existe(spreadsheet_id: str, token: str) -> bool:
    try:
        _api('GET', f'{SHEETS_API}/{spreadsheet_id}', token=token)
        return True
    except Exception:
        return False


def _obter_ou_criar_planilha(token: str) -> str:
    """Retorna o ID da planilha de backup, criando-a se necessário."""
    cfg = _carregar_config()
    sid = cfg.get('backup_spreadsheet_id', '')

    if sid and _planilha_existe(sid, token):
        return sid

    # Criar nova planilha
    _log('Criando nova planilha de backup no Google Sheets...')
    resultado = _api('POST', SHEETS_API, body={
        'properties': {'title': BACKUP_SPREADSHEET_TITLE, 'locale': 'pt_BR'},
        'sheets': [
            {'properties': {'title': ABA_CONSOLIDADA, 'index': 0}},
        ]
    }, token=token)

    sid = resultado['spreadsheetId']
    cfg['backup_spreadsheet_id'] = sid
    cfg['criado_em'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _salvar_config(cfg)
    _log(f'Planilha criada: {sid}')
    return sid


def _listar_abas(spreadsheet_id: str, token: str) -> list:
    """Retorna lista de {'sheetId': int, 'title': str}."""
    r = _api('GET', f'{SHEETS_API}/{spreadsheet_id}', token=token)
    return [
        {'sheetId': s['properties']['sheetId'], 'title': s['properties']['title']}
        for s in r.get('sheets', [])
    ]


def _garantir_aba(spreadsheet_id: str, titulo: str, token: str) -> int:
    """Garante que a aba existe. Retorna sheetId."""
    abas = _listar_abas(spreadsheet_id, token)
    for aba in abas:
        if aba['title'] == titulo:
            return aba['sheetId']

    # Criar aba
    r = _api('POST', f'{SHEETS_API}/{spreadsheet_id}:batchUpdate', body={
        'requests': [{'addSheet': {'properties': {'title': titulo}}}]
    }, token=token)
    return r['replies'][0]['addSheet']['properties']['sheetId']


def _limpar_abas_antigas(spreadsheet_id: str, token: str, manter: int = 30):
    """Remove abas de datas antigas, mantendo as últimas N."""
    abas = _listar_abas(spreadsheet_id, token)
    # Filtrar só abas de datas (formato YYYY-MM-DD)
    datas = sorted(
        [a for a in abas if len(a['title']) == 10 and a['title'].count('-') == 2],
        key=lambda x: x['title']
    )
    remover = datas[:-manter] if len(datas) > manter else []
    if not remover:
        return
    requests = [{'deleteSheet': {'sheetId': a['sheetId']}} for a in remover]
    _api('POST', f'{SHEETS_API}/{spreadsheet_id}:batchUpdate',
         body={'requests': requests}, token=token)
    _log(f'Removidas {len(remover)} abas antigas: {[a["title"] for a in remover]}')


def _formatar_header(sheet_id: int) -> list:
    """Requests para formatar linha de cabeçalho (bordô + texto branco + negrito)."""
    return [{
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': 0, 'endRowIndex': 1,
                'startColumnIndex': 0, 'endColumnIndex': len(COLUNAS)
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {'red': 0.655, 'green': 0.173, 'blue': 0.192},
                    'textFormat': {
                        'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                        'bold': True,
                        'fontSize': 10
                    },
                    'horizontalAlignment': 'CENTER',
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    }, {
        'updateSheetProperties': {
            'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
            'fields': 'gridProperties.frozenRowCount'
        }
    }]


def _escrever_dados(spreadsheet_id: str, titulo_aba: str,
                    sheet_id: int, linhas: list, token: str):
    """Limpa e escreve os dados na aba, depois formata o cabeçalho."""
    # Limpar o range completo ANTES de escrever para garantir que
    # células antigas (inclusive em colunas do meio) não permaneçam.
    clear_rng = urllib.parse.quote(f"'{titulo_aba}'!A1:Z5000")
    _api('POST', f'{SHEETS_API}/{spreadsheet_id}/values/{clear_rng}:clear',
         body={}, token=token)

    # Escrever dados (cabeçalho + linhas)
    rng = f"'{titulo_aba}'!A1"
    _api('POST', f'{SHEETS_API}/{spreadsheet_id}/values:batchUpdate', body={
        'valueInputOption': 'USER_ENTERED',
        'data': [{'range': rng, 'values': linhas}]
    }, token=token)

    # Formatar cabeçalho
    _api('POST', f'{SHEETS_API}/{spreadsheet_id}:batchUpdate', body={
        'requests': _formatar_header(sheet_id)
    }, token=token)


# ─── Leitura do banco ──────────────────────────────────────────────────────────

def _ler_empresas() -> list:
    """Lê todas as empresas do banco local e retorna lista de listas [header] + [linhas]."""
    import database
    conn = database.get_db()
    campos = [c[0] for c in COLUNAS]
    sql = f'SELECT {", ".join(campos)} FROM empresas_planilha ORDER BY aba, nome_empresa'
    rows = conn.execute(sql).fetchall()
    conn.close()

    header = [c[1] for c in COLUNAS]
    linhas = [[str(row[c] or '') for c in campos] for row in rows]
    return [header] + linhas


# ─── Execução principal do backup ─────────────────────────────────────────────

def executar_backup():
    """Executa o backup completo. Pode ser chamado manualmente via rota admin."""
    with _lock:
        inicio = datetime.now()
        data_hoje = inicio.strftime('%Y-%m-%d')
        _log(f'=== INÍCIO DO BACKUP {data_hoje} ===')

        try:
            token = _get_token()

            # Obter/criar planilha
            sid = _obter_ou_criar_planilha(token)

            # Ler dados do banco
            linhas = _ler_empresas()
            total_empresas = len(linhas) - 1  # desconta cabeçalho
            _log(f'{total_empresas} empresas lidas do banco')

            # Garantir aba "Consolidada" (aba principal de sincronização)
            sheet_id_recente = _garantir_aba(sid, ABA_CONSOLIDADA, token)
            _escrever_dados(sid, ABA_CONSOLIDADA, sheet_id_recente, linhas, token)
            _log(f'Aba "{ABA_CONSOLIDADA}" atualizada')

            # Garantir aba datada
            sheet_id_data = _garantir_aba(sid, data_hoje, token)
            _escrever_dados(sid, data_hoje, sheet_id_data, linhas, token)
            _log(f'Aba "{data_hoje}" criada/atualizada')

            # Limpar abas antigas (manter últimos 30 dias)
            _limpar_abas_antigas(sid, token, manter=30)

            duracao = (datetime.now() - inicio).seconds
            _log(f'=== BACKUP CONCLUÍDO em {duracao}s — {total_empresas} empresas ===')
            _log(f'Planilha: https://docs.google.com/spreadsheets/d/{sid}')

            # Salvar resultado no config
            cfg = _carregar_config()
            cfg['ultimo_backup'] = inicio.strftime('%Y-%m-%d %H:%M:%S')
            cfg['ultimo_backup_status'] = 'sucesso'
            cfg['ultimo_backup_total'] = total_empresas
            _salvar_config(cfg)

            return True, sid, total_empresas

        except Exception as e:
            _log(f'=== ERRO NO BACKUP: {e} ===')
            cfg = _carregar_config()
            cfg['ultimo_backup'] = inicio.strftime('%Y-%m-%d %H:%M:%S')
            cfg['ultimo_backup_status'] = f'erro: {e}'
            _salvar_config(cfg)
            return False, '', 0


# ─── Thread de agendamento diário ─────────────────────────────────────────────

def _segundos_ate_proximas_2h() -> float:
    """Calcula segundos até o próximo 02:00 AM local."""
    agora = datetime.now()
    proxima = agora.replace(hour=2, minute=0, second=0, microsecond=0)
    if proxima <= agora:
        proxima += timedelta(days=1)
    return (proxima - agora).total_seconds()


def iniciar_backup_diario():
    """Inicia thread de backup diário às 02:00 AM. Chame no startup do portal."""
    def _loop():
        espera = _segundos_ate_proximas_2h()
        _log(f'Backup agendado para 02:00 AM (em {espera/3600:.1f}h)')
        time.sleep(espera)

        while True:
            executar_backup()
            # Dormir até o próximo 02:00 AM
            espera = _segundos_ate_proximas_2h()
            _log(f'Próximo backup em {espera/3600:.1f}h')
            time.sleep(espera)

    t = threading.Thread(target=_loop, daemon=True, name='backup-diario')
    t.start()
    _log('Thread de backup diário iniciada (02:00 AM)')
