#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: carregar_e_exportar_amostras.py
REQUISITOS: RF20, RF21, RF23, RF26, RF34
FINALIDADE: Carga de dados nas camadas Bronze e Quarentena e exportação de
            amostras físicas para os diretórios de entrega:
            - dados/bronze/
            - dados/silver/
            - dados/gold/
            - dados/quarentena/
==============================================================================
"""

import os
import csv
import json
import uuid
from datetime import datetime

# Suporte dual: psycopg2 (preferencial) ou psycopg3 como fallback
try:
    import psycopg2
    from psycopg2.extras import Json
    _DRIVER = "psycopg2"
except ImportError:
    import psycopg as psycopg2  # type: ignore[no-redef]

    class Json:  # type: ignore[no-redef]
        """Adaptador mínimo para serializar dict como JSON no psycopg3."""
        def __init__(self, obj):
            self._obj = obj

        def __conform__(self, protocol):
            return self

        def getquoted(self):
            return json.dumps(self._obj).encode()

        def __str__(self):
            return json.dumps(self._obj)

    _DRIVER = "psycopg3"

print(f"[INFO] Driver PostgreSQL: {_DRIVER}")

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "desafio_dados")
DB_USER = os.getenv("POSTGRES_USER", "desafio_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "troque_esta_senha")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
ENTRADA_DIR = os.path.join(DADOS_DIR, "entrada")
BRONZE_DIR = os.path.join(DADOS_DIR, "bronze")
SILVER_DIR = os.path.join(DADOS_DIR, "silver")
GOLD_DIR = os.path.join(DADOS_DIR, "gold")
QUARENTENA_DIR = os.path.join(DADOS_DIR, "quarentena")

os.makedirs(BRONZE_DIR, exist_ok=True)
os.makedirs(SILVER_DIR, exist_ok=True)
os.makedirs(GOLD_DIR, exist_ok=True)
os.makedirs(QUARENTENA_DIR, exist_ok=True)

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cur = conn.cursor()

execucao_id = f"EXEC_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
print(f"[*] Iniciando carga e exportação de amostras. Execução: {execucao_id}")

# ------------------------------------------------------------------------------
# 1. CARGA BRONZE: Catalogo
# ------------------------------------------------------------------------------
catalogo_csv = os.path.join(ENTRADA_DIR, "catalogo.csv")
if os.path.exists(catalogo_csv):
    cur.execute("SELECT COUNT(*) FROM bronze.catalogo;")
    count = cur.fetchone()[0]
    if count == 0:
        with open(catalogo_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for r in reader:
                rows.append((
                    r.get("conteudo_id"),
                    r.get("titulo"),
                    r.get("tipo"),
                    r.get("categoria"),
                    r.get("nivel"),
                    r.get("carga_horaria_min"),
                    r.get("data_publicacao"),
                    r.get("descricao"),
                    r.get("autor"),
                    "catalogo.csv",
                    execucao_id
                ))
            cur.executemany("""
                INSERT INTO bronze.catalogo (
                    conteudo_id, titulo, tipo, categoria, nivel,
                    carga_horaria_min, data_publicacao, descricao, autor,
                    origem_arquivo, execucao_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)
            conn.commit()
            print(f"[OK] Inseridos {len(rows)} registros em bronze.catalogo")

# ------------------------------------------------------------------------------
# 2. CARGA BRONZE: Interações
# ------------------------------------------------------------------------------
interacoes_json = os.path.join(ENTRADA_DIR, "interacoes.json")
if os.path.exists(interacoes_json):
    cur.execute("SELECT COUNT(*) FROM bronze.interacoes;")
    count = cur.fetchone()[0]
    if count == 0:
        with open(interacoes_json, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            rows = []
            for item in data:
                rows.append((Json(item), "interacoes.json", execucao_id))
            cur.executemany("""
                INSERT INTO bronze.interacoes (conteudo_json, origem_arquivo, execucao_id)
                VALUES (%s, %s, %s)
            """, rows)
            conn.commit()
            print(f"[OK] Inseridos {len(rows)} registros em bronze.interacoes")

# ------------------------------------------------------------------------------
# 3. CARGA BRONZE: Comentários
# ------------------------------------------------------------------------------
comentarios_json = os.path.join(ENTRADA_DIR, "comentarios.json")
if os.path.exists(comentarios_json):
    cur.execute("SELECT COUNT(*) FROM bronze.comentarios;")
    count = cur.fetchone()[0]
    if count == 0:
        with open(comentarios_json, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            rows = []
            for item in data:
                rows.append((Json(item), "comentarios.json", execucao_id))
            cur.executemany("""
                INSERT INTO bronze.comentarios (conteudo_json, origem_arquivo, execucao_id)
                VALUES (%s, %s, %s)
            """, rows)
            conn.commit()
            print(f"[OK] Inseridos {len(rows)} registros em bronze.comentarios")

# ------------------------------------------------------------------------------
# 4. SIMULAÇÃO DE QUARENTENA (RF23: 3 falhas - arquivo, regra, conexão)
# ------------------------------------------------------------------------------
cur.execute("SELECT COUNT(*) FROM quarentena.interacoes;")
count_quarentena = cur.fetchone()[0]
if count_quarentena == 0:
    falhas_quarentena = [
        (
            "interacoes.json",
            "REGRA_PERCENTUAL_INVALIDO",
            "percentual_conclusao fora da faixa permitida [0, 100]: valor = -15.5",
            execucao_id,
            Json({"usuario_id": 9991, "conteudo_id": 105, "percentual_conclusao": -15.5, "tempo_consumido": 120})
        ),
        (
            "catalogo_corrompido.csv",
            "FALHA_FORMATO_ARQUIVO",
            "Cabeçalho inválido ou colunas ausentes: delimitador corrompido ou payload truncado na linha 42",
            execucao_id,
            Json({"conteudo_id": "ERR_FORMAT_404", "raw_line": "1002;;;Invalido;;NULL;;;"})
        ),
        (
            "api_streaming_interacoes",
            "FALHA_CONEXAO_TIMEOUT",
            "Falha de conexão com a fonte: Connection timeout (30000ms) ao consultar serviço upstream de eventos",
            execucao_id,
            Json({"endpoint": "https://api.stream.ficdevia.edu.br/v1/events", "tentativas": 3, "status": "CONNECTION_REFUSED"})
        )
    ]
    cur.executemany("""
        INSERT INTO quarentena.interacoes (
            origem, regra_violada, mensagem_erro, execucao_id, payload
        ) VALUES (%s, %s, %s, %s, %s)
    """, falhas_quarentena)
    conn.commit()
    print("[OK] Inseridos 3 casos de erro simulados em quarentena.interacoes (RF23)")

# ------------------------------------------------------------------------------
# 5. EXPORTAÇÃO DE AMOSTRAS FÍSICAS (CSV / JSON)
# ------------------------------------------------------------------------------
def exportar_consulta_csv(sql, filepath, limit=100):
    cur.execute(f"{sql} LIMIT {limit};")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(colnames)
        writer.writerows(rows)
    print(f" -> Exportado: {filepath} ({len(rows)} linhas)")

def exportar_consulta_json(sql, filepath, limit=100):
    cur.execute(f"{sql} LIMIT {limit};")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    result = [dict(zip(colnames, r)) for r in rows]
    # converter datas para str
    for d in result:
        for k, v in d.items():
            if isinstance(v, (datetime,)):
                d[k] = v.isoformat()
    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f" -> Exportado: {filepath} ({len(result)} registros)")

print("\n[*] Exportando amostras das camadas...")
# Bronze
exportar_consulta_csv("SELECT * FROM bronze.catalogo", os.path.join(BRONZE_DIR, "catalogo_amostra.csv"), 50)
exportar_consulta_json("SELECT * FROM bronze.interacoes", os.path.join(BRONZE_DIR, "interacoes_amostra.json"), 50)
exportar_consulta_json("SELECT * FROM bronze.comentarios", os.path.join(BRONZE_DIR, "comentarios_amostra.json"), 50)

# Silver
exportar_consulta_csv("SELECT * FROM silver.catalogo", os.path.join(SILVER_DIR, "catalogo.csv"), 100)
exportar_consulta_csv("SELECT * FROM silver.interacoes", os.path.join(SILVER_DIR, "interacoes.csv"), 100)

# Gold
exportar_consulta_csv("SELECT * FROM gold.engajamento_conteudo", os.path.join(GOLD_DIR, "engajamento_conteudo.csv"), 100)
exportar_consulta_csv("SELECT * FROM gold.engajamento_conteudo_mensal", os.path.join(GOLD_DIR, "engajamento_conteudo_mensal.csv"), 100)
exportar_consulta_csv("SELECT * FROM gold.vw_resumo_categoria", os.path.join(GOLD_DIR, "vw_resumo_categoria.csv"), 20)
exportar_consulta_csv("SELECT * FROM gold.vw_conteudos_atencao", os.path.join(GOLD_DIR, "vw_conteudos_atencao.csv"), 50)

# Quarentena
exportar_consulta_csv("SELECT registro_id, origem, regra_violada, data_erro, mensagem_erro, execucao_id FROM quarentena.interacoes", os.path.join(QUARENTENA_DIR, "quarentena_interacoes.csv"), 50)
exportar_consulta_json("SELECT registro_id, origem, regra_violada, data_erro, mensagem_erro, execucao_id, payload FROM quarentena.interacoes", os.path.join(QUARENTENA_DIR, "quarentena_falhas.json"), 50)

cur.close()
conn.close()
print("\n[SUCESSO] Carga e exportação de amostras concluídas com êxito!")
