"""
Gravação dos resultados da ingestão em dados/processados/ (RF04):
- dados tratados (prontos para carga no PostgreSQL);
- registros rejeitados, com o motivo da rejeição (RF03).

Os arquivos originais em dados/brutos/ nunca são modificados.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from src.validacao.validadores import STATUS_VALIDO, ResultadoValidacao


def separar_validos_e_rejeitados(
    resultados: list[ResultadoValidacao],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retorna (registros_validos, registros_rejeitados_com_motivo)."""
    validos: list[dict[str, Any]] = []
    rejeitados: list[dict[str, Any]] = []

    for resultado in resultados:
        if resultado.status == STATUS_VALIDO:
            validos.append(resultado.registro)
        else:
            rejeitados.append(
                {
                    "status": resultado.status,
                    "motivos": resultado.motivos,
                    "registro_original": resultado.registro,
                }
            )

    return validos, rejeitados


def gravar_json(dados: list[dict[str, Any]], caminho: Path, logger: logging.Logger) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Arquivo gravado: %s (%d registros)", caminho, len(dados))


def gravar_csv(dados: list[dict[str, Any]], caminho: Path, logger: logging.Logger) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not dados:
        # Ainda assim cria o arquivo, vazio, para manter o contrato de saída.
        caminho.write_text("", encoding="utf-8")
        logger.info("Arquivo gravado: %s (0 registros)", caminho)
        return

    campos = list(dados[0].keys())
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(dados)
    logger.info("Arquivo gravado: %s (%d registros)", caminho, len(dados))
