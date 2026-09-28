import glob
import os
from decimal import Decimal
from pathlib import Path

import psycopg
import pyarrow.parquet as pq


BASE_DIR = Path(__file__).resolve().parents[1]

PARQUET_PATTERN = str(
    BASE_DIR
    / "beam"
    / "saida"
    / "direct"
    / "*.parquet"
)

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "desafio2")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")


SQL_CATALOGO = """
SELECT
    conteudo_id::int AS conteudo_id,
    titulo,
    tipo,
    categoria,
    nivel
FROM silver.catalogo
WHERE conteudo_id IS NOT NULL
"""


SQL_INSERT = """
INSERT INTO gold.engajamento_conteudo (
    conteudo_id,
    titulo,
    tipo,
    categoria,
    nivel,
    total_interacoes,
    tempo_total_segundos,
    media_percentual_conclusao,
    quantidade_conclusoes
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
)
"""


def main():
    if not DB_PASSWORD:
        raise RuntimeError(
            "A variável POSTGRES_PASSWORD não foi definida."
        )

    arquivos = glob.glob(PARQUET_PATTERN)

    if not arquivos:
        raise RuntimeError(
            "Nenhum arquivo Parquet do DirectRunner foi encontrado."
        )

    print("=== CARGA DA CAMADA GOLD ===")
    print(f"Arquivos Parquet encontrados: {len(arquivos)}")

    tabela = pq.read_table(arquivos)
    df_beam = tabela.to_pandas()

    print(f"Linhas agregadas no Beam: {len(df_beam)}")
    print(
        "Interações representadas:",
        int(df_beam["total_interacoes"].sum()),
    )

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SQL_CATALOGO)

            catalogo = {
                row[0]: {
                    "titulo": row[1],
                    "tipo": row[2],
                    "categoria": row[3],
                    "nivel": row[4],
                }
                for row in cursor.fetchall()
            }

            registros_gold = []
            conteudos_sem_catalogo = []

            for _, row in df_beam.iterrows():
                conteudo_id = int(row["conteudo_id"])

                dados_catalogo = catalogo.get(conteudo_id)

                if dados_catalogo is None:
                    conteudos_sem_catalogo.append(conteudo_id)
                    continue

                media = row["media_percentual_conclusao"]

                if media is None:
                    media_decimal = None
                else:
                    media_decimal = Decimal(
                        str(round(float(media), 2))
                    )

                registros_gold.append(
                    (
                        conteudo_id,
                        dados_catalogo["titulo"],
                        dados_catalogo["tipo"],
                        dados_catalogo["categoria"],
                        dados_catalogo["nivel"],
                        int(row["total_interacoes"]),
                        int(row["tempo_total_segundos"]),
                        media_decimal,
                        int(row["quantidade_conclusoes"]),
                    )
                )

            if conteudos_sem_catalogo:
                raise RuntimeError(
                    "Foram encontrados conteúdos da agregação "
                    "sem correspondência em silver.catalogo: "
                    f"{conteudos_sem_catalogo}"
                )

            # Carga completa e idempotente da Gold.
            cursor.execute(
                "TRUNCATE TABLE gold.engajamento_conteudo"
            )

            cursor.executemany(
                SQL_INSERT,
                registros_gold,
            )

        conn.commit()

    print()
    print("Carga Gold concluída com sucesso.")
    print(
        f"Registros gravados: {len(registros_gold)}"
    )


if __name__ == "__main__":
    main()