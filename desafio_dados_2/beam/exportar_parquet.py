import os
import shutil
import time
from pathlib import Path

import pandas as pd
import psycopg
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq


BASE_DIR = Path(__file__).resolve().parents[1]

CSV_PATH = BASE_DIR / "dados" / "silver" / "interacoes.csv"
PARQUET_DIR = BASE_DIR / "dados" / "silver" / "interacoes_parquet"

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "desafio2")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

SQL = """
SELECT
    usuario_id,
    conteudo_id,
    tipo_interacao,
    data_hora,
    tempo_consumido,
    percentual_conclusao,
    avaliacao_atribuida,
    execucao_id,
    data_hora_padronizacao
FROM silver.interacoes
ORDER BY data_hora, usuario_id, conteudo_id
"""


def tamanho_total(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size

    return sum(
        arquivo.stat().st_size
        for arquivo in path.rglob("*")
        if arquivo.is_file()
    )


def formatar_bytes(valor: int) -> str:
    if valor < 1024:
        return f"{valor} B"

    if valor < 1024**2:
        return f"{valor / 1024:.2f} KB"

    return f"{valor / 1024**2:.2f} MB"


def main():
    if not DB_PASSWORD:
        raise RuntimeError(
            "A variável POSTGRES_PASSWORD não foi definida."
        )

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    if PARQUET_DIR.exists():
        shutil.rmtree(PARQUET_DIR)

    print("Conectando ao PostgreSQL...")

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:
        inicio = time.perf_counter()

        with conn.cursor() as cursor:
            cursor.execute(SQL)
            registros = cursor.fetchall()
            colunas = [desc.name for desc in cursor.description]

        df = pd.DataFrame(registros, columns=colunas)

        # Preserva os tipos lógicos da camada Silver.
        df["usuario_id"] = df["usuario_id"].astype("int32")
        df["conteudo_id"] = df["conteudo_id"].astype("int32")
        df["tempo_consumido"] = df["tempo_consumido"].astype("int32")

        # Inteiro nullable: evita que NULL vire float.
        df["avaliacao_atribuida"] = (
            df["avaliacao_atribuida"].astype("Int16")
        )

        df["tipo_interacao"] = df["tipo_interacao"].astype("string")
        df["execucao_id"] = df["execucao_id"].astype("string")

        tempo_extracao = time.perf_counter() - inicio

    if df.empty:
        raise RuntimeError(
            "A consulta à silver.interacoes não retornou dados."
        )

    # Coluna usada exclusivamente para particionamento.
    df["ano_mes"] = df["data_hora"].dt.strftime("%Y-%m")

    print(f"Registros extraídos: {len(df)}")
    print(
        f"Tempo de extração do PostgreSQL: "
        f"{tempo_extracao:.6f} s"
    )

    # ---------------------------------------------------------
    # CSV
    # ---------------------------------------------------------
    inicio = time.perf_counter()

    df.to_csv(
        CSV_PATH,
        index=False,
        encoding="utf-8",
    )

    tempo_escrita_csv = time.perf_counter() - inicio

    # ---------------------------------------------------------
    # PARQUET particionado por ano_mes
    # ---------------------------------------------------------
    schema_arrow = pa.schema([
        ("usuario_id", pa.int32()),
        ("conteudo_id", pa.int32()),
        ("tipo_interacao", pa.string()),
        ("data_hora", pa.timestamp("us")),
        ("tempo_consumido", pa.int32()),
        ("percentual_conclusao", pa.decimal128(5, 2)),
        ("avaliacao_atribuida", pa.int16()),
        ("execucao_id", pa.string()),
        ("data_hora_padronizacao", pa.timestamp("us")),
        ("ano_mes", pa.string()),
    ])

    tabela = pa.Table.from_pandas(
        df,
        schema=schema_arrow,
        preserve_index=False,
        safe=True,
    )

    inicio = time.perf_counter()

    pq.write_to_dataset(
        tabela,
        root_path=str(PARQUET_DIR),
        partition_cols=["ano_mes"],
        compression="snappy",
    )

    tempo_escrita_parquet = time.perf_counter() - inicio

    tamanho_csv = tamanho_total(CSV_PATH)
    tamanho_parquet = tamanho_total(PARQUET_DIR)

    # ---------------------------------------------------------
    # Comparação de leitura
    # ---------------------------------------------------------
    inicio = time.perf_counter()

    df_csv = pd.read_csv(CSV_PATH)

    tempo_leitura_csv = time.perf_counter() - inicio

    inicio = time.perf_counter()

    dataset = ds.dataset(
        PARQUET_DIR,
        format="parquet",
        partitioning="hive",
    )

    tabela_lida = dataset.to_table()
    df_parquet = tabela_lida.to_pandas()

    tempo_leitura_parquet = time.perf_counter() - inicio

    # ---------------------------------------------------------
    # Resultados
    # ---------------------------------------------------------
    print()
    print("=== COMPARAÇÃO CSV x PARQUET ===")
    print(f"Registros CSV:     {len(df_csv)}")
    print(f"Registros Parquet: {len(df_parquet)}")

    print()
    print(f"Tamanho CSV:       {formatar_bytes(tamanho_csv)}")
    print(
        f"Tamanho Parquet:   "
        f"{formatar_bytes(tamanho_parquet)}"
    )

    print()
    print(f"Escrita CSV:       {tempo_escrita_csv:.6f} s")
    print(
        f"Escrita Parquet:   "
        f"{tempo_escrita_parquet:.6f} s"
    )

    print()
    print(f"Leitura CSV:       {tempo_leitura_csv:.6f} s")
    print(
        f"Leitura Parquet:   "
        f"{tempo_leitura_parquet:.6f} s"
    )

    if tamanho_csv > 0:
        economia = (
            1 - tamanho_parquet / tamanho_csv
        ) * 100

        print()
        print(
            f"Redução de tamanho: "
            f"{economia:.2f}%"
        )

    print()
    print("Schema Parquet:")
    print(dataset.schema)


if __name__ == "__main__":
    main()