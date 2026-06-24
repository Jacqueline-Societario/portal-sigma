# Sessão: Planejamento Painel de Avisos
**Data**: 24/06/2026 | **Cliente**: Sigma Contabilidade | **Status**: PARCIAL (planejamento concluído — implementação pendente)

## Resumo
Sessão dedicada ao planejamento e design do novo módulo Painel de Avisos para o Portal Societário. Foram lidos todos os arquivos-chave do portal (database.py, portal.py, base.html, blueprints), consolidado o plano, refinadas as regras de negócio e produzido um mapeamento cirúrgico completo com pontos exatos de inserção em cada arquivo.

## O que foi feito
- Identificado e corrigido erro de localização do mockup (estava em `centro-comando/docs/`, movido para `portal-sigma/docs/`)
- Leitura completa de `database.py` (1664 linhas), `portal.py` (600+ linhas), `templates/base.html` (575 linhas)
- Consolidação do plano em `docs/PLANO_PAINEL_AVISOS.md`
- Refinamento das regras de negócio:
  - Avisos integrados ao sino existente (não badge separado)
  - Botão "+" visível apenas para usuários com módulo `avisos` habilitado
  - Card flutuante: apenas X (fecha sem marcar) e Entendi (fecha + marca como lido)
  - Botão "Fechar" removido (redundante)
- Mapeamento cirúrgico produzido em `docs/MAPEAMENTO_IMPACTO_PAINEL_AVISOS.md`:
  - 4 pontos de inserção em `database.py` (linhas 297, 482, 614, 1664)
  - 6 pontos em `portal.py` (linhas 65, 232, 281, 392, 474)
  - 3 pontos em `base.html` (após linha 308, linha 394, após linha 564)
  - 2 arquivos novos: `blueprints/avisos.py` + `templates/avisos/index.html`

## Arquivos criados/modificados
- `docs/PLANO_PAINEL_AVISOS.md` — plano consolidado com regras de negócio
- `docs/MAPEAMENTO_IMPACTO_PAINEL_AVISOS.md` — mapeamento cirúrgico de todos os pontos de inserção
- `docs/mockup_painel_avisos.html` — movido de centro-comando (não alterado nesta sessão)
- `PROJETO_STATUS.md` — atualizado com módulo Painel de Avisos e tarefa pendente

## O que funcionou
- Análise completa dos arquivos sem necessidade de acessar a VPS (código disponível localmente)
- `criar_notificacoes_para_evento()` (linha 1078 do database.py) já faz fan-out para todos os usuários — reutilizável diretamente pelo `criar_aviso()`
- `get_user_permission()` retorna True por padrão — sem registro = acesso liberado — todos recebem notificações automaticamente
- `inject_modules_config()` já injeta `modules_config` em todos os templates — visibilidade do botão "+" controlada por aqui

## Atenção
- O arquivo local WSL pode estar desatualizado em relação à VPS — verificar diffs antes de aplicar no deploy
- `add_coluna_se_necessario()` é obrigatório para bancos já existentes na VPS (tabelas novas não criadas via `init_db()` sozinho)
- `_SKIP_STEPUP` precisa incluir `/api/avisos` — sem isso o step-up Passkey bloqueia o card flutuante

## Próximos Passos
- [ ] Iniciar implementação na ordem: database.py → blueprints/avisos.py → templates/avisos/ → portal.py → base.html
- [ ] Verificar estado atual dos arquivos na VPS antes de aplicar (pode haver divergência com WSL)
- [ ] Após implementação: deploy + teste do card flutuante + teste do sino + teste do painel admin
