"""
Leitura das fontes de dados (RF02).

O sistema deve ler, no mínimo:
- um CSV com o catálogo de conteúdos;
- um JSON com as interações dos usuários;
- um JSON com comentários/avaliações.

Cada função retorna uma lista de dicionários (um por registro) e informa,
via logger, o nome do arquivo e a quantidade de registros encontrados.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any


def _logar_leitura(logger: logging.Logger, caminho: Path, quantidade: int) -> None:
    logger.info("Fonte lida: %s | registros encontrados: %d", caminho.name, quantidade)


def ler_catalogo_csv(caminho: Path, logger: logging.Logger) -> list[dict[str, Any]]:
    """Lê o catálogo de conteúdos (CSV) e retorna uma lista de dicionários."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo do catálogo não encontrado: {caminho}")

    with open(caminho, "r", encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        registros = [dict(linha) for linha in leitor]

    _logar_leitura(logger, caminho, len(registros))
    return registros


def ler_json_lista(caminho: Path, logger: logging.Logger) -> list[dict[str, Any]]:
    """Lê um arquivo JSON contendo uma lista de objetos (interações ou comentários)."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {caminho}")

    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if not isinstance(dados, list):
        raise ValueError(f"Esperava uma lista de registros em {caminho}, recebi {type(dados)}")

    _logar_leitura(logger, caminho, len(dados))
    return dados


def ler_todas_as_fontes(
    caminho_catalogo: Path,
    caminho_interacoes: Path,
    caminho_comentarios: Path,
    logger: logging.Logger,
) -> dict[str, list[dict[str, Any]]]:
    """Lê as três fontes obrigatórias e retorna um dicionário com os registros brutos."""
    logger.info("Iniciando leitura das fontes de dados...")

    catalogo = ler_catalogo_csv(caminho_catalogo, logger)
    interacoes = ler_json_lista(caminho_interacoes, logger)
    comentarios = ler_json_lista(caminho_comentarios, logger)

    logger.info("Leitura das fontes concluída.")

    return {
        "catalogo": catalogo,
        "interacoes": interacoes,
        "comentarios": comentarios,
    }
