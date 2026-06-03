"""
blueprints/processos.py — Processos em Andamento (Google Forms)
Recebe respostas via webhook e gerencia processos internos do setor societário.
"""
import io
from flask import (Blueprint, render_template, redirect, url_for, request,
                   jsonify, session, send_file)
from blueprints.auth import login_obrigatorio
import database

processos_bp = Blueprint('processos', __name__, url_prefix='/processos')

STATUS_OPCOES = [
    'Novo',
    'Em análise',
    'Pendente com cliente',
    'Aguardando assinatura',
    'Aguardando protocolo',
    'Em exigência',
    'Concluído',
    'Arquivado',
]

PER_PAGE = 10


# ── Listagem principal ─────────────────────────────────────────────────────────

@processos_bp.route('/')
def index():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))

    aba      = request.args.get('aba', 'ativos')
    page     = max(1, int(request.args.get('page', 1) or 1))
    arquivado = 1 if aba == 'arquivados' else 0

    total        = database.count_processos_formularios(arquivado)
    processos    = database.get_processos_formularios(arquivado, page, PER_PAGE)
    usuarios     = database.get_users_ativos()
    total_pages  = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    total_ativos = database.count_processos_formularios(0)
    total_arq    = database.count_processos_formularios(1)

    return render_template(
        'processos/index.html',
        processos=processos,
        usuarios=usuarios,
        aba=aba,
        page=page,
        total_pages=total_pages,
        total=total,
        total_ativos=total_ativos,
        total_arquivados=total_arq,
        status_opcoes=STATUS_OPCOES,
    )


# ── Atualizar status ───────────────────────────────────────────────────────────

@processos_bp.route('/<int:processo_id>/status', methods=['POST'])
def atualizar_status(processo_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    novo_status = (request.json or {}).get('status', '')
    if novo_status not in STATUS_OPCOES:
        return jsonify({'erro': 'Status inválido'}), 400
    database.update_processo_formulario(processo_id, {'status': novo_status})
    return jsonify({'ok': True})


# ── Atualizar responsável ──────────────────────────────────────────────────────

@processos_bp.route('/<int:processo_id>/responsavel', methods=['POST'])
def atualizar_responsavel(processo_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    responsavel_id = (request.json or {}).get('responsavel_id') or None
    database.update_processo_formulario(processo_id, {'responsavel_id': responsavel_id})
    return jsonify({'ok': True})


# ── Atualizar observações ──────────────────────────────────────────────────────

@processos_bp.route('/<int:processo_id>/observacoes', methods=['POST'])
def atualizar_observacoes(processo_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    user_id = session.get('user_id')
    texto   = (request.json or {}).get('observacoes', '')
    database.update_processo_observacoes(processo_id, texto, user_id)
    return jsonify({'ok': True})


# ── Arquivar / Reativar ────────────────────────────────────────────────────────

@processos_bp.route('/<int:processo_id>/arquivar', methods=['POST'])
def arquivar(processo_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    database.update_processo_formulario(processo_id, {'arquivado': 1})
    return jsonify({'ok': True})


@processos_bp.route('/<int:processo_id>/reativar', methods=['POST'])
def reativar(processo_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    database.update_processo_formulario(processo_id, {'arquivado': 0})
    return jsonify({'ok': True})


# ── Download PDF ───────────────────────────────────────────────────────────────

def _slugify(s: str) -> str:
    """Converte texto em slug seguro para nome de arquivo."""
    import unicodedata, re
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^\w\s-]', '', s.lower())
    return re.sub(r'\s+', '-', s).strip('-')[:50]


@processos_bp.route('/<int:processo_id>/pdf')
def baixar_pdf(processo_id):
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    processo  = database.get_processo_formulario_by_id(processo_id)
    if not processo:
        return 'Processo não encontrado', 404
    respostas = database.get_respostas_processo(processo_id)

    # Extrair razão social (ou nome da empresa para Alteração Contratual)
    razao = ''
    for r in respostas:
        perg = (r.get('pergunta') or '').lower()
        if 'razão social' in perg and (r.get('resposta') or '').strip():
            razao = r['resposta'].strip()
            break
    if not razao:
        for r in respostas:
            perg = (r.get('pergunta') or '').lower()
            if 'informe o nome da empresa' in perg and (r.get('resposta') or '').strip():
                razao = r['resposta'].strip()
                break

    pdf_buf   = _gerar_pdf_processo(processo, respostas)

    tipo  = _slugify(processo.get('tipo_processo') or 'processo')
    data  = str(processo.get('data_envio') or processo.get('criado_em') or '')[:10]
    ident = _slugify(razao) if razao else str(processo_id)
    nome  = f"{tipo}_{ident}_{data}.pdf"
    return send_file(pdf_buf, as_attachment=True, download_name=nome,
                     mimetype='application/pdf')


# ── Admin: formulários cadastrados ────────────────────────────────────────────

@processos_bp.route('/admin/formularios')
def admin_formularios():
    if login_obrigatorio():
        return redirect(url_for('auth.login'))
    if not session.get('is_admin'):
        return redirect(url_for('processos.index'))
    formularios = database.get_formularios_cadastrados()
    return render_template('processos/formularios.html', formularios=formularios)


@processos_bp.route('/admin/formularios', methods=['POST'])
def admin_formulario_criar():
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if not session.get('is_admin'):
        return jsonify({'erro': 'Acesso negado'}), 403
    data     = request.json or {}
    nome     = (data.get('nome') or '').strip()
    tipo     = (data.get('tipo_processo') or '').strip()
    link     = (data.get('link_formulario') or '').strip()
    form_id  = (data.get('form_id') or '').strip()
    sheet_id = (data.get('sheet_id') or '').strip()
    if not nome or not tipo:
        return jsonify({'erro': 'Nome e tipo são obrigatórios'}), 400
    fid = database.criar_formulario_cadastrado(nome, tipo, link, form_id, sheet_id)
    return jsonify({'ok': True, 'id': fid})


@processos_bp.route('/admin/formularios/<int:form_id>/toggle', methods=['POST'])
def admin_formulario_toggle(form_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if not session.get('is_admin'):
        return jsonify({'erro': 'Acesso negado'}), 403
    database.toggle_formulario_ativo(form_id)
    return jsonify({'ok': True})


@processos_bp.route('/admin/formularios/<int:form_id>/deletar', methods=['POST'])
def admin_formulario_deletar(form_id):
    if login_obrigatorio():
        return jsonify({'erro': 'Não autorizado'}), 401
    if not session.get('is_admin'):
        return jsonify({'erro': 'Acesso negado'}), 403
    database.deletar_formulario_cadastrado(form_id)
    return jsonify({'ok': True})


# ── Gerador de PDF (ReportLab) ─────────────────────────────────────────────────

# Palavras-chave para classificar perguntas em seções
_KW_EMPRESA = (
    'razão social', 'nome fantasia', 'atividade', 'atividades', 'cnae',
    'endereço', 'sede', 'tamanho', 'metragem', 'm²', 'iptu',
    'funcionamento', 'horário', 'tributação', 'regime', 'faturamento',
    'atuação', 'modalidade', 'empresa que estamos alterando',
    'informe o nome da empresa', 'nome da empresa',
    'natureza jurídica', 'objeto social',
)
_KW_SOCIOS = (
    'sócio', 'socio', 'participação', 'estado civil', 'cônjuge',
    'administrador', 'ficha informativa', 'cpf', 'rg', 'identidade',
    'data de nascimento', 'naturalidade', 'profissão',
)


def _classi_resposta(pergunta: str) -> str:
    """Retorna 'empresa', 'socios' ou 'outros' conforme palavras-chave."""
    p = pergunta.lower()
    for kw in _KW_EMPRESA:
        if kw in p:
            return 'empresa'
    for kw in _KW_SOCIOS:
        if kw in p:
            return 'socios'
    return 'outros'


def _safe(texto: str) -> str:
    return (str(texto or '')
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br/>'))


def _gerar_pdf_processo(processo, respostas):
    """Gera PDF estruturado em seções com as respostas do formulário."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    HRFlowable)
    from reportlab.lib.styles import ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.2*cm, rightMargin=2.2*cm)

    sigma_red   = HexColor('#A72C31')
    cinza       = HexColor('#6b7280')
    escuro      = HexColor('#1a1a1a')
    cinza_claro = HexColor('#e5e7eb')
    sec_bg      = HexColor('#f5f5f5')

    s_cabecalho = ParagraphStyle('cab', fontName='Helvetica', fontSize=9,
                                  textColor=cinza, spaceAfter=2)
    s_titulo    = ParagraphStyle('tit', fontName='Helvetica-Bold', fontSize=17,
                                  textColor=sigma_red, spaceAfter=6)
    s_meta      = ParagraphStyle('meta', fontName='Helvetica', fontSize=10,
                                  textColor=cinza, spaceAfter=3)
    s_secao     = ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=11,
                                  textColor=sigma_red, spaceBefore=14, spaceAfter=6)
    s_pergunta  = ParagraphStyle('perg', fontName='Helvetica-Bold', fontSize=10,
                                  textColor=escuro, spaceBefore=7, spaceAfter=2)
    s_resposta  = ParagraphStyle('resp', fontName='Helvetica', fontSize=10,
                                  textColor=escuro, leftIndent=12, spaceAfter=2)
    s_obs       = ParagraphStyle('obs', fontName='Helvetica', fontSize=10,
                                  textColor=escuro, leading=15)

    story = []

    # ── Cabeçalho ──────────────────────────────────────────────────────────────
    story.append(Paragraph('Sigma Contabilidade — Portal Societário', s_cabecalho))
    story.append(Spacer(1, 0.15*cm))

    titulo = processo.get('form_name') or processo.get('tipo_processo') or 'Formulário'
    story.append(Paragraph(titulo, s_titulo))
    story.append(HRFlowable(color=sigma_red, thickness=1.5, width='100%'))
    story.append(Spacer(1, 0.3*cm))

    # ── Dados do Envio ─────────────────────────────────────────────────────────
    story.append(Paragraph('DADOS DO ENVIO', s_secao))

    data_envio = str(processo.get('data_envio') or '').replace('T', ' ')[:16]
    metas = []
    if processo.get('tipo_processo'):
        metas.append(f'<b>Tipo de processo:</b> {processo["tipo_processo"]}')
    if data_envio:
        metas.append(f'<b>Data e hora de envio:</b> {data_envio}')
    if processo.get('enviado_por'):
        metas.append(f'<b>Endereço de e-mail:</b> {processo["enviado_por"]}')
    if processo.get('response_id') and not str(processo.get('response_id', '')).startswith(('fallback_', 'sheet_')):
        metas.append(f'<b>ID da resposta:</b> {processo["response_id"]}')
    metas.append(f'<b>Status:</b> {processo.get("status", "Novo")}')
    for m in metas:
        story.append(Paragraph(m, s_meta))

    if not respostas:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph('Nenhuma resposta registrada.', s_meta))
    else:
        # Classificar respostas em seções
        empresa = [(r['pergunta'], r.get('resposta') or '') for r in respostas
                   if _classi_resposta(r.get('pergunta', '')) == 'empresa']
        socios  = [(r['pergunta'], r.get('resposta') or '') for r in respostas
                   if _classi_resposta(r.get('pergunta', '')) == 'socios']
        outros  = [(r['pergunta'], r.get('resposta') or '') for r in respostas
                   if _classi_resposta(r.get('pergunta', '')) == 'outros'
                   and 'e-mail' not in r.get('pergunta', '').lower()
                   and 'email' not in r.get('pergunta', '').lower()]

        def _bloco(pares):
            for perg, resp in pares:
                resp_txt = resp.strip() or '—'
                story.append(Paragraph(_safe(perg), s_pergunta))
                story.append(Paragraph(_safe(resp_txt), s_resposta))

        # ── Dados da Empresa ───────────────────────────────────────────────────
        if empresa:
            story.append(Spacer(1, 0.2*cm))
            story.append(HRFlowable(color=cinza_claro, thickness=0.5, width='100%'))
            story.append(Paragraph('DADOS DA EMPRESA', s_secao))
            _bloco(empresa)

        # ── Dados dos Sócios ───────────────────────────────────────────────────
        if socios:
            story.append(Spacer(1, 0.2*cm))
            story.append(HRFlowable(color=cinza_claro, thickness=0.5, width='100%'))
            story.append(Paragraph('DADOS DOS SÓCIOS', s_secao))
            _bloco(socios)

        # ── Demais Informações ─────────────────────────────────────────────────
        if outros:
            story.append(Spacer(1, 0.2*cm))
            story.append(HRFlowable(color=cinza_claro, thickness=0.5, width='100%'))
            story.append(Paragraph('DEMAIS INFORMAÇÕES', s_secao))
            _bloco(outros)

    # ── Observações Internas ───────────────────────────────────────────────────
    obs = (processo.get('observacoes') or '').strip()
    if obs:
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(color=cinza_claro, thickness=1, width='100%'))
        story.append(Paragraph('OBSERVAÇÕES INTERNAS', s_secao))
        story.append(Paragraph(_safe(obs), s_obs))

    doc.build(story)
    buf.seek(0)
    return buf
