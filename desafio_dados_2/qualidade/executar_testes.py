import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import psycopg


BASE_DIR = Path(__file__).resolve().parents[1]
RESULTADOS_DIR = BASE_DIR / "qualidade" / "resultados"

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "desafio_dados")
DB_USER = os.getenv("POSTGRES_USER", "desafio_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "troque_esta_senha")


TESTES = [
    {
        "codigo": "Q01_COMPLETUDE",
        "nome": "Completude dos campos obrigatórios de interações",
        "dimensao": "completude",
        "fonte": "silver.interacoes",
        "formula": (
            "(registros válidos / total de registros) * 100"
        ),
        "limite": 100.0,
        "severidade": "CRITICA",
        "acao": (
            "Bloquear publicação da Gold e revisar a etapa "
            "Silver/quarentena."
        ),
        "sql_total": """
            SELECT COUNT(*)
            FROM silver.interacoes
        """,
        "sql_invalidos": """
            SELECT COUNT(*)
            FROM silver.interacoes
            WHERE
                usuario_id IS NULL
                OR conteudo_id IS NULL
                OR tipo_interacao IS NULL
                OR BTRIM(tipo_interacao) = ''
                OR data_hora IS NULL
                OR tempo_consumido IS NULL
                OR percentual_conclusao IS NULL
                OR execucao_id IS NULL
                OR BTRIM(execucao_id) = ''
                OR data_hora_padronizacao IS NULL
        """,
    },
    {
        "codigo": "Q02_VALIDADE_PERCENTUAL",
        "nome": "Validade do percentual de conclusão",
        "dimensao": "validade",
        "fonte": "silver.interacoes",
        "formula": (
            "(registros com percentual entre 0 e 100 "
            "/ total de registros) * 100"
        ),
        "limite": 100.0,
        "severidade": "ALTA",
        "acao": (
            "Registrar ocorrência e revisar a regra de validação "
            "da Silver antes da próxima publicação."
        ),
        "sql_total": """
            SELECT COUNT(*)
            FROM silver.interacoes
        """,
        "sql_invalidos": """
            SELECT COUNT(*)
            FROM silver.interacoes
            WHERE
                percentual_conclusao IS NOT NULL
                AND (
                    percentual_conclusao < 0
                    OR percentual_conclusao > 100
                )
        """,
    },
    {
        "codigo": "Q03_UNICIDADE_CATALOGO",
        "nome": "Unicidade da chave de conteúdo no catálogo",
        "dimensao": "unicidade",
        "fonte": "silver.catalogo",
        "formula": (
            "(conteúdos únicos / total de registros) * 100"
        ),
        "limite": 100.0,
        "severidade": "CRITICA",
        "acao": (
            "Bloquear publicação da Gold e revisar "
            "deduplicação do catálogo."
        ),
        "sql_total": """
            SELECT COUNT(*)
            FROM silver.catalogo
        """,
        "sql_invalidos": """
            SELECT
                COUNT(*) - COUNT(DISTINCT conteudo_id)
            FROM silver.catalogo
        """,
    },
    {
        "codigo": "Q04_CONSISTENCIA_CONCLUSAO",
        "nome": "Consistência entre conclusão e percentual",
        "dimensao": "consistencia",
        "fonte": "silver.interacoes",
        "formula": (
            "(registros consistentes / total de registros) * 100"
        ),
        "limite": 100.0,
        "severidade": "MEDIA",
        "acao": (
            "Registrar ressalva e investigar interações de conclusão "
            "com percentual diferente de 100."
        ),
        "sql_total": """
            SELECT COUNT(*)
            FROM silver.interacoes
        """,
        "sql_invalidos": """
            SELECT COUNT(*)
            FROM silver.interacoes
            WHERE
                LOWER(BTRIM(tipo_interacao)) = 'conclusão'
                AND (
                    percentual_conclusao IS NULL
                    OR percentual_conclusao <> 100
                )
        """,
    },
    {
        "codigo": "Q05_INTEGRIDADE_REFERENCIAL",
        "nome": "Integridade referencial das interações com o catálogo",
        "dimensao": "integridade_referencial",
        "fonte": "silver.interacoes -> silver.catalogo",
        "formula": (
            "(interações com conteúdo existente "
            "/ total de interações) * 100"
        ),
        "limite": 100.0,
        "severidade": "CRITICA",
        "acao": (
            "Bloquear publicação da Gold e encaminhar registros "
            "órfãos para investigação/quarentena."
        ),
        "sql_total": """
            SELECT COUNT(*)
            FROM silver.interacoes
        """,
        "sql_invalidos": """
            SELECT COUNT(*)
            FROM silver.interacoes i
            WHERE NOT EXISTS (
                SELECT 1
                FROM silver.catalogo c
                WHERE c.conteudo_id::int = i.conteudo_id
            )
        """,
    },
]


SQL_INSERT_RESULTADO = """
INSERT INTO qualidade.resultados (
    execucao_qualidade_id,
    execucao_dados_id,
    fonte,
    teste_codigo,
    teste_nome,
    dimensao,
    formula,
    limite_aceitavel,
    severidade,
    acao,
    total_registros,
    registros_invalidos,
    valor_metrica,
    status
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
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
)
"""


def obter_execucao_dados(cursor):
    cursor.execute(
        """
        SELECT STRING_AGG(
            execucao_id,
            ','
            ORDER BY execucao_id
        )
        FROM (
            SELECT DISTINCT execucao_id
            FROM silver.interacoes
            WHERE execucao_id IS NOT NULL
        ) execucoes
        """
    )

    valor = cursor.fetchone()[0]

    return valor or "desconhecida"


def calcular_metrica(total, invalidos):
    if total <= 0:
        return 0.0

    validos = total - invalidos

    return round(
        (validos / total) * 100,
        3,
    )


def executar_teste(cursor, teste):
    cursor.execute(teste["sql_total"])
    total = int(cursor.fetchone()[0])

    cursor.execute(teste["sql_invalidos"])
    invalidos = int(cursor.fetchone()[0])

    metrica = calcular_metrica(
        total,
        invalidos,
    )

    status = (
        "APROVADO"
        if metrica >= teste["limite"]
        else "REPROVADO"
    )

    return {
        "codigo": teste["codigo"],
        "nome": teste["nome"],
        "dimensao": teste["dimensao"],
        "fonte": teste["fonte"],
        "formula": teste["formula"],
        "limite": teste["limite"],
        "severidade": teste["severidade"],
        "acao": teste["acao"],
        "total_registros": total,
        "registros_invalidos": invalidos,
        "valor_metrica": metrica,
        "status": status,
    }


def salvar_json(
    execucao_qualidade_id,
    execucao_dados_id,
    resultados,
    status_geral,
):
    RESULTADOS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = (
        RESULTADOS_DIR
        / f"qualidade_{execucao_qualidade_id}.json"
    )

    conteudo = {
        "execucao_qualidade_id": execucao_qualidade_id,
        "execucao_dados_id": execucao_dados_id,
        "data_execucao": datetime.now().isoformat(
            timespec="seconds"
        ),
        "status_geral": status_geral,
        "resultados": resultados,
    }

    with caminho.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            conteudo,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    return caminho


def main():
    if not DB_PASSWORD:
        raise RuntimeError(
            "A variável POSTGRES_PASSWORD não foi definida."
        )

    execucao_qualidade_id = str(
        uuid.uuid4()
    )

    print("=== RF31 - QUALIDADE DE DADOS ===")
    print(
        "Execução de qualidade:",
        execucao_qualidade_id,
    )
    print()

    resultados = []

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:
        with conn.cursor() as cursor:
            execucao_dados_id = obter_execucao_dados(
                cursor
            )

            print(
                "Execução dos dados:",
                execucao_dados_id,
            )
            print()

            for teste in TESTES:
                resultado = executar_teste(
                    cursor,
                    teste,
                )

                resultados.append(resultado)

                cursor.execute(
                    SQL_INSERT_RESULTADO,
                    (
                        execucao_qualidade_id,
                        execucao_dados_id,
                        resultado["fonte"],
                        resultado["codigo"],
                        resultado["nome"],
                        resultado["dimensao"],
                        resultado["formula"],
                        resultado["limite"],
                        resultado["severidade"],
                        resultado["acao"],
                        resultado["total_registros"],
                        resultado["registros_invalidos"],
                        resultado["valor_metrica"],
                        resultado["status"],
                    ),
                )

        conn.commit()

    falhas_criticas = [
        resultado
        for resultado in resultados
        if (
            resultado["status"] == "REPROVADO"
            and resultado["severidade"] == "CRITICA"
        )
    ]

    falhas_nao_criticas = [
        resultado
        for resultado in resultados
        if (
            resultado["status"] == "REPROVADO"
            and resultado["severidade"] != "CRITICA"
        )
    ]

    if falhas_criticas:
        status_geral = "FALHA"
    elif falhas_nao_criticas:
        status_geral = "SUCESSO_COM_RESSALVAS"
    else:
        status_geral = "SUCESSO"

    print(
        f"{'Teste':<32}"
        f"{'Dimensão':<25}"
        f"{'Total':>8}"
        f"{'Inválidos':>12}"
        f"{'Métrica':>12}"
        f"{'Status':>14}"
    )

    print("-" * 103)

    for resultado in resultados:
        print(
            f"{resultado['codigo']:<32}"
            f"{resultado['dimensao']:<25}"
            f"{resultado['total_registros']:>8}"
            f"{resultado['registros_invalidos']:>12}"
            f"{resultado['valor_metrica']:>11.3f}%"
            f"{resultado['status']:>14}"
        )

    print()

    caminho_json = salvar_json(
        execucao_qualidade_id,
        execucao_dados_id,
        resultados,
        status_geral,
    )

    print(
        "Status geral:",
        status_geral,
    )

    print(
        "Evidência JSON:",
        caminho_json,
    )

    if falhas_criticas:
        print()
        print(
            "PUBLICAÇÃO GOLD BLOQUEADA:"
            " existe pelo menos uma regra crítica reprovada."
        )

        sys.exit(1)

    if falhas_nao_criticas:
        print()
        print(
            "Execução concluída com ressalvas."
        )

    else:
        print()
        print(
            "Qualidade aprovada."
            " Publicação Gold autorizada."
        )


if __name__ == "__main__":
    main()