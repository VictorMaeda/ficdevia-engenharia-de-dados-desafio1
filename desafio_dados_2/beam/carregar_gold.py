import argparse
import glob
import os
from decimal import Decimal
from pathlib import Path

import psycopg
import pyarrow.parquet as pq


BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_PARQUET_PATTERN = str(
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


def obter_argumentos():
    parser = argparse.ArgumentParser(
        description=(
            "Carrega na camada Gold a agregacao "
            "produzida pelo Apache Beam."
        )
    )

    parser.add_argument(
        "--input",
        default=DEFAULT_PARQUET_PATTERN,
        help=(
            "Padrao dos arquivos Parquet gerados "
            "pelo Beam."
        ),
    )

    return parser.parse_args()


def main():
    argumentos = obter_argumentos()

    if not DB_PASSWORD:
        raise RuntimeError(
            "A variavel POSTGRES_PASSWORD "
            "nao foi definida."
        )

    arquivos = sorted(
        glob.glob(argumentos.input)
    )

    if not arquivos:
        raise RuntimeError(
            "Nenhum arquivo Parquet do Beam "
            "foi encontrado para o padrao: "
            f"{argumentos.input}"
        )

    print("=== CARGA DA CAMADA GOLD ===")
    print(
        f"Padrao de entrada: {argumentos.input}"
    )
    print(
        f"Arquivos Parquet encontrados: "
        f"{len(arquivos)}"
    )

    tabela = pq.read_table(arquivos)
    df_beam = tabela.to_pandas()

    if df_beam.empty:
        raise RuntimeError(
            "A saida do Beam nao possui registros."
        )

    if df_beam["conteudo_id"].duplicated().any():
        duplicados = (
            df_beam.loc[
                df_beam[
                    "conteudo_id"
                ].duplicated(keep=False),
                "conteudo_id",
            ]
            .astype(int)
            .tolist()
        )

        raise RuntimeError(
            "A saida do Beam possui conteudo_id "
            f"duplicado: {duplicados}"
        )

    print(
        f"Linhas agregadas no Beam: "
        f"{len(df_beam)}"
    )

    print(
        "Interacoes representadas:",
        int(
            df_beam[
                "total_interacoes"
            ].sum()
        ),
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
                conteudo_id = int(
                    row["conteudo_id"]
                )

                dados_catalogo = (
                    catalogo.get(conteudo_id)
                )

                if dados_catalogo is None:
                    conteudos_sem_catalogo.append(
                        conteudo_id
                    )
                    continue

                media = row[
                    "media_percentual_conclusao"
                ]

                if media is None:
                    media_decimal = None
                else:
                    media_decimal = Decimal(
                        str(
                            round(
                                float(media),
                                2,
                            )
                        )
                    )

                registros_gold.append(
                    (
                        conteudo_id,
                        dados_catalogo["titulo"],
                        dados_catalogo["tipo"],
                        dados_catalogo["categoria"],
                        dados_catalogo["nivel"],
                        int(
                            row[
                                "total_interacoes"
                            ]
                        ),
                        int(
                            row[
                                "tempo_total_segundos"
                            ]
                        ),
                        media_decimal,
                        int(
                            row[
                                "quantidade_conclusoes"
                            ]
                        ),
                    )
                )

            if conteudos_sem_catalogo:
                raise RuntimeError(
                    "Foram encontrados conteudos "
                    "da agregacao sem correspondencia "
                    "em silver.catalogo: "
                    f"{conteudos_sem_catalogo}"
                )

            # A operacao ocorre dentro da mesma
            # transacao. Se o INSERT falhar,
            # o TRUNCATE tambem sera revertido.
            cursor.execute(
                """
                TRUNCATE TABLE
                    gold.engajamento_conteudo
                """
            )

            cursor.executemany(
                SQL_INSERT,
                registros_gold,
            )

        conn.commit()

    print()
    print(
        "Carga Gold concluida com sucesso."
    )

    print(
        f"Registros gravados: "
        f"{len(registros_gold)}"
    )


if __name__ == "__main__":
    main()