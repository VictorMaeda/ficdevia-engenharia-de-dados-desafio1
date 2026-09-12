"""
Validação dos dados (RF03).

Cada registro é classificado como:
- valido
- invalido
- incompleto
- duplicado

e o motivo da classificação (quando não "valido") é registrado no
próprio resultado, para permitir auditoria e geração dos arquivos de
registros rejeitados.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.config import ConfigValidacao

STATUS_VALIDO = "valido"
STATUS_INVALIDO = "invalido"
STATUS_INCOMPLETO = "incompleto"
STATUS_DUPLICADO = "duplicado"

REGEX_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ResultadoValidacao:
    registro: dict[str, Any]
    status: str
    motivos: list[str] = field(default_factory=list)


def _normalizar_categorico(valor: Any) -> str:
    """Minusculas e sem acentos, para comparação robusta com os domínios do config.yaml."""
    texto = str(valor or "").strip().lower()
    texto_sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto_sem_acento if not unicodedata.combining(c))


def _campo_ausente(registro: dict[str, Any], campo: str) -> bool:
    valor = registro.get(campo)
    return valor is None or (isinstance(valor, str) and valor.strip() == "")


def _parse_data(valor: str) -> datetime | None:
    if not valor:
        return None
    valor = valor.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None


def _numero_valido(valor: Any, minimo: float | None = None, maximo: float | None = None) -> bool:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return False
    if minimo is not None and numero < minimo:
        return False
    if maximo is not None and numero > maximo:
        return False
    return True


# ------------------------------------------------------------------
# Catálogo de conteúdos
# ------------------------------------------------------------------

CAMPOS_OBRIGATORIOS_CATALOGO = [
    "conteudo_id",
    "titulo",
    "tipo",
    "categoria",
    "nivel",
    "carga_horaria_min",
    "data_publicacao",
]


def validar_catalogo(
    registros: list[dict[str, Any]], cfg: ConfigValidacao
) -> list[ResultadoValidacao]:
    resultados: list[ResultadoValidacao] = []
    ids_vistos: set[str] = set()

    for registro in registros:
        motivos: list[str] = []

        campos_ausentes = [c for c in CAMPOS_OBRIGATORIOS_CATALOGO if _campo_ausente(registro, c)]
        if campos_ausentes:
            motivos.append(f"campos obrigatorios ausentes: {', '.join(campos_ausentes)}")
            resultados.append(ResultadoValidacao(registro, STATUS_INCOMPLETO, motivos))
            continue

        conteudo_id = str(registro.get("conteudo_id", "")).strip()
        if not conteudo_id.isdigit():
            motivos.append("conteudo_id nao numerico")
        elif conteudo_id in ids_vistos:
            resultados.append(
                ResultadoValidacao(registro, STATUS_DUPLICADO, ["conteudo_id duplicado"])
            )
            continue
        else:
            ids_vistos.add(conteudo_id)

        tipo = _normalizar_categorico(registro.get("tipo"))
        if tipo and tipo not in cfg.tipos_conteudo_validos:
            motivos.append(f"tipo fora do dominio esperado: {tipo}")

        nivel = _normalizar_categorico(registro.get("nivel"))
        if nivel and nivel not in cfg.niveis_validos:
            motivos.append(f"nivel fora do dominio esperado: {nivel}")

        if not _numero_valido(registro.get("carga_horaria_min"), minimo=cfg.carga_horaria_min_minutos):
            motivos.append("carga_horaria_min invalida (negativa, nula ou nao numerica)")

        if not _parse_data(str(registro.get("data_publicacao", ""))):
            motivos.append("data_publicacao em formato invalido")

        status = STATUS_INVALIDO if motivos else STATUS_VALIDO
        resultados.append(ResultadoValidacao(registro, status, motivos))

    return resultados


# ------------------------------------------------------------------
# Interações dos usuários
# ------------------------------------------------------------------

CAMPOS_OBRIGATORIOS_INTERACAO = [
    "usuario_id",
    "conteudo_id",
    "tipo_interacao",
    "data_hora",
]


def validar_interacoes(
    registros: list[dict[str, Any]],
    cfg: ConfigValidacao,
    ids_conteudo_validos: set[str],
) -> list[ResultadoValidacao]:
    resultados: list[ResultadoValidacao] = []
    chaves_vistas: set[tuple] = set()

    for registro in registros:
        motivos: list[str] = []

        campos_ausentes = [c for c in CAMPOS_OBRIGATORIOS_INTERACAO if _campo_ausente(registro, c)]
        if campos_ausentes:
            motivos.append(f"campos obrigatorios ausentes: {', '.join(campos_ausentes)}")
            resultados.append(ResultadoValidacao(registro, STATUS_INCOMPLETO, motivos))
            continue

        usuario_id = str(registro.get("usuario_id", "")).strip()
        conteudo_id = str(registro.get("conteudo_id", "")).strip()

        if not usuario_id.isdigit() or int(usuario_id) <= 0:
            motivos.append("usuario_id invalido")

        if not conteudo_id.isdigit():
            motivos.append("conteudo_id invalido")
        elif conteudo_id not in ids_conteudo_validos:
            motivos.append("conteudo_id nao existe no catalogo validado")

        tipo_interacao = _normalizar_categorico(registro.get("tipo_interacao"))
        dominio_tipos_interacao = [_normalizar_categorico(t) for t in cfg.tipos_interacao_validos]
        if tipo_interacao not in dominio_tipos_interacao:
            motivos.append(f"tipo_interacao fora do dominio esperado: {tipo_interacao}")

        if not _parse_data(str(registro.get("data_hora", ""))):
            motivos.append("data_hora em formato invalido")

        tempo_consumido = registro.get("tempo_consumido")
        if tempo_consumido is not None and not _numero_valido(tempo_consumido, minimo=0):
            motivos.append("tempo_consumido negativo ou invalido")

        percentual = registro.get("percentual_conclusao")
        if percentual is not None and not _numero_valido(
            percentual, minimo=cfg.percentual_conclusao_min, maximo=cfg.percentual_conclusao_max
        ):
            motivos.append("percentual_conclusao fora do intervalo 0-100")

        avaliacao = registro.get("avaliacao_atribuida")
        if avaliacao is not None and not _numero_valido(
            avaliacao, minimo=cfg.avaliacao_min, maximo=cfg.avaliacao_max
        ):
            motivos.append("avaliacao_atribuida fora do intervalo permitido")

        if motivos:
            resultados.append(ResultadoValidacao(registro, STATUS_INVALIDO, motivos))
            continue

        chave = (usuario_id, conteudo_id, tipo_interacao, str(registro.get("data_hora")))
        if chave in chaves_vistas:
            resultados.append(
                ResultadoValidacao(registro, STATUS_DUPLICADO, ["interacao duplicada"])
            )
            continue
        chaves_vistas.add(chave)

        resultados.append(ResultadoValidacao(registro, STATUS_VALIDO, []))

    return resultados


# ------------------------------------------------------------------
# Comentários e avaliações
# ------------------------------------------------------------------

CAMPOS_OBRIGATORIOS_COMENTARIO = [
    "usuario_id",
    "conteudo_id",
    "avaliacao",
    "data",
]


def validar_comentarios(
    registros: list[dict[str, Any]],
    cfg: ConfigValidacao,
    ids_conteudo_validos: set[str],
) -> list[ResultadoValidacao]:
    resultados: list[ResultadoValidacao] = []
    chaves_vistas: set[tuple] = set()

    for registro in registros:
        motivos: list[str] = []

        campos_ausentes = [c for c in CAMPOS_OBRIGATORIOS_COMENTARIO if _campo_ausente(registro, c)]
        if campos_ausentes:
            motivos.append(f"campos obrigatorios ausentes: {', '.join(campos_ausentes)}")
            resultados.append(ResultadoValidacao(registro, STATUS_INCOMPLETO, motivos))
            continue

        usuario_id = str(registro.get("usuario_id", "")).strip()
        conteudo_id = str(registro.get("conteudo_id", "")).strip()

        if not usuario_id.isdigit() or int(usuario_id) <= 0:
            motivos.append("usuario_id invalido")

        if not conteudo_id.isdigit():
            motivos.append("conteudo_id invalido")
        elif conteudo_id not in ids_conteudo_validos:
            motivos.append("conteudo_id nao existe no catalogo validado")

        if not _numero_valido(
            registro.get("avaliacao"), minimo=cfg.avaliacao_min, maximo=cfg.avaliacao_max
        ):
            motivos.append("avaliacao fora do intervalo permitido")

        if not _parse_data(str(registro.get("data", ""))):
            motivos.append("data em formato invalido")

        if motivos:
            resultados.append(ResultadoValidacao(registro, STATUS_INVALIDO, motivos))
            continue

        chave = (usuario_id, conteudo_id, str(registro.get("data")))
        if chave in chaves_vistas:
            resultados.append(
                ResultadoValidacao(registro, STATUS_DUPLICADO, ["comentario/avaliacao duplicado"])
            )
            continue
        chaves_vistas.add(chave)

        resultados.append(ResultadoValidacao(registro, STATUS_VALIDO, []))

    return resultados
