"""
scripts/testar_busca_cnae.py
=============================
QA da busca CNAE local (blueprints/cnae_busca.py + base formato 2).
Compara com o comportamento da busca oficial do IBGE/CONCLA.

Uso:
    python scripts/testar_busca_cnae.py               # roda a suite de casos
    python scripts/testar_busca_cnae.py "sua busca"   # busca livre (debug)

Sai com codigo 1 se algum caso obrigatorio falhar.
"""
import os
import sys
import json
import time
import importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
BASE_JSON  = os.path.join(BASE_DIR, 'static', 'data', 'cnae_subclasses.json')
SINONIMOS  = os.path.join(BASE_DIR, 'static', 'data', 'cnae_sinonimos.json')
MOTOR_PY   = os.path.join(BASE_DIR, 'blueprints', 'cnae_busca.py')

spec = importlib.util.spec_from_file_location('cnae_busca', MOTOR_PY)
cnae_busca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cnae_busca)

# (query, codigos_obrigatorios, codigos_proibidos_no_top10)
CASOS = [
    # Caso que motivou o projeto — deve replicar as 6 subclasses do IBGE
    ('comércio de pneus',
     ['4530702', '4530705', '4541202', '4661300', '4662100', '4669999'],
     ['4755503', '4511101']),          # cama/mesa/banho e automoveis eram o lixo antigo
    ('pneus',
     ['4530702', '4530705'], []),      # antes retornava ZERO
    ('comercio pneus',
     ['4530705'], ['4755503']),
    ('farmácia',
     ['4771701'], []),                 # denominacao oficial nao usa "farmacia"; descritor usa
    ('açougue',
     ['4722901'], []),
    ('loja de pneus',
     ['4530705'], []),                 # sinonimo IBGE: loja -> comercio
    ('cabeleireiro',
     ['9602501'], []),
    ('contabilidade',
     ['6920601'], []),
    ('6920-6/01',
     ['6920601'], []),                 # busca por codigo com mascara
    ('69206',
     ['6920601', '6920602'], []),      # busca por codigo parcial
]


def carregar_indice():
    with open(BASE_JSON, encoding='utf-8') as f:
        base = json.load(f)
    sin = cnae_busca.carregar_sinonimos(SINONIMOS)
    t0 = time.time()
    indice = cnae_busca.construir_indice(base['subclasses'], sin)
    print(f"[INDICE] {len(indice['itens'])} subclasses | formato {base.get('formato', 1)} | "
          f"construido em {time.time()-t0:.2f}s")
    return indice


def mostrar(resultados, n=10):
    for r in resultados[:n]:
        cod = r['id']
        cod_fmt = f"{cod[:4]}-{cod[4]}/{cod[5:]}"
        extra = f" — via: {r['descritor_casado'][:60]}" if r.get('descritor_casado') else ''
        print(f"   [{r['score']:2d}] {cod_fmt}  {r['descricao'][:60]}{extra}")


def main():
    indice = carregar_indice()

    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        query = ' '.join(sys.argv[1:])
        t0 = time.time()
        res = cnae_busca.buscar(indice, query)
        print(f"\n'{query}' — {len(res)} resultados em {(time.time()-t0)*1000:.0f}ms")
        mostrar(res, 20)
        return

    falhas = 0
    for query, obrigatorios, proibidos in CASOS:
        t0 = time.time()
        res = cnae_busca.buscar(indice, query, limite=20)
        ms = (time.time() - t0) * 1000
        ids_todos = [r['id'] for r in res]
        ids_top10 = ids_todos[:10]

        faltando  = [c for c in obrigatorios if c not in ids_todos]
        indevidos = [c for c in proibidos if c in ids_top10]

        status = 'PASS' if not faltando and not indevidos else 'FAIL'
        if status == 'FAIL':
            falhas += 1
        print(f"\n[{status}] '{query}' — {len(res)} resultados em {ms:.0f}ms")
        if faltando:
            print(f"   FALTAM: {faltando}")
        if indevidos:
            print(f"   INDEVIDOS no top10: {indevidos}")
        mostrar(res, 6)

    print(f"\n{'='*60}")
    print(f"RESULTADO: {len(CASOS)-falhas}/{len(CASOS)} casos OK")
    if falhas:
        sys.exit(1)


if __name__ == '__main__':
    main()
