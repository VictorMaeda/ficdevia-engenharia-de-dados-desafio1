"""
Persistência no MongoDB (RF07).

Cada documento de comentário/avaliação mantém a identificação do
usuário e do conteúdo aos quais está relacionado. Para permitir a
agregação por categoria diretamente no MongoDB (sem precisar consultar
o PostgreSQL a cada consulta), o documento é enriquecido com o campo
"categoria" no momento da carga (denormalização deliberada — decisão
registrada em documentacao/modelo_de_dados.md).

A coleção oferece, no mínimo:
- inserir documentos;
- consultar comentários de determinado conteúdo;
- localizar documentos por tag;
- filtrar avaliações pela nota;
- agregar a quantidade de comentários/avaliações por categoria.
"""

from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config import ConfigMongo


class RepositorioMongo:
    def __init__(self, config: ConfigMongo, logger: logging.Logger):
        self._config = config
        self._logger = logger
        self._cliente: MongoClient | None = None

    # ------------------------------------------------------------
    # Conexão e índices
    # ------------------------------------------------------------

    def conectar(self) -> None:
        try:
            self._cliente = MongoClient(self._config.uri(), serverSelectionTimeoutMS=5000)
            # Força a validação da conexão (levanta exceção se o servidor não responder).
            self._cliente.admin.command("ping")
            self._logger.info(
                "Conectado ao MongoDB em %s:%s/%s",
                self._config.host,
                self._config.porta,
                self._config.banco,
            )
        except PyMongoError as erro:
            self._logger.error("Falha ao conectar ao MongoDB: %s", erro)
            raise

    def fechar(self) -> None:
        if self._cliente is not None:
            self._cliente.close()
            self._logger.info("Conexao com o MongoDB encerrada.")

    def __enter__(self) -> "RepositorioMongo":
        self.conectar()
        if self._config.aplicar_indices_ao_iniciar:
            self.criar_indices()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.fechar()

    @property
    def _colecao(self) -> Collection:
        assert self._cliente is not None
        return self._cliente[self._config.banco][self._config.colecao_comentarios]

    def criar_indices(self) -> None:
        colecao = self._colecao
        # Evita duplicidade quando o pipeline é executado mais de uma vez.
        colecao.create_index(
            [("usuario_id", ASCENDING), ("conteudo_id", ASCENDING), ("data", ASCENDING)],
            unique=True,
            name="uniq_usuario_conteudo_data",
        )
        colecao.create_index([("conteudo_id", ASCENDING)], name="idx_conteudo_id")
        colecao.create_index([("tags", ASCENDING)], name="idx_tags")
        colecao.create_index([("avaliacao", ASCENDING)], name="idx_avaliacao")
        colecao.create_index([("categoria", ASCENDING)], name="idx_categoria")
        self._logger.info("Indices do MongoDB verificados/criados.")

    # ------------------------------------------------------------
    # Inserção (RF07 - inserir documentos)
    # ------------------------------------------------------------

    def inserir_documentos(self, documentos: list[dict[str, Any]]) -> int:
        """Insere os documentos, ignorando duplicados (mesma chave usuario+conteudo+data)."""
        if not documentos:
            return 0

        inseridos = 0
        try:
            for documento in documentos:
                resultado = self._colecao.update_one(
                    {
                        "usuario_id": documento["usuario_id"],
                        "conteudo_id": documento["conteudo_id"],
                        "data": documento.get("data"),
                    },
                    {"$setOnInsert": documento},
                    upsert=True,
                )
                if resultado.upserted_id is not None:
                    inseridos += 1
            self._logger.info(
                "Documentos processados no MongoDB: %d (novos: %d, ja existentes: %d)",
                len(documentos),
                inseridos,
                len(documentos) - inseridos,
            )
            return inseridos
        except PyMongoError as erro:
            self._logger.error("Falha ao inserir documentos no MongoDB: %s", erro)
            raise

    # ------------------------------------------------------------
    # Consultas (RF07)
    # ------------------------------------------------------------

    def consultar_comentarios_por_conteudo(self, conteudo_id: int) -> list[dict[str, Any]]:
        """Consulta comentários de determinado conteúdo."""
        cursor = self._colecao.find({"conteudo_id": conteudo_id}, {"_id": 0})
        return list(cursor)

    def localizar_por_tag(self, tag: str) -> list[dict[str, Any]]:
        """Localiza documentos que contenham a tag informada."""
        cursor = self._colecao.find({"tags": tag}, {"_id": 0})
        return list(cursor)

    def filtrar_por_nota(self, nota_min: int, nota_max: int | None = None) -> list[dict[str, Any]]:
        """Filtra avaliações pela nota (intervalo fechado [nota_min, nota_max])."""
        filtro: dict[str, Any] = {"avaliacao": {"$gte": nota_min}}
        if nota_max is not None:
            filtro["avaliacao"]["$lte"] = nota_max
        cursor = self._colecao.find(filtro, {"_id": 0})
        return list(cursor)

    def agregar_quantidade_por_categoria(self) -> list[dict[str, Any]]:
        """Agrega a quantidade de comentários/avaliações por categoria."""
        pipeline = [
            {"$group": {"_id": "$categoria", "quantidade": {"$sum": 1}}},
            {"$sort": {"quantidade": -1}},
            {"$project": {"_id": 0, "categoria": "$_id", "quantidade": 1}},
        ]
        return list(self._colecao.aggregate(pipeline))

    def contar_documentos(self) -> int:
        return self._colecao.count_documents({})
