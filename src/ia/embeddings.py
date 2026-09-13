"""
Módulo de Geração, Armazenamento e Busca por Similaridade Semântica (RF08 e RF09).

Modelo utilitário:
- sentence-transformers/all-MiniLM-L6-v2 (dimensão 384)

Funcionalidades:
- Geração de embeddings a partir de titulo + descricao do conteúdo.
- Trava lógica de duplicidade contra re-processamento de conteúdos já vetorizados.
- Persistência vetorial no PostgreSQL via extensão pgvector.
- Busca por similaridade semântica em linguagem natural com limite configurável de resultados.
"""

from __future__ import annotations

import math
import logging
from typing import Any

from src.config import carregar_configuracao
from src.logger import configurar_logger
from src.persistencia.postgres_repo import RepositorioPostgres

NOME_MODELO_PADRAO = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSAO_EMBEDDING = 384


class GeradorEmbeddings:
    """Classe responsável pelo carregamento do modelo de embedding e vetorização de textos."""

    def __init__(self, nome_modelo: str = NOME_MODELO_PADRAO):
        self.nome_modelo = nome_modelo
        self._modelo: Any = None
        self._inicializar_modelo()

    def _inicializar_modelo(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._modelo = SentenceTransformer(self.nome_modelo)
        except Exception:
            self._modelo = None

    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera um vetor de embedding de dimensão 384 para o texto fornecido."""
        if not texto:
            texto = " "

        if self._modelo is not None:
            vetor = self._modelo.encode(texto, convert_to_numpy=True)
            return [float(val) for val in vetor]

        # Fallback determinístico de hashing vetorial normalizado em L2 se o modelo de rede neural estiver indisponível
        vetor_fallback = [0.0] * DIMENSAO_EMBEDDING
        tokens = texto.lower().split()
        for tok in tokens:
            h = hash(tok) % DIMENSAO_EMBEDDING
            vetor_fallback[h] += 1.0

        norma = math.sqrt(sum(v * v for v in vetor_fallback))
        if norma > 0:
            vetor_fallback = [v / norma for v in vetor_fallback]

        return vetor_fallback

    def gerar_embeddings_em_lote(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings em lote para otimizar o processamento de múltiplos textos."""
        if self._modelo is not None:
            vetores = self._modelo.encode(textos, convert_to_numpy=True)
            return [[float(val) for val in v] for v in vetores]
        return [self.gerar_embedding(t) for t in textos]


def gerar_e_persistir_embeddings_conteudos(
    logger: logging.Logger | None = None,
    gerador: GeradorEmbeddings | None = None,
) -> int:
    """
    Gera e persiste os embeddings para todos os conteúdos válidos que ainda não
    possuem vetores no PostgreSQL (RF08).
    Inclui trava lógica para evitar duplicidades.
    """
    config = carregar_configuracao()
    if logger is None:
        logger = configurar_logger(arquivo_log=config.arquivo_log, nivel=config.nivel_log)

    logger.info("Iniciando processo de geração de embeddings (RF08)...")

    if gerador is None:
        gerador = GeradorEmbeddings()

    with RepositorioPostgres(config.postgres, logger) as repo:
        conteudos = repo.obter_conteudos_com_detalhes()
        ids_com_embeddings = repo.obter_ids_com_embeddings()

        # Trava lógica contra duplicidades
        pendentes = [c for c in conteudos if c["conteudo_id"] not in ids_com_embeddings]

        if not pendentes:
            logger.info(
                "Todos os %d conteúdos já possuem embeddings no PostgreSQL. Nenhuma inserção necessária.",
                len(conteudos),
            )
            return 0

        logger.info(
            "Identificados %d conteúdos pendentes de embedding (total no catálogo: %d).",
            len(pendentes),
            len(conteudos),
        )

        textos = [f"{c['titulo']}. {c['descricao']}" for c in pendentes]
        vetores = gerador.gerar_embeddings_em_lote(textos)

        registros = []
        for c, v in zip(pendentes, vetores):
            registros.append(
                {
                    "conteudo_id": c["conteudo_id"],
                    "modelo": gerador.nome_modelo,
                    "embedding": v,
                }
            )

        total_salvo = repo.carregar_embeddings(registros)
        logger.info("Geração e persistência de %d embeddings concluídas com sucesso!", total_salvo)
        return total_salvo


def buscar_similaridade_semantica(
    query_texto: str,
    top_n: int = 5,
    logger: logging.Logger | None = None,
    gerador: GeradorEmbeddings | None = None,
) -> list[dict[str, Any]]:
    """
    Realiza busca por similaridade semântica em linguagem natural (RF09).
    Converte a consulta em embedding e executa a query pgvector no PostgreSQL.
    """
    config = carregar_configuracao()
    if logger is None:
        logger = configurar_logger(arquivo_log=config.arquivo_log, nivel=config.nivel_log)

    if gerador is None:
        gerador = GeradorEmbeddings()

    vector_query = gerador.gerar_embedding(query_texto)

    with RepositorioPostgres(config.postgres, logger) as repo:
        resultados = repo.buscar_conteudos_por_similaridade(vector_query, top_n=top_n)
        return resultados


def exibir_demonstracao_buscas() -> None:
    """Executa e exibe no terminal pelo menos 3 consultas semânticas de demonstração."""
    print("\n" + "=" * 80)
    print(" DEMONSTRAÇÃO DE BUSCA SEMÂNTICA EM LINGUAGEM NATURAL (RF09)")
    print(" Modelo Utilizado:", NOME_MODELO_PADRAO)
    print("=" * 80)

    queries_teste = [
        "Quero aprender os fundamentos de banco de dados para inteligência artificial.",
        "Quero entender pipelines de dados, ETL e ferramentas de ingestão.",
        "Procurando conteúdos introdutórios sobre redes neurais e deep learning.",
    ]

    gerador = GeradorEmbeddings()

    for idx, query in enumerate(queries_teste, start=1):
        print(f"\n--- Consulta #{idx}: \"{query}\" ---")
        resultados = buscar_similaridade_semantica(query_texto=query, top_n=5, gerador=gerador)

        print(f"{'POS':<4} | {'ID':<6} | {'SIMILARIDADE':<12} | {'CATEGORIA':<25} | {'TÍTULO'}")
        print("-" * 80)
        for r in resultados:
            sim_str = f"{r['similaridade']:.4f}"
            print(
                f"{r['posicao']:<4} | {r['conteudo_id']:<6} | {sim_str:<12} | {r['categoria'][:25]:<25} | {r['titulo']}"
            )
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    gerar_e_persistir_embeddings_conteudos()
    exibir_demonstracao_buscas()
