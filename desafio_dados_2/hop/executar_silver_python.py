#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRÁTICO 2 — FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: desafio_dados_2/hop/executar_silver_python.py
REQUISITOS: RF21 (Pipeline Silver e Padronização), RF23 (Quarentena)
FINALIDADE: Script Python que replica a lógica dos pipelines Apache Hop
            silver_catalogo.hpl, silver_interacoes.hpl e silver_comentarios.hpl.
            Serve como alternativa executável quando o Apache Hop não está
            instalado no ambiente, mantendo a mesma semântica de transformação,
            validação, deduplicação e quarentena.

NOTA: Os arquivos .hpl originais (definição canônica do Apache Hop) continuam
      sendo o entregável oficial do RF21. Este script é um executor alternativo
      para ambientes sem Hop instalado.
==============================================================================
"""

import json
import os
import uuid
from datetime import datetime, date
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
    _DRIVER = "psycopg2"
except ImportError:
    import psycopg as psycopg2  # type: ignore[no-redef]
    _DRIVER = "psycopg3"

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "desafio_dados")
DB_USER = os.getenv("POSTGRES_USER", "desafio_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "troque_esta_senha")

EXECUCAO_ID = f"SILVER_EXEC_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


# ─── TIPOS VÁLIDOS POR COLUNA ────────────────────────────────────────────────
TIPOS_VALIDOS = {"Vídeo", "Artigo", "Podcast", "Curso", "Ebook", "Webinar"}
NIVEIS_VALIDOS = {"Básico", "Intermediário", "Avançado"}
TIPOS_INTERACAO_VALIDOS = {
    "visualização", "conclusão", "curtida", "avaliação", "compartilhamento"
}


def conectar():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )


def normalizar_texto(valor: str | None) -> str | None:
    """Remove espaços, converte para capitalização padronizada."""
    if valor is None:
        return None
    return valor.strip()


def parse_data(valor: str | None) -> date | None:
    """Converte string de data para objeto date. Retorna None se inválida."""
    if not valor:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(valor.strip(), fmt).date()
        except ValueError:
            continue
    return None


def popular_silver_catalogo(conn):
    """
    Replica silver_catalogo.hpl:
    - Lê bronze.catalogo
    - Remove duplicados por conteudo_id
    - Padroniza tipos numéricos
    - Valida campos obrigatórios e data
    - Registros inválidos → quarentena.catalogo
    - Registros válidos → silver.catalogo (truncate + insert)
    """
    print("\n[Silver Catálogo] Iniciando padronização...")

    with conn.cursor() as cur:
        # Lê Bronze
        cur.execute("""
            SELECT conteudo_id, titulo, tipo, categoria, nivel,
                   carga_horaria_min, data_publicacao, descricao, autor,
                   origem_arquivo, execucao_id
            FROM bronze.catalogo
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        registros = [dict(zip(cols, r)) for r in rows]

    print(f"  Bronze lida: {len(registros)} registros.")

    # Deduplicação por conteudo_id (mantém primeiro ocorrência)
    vistos = set()
    unicos = []
    for r in registros:
        cid = r.get("conteudo_id")
        if cid not in vistos:
            vistos.add(cid)
            unicos.append(r)
    print(f"  Após deduplicação: {len(unicos)} registros únicos.")

    validos = []
    quarentena = []

    for r in unicos:
        erros = []

        # Converte tipos numéricos
        try:
            cid = int(float(r["conteudo_id"])) if r["conteudo_id"] is not None else None
        except (ValueError, TypeError):
            cid = None

        try:
            carga = float(r["carga_horaria_min"]) if r["carga_horaria_min"] is not None else None
        except (ValueError, TypeError):
            carga = None

        # Valida obrigatórios
        if cid is None:
            erros.append("conteudo_id ausente ou inválido")
        if not r.get("titulo", "").strip():
            erros.append("titulo ausente")
        if not r.get("tipo", "").strip():
            erros.append("tipo ausente")
        if not r.get("categoria", "").strip():
            erros.append("categoria ausente")
        if not r.get("nivel", "").strip():
            erros.append("nivel ausente")
        if carga is None:
            erros.append("carga_horaria_min inválida")
        if not r.get("descricao", "").strip():
            erros.append("descricao ausente")
        if not r.get("autor", "").strip():
            erros.append("autor ausente")

        # Valida data
        data_pub = parse_data(r.get("data_publicacao"))
        if data_pub is None:
            erros.append("data_publicacao inválida ou ausente")

        if erros:
            quarentena.append({
                "origem": "bronze.catalogo",
                "regra_violada": "; ".join(erros),
                "execucao_id": EXECUCAO_ID,
                "payload": json.dumps({**r, "conteudo_id": str(r.get("conteudo_id"))}),
            })
        else:
            validos.append((
                normalizar_texto(r["titulo"]),
                normalizar_texto(r["tipo"]),
                normalizar_texto(r["categoria"]),
                normalizar_texto(r["nivel"]),
                data_pub,
                normalizar_texto(r.get("descricao")),
                normalizar_texto(r.get("autor")),
                r.get("origem_arquivo"),
                EXECUCAO_ID,
                float(cid),
                carga,
            ))

    print(f"  Válidos: {len(validos)} | Quarentena: {len(quarentena)}")

    with conn.cursor() as cur:
        # Truncate Silver (idempotente)
        cur.execute("TRUNCATE TABLE silver.catalogo")

        if validos:
            cur.executemany("""
                INSERT INTO silver.catalogo
                (titulo, tipo, categoria, nivel, data_publicacao, descricao, autor,
                 origem_arquivo, execucao_id, conteudo_id, carga_horaria_min)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, validos)

        for q in quarentena:
            cur.execute("""
                INSERT INTO quarentena.catalogo
                (origem, regra_violada, execucao_id, payload)
                VALUES (%s, %s, %s, %s::jsonb)
            """, (q["origem"], q["regra_violada"], q["execucao_id"], q["payload"]))

    conn.commit()
    print(f"  [OK] Silver.catalogo: {len(validos)} registros. Quarentena: {len(quarentena)}.")
    return len(validos)


def popular_silver_interacoes(conn):
    """
    Replica silver_interacoes.hpl:
    - Lê bronze.interacoes (JSONB)
    - Extrai campos do JSON
    - Valida e padroniza
    - Registros inválidos → quarentena.interacoes
    - Registros válidos → silver.interacoes
    """
    print("\n[Silver Interações] Iniciando padronização...")

    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT conteudo_id FROM silver.catalogo")
        conteudos_validos = {int(r[0]) for r in cur.fetchall() if r[0] is not None}

        cur.execute("SELECT id, conteudo_json, origem_arquivo, execucao_id FROM bronze.interacoes")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        registros = [dict(zip(cols, r)) for r in rows]

    print(f"  Bronze lida: {len(registros)} registros. Catálogo válido: {len(conteudos_validos)} IDs.")

    validos = []
    quarentena = []
    vistos = set()  # (usuario_id, conteudo_id, data_hora) para deduplicação

    for r in registros:
        payload = r["conteudo_json"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                quarentena.append({
                    "origem": "bronze.interacoes",
                    "regra_violada": "JSON inválido",
                    "execucao_id": EXECUCAO_ID,
                    "payload": json.dumps({"id": r["id"]}),
                })
                continue

        erros = []

        # Extrai campos
        try:
            uid = int(payload.get("usuario_id")) if payload.get("usuario_id") is not None else None
        except (ValueError, TypeError):
            uid = None

        try:
            cid = int(payload.get("conteudo_id")) if payload.get("conteudo_id") is not None else None
        except (ValueError, TypeError):
            cid = None

        tipo_int = str(payload.get("tipo_interacao", "")).strip().lower()

        # Parse data_hora
        data_hora = None
        for fld in ("data_hora", "data", "timestamp"):
            if payload.get(fld):
                try:
                    data_hora = datetime.fromisoformat(str(payload[fld]).replace("Z", "+00:00"))
                    break
                except ValueError:
                    pass

        try:
            tempo = int(payload.get("tempo_consumido", 0))
        except (ValueError, TypeError):
            tempo = 0

        try:
            perc_raw = payload.get("percentual_conclusao")
            percentual = float(perc_raw) if perc_raw is not None else None
        except (ValueError, TypeError):
            percentual = None

        try:
            aval_raw = payload.get("avaliacao_atribuida") or payload.get("nota")
            avaliacao = int(aval_raw) if aval_raw is not None else None
        except (ValueError, TypeError):
            avaliacao = None

        # Validações
        if uid is None:
            erros.append("usuario_id ausente ou inválido")
        if cid is None:
            erros.append("conteudo_id ausente ou inválido")
        elif cid not in conteudos_validos:
            erros.append(f"conteudo_id {cid} não existe no catálogo (falha de integridade referencial)")
        if not tipo_int:
            erros.append("tipo_interacao ausente")
        if data_hora is None:
            erros.append("data_hora inválida ou ausente")
        if tempo < 0:
            erros.append("tempo_consumido negativo")
        if percentual is not None and not (0 <= percentual <= 100):
            erros.append(f"percentual_conclusao fora da faixa [0,100]: {percentual}")

        # Deduplicação
        chave = (uid, cid, str(data_hora))
        if chave in vistos:
            erros.append("duplicata por (usuario_id, conteudo_id, data_hora)")
        else:
            vistos.add(chave)

        if erros:
            quarentena.append({
                "origem": "bronze.interacoes",
                "regra_violada": "; ".join(erros),
                "execucao_id": EXECUCAO_ID,
                "payload": json.dumps({k: str(v) for k, v in payload.items()}),
            })
        else:
            validos.append((
                uid,
                cid,
                tipo_int,
                data_hora,
                tempo,
                percentual,
                avaliacao,
                EXECUCAO_ID,
            ))

    print(f"  Válidos: {len(validos)} | Quarentena: {len(quarentena)}")

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE silver.interacoes")

        if validos:
            cur.executemany("""
                INSERT INTO silver.interacoes
                (usuario_id, conteudo_id, tipo_interacao, data_hora,
                 tempo_consumido, percentual_conclusao, avaliacao_atribuida, execucao_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, validos)

        for q in quarentena:
            cur.execute("""
                INSERT INTO quarentena.interacoes
                (origem, regra_violada, execucao_id, payload)
                VALUES (%s, %s, %s, %s::jsonb)
            """, (q["origem"], q["regra_violada"], q["execucao_id"], q["payload"]))

    conn.commit()
    print(f"  [OK] Silver.interacoes: {len(validos)} registros. Quarentena: {len(quarentena)}.")
    return len(validos)


def popular_silver_comentarios(conn):
    """
    Replica silver_comentarios.hpl:
    - Lê bronze.comentarios (JSONB)
    - Extrai campos, valida e padroniza
    - Registros inválidos → quarentena.comentarios
    - Registros válidos → silver.comentarios
    """
    print("\n[Silver Comentários] Iniciando padronização...")

    with conn.cursor() as cur:
        cur.execute("SELECT id, conteudo_json, origem_arquivo, execucao_id FROM bronze.comentarios")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        registros = [dict(zip(cols, r)) for r in rows]

    print(f"  Bronze lida: {len(registros)} registros.")

    validos = []
    quarentena = []

    for r in registros:
        payload = r["conteudo_json"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                quarentena.append({
                    "origem": "bronze.comentarios",
                    "regra_violada": "JSON inválido",
                    "execucao_id": EXECUCAO_ID,
                    "payload": json.dumps({"id": r["id"]}),
                })
                continue

        erros = []

        try:
            uid = int(payload.get("usuario_id")) if payload.get("usuario_id") is not None else None
        except (ValueError, TypeError):
            uid = None

        try:
            cid = int(payload.get("conteudo_id")) if payload.get("conteudo_id") is not None else None
        except (ValueError, TypeError):
            cid = None

        try:
            nota_raw = payload.get("nota") or payload.get("avaliacao")
            nota = int(nota_raw) if nota_raw is not None else None
        except (ValueError, TypeError):
            nota = None

        comentario = str(payload.get("comentario", "")).strip() or None

        data_coment = None
        for fld in ("data", "data_hora", "timestamp"):
            if payload.get(fld):
                data_coment = parse_data(str(payload[fld])[:10])
                if data_coment:
                    break

        if uid is None:
            erros.append("usuario_id ausente")
        if cid is None:
            erros.append("conteudo_id ausente")
        if nota is not None and not (1 <= nota <= 5):
            erros.append(f"nota fora da faixa [1,5]: {nota}")

        if erros:
            quarentena.append({
                "origem": "bronze.comentarios",
                "regra_violada": "; ".join(erros),
                "execucao_id": EXECUCAO_ID,
                "payload": json.dumps({k: str(v) for k, v in payload.items()}),
            })
        else:
            validos.append((uid, cid, nota, comentario, data_coment, EXECUCAO_ID))

    print(f"  Válidos: {len(validos)} | Quarentena: {len(quarentena)}")

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE silver.comentarios")

        if validos:
            cur.executemany("""
                INSERT INTO silver.comentarios
                (usuario_id, conteudo_id, avaliacao, comentario, data, execucao_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, validos)

        for q in quarentena:
            cur.execute("""
                INSERT INTO quarentena.comentarios
                (origem, regra_violada, execucao_id, payload)
                VALUES (%s, %s, %s, %s::jsonb)
            """, (q["origem"], q["regra_violada"], q["execucao_id"], q["payload"]))

    conn.commit()
    print(f"  [OK] Silver.comentarios: {len(validos)} registros. Quarentena: {len(quarentena)}.")
    return len(validos)


def main():
    print("=" * 70)
    print("RF21 — PIPELINES SILVER (EXECUTOR PYTHON — EQUIVALENTE AO APACHE HOP)")
    print(f"Execução: {EXECUCAO_ID}")
    print(f"Driver: {_DRIVER}")
    print("=" * 70)

    inicio = datetime.now()
    conn = conectar()
    print(f"[OK] Conectado ao PostgreSQL em {DB_HOST}:{DB_PORT}/{DB_NAME}")

    try:
        n_cat = popular_silver_catalogo(conn)
        n_int = popular_silver_interacoes(conn)
        n_com = popular_silver_comentarios(conn)
    finally:
        conn.close()

    duracao = (datetime.now() - inicio).total_seconds()
    print("\n" + "=" * 70)
    print("RESUMO DA PADRONIZAÇÃO SILVER:")
    print(f"  silver.catalogo:     {n_cat} registros")
    print(f"  silver.interacoes:   {n_int} registros")
    print(f"  silver.comentarios:  {n_com} registros")
    print(f"  Duração total:       {duracao:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
