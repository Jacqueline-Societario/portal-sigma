# Módulo Empresas — Documentação Técnica Oficial

**Última atualização:** 2026-05-12 (v2 — Certificado Digital + badges clicáveis)
**Portal:** Portal Societário Sigma Contabilidade
**Responsável pela documentação:** Yuzu (assistente IA)

---

## 1. Resumo Geral

O módulo Empresas é o componente central do Portal Societário Sigma Contabilidade. Gerencia o cadastro, consulta, edição e exportação das empresas clientes, integrando-se com a planilha de backup Google Sheets (aba "Consolidada") para sincronização bidirecional dos dados.

---

## 2. Como o Módulo está Incorporado ao Portal

O módulo é um Flask Blueprint registrado em `portal.py`:

```python
# portal.py — linha 54 e 267
from blueprints.empresas import empresas_bp
app.register_blueprint(empresas_bp)
```

O Blueprint usa o prefixo `/empresas/` (definido em `blueprints/empresas.py`, linha 82):

```python
empresas_bp = Blueprint('empresas', __name__, url_prefix='/empresas')
```

---

## 3. Infraestrutura Real em Produção

| Item | Valor |
|------|-------|
| **Servidor** | VPS — `129.121.54.101:22022` |
| **Usuário** | `jacqueline-benedito` |
| **Serviço** | `portal-sigma.service` (systemd user) |
| **Arquivo de serviço** | `/home/jacqueline-benedito/.config/systemd/user/portal-sigma.service` |
| **WorkingDirectory** | `/home/jacqueline-benedito/projetos/portal-sigma` |
| **ExecStart** | `.venv/bin/python3 portal.py` |
| **Porta** | 5080 (via variável `PORT` no `.env`) |
| **Python** | 3.9 (venv em `.venv/`) |
| **PID verificado em** | 2026-05-12 (PID 1250637) |
| **Logs** | `/home/jacqueline-benedito/logs/portal-sigma.log` |
| **Restart** | automático com `RestartSec=5` |

---

## 4. Arquivos Reais do Módulo Empresas

### Blueprint principal
```
blueprints/empresas.py          — 47414 bytes (versão 2026-05-12)
```

### Templates
```
templates/empresas/index.html   — 41594 bytes  — Tela principal: Consulta de Empresas
templates/empresas/detalhe.html — 14169 bytes  — Detalhe/visualização de uma empresa
templates/empresas/nova.html    —  6508 bytes  — Formulário de cadastro de nova empresa
```

### Arquivos de suporte (usados pelo módulo)
```
portal.py                       — 37351 bytes  — Arquivo principal Flask; registra blueprint; inicia backup diário
app.py                          — 64472 bytes  — Funções de base importadas por portal.py
database.py                     — 60299 bytes  — Acesso SQLite; funções de criação de tabelas
backup_sheets.py                — 14340 bytes  — Sincronização com Google Sheets; backup diário às 02:00
credentials/token.json          — Token OAuth Google (lido via GMAIL_TOKEN_PATH no .env)
.env                            — Variáveis de ambiente (PORT, GMAIL_TOKEN_PATH, BACKUP_SHEET_ID, etc.)
```

### Arquivos estáticos
Não há arquivos CSS ou JS específicos do módulo Empresas. Os estilos e scripts estão embutidos no próprio `index.html` (bloco `{% block extra_styles %}` e `{% block extra_scripts %}`).

### Backups automáticos existentes (não são código ativo)
```
blueprints/empresas.py.bak_20260413           — 18438 bytes
blueprints/empresas.py.bak_20260511_202505    — 16532 bytes
blueprints/empresas.py.bak_20260512_073448    — 17894 bytes
blueprints/empresas.py.bak_20260512_073703    — 17894 bytes
blueprints/empresas.py.bak_antes_fix          — 0 bytes (vazio)
blueprints/empresas.py.bak_deploy             — 0 bytes (vazio)
templates/empresas/index.html.bak             — 13214 bytes
templates/empresas/index.html.bak_20260511_202505 — 19234 bytes
templates/empresas/index.html.bak_layout      — 9781 bytes
```

---

## 5. Rotas Registradas

| Método | Rota | Função | Descrição |
|--------|------|---------|-----------|
| GET | `/empresas/` | `index()` | Tela principal — listagem filtrada e paginada |
| POST | `/empresas/sincronizar` | `sincronizar()` | Importa dados da planilha de backup para o banco |
| GET, POST | `/empresas/nova` | `nova()` | Cadastro de nova empresa |
| GET | `/empresas/<int:id>` | `detalhe(empresa_id)` | Detalhe de uma empresa |
| POST | `/empresas/<int:id>/editar` | `editar(empresa_id)` | Edição de empresa |
| POST | `/empresas/gravar-sheets` | `gravar_sheets()` | Exporta banco para planilha de backup |
| GET | `/empresas/exportar-excel` | `exportar_excel()` | Exporta lista filtrada em Excel |
| GET | `/empresas/relatorio-excel` | `relatorio_excel()` | Exporta relatório de controle em Excel |

A função `gravar_planilha()` (linha 616) é chamada internamente por `portal.py` no thread de sincronização periódica — não é uma rota, mas exportada como função.

---

## 6. Tela Principal — Consulta de Empresas (`index.html`)

### Aba padrão
A listagem carrega com a aba **ATIVAS** por padrão (`aba_param` sem valor = aba ATIVAS).

### Filtros disponíveis
- **Busca textual** (`q`): filtra por nome da empresa ou CNPJ
- **Filtro por aba**: ATIVAS / INATIVAS / NÃO MENSAIS (parâmetro `aba`)
- **Filtros avançados dinâmicos** (`CAMPOS_FILTRO`):
  - município, responsável, atuação, escritório
  - procuração, CNES, VISA, TPI, publicidade
  - licença ambiental, alvará de funcionamento
  - bombeiro vencimento, bombeiro protocolo
  - **certificado digital** *(adicionado 2026-05-12)*
- **Filtros de classificação** (`class_*`): aplicados em memória sobre o resultado SQL, via URL params `class_<campo>=<categoria>`. Ativados clicando nos badges do Resumo da Seleção.

### Filtros cumulativos
Múltiplos valores por campo são acumulados via `request.args.getlist()`. Qualquer combinação de filtros é aplicada antes da paginação.

### Chips de filtros ativos
A interface exibe chips visuais para cada filtro ativo, com botão ×. Ao remover um chip, o filtro correspondente é retirado da URL sem recarregar a página (JavaScript no template).

### Variável `tem_filtros`
Controla se o Resumo da Seleção aparece:
```python
tem_filtros = (bool(q) or n_filtros > 0
               or bool(active_class)
               or (aba_param is not None and bool(aba_param.strip())))
```
O resumo só é exibido quando há algum filtro ativo (incluindo filtros class_*).

---

## 7. Paginação

- **Constante:** `PER_PAGE = 150` empresas por página
- **Fluxo:**
  1. `_build_query()` gera o SQL filtrado
  2. `empresas_todas = conn.execute(sql, params).fetchall()` — carrega **todos** os resultados filtrados
  3. `total_filtrado = len(empresas_todas)` — total real para o Resumo e meta-bar
  4. Slice em memória: `empresas = empresas_todas[offset:offset + PER_PAGE]`
  5. Template recebe: `empresas`, `total_filtrado`, `page`, `total_pages`, `per_page`, `base_query`

- **Meta-bar:** "Mostrando **X–Y** de **Z** empresa(s)"
- **Controles:** ‹ Anterior / 1 2 3 … N / Próxima › (ellipsis ± 2 páginas da atual)
- **Links de paginação:** preservam todos os filtros e parâmetros de busca via `base_query`

---

## 8. Resumo da Seleção

Calculado sobre `empresas_todas` (conjunto completo filtrado, não só a página atual).

- **Título:** exibe `{{ total_filtrado }}` — total real, não `{{ empresas|length }}` (slice de página).
- Para cada campo documental (`CAMPOS_DOCUMENTAIS`), conta quantas empresas têm cada classificação.
- A classificação usa `classificar_campo(nome_campo, valor)` — nunca classifica como "Vencido" sem data válida.

### Badges clicáveis (desde 2026-05-12)
Cada badge é um `<button>` que ao ser clicado aplica um filtro `class_<campo>=<categoria>` na URL:
- Badge **não ativo** → clica → `aplicarClassFiltro(campo, cat)` → redireciona com o param na URL
- Badge **ativo** (borda escura) → clica → `removerClassFiltro(campo)` → remove o param da URL
- Apenas um badge ativo por campo (replace, não acumula)
- Chip de filtro ativo também aparece na barra de chips com botão ×

---

## 9. Exportações Excel

### Botão "Exportar lista Excel" — rota `/empresas/exportar-excel`
- Exporta **todos** os resultados filtrados (sem limite de página)
- Recebe os mesmos parâmetros de filtro da URL
- Chama `_build_query()` diretamente — independente da paginação
- Usa `xlsxwriter 3.2.9` (único Excel disponível; `openpyxl` **não** está instalado)
- Visível para todos os usuários autenticados

### Botão "Relatório de controle Excel" — rota `/empresas/relatorio-excel`
- Exporta relatório completo com coloração por status documental
- Usa `xlsxwriter 3.2.9`
- Visível para todos os usuários autenticados
- **Regra de permissão no back-end:** veja seção 10

---

## 10. Regras de Permissão

### Usuário comum (não-admin)
- Pode visualizar a listagem
- Pode exportar lista Excel com qualquer filtro
- **Não pode** gerar Relatório de controle Excel a não ser que:
  - Exatamente 1 responsável selecionado no filtro
  - E esse responsável seja o próprio nome do usuário logado
- Se tentar gerar sem cumprir a regra → mensagem amigável via `flash()`:
  > *"Para gerar o relatório de controle, selecione no filtro Responsável apenas o seu próprio nome."*
  - Implementada com `flash(_MSG_PERMISSAO, 'warning')` + `redirect(url_for('empresas.index'))`
  - Exibida no topo da tela com estilo `.flash-warning` (fundo amarelo claro)

### Master / Admin (`session.is_admin = True`)
- Pode gerar Relatório de controle com qualquer filtro (inclusive geral, sem filtro de responsável)
- Pode usar botões da planilha de backup (Importar / Exportar)
- Sem restrições de conteúdo

### Verificação de permissão (back-end)
A validação ocorre em `relatorio_excel()`:
```python
if not is_admin:
    if len(responsaveis_filtro) != 1:
        flash(_MSG_PERMISSAO, 'warning')
        return redirect(url_for('empresas.index'))
    resp_sel = _normalizar(responsaveis_filtro[0])
    user_norm = _normalizar(user_nome)
    if resp_sel != user_norm:
        flash(_MSG_PERMISSAO, 'warning')
        return redirect(url_for('empresas.index'))
```

---

## 11. Planilha de Backup Google Sheets

A planilha Google Sheets é a **planilha de backup operacional** dos dados das empresas. **Não** é a planilha de controle principal.

### Identificação
- **ID da planilha:** variável `BACKUP_SHEET_ID` no `.env`
- **Constante no código:** `ABA_CONSOLIDADA = 'Consolidada'` (definida em `empresas.py` e em `backup_sheets.py`)

### Aba ativa
- **Aba usada:** `'Consolidada'`
- A aba "Consolidada" é sempre sobrescrita com os dados mais atuais
- Uma segunda aba datada (`YYYY-MM-DD`) é criada/atualizada no mesmo backup
- **Não há referência ativa à aba "Mais Recente"** nos arquivos de código em uso
  - A expressão "mais_recentes" que aparece em `database.py` é um alias de CTE SQL (lógica interna de banco), sem relação com o nome de aba da planilha

### Botões da planilha de backup

| Botão | Rota | Visibilidade |
|-------|------|--------------|
| ↓ Importar planilha | `POST /empresas/sincronizar` | **Somente admin** (`{% if session.is_admin %}`) |
| ↑ Exportar planilha | `POST /empresas/gravar-sheets` | **Somente admin** (`{% if session.is_admin %}`) |

Usuários comuns **não veem** esses botões — controle no template via `{% if session.is_admin %}`.

Ambos os botões exibem aviso de confirmação antes de executar.

---

## 12. Backup Diário Automático às 02:00

- **Arquivo:** `backup_sheets.py` — função `iniciar_backup_diario()`
- **Acionamento:** `portal.py` chama `iniciar_backup_diario()` no startup (linha 889)
- **Mecanismo:** thread daemon Python que calcula segundos até o próximo 02:00 AM local
- **Ação:** executa a mesma lógica do botão "Exportar planilha" — grava dados na aba "Consolidada" + aba datada
- **Log:** registrado em `backup.log` na raiz do projeto

---

## 13. Classificação Documental

A função `classificar_campo(nome_campo, valor)` classifica cada campo documental de cada empresa:

| Classificação | Critério |
|---------------|----------|
| **OK** | Documento válido (contém "OK", "VIGENTE", "REGULAR", "VÁLIDO", "VALIDO") |
| **A vencer** | Data futura dentro de 90 dias |
| **Vencido** | Data passada (somente com data válida) |
| **Pendente** | Campo não vazio, mas não se enquadra nos anteriores |
| **Não se aplica** | Campo vazio ou "N/A" |

Campos documentais analisados (`CAMPOS_DOCUMENTAIS`):
`alvara_funcionamento`, `visa`, `cnes`, `licenca_ambiental`, `tpi`, `publicidade`, `venc_bombeiro`, `prot_bombeiro`, `procuracao`, **`certificado_digital`** *(adicionado 2026-05-12)*

### Palavra-chave "Em emissão" → "Em andamento" (desde 2026-05-12)
`'EMISS'` foi adicionado ao bloco de palavras-chave da categoria "Em andamento":
```python
if any(k in vl for k in ('ANDAMENTO', 'AGUARDANDO', 'PROTOCOLO', 'EMISS')):
    return 'Em andamento'
```
Cobre variantes: "Em emissão", "Em Emissao", "EMISSÃO", etc.

Campo `responsavel` está em `SEM_CONTADOR` — não aparece nos contadores do Resumo da Seleção (privacidade da equipe).

---

## 14. Dependências Principais

| Pacote | Versão | Uso |
|--------|--------|-----|
| Flask | 3.1.3 | Framework web |
| Flask-Session | 0.8.0 | Sessões do servidor |
| Werkzeug | 3.1.7 | WSGI / segurança |
| xlsxwriter | 3.2.9 | Geração de Excel |
| python-dotenv | 1.2.1 | Variáveis de ambiente |
| python-docx | 1.2.0 | Geração de documentos Word |
| anthropic | 0.86.0 | Claude API (módulo Conferência) |
| openai | 2.36.0 | OpenAI API |
| webauthn | 2.7.1 | Passkeys / autenticação |

**`openpyxl` não está instalado.** Qualquer código que tente importar `openpyxl` vai falhar. Usar exclusivamente `xlsxwriter`.

---

## 15. Cuidados Futuros

1. **Nunca usar `openpyxl`** — não está instalado e não há previsão de instalação.
2. **Nunca referenciar a aba "Mais Recente"** em código novo — a aba ativa é `'Consolidada'`.
3. **Não exibir botões de planilha para usuários comuns** — controle em `{% if session.is_admin %}`.
4. **Manter `ABA_CONSOLIDADA`** sincronizado entre `empresas.py` e `backup_sheets.py` — ambos devem usar `'Consolidada'`.
5. **Exportações Excel ignoram paginação** — `_build_query()` é chamado diretamente; não limitar pelos parâmetros de página.
6. **Mensagem de permissão** — usar `flash()` + redirect, nunca retornar JSON 403 para erros de permissão visíveis ao usuário.
7. **Deploy** — usar método chunks SSH de 800 bytes (SCP e SFTP travam nesta VPS); script Python local `subprocess.run` por chunk.
8. **Reiniciar serviço** — `systemctl --user restart portal-sigma`.

---

## 16. Arquivos que Não Devem ser Alterados Sem Autorização

| Arquivo | Motivo |
|---------|--------|
| `backup_sheets.py` | Sincronização com planilha de backup — alteração pode corromper dados |
| `.env` | Credenciais e configuração de produção |
| `credentials/token.json` | Token OAuth Google — regenerar exige fluxo manual |
| `database.py` | Estrutura do banco SQLite — alteração pode causar perda de dados |
| `portal.py` (linhas 889-893) | Startup do portal e backup diário — não alterar sem entender dependências |

---

## 17. Histórico Resumido das Últimas Mudanças Relevantes

| Data | Mudança |
|------|---------|
| 2026-04-13 | Criação inicial do módulo Empresas no portal |
| 2026-05-11 | Correção de 4 bugs críticos: token path no `.env`, clear de células, DELETE antes de validar, import sem transação |
| 2026-05-11 | Renomeação interna "Mais Recente" → "Consolidada" (constante `ABA_CONSOLIDADA`) |
| 2026-05-12 | Restauração dos arquivos 0 bytes pós-deploy com falha |
| 2026-05-12 | Ajuste 1: mensagem amigável via `flash()` para não-admin sem filtro correto |
| 2026-05-12 | Ajuste 2: paginação de 150 empresas por página com resumo sobre total filtrado |
| 2026-05-12 (v2) | Novo campo `certificado_digital` (texto livre) em DB, forms, filtro, Resumo, Excel, Sheets (col X) |
| 2026-05-12 (v2) | Renomeado bloco "Procuração e Situação" → "Representação da Empresa" em detalhe e nova empresa |
| 2026-05-12 (v2) | `classificar_campo`: adicionado `'EMISS'` em "Em andamento" — cobre "Em emissão" |
| 2026-05-12 (v2) | Badges do Resumo da Seleção tornados clicáveis (filter class_* em memória + active state CSS) |
| 2026-05-12 (v2) | Fix: título do Resumo usava `{{ empresas\|length }}` (página) → `{{ total_filtrado }}` (total real) |
| 2026-05-12 (v3) | Planilha backup: aba "Consolidada" atualizada para 24 colunas com "Certificado Digital" na coluna X; aba "2026-05-12v2" criada com mesma estrutura; aba "2026-05-12" original preservada |
| 2026-05-12 (v3) | `nova.html`: Procuração alterada de `<select>` para `<input type="text">` — texto livre, placeholder "Ex.: Assinada cartório", dica corrigida |
| 2026-05-12 (v3) | `nova.html` e `detalhe.html`: link "Consultar padrão de preenchimento" movido para o início do formulário (antes das seções), removido de "Documentos e Licenças" |
| 2026-05-12 (v3) | `nova.html` e `detalhe.html`: todos os ícones de informação corrigidos — `<svg title="">` substituído por `<span title=""><svg>` para exibição confiável de tooltip no Chrome |
| 2026-05-12 (v3) | `detalhe.html`: Observações — placeholder atualizado para "Ex.: particularidades da empresa, imóvel, contatos ou orientações importantes." e ícone de dica adicionado ao título da seção |
