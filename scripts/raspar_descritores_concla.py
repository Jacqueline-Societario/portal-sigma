"""
scripts/raspar_descritores_concla.py
=====================================
Captura a Lista de Descritores de cada subclasse CNAE nas paginas oficiais
do CONCLA/IBGE (busca-online-cnae.html?view=subclasse) e mantem um cache
incremental em static/data/descritores_concla_raw.json.

Os descritores sao a base da busca por termos populares (ex.: "pneus"
encontra 4530-7/05, cuja denominacao oficial usa "pneumaticos").
Nao existe download oficial dos descritores — esta raspagem e a unica fonte.

Uso:
    python scripts/raspar_descritores_concla.py            # incremental (so faltantes)
    python scripts/raspar_descritores_concla.py --teste    # apenas 5 subclasses
    python scripts/raspar_descritores_concla.py --force    # recaptura tudo
    python scripts/raspar_descritores_concla.py --intervalo 1.0

Seguranca:
- Valida contagem extraida == contagem anunciada pela pagina; divergencia nao grava.
- Aborta apos 10 falhas consecutivas (site fora/HTML mudou) preservando o cache.
- Salvamento atomico a cada 25 paginas — interrompeu, retoma do ponto.
"""
import os
import re
import sys
import json
import time
import shutil
from datetime import datetime, timezone

import httpx
from lxml import html as lxml_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
DATA_DIR   = os.path.join(BASE_DIR, 'static', 'data')
BASE_JSON  = os.path.join(DATA_DIR, 'cnae_subclasses.json')
CACHE_JSON = os.path.join(DATA_DIR, 'descritores_concla_raw.json')

URL_BUSCA       = 'https://concla.ibge.gov.br/busca-online-cnae.html'
VERSAO_INTERNA  = '10.1.0'   # CNAE-Subclasses 2.3 no seletor do CONCLA
FALHAS_CONSECUTIVAS_MAX = 10

USER_AGENT = ('Mozilla/5.0 (compatible; PortalSocietarioSigma/1.0; '
              'atualizacao de base CNAE; contato: societario1@gsigma.com.br)')


def carregar_codigos() -> list:
    """Codigos de subclasse validos (7 digitos) a partir da base local atual."""
    with open(BASE_JSON, encoding='utf-8') as f:
        dados = json.load(f)
    codigos = []
    for s in dados.get('subclasses', []):
        cod = s.get('codigo_sem_mascara', '')
        if re.fullmatch(r'\d{7}', cod):
            codigos.append(cod)
    return sorted(set(codigos))


def carregar_cache() -> dict:
    if os.path.isfile(CACHE_JSON):
        with open(CACHE_JSON, encoding='utf-8') as f:
            return json.load(f)
    return {
        'fonte': 'CONCLA/IBGE — busca-online-cnae.html?view=subclasse',
        'versao_interna': VERSAO_INTERNA,
        'versao_cnae': '2.3',
        'subclasses': {},
    }


def salvar_cache(cache: dict):
    cache['atualizado_em'] = datetime.now(timezone.utc).isoformat()
    cache['total_capturado'] = len(cache['subclasses'])
    tmp = CACHE_JSON + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
    shutil.move(tmp, CACHE_JSON)


def extrair_descritores(html_text: str):
    """Retorna (contagem_anunciada, [descritores]) da pagina view=subclasse."""
    m = re.search(r'Registros encontrados:\s*(?:<[^>]*>)?\s*(\d+)', html_text)
    anunciado = int(m.group(1)) if m else -1

    descritores = []
    doc = lxml_html.fromstring(html_text)
    h3 = doc.xpath('//h3[contains(text(),"Lista de Descritores")]')
    if h3:
        tabela = h3[0].xpath('following::table[1]')
        if tabela:
            for tr in tabela[0].xpath('.//tr'):
                tds = tr.xpath('./td')
                if len(tds) >= 2:
                    desc = tds[1].text_content().strip()
                    if desc:
                        descritores.append(desc)
    return anunciado, descritores


def main():
    modo_teste = '--teste' in sys.argv
    modo_force = '--force' in sys.argv
    intervalo = 0.6
    if '--intervalo' in sys.argv:
        intervalo = float(sys.argv[sys.argv.index('--intervalo') + 1])

    codigos = carregar_codigos()
    cache = carregar_cache()
    ja_tem = set() if modo_force else set(cache['subclasses'].keys())
    pendentes = [c for c in codigos if c not in ja_tem]

    if modo_teste:
        pendentes = pendentes[:5]

    print(f"[INICIO] {len(codigos)} subclasses na base | {len(ja_tem)} em cache | "
          f"{len(pendentes)} a capturar | intervalo {intervalo}s")
    if not pendentes:
        print("[OK] Nada a capturar — cache completo.")
        return

    cli = httpx.Client(timeout=30, follow_redirects=True,
                       headers={'User-Agent': USER_AGENT})

    falhas_consecutivas = 0
    capturados = 0
    inicio = time.time()

    for i, cod in enumerate(pendentes, 1):
        ok = False
        erro = ''
        for tentativa in (1, 2):
            try:
                r = cli.get(URL_BUSCA, params={
                    'view': 'subclasse', 'tipo': 'cnae',
                    'versao': VERSAO_INTERNA, 'subclasse': cod,
                })
                if r.status_code != 200:
                    erro = f'HTTP {r.status_code}'
                    time.sleep(2)
                    continue
                anunciado, descs = extrair_descritores(r.text)
                if anunciado >= 1 and len(descs) == anunciado:
                    cache['subclasses'][cod] = {
                        'descritores': descs,
                        'capturado_em': datetime.now(timezone.utc).isoformat(),
                    }
                    ok = True
                    break
                erro = f'parse invalido (anunciado={anunciado}, extraidos={len(descs)})'
                time.sleep(2)
            except Exception as e:
                erro = f'{type(e).__name__}: {e}'
                time.sleep(2)

        if ok:
            capturados += 1
            falhas_consecutivas = 0
        else:
            falhas_consecutivas += 1
            print(f"[FALHA] {cod}: {erro} ({falhas_consecutivas} consecutivas)")
            if falhas_consecutivas >= FALHAS_CONSECUTIVAS_MAX:
                salvar_cache(cache)
                print(f"[ABORTADO] {FALHAS_CONSECUTIVAS_MAX} falhas consecutivas — "
                      "site indisponivel ou HTML mudou. Cache preservado; rode novamente para retomar.")
                sys.exit(2)

        if i % 25 == 0:
            salvar_cache(cache)
        if i % 50 == 0 or i == len(pendentes):
            decorrido = time.time() - inicio
            ritmo = decorrido / i
            resta = ritmo * (len(pendentes) - i)
            print(f"[PROGRESSO] {i}/{len(pendentes)} ({capturados} ok) — "
                  f"~{resta/60:.0f} min restantes")
        time.sleep(intervalo)

    salvar_cache(cache)
    total_desc = sum(len(v['descritores']) for v in cache['subclasses'].values())
    print(f"[FIM] cache com {len(cache['subclasses'])} subclasses, "
          f"{total_desc} descritores no total.")
    print(f"      Arquivo: {CACHE_JSON}")


if __name__ == '__main__':
    main()
