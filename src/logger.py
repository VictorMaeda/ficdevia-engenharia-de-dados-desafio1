"""
Configuração de logging do pipeline (RF01 e RF14).

Registra em console e em arquivo:
- início e término do processamento;
- etapas executadas e seus tempos;
- falhas de conexão, de geração/carga e de persistência.
"""

from __future__ import annotations

import logging
from pathlib import Path


def configurar_logger(
    nome: str = "desafio_dados",
    arquivo_log: Path | str = "logs/execucao.log",
    nivel: str = "INFO",
) -> logging.Logger:
    arquivo_log = Path(arquivo_log)
    arquivo_log.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(nome)
    logger.setLevel(getattr(logging, nivel.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        # Evita handlers duplicados caso a função seja chamada mais de uma vez.
        return logger

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formato)

    handler_arquivo = logging.FileHandler(arquivo_log, encoding="utf-8")
    handler_arquivo.setFormatter(formato)

    logger.addHandler(handler_console)
    logger.addHandler(handler_arquivo)

    return logger
