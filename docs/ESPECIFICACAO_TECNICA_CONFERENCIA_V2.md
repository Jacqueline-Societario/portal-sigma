# Especificação Técnica — Módulo Conferência de Contrato Social v6
**Arquivo:** `blueprints/conferencia.py`
**Data base:** 06/05/2026
**Elaborado por:** Yuzu (análise) / Jacqueline Benedito (requisitos)
**Versão atual do módulo:** v5 (sem IA, Python/regex)

---

## 1. RESUMO EXECUTIVO

O módulo de Conferência de Contrato Social funciona como robô conferente documental —
não como parecerista jurídico. A versão atual (v5) apresenta 12 falhas que comprometem
a confiabilidade do relatório. Esta especificação define as correções necessárias para a
versão v6, mantendo a conferência 100% determinística (sem IA/Claude no relatório principal).

**Problemas críticos confirmados no relatório gerado em 06/05/2026:**
- Quadro societário exibiu trechos de qualificação civil como se fossem nomes de sócios
- Gerou pendência objetiva falsa baseada em dado extraído incorretamente
- Contradição interna: cabeçalho diz "número não identificado", corpo diz "12ª e 13ª"
- Título da seção de filial duplicado: "Filial 1 — Filial 1"
- CNPJ adicional na viabilidade (40.300.201/5200-17) listado sem classificação
- Alerta de filial não vinculada apareceu no corpo mas não nas pendências finais
- 11 linhas de CEP para 7 valores distintos (repetições sem agrupamento)
- Última alteração lida com limite de 10.000 caracteres (truncamento silencioso)
- Seção de pendências finais com apenas 1 item (falso), enquanto o corpo tinha vários alertas

---

## 2. DIAGNÓSTICO DOS PROBLEMAS ATUAIS

### Problema 1 — Extração incorreta de sócios
**Evidência no relatório:**
```
"expedida pela SSPII"       CPF 002.514.101-53  → Retirante
"portadora da Carteira de Identidade n"  CPF 699.885.101-44  → Remanescente
"expedida pela SSP"          CPF 295.639.251-49  → Remanescente
"portador da Carteira de identidade"     CPF 295.636.901-68  → Remanescente
"portador da Carteira de identidade"     CPF 331.768.841-68  → Remanescente
```
**Causa:** O regex atual captura o texto que aparece imediatamente antes do CPF no documento,
sem validar se esse texto é um nome próprio ou um trecho de qualificação civil.

**Impacto:** Todos os 5 sócios extraídos são inválidos. A pendência objetiva #1 gerada
("verificar se sócio retirante 'expedida pela SSPII' foi removido da consolidação") é falsa.

### Problema 2 — Pendência falsa
**Evidência:** A única pendência objetiva gerada no relatório é baseada em nome inválido.
O relatório passou com aparente "1 pendência objetiva", mas essa pendência não tem base real.

### Problema 3 — Contradição na numeração
**Evidência:**
- Cabeçalho: "Numeração: Número não identificado na minuta"
- Seção 3: "Sequência numérica correta: última alteração é a 12ª, a minuta é a 13ª (N+1)."
**Causa:** Duas funções independentes extraem o número da alteração; os resultados
não são compartilhados. O cabeçalho usa `_extrair_heuristicas()`, a seção 3 usa
`_extrair_numero_alteracao()` separadamente.

### Problema 4 — Título duplicado de filial
**Evidência:** "Por Estabelecimento — Filial 1 — Filial 1"
**Causa:** O título é construído como `f'Filial {i}'` e depois concatenado com `descricao_e`
que já contém o texto "Filial 1" inserido pelo usuário no campo descrição.

### Problema 5 — CNPJ adicional sem classificação
**Evidência:** Viabilidade da Matriz listou:
"CNPJs no documento: 02.889.277/0001-42, 40.300.201/5200-17"
O CNPJ 40.300.201/5200-17 não foi classificado. O sistema apenas listou sem informar
se é esperado, adicional, da filial ou divergente.

### Problema 6 — Alerta de filial ausente das pendências finais
**Evidência:** O corpo exibiu "Não foi possível vincular automaticamente esta filial a
uma cláusula específica da minuta." — mas esse alerta não apareceu nas pendências finais.

### Problema 7 — CEPs repetidos sem agrupamento
**Evidência:** 11 linhas de alerta de CEP para 7 valores distintos:
- 74.110.060 → 2x
- 74025 020 → 2x
- 74.075-040 → 3x
- 75.630-000 → 1x
- 74.465-539 → 1x
- 74.013-040 → 1x
- 74.013-030 → 1x

### Problema 8 — Truncamento silencioso de documento
**Evidência:** "Última Alteração Contratual — Recebida (10000 caracteres extraídos)"
O limite de 10.000 caracteres em `_extrair_heuristicas()` (`t = texto[:30000]`) afeta
a conferência de sequência e a extração de sócios sem avisar o usuário.

### Problema 9 — Pendências finais incompletas
Os seguintes alertas apareceram no corpo mas não nas pendências finais:
- CNPJ adicional na viabilidade (40.300.201/5200-17)
- Filial não vinculada à cláusula da minuta
- 11 alertas de CEP

### Problema 10 — Sem comparativo de consolidação contratual
O sistema conta cláusulas mas não compara o texto das cláusulas da consolidação
anterior com as da consolidação nova.

### Problema 11 — Conferência por estabelecimento sem tabela estruturada
CNPJ, NIRE, endereço, CNAE, eventos, protocolos e datas são conferidos de forma
narrativa sem tabela comparativa clara.

### Problema 12 — Status sem padronização
Itens do relatório usam linguagem informal ("Recebido. CNPJs no documento: ...") sem
status padronizado explícito (Conforme / Divergente / Ausente / etc.).

---

## 3. REGRAS INEGOCIÁVEIS (manter em v6)

- A conferência principal NÃO chama Claude/Anthropic (`USE_AI_FOR_MAIN_CONFERENCE = False`)
- Não fazer análise jurídica automática
- Não sugerir redação alternativa de cláusulas
- Não avaliar validade jurídica de cláusulas
- O usuário escolhe manualmente matriz e filiais
- O sistema não abre estabelecimentos automaticamente
- O sistema não inicia conferência automaticamente
- Documentos ignorados pelo usuário não bloqueiam a conferência
- O relatório deve ser objetivo, comparativo e operacional

---

## 4. MODELO DE DADOS — OBJETO DE RESULTADO ESTRUTURADO

Toda verificação do sistema deve produzir um objeto `ResultadoConferencia`. Este objeto
é a fonte única de dados tanto para o corpo do relatório quanto para as seções finais.
Não deve haver texto no relatório que não tenha origem em um objeto desse tipo.

```python
@dataclass
class ResultadoConferencia:
    escopo: str          # "Minuta" | "Ultima Alteração" | "Matriz" | "Filial 1" | "Consolidação"
    campo: str           # "CNPJ" | "NIRE" | "Endereço" | "CNAE" | "Sócio" | "CEP" | "Cláusula" | ...
    fonte_esperada: str  # "Minuta" | "Usuário" | "Última Alteração" | "Consolidação anterior"
    valor_esperado: str  # valor de referência
    fonte_encontrada: str  # "Viabilidade" | "FCN" | "DBE" | "Consolidação atual" | ...
    valor_encontrado: str  # valor extraído do documento
    status: str          # ver enum abaixo
    observacao: str      # mensagem para o usuário
    confianca_extracao: str   # "Alta" | "Média" | "Baixa" | "Não confiável"
    incluir_em_pendencias: bool
    tipo_pendencia: str  # ver enum abaixo
```

### 4.1 Enum de Status (obrigatório em todo item)

| Status | Quando usar |
|--------|-------------|
| `Conforme` | Valor encontrado = valor esperado |
| `Divergente` | Valor encontrado != valor esperado (dado confiável) |
| `Ausente` | Documento não foi anexado |
| `Ignorado pelo usuário` | Usuário marcou o documento como ignorado |
| `Não localizado` | Documento presente mas dado não encontrado no texto |
| `Atenção para conferência manual` | Sistema encontrou dado mas não tem confiança para classificar automaticamente |
| `Possível falha de extração` | Dado extraído é duvidoso (nome de sócio inválido, regex impreciso) |
| `Não aplicável` | A verificação não se aplica ao tipo de processo atual |

### 4.2 Enum de Tipo de Pendência

| Tipo | Seção final onde aparece |
|------|--------------------------|
| `Divergência objetiva` | Pendências Objetivas |
| `Alerta manual` | Alertas para Conferência Manual |
| `Falha de extração` | Possíveis Falhas de Extração |
| `Documento ignorado` | Documentos Ignorados pelo Usuário |
| `Ausência documental` | Pendências Objetivas |
| `Informação não localizada` | Alertas para Conferência Manual |

---

## 5. REGRAS CORRIGIDAS

### Regra C1 — Numeração da alteração (CORRIGIR)

**Problema:** Duas funções independentes extraem a numeração; resultados inconsistentes.

**Solução:** Criar função única `_extrair_numero_alteracao_unificado(texto)` que:
1. Aplica múltiplos patterns em ordem de confiança
2. Retorna `(numero: int | None, confianca: str)`
3. É chamada UMA VEZ por documento (minuta e última alteração) no início do job
4. O resultado é armazenado em variáveis de sessão do job e reutilizado em TODAS as seções

```python
def _extrair_numero_alteracao_unificado(texto: str) -> tuple[int | None, str]:
    """
    Retorna (numero, confianca).
    confianca: "Alta" | "Média" | "Baixa"
    """
    patterns_alta = [
        r'(\d+)[ªº°]\s*(?:altera[çc][aã]o\s+(?:ao\s+|do\s+)?contrato\s+social)',
        r'(\d+)[ªº°]\s*(?:altera[çc][aã]o\s+contratual)',
    ]
    patterns_media = [
        r'(\d+)[ªº°]\s+alteração',
        r'(\d+)[ªº°]\s*altera[çc][aã]o',
    ]
    patterns_baixa = [
        r'instrumento\s+particular[^\n]{0,60}(\d+)[ªº°]',
    ]
    for p in patterns_alta:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return int(m.group(1)), "Alta"
    for p in patterns_media:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return int(m.group(1)), "Média"
    for p in patterns_baixa:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return int(m.group(1)), "Baixa"
    return None, "Não localizado"
```

**Regra de exibição no cabeçalho:**
- Confiança Alta/Média → exibir normalmente: "13ª Alteração Contratual"
- Confiança Baixa → "Possível 13ª Alteração Contratual — confirmar manualmente"
- Não localizado → "Número não identificado — conferir manualmente"

**Regra interna de consistência:**
Nunca exibir "número não identificado" no cabeçalho E "12ª e 13ª" no corpo.
Se o corpo identificou o número, o cabeçalho deve usar o mesmo resultado.


### Regra C2 — Extração de sócios (CORRIGIR)

**Problema:** O regex captura texto de qualificação civil antes do CPF como nome de sócio.

**Novo fluxo:**

```
1. Localizar todos os CPFs/CNPJs no texto
2. Para cada CPF/CNPJ, extrair o contexto (300 chars antes)
3. Dentro do contexto, localizar o nome próprio (não a qualificação)
4. Validar o nome extraído contra lista de termos proibidos
5. Atribuir confiança à extração
6. Classificar (Remanescente / Retirante / Ingressante) APENAS se confiança >= Média
```

**Lista de termos que INVALIDAM o nome extraído** (a presença de qualquer um torna a extração inválida):

```python
TERMOS_QUALIFICACAO_CIVIL = [
    'expedida', 'expedido', 'SSP', 'SSPII', 'SSPC',
    'Carteira de Identidade', 'carteira de identidade',
    'identidade', 'portador', 'portadora',
    'residente', 'domiciliado', 'domiciliada',
    'brasileiro', 'brasileira', 'estrangeiro', 'estrangeira',
    'casado', 'casada', 'solteiro', 'solteira', 'viúvo', 'viúva',
    'divorciado', 'divorciada', 'separado', 'separada',
    'profissão', 'profissao', 'natural de',
    r'\bRG\b', r'\bCPF\b', r'\bCNPJ\b',
    'filiado', 'filiada', 'filho', 'filha',
]
```

**Algoritmo de extração de nome:**

```python
def _extrair_socios_v2(texto: str) -> list[dict]:
    """
    Extrai sócios com validação de qualidade.
    Retorna lista de dicts com: nome, cpf, confianca, valido
    """
    resultado = []

    # Encontrar CPFs
    cpf_pattern = r'(\d{3}\.?\d{3}\.?\d{3}[-/]?\d{2})'
    for m_cpf in re.finditer(cpf_pattern, texto):
        cpf_raw = m_cpf.group(1)
        cpf_norm = re.sub(r'[^\d]', '', cpf_raw)
        if len(cpf_norm) != 11:
            continue

        # Contexto antes do CPF (até 400 chars)
        inicio = max(0, m_cpf.start() - 400)
        contexto = texto[inicio:m_cpf.start()]

        nome, confianca = _extrair_nome_do_contexto(contexto)
        valido = _validar_nome_socio(nome)

        resultado.append({
            'cpf': cpf_norm,
            'nome': nome,
            'confianca': confianca,
            'valido': valido,
        })

    return _deduplicar_socios(resultado)


def _extrair_nome_do_contexto(contexto: str) -> tuple[str, str]:
    """
    Extrai o nome próprio mais próximo ao CPF.
    Retorna (nome, confianca).
    """
    # Tentar padrão: nome seguido de vírgula e qualificação
    # Ex: "JACI BARBOSA DE SOUZA, brasileira, casada, ..."
    m = re.search(
        r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s]{4,60})'
        r'(?:\s*,\s*(?:brasileiro|brasileira|casado|casada|solteiro|solteira|portador|portadora))',
        contexto, re.IGNORECASE
    )
    if m:
        return m.group(1).strip(), "Alta"

    # Padrão: sequência de palavras em maiúsculas (nome empresarial ou nome em caps)
    m2 = re.search(
        r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{4,60}(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ]))'
        r'\s*(?:,|\s+portador|\s+portadora|\s+brasileiro|\s+brasileira)',
        contexto
    )
    if m2:
        return m2.group(1).strip(), "Média"

    # Última tentativa: última palavra-sequência que parece nome próprio
    candidatos = re.findall(
        r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){1,5})',
        contexto
    )
    if candidatos:
        return candidatos[-1].strip(), "Baixa"

    return "", "Não localizado"


def _validar_nome_socio(nome: str) -> bool:
    """Retorna False se o nome contiver termos de qualificação civil."""
    if not nome or len(nome) < 5:
        return False
    nome_lower = nome.lower()
    for termo in TERMOS_QUALIFICACAO_CIVIL:
        if isinstance(termo, str):
            if termo.lower() in nome_lower:
                return False
        else:
            if re.search(termo, nome, re.IGNORECASE):
                return False
    # Validação adicional: nome deve ter pelo menos 2 palavras
    palavras = nome.strip().split()
    if len(palavras) < 2:
        return False
    return True
```

**Regras de classificação com validação:**
- `confianca = "Alta"` e `valido = True` → classificar normalmente (Remanescente/Retirante/Ingressante)
- `confianca = "Média"` e `valido = True` → classificar com observação "confirmar manualmente"
- `valido = False` ou `confianca = "Baixa"` ou `confianca = "Não localizado"` → Status: `Possível falha de extração`
  - Observação: "CPF {cpf} localizado, mas nome não identificado com segurança. Conferir manualmente."
  - `incluir_em_pendencias = True`, `tipo_pendencia = "Falha de extração"`
  - NÃO classificar como Retirante/Remanescente/Ingressante

**Regra anti-falso-positivo:**
Nunca gerar pendência objetiva baseada em nome com `confianca != "Alta"` ou `valido = False`.


### Regra C3 — Título de estabelecimento (CORRIGIR)

**Problema:** "Filial 1 — Filial 1" — o índice numérico é concatenado com a descrição
que já contém "Filial 1".

**Solução:** Montar o título como:
```python
def _titulo_estabelecimento(tipo_e: str, idx_filial: int, descricao_e: str, cnpj_e: str) -> str:
    if tipo_e == 'matriz':
        titulo = 'Matriz'
        if cnpj_e:
            titulo += f' — CNPJ: {cnpj_e}'
        return titulo

    # Para filial: usar descrição se existir, senão usar "Filial N"
    if descricao_e and descricao_e.strip():
        titulo = descricao_e.strip()
        # Evitar duplicação: se a descrição já começa com "Filial" seguido de número, usar só ela
        if not re.match(r'^[Ff]ilial\s+\d+', titulo):
            titulo = f'Filial {idx_filial} — {titulo}'
    else:
        titulo = f'Filial {idx_filial}'

    if cnpj_e:
        titulo += f' (CNPJ: {cnpj_e})'
    return titulo
```


### Regra C4 — Classificação de CNPJs nos documentos (CORRIGIR)

**Problema:** CNPJs encontrados nos documentos são apenas listados sem classificação.

**Nova lógica para cada documento de estabelecimento:**

```python
def _classificar_cnpjs_documento(
    cnpjs_encontrados: list[str],
    cnpj_esperado: str,        # CNPJ do estabelecimento (informado pelo usuário)
    cnpjs_todos_estabs: list[str],  # lista de todos os CNPJs de todos os estabelecimentos
) -> list[ResultadoConferencia]:
    resultados = []
    for cnpj in cnpjs_encontrados:
        if _cnpjs_iguais(cnpj, cnpj_esperado):
            resultados.append(ResultadoConferencia(
                campo="CNPJ",
                status="Conforme",
                observacao=f"CNPJ esperado encontrado: {cnpj}",
                incluir_em_pendencias=False,
            ))
        elif any(_cnpjs_iguais(cnpj, c) for c in cnpjs_todos_estabs):
            resultados.append(ResultadoConferencia(
                campo="CNPJ",
                status="Atenção para conferência manual",
                observacao=f"CNPJ {cnpj} pertence a outro estabelecimento do processo.",
                incluir_em_pendencias=True,
                tipo_pendencia="Alerta manual",
            ))
        else:
            resultados.append(ResultadoConferencia(
                campo="CNPJ",
                status="Atenção para conferência manual",
                observacao=f"CNPJ adicional {cnpj} localizado no documento sem vínculo automático com este estabelecimento.",
                incluir_em_pendencias=True,
                tipo_pendencia="Alerta manual",
            ))
    return resultados
```


### Regra C5 — CEPs agrupados (CORRIGIR)

**Problema:** CEPs listados repetidamente, uma linha por ocorrência.

**Nova lógica:**
```python
def _verificar_ceps(texto: str) -> list[ResultadoConferencia]:
    ceps_raw = re.findall(
        r'\bCEP[:\s]*(\d[\d.\s-]{6,12})\b',
        texto, re.IGNORECASE
    )

    # Contagem e identificação do problema por valor único
    contagem = {}  # cep_raw -> {count, problema}
    for cep in ceps_raw:
        cep_strip = cep.strip()
        cep_num = re.sub(r'[^\d]', '', cep_strip)
        if len(cep_num) != 8:
            continue

        # Verificar se está no formato correto XXXXX-XXX
        cep_correto = f'{cep_num[:5]}-{cep_num[5:]}'
        if cep_strip == cep_correto:
            continue  # Formato correto, ignorar

        # Identificar o problema
        if '.' in cep_strip:
            problema = f"ponto indevido (ex: {cep_strip})"
        elif ' ' in cep_strip.strip():
            problema = f"espaço indevido (ex: {cep_strip})"
        else:
            problema = f"formato inesperado (ex: {cep_strip})"

        chave = cep_num
        if chave not in contagem:
            contagem[chave] = {'count': 0, 'problema': problema, 'exemplo': cep_strip}
        contagem[chave]['count'] += 1

    resultados = []
    for cep_num, info in contagem.items():
        cep_correto = f'{cep_num[:5]}-{cep_num[5:]}'
        resultados.append(ResultadoConferencia(
            campo="CEP",
            status="Divergente",
            observacao=(
                f"CEP {info['exemplo']} — {info['problema']} — "
                f"{info['count']} ocorrência(s) — "
                f"Formato esperado: {cep_correto}"
            ),
            incluir_em_pendencias=True,
            tipo_pendencia="Alerta manual",
        ))
    return resultados
```

**Exibição no relatório:** Uma linha por CEP único, com coluna de ocorrências.


### Regra C6 — Limite de extração de texto (CORRIGIR)

**Problema:** `texto[:30000]` em `_extrair_heuristicas()` e possível limite em extração.

**Solução:**
1. Remover qualquer `texto[:N]` das funções de extração de sócios, numeração e comparação
2. Manter `texto[:30000]` APENAS para a inferência de tipo de processo (rápida e não crítica)
3. Se o texto extraído do documento tiver menos de 5.000 chars e o arquivo tiver mais de
   50KB, inferir truncamento e gerar alerta

```python
def _verificar_truncamento(texto_extraido: str, tamanho_arquivo_bytes: int) -> ResultadoConferencia | None:
    chars = len(texto_extraido)
    kb = tamanho_arquivo_bytes / 1024

    # Heurística: arquivo grande mas pouco texto extraído
    if kb > 50 and chars < 3000:
        return ResultadoConferencia(
            campo="Extração de texto",
            status="Atenção para conferência manual",
            observacao=(
                f"Documento de {kb:.0f}KB resultou em apenas {chars} caracteres extraídos. "
                "Possível leitura parcial. A conferência pode estar incompleta."
            ),
            incluir_em_pendencias=True,
            tipo_pendencia="Alerta manual",
        )
    return None
```

**Nota:** Para alterações contratuais longas com consolidação, o sistema deve extrair
o texto completo sem limite. O limite de `[:30000]` só pode ser aplicado para inferência
inicial de tipo, nunca para a conferência real de dados.


### Regra C7 — Filial não vinculada entra nas pendências finais (CORRIGIR)

**Problema:** O alerta de filial não vinculada aparece no corpo mas não nas pendências.

**Solução:** Quando `tipo_e == 'filial'` e o sistema não consegue vincular à cláusula:
```python
ResultadoConferencia(
    escopo=f"Filial {idx_filial}",
    campo="Vínculo com cláusula da minuta",
    status="Atenção para conferência manual",
    observacao=(
        f"Filial {idx_filial} não vinculada automaticamente à cláusula "
        f"correspondente da minuta. Conferir manualmente CNPJ, NIRE, endereço e evento."
    ),
    incluir_em_pendencias=True,
    tipo_pendencia="Alerta manual",
)
```


### Regra C8 — Pendências finais consolidadas (CORRIGIR)

**Problema:** A seção final de pendências é construída por lista manual (`pendencias.append()`),
desvinculada dos resultados estruturados.

**Solução:** Criar repositório único de resultados:

```python
class RepositorioResultados:
    def __init__(self):
        self._resultados: list[ResultadoConferencia] = []

    def adicionar(self, r: ResultadoConferencia):
        self._resultados.append(r)

    def pendencias_objetivas(self):
        return [r for r in self._resultados
                if r.incluir_em_pendencias
                and r.tipo_pendencia in ("Divergência objetiva", "Ausência documental")
                and r.confianca_extracao in ("Alta", "Média")]

    def alertas_manuais(self):
        return [r for r in self._resultados
                if r.incluir_em_pendencias
                and r.tipo_pendencia in ("Alerta manual", "Informação não localizada")]

    def falhas_extracao(self):
        return [r for r in self._resultados
                if r.tipo_pendencia == "Falha de extração"]

    def documentos_ignorados(self):
        return [r for r in self._resultados
                if r.status == "Ignorado pelo usuário"]
```

**Regra anti-falso-positivo crítica:**
`incluir_em_pendencias = True` com `tipo_pendencia = "Divergência objetiva"` SOMENTE
quando `confianca_extracao in ("Alta", "Média")`. Dados com `confianca_extracao = "Baixa"`
ou `"Não confiável"` vão para `"Falha de extração"`, nunca para `"Divergência objetiva"`.


---

## 6. NOVAS REGRAS A SEREM ADICIONADAS

### Regra N1 — Tabela comparativa por estabelecimento

Para cada estabelecimento (matriz e filiais), o relatório deve exibir tabela HTML:

```
| Campo           | Valor esperado (minuta) | Valor encontrado (doc) | Documento | Status | Observação |
|-----------------|------------------------|------------------------|-----------|--------|------------|
| CNPJ            | 02.889.277/0001-42     | 02.889.277/0001-42     | Viabilidade | Conforme | — |
| CNPJ adicional  | —                      | 40.300.201/5200-17     | Viabilidade | Atenção | CNPJ adicional sem vínculo |
| NIRE            | 62300000000            | Não localizado         | Viabilidade | Não localizado | — |
| CEP             | 74110-060              | 74.110.060             | Minuta  | Divergente | ponto indevido |
| CNAE principal  | 47.81-4-00             | 47.81-4-00             | Viabilidade | Conforme | — |
```

Campos da tabela: CNPJ, NIRE, Endereço completo, Logradouro, Número, Complemento,
Bairro, Município, UF, CEP, CNAE(s), Atividade econômica principal.


### Regra N2 — Comparativo da Consolidação Contratual (NOVA SEÇÃO)

**Quando ativar:** Quando houver minuta e última alteração, ambas recebidas e não truncadas.

**Objetivo:** Verificar se as cláusulas consolidadas que não foram objeto da alteração
permaneceram iguais entre a consolidação da última alteração registrada e a consolidação
da nova minuta.

**Importante:** Esta seção NÃO avalia validade jurídica. Apenas aponta se o texto mudou,
não mudou, desapareceu ou surgiu em relação à consolidação anterior.

#### Fluxo técnico:

**Passo 1 — Localizar a consolidação em cada documento:**
```python
MARCADORES_CONSOLIDACAO = [
    r'consoli[ds]a[çc][aã]o\s+do\s+contrato\s+social',
    r'contrato\s+social\s+consolidado',
    r'consoli[ds]a-se\s+o\s+contrato\s+social',
    r'da\s+consolida[çc][aã]o',
    r'\bconsolida[çc][aã]o\b',
]

def _localizar_consolidacao(texto: str) -> str | None:
    """Retorna o texto a partir do marcador de consolidação, ou None se não encontrado."""
    for pattern in MARCADORES_CONSOLIDACAO:
        m = re.search(pattern, texto, re.IGNORECASE)
        if m:
            return texto[m.start():]
    return None
```

**Passo 2 — Segmentar por cláusulas:**
```python
PATTERN_CLAUSULA = re.compile(
    r'(?:^|\n)\s*(?:CL[AÁ]USULA|Cl[aá]usula)\s+'
    r'(?:'
    r'PRIMEIRA|SEGUNDA|TERCEIRA|QUARTA|QUINTA|SEXTA|S[EÉ]TIMA|OITAVA|NONA|D[EÉ]CIMA|'
    r'DÉCIMA\s+PRIMEIRA|DÉCIMA\s+SEGUNDA|DÉCIMA\s+TERCEIRA|'
    r'primeira|segunda|terceira|quarta|quinta|sexta|sétima|oitava|nona|décima|'
    r'\d+[ªº°]?'
    r')',
    re.IGNORECASE | re.MULTILINE
)

def _segmentar_clausulas(texto_consolidacao: str) -> dict[str, str]:
    """
    Retorna dict: {identificador_clausula: texto_da_clausula}
    Ex: {"Cláusula Primeira": "texto...", "Cláusula Segunda": "texto..."}
    """
    matches = list(PATTERN_CLAUSULA.finditer(texto_consolidacao))
    clausulas = {}
    for i, m in enumerate(matches):
        inicio = m.start()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto_consolidacao)
        header = m.group(0).strip()
        corpo = texto_consolidacao[inicio:fim].strip()
        clausulas[header] = corpo
    return clausulas
```

**Passo 3 — Normalizar texto para comparação:**
```python
def _normalizar_para_comparacao(texto: str) -> str:
    """Remove diferenças irrelevantes para comparação de conteúdo."""
    t = texto.lower().strip()
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'\s+', ' ', t)                    # espaços múltiplos
    t = re.sub(r'[^\w\s,;:.()/\-]', '', t)        # pontuação irrelevante
    t = re.sub(r'\n+', ' ', t)                    # quebras de linha
    return t.strip()
```

**Passo 4 — Identificar temas alterados:**

O sistema deve sugerir temas automaticamente com base em regex, mas eles ficam apenas
como sugestão. O usuário pode confirmar/ajustar via campo no formulário antes de gerar.

```python
TEMAS_ALTERACAO = {
    'razao_social':     r'(?:raz[aã]o\s+social|nome\s+empresarial|denomina[çc][aã]o)',
    'objeto_social':    r'(?:objeto\s+social|atividade(?:s)?\s+econ[oô]mica)',
    'capital_social':   r'capital\s+social',
    'quadro_societario': r'(?:ingresso|retirada|cede\s+e\s+transfer|s[oó]cio)',
    'endereco_matriz':  r'(?:sede|endere[çc]o\s+da\s+(?:sede|empresa|matriz))',
    'abertura_filial':  r'(?:abrir|abertura|instala[çc][aã]o)[^\n]{0,60}filial',
    'alteracao_filial': r'(?:altera[çc][aã]o|transferência)[^\n]{0,60}filial',
    'baixa_filial':     r'(?:encerramento|baixa|fecha)[^\n]{0,60}filial',
    'administracao':    r'(?:administra[çc][aã]o|gerente|diretor)',
    'foro':             r'\bforo\b',
    'prazo':            r'(?:prazo\s+de\s+dura[çc][aã]o|prazo\s+social)',
    'enquadramento':    r'(?:simples\s+nacional|microempresa|empresa\s+de\s+pequeno)',
}
```

**Passo 5 — Comparar cláusulas correspondentes:**

```python
def _comparar_consolidacoes(
    clausulas_anterior: dict[str, str],
    clausulas_atual: dict[str, str],
    temas_alterados: list[str],
) -> list[ResultadoConferencia]:
    resultados = []

    # Mapa de correspondência por ordinal
    # Ex: "Cláusula Primeira" <-> "CLÁUSULA PRIMEIRA" <-> "Cláusula 1ª"
    # Normalizar identificadores para comparação

    for id_ant, texto_ant in clausulas_anterior.items():
        id_correspondente = _encontrar_clausula_correspondente(id_ant, clausulas_atual)

        if id_correspondente is None:
            resultados.append(ResultadoConferencia(
                campo=id_ant,
                status="Ausente",
                observacao=f"Cláusula '{id_ant}' presente na última alteração mas não localizada na minuta.",
                incluir_em_pendencias=True,
                tipo_pendencia="Alerta manual",
            ))
            continue

        texto_atual = clausulas_atual[id_correspondente]
        norm_ant = _normalizar_para_comparacao(texto_ant)
        norm_atual = _normalizar_para_comparacao(texto_atual)

        tema = _inferir_tema_clausula(texto_ant, temas_alterados)

        if norm_ant == norm_atual:
            status = "Conforme"
            obs = "Sem alteração de conteúdo relevante."
            incluir = False
        else:
            diferenca = _resumir_diferenca(texto_ant, texto_atual)
            if tema and any(t in temas_alterados for t in tema):
                status = "Alterada conforme evento"
                obs = f"Cláusula alterada. Tema '{', '.join(tema)}' está entre os eventos informados. {diferenca}"
                incluir = False
            else:
                status = "Divergente"
                obs = f"Cláusula alterada sem evento identificado. {diferenca}"
                incluir = True

        resultados.append(ResultadoConferencia(
            escopo="Comparativo de Consolidação",
            campo=id_ant,
            status=status,
            observacao=obs,
            incluir_em_pendencias=incluir,
            tipo_pendencia="Alerta manual" if incluir else None,
        ))

    # Cláusulas novas (existem na atual mas não na anterior)
    for id_atual in clausulas_atual:
        if not _encontrar_clausula_correspondente(id_atual, clausulas_anterior):
            resultados.append(ResultadoConferencia(
                campo=id_atual,
                status="Nova cláusula",
                observacao=f"Cláusula '{id_atual}' aparece na minuta mas não existia na última alteração.",
                incluir_em_pendencias=True,
                tipo_pendencia="Alerta manual",
            ))

    return resultados
```

**Passo 6 — Tabela de saída:**

```
Cláusula          | Tema provável        | Status                  | Diferença encontrada          | Ação sugerida
Cláusula Primeira | Nome empresarial     | Conforme                | Sem alteração relevante       | —
Cláusula Segunda  | Objeto social        | Alterada conforme evento| Texto do objeto foi alterado  | Conferir com documentos de apoio
Cláusula Terceira | Capital social       | Divergente              | Alteração textual sem evento  | Conferir manualmente
Cláusula Décima   | Filial               | Alterada conforme evento| Alteração de filial           | Conferir documentos da filial
```

**Quando o sistema não encontrar a consolidação:**
```
Status: Possível falha de extração
Observação: Seção de consolidação não localizada no documento. Comparativo entre consolidações não realizado.
```

---

## 7. ESTRUTURA REVISADA DO RELATÓRIO (v6)

```
1.  Cabeçalho (analista, data, tipo de processo, numeração, razão social, CNPJ)
2.  Resumo do processo
3.  Tipo de processo e eventos identificados
4.  Documentos anexados
5.  Documentos ignorados pelo usuário
6.  Documentos ausentes
7.  Conferência da minuta e última alteração
        7.1 Sequência numérica
        7.2 CNPJ consistente
        7.3 Local de assinatura vs. foro
8.  Comparativo da Consolidação Contratual — Última Alteração x Minuta Atual
        (apenas quando ambos os documentos forem recebidos e não truncados)
9.  Por Estabelecimento — Matriz
        Tabela comparativa (CNPJ, NIRE, Endereço, CEP, CNAEs, Atividades)
10. Por Estabelecimento — Filial N (repetir para cada filial)
        Tabela comparativa (mesmos campos)
11. Comparativo — Quadro Societário
        (apenas quando extração com confiança Alta ou Média)
12. Revisão Textual — Formatação e Preenchimento
        (CEPs agrupados, campos em branco, nome empresarial antigo)
13. Pendências Objetivas
        (divergências objetivas com alta/média confiança)
14. Alertas para Conferência Manual
        (CNPJs adicionais, filiais não vinculadas, CEPs, filiais não localizadas)
15. Possíveis Falhas de Extração
        (sócios com nome inválido, consolidação não localizada, dados de baixa confiança)
16. Documentos Ignorados pelo Usuário
17. Conclusão Operacional
        "Foram identificadas N pendências objetivas, N alertas para conferência manual,
         N possíveis falhas de extração e N documentos ignorados."
18. Aviso final obrigatório
```

**Remover do relatório:**
- Linha de log `[LOG] IA_CHAMADA=False | SEM_IA=True | ...` (não deve aparecer para o usuário)

---

## 8. STATUS PADRONIZADOS

| Status | Cor visual sugerida | Inclui em pendências |
|--------|--------------------|-----------------------|
| Conforme | verde | Não |
| Divergente | vermelho | Sim — Pendências Objetivas |
| Ausente | vermelho | Sim — Pendências Objetivas |
| Ignorado pelo usuário | amarelo | Sim — Documentos Ignorados |
| Não localizado | cinza | Sim — Alertas Manuais |
| Atenção para conferência manual | laranja | Sim — Alertas Manuais |
| Possível falha de extração | roxo/azul | Sim — Falhas de Extração |
| Não aplicável | cinza claro | Não |
| Alterada conforme evento | azul | Não |
| Nova cláusula | azul | Sim — Alertas Manuais |

---

## 9. REGRAS DE VALIDAÇÃO PARA EVITAR FALSOS POSITIVOS

1. **Nunca** gerar pendência objetiva com `confianca_extracao = "Baixa"` ou `"Não confiável"`
2. **Nunca** classificar como Retirante/Remanescente/Ingressante quando `valido = False`
3. **Nunca** exibir numeração no cabeçalho diferente da usada na verificação de sequência
4. **Nunca** repetir o mesmo CEP mais de uma vez na listagem (agrupar por valor único)
5. **Nunca** gerar título com texto duplicado em seções de estabelecimento
6. **Nunca** gerar conclusões definitivas baseadas em documento truncado
7. **Nunca** alimentar `tipo_pendencia = "Divergência objetiva"` com dados de qualificação civil
8. **Sempre** verificar se o nome de sócio contém termos da lista `TERMOS_QUALIFICACAO_CIVIL`
9. **Sempre** usar a mesma instância de `RepositorioResultados` para alimentar corpo e seções finais
10. **Sempre** exibir o aviso final obrigatório, mesmo em relatórios sem pendências

---

## 10. CRITÉRIOS DE ACEITAÇÃO

### CA-01 — Extração de sócios
- [ ] Nenhum nome de sócio deve conter termos da lista `TERMOS_QUALIFICACAO_CIVIL`
- [ ] CPF localizado sem nome confiável → Status "Possível falha de extração"
- [ ] Nenhuma pendência objetiva deve ser gerada com nome inválido
- [ ] Sócios com confiança "Alta" devem ser classificados normalmente
- [ ] Sócios com confiança "Baixa" ou inválidos devem aparecer apenas em "Falhas de Extração"

### CA-02 — Numeração da alteração
- [ ] Cabeçalho e seção de sequência devem exibir o mesmo número
- [ ] Não deve existir "número não identificado" no cabeçalho quando o corpo identifica o número
- [ ] Confiança "Baixa" → exibir com prefixo "possível"

### CA-03 — Títulos de estabelecimento
- [ ] "Filial 1" não deve aparecer duplicado no título da seção
- [ ] Matriz deve exibir CNPJ quando disponível
- [ ] Filial deve exibir CNPJ quando disponível

### CA-04 — CNPJs nos documentos
- [ ] Todo CNPJ encontrado deve ter classificação: Conforme, Adicional sem vínculo, ou Pertence a outro estabelecimento
- [ ] Nunca listar CNPJs sem status

### CA-05 — CEPs
- [ ] Cada CEP único deve aparecer apenas uma linha, com contagem de ocorrências
- [ ] Informar o problema específico (ponto, espaço, formato)
- [ ] CEPs devem aparecer na seção final de Alertas Manuais

### CA-06 — Truncamento de documento
- [ ] Arquivo com suspeita de truncamento deve exibir alerta
- [ ] Não deve gerar conclusão definitiva com documento truncado
- [ ] Alerta deve aparecer na seção final

### CA-07 — Filial não vinculada
- [ ] Alerta deve aparecer tanto no corpo quanto na seção final "Alertas para Conferência Manual"

### CA-08 — Pendências finais
- [ ] Todo alerta/divergência/falha no corpo deve estar refletido em uma das quatro seções finais
- [ ] A conclusão operacional deve contar corretamente os itens de cada seção

### CA-09 — Comparativo de consolidação
- [ ] Seção exibida apenas quando minuta e última alteração recebidas e não truncadas
- [ ] Cláusulas sem mudança → Status "Conforme"
- [ ] Cláusulas com mudança em tema alterado → "Alterada conforme evento"
- [ ] Cláusulas com mudança em tema não alterado → "Divergente" → seção final
- [ ] Cláusulas desaparecidas → "Ausente" → seção final
- [ ] Cláusulas novas → "Nova cláusula" → seção final

### CA-10 — Log interno
- [ ] A linha `[LOG] IA_CHAMADA=...` não deve ser exibida ao usuário final

---

## 11. CASOS DE TESTE

### Teste T01 — Sócio com qualificação civil
**Entrada:** Texto com `"portador da Carteira de Identidade nº 12345, CPF 123.456.789-00"`
**Esperado:** Status "Possível falha de extração", observação "CPF 12345678900 localizado, mas nome não identificado com segurança."
**Não esperado:** Classificação como Retirante, Remanescente ou Ingressante

### Teste T02 — Numeração consistente
**Entrada:** Minuta com "13ª Alteração", última alteração com "12ª Alteração"
**Esperado:** Cabeçalho = "13ª Alteração Contratual", Seção 7 = "12ª e 13ª — N+1 — Conforme"
**Não esperado:** Cabeçalho = "Número não identificado" + Seção 7 = "12ª e 13ª"

### Teste T03 — Título de filial
**Entrada:** tipo="filial", idx=1, descricao="Filial 1", cnpj="02.889.277/0005-76"
**Esperado:** "Filial 1 (CNPJ: 02.889.277/0005-76)"
**Não esperado:** "Filial 1 — Filial 1 (CNPJ: 02.889.277/0005-76)"

### Teste T04 — CNPJ adicional
**Entrada:** Viabilidade com CNPJs ["02.889.277/0001-42", "40.300.201/5200-17"], esperado="02.889.277/0001-42"
**Esperado:**
- 02.889.277/0001-42 → Conforme
- 40.300.201/5200-17 → "Atenção para conferência manual — CNPJ adicional sem vínculo"

### Teste T05 — CEPs repetidos
**Entrada:** Minuta com 3 ocorrências de "CEP 74.075-040" e 2 de "CEP 74.110.060"
**Esperado:** Relatório com 2 linhas (uma por CEP único), com colunas de ocorrências
**Não esperado:** 5 linhas de alertas de CEP

### Teste T06 — Documento truncado
**Entrada:** Última alteração com exatamente 10.000 chars e arquivo de 80KB
**Esperado:** Alerta "Possível leitura parcial. A conferência pode estar incompleta."

### Teste T07 — Filial não vinculada nas pendências
**Entrada:** Filial sem CNPJ nem NIRE informados
**Esperado:** Alerta aparece no corpo E em "Alertas para Conferência Manual"

### Teste T08 — Pendências finais completas
**Entrada:** Relatório com 3 alertas de CEP, 1 CNPJ adicional, 1 filial não vinculada
**Esperado:** Seção "Alertas para Conferência Manual" com 5 itens
**Não esperado:** Seção vazia ou com menos itens

### Teste T09 — Comparativo de consolidação conforme
**Entrada:** Consolidação anterior = consolidação atual (mesmas cláusulas, sem alteração)
**Esperado:** Todas as cláusulas com Status "Conforme"

### Teste T10 — Log interno removido
**Entrada:** Qualquer relatório gerado
**Esperado:** Linha "[LOG] IA_CHAMADA=..." não visível ao usuário

---

## 12. CHECKLIST DE IMPLEMENTAÇÃO (ordem de prioridade)

### Prioridade 1 — Correções críticas (falsos positivos e contradições)

- [ ] **P1.1** Criar função `_extrair_numero_alteracao_unificado()` com retorno `(numero, confianca)`
- [ ] **P1.2** Armazenar resultado em variável de sessão do job e reutilizar em cabeçalho, seção 7 e pendências
- [ ] **P1.3** Eliminar chamada separada de `_extrair_numero_alteracao()` no corpo do relatório
- [ ] **P1.4** Implementar `_extrair_socios_v2()` com validação contra `TERMOS_QUALIFICACAO_CIVIL`
- [ ] **P1.5** Implementar `_validar_nome_socio()` com lista de termos proibidos
- [ ] **P1.6** Bloquear pendência objetiva com `confianca_extracao` Baixa ou Não confiável
- [ ] **P1.7** Remover linha `[LOG] IA_CHAMADA=...` da saída HTML do relatório

### Prioridade 2 — Correções visuais e estruturais

- [ ] **P2.1** Corrigir `_titulo_estabelecimento()` para evitar duplicação "Filial 1 — Filial 1"
- [ ] **P2.2** Implementar `_verificar_ceps()` com agrupamento por CEP único + contagem de ocorrências
- [ ] **P2.3** Exibir CEPs em tabela com colunas: CEP encontrado | Problema | Ocorrências | Formato esperado | Status
- [ ] **P2.4** Implementar `_classificar_cnpjs_documento()` com classificação: Conforme / Adicional sem vínculo / Pertence a outro estabelecimento

### Prioridade 3 — Repositório de resultados e pendências finais

- [ ] **P3.1** Criar dataclass `ResultadoConferencia` com todos os campos especificados
- [ ] **P3.2** Criar classe `RepositorioResultados` com métodos de filtragem por tipo
- [ ] **P3.3** Refatorar toda função de verificação para retornar `ResultadoConferencia`
- [ ] **P3.4** Substituir `pendencias.append()` por `repo.adicionar(resultado)`
- [ ] **P3.5** Gerar as quatro seções finais a partir do repositório (não de lista manual)
- [ ] **P3.6** Garantir que alerta de filial não vinculada entra no repositório com `incluir_em_pendencias=True`
- [ ] **P3.7** Atualizar conclusão operacional para contar as quatro seções separadamente

### Prioridade 4 — Tabela comparativa por estabelecimento

- [ ] **P4.1** Criar função `_gerar_tabela_estabelecimento()` que retorna HTML de tabela
- [ ] **P4.2** Implementar linhas para: CNPJ, NIRE, Endereço, CEP, CNAE(s)
- [ ] **P4.3** Aplicar a tabela em todas as seções de estabelecimento (matriz e filiais)
- [ ] **P4.4** Incluir coluna "Documento" indicando a origem do valor encontrado

### Prioridade 5 — Truncamento de documento

- [ ] **P5.1** Remover limite `[:10000]` das funções de extração de sócios e numeração
- [ ] **P5.2** Manter `[:30000]` apenas na inferência rápida de tipo de processo
- [ ] **P5.3** Implementar `_verificar_truncamento()` com heurística de KB vs chars
- [ ] **P5.4** Bloquear conclusão definitiva quando truncamento for detectado

### Prioridade 6 — Comparativo de consolidação (nova seção)

- [ ] **P6.1** Implementar `_localizar_consolidacao()` com os marcadores definidos
- [ ] **P6.2** Implementar `_segmentar_clausulas()` com os patterns definidos
- [ ] **P6.3** Implementar `_normalizar_para_comparacao()` ignorando diferenças irrelevantes
- [ ] **P6.4** Implementar mapa de correspondência de cláusulas por ordinal normalizado
- [ ] **P6.5** Implementar `_inferir_tema_clausula()` com os 14 temas mapeados
- [ ] **P6.6** Implementar `_comparar_consolidacoes()` com os 7 status de cláusula
- [ ] **P6.7** Gerar tabela HTML com colunas: Cláusula | Tema | Última Alt. | Minuta | Status | Observação
- [ ] **P6.8** Alimentar repositório de resultados com divergências do comparativo
- [ ] **P6.9** Adicionar seção ao relatório apenas quando ambos os documentos estão disponíveis

---

## 13. AVISO FINAL OBRIGATÓRIO (texto exato)

> "Esta conferência possui natureza exclusivamente documental e comparativa. Ela não
> substitui a análise jurídica das cláusulas contratuais pela liderança do setor ou
> pelo profissional responsável."

Este aviso deve aparecer ao final de TODOS os relatórios, independentemente do resultado.

---

*Especificação elaborada com base no relatório de conferência gerado em 06/05/2026,
empresa JACI BARBOSA DE SOUZA E CIA (CNPJ 02.889.277/0001-42), 13ª Alteração Contratual.*
