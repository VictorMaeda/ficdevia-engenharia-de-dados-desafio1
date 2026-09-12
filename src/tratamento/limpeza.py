"""
Tratamento e padronização (RF04).

Aplicado somente sobre os registros classificados como "valido" pela
etapa de validação (RF03). Os arquivos originais nunca são alterados;
o resultado do tratamento é gravado em dados/processados/.

Decisões de tratamento adotadas (ver também documentacao/):
- espaços nas extremidades de campos textuais são removidos;
- categoria/tipo/nível são normalizados para minúsculas e sem acentos;
- datas são convertidas para o formato ISO (YYYY-MM-DD ou
  YYYY-MM-DDTHH:MM:SS);
- campos numéricos são convertidos para int/float;
- valores ausentes em campos não obrigatórios são mantidos como None
  e registrados como tal (não são inventados valores).
"""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any


def _remover_acentos(texto: str) -> str:
    forma_normalizada = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in forma_normalizada if not unicodedata.combining(c))


def _normalizar_categorico(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return _remover_acentos(texto).lower()


def _normalizar_texto(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _padronizar_data(valor: Any, incluir_hora: bool = False) -> str | None:
    if not valor:
        return None
    texto = str(valor).strip()
    formatos = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]
    for fmt in formatos:
        try:
            data = datetime.strptime(texto, fmt)
            return data.strftime("%Y-%m-%dT%H:%M:%S") if incluir_hora else data.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _para_inteiro(valor: Any) -> int | None:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _para_float(valor: Any) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def tratar_catalogo(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tratados = []
    for registro in registros:
        tratados.append(
            {
                "conteudo_id": _para_inteiro(registro.get("conteudo_id")),
                "titulo": _normalizar_texto(registro.get("titulo")),
                "tipo": _normalizar_categorico(registro.get("tipo")),
                "categoria": _normalizar_texto(registro.get("categoria")),
                "nivel": _normalizar_categorico(registro.get("nivel")),
                "carga_horaria_min": _para_inteiro(registro.get("carga_horaria_min")),
                "data_publicacao": _padronizar_data(registro.get("data_publicacao")),
                "descricao": _normalizar_texto(registro.get("descricao")),
                "autor": _normalizar_texto(registro.get("autor")),
            }
        )
    return tratados


def tratar_interacoes(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tratados = []
    for registro in registros:
        tratados.append(
            {
                "usuario_id": _para_inteiro(registro.get("usuario_id")),
                "conteudo_id": _para_inteiro(registro.get("conteudo_id")),
                "tipo_interacao": _normalizar_categorico(registro.get("tipo_interacao")),
                "data_hora": _padronizar_data(registro.get("data_hora"), incluir_hora=True),
                "tempo_consumido": _para_float(registro.get("tempo_consumido")),
                "percentual_conclusao": _para_float(registro.get("percentual_conclusao")),
                "avaliacao_atribuida": _para_inteiro(registro.get("avaliacao_atribuida")),
            }
        )
    return tratados


def tratar_comentarios(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tratados = []
    for registro in registros:
        tags = registro.get("tags") or []
        tags_tratadas = [
            _normalizar_categorico(tag) for tag in tags if _normalizar_categorico(tag)
        ]
        tratados.append(
            {
                "usuario_id": _para_inteiro(registro.get("usuario_id")),
                "conteudo_id": _para_inteiro(registro.get("conteudo_id")),
                "avaliacao": _para_inteiro(registro.get("avaliacao")),
                "comentario": _normalizar_texto(registro.get("comentario")),
                "tags": tags_tratadas,
                "data": _padronizar_data(registro.get("data")),
            }
        )
    return tratados
