"""
blueprints/procuracoes.py — Módulo Elaboração de Procurações
Gera procurações via Claude API com base nos dados informados pela usuária.
"""
import io
import os
import re
import uuid
import time
import logging
from datetime import date
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file, abort
import anthropic
import httpx

from blueprints.auth import login_obrigatorio

# ─── Regenerar template limpo na inicialização ────────────────────────────────

def _garantir_template_servicos_externos():
    """Recria o template de Serviços Externos sem dados de empresa hardcoded."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    modelos_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'modelos_procuracao')
    caminho = os.path.join(modelos_dir, 'procuracao_para_servicos_externos_terceirizado.docx')

    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(3)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(3)
        section.right_margin  = Cm(2)

    def _p(doc, texto, bold=False, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, color=None):
        p = doc.add_paragraph()
        p.alignment = align
        if not texto:
            return p
        run = p.add_run(texto)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.bold = bold
        if color:
            run.font.color.rgb = color
        return p

    _p(doc, 'PROCURAÇÃO PARA SERVIÇOS EXTERNOS',
       bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
       color=RGBColor(0xA7, 0x2C, 0x31))
    doc.add_paragraph()

    linhas = [
        ('OUTORGANTE: [RAZÃO SOCIAL], pessoa jurídica de direito privado, inscrita no CNPJ '
         'sob o nº [CNPJ], com sede em [ENDEREÇO COMPLETO], neste ato representada por '
         '[NOME DO REPRESENTANTE], [estado civil], [profissão/cargo], portador(a) da '
         'Cédula de Identidade RG nº [RG] e CPF nº [CPF];', False),
        ('', False),
        ('OUTORGADO(A): [NOME COMPLETO], [estado civil], [profissão], portador(a) da '
         'Cédula de Identidade RG nº [RG] e CPF nº [CPF], residente e domiciliado(a) '
         'à [ENDEREÇO COMPLETO];', False),
        ('', False),
        ('PODERES: Pelo presente instrumento particular de procuração, o(a) OUTORGANTE '
         'nomeia e constitui o(a) acima qualificado(a) como seu bastante procurador(a), '
         'para [DESCREVER OS PODERES: representar a empresa, assinar documentos, praticar '
         'atos junto a órgãos públicos e privados, etc.], podendo para tanto praticar todos '
         'os atos necessários ao fiel cumprimento deste mandato.', False),
        ('', False),
        ('A presente procuração é conferida com prazo de validade de [VIGÊNCIA / "por prazo '
         'indeterminado"], podendo ser revogada a qualquer tempo por instrumento escrito.', False),
        ('', False),
        ('', False),
        ('Goiânia, ___ de __________________ de 20___.', False),
        ('', False),
        ('', False),
    ]
    for texto, bold in linhas:
        _p(doc, texto, bold=bold)

    for txt in ['___________________________________________',
                '[NOME DO REPRESENTANTE]',
                '[CARGO]',
                'OUTORGANTE']:
        _p(doc, txt, align=WD_ALIGN_PARAGRAPH.CENTER)

    footer = doc.sections[0].footer
    pf = footer.paragraphs[0]
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = pf.add_run('Sigma Contabilidade — Além da Contabilidade | www.gsigma.com.br')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0xA7, 0x2C, 0x31)

    doc.save(caminho)

try:
    _garantir_template_servicos_externos()
except Exception:
    pass

procuracoes_bp = Blueprint('procuracoes', __name__, url_prefix='/procuracoes')

# ─── Textos dos modelos Sigma (para geração com template) ────────────────────
TEMPLATES_SIGMA = {
    'procuracao_sigma.docx': """\
PROCURAÇÃO

A empresa , estabelecida no endereço , inscrita no CNPJ nº , representada por , , , , residente e domiciliado(a) na , inscrito(a) no CPF sob o nº , nomeia e constitui como seus bastantes procuradores,

Bruno Augusto De Leles Carvalho, brasileiro, Gerente Contábil, portador da RG n° 4.296.269 DGPC/GO e CPF nº 009.216.091-32 com endereço profissional situado à Avenida T-2, nº 471, Focus Business Center, Sala 507, Setor Bueno, Goiânia/GO, CEP 74210-005, a quem confere amplos, gerais e ilimitados poderes, podendo substabelecer com ou sem reserva de poderes, para:

PODERES OUTORGADOS: Assinar documentos referentes aos procedimentos abaixo relacionados, nos seguintes órgãos públicos: Junta Comercial do Estado, Receita Federal do Brasil, Secretaria da Economia do Estado de  – SEFAZ, Instituto Nacional da Previdência Social – INSS, Caixa Econômica Federal, Fórum, Ministério do Trabalho, Procuradoria Geral da Fazenda, Prefeitura Municipal de  e suas Secretarias, como Agência Municipal do Meio Ambiente, Vigilância Sanitária e outras, Agência Nacional do Petróleo, Gás Natural e Biocombustíveis – ANP, Agência Nacional de Vigilância Sanitária – ANVISA, Sindicatos, Corpo de Bombeiros, Conselhos Profissionais ou em qualquer outro órgão público não citado e necessários para o bom e fiel cumprimento do presente mandato, conforme § 1° e 2°, artigo 654 do Código Civil, para:

Assinar requerimentos para abertura de processos de Constituição, Baixa de Empresa, Paralisação/Suspensão das Atividades, Alteração Contratual perante a Junta Comercial do Estado, Receita Federal do Brasil, Secretária de Estado da Economia – SEFAZ, Prefeituras e suas Secretarias.

Solicitar, protocolar e assinar inclusão e exclusão de contador e retirar certidões de qualquer a natureza;

Assinar e protocolar em recursos e defesas, bem como dar vistas em processos em nome da empresa;

Solicitar, requerer, protocolar, retirar e juntas documentos, bem como assinar em processos e requerimentos de Parcelamentos Fiscais;

Perante o Ministério do Trabalho, Receita Federal, Previdência Social e INSS: dar entrada, registrar/cadastrar senhas e solicitar segunda via de RAIS, CAGEDS, GEFIPS/SEFIPS, relatórios de FGTS pagos ou em aberto, resolver pendencias quanto seguro-desemprego dos funcionários da empresa, e o que mais for necessário para solução de problemas na área de Recursos Humanos /Pessoal;

Perante a Caixa Econômica Federal: RDT / RDE / DCN e todos os serviços relacionados a cadastro, apuração de inconsistências, débitos, apresentação e solicitação de documentos;

Dar entrada e assinar processos de Retificações de Imposto de Renda, PERDCOMP, incluindo pegar relatórios destes junto à Receita Federal;

Cadastrar senhas e acessos eletrônicos perante a Receita Federal, Secretaria de Estado da Economia – SEFAZ e na Prefeitura para REST, DMS etc.

Solicitar emissão, correção ou cancelamento de Nota Fiscal Avulsa da Secretária de Estado da Economia – SEFAZ e Nota Fiscal de Serviço Avulsa perante à Prefeitura Municipal;

Retirar, solicitar, protocolar e das vistas em processos de Alvarás e Licenças dos órgãos públicos, quais sejam, Corpo de Bombeiros, Vigilância Sanitária Municipal e Estadual, Agência ou Secretarial Ambiental Municipal e Estadual, bem como quaisquer outras licenças, alvarás e autorizações de Prefeitura.

Abrangendo a matriz e todas as filiais da empresa.

Este instrumento será válido por tempo indeterminado, responsabilizando-se os outorgados por todos os atos praticados no cumprimento deste.
""",

    'procuracao_poderes_especificos_sigma.docx': """\
PROCURAÇÃO

A empresa , estabelecida no endereço , inscrita no CNPJ nº , representada por , , , , residente e domiciliado(a) na , inscrito(a) no CPF sob o nº , nomeia e constitui como seus bastantes procuradores,

Bruno Augusto De Leles Carvalho, brasileiro, Gerente Contábil, portador da RG n° 4.296.269 DGPC/GO e CPF nº 009.216.091-32 e Jacqueline Benedito Silva, brasileira, inscrito no CPF nº 057.541.315-85, ambos com endereço profissional situado à Avenida T-2, nº 471, Focus Business Center, Sala 507, Setor Bueno, Goiânia/GO, CEP 74210-005, a quem confere amplos, gerais e ilimitados poderes, podendo substabelecer com ou sem reserva de poderes, para:

PODERES OUTORGADOS: [A PREENCHER CONFORME INSTRUÇÕES]

Este instrumento será válido por [VIGÊNCIA], responsabilizando-se os outorgados por todos os atos praticados no cumprimento deste.
""",

    'substabelecimento_com_reserva_sigma.docx': """\
SUBSTABELECIMENTO DE PROCURAÇÃO

Pelo presente instrumento particular de SUBSTABELECIMENTO, Bruno Augusto De Leles Carvalho, brasileiro, Gerente Contábil, portador da RG n° 4.296.269 DGPC/GO e CPF nº 009.216.091-32, substabelece com reserva de poderes, em favor de , inscrito no CPF , portador do RG , ambos com endereço profissional situado à Avenida T-2, nº 471, Focus Business Center, Sala 507, Setor Bueno, Goiânia/GO, CEP 74210-005, os poderes que lhes foram conferidos por , inscrita no CNPJ nº , poderes para atuação junto a:

[PODERES A ESPECIFICAR]

Este instrumento será válido por [VIGÊNCIA], responsabilizando-se os outorgados por todos os atos praticados no cumprimento deste.
""",

    'substabelecimento_sem_reserva_sigma.docx': """\
SUBSTABELECIMENTO DE PROCURAÇÃO

Pelo presente instrumento particular de SUBSTABELECIMENTO, Bruno Augusto De Leles Carvalho, brasileiro, Gerente Contábil, portador da RG n° 4.296.269 DGPC/GO e CPF nº 009.216.091-32, substabelece sem reserva de poderes, em favor de , inscrito no CPF , portador do RG , ambos com endereço profissional situado à Avenida T-2, nº 471, Focus Business Center, Sala 507, Setor Bueno, Goiânia/GO, CEP 74210-005, os poderes que lhes foram conferidos por , inscrita no CNPJ nº , podendo praticar os atos necessários na demanda, iguais aos que me foram outorgados.

Poderes Substabelecidos: [PODERES A ESPECIFICAR]

Este instrumento será válido por [VIGÊNCIA], responsabilizando-se os outorgados por todos os atos praticados no cumprimento deste.
""",
}

MODELOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'modelos_procuracao')

MODELOS_DISPONÍVEIS = [
    {
        'nome': 'Procuração Para Serviços Externos - Terceirizado',
        'arquivo': 'procuracao_para_servicos_externos_terceirizado.docx',
        'descricao': 'Procuração para prestadores de serviços externos / terceirizados',
    },
    {
        'nome': 'Procuração Poderes Específicos - Sigma',
        'arquivo': 'procuracao_poderes_especificos_sigma.docx',
        'descricao': 'Procuração com poderes específicos — modelo padrão Sigma',
    },
    {
        'nome': 'Procuração - Sigma',
        'arquivo': 'procuracao_sigma.docx',
        'descricao': 'Procuração geral — modelo padrão Sigma',
    },
    {
        'nome': 'Substabelecimento Com Reserva - Sigma',
        'arquivo': 'substabelecimento_com_reserva_sigma.docx',
        'descricao': 'Substabelecimento com reserva de poderes — modelo padrão Sigma',
    },
    {
        'nome': 'Substabelecimento Sem Reserva - Sigma',
        'arquivo': 'substabelecimento_sem_reserva_sigma.docx',
        'descricao': 'Substabelecimento sem reserva de poderes — modelo padrão Sigma',
    },
]

# Cache de procurações geradas (token → {docx, pdf, nome, ts})
_PROC_CACHE: dict = {}

# Dados do contador responsável da Sigma
BRUNO_CONTADOR = {
    'nome': 'Bruno Augusto De Leles Carvalho',
    'doc': '009.216.091-32',
    'qualificacao': (
        'Bruno Augusto De Leles Carvalho, brasileiro, Gerente Contábil, '
        'portador da RG n° 4.296.269 DGPC/GO e CPF nº 009.216.091-32, '
        'com endereço profissional situado à Avenida T-2, nº 471, '
        'Focus Business Center, Sala 507, Setor Bueno, Goiânia/GO, CEP 74210-005'
    ),
}


def _limpar_cache():
    agora = time.time()
    for token in list(_PROC_CACHE.keys()):
        if agora - _PROC_CACHE[token]['ts'] > 3600:
            del _PROC_CACHE[token]


# ─── Tipos de procuração disponíveis ────────────────────────────────────────

TIPOS_PROCURACAO = [
    'Procuração Pública Geral Ad Negotia',
    'Procuração Particular Geral Ad Negotia',
    'Procuração para Abertura de Empresa',
    'Procuração para Alteração Contratual',
    'Procuração para Encerramento de Empresa',
    'Procuração para Assuntos Fiscais e Tributários',
    'Procuração para Assuntos junto à Receita Federal',
    'Procuração para Assuntos junto ao INSS',
    'Procuração para Assuntos junto à Prefeitura',
    'Procuração para Assuntos junto ao Corpo de Bombeiros',
    'Procuração para Representação perante Instituições Financeiras',
    'Procuração para Recebimento de Valores',
    'Procuração para Assinatura de Contratos',
    'Procuração para Movimentação de Conta Bancária',
    'Procuração para Processos Administrativos',
    'Procuração para Fins Trabalhistas e Previdenciários',
    'Procuração para Registro em Cartório',
    'Substabelecimento de Procuração',
    'Procuração para Renovação de Alvará',
    'Procuração para Licenciamento Ambiental',
    'Outro (descrever)',
]

MESES_PT = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
]


def _data_extenso():
    hoje = date.today()
    return f'Goiânia, {hoje.day} de {MESES_PT[hoje.month - 1]} de {hoje.year}.'


logger = logging.getLogger(__name__)


def _gerar_procuracao_claude(dados: dict) -> str:
    """Chama Claude API para gerar o texto da procuração."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada.")

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=httpx.Timeout(timeout=180.0, connect=30.0),
        max_retries=2,
    )

    tipo = dados.get('tipo', '')
    vigencia = dados.get('vigencia', '')
    poderes = dados.get('poderes', '')
    observacoes = dados.get('observacoes', '')
    modelo_arquivo = dados.get('modelo_arquivo', '').strip()

    # Outorgante — qualificação estruturada
    outorgante_qualificacao = dados.get('outorgante_qualificacao', '').strip()
    if not outorgante_qualificacao:
        razao = dados.get('outorgante_razao_social', '')
        cnpj = dados.get('outorgante_cnpj', '')
        representante = dados.get('outorgante_representante', '')
        partes = [razao]
        if cnpj:
            partes.append(f'CNPJ {cnpj}')
        if representante:
            partes.append(f'representada por {representante}')
        outorgante_qualificacao = ', '.join(p for p in partes if p)

    # Outorgado — qualificação estruturada
    outorgado_qualificacao = dados.get('outorgado_qualificacao', '').strip()
    if not outorgado_qualificacao:
        outorgado_nome = dados.get('outorgado_nome', '')
        outorgado_doc = dados.get('outorgado_doc', '')
        partes_o = [outorgado_nome]
        if outorgado_doc:
            partes_o.append(f'CPF/CNPJ {outorgado_doc}')
        outorgado_qualificacao = ', '.join(p for p in partes_o if p)

    # ── Geração com template Sigma ────────────────────────────────────────
    template_texto = TEMPLATES_SIGMA.get(modelo_arquivo, '')
    if template_texto:
        prompt = f"""Você é um especialista em direito societário brasileiro e assistente da Sigma Contabilidade.

Abaixo está o MODELO PADRÃO desta procuração. Sua tarefa é preencher os campos em branco
(marcados com espaços vazios, vírgulas duplas ou colchetes) com os dados fornecidos,
mantendo EXATAMENTE a estrutura, parágrafos, pontuação e redação do modelo original.

MODELO ORIGINAL:
{template_texto}

DADOS PARA PREENCHIMENTO:
Outorgante (empresa): {outorgante_qualificacao}
{f"Vigência: {vigencia}" if vigencia else "Vigência: por prazo indeterminado"}
{f"Poderes específicos: {poderes}" if poderes else ""}
{f"Outorgado (para substabelecimento): {outorgado_qualificacao}" if outorgado_qualificacao and 'SUBSTABELECIMENTO' in modelo_arquivo.upper() else ""}
{f"Observações: {observacoes}" if observacoes else ""}

DATA: {_data_extenso()}

INSTRUÇÕES:
- Mantenha EXATAMENTE a estrutura, ordem de parágrafos e redação do modelo
- Substitua campos em branco (vírgulas seguidas de vírgula ou espaços entre vírgulas) com os dados fornecidos
- Substitua [VIGÊNCIA] com a vigência informada
- Para substabelecimentos: substitua os campos do substabelecido com os dados de outorgado fornecidos
- Para a procuração padrão Sigma: preencha o estado na SEFAZ e o município na Prefeitura a partir do endereço da empresa
- Use marcadores <<<NOME_EMPRESA>>> onde o nome da empresa (outorgante) deve aparecer em destaque na primeira menção
- Inclua ao final: a data ({_data_extenso()}) e linha de assinatura do Outorgante/Substabelecente
- NÃO adicione texto fora do modelo — apenas preencha os campos em branco
- NÃO inclua explicações ou comentários
"""
    else:
        # ── Geração livre (tipos não-Sigma) ───────────────────────────────
        prompt = f"""Você é um especialista em direito societário e empresarial brasileiro.
Elabore uma procuração profissional e juridicamente correta com base nas informações abaixo.

TIPO DE PROCURAÇÃO: {tipo}

OUTORGANTE (quem concede os poderes):
{outorgante_qualificacao}

OUTORGADO (quem recebe os poderes):
{outorgado_qualificacao}

PODERES A SEREM CONCEDIDOS:
{poderes}

{f"VIGÊNCIA: {vigencia}" if vigencia else ""}
{f"OBSERVAÇÕES ADICIONAIS: {observacoes}" if observacoes else ""}

DATA: {_data_extenso()}

INSTRUÇÕES DE FORMATAÇÃO:
- Escreva a procuração completa em português brasileiro formal e jurídico
- Use marcadores <<<NOME_OUTORGANTE>>> e <<<NOME_OUTORGADO>>> onde os nomes devem aparecer em destaque
- Estrutura obrigatória: cabeçalho PROCURAÇÃO, qualificação das partes, cláusula de outorga de poderes, cláusula de ratificação, local e data, linha de assinatura do outorgante
- Inclua a expressão "em causa própria" se aplicável
- Redija de forma clara, completa e sem ambiguidades
- NÃO inclua explicações ou comentários — apenas o texto da procuração
- Ao final, inclua apenas a data e o espaço para assinatura
"""

    logger.info("Gerando procuração: tipo=%s modelo=%s outorgante=%s",
                dados.get('tipo', ''), dados.get('modelo_arquivo', ''),
                dados.get('outorgante_razao_social', '')[:40])
    t0 = time.time()
    try:
        mensagem = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': prompt}]
        )
    except anthropic.APITimeoutError as e:
        logger.error("Timeout na API Anthropic após %.1fs: %s", time.time() - t0, e)
        raise RuntimeError(
            "A geração demorou mais do que o esperado. "
            "Verifique sua conexão e tente novamente. "
            "Se o problema persistir, reduza o texto dos campos."
        ) from e
    except anthropic.APIConnectionError as e:
        logger.error("Erro de conexão com API Anthropic após %.1fs: %s", time.time() - t0, e)
        raise RuntimeError(
            "Falha de conexão com o serviço de IA. Tente novamente em instantes."
        ) from e
    except anthropic.APIStatusError as e:
        logger.error("Erro de status Anthropic (HTTP %s) após %.1fs: %s",
                     e.status_code, time.time() - t0, e)
        raise RuntimeError(
            f"Serviço de IA retornou erro ({e.status_code}). Tente novamente."
        ) from e

    logger.info("Procuração gerada em %.1fs (%d tokens)",
                time.time() - t0, mensagem.usage.output_tokens)
    return mensagem.content[0].text


def _gerar_docx_procuracao(texto: str, titulo: str) -> io.BytesIO:
    """Gera arquivo Word (.docx) da procuração."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # Margens
    for section in doc.sections:
        section.top_margin = Cm(3)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(3)
        section.right_margin = Cm(2)

    def set_font(run, bold=False, size=12):
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.bold = bold
        rPr = run._r.get_or_add_rPr()
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        rPr.insert(0, rFonts)

    # Processa texto em parágrafos
    linhas = texto.split('\n')
    for linha in linhas:
        linha_stripped = linha.strip()
        if not linha_stripped:
            doc.add_paragraph()
            continue

        # Detectar títulos (PROCURAÇÃO, etc.)
        is_titulo = (linha_stripped.isupper() and len(linha_stripped) < 60) or \
                    linha_stripped.startswith('PROCURAÇÃO')

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_titulo else WD_ALIGN_PARAGRAPH.JUSTIFY

        # Processar marcadores <<<>>>
        partes = re.split(r'(<<<.+?>>>)', linha_stripped)
        for parte in partes:
            if parte.startswith('<<<') and parte.endswith('>>>'):
                conteudo = parte[3:-3]
                run = p.add_run(conteudo)
                set_font(run, bold=True, size=14 if is_titulo else 12)
                run.font.color.rgb = RGBColor(0xA7, 0x2C, 0x31)
            else:
                run = p.add_run(parte)
                set_font(run, bold=is_titulo, size=14 if is_titulo else 12)

    # Rodapé
    footer_section = doc.sections[0]
    footer = footer_section.footer
    p_footer = footer.paragraphs[0]
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_footer = p_footer.add_run('Sigma Contabilidade — Além da Contabilidade | www.gsigma.com.br')
    run_footer.font.size = Pt(9)
    run_footer.font.color.rgb = RGBColor(0xA7, 0x2C, 0x31)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _gerar_pdf_procuracao(texto: str, titulo: str) -> io.BytesIO:
    """Gera PDF da procuração usando reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

    def _esc(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    buf = io.BytesIO()
    doc_pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=3*cm, bottomMargin=2*cm,
        leftMargin=3*cm, rightMargin=2*cm,
    )

    sigma_red = colors.HexColor('#A72C31')

    style_normal = ParagraphStyle(
        'Normal_PT', parent=getSampleStyleSheet()['Normal'],
        fontName='Times-Roman', fontSize=12, leading=18,
        alignment=TA_JUSTIFY, spaceAfter=4,
    )
    style_titulo = ParagraphStyle(
        'Titulo_PT', parent=getSampleStyleSheet()['Normal'],
        fontName='Times-Bold', fontSize=14, leading=20,
        alignment=TA_CENTER, textColor=sigma_red, spaceAfter=14,
    )
    style_footer = ParagraphStyle(
        'Footer_PT', parent=getSampleStyleSheet()['Normal'],
        fontName='Times-Roman', fontSize=9,
        alignment=TA_CENTER, textColor=sigma_red,
    )

    story = []
    for linha in texto.split('\n'):
        s = linha.strip()
        if not s:
            story.append(Spacer(1, 8))
            continue
        is_titulo = (s.isupper() and len(s) < 60) or s.startswith('PROCURAÇÃO')
        # Processar marcadores <<<>>>
        partes = re.split(r'(<<<.+?>>>)', s)
        html = ''.join(
            f'<b><font color="#A72C31">{_esc(p[3:-3])}</font></b>'
            if p.startswith('<<<') and p.endswith('>>>')
            else _esc(p)
            for p in partes
        )
        story.append(Paragraph(html, style_titulo if is_titulo else style_normal))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        'Sigma Contabilidade — Além da Contabilidade | www.gsigma.com.br',
        style_footer
    ))
    doc_pdf.build(story)
    buf.seek(0)
    return buf


# ─── Rotas ────────────────────────────────────────────────────────────────────

@procuracoes_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    return render_template('procuracoes/index.html',
                           tipos=TIPOS_PROCURACAO,
                           modelos=MODELOS_DISPONÍVEIS,
                           bruno=BRUNO_CONTADOR)


@procuracoes_bp.route('/modelo/<arquivo>')
def baixar_modelo(arquivo):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    # Segurança: só permite arquivos da lista conhecida
    nomes_validos = {m['arquivo'] for m in MODELOS_DISPONÍVEIS}
    if arquivo not in nomes_validos:
        abort(404)
    caminho = os.path.join(MODELOS_DIR, arquivo)
    if not os.path.exists(caminho):
        abort(404)
    nome_download = arquivo.replace('_', ' ').replace('.docx', '').title() + '.docx'
    return send_file(caminho, as_attachment=True, download_name=nome_download,
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


@procuracoes_bp.route('/gerar', methods=['POST'])
def gerar():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    dados = request.get_json()
    if not dados:
        return jsonify({'erro': 'Dados inválidos'}), 400

    campos_obrigatorios = ['tipo', 'outorgante_razao_social', 'outorgado_nome', 'poderes']
    for campo in campos_obrigatorios:
        if not dados.get(campo, '').strip():
            nomes = {
                'tipo': 'Tipo de procuração',
                'outorgante_razao_social': 'Razão Social do outorgante',
                'outorgado_nome': 'Nome do outorgado',
                'poderes': 'Poderes',
            }
            return jsonify({'erro': f'Campo obrigatório não preenchido: {nomes.get(campo, campo)}'}), 400

    try:
        texto = _gerar_procuracao_claude(dados)
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'erro': str(e)}), 503
    except Exception as e:
        logger.exception("Erro inesperado na geração de procuração")
        return jsonify({'erro': 'Erro interno ao gerar o documento. Tente novamente.'}), 500

    titulo = f"Procuração — {dados.get('outorgante_razao_social', 'EMPRESA')}"
    nome_base = f"Procuracao_{dados.get('outorgante_razao_social', 'documento').replace(' ', '_')[:30]}"

    try:
        buf_docx = _gerar_docx_procuracao(texto, titulo)
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Word: {str(e)}'}), 500

    pdf_bytes = None
    try:
        pdf_bytes = _gerar_pdf_procuracao(texto, titulo).read()
    except Exception:
        pass  # PDF é opcional; docx sempre disponível

    _limpar_cache()
    token = str(uuid.uuid4())
    _PROC_CACHE[token] = {
        'docx': buf_docx.read(),
        'pdf':  pdf_bytes,
        'nome': nome_base,
        'ts':   time.time(),
    }

    return jsonify({
        'token':   token,
        'nome':    nome_base,
        'pdf_ok':  pdf_bytes is not None,
    })


@procuracoes_bp.route('/download/<token>')
@procuracoes_bp.route('/download/<token>/<formato>')
def download(token, formato='docx'):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401

    entrada = _PROC_CACHE.get(token)
    if not entrada:
        return jsonify({'erro': 'Documento expirado. Gere novamente.'}), 404

    nome = entrada['nome']
    if formato == 'pdf':
        if not entrada.get('pdf'):
            return jsonify({'erro': 'PDF não disponível para este documento.'}), 500
        return send_file(
            io.BytesIO(entrada['pdf']),
            as_attachment=True,
            download_name=f'{nome}.pdf',
            mimetype='application/pdf',
        )
    return send_file(
        io.BytesIO(entrada['docx']),
        as_attachment=True,
        download_name=f'{nome}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
