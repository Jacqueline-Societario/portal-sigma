"""
blueprints/cnae_busca.py — Motor de busca da base CNAE local.
==============================================================
Funcoes puras, sem dependencia de Flask — importado por blueprints/cnae.py
e pelos scripts de QA (scripts/testar_busca_cnae.py).

Regras de busca (replicam o comportamento da busca oficial do IBGE/CONCLA):
- Stopwords ("de", "para", "e"...) sao ignoradas — nao pontuam.
- Termos significativos combinam em AND: a subclasse so aparece se TODOS
  os termos casarem em algum campo dela.
- Match por palavra exata ou por prefixo ("pneu" encontra "pneumaticos"),
  com variantes simples de plural ("pneus" -> "pneu").
- Sinonimos expandem a consulta (grupos IBGE + grupos Sigma em
  static/data/cnae_sinonimos.json): "loja de pneus" encontra "comercio".
- Ranking por onde o termo casou: denominacao oficial (5) > descritor (4)
  > notas explicativas (2) > hierarquia (1). Resultado agrupado por
  subclasse, informando o descritor que casou.
- Busca por codigo (query numerica): exato > parcial, como antes.
"""
import re
import json
import unicodedata

STOPWORDS = {
    'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'a', 'o', 'as', 'os',
    'para', 'por', 'com', 'sem', 'no', 'na', 'nos', 'nas', 'ao', 'aos',
    'um', 'uma', 'uns', 'umas', 'que', 'ou', 'ate', 'sobre',
}

# Pesos por camada de match (a melhor camada de cada termo pontua)
PESO_DENOMINACAO = 5
PESO_DESCRITOR   = 4
PESO_NOTAS       = 2
PESO_HIERARQUIA  = 1


def normalizar(texto: str) -> str:
    """Minusculas, sem acentos; hifens viram espaco (mao-de-obra -> mao de obra)."""
    texto = (texto or '').replace('-', ' ')
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()


def _palavras(texto: str) -> frozenset:
    return frozenset(w for w in re.findall(r'[a-z0-9]+', normalizar(texto)) if w)


def _variantes(termo: str) -> tuple:
    """Variantes simples de plural para match por prefixo."""
    v = {termo}
    if len(termo) >= 4:
        if termo.endswith('oes'):
            v.add(termo[:-3] + 'ao')
        if termo.endswith('es'):
            v.add(termo[:-2])
        if termo.endswith('s'):
            v.add(termo[:-1])
    return tuple(t for t in v if len(t) >= 3)


def carregar_sinonimos(caminho: str) -> dict:
    """Le cnae_sinonimos.json e devolve mapa termo -> conjunto do grupo."""
    mapa = {}
    try:
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
        for chave in ('grupos_ibge', 'grupos_sigma'):
            for grupo in dados.get(chave, []):
                grupo_norm = frozenset(normalizar(t) for t in grupo)
                for termo in grupo_norm:
                    mapa[termo] = mapa.get(termo, frozenset()) | grupo_norm
    except Exception:
        pass  # sem sinonimos a busca segue funcionando
    return mapa


def construir_indice(subclasses: list, sinonimos: dict) -> dict:
    """Pre-computa as estruturas normalizadas de busca (1x por processo)."""
    itens = []
    for s in subclasses:
        cod = s.get('codigo_sem_mascara', '')
        if not re.fullmatch(r'\d{7}', cod):
            continue  # descarta registro-cabecalho e lixo
        descritores = s.get('descritores', []) or []
        ctx = ' '.join([
            s.get('classe_desc', ''), s.get('grupo_desc', ''),
            s.get('divisao_desc', ''), s.get('secao_desc', ''),
        ])
        itens.append({
            'dados': s,
            'den_palavras':   _palavras(s.get('descricao', '')),
            'descritores':    [(d, _palavras(d)) for d in descritores],
            'notas_palavras': _palavras(s.get('notas', '')),
            'ctx_palavras':   _palavras(ctx),
        })
    return {'itens': itens, 'sinonimos': sinonimos}


def _termos_da_query(query: str, sinonimos: dict) -> list:
    """Tokens significativos; cada um vira um conjunto de variantes+sinonimos."""
    termos = []
    for t in re.findall(r'[a-z0-9]+', normalizar(query)):
        if t in STOPWORDS or len(t) < 2:
            continue
        expandido = set(_variantes(t)) or {t}
        for sin in sinonimos.get(t, ()):  # sinonimos do proprio termo
            expandido.update(_variantes(sin))
        termos.append(tuple(sorted(expandido)))
    return termos


def _casa(palavras: frozenset, expandido: tuple) -> bool:
    """True se alguma palavra do texto e igual ou comeca com alguma variante."""
    for e in expandido:
        if e in palavras:
            return True
    for p in palavras:
        for e in expandido:
            if p.startswith(e):
                return True
    return False


def _buscar_por_codigo(indice: dict, q_cod: str, limite: int) -> list:
    resultados = []
    for item in indice['itens']:
        cod = item['dados']['codigo_sem_mascara']
        if cod == q_cod:
            resultados.append((20, item))
        elif cod.startswith(q_cod) or q_cod in cod:
            resultados.append((10, item))
    resultados.sort(key=lambda x: (-x[0], x[1]['dados']['codigo_sem_mascara']))
    return [_formatar(s, it, [], ['codigo']) for s, it in resultados[:limite]]


def _formatar(score, item, termos, camadas, descritor_casado='') -> dict:
    s = item['dados']
    return {
        'id':            s['codigo_sem_mascara'],
        'descricao':     s.get('descricao', ''),
        'secao':         s.get('secao', ''),
        'secao_desc':    s.get('secao_desc', ''),
        'divisao':       s.get('divisao', ''),
        'divisao_desc':  s.get('divisao_desc', ''),
        'classe_desc':   s.get('classe_desc', ''),
        'score':         score,
        'match_em':      camadas,
        'descritor_casado': descritor_casado,
    }


def buscar(indice: dict, query: str, limite: int = 20) -> list:
    """Busca principal. Retorna lista de dicts prontos para o front."""
    query = (query or '').strip()
    if not query:
        return []

    q_cod = re.sub(r'\D', '', query)
    so_digitos = bool(q_cod) and not re.search(r'[a-zA-Z]', query)
    if so_digitos:
        return _buscar_por_codigo(indice, q_cod, limite)

    termos = _termos_da_query(query, indice['sinonimos'])
    if not termos:
        return []

    candidatos = []
    for item in indice['itens']:
        score = 0
        camadas = set()
        eliminado = False
        for expandido in termos:
            if _casa(item['den_palavras'], expandido):
                score += PESO_DENOMINACAO
                camadas.add('denominacao')
            elif any(_casa(pal, expandido) for _, pal in item['descritores']):
                score += PESO_DESCRITOR
                camadas.add('descritor')
            elif _casa(item['notas_palavras'], expandido):
                score += PESO_NOTAS
                camadas.add('notas')
            elif _casa(item['ctx_palavras'], expandido):
                score += PESO_HIERARQUIA
                camadas.add('hierarquia')
            else:
                eliminado = True
                break  # AND: termo sem match elimina a subclasse
        if not eliminado:
            candidatos.append((score, item, sorted(camadas)))

    candidatos.sort(key=lambda x: (-x[0], x[1]['dados']['codigo_sem_mascara']))

    resultados = []
    for score, item, camadas in candidatos[:limite]:
        descritor_casado = ''
        melhor = 0
        for texto, pal in item['descritores']:
            n = sum(1 for exp in termos if _casa(pal, exp))
            if n > melhor:
                melhor, descritor_casado = n, texto
        resultados.append(_formatar(score, item, termos, camadas, descritor_casado))
    return resultados
