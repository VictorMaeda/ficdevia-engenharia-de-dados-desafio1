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
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "desafio_dados")
DB_USER = os.getenv("POSTGRES_USER", "desafio_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "troque_esta_senha")


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


SQL_INSERT_ENGAJAMENTO = """
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


SQL_INSERT_MENSAL = """
INSERT INTO gold.engajamento_conteudo_mensal (
    mes_referencia,
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
SELECT
    DATE_TRUNC(
        'month',
        i.data_hora
    )::date AS mes_referencia,

    i.conteudo_id::int,

    c.titulo,
    c.tipo,
    c.categoria,
    c.nivel,

    COUNT(*)::bigint
        AS total_interacoes,

    SUM(
        COALESCE(
            i.tempo_consumido,
            0
        )
    )::bigint
        AS tempo_total_segundos,

    ROUND(
        AVG(
            i.percentual_conclusao
        ),
        2
    ) AS media_percentual_conclusao,

    COUNT(*) FILTER (
        WHERE LOWER(
            TRIM(i.tipo_interacao)
        ) = 'conclusão'
    )::bigint
        AS quantidade_conclusoes

FROM silver.interacoes i

INNER JOIN silver.catalogo c
    ON c.conteudo_id = i.conteudo_id

GROUP BY
    DATE_TRUNC(
        'month',
        i.data_hora
    )::date,
    i.conteudo_id,
    c.titulo,
    c.tipo,
    c.categoria,
    c.nivel
"""


def obter_argumentos():
    parser = argparse.ArgumentParser(
        description=(
            "Carrega na camada Gold a agregacao "
            "produzida pelo Apache Beam e a "
            "agregacao mensal derivada da Silver."
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
        f"Padrao de entrada: "
        f"{argumentos.input}"
    )

    print(
        f"Arquivos Parquet encontrados: "
        f"{len(arquivos)}"
    )

    # ---------------------------------------------------------
    # LEITURA DA AGREGACAO PRODUZIDA PELO BEAM
    # ---------------------------------------------------------

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

    total_interacoes_beam = int(
        df_beam[
            "total_interacoes"
        ].sum()
    )

    total_conclusoes_beam = int(
        df_beam[
            "quantidade_conclusoes"
        ].sum()
    )

    print(
        f"Linhas agregadas no Beam: "
        f"{len(df_beam)}"
    )

    print(
        "Interacoes representadas:",
        total_interacoes_beam,
    )

    print(
        "Conclusoes representadas:",
        total_conclusoes_beam,
    )

    # ---------------------------------------------------------
    # TRANSACAO GOLD
    # ---------------------------------------------------------

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:

        with conn.cursor() as cursor:

            # -------------------------------------------------
            # CATALOGO SILVER
            # -------------------------------------------------

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

            # -------------------------------------------------
            # PREPARA GOLD CONSOLIDADA
            # -------------------------------------------------

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
                print(
                    f"[AVISO] {len(conteudos_sem_catalogo)} conteúdo(s) sem"
                    " correspondência em silver.catalogo foram ignorados na Gold"
                    f" (RF05 - integridade referencial): {conteudos_sem_catalogo}"
                )
                # Ajusta contadores para refletir apenas registros carregados
                df_filtrado = df_beam[df_beam["conteudo_id"].isin(catalogo.keys())]
                total_interacoes_beam = int(df_filtrado["total_interacoes"].sum())
                total_conclusoes_beam = int(df_filtrado["quantidade_conclusoes"].sum())

            # -------------------------------------------------
            # CARGA COMPLETA E ATOMICA
            # -------------------------------------------------

            cursor.execute(
                """
                TRUNCATE TABLE
                    gold.engajamento_conteudo,
                    gold.engajamento_conteudo_mensal
                """
            )

            cursor.executemany(
                SQL_INSERT_ENGAJAMENTO,
                registros_gold,
            )

            cursor.execute(
                SQL_INSERT_MENSAL
            )

            # -------------------------------------------------
            # VALIDACAO DA GOLD MENSAL
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(
                        DISTINCT mes_referencia
                    ),
                    SUM(total_interacoes),
                    SUM(quantidade_conclusoes)
                FROM
                    gold.engajamento_conteudo_mensal
                """
            )

            (
                registros_mensais,
                meses,
                interacoes_mensais,
                conclusoes_mensais,
            ) = cursor.fetchone()

            interacoes_mensais = int(
                interacoes_mensais or 0
            )

            conclusoes_mensais = int(
                conclusoes_mensais or 0
            )

            # A soma mensal deve representar
            # exatamente o mesmo universo do Beam.
            if (
                interacoes_mensais
                != total_interacoes_beam
            ):
                raise RuntimeError(
                    "Divergencia entre Beam e "
                    "Gold mensal. "
                    "Interacoes Beam: "
                    f"{total_interacoes_beam}; "
                    "interacoes mensais: "
                    f"{interacoes_mensais}."
                )

            if (
                conclusoes_mensais
                != total_conclusoes_beam
            ):
                raise RuntimeError(
                    "Divergencia entre Beam e "
                    "Gold mensal. "
                    "Conclusoes Beam: "
                    f"{total_conclusoes_beam}; "
                    "conclusoes mensais: "
                    f"{conclusoes_mensais}."
                )

        # O commit acontece somente depois
        # de todas as validacoes.
        conn.commit()

    # ---------------------------------------------------------
    # RESULTADO
    # ---------------------------------------------------------

    print()

    print(
        "Carga Gold concluida com sucesso."
    )

    print(
        "Gold consolidada - registros:",
        len(registros_gold),
    )

    print(
        "Gold mensal - registros:",
        registros_mensais,
    )

    print(
        "Gold mensal - meses:",
        meses,
    )

    print(
        "Gold mensal - interacoes:",
        interacoes_mensais,
    )

    print(
        "Gold mensal - conclusoes:",
        conclusoes_mensais,
    )


if __name__ == "__main__":
    main()