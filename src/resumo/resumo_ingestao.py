"""
Resumo da ingestão (RF05).

Ao final da ingestão, o sistema apresenta e grava (em JSON) um resumo
contendo, por fonte: quantidade de registros lidos, válidos, inválidos,
incompletos, duplicados, corrigidos, carregados no PostgreSQL, além do
tempo total de processamento.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.validacao.validadores import (
    STATUS_DUPLICADO,
    STATUS_INCOMPLETO,
    STATUS_INVALIDO,
    STATUS_VALIDO,
    ResultadoValidacao,
)


@dataclass
class ResumoFonte:
    nome_fonte: str
    registros_lidos: int = 0
    registros_validos: int = 0
    registros_invalidos: int = 0
    registros_incompletos: int = 0
    registros_duplicados: int = 0
    registros_corrigidos: int = 0
    registros_carregados: int = 0


@dataclass
class ResumoIngestao:
    fontes: list[ResumoFonte] = field(default_factory=list)
    tempo_total_segundos: float = 0.0
    carregados_por_banco: dict[str, int] = field(default_factory=dict)


def montar_resumo_fonte(
    nome_fonte: str,
    resultados: list[ResultadoValidacao],
    registros_corrigidos: int = 0,
    registros_carregados: int = 0,
) -> ResumoFonte:
    contagem = {
        STATUS_VALIDO: 0,
        STATUS_INVALIDO: 0,
        STATUS_INCOMPLETO: 0,
        STATUS_DUPLICADO: 0,
    }
    for resultado in resultados:
        contagem[resultado.status] = contagem.get(resultado.status, 0) + 1

    return ResumoFonte(
        nome_fonte=nome_fonte,
        registros_lidos=len(resultados),
        registros_validos=contagem[STATUS_VALIDO],
        registros_invalidos=contagem[STATUS_INVALIDO],
        registros_incompletos=contagem[STATUS_INCOMPLETO],
        registros_duplicados=contagem[STATUS_DUPLICADO],
        registros_corrigidos=registros_corrigidos,
        registros_carregados=registros_carregados,
    )


def gravar_resumo(resumo: ResumoIngestao, caminho: Path, logger: logging.Logger) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "fontes": [asdict(f) for f in resumo.fontes],
        "tempo_total_segundos": round(resumo.tempo_total_segundos, 3),
        "carregados_por_banco": resumo.carregados_por_banco,
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=2)

    logger.info("Resumo da ingestao gravado em %s", caminho)
    for fonte in resumo.fontes:
        logger.info(
            "Resumo [%s] lidos=%d validos=%d invalidos=%d incompletos=%d "
            "duplicados=%d corrigidos=%d carregados=%d",
            fonte.nome_fonte,
            fonte.registros_lidos,
            fonte.registros_validos,
            fonte.registros_invalidos,
            fonte.registros_incompletos,
            fonte.registros_duplicados,
            fonte.registros_corrigidos,
            fonte.registros_carregados,
        )
    logger.info("Registros carregados por banco de dados: %s", resumo.carregados_por_banco)
    logger.info("Tempo total de processamento: %.3f segundos", resumo.tempo_total_segundos)
