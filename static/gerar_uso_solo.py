from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

# ── Cores ──────────────────────────────────────────────────────────────────
COR_TITULO_BG  = colors.HexColor("#3D3D3D")
COR_SECAO_BG   = colors.HexColor("#D9D9D9")
COR_BORDA      = colors.HexColor("#7F7F7F")
COR_BORDA_FINA = colors.HexColor("#BFBFBF")
BRANCO         = colors.white
PRETO          = colors.black

W, H = A4
ML = 18*mm; MR = 28*mm; MT = 8*mm; MB = 16*mm
CW = W - ML - MR   # ≈ 164mm de largura útil

BRASAO  = "/tmp/brasao_branco.png"
LATERAL = "/tmp/ref_img_0.jpeg"
OUTPUT  = "/tmp/Requerimento_Uso_do_Solo_Atividade_Economica.pdf"

# ── Canvas: lateral + rodapé ───────────────────────────────────────────────
class MyCanvas(canvas.Canvas):
    def showPage(self):
        # lateral
        self.drawImage(LATERAL, W - 22*mm - 3*mm, MB + 18*mm,
                       width=22*mm, height=118*mm,
                       preserveAspectRatio=False, mask='auto')
        # rodapé
        self.setFont("Helvetica", 7)
        self.setFillColor(PRETO)
        self.drawCentredString(W/2, MB - 3*mm, "Página 1")
        self.drawCentredString(W/2, MB - 10*mm,
            "Av. do Cerrado, 999 – Park Lozandes, Paço Municipal, 2º andar, Bloco C , Goiânia – GO. CEP: 74884-900")
        super().showPage()

# ── Helpers de estilo ──────────────────────────────────────────────────────
def S(name, font="Helvetica", size=8, color=PRETO, align=TA_LEFT, leading=10, bold=False):
    return ParagraphStyle(name,
        fontName="Helvetica-Bold" if bold else font,
        fontSize=size, textColor=color, alignment=align, leading=leading)

def P(text, **kw): return Paragraph(text, S("_", **kw))

# ── Build ──────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT,
        bottomMargin=MB + 14*mm)
    story = []

    # ── 1. CABEÇALHO ───────────────────────────────────────────────────────
    brasao = Image(BRASAO, width=52*mm, height=17*mm)
    sefic  = Paragraph(
        "Secretaria Municipal de Eficiência – <b>SEFIC</b><br/>"
        "Gerência de Informação do Uso do Solo e Número Predial – <b>GERINF</b>",
        S("sefic", size=8, align=TA_RIGHT, leading=11))

    ht = Table([[brasao, sefic]], colWidths=[56*mm, CW - 56*mm])
    ht.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),  ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(ht)
    story.append(Spacer(1, 3*mm))

    # ── 2. TÍTULO + COD.646 ────────────────────────────────────────────────
    w_cod = 25*mm
    w_tit = CW - w_cod
    titulo_t = Table([[
        Paragraph("REQUERIMENTO – USO DO SOLO ATIVIDADE ECONÔMICA",
                  S("tit", size=12, color=BRANCO, align=TA_CENTER, leading=14, bold=True)),
        Paragraph("COD. 646",
                  S("cod", size=10, color=PRETO, align=TA_CENTER, leading=12, bold=True)),
    ]], colWidths=[w_tit, w_cod], rowHeights=[10*mm])
    titulo_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0), COR_TITULO_BG),
        ("BACKGROUND",(1,0),(1,0), BRANCO),
        ("BOX",(0,0),(-1,-1), 0.8, PRETO),
        ("LINEAFTER",(0,0),(0,0), 0.8, PRETO),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(titulo_t)
    story.append(Spacer(1, 3*mm))

    # ── 3. SEÇÃO 1 ─────────────────────────────────────────────────────────
    def sec_header(txt):
        t = Table([[Paragraph(txt, S("sh", size=8.5, bold=True, leading=11))]],
                  colWidths=[CW])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), COR_SECAO_BG),
            ("BOX",(0,0),(-1,-1), 0.5, COR_BORDA),
            ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),5),
        ]))
        return t

    def campo(label, h=13*mm):
        t = Table([[Paragraph(label, S("c", size=7.5, leading=10))]],
                  colWidths=[CW], rowHeights=[h])
        t.setStyle(TableStyle([
            ("BOX",(0,0),(-1,-1), 0.5, COR_BORDA),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),5),
        ]))
        return t

    story.append(sec_header("1- REQUERENTE / DADOS DO IMÓVEL / ÁREA OCUPADA"))
    story.append(campo("NOME OU RAZÃO SOCIAL:", 11*mm))
    story.append(campo("ENDEREÇO DO ESTABELECIMENTO:(RUA/AV, QUADRA, LOTE, BAIRRO, CEP)", 11*mm))
    story.append(campo("INSCRIÇÃO IMOBILIÁRIA: (IPTU)", 11*mm))
    story.append(campo("ÁREA OCUPADA PELO ESTABELECIMENTO - M²:", 11*mm))
    story.append(Spacer(1, 2*mm))

    # ── 4. SEÇÃO 2 — CNAE (12 linhas) ─────────────────────────────────────
    story.append(sec_header("2-  ATIVIDADES – CNAE / DESCRIÇÃO:"))

    cn = 15*mm; ce = 19*mm; cc = CW/2 - cn - ce
    cws = [cn, cc, ce, cn, cc, ce]

    def pc(t, bold=False):
        return Paragraph(t, S("pc", size=7, align=TA_CENTER, leading=9, bold=bold))
    def pl(t):
        return Paragraph(t, S("pl", size=7.5, leading=9))

    cnae_rows = [[pc(""), pc("CNAE", True), pc("ESCRITÓRIO*", True),
                  pc(""), pc("CNAE", True), pc("ESCRITÓRIO*", True)]]
    for _ in range(12):
        cnae_rows.append([pl("Nº CNAE:"), "", "", pl("Nº CNAE:"), "", ""])

    cnae_t = Table(cnae_rows, colWidths=cws, rowHeights=[6*mm] + [5*mm]*12)
    cnae_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(2,0), COR_SECAO_BG),
        ("BACKGROUND",(3,0),(5,0), COR_SECAO_BG),
        ("BOX",(0,0),(-1,-1), 0.5, COR_BORDA),
        ("INNERGRID",(0,0),(-1,-1), 0.3, COR_BORDA_FINA),
        ("LINEAFTER",(2,0),(2,-1), 0.8, COR_BORDA),
        ("LINEBELOW",(0,0),(-1,0), 0.5, COR_BORDA),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),3),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("TOPPADDING",(0,0),(-1,-1),1),
        ("BOTTOMPADDING",(0,0),(-1,-1),1),
    ]))
    story.append(cnae_t)
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph('*ESCRITÓRIO MARCAR <b>"SIM"</b> (QUANDO FOR O CASO)',
                           S("nota", size=7.5)))
    story.append(Spacer(1, 2*mm))

    # ── 5. SEÇÃO 3 — UMA ÚNICA TABELA (obs + tel/email + art299 + data + assinatura) ──
    # Colunas: col0=label(38mm) | col1=meio | col2=meio (col1+col2 = CW)
    c0 = 38*mm
    c2 = CW / 2
    c1 = c2 - c0
    cw3 = [c0, c1, c2]

    art299 = (
        "Art. 299 - Omitir, em documento público ou particular, declaração que dele devia constar, "
        "ou nele inserir ou fazer inserir declaração falsa ou diversa da que devia ser escrita, "
        "com o fim de prejudicar direito, criar obrigação ou alterar a verdade sobre fato "
        "juridicamente relevante: Pena - reclusão, de um a cinco anos, e multa, se o documento é "
        "público, e reclusão de um a três anos, e multa, de quinhentos mil réis a cinco contos "
        "de réis, se o documento é particular."
    )

    st_obs  = S("obs",  size=8.5, bold=True, leading=11)
    st_tel  = S("tel",  size=8,   bold=True, leading=10)
    st_art  = S("art",  size=6.8, leading=10)
    st_data = S("data", size=8,   align=TA_CENTER, leading=11)
    st_ass  = S("ass",  size=7.5, align=TA_CENTER, leading=10)

    # Linha de assinatura centralizada (20% espaço | 60% linha | 20% espaço)
    sig_inner = Table([["", "", ""]], colWidths=[CW*0.2, CW*0.6, CW*0.2], rowHeights=[5*mm])
    sig_inner.setStyle(TableStyle([
        ("LINEABOVE", (1,0), (1,0), 0.5, PRETO),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))

    sec3 = [
        # 0 — cabeçalho
        [Paragraph("3-  OBSERVAÇÕES:", st_obs), "", ""],
        # 1-4 — linhas de observação (4mm cada para caber na página)
        ["", None, None],
        ["", None, None],
        ["", None, None],
        ["", None, None],
        # 5 — telefone / e-mail
        [Paragraph("   TELEFONE:", st_tel), None, Paragraph("   E-MAIL:", st_tel)],
        # 6 — art. 299
        [Paragraph(art299, st_art), None, None],
        # 7 — data
        [Paragraph("GOIÂNIA, ___________ DE _________________________ DE 20_________ .", st_data), None, None],
        # 8 — espaço generoso para assinar
        ["", None, None],
        # 9 — linha de assinatura centralizada
        [sig_inner, None, None],
        # 10 — label assinatura
        [Paragraph("ASSINATURA DO REQUERENTE", st_ass), None, None],
    ]

    rh3 = [7*mm, 4*mm, 4*mm, 4*mm, 4*mm, 7*mm, 14*mm, 6*mm, 12*mm, 5*mm, 5*mm]

    t3 = Table(sec3, colWidths=cw3, rowHeights=rh3)
    t3.setStyle(TableStyle([
        # spans
        ("SPAN",(1,0),(2,0)),    # header: col1+2 vazio
        ("SPAN",(0,1),(2,1)),    # obs rows
        ("SPAN",(0,2),(2,2)),
        ("SPAN",(0,3),(2,3)),
        ("SPAN",(0,4),(2,4)),
        ("SPAN",(0,5),(1,5)),    # telefone: col0+1
        ("SPAN",(0,6),(2,6)),    # art299
        ("SPAN",(0,7),(2,7)),    # data
        ("SPAN",(0,8),(2,8)),    # espaço
        ("SPAN",(0,9),(2,9)),    # linha assinatura (full width)
        ("SPAN",(0,10),(2,10)), # label assinatura (full width)
        # borda externa
        ("BOX",(0,0),(-1,-1), 0.5, COR_BORDA),
        # cabeçalho
        ("BACKGROUND",(0,0),(0,0), COR_SECAO_BG),
        ("LINEAFTER",(0,0),(0,0), 0.5, COR_BORDA),
        ("LINEBELOW",(0,0),(-1,0), 0.5, COR_BORDA),
        # linhas obs
        ("LINEBELOW",(0,1),(-1,1), 0.3, COR_BORDA_FINA),
        ("LINEBELOW",(0,2),(-1,2), 0.3, COR_BORDA_FINA),
        ("LINEBELOW",(0,3),(-1,3), 0.3, COR_BORDA_FINA),
        ("LINEBELOW",(0,4),(-1,4), 0.3, COR_BORDA_FINA),
        # linha após telefone/email
        ("LINEBELOW",(0,5),(-1,5), 0.5, COR_BORDA),
        # separador telefone | email
        ("LINEAFTER",(1,5),(1,5), 0.5, COR_BORDA),
        # padding geral
        ("LEFTPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),3),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("VALIGN",(0,6),(-1,6),"TOP"),
        ("VALIGN",(0,9),(-1,9),"BOTTOM"),
        ("LEFTPADDING",(0,9),(2,9),0),
        ("RIGHTPADDING",(0,9),(2,9),0),
        ("TOPPADDING",(0,9),(2,9),0),
        ("BOTTOMPADDING",(0,9),(2,9),0),
    ]))
    story.append(t3)

    doc.build(story, canvasmaker=MyCanvas)
    print(f"✓ PDF gerado: {OUTPUT}")

build()
