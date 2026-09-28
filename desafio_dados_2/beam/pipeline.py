import argparse
import os
import time

import apache_beam as beam
import pyarrow as pa
from apache_beam.io.parquetio import ReadFromParquet, WriteToParquet
from apache_beam.options.pipeline_options import PipelineOptions


class SomarEstatisticas(beam.CombineFn):
    """
    Acumulador:
    (
        total_interacoes,
        tempo_total,
        soma_percentual,
        qtd_percentual,
        qtd_conclusoes
    )
    """

    def create_accumulator(self):
        return 0, 0, 0.0, 0, 0

    def add_input(self, acumulador, valor):
        (
            total,
            tempo_total,
            soma_percentual,
            qtd_percentual,
            qtd_conclusoes,
        ) = acumulador

        (
            tempo,
            percentual,
            possui_percentual,
            conclusao,
        ) = valor

        return (
            total + 1,
            tempo_total + tempo,
            soma_percentual + percentual,
            qtd_percentual + possui_percentual,
            qtd_conclusoes + conclusao,
        )

    def merge_accumulators(self, acumuladores):
        total = 0
        tempo_total = 0
        soma_percentual = 0.0
        qtd_percentual = 0
        qtd_conclusoes = 0

        for acumulador in acumuladores:
            total += acumulador[0]
            tempo_total += acumulador[1]
            soma_percentual += acumulador[2]
            qtd_percentual += acumulador[3]
            qtd_conclusoes += acumulador[4]

        return (
            total,
            tempo_total,
            soma_percentual,
            qtd_percentual,
            qtd_conclusoes,
        )

    def extract_output(self, acumulador):
        return acumulador


def preparar_registro(registro):
    conteudo_id = int(registro["conteudo_id"])

    tempo = registro.get("tempo_consumido")
    tempo = int(tempo) if tempo is not None else 0

    percentual = registro.get("percentual_conclusao")

    if percentual is None:
        percentual_valor = 0.0
        possui_percentual = 0
    else:
        percentual_valor = float(percentual)
        possui_percentual = 1

    tipo_interacao = str(
        registro.get("tipo_interacao") or ""
    ).strip().lower()

    conclusao = (
        1 if tipo_interacao == "conclusão" else 0
    )

    return (
        conteudo_id,
        (
            tempo,
            percentual_valor,
            possui_percentual,
            conclusao,
        ),
    )


def montar_saida(elemento):
    conteudo_id, valores = elemento

    (
        total_interacoes,
        tempo_total,
        soma_percentual,
        qtd_percentual,
        qtd_conclusoes,
    ) = valores

    if qtd_percentual > 0:
        media_percentual = (
            soma_percentual / qtd_percentual
        )
    else:
        media_percentual = 0.0

    return {
        "conteudo_id": conteudo_id,
        "total_interacoes": total_interacoes,
        "tempo_total_segundos": tempo_total,
        "media_percentual_conclusao": media_percentual,
        "quantidade_conclusoes": qtd_conclusoes,
    }


SCHEMA_SAIDA = pa.schema([
    ("conteudo_id", pa.int32()),
    ("total_interacoes", pa.int64()),
    ("tempo_total_segundos", pa.int64()),
    ("media_percentual_conclusao", pa.float64()),
    ("quantidade_conclusoes", pa.int64()),
])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Padrão dos arquivos Parquet de entrada.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Prefixo dos arquivos Parquet de saída.",
    )

    argumentos, pipeline_args = parser.parse_known_args()

    caminho_entrada = os.path.abspath(argumentos.input)
    if os.path.isdir(caminho_entrada):
        caminho_entrada = os.path.join(caminho_entrada, "*", "*.parquet")
    elif "interacoes_parquet" in caminho_entrada:
        pasta_base = os.path.dirname(caminho_entrada) if "*" in caminho_entrada else caminho_entrada
        if os.path.isdir(pasta_base):
            subpastas = [d for d in os.listdir(pasta_base) if os.path.isdir(os.path.join(pasta_base, d))]
            if subpastas:
                caminho_entrada = os.path.join(pasta_base, "*", "*.parquet")

    caminho_saida = os.path.abspath(argumentos.output)
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)

    options = PipelineOptions(pipeline_args)

    print("=== RF25 - APACHE BEAM ===")
    print(f"Entrada resolvida: {caminho_entrada}")
    print(f"Saída resolvida:   {caminho_saida}")
    print()

    inicio = time.perf_counter()

    pipeline = beam.Pipeline(options=options)

    (
        pipeline
        | "Ler Parquet Silver"
        >> ReadFromParquet(
            file_pattern=caminho_entrada
        )
        | "Preparar agregacao"
        >> beam.Map(preparar_registro)
        | "Agrupar por conteudo"
        >> beam.CombinePerKey(
            SomarEstatisticas()
        )
        | "Montar resultado Gold"
        >> beam.Map(montar_saida)
        | "Gravar Parquet"
        >> WriteToParquet(
            file_path_prefix=caminho_saida,
            schema=SCHEMA_SAIDA,
            file_name_suffix=".parquet",
            num_shards=1,
        )
    )

    resultado = pipeline.run()
    resultado.wait_until_finish()

    duracao = time.perf_counter() - inicio

    print()
    print("Pipeline concluído com sucesso.")
    print(f"Tempo total: {duracao:.6f} s")


if __name__ == "__main__":
    main()
