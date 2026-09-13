"""
Ponto de entrada único e orquestração do pipeline completo.

Execução:
    python -m src.main

Etapas orquestradas:
    1. leitura das fontes (CSV + JSON) (RF02);
    2. validação dos registros
       (válido/inválido/incompleto/duplicado) (RF03);
    3. tratamento e padronização dos registros válidos (RF04);
    4. gravação dos dados tratados e rejeitados em dados/processados/ (RF04);
    5. persistência no PostgreSQL (schema + carga transacional) (RF06);
    6. persistência no MongoDB dos comentários/avaliações (RF07);
    7. motor de recomendação personalizada e pontuação
       Ivis/Icur/Iconc (RF10);
    8. persistência das recomendações no PostgreSQL (RF11);
    9. geração e armazenamento vetorial de embeddings 384D
       utilizando pgvector (RF08);
    10. demonstração de busca por similaridade semântica
        em linguagem natural (RF09);
    11. geração do resumo da ingestão (RF05);
    12. registro dos tempos das principais etapas e falhas (RF14).
"""

from __future__ import annotations

import sys
import time

from src.config import carregar_configuracao
from src.logger import configurar_logger
from src.leitura.leitores import ler_todas_as_fontes
from src.validacao.validadores import (
    validar_catalogo,
    validar_comentarios,
    validar_interacoes,
)
from src.tratamento.limpeza import (
    tratar_catalogo,
    tratar_comentarios,
    tratar_interacoes,
)
from src.saida.escritores import (
    gravar_csv,
    gravar_json,
    separar_validos_e_rejeitados,
)
from src.resumo.resumo_ingestao import (
    ResumoIngestao,
    gravar_resumo,
    montar_resumo_fonte,
)
from src.persistencia.postgres_repo import RepositorioPostgres
from src.persistencia.mongo_repo import RepositorioMongo
from src.recomendacao.motor import gerar_e_persistir_recomendacoes
from src.ia.embeddings import (
    gerar_e_persistir_embeddings_conteudos,
    exibir_demonstracao_buscas,
)


def _contar_diferencas(
    brutos: list[dict],
    tratados: list[dict],
) -> int:
    """
    Conta quantos registros tiveram ao menos um campo alterado
    pelo tratamento (RF04).
    """
    corrigidos = 0

    for bruto, tratado in zip(brutos, tratados):
        for chave, valor_tratado in tratado.items():
            valor_bruto = bruto.get(chave)

            if (
                valor_bruto is not None
                and str(valor_bruto).strip() != str(valor_tratado)
            ):
                corrigidos += 1
                break

    return corrigidos


def gravar_recomendacao(recomendacao: dict) -> None:
    """
    Permite persistir uma recomendação individual sem substituir
    as recomendações já existentes.
    """
    config = carregar_configuracao()

    logger = configurar_logger(
        arquivo_log=config.arquivo_log,
        nivel=config.nivel_log,
    )

    with RepositorioPostgres(config.postgres, logger) as repo:
        repo.carregar_recomendacoes([recomendacao])


def executar() -> int:
    inicio = time.perf_counter()

    config = carregar_configuracao()

    logger = configurar_logger(
        arquivo_log=config.arquivo_log,
        nivel=config.nivel_log,
    )

    logger.info("=" * 60)
    logger.info("INICIO DO PROCESSAMENTO - Pipeline Desafio 1")
    logger.info("=" * 60)

    resumo = ResumoIngestao()

    try:
        # ============================================================
        # 1) Leitura das fontes (RF02)
        # ============================================================

        inicio_etapa = time.perf_counter()

        brutos = ler_todas_as_fontes(
            config.caminho_catalogo_csv,
            config.caminho_interacoes_json,
            config.caminho_comentarios_json,
            logger,
        )

        logger.info(
            "Tempo da etapa de leitura: %.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 2) Validação (RF03)
        # ============================================================

        inicio_etapa = time.perf_counter()

        resultados_catalogo = validar_catalogo(
            brutos["catalogo"],
            config.validacao,
        )

        ids_conteudo_validos = {
            str(r.registro["conteudo_id"]).strip()
            for r in resultados_catalogo
            if r.status == "valido"
        }

        resultados_interacoes = validar_interacoes(
            brutos["interacoes"],
            config.validacao,
            ids_conteudo_validos,
        )

        resultados_comentarios = validar_comentarios(
            brutos["comentarios"],
            config.validacao,
            ids_conteudo_validos,
        )

        logger.info(
            "Tempo da etapa de validacao: %.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 3) Separação de válidos/rejeitados
        # 4) Tratamento e padronização (RF03/RF04)
        # ============================================================

        inicio_etapa = time.perf_counter()

        catalogo_validos, catalogo_rejeitados = (
            separar_validos_e_rejeitados(resultados_catalogo)
        )

        interacoes_validas, interacoes_rejeitadas = (
            separar_validos_e_rejeitados(resultados_interacoes)
        )

        comentarios_validos, comentarios_rejeitados = (
            separar_validos_e_rejeitados(resultados_comentarios)
        )

        gravar_json(
            catalogo_rejeitados,
            config.arquivo_rejeitados_catalogo,
            logger,
        )

        gravar_json(
            interacoes_rejeitadas,
            config.arquivo_rejeitados_interacoes,
            logger,
        )

        gravar_json(
            comentarios_rejeitados,
            config.arquivo_rejeitados_comentarios,
            logger,
        )

        catalogo_tratado = tratar_catalogo(catalogo_validos)
        interacoes_tratadas = tratar_interacoes(interacoes_validas)
        comentarios_tratados = tratar_comentarios(comentarios_validos)

        gravar_csv(
            catalogo_tratado,
            config.catalogo_tratado,
            logger,
        )

        gravar_json(
            interacoes_tratadas,
            config.interacoes_tratadas,
            logger,
        )

        gravar_json(
            comentarios_tratados,
            config.comentarios_tratados,
            logger,
        )

        corrigidos_catalogo = _contar_diferencas(
            catalogo_validos,
            catalogo_tratado,
        )

        corrigidos_interacoes = _contar_diferencas(
            interacoes_validas,
            interacoes_tratadas,
        )

        corrigidos_comentarios = _contar_diferencas(
            comentarios_validos,
            comentarios_tratados,
        )

        logger.info(
            "Tempo da etapa de tratamento e gravacao dos processados: "
            "%.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 5) Preparação das entidades derivadas para PostgreSQL
        # ============================================================

        categorias = {
            c["categoria"]
            for c in catalogo_tratado
            if c.get("categoria")
        }

        usuarios_por_id: dict[int, dict] = {}

        for interacao in interacoes_tratadas:
            usuario_id = interacao["usuario_id"]

            if usuario_id is None:
                continue

            if usuario_id not in usuarios_por_id:
                usuarios_por_id[usuario_id] = {
                    "usuario_id": usuario_id,
                    "primeira_ocorrencia": interacao["data_hora"],
                    "origem_primeiro_registro": "interacao",
                }

        for comentario in comentarios_tratados:
            usuario_id = comentario["usuario_id"]

            if usuario_id is None:
                continue

            if usuario_id not in usuarios_por_id:
                usuarios_por_id[usuario_id] = {
                    "usuario_id": usuario_id,
                    "primeira_ocorrencia": comentario["data"],
                    "origem_primeiro_registro": "comentario",
                }

        usuarios = list(usuarios_por_id.values())

        carregados = {
            "usuarios": 0,
            "conteudos": 0,
            "interacoes": 0,
            "avaliacoes_resumo": 0,
            "mongo_comentarios": 0,
            "recomendacoes": 0,
            "embeddings": 0,
        }

        # ============================================================
        # 6) Persistência no PostgreSQL (RF06)
        # ============================================================

        inicio_etapa = time.perf_counter()

        try:
            with RepositorioPostgres(config.postgres, logger) as repo:
                repo.carregar_categorias(categorias)

                carregados["conteudos"] = repo.carregar_conteudos(
                    catalogo_tratado
                )

                carregados["usuarios"] = repo.carregar_usuarios(
                    usuarios
                )

                carregados["interacoes"] = repo.carregar_interacoes(
                    interacoes_tratadas
                )

                carregados["avaliacoes_resumo"] = (
                    repo.carregar_avaliacoes_resumo(
                        comentarios_tratados
                    )
                )

                contagens = repo.contar_registros_por_tabela()

                logger.info(
                    "Registros atualmente no PostgreSQL: %s",
                    contagens,
                )

        except Exception as erro:
            logger.error(
                "Falha na persistencia no PostgreSQL: %s",
                erro,
            )

            logger.warning(
                "Prosseguindo sem persistencia; "
                "dados tratados permanecem em %s",
                config.dir_processados,
            )

        logger.info(
            "Tempo da etapa PostgreSQL: %.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 6b) Persistência no MongoDB (RF07)
        # ============================================================

        inicio_etapa = time.perf_counter()

        categoria_por_conteudo = {
            c["conteudo_id"]: c.get("categoria")
            for c in catalogo_tratado
        }

        documentos_mongo = [
            {
                **comentario,
                "categoria": categoria_por_conteudo.get(
                    comentario["conteudo_id"]
                ),
            }
            for comentario in comentarios_tratados
        ]

        try:
            with RepositorioMongo(config.mongo, logger) as repo_mongo:
                carregados["mongo_comentarios"] = (
                    repo_mongo.inserir_documentos(
                        documentos_mongo
                    )
                )

                logger.info(
                    "Total de documentos na colecao MongoDB '%s': %d",
                    config.mongo.colecao_comentarios,
                    repo_mongo.contar_documentos(),
                )

        except Exception as erro:
            logger.error(
                "Falha na persistencia no MongoDB: %s",
                erro,
            )

            logger.warning(
                "Prosseguindo sem persistencia no MongoDB; "
                "dados tratados permanecem em %s",
                config.dir_processados,
            )

        logger.info(
            "Tempo da etapa MongoDB: %.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 7) Motor de recomendação (RF10/RF11)
        # ============================================================

        inicio_etapa = time.perf_counter()

        try:
            carregados["recomendacoes"] = (
                gerar_e_persistir_recomendacoes(logger)
            )

        except Exception as erro:
            logger.error(
                "Falha ao gerar e persistir recomendacoes: %s",
                erro,
            )

            carregados["recomendacoes"] = 0

        logger.info(
            "Tempo da etapa de recomendacoes: %.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 8) Embeddings e busca semântica (RF08/RF09)
        # ============================================================

        inicio_etapa = time.perf_counter()

        try:
            carregados["embeddings"] = (
                gerar_e_persistir_embeddings_conteudos(logger)
            )

            exibir_demonstracao_buscas()

        except Exception as erro:
            logger.error(
                "Falha na geracao ou busca de embeddings: %s",
                erro,
            )

            carregados["embeddings"] = 0

        logger.info(
            "Tempo da etapa de embeddings e busca semantica: "
            "%.3f segundos",
            time.perf_counter() - inicio_etapa,
        )

        # ============================================================
        # 9) Resumo da ingestão (RF05)
        # ============================================================

        resumo.fontes.append(
            montar_resumo_fonte(
                "catalogo.csv",
                resultados_catalogo,
                registros_corrigidos=corrigidos_catalogo,
                registros_carregados=carregados["conteudos"],
            )
        )

        resumo.fontes.append(
            montar_resumo_fonte(
                "interacoes.json",
                resultados_interacoes,
                registros_corrigidos=corrigidos_interacoes,
                registros_carregados=carregados["interacoes"],
            )
        )

        resumo.fontes.append(
            montar_resumo_fonte(
                "comentarios.json",
                resultados_comentarios,
                registros_corrigidos=corrigidos_comentarios,
                registros_carregados=(
                    carregados["avaliacoes_resumo"]
                    + carregados["mongo_comentarios"]
                ),
            )
        )

        resumo.tempo_total_segundos = (
            time.perf_counter() - inicio
        )

        resumo.carregados_por_banco = {
            "postgres": (
                carregados["conteudos"]
                + carregados["usuarios"]
                + carregados["interacoes"]
                + carregados["avaliacoes_resumo"]
                + carregados["recomendacoes"]
                + carregados["embeddings"]
            ),
            "mongodb": carregados["mongo_comentarios"],
        }

        gravar_resumo(
            resumo,
            config.arquivo_resumo,
            logger,
        )

        logger.info(
            "Tempo total do processamento: %.3f segundos",
            resumo.tempo_total_segundos,
        )

        logger.info("=" * 60)
        logger.info(
            "FIM DO PROCESSAMENTO - concluido com sucesso"
        )
        logger.info("=" * 60)

        return 0

    except Exception as erro:
        logger.exception(
            "Falha nao tratada durante o processamento: %s",
            erro,
        )

        logger.info(
            "Tempo transcorrido ate a falha: %.3f segundos",
            time.perf_counter() - inicio,
        )

        logger.info(
            "FIM DO PROCESSAMENTO - concluido com falha"
        )

        return 1


if __name__ == "__main__":
    sys.exit(executar())