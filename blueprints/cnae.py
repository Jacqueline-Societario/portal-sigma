"""
blueprints/cnae.py — Módulo Consulta CNAE / Regime Tributário
Busca CNAEs a partir de base local gerada pelo CONCLA/IBGE
e consulta tributação na Objetiva Edições.

Base local: static/data/cnae_subclasses.json
Atualizar:  python scripts/atualizar_base_cnae_concla.py
"""
import os
import json
import threading
import unicodedata
import re
from typing import Optional
import httpx
from lxml import html as lxml_html
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

from blueprints.auth import login_obrigatorio
import database

cnae_bp = Blueprint('cnae', __name__, url_prefix='/cnae')

# ── Caminho da base local CNAE ────────────────────────────────────────────────
_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON_PATH = os.path.join(_BASE_DIR, 'static', 'data', 'cnae_subclasses.json')

# ── Cache de subclasses (carregado uma vez por processo) ──────────────────────
_ibge_cache: list = []
_ibge_meta:  dict = {}
_ibge_lock = threading.Lock()


def _carregar_ibge() -> list:
    """
    Carrega a base CNAE do arquivo JSON local gerado pelo CONCLA/IBGE.
    Retorna lista vazia e registra erro se o arquivo estiver ausente ou inválido.
    """
    global _ibge_cache, _ibge_meta
    with _ibge_lock:
        if _ibge_cache:
            return _ibge_cache
        if not os.path.isfile(_JSON_PATH):
            import logging
            logging.getLogger('cnae').error(
                "Base CNAE ausente: %s — execute scripts/atualizar_base_cnae_concla.py",
                _JSON_PATH,
            )
            return []
        try:
            with open(_JSON_PATH, encoding='utf-8') as f:
                dados = json.load(f)
            subclasses = dados.get('subclasses', [])
            if len(subclasses) < 100:
                raise ValueError(f"Base com apenas {len(subclasses)} registros — arquivo inválido.")
            _ibge_meta  = {k: v for k, v in dados.items() if k != 'subclasses'}
            _ibge_cache = subclasses
        except Exception as e:
            import logging
            logging.getLogger('cnae').error("Erro ao carregar base CNAE: %s", e)
            _ibge_cache = []
        return _ibge_cache


def _normalizar(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()


def _buscar_ibge(query: str) -> list:
    """
    Busca subclasses por texto (com/sem acento, parcial) ou por código
    (com ou sem máscara: '6920601' e '6920-6/01' são equivalentes).
    Retorna até 20 resultados ordenados por relevância.
    """
    subclasses = _carregar_ibge()
    if not subclasses:
        return []

    termos = _normalizar(query).split()
    if not termos:
        return []

    # Detectar busca por código (query contém apenas dígitos após remover separadores)
    q_cod = re.sub(r'\D', '', query)
    busca_por_codigo = bool(q_cod) and all(c.isdigit() for c in q_cod)

    resultados = []
    for s in subclasses:
        score = 0

        if busca_por_codigo:
            # Correspondência exata ou parcial pelo código
            if s['codigo_sem_mascara'] == q_cod:
                score = 20          # exato
            elif s['codigo_sem_mascara'].startswith(q_cod) or q_cod in s['codigo_sem_mascara']:
                score = 10          # parcial
        else:
            # Busca textual: peso 2 se o termo estiver na descrição principal,
            # peso 1 se estiver apenas no contexto hierárquico
            desc_norm = _normalizar(s.get('descricao', ''))
            ctx_norm  = s.get('termos_normalizados', desc_norm)
            for t in termos:
                if t in desc_norm:
                    score += 2
                elif t in ctx_norm:
                    score += 1

        if score > 0:
            resultados.append((score, s))

    resultados.sort(key=lambda x: (-x[0], x[1].get('descricao', '')))

    return [
        {
            'id':           s['codigo_sem_mascara'],
            'descricao':    s['descricao'],
            'secao':        s.get('secao', ''),
            'secao_desc':   s.get('secao_desc', ''),
            'divisao':      s.get('divisao', ''),
            'divisao_desc': s.get('divisao_desc', ''),
            'classe_desc':  s.get('classe_desc', ''),
        }
        for _, s in resultados[:20]
    ]


# ── Sessão Objetiva com httpx + 2captcha (sem Playwright) ────────────────────
_obj_session: Optional[httpx.Client] = None
_obj_logado: bool = False
_obj_lock = threading.Lock()

_OBJETIVA_LOGIN_URL = 'https://www.objetivaedicoes.com.br/login.php'
_OBJETIVA_BUSCA_URL = 'https://www.objetivaedicoes.com.br/busca_cnae_2.php'
_RECAPTCHA_SITEKEY  = '6LcThxIUAAAAAFPqbMX9yfgSDHgZLbCSMf2atcap'
_TWOCAPTCHA_KEY     = os.getenv('TWOCAPTCHA_KEY', '5f5c651486775b5dfb165ab05c18c7ec')


def _resolver_recaptcha_v2(page_url: str, sitekey: str) -> str:
    import time
    r = httpx.post(
        'http://2captcha.com/in.php',
        data={'key': _TWOCAPTCHA_KEY, 'method': 'userrecaptcha',
              'googlekey': sitekey, 'pageurl': page_url, 'json': '1'},
        timeout=30,
    )
    resp = r.json()
    if resp.get('status') != 1:
        raise RuntimeError(f'2captcha erro ao enviar: {resp}')
    task_id = resp['request']
    for _ in range(24):
        time.sleep(5)
        r2 = httpx.get(
            'http://2captcha.com/res.php',
            params={'key': _TWOCAPTCHA_KEY, 'action': 'get', 'id': task_id, 'json': '1'},
            timeout=15,
        )
        resp2 = r2.json()
        if resp2.get('status') == 1:
            return resp2['request']
        if resp2.get('request') not in ('CAPCHA_NOT_READY', 'CAPTCHA_NOT_READY'):
            raise RuntimeError(f'2captcha erro: {resp2}')
    raise RuntimeError('2captcha timeout: captcha não resolvido em 120s')


def _obter_sessao_objetiva() -> httpx.Client:
    global _obj_session, _obj_logado
    with _obj_lock:
        if _obj_session and _obj_logado:
            return _obj_session
        user  = os.getenv('OBJETIVA_USER', '')
        senha = os.getenv('OBJETIVA_SENHA', '')
        s = httpx.Client(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': _OBJETIVA_LOGIN_URL,
                'Origin': 'https://www.objetivaedicoes.com.br',
            },
            follow_redirects=True,
        )
        s.get(_OBJETIVA_LOGIN_URL, timeout=15)
        token = _resolver_recaptcha_v2(_OBJETIVA_LOGIN_URL, _RECAPTCHA_SITEKEY)
        s.post(_OBJETIVA_LOGIN_URL, data={
            'post_login': user, 'post_senha': senha,
            'post': '1', 'g-recaptcha-response': token,
        }, timeout=15)
        _obj_session = s
        _obj_logado = True
        return _obj_session


def _resetar_sessao_objetiva():
    global _obj_session, _obj_logado
    with _obj_lock:
        if _obj_session:
            try:
                _obj_session.close()
            except Exception:
                pass
        _obj_session = None
        _obj_logado  = False


def _consultar_objetiva(codigo: str) -> dict:
    """Consulta um CNAE na Objetiva (fluxo 2 passos: busca → detalhamento)."""
    import re as _re
    codigo_limpo = codigo.replace('-', '').replace('/', '').replace('.', '').strip()

    def _fazer_busca(s: httpx.Client):
        return s.get(_OBJETIVA_BUSCA_URL,
                     params={'get_cnae': codigo_limpo, 'get_post': '1'}, timeout=15)

    try:
        s = _obter_sessao_objetiva()
        r = _fazer_busca(s)
    except Exception as e:
        return {'codigo': codigo, 'erro': f'Falha na conexão com a Objetiva: {e}'}

    if 'post_login' in r.text or 'login.php' in str(r.url):
        _resetar_sessao_objetiva()
        try:
            s = _obter_sessao_objetiva()
            r = _fazer_busca(s)
        except Exception as e:
            return {'codigo': codigo, 'erro': f'Falha ao re-autenticar na Objetiva: {e}'}

    doc = lxml_html.fromstring(r.text)
    links = doc.xpath('//a[contains(@href,"ver_cnae_2.php")]/@href')

    if not links:
        return {'codigo': codigo, 'erro': 'CNAE não encontrado na Objetiva'}

    try:
        detail_url = 'https://www.objetivaedicoes.com.br/' + links[0].lstrip('/')
        r2 = s.get(detail_url, timeout=15)
    except Exception as e:
        return {'codigo': codigo, 'erro': f'Falha ao obter detalhamento: {e}'}

    doc2 = lxml_html.fromstring(r2.text)
    body = ' | '.join(t.strip() for t in doc2.itertext() if t.strip())

    resultado: dict = {'codigo': codigo, 'erro': None}

    # ── Descrição ────────────────────────────────────────────────────────────
    try:
        idx_b = body.index('Pesquise ativida')
        # Tentar extrair descrição do badge do link clicado
        span_text = doc.xpath('//a[contains(@href,"ver_cnae_2.php")]//div/text()')
        resultado['descricao']      = span_text[0].strip() if span_text else codigo
        resultado['descricao_full'] = span_text[1].strip() if len(span_text) > 1 else ''
    except Exception:
        resultado['descricao']      = codigo
        resultado['descricao_full'] = ''

    resultado['secao'] = ''

    # ── MEI ───────────────────────────────────────────────────────────────────
    if 'Atividade não permitida ao MEI' in body:
        resultado['mei'] = 'Não permitido'
    elif 'permitida ao MEI' in body or 'Atividade permitida ao MEI' in body:
        try:
            idx_m = body.index('Ocupação MEI |')
            ocup = body[idx_m:idx_m+100].split('|')[1].strip()
            resultado['mei'] = f'Permitido ({ocup})'
        except Exception:
            resultado['mei'] = 'Permitido'
    else:
        resultado['mei'] = '—'

    # ── Simples Nacional ──────────────────────────────────────────────────────
    if 'não é Impeditiva a adesão ao Simples Nacional' in body:
        resultado['simples'] = 'Não impeditivo'
        resultado['simples_status'] = 'ok'
        resultado['simples_obs'] = ''
    elif 'Poderá optar pelo Simples Nacional desde que' in body:
        resultado['simples'] = 'Condicional'
        resultado['simples_status'] = 'warn'
        try:
            idx_c = body.index('Poderá optar pelo Simples Nacional desde que')
            resultado['simples_obs'] = body[idx_c:idx_c+400].split('|')[0].strip()
        except Exception:
            resultado['simples_obs'] = 'CNAE abrange atividade impeditiva e permitida.'
    elif 'impeditiva' in body.lower() and 'não é Impeditiva' not in body:
        resultado['simples'] = 'Impeditivo'
        resultado['simples_status'] = 'err'
        resultado['simples_obs'] = ''
    else:
        resultado['simples'] = '—'
        resultado['simples_status'] = ''
        resultado['simples_obs'] = ''

    # ── Anexos do Simples ─────────────────────────────────────────────────────
    anexos = []
    for a in ['III', 'IV', 'V', 'I', 'II']:
        if f'ANEXO {a}' in body and a not in anexos:
            anexos.append(a)
    resultado['anexo'] = ' / '.join(anexos) if anexos else '—'

    resultado['fator_r'] = any(p in body.lower() for p in ("fator ''r''", 'fator "r"', 'fator r'))

    for fund, key in [('§ 5º-F', '§ 5º-F do Art. 18 da LC 123/2006'),
                       ('§5º-I',  '§5º-I do Art. 18 da LC 123/2006'),
                       ('§5º-C',  '§5º-C do Art. 18 da LC 123/2006'),
                       ('§ 5º-B', '§ 5º-B do Art. 18 da LC 123/2006')]:
        if fund in body:
            resultado['fundamento'] = key
            break
    else:
        resultado['fundamento'] = '—'

    # ── Lucro Presumido ───────────────────────────────────────────────────────
    if 'Lucro Presumido' in body:
        resultado['lucro_presumido'] = 'Permitido'
        try:
            idx_irpj = body.index('IRPJ | Presunção |')
            resultado['irpj_presuncao'] = body[idx_irpj:idx_irpj+80].split('|')[2].strip()
        except Exception:
            resultado['irpj_presuncao'] = '—'
        try:
            idx_csll = body.index('CSLL | Presunção |')
            resultado['csll_presuncao'] = body[idx_csll:idx_csll+80].split('|')[2].strip()
        except Exception:
            resultado['csll_presuncao'] = '—'
    else:
        resultado['lucro_presumido'] = '—'
        resultado['irpj_presuncao']  = '—'
        resultado['csll_presuncao']  = '—'

    return resultado

# ── Rotas ──────────────────────────────────────────────────────────────────────

@cnae_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    user_id = session.get('user_id')
    if user_id and not database.get_user_permission(user_id, 'cnae'):
        return redirect(url_for('acesso_negado'))
    return render_template('cnae/index.html')


@cnae_bp.route('/api/buscar-ibge', methods=['POST'])
def buscar_ibge():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    if user_id and not database.get_user_permission(user_id, 'cnae'):
        return jsonify({'erro': 'Acesso negado'}), 403

    dados = request.get_json() or {}
    query = dados.get('query', '').strip()
    if len(query) < 3:
        return jsonify({'erro': 'Digite pelo menos 3 caracteres'}), 400

    resultados = _buscar_ibge(query)
    return jsonify({'resultados': resultados, 'total': len(resultados)})


@cnae_bp.route('/api/consultar-objetiva', methods=['POST'])
def consultar_objetiva():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    if user_id and not database.get_user_permission(user_id, 'cnae'):
        return jsonify({'erro': 'Acesso negado'}), 403

    dados  = request.get_json() or {}
    codigos = dados.get('codigos', [])
    if not codigos:
        return jsonify({'erro': 'Nenhum CNAE informado'}), 400
    if len(codigos) > 15:
        return jsonify({'erro': 'Máximo de 15 CNAEs por consulta'}), 400

    resultados = []
    for codigo in codigos:
        resultados.append(_consultar_objetiva(str(codigo).strip()))

    return jsonify({'resultados': resultados})
