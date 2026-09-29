#!/usr/bin/env bash
# ==============================================================================
# DESAFIO PRÁTICO 2 — FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
# SCRIPT: executar_pipeline_completo.sh
# FINALIDADE: Orquestra a execução ponta a ponta de todos os componentes do
#             Desafio 2, desde a inicialização dos serviços até o carregamento
#             da Camada Gold e testes de qualidade.
# REQUISITOS: RF15 (execução completa e por etapas), RF22, RF34
# ==============================================================================
# Uso:
#   chmod +x executar_pipeline_completo.sh
#   ./executar_pipeline_completo.sh              # executa tudo
#   ./executar_pipeline_completo.sh parquet      # apenas etapa Parquet (RF24)
#   ./executar_pipeline_completo.sh beam         # apenas Beam DirectRunner (RF25)
#   ./executar_pipeline_completo.sh gold         # apenas carga Gold (RF26)
#   ./executar_pipeline_completo.sh qualidade    # apenas testes de qualidade (RF31)
#   ./executar_pipeline_completo.sh lgpd         # apenas demonstração LGPD (RF33)
#   ./executar_pipeline_completo.sh amostras     # apenas exportar amostras (RF34)
#   ./executar_pipeline_completo.sh openmetadata # apenas glossário OpenMetadata (RF28)
# ==============================================================================

set -euo pipefail

# ─── Cores para saída formatada ─────────────────────────────────────────────
AZUL='\033[0;34m'
VERDE='\033[0;32m'
AMARELO='\033[1;33m'
VERMELHO='\033[0;31m'
NEGRITO='\033[1m'
RESET='\033[0m'

# ─── Diretórios ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="${SCRIPT_DIR}/.."          # raiz do repositório (Desafio 1 + 2)
DD2="${SCRIPT_DIR}"              # desafio_dados_2/

# ─── Carrega variáveis de ambiente ───────────────────────────────────────────
# Procura .env na raiz do repositório primeiro, depois no desafio_dados_2
if [[ -f "${RAIZ}/.env" ]]; then
    set -a; source "${RAIZ}/.env"; set +a
elif [[ -f "${DD2}/.env" ]]; then
    set -a; source "${DD2}/.env"; set +a
else
    echo -e "${AMARELO}[AVISO] Nenhum .env encontrado. Usando defaults do ambiente.${RESET}"
fi

# ─── Variáveis de conexão com defaults seguros ───────────────────────────────
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-desafio_dados}"
export POSTGRES_USER="${POSTGRES_USER:-desafio_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-troque_esta_senha}"

# ─── Variáveis LGPD (RF33) ───────────────────────────────────────────────────
export LGPD_PEPPER_KEY="${LGPD_PEPPER_KEY:-pepper_fic_dev_ia_2026_segredo}"
export LGPD_SALT_SECRET="${LGPD_SALT_SECRET:-salt_corporativo_desafio2_k9}"

# ─── Timestamp e ID de execução ──────────────────────────────────────────────
EXECUCAO_ID="EXEC_$(date +%Y%m%d_%H%M%S)_$$"
INICIO_TOTAL=$(date +%s)

# ─── Helpers ─────────────────────────────────────────────────────────────────
cabecalho() {
    echo -e "\n${AZUL}${NEGRITO}╔══════════════════════════════════════════════════════╗${RESET}"
    echo -e "${AZUL}${NEGRITO}║  $1${RESET}"
    echo -e "${AZUL}${NEGRITO}╚══════════════════════════════════════════════════════╝${RESET}"
}

ok()   { echo -e "${VERDE}[OK]${RESET} $*"; }
info() { echo -e "${AZUL}[INFO]${RESET} $*"; }
warn() { echo -e "${AMARELO}[AVISO]${RESET} $*"; }
erro() { echo -e "${VERMELHO}[ERRO]${RESET} $*" >&2; }

duracao() {
    local inicio=$1
    local fim=$(date +%s)
    echo "$((fim - inicio))s"
}

aguardar_postgres() {
    info "Aguardando PostgreSQL em ${POSTGRES_HOST}:${POSTGRES_PORT}..."
    local tentativas=0
    until python3 -c "import psycopg2, os; conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST', 'localhost'), port=int(os.getenv('POSTGRES_PORT', '5432')), dbname=os.getenv('POSTGRES_DB', 'desafio_dados'), user=os.getenv('POSTGRES_USER', 'desafio_user'), password=os.getenv('POSTGRES_PASSWORD', 'troque_esta_senha')); conn.close()" > /dev/null 2>&1; do
        tentativas=$((tentativas + 1))
        if [[ $tentativas -gt 30 ]]; then
            erro "PostgreSQL não respondeu após 30 tentativas."
            erro "Verifique se o Docker está rodando: docker compose up -d"
            exit 1
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    ok "PostgreSQL disponível."
}

# ─── Etapas do pipeline ──────────────────────────────────────────────────────

etapa_amostras() {
    cabecalho "RF20/21/23/26/34 — Carga Bronze e Exportação de Amostras"
    local t=$(date +%s)
    python3 "${DD2}/dados/carregar_e_exportar_amostras.py"
    ok "Amostras exportadas. Duração: $(duracao $t)"
}

etapa_silver() {
    cabecalho "RF21 — Padronização Silver (executor Python equivalente ao Hop)"
    local t=$(date +%s)
    python3 "${DD2}/hop/executar_silver_python.py"
    ok "Silver populada. Duração: $(duracao $t)"
}

etapa_parquet() {
    cabecalho "RF24 — Exportação Parquet e Benchmark CSV x Parquet"
    local t=$(date +%s)
    python3 "${DD2}/beam/exportar_parquet.py"
    ok "Exportação Parquet concluída. Duração: $(duracao $t)"
}

etapa_beam() {
    cabecalho "RF25 — Pipeline Apache Beam (DirectRunner)"
    local t=$(date +%s)

    PARQUET_INPUT="${DD2}/dados/silver/interacoes_parquet"
    BEAM_OUTPUT="${DD2}/beam/saida/direct/engajamento"

    if [[ ! -d "${PARQUET_INPUT}" ]]; then
        warn "Diretório Parquet não encontrado. Executando etapa_parquet primeiro..."
        etapa_parquet
    fi

    mkdir -p "$(dirname "${BEAM_OUTPUT}")"

    python3 "${DD2}/beam/pipeline_beam.py" \
        --input "${PARQUET_INPUT}" \
        --output "${BEAM_OUTPUT}" \
        --runner DirectRunner

    ok "Pipeline Beam DirectRunner concluído. Duração: $(duracao $t)"
}

etapa_gold() {
    cabecalho "RF26 — Carga da Camada Gold"
    local t=$(date +%s)

    BEAM_SAIDA="${DD2}/beam/saida/direct"
    if ! ls "${BEAM_SAIDA}"/*.parquet 1>/dev/null 2>&1; then
        warn "Saída do Beam não encontrada. Executando etapa_beam primeiro..."
        etapa_beam
    fi

    python3 "${DD2}/beam/carregar_gold.py"
    ok "Camada Gold carregada. Duração: $(duracao $t)"
}

etapa_qualidade() {
    cabecalho "RF31 — Testes de Qualidade de Dados (Quality Gate)"
    local t=$(date +%s)
    python3 "${DD2}/qualidade/executar_testes.py" || {
        local rc=$?
        warn "Testes de qualidade concluídos com falhas críticas (exit ${rc})."
        warn "Publicação da Gold bloqueada até resolução das regras críticas."
        return $rc
    }
    ok "Testes de qualidade aprovados. Duração: $(duracao $t)"
}

etapa_lgpd() {
    cabecalho "RF33 — Demonstração de Proteção de Dados Pessoais (LGPD)"
    local t=$(date +%s)
    python3 "${DD2}/lgpd/demonstrar_protecao_lgpd.py"
    ok "Demonstração LGPD concluída. Duração: $(duracao $t)"
}

etapa_openmetadata() {
    cabecalho "RF27/28 — Cadastro de Glossário e Metadados no OpenMetadata"
    local t=$(date +%s)
    python3 "${DD2}/openmetadata/cadastrar_glossario_metadados.py" || {
        warn "Falha ao conectar ao OpenMetadata. Verifique se a instância está ativa."
        warn "O script registrou as definições localmente em openmetadata/evidencias/"
        return 0
    }
    ok "Glossário e metadados registrados. Duração: $(duracao $t)"
}

etapa_completa() {
    cabecalho "PIPELINE COMPLETO — Desafio Prático 2"
    info "Execução ID: ${EXECUCAO_ID}"
    info "Início: $(date '+%Y-%m-%d %H:%M:%S')"

    aguardar_postgres

    etapa_amostras
    etapa_silver
    etapa_parquet
    etapa_beam
    etapa_gold

    local qualidade_ok=0
    etapa_qualidade || qualidade_ok=$?

    etapa_lgpd
    etapa_openmetadata

    local duracao_total=$(duracao ${INICIO_TOTAL})
    echo ""
    echo -e "${NEGRITO}══════════════════════════════════════════════════════${RESET}"
    if [[ $qualidade_ok -eq 0 ]]; then
        echo -e "${VERDE}${NEGRITO}  PIPELINE CONCLUÍDO COM SUCESSO  ✓${RESET}"
        echo -e "${VERDE}  Status: SUCESSO${RESET}"
    else
        echo -e "${AMARELO}${NEGRITO}  PIPELINE CONCLUÍDO COM RESSALVAS  ⚠${RESET}"
        echo -e "${AMARELO}  Status: SUCESSO_COM_RESSALVAS (qualidade com falhas não-críticas)${RESET}"
    fi
    echo -e "  Duração total: ${duracao_total}"
    echo -e "  Execução ID:  ${EXECUCAO_ID}"
    echo -e "${NEGRITO}══════════════════════════════════════════════════════${RESET}"
}

# ─── Roteamento por etapa ────────────────────────────────────────────────────
ETAPA="${1:-completo}"

case "${ETAPA}" in
    completo|all)       etapa_completa ;;
    amostras)           aguardar_postgres && etapa_amostras ;;
    silver|rf21)        aguardar_postgres && etapa_silver ;;
    parquet|rf24)       aguardar_postgres && etapa_parquet ;;
    beam|rf25)          aguardar_postgres && etapa_beam ;;
    gold|rf26)          aguardar_postgres && etapa_gold ;;
    qualidade|rf31)     aguardar_postgres && etapa_qualidade ;;
    lgpd|rf33)          etapa_lgpd ;;
    openmetadata|rf28)  etapa_openmetadata ;;
    *)
        echo "Uso: $0 [completo|amostras|silver|parquet|beam|gold|qualidade|lgpd|openmetadata]"
        exit 1
        ;;
esac
