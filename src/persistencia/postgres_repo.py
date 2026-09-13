"""
Persistência no PostgreSQL (RF06).

Responsável por:
- aplicar o schema (sql/criar_banco.sql), se configurado;
- carregar, dentro de transações, os dados tratados nas entidades
  usuario, conteudo, categoria, interacao (e avaliacoes_resumo);
- evitar duplicidade de identificadores (chaves primárias/únicas e
  ON CONFLICT DO NOTHING);
- manter a integridade dos relacionamentos (chaves estrangeiras);
- permitir consultar os registros armazenados.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

from src.config import ConfigPostgres


class RepositorioPostgres:
    def __init__(self, config: ConfigPostgres, logger: logging.Logger):
        self._config = config
        self._logger = logger
        self._conexao: psycopg2.extensions.connection | None = None

    # ------------------------------------------------------------
    # Conexão e schema
    # ------------------------------------------------------------

    def conectar(self) -> None:
        try:
            self._conexao = psycopg2.connect(
                host=self._config.host,
                port=self._config.porta,
                dbname=self._config.banco,
                user=self._config.usuario,
                password=self._config.senha,
            )
            self._logger.info(
                "Conectado ao PostgreSQL em %s:%s/%s",
                self._config.host,
                self._config.porta,
                self._config.banco,
            )
        except psycopg2.OperationalError as erro:
            self._logger.error("Falha ao conectar ao PostgreSQL: %s", erro)
            raise

    def fechar(self) -> None:
        if self._conexao is not None:
            self._conexao.close()
            self._logger.info("Conexao com o PostgreSQL encerrada.")

    def __enter__(self) -> "RepositorioPostgres":
        self.conectar()
        if self._config.aplicar_schema_ao_iniciar:
            self.aplicar_schema(self._config.script_schema)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.fechar()

    def aplicar_schema(self, caminho_script: Path) -> None:
        assert self._conexao is not None
        if not Path(caminho_script).exists():
            raise FileNotFoundError(f"Script de schema nao encontrado: {caminho_script}")

        with open(caminho_script, "r", encoding="utf-8") as f:
            sql_schema = f.read()

        with self._conexao.cursor() as cursor:
            cursor.execute(sql_schema)
        self._conexao.commit()
        self._logger.info("Schema aplicado a partir de %s", caminho_script)

    # ------------------------------------------------------------
    # Carga (RF06) - cada método roda em sua própria transação
    # ------------------------------------------------------------

    def carregar_categorias(self, categorias: set[str]) -> int:
        assert self._conexao is not None
        if not categorias:
            return 0
        try:
            with self._conexao.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    "INSERT INTO categorias (nome) VALUES %s ON CONFLICT (nome) DO NOTHING",
                    [(nome,) for nome in sorted(categorias)],
                )
            self._conexao.commit()
            self._logger.info("Categorias carregadas/atualizadas: %d", len(categorias))
            return len(categorias)
        except Exception as erro:
            self._conexao.rollback()
            self._logger.error("Falha ao carregar categorias: %s", erro)
            raise

    def carregar_usuarios(self, usuarios: list[dict[str, Any]]) -> int:
        """usuarios: lista de dicts com usuario_id, primeira_ocorrencia, origem_primeiro_registro."""
        assert self._conexao is not None
        if not usuarios:
            return 0
        try:
            with self._conexao.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO usuarios (usuario_id, primeira_ocorrencia, origem_primeiro_registro)
                    VALUES %s
                    ON CONFLICT (usuario_id) DO NOTHING
                    """,
                    [
                        (u["usuario_id"], u.get("primeira_ocorrencia"), u.get("origem_primeiro_registro"))
                        for u in usuarios
                    ],
                )
            self._conexao.commit()
            self._logger.info("Usuarios carregados/atualizados: %d", len(usuarios))
            return len(usuarios)
        except Exception as erro:
            self._conexao.rollback()
            self._logger.error("Falha ao carregar usuarios: %s", erro)
            raise

    def carregar_conteudos(self, conteudos: list[dict[str, Any]]) -> int:
        assert self._conexao is not None
        if not conteudos:
            return 0
        try:
            with self._conexao.cursor() as cursor:
                cursor.execute("SELECT categoria_id, nome FROM categorias")
                mapa_categorias = {nome: cid for cid, nome in cursor.fetchall()}

                valores = []
                for c in conteudos:
                    categoria_id = mapa_categorias.get(c["categoria"])
                    if categoria_id is None:
                        self._logger.warning(
                            "Categoria '%s' nao encontrada para conteudo_id=%s; registro ignorado",
                            c["categoria"],
                            c["conteudo_id"],
                        )
                        continue
                    valores.append(
                        (
                            c["conteudo_id"],
                            c["titulo"],
                            c["tipo"],
                            categoria_id,
                            c["nivel"],
                            c["carga_horaria_min"],
                            c["data_publicacao"],
                            c.get("descricao"),
                            c.get("autor"),
                        )
                    )

                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO conteudos
                        (conteudo_id, titulo, tipo, categoria_id, nivel,
                         carga_horaria_min, data_publicacao, descricao, autor)
                    VALUES %s
                    ON CONFLICT (conteudo_id) DO NOTHING
                    """,
                    valores,
                )
            self._conexao.commit()
            self._logger.info("Conteudos carregados/atualizados: %d", len(valores))
            return len(valores)
        except Exception as erro:
            self._conexao.rollback()
            self._logger.error("Falha ao carregar conteudos: %s", erro)
            raise

    def carregar_interacoes(self, interacoes: list[dict[str, Any]]) -> int:
        assert self._conexao is not None
        if not interacoes:
            return 0
        try:
            with self._conexao.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO interacoes
                        (usuario_id, conteudo_id, tipo_interacao, data_hora,
                         tempo_consumido_min, percentual_conclusao, avaliacao)
                    VALUES %s
                    ON CONFLICT (usuario_id, conteudo_id, tipo_interacao, data_hora) DO NOTHING
                    """,
                    [
                        (
                            i["usuario_id"],
                            i["conteudo_id"],
                            i["tipo_interacao"],
                            i["data_hora"],
                            i.get("tempo_consumido") or 0,
                            i.get("percentual_conclusao") or 0,
                            i.get("avaliacao_atribuida"),
                        )
                        for i in interacoes
                    ],
                )
            self._conexao.commit()
            self._logger.info("Interacoes carregadas/atualizadas: %d", len(interacoes))
            return len(interacoes)
        except Exception as erro:
            self._conexao.rollback()
            self._logger.error("Falha ao carregar interacoes: %s", erro)
            raise

    def carregar_avaliacoes_resumo(self, comentarios: list[dict[str, Any]]) -> int:
        assert self._conexao is not None
        if not comentarios:
            return 0
        try:
            with self._conexao.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO avaliacoes_resumo (usuario_id, conteudo_id, nota, data_avaliacao)
                    VALUES %s
                    ON CONFLICT (usuario_id, conteudo_id, data_avaliacao) DO NOTHING
                    """,
                    [
                        (c["usuario_id"], c["conteudo_id"], c["avaliacao"], c.get("data"))
                        for c in comentarios
                    ],
                )
            self._conexao.commit()
            self._logger.info("Avaliacoes (resumo) carregadas/atualizadas: %d", len(comentarios))
            return len(comentarios)
        except Exception as erro:
            self._conexao.rollback()
            self._logger.error("Falha ao carregar avaliacoes_resumo: %s", erro)
            raise

    # ------------------------------------------------------------
    # Consultas (RF06 - permitir consultar os registros armazenados)
    # ------------------------------------------------------------

    def contar_registros_por_tabela(self) -> dict[str, int]:
        assert self._conexao is not None
        tabelas = ["usuarios", "conteudos", "categorias", "interacoes", "avaliacoes_resumo", "recomendacoes"]
        contagens: dict[str, int] = {}
        with self._conexao.cursor() as cursor:
            for tabela in tabelas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                contagens[tabela] = cursor.fetchone()[0]
        return contagens

    def consultar_conteudos_por_categoria(self) -> list[tuple]:
        assert self._conexao is not None
        with self._conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.nome, COUNT(*)
                FROM conteudos co
                JOIN categorias c ON c.categoria_id = co.categoria_id
                GROUP BY c.nome
                ORDER BY COUNT(*) DESC
                """
            )
            return cursor.fetchall()
    def carregar_recomendacoes(self, recomendacoes: list[dict]) -> int:
        if not recomendacoes:
            return 0

        sql = """
            INSERT INTO recomendacoes (
                usuario_id,
                conteudo_id,
                pontuacao,
                posicao,
                status,
                data_geracao
            )
            VALUES (
                %(usuario_id)s,
                %(conteudo_id)s,
                %(pontuacao)s,
                %(posicao)s,
                %(status)s,
                COALESCE(%(data_geracao)s, NOW())
            )
            ON CONFLICT (usuario_id, conteudo_id, data_geracao) DO NOTHING
        """

        preparados = []
        for r in recomendacoes:
            preparados.append({
                "usuario_id": r["usuario_id"],
                "conteudo_id": r["conteudo_id"],
                "pontuacao": r["pontuacao"],
                "posicao": r["posicao"],
                "status": r["status"],
                "data_geracao": r.get("data_geracao"),
            })

        with self._conexao.cursor() as cursor:
            cursor.executemany(sql, preparados)

        self._conexao.commit()

        return len(recomendacoes)

    def obter_todos_usuarios_ids(self) -> list[int]:
        assert self._conexao is not None
        with self._conexao.cursor() as cursor:
            cursor.execute("SELECT usuario_id FROM usuarios ORDER BY usuario_id")
            return [row[0] for row in cursor.fetchall()]

    def obter_todos_conteudos(self) -> list[dict[str, Any]]:
        assert self._conexao is not None
        with self._conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.conteudo_id, c.categoria_id, cat.nome AS categoria_nome
                FROM conteudos c
                JOIN categorias cat ON c.categoria_id = cat.categoria_id
                ORDER BY c.conteudo_id
                """
            )
            return [
                {
                    "conteudo_id": row[0],
                    "categoria_id": row[1],
                    "categoria_nome": row[2],
                }
                for row in cursor.fetchall()
            ]

    def obter_interacoes_todas(self) -> list[dict[str, Any]]:
        assert self._conexao is not None
        with self._conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.usuario_id, i.conteudo_id, i.tipo_interacao,
                       i.tempo_consumido_min, i.percentual_conclusao, i.avaliacao,
                       c.categoria_id
                FROM interacoes i
                JOIN conteudos c ON i.conteudo_id = c.conteudo_id
                """
            )
            return [
                {
                    "usuario_id": row[0],
                    "conteudo_id": row[1],
                    "tipo_interacao": row[2],
                    "tempo_consumido_min": float(row[3]) if row[3] is not None else 0.0,
                    "percentual_conclusao": float(row[4]) if row[4] is not None else 0.0,
                    "avaliacao": row[5],
                    "categoria_id": row[6],
                }
                for row in cursor.fetchall()
            ]

    def obter_avaliacoes_resumo_todas(self) -> list[dict[str, Any]]:
        assert self._conexao is not None
        with self._conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT usuario_id, conteudo_id, nota
                FROM avaliacoes_resumo
                """
            )
            return [
                {
                    "usuario_id": row[0],
                    "conteudo_id": row[1],
                    "nota": row[2],
                }
                for row in cursor.fetchall()
            ]

