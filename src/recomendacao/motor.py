"""
Motor de Recomendação de Conteúdos (RF10 e RF11).

Este módulo calcula recomendações personalizadas para usuários com base no histórico de
interações e avaliações, aplicando a fórmula exigida pelo edital:

    Pontuação = ((Ivis + Icur) / 2) * 100 * Iconc

Onde:
- Ivis (Índice de Visualizações): variando de 0.0 a 1.0, calculado via proporção de
  tempo consumido na mesma categoria (ou similaridade vetorial via pgvector, se disponível).
- Icur (Índice de Curtidas e Avaliações): variando de 0.0 a 1.0, baseado no histórico
  de curtidas ou avaliações positivas (nota >= 4).
- Iconc (Índice de Remoção de Concluídos): filtro binário (0 se concluído, 1 caso contrário).

Classificação:
- Positivo: Pontuação >= 70
- Estável: 40 <= Pontuação < 70
- Negativo: Pontuação <= 40 ou Iconc = 0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.config import carregar_configuracao
from src.logger import configurar_logger
from src.persistencia.postgres_repo import RepositorioPostgres


class MotorRecomendacao:
    """Classe responsável pelo cálculo das métricas e geração de recomendações."""

    def __init__(
        self,
        conteudos: list[dict[str, Any]],
        interacoes: list[dict[str, Any]],
        avaliacoes_resumo: list[dict[str, Any]] | None = None,
    ):
        self.conteudos = conteudos
        self.interacoes = interacoes
        self.avaliacoes_resumo = avaliacoes_resumo or []

        self._preparar_estruturas()

    def _preparar_estruturas(self) -> None:
        """Organiza os dados em estruturas em memória para cálculo rápido dos índices."""
        # Mapeamento de conteúdo -> categoria_id
        self.conteudo_categoria: dict[int, int] = {
            c["conteudo_id"]: c["categoria_id"] for c in self.conteudos
        }

        # Conjunto de (usuario_id, conteudo_id) concluídos
        self.concluidos: set[tuple[int, int]] = set()

        # Tempo consumido por usuario_id e categoria_id: {usuario_id: {categoria_id: tempo_total}}
        self.tempo_por_usuario_cat: dict[int, dict[int, float]] = {}
        # Tempo total consumido por usuario_id
        self.tempo_total_usuario: dict[int, float] = {}

        # Interações positivas (curtidas ou avaliações >= 4) por usuario_id e categoria_id
        self.positos_por_usuario_cat: dict[int, dict[int, int]] = {}
        self.positivos_total_usuario: dict[int, int] = {}

        for i in self.interacoes:
            uid = i["usuario_id"]
            cid = i["conteudo_id"]
            cat_id = i.get("categoria_id") or self.conteudo_categoria.get(cid)

            # Verificar se foi concluído
            perc = i.get("percentual_conclusao") or 0.0
            tipo = i.get("tipo_interacao")
            if tipo == "conclusao" or perc >= 100.0:
                self.concluidos.add((uid, cid))

            # Tempo consumido
            tempo = i.get("tempo_consumido_min") or 0.0
            if cat_id is not None:
                self.tempo_por_usuario_cat.setdefault(uid, {}).setdefault(cat_id, 0.0)
                self.tempo_por_usuario_cat[uid][cat_id] += tempo
            self.tempo_total_usuario[uid] = self.tempo_total_usuario.get(uid, 0.0) + tempo

            # Curtidas / Avaliações positivas nas interações
            aval = i.get("avaliacao")
            eh_positivo = tipo == "curtida" or (aval is not None and aval >= 4)
            if eh_positivo and cat_id is not None:
                self.positos_por_usuario_cat.setdefault(uid, {}).setdefault(cat_id, 0)
                self.positos_por_usuario_cat[uid][cat_id] += 1
                self.positivos_total_usuario[uid] = self.positivos_total_usuario.get(uid, 0) + 1

        # Processar também avaliações em avaliacoes_resumo (se nota >= 4)
        for a in self.avaliacoes_resumo:
            uid = a["usuario_id"]
            cid = a["conteudo_id"]
            nota = a.get("nota") or 0
            cat_id = self.conteudo_categoria.get(cid)

            if nota >= 4 and cat_id is not None:
                self.positos_por_usuario_cat.setdefault(uid, {}).setdefault(cat_id, 0)
                self.positos_por_usuario_cat[uid][cat_id] += 1
                self.positivos_total_usuario[uid] = self.positivos_total_usuario.get(uid, 0) + 1

    def calcular_ivis(self, usuario_id: int, conteudo_id: int) -> float:
        """
        Calcula o Índice de Visualizações (Ivis), variando de 0.0 a 1.0.
        Proporção do tempo consumido pelo usuário na mesma categoria do conteúdo.
        """
        cat_id = self.conteudo_categoria.get(conteudo_id)
        if cat_id is None:
            return 0.0

        tempo_total = self.tempo_total_usuario.get(usuario_id, 0.0)
        if tempo_total <= 0:
            return 0.0

        tempo_cat = self.tempo_por_usuario_cat.get(usuario_id, {}).get(cat_id, 0.0)
        ivis = tempo_cat / tempo_total
        return min(max(ivis, 0.0), 1.0)

    def calcular_icur(self, usuario_id: int, conteudo_id: int) -> float:
        """
        Calcula o Índice de Curtidas e Avaliações (Icur), variando de 0.0 a 1.0.
        Baseado na proporção de histórico positivo (curtidas ou nota >= 4) na mesma categoria.
        """
        cat_id = self.conteudo_categoria.get(conteudo_id)
        if cat_id is None:
            return 0.0

        pos_total = self.positivos_total_usuario.get(usuario_id, 0)
        if pos_total <= 0:
            return 0.0

        pos_cat = self.positos_por_usuario_cat.get(usuario_id, {}).get(cat_id, 0)
        icur = pos_cat / float(pos_total)
        return min(max(icur, 0.0), 1.0)

    def calcular_iconc(self, usuario_id: int, conteudo_id: int) -> int:
        """
        Calcula o Índice de Remoção de Concluídos (Iconc).
        Retorna 0 se o usuário já concluiu o conteúdo e 1 caso contrário.
        """
        if (usuario_id, conteudo_id) in self.concluidos:
            return 0
        return 1

    def calcular_pontuacao(self, ivis: float, icur: float, iconc: int) -> float:
        """
        Aplica a fórmula obrigatória:
        Pontuação = ((Ivis + Icur)/2) * 100 * Iconc
        """
        if iconc == 0:
            return 0.0

        media_indices = (ivis + icur) / 2.0
        pontuacao = media_indices * 100.0 * iconc
        return round(min(max(pontuacao, 0.0), 100.0), 2)

    def classificar_status(self, pontuacao: float, iconc: int) -> str:
        """
        Classifica as recomendações com base na pontuação e iconc:
        - Positivo (Pontuação >= 70)
        - Estável (40 <= Pontuação < 70)
        - Negativo (Pontuação <= 40 ou Iconc = 0)
        """
        if iconc == 0 or pontuacao <= 40.0:
            return "negativo"
        elif 40.0 <= pontuacao < 70.0:
            return "estavel"
        else:
            return "positivo"

    def gerar_recomendacoes_usuario(
        self, usuario_id: int, data_geracao: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Gera a lista ordenada de recomendações pontuadas para um único usuário."""
        agora = data_geracao or datetime.now()
        itens: list[dict[str, Any]] = []

        for c in self.conteudos:
            cid = c["conteudo_id"]
            ivis = self.calcular_ivis(usuario_id, cid)
            icur = self.calcular_icur(usuario_id, cid)
            iconc = self.calcular_iconc(usuario_id, cid)

            pontuacao = self.calcular_pontuacao(ivis, icur, iconc)
            status = self.classificar_status(pontuacao, iconc)

            itens.append(
                {
                    "usuario_id": usuario_id,
                    "conteudo_id": cid,
                    "pontuacao": pontuacao,
                    "status": status,
                    "data_geracao": agora,
                }
            )

        # Ordenar por pontuação decrescente, e conteudo_id crescente em caso de empate
        itens.sort(key=lambda x: (-x["pontuacao"], x["conteudo_id"]))

        # Atribuir a posição
        for pos, item in enumerate(itens, start=1):
            item["posicao"] = pos

        return itens

    def gerar_todas_recomendacoes(
        self, usuarios_ids: list[int], data_geracao: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Gera recomendações para todos os usuários fornecidos."""
        todas: list[dict[str, Any]] = []
        agora = data_geracao or datetime.now()
        for uid in usuarios_ids:
            recs = self.gerar_recomendacoes_usuario(uid, data_geracao=agora)
            todas.extend(recs)
        return todas


def gerar_e_persistir_recomendacoes(logger: logging.Logger | None = None) -> int:
    """Função utilitária para executar o motor e salvar todas as recomendações no PostgreSQL."""
    config = carregar_configuracao()
    if logger is None:
        logger = configurar_logger(arquivo_log=config.arquivo_log, nivel=config.nivel_log)

    logger.info("Iniciando geração e persistência das recomendações (RF10/RF11)...")

    with RepositorioPostgres(config.postgres, logger) as repo:
        usuarios_ids = repo.obter_todos_usuarios_ids()
        conteudos = repo.obter_todos_conteudos()
        interacoes = repo.obter_interacoes_todas()
        avaliacoes = repo.obter_avaliacoes_resumo_todas()

        logger.info(
            "Carregados do PostgreSQL: %d usuários, %d conteúdos, %d interações",
            len(usuarios_ids),
            len(conteudos),
            len(interacoes),
        )

        motor = MotorRecomendacao(conteudos, interacoes, avaliacoes)
        todas_recs = motor.gerar_todas_recomendacoes(usuarios_ids)

        total_salvo = repo.carregar_recomendacoes(todas_recs)
        logger.info(
            "Persistidas %d recomendações no PostgreSQL com sucesso!", total_salvo
        )
        return total_salvo


if __name__ == "__main__":
    gerar_e_persistir_recomendacoes()
