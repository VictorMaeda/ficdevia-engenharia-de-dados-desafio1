"""
Módulo de geração, armazenamento e busca por similaridade semântica
(RF08 e RF09).

Modelo utilizado:
- sentence-transformers/all-MiniLM-L6-v2
- dimensão: 384

Funcionalidades:
- geração de embeddings a partir de título + descrição do conteúdo;
- prevenção de reprocessamento de conteúdos já vetorizados;
- persistência no PostgreSQL utilizando pgvector;
- busca por similaridade semântica em linguagem natural;
- quantidade configurável de resultados.
"""

from __future__ import annotations

import logging
from typing import Any

from sentence_transformers import SentenceTransformer

from src.config import carregar_configuracao
from src.logger import configurar_logger
from src.persistencia.postgres_repo import RepositorioPostgres


NOME_MODELO_PADRAO = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSAO_EMBEDDING = 384


class GeradorEmbeddings:
    """Responsável pelo carregamento do modelo e vetorização dos textos."""

    def __init__(self, nome_modelo: str = NOME_MODELO_PADRAO):
        self.nome_modelo = nome_modelo
        self._modelo = SentenceTransformer(self.nome_modelo)

        dimensao_modelo = self._modelo.get_embedding_dimension()

        if dimensao_modelo != DIMENSAO_EMBEDDING:
            raise ValueError(
                f"Dimensão inesperada para o modelo {self.nome_modelo}: "
                f"esperado={DIMENSAO_EMBEDDING}, obtido={dimensao_modelo}"
            )

    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera um embedding de 384 dimensões para o texto informado."""

        if not texto or not texto.strip():
            texto = " "

        vetor = self._modelo.encode(texto, convert_to_numpy=True)

        return [float(valor) for valor in vetor]

    def gerar_embeddings_em_lote(
        self,
        textos: list[str],
    ) -> list[list[float]]:
        """Gera embeddings em lote."""

        vetores = self._modelo.encode(
            textos,
            convert_to_numpy=True,
        )

        return [
            [float(valor) for valor in vetor]
            for vetor in vetores
        ]


def gerar_e_persistir_embeddings_conteudos(
    logger: logging.Logger | None = None,
    gerador: GeradorEmbeddings | None = None,
) -> int:
    """
    Gera e persiste os embeddings para conteúdos que ainda não
    possuem vetores no PostgreSQL.

    O texto utilizado é formado por:
        título + descrição

    Evita a geração duplicada de embeddings para o mesmo conteúdo.
    """

    config = carregar_configuracao()

    if logger is None:
        logger = configurar_logger(
            arquivo_log=config.arquivo_log,
            nivel=config.nivel_log,
        )

    logger.info(
        "Iniciando geração de embeddings com o modelo %s.",
        NOME_MODELO_PADRAO,
    )

    if gerador is None:
        gerador = GeradorEmbeddings()

    with RepositorioPostgres(config.postgres, logger) as repo:
        conteudos = repo.obter_conteudos_com_detalhes()
        ids_com_embeddings = repo.obter_ids_com_embeddings()

        pendentes = [
            conteudo
            for conteudo in conteudos
            if conteudo["conteudo_id"] not in ids_com_embeddings
        ]

        if not pendentes:
            logger.info(
                "Todos os %d conteúdos já possuem embeddings. "
                "Nenhuma inserção necessária.",
                len(conteudos),
            )
            return 0

        logger.info(
            "Identificados %d conteúdos pendentes de embedding "
            "(total no catálogo: %d).",
            len(pendentes),
            len(conteudos),
        )

        textos = [
            f"{conteudo['titulo']}. {conteudo['descricao']}"
            for conteudo in pendentes
        ]

        vetores = gerador.gerar_embeddings_em_lote(textos)

        registros = []

        for conteudo, vetor in zip(pendentes, vetores):
            registros.append(
                {
                    "conteudo_id": conteudo["conteudo_id"],
                    "modelo": gerador.nome_modelo,
                    "embedding": vetor,
                }
            )

        total_salvo = repo.carregar_embeddings(registros)

        logger.info(
            "Geração e persistência de %d embeddings concluídas "
            "com sucesso utilizando %s.",
            total_salvo,
            gerador.nome_modelo,
        )

        return total_salvo


def buscar_similaridade_semantica(
    query_texto: str,
    top_n: int = 5,
    logger: logging.Logger | None = None,
    gerador: GeradorEmbeddings | None = None,
) -> list[dict[str, Any]]:
    """
    Executa uma busca semântica em linguagem natural.

    O parâmetro top_n permite configurar a quantidade de
    resultados retornados.
    """

    config = carregar_configuracao()

    if logger is None:
        logger = configurar_logger(
            arquivo_log=config.arquivo_log,
            nivel=config.nivel_log,
        )

    if gerador is None:
        gerador = GeradorEmbeddings()

    vetor_query = gerador.gerar_embedding(query_texto)

    with RepositorioPostgres(config.postgres, logger) as repo:
        return repo.buscar_conteudos_por_similaridade(
            vetor_query,
            top_n=top_n,
        )


def exibir_demonstracao_buscas() -> None:
    """Executa três consultas semânticas para demonstração do RF09."""

    print("\n" + "=" * 110)
    print(" DEMONSTRAÇÃO DE BUSCA SEMÂNTICA EM LINGUAGEM NATURAL (RF09)")
    print(" Modelo utilizado:", NOME_MODELO_PADRAO)
    print("=" * 110)

    consultas = [
        "Quero aprender os fundamentos de banco de dados para inteligência artificial.",
        "Quero entender pipelines de dados, ETL e ferramentas de ingestão.",
        "Procurando conteúdos introdutórios sobre redes neurais e deep learning.",
    ]

    gerador = GeradorEmbeddings()

    for indice, consulta in enumerate(consultas, start=1):
        print(f'\n--- Consulta #{indice}: "{consulta}" ---')

        resultados = buscar_similaridade_semantica(
            query_texto=consulta,
            top_n=5,
            gerador=gerador,
        )

        print(
            f"{'POS':<4} | "
            f"{'ID':<6} | "
            f"{'SIMILARIDADE':<12} | "
            f"{'CATEGORIA':<25} | "
            f"{'TIPO':<10} | "
            f"TÍTULO"
        )

        print("-" * 110)

        for resultado in resultados:
            similaridade = f"{resultado['similaridade']:.4f}"

            print(
                f"{resultado['posicao']:<4} | "
                f"{resultado['conteudo_id']:<6} | "
                f"{similaridade:<12} | "
                f"{resultado['categoria'][:25]:<25} | "
                f"{resultado['tipo'][:10]:<10} | "
                f"{resultado['titulo']}"
            )

    print("\n" + "=" * 110 + "\n")


if __name__ == "__main__":
    gerar_e_persistir_embeddings_conteudos()
    exibir_demonstracao_buscas()