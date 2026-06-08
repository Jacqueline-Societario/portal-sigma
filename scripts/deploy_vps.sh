#!/bin/bash
# =============================================================================
# deploy_vps.sh — Script seguro de deploy para o portal-sigma
# Sigma Contabilidade | Portal Societário
# =============================================================================
# Uso:
#   ./deploy_vps.sh <caminho/relativo/do/arquivo>   # deploy real
#   ./deploy_vps.sh --dry-run <caminho/relativo>    # simula sem executar nada
#
# Exemplos:
#   ./deploy_vps.sh blueprints/auth.py
#   ./deploy_vps.sh templates/base.html
#   ./deploy_vps.sh --dry-run blueprints/manuais.py
# =============================================================================
#
# ATENÇÃO — LEIA ANTES DE EXECUTAR:
#
#   1. Este script é específico para execução na VPS de produção.
#      Ele não deve ser executado no WSL local nem em qualquer outro ambiente.
#
#   2. O path fixo abaixo é o caminho real do projeto na VPS:
#        PROJETO="/home/jacqueline-benedito/projetos/portal-sigma"
#      Se o ambiente mudar (nova VPS, novo usuário, novo caminho), ajuste
#      essa variável antes de usar o script.
#
#   3. Este script reinicia o serviço portal-sigma.service após o deploy.
#      Não execute sem ter:
#        - Backup local do arquivo que será substituído
#        - Confirmação de que a VPS está acessível e o serviço está ativo
#        - Autorização explícita para o deploy (ver CHECKLIST_DEPLOY.md)
#        - Plano de rollback pronto
#
#   4. Para simular sem executar nada, use a flag --dry-run.
#
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# VARIÁVEIS
# -----------------------------------------------------------------------------
PROJETO="/home/jacqueline-benedito/projetos/portal-sigma"
SERVICO="portal-sigma.service"
BACKUP_DIR="${PROJETO}/backups/deploy"
LOG_FILE="${PROJETO}/logs/deploy.log"
DRY_RUN=false
ARQUIVO_RELATIVO=""

# -----------------------------------------------------------------------------
# CORES
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # sem cor

# -----------------------------------------------------------------------------
# FUNÇÕES
# -----------------------------------------------------------------------------
log() {
    local nivel="$1"
    local mensagem="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$nivel" in
        INFO)  echo -e "${BLUE}[INFO]${NC}  ${mensagem}" ;;
        OK)    echo -e "${GREEN}[OK]${NC}    ${mensagem}" ;;
        WARN)  echo -e "${YELLOW}[AVISO]${NC} ${mensagem}" ;;
        ERROR) echo -e "${RED}[ERRO]${NC}  ${mensagem}" ;;
    esac

    # Gravar em log apenas fora do dry-run
    if [ "$DRY_RUN" = false ]; then
        echo "[${timestamp}] [${nivel}] ${mensagem}" >> "${LOG_FILE}" 2>/dev/null || true
    fi
}

dry_log() {
    echo -e "${YELLOW}[DRY-RUN]${NC} $1"
}

separador() {
    echo "──────────────────────────────────────────────────────────────────"
}

usage() {
    echo ""
    echo "Uso: $0 [--dry-run] <caminho/relativo/do/arquivo>"
    echo ""
    echo "  --dry-run   Simula o deploy sem alterar arquivos, sem criar backup"
    echo "              e sem reiniciar o serviço."
    echo ""
    echo "Exemplos:"
    echo "  $0 blueprints/auth.py"
    echo "  $0 templates/base.html"
    echo "  $0 --dry-run blueprints/manuais.py"
    echo ""
    exit 1
}

# -----------------------------------------------------------------------------
# PARSEAR ARGUMENTOS
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    log ERROR "Nenhum argumento informado."
    usage
fi

if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    shift
fi

if [ $# -eq 0 ]; then
    log ERROR "Caminho relativo do arquivo não informado."
    usage
fi

ARQUIVO_RELATIVO="$1"

# -----------------------------------------------------------------------------
# VALIDAÇÃO 1: executar dentro do projeto correto
# -----------------------------------------------------------------------------
separador
log INFO "Validando ambiente..."

DIRETORIO_ATUAL="$(cd "$(dirname "$0")" && pwd)"
if [ "${DIRETORIO_ATUAL}" != "${PROJETO}" ]; then
    log ERROR "Este script deve ser executado a partir de ${PROJETO}"
    log ERROR "Diretório atual detectado: ${DIRETORIO_ATUAL}"
    exit 1
fi

# -----------------------------------------------------------------------------
# VALIDAÇÃO 2: caminho não pode ser absoluto
# -----------------------------------------------------------------------------
if [[ "${ARQUIVO_RELATIVO}" = /* ]]; then
    log ERROR "Caminhos absolutos não são permitidos."
    log ERROR "Informe apenas o caminho relativo dentro do projeto."
    exit 1
fi

# -----------------------------------------------------------------------------
# VALIDAÇÃO 3: caminhos perigosos bloqueados
# -----------------------------------------------------------------------------
BLOQUEADOS=(
    ".."
    ".env"
    "credentials/"
    "portal.db"
    "logs/"
    "backups/"
    "uploads/"
    ".venv/"
    ".git/"
    ".pyc"
    ".b64"
)

for padrao in "${BLOQUEADOS[@]}"; do
    if [[ "${ARQUIVO_RELATIVO}" == *"${padrao}"* ]]; then
        log ERROR "Arquivo ou caminho bloqueado: '${padrao}' detectado em '${ARQUIVO_RELATIVO}'"
        log ERROR "Este script não permite deploy de arquivos sensíveis ou perigosos."
        exit 1
    fi
done

# -----------------------------------------------------------------------------
# VALIDAÇÃO 4: arquivo existe no projeto
# -----------------------------------------------------------------------------
ARQUIVO_ABSOLUTO="${PROJETO}/${ARQUIVO_RELATIVO}"

if [ ! -f "${ARQUIVO_ABSOLUTO}" ]; then
    log ERROR "Arquivo não encontrado: ${ARQUIVO_ABSOLUTO}"
    log ERROR "Verifique o caminho relativo informado."
    exit 1
fi

# -----------------------------------------------------------------------------
# VALIDAÇÃO 5: estado do Git
# -----------------------------------------------------------------------------
log INFO "Verificando estado do Git..."

cd "${PROJETO}"

GIT_STATUS=$(git status --short 2>/dev/null || echo "GIT_INDISPONIVEL")

if [ "${GIT_STATUS}" = "GIT_INDISPONIVEL" ]; then
    log WARN "Git não disponível ou repositório não inicializado. Continuando sem controle de versão."
else
    ALTERACOES_STAGED=$(git diff --cached --name-only 2>/dev/null || true)
    if [ -n "${ALTERACOES_STAGED}" ]; then
        log WARN "Há alterações em staged não commitadas:"
        echo "${ALTERACOES_STAGED}"
        log WARN "Recomenda-se commitar antes de fazer deploy."
    fi

    COMMIT_ATUAL=$(git log --oneline -1 2>/dev/null || echo "sem commits")
    log INFO "Commit de referência: ${COMMIT_ATUAL}"
fi

# -----------------------------------------------------------------------------
# MODO DRY-RUN
# -----------------------------------------------------------------------------
if [ "$DRY_RUN" = true ]; then
    separador
    dry_log "MODO DRY-RUN — nada será alterado, nenhum backup será criado, serviço não será reiniciado."
    separador
    dry_log "Arquivo alvo:     ${ARQUIVO_RELATIVO}"
    dry_log "Caminho completo: ${ARQUIVO_ABSOLUTO}"
    dry_log "Backup seria criado em: ${BACKUP_DIR}/"
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    NOME_BASE=$(basename "${ARQUIVO_RELATIVO}")
    NOME_BACKUP="${NOME_BASE}.bak_deploy_${TIMESTAMP}"
    dry_log "Nome do backup: ${NOME_BACKUP}"
    dry_log "Log de deploy seria gravado em: ${LOG_FILE}"
    dry_log "Serviço que seria reiniciado: ${SERVICO}"
    dry_log "Verificação pós-restart: systemctl --user is-active ${SERVICO}"
    separador
    dry_log "DRY-RUN concluído. Nenhuma alteração foi feita."
    exit 0
fi

# -----------------------------------------------------------------------------
# MODO REAL — A PARTIR DAQUI, AÇÕES REAIS
# -----------------------------------------------------------------------------
separador
log INFO "Iniciando deploy de: ${ARQUIVO_RELATIVO}"

# Garantir que as pastas de backup e log existam
mkdir -p "${BACKUP_DIR}"
mkdir -p "$(dirname "${LOG_FILE}")"

# -----------------------------------------------------------------------------
# PASSO 1: BACKUP com timestamp
# -----------------------------------------------------------------------------
log INFO "Criando backup do arquivo atual..."

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
NOME_BASE=$(basename "${ARQUIVO_RELATIVO}")
NOME_BACKUP="${NOME_BASE}.bak_deploy_${TIMESTAMP}"
ARQUIVO_BACKUP="${BACKUP_DIR}/${NOME_BACKUP}"

cp "${ARQUIVO_ABSOLUTO}" "${ARQUIVO_BACKUP}"

if [ -f "${ARQUIVO_BACKUP}" ]; then
    log OK "Backup criado: backups/deploy/${NOME_BACKUP}"
else
    log ERROR "Falha ao criar backup. Deploy abortado por segurança."
    exit 1
fi

# -----------------------------------------------------------------------------
# PASSO 2: REGISTRO EM LOG
# -----------------------------------------------------------------------------
log INFO "Registrando deploy no log..."
echo "[${TIMESTAMP}] DEPLOY | arquivo=${ARQUIVO_RELATIVO} | backup=${ARQUIVO_BACKUP} | commit=$(git log --oneline -1 2>/dev/null || echo 'n/a')" >> "${LOG_FILE}"
log OK "Deploy registrado em logs/deploy.log"

# -----------------------------------------------------------------------------
# PASSO 3: RESTART DO SERVIÇO
# -----------------------------------------------------------------------------
log INFO "Reiniciando o serviço: ${SERVICO}..."
systemctl --user restart "${SERVICO}"

sleep 2

# -----------------------------------------------------------------------------
# PASSO 4: VERIFICAÇÃO PÓS-RESTART
# -----------------------------------------------------------------------------
log INFO "Verificando serviço após restart..."

STATUS=$(systemctl --user is-active "${SERVICO}" 2>/dev/null || echo "failed")

if [ "${STATUS}" = "active" ]; then
    log OK "Serviço ${SERVICO} está ativo (active)."
    log OK "Deploy de '${ARQUIVO_RELATIVO}' concluído com sucesso."
else
    log ERROR "Serviço ${SERVICO} não voltou ativo. Status: ${STATUS}"
    separador
    log WARN "AÇÃO RECOMENDADA — Rollback manual:"
    log WARN "  cp '${ARQUIVO_BACKUP}' '${ARQUIVO_ABSOLUTO}'"
    log WARN "  systemctl --user restart ${SERVICO}"
    log WARN "  systemctl --user is-active ${SERVICO}"
    separador
    echo "[${TIMESTAMP}] FALHA_POS_RESTART | arquivo=${ARQUIVO_RELATIVO} | backup=${ARQUIVO_BACKUP}" >> "${LOG_FILE}"
    exit 1
fi

# -----------------------------------------------------------------------------
# ROLLBACK MANUAL (informativo)
# -----------------------------------------------------------------------------
separador
log INFO "Se precisar reverter este deploy manualmente:"
echo ""
echo "  cp '${ARQUIVO_BACKUP}' '${ARQUIVO_ABSOLUTO}'"
echo "  systemctl --user restart ${SERVICO}"
echo "  systemctl --user is-active ${SERVICO}"
echo ""
separador

exit 0
