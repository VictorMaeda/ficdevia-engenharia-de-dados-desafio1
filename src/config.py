"""
Carregamento da configuração do pipeline (RF01).

- Parâmetros não sensíveis (caminhos de arquivos, opções de validação,
  nomes de tabelas etc.) vêm de config/config.yaml.
- Segredos (usuário/senha/host de banco) vêm de variáveis de ambiente
  (arquivo .env, carregado via python-dotenv), nunca do código-fonte.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "config" / "config.yaml"
CAMINHO_ENV_PADRAO = RAIZ_PROJETO / ".env"


@dataclass
class ConfigPostgres:
    host: str
    porta: int
    banco: str
    usuario: str
    senha: str
    aplicar_schema_ao_iniciar: bool
    script_schema: Path


@dataclass
class ConfigMongo:
    host: str
    porta: int
    banco: str
    usuario: str
    senha: str
    colecao_comentarios: str
    aplicar_indices_ao_iniciar: bool

    def uri(self) -> str:
        if self.usuario and self.senha:
            return f"mongodb://{self.usuario}:{self.senha}@{self.host}:{self.porta}/{self.banco}"
        return f"mongodb://{self.host}:{self.porta}/{self.banco}"


@dataclass
class ConfigValidacao:
    tipos_conteudo_validos: list[str] = field(default_factory=list)
    niveis_validos: list[str] = field(default_factory=list)
    tipos_interacao_validos: list[str] = field(default_factory=list)
    avaliacao_min: int = 1
    avaliacao_max: int = 5
    percentual_conclusao_min: float = 0
    percentual_conclusao_max: float = 100
    carga_horaria_min_minutos: int = 1


@dataclass
class Config:
    caminho_catalogo_csv: Path
    caminho_interacoes_json: Path
    caminho_comentarios_json: Path

    dir_processados: Path
    arquivo_resumo: Path
    arquivo_rejeitados_catalogo: Path
    arquivo_rejeitados_interacoes: Path
    arquivo_rejeitados_comentarios: Path
    catalogo_tratado: Path
    interacoes_tratadas: Path
    comentarios_tratados: Path

    dir_logs: Path
    arquivo_log: Path
    nivel_log: str

    postgres: ConfigPostgres
    mongo: ConfigMongo
    validacao: ConfigValidacao


def _resolver_caminho(valor: str) -> Path:
    caminho = Path(valor)
    if not caminho.is_absolute():
        caminho = RAIZ_PROJETO / caminho
    return caminho


def _obter_env(nome: str, obrigatorio: bool = True, padrao: str | None = None) -> str:
    valor = os.environ.get(nome, padrao)
    if obrigatorio and not valor:
        raise RuntimeError(
            f"Variável de ambiente obrigatória ausente: {nome}. "
            "Copie .env.example para .env e preencha os valores."
        )
    return valor or ""


def carregar_configuracao(
    caminho_config: Path | str = CAMINHO_CONFIG_PADRAO,
    caminho_env: Path | str = CAMINHO_ENV_PADRAO,
) -> Config:
    """Lê config.yaml e .env e monta o objeto Config usado pelo restante do pipeline."""

    load_dotenv(dotenv_path=caminho_env, override=False)

    caminho_config = Path(caminho_config)
    if not caminho_config.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho_config}")

    with open(caminho_config, "r", encoding="utf-8") as f:
        bruto: dict[str, Any] = yaml.safe_load(f)

    fontes = bruto["fontes"]
    saida = bruto["saida"]
    logs = bruto["logs"]
    postgres_cfg = bruto["postgres"]
    mongo_cfg = bruto["mongodb"]
    validacao_cfg = bruto.get("validacao", {})

    postgres = ConfigPostgres(
        host=_obter_env("POSTGRES_HOST"),
        porta=int(_obter_env("POSTGRES_PORT", padrao="5432")),
        banco=_obter_env("POSTGRES_DB"),
        usuario=_obter_env("POSTGRES_USER"),
        senha=_obter_env("POSTGRES_PASSWORD"),
        aplicar_schema_ao_iniciar=bool(postgres_cfg.get("aplicar_schema_ao_iniciar", True)),
        script_schema=_resolver_caminho(postgres_cfg["script_schema"]),
    )

    mongo = ConfigMongo(
        host=_obter_env("MONGO_HOST"),
        porta=int(_obter_env("MONGO_PORT", padrao="27017")),
        banco=_obter_env("MONGO_DB"),
        usuario=_obter_env("MONGO_USER", obrigatorio=False),
        senha=_obter_env("MONGO_PASSWORD", obrigatorio=False),
        colecao_comentarios=mongo_cfg.get("colecao_comentarios", "comentarios_avaliacoes"),
        aplicar_indices_ao_iniciar=bool(mongo_cfg.get("aplicar_indices_ao_iniciar", True)),
    )

    validacao = ConfigValidacao(
        tipos_conteudo_validos=validacao_cfg.get("tipos_conteudo_validos", []),
        niveis_validos=validacao_cfg.get("niveis_validos", []),
        tipos_interacao_validos=validacao_cfg.get("tipos_interacao_validos", []),
        avaliacao_min=validacao_cfg.get("avaliacao_min", 1),
        avaliacao_max=validacao_cfg.get("avaliacao_max", 5),
        percentual_conclusao_min=validacao_cfg.get("percentual_conclusao_min", 0),
        percentual_conclusao_max=validacao_cfg.get("percentual_conclusao_max", 100),
        carga_horaria_min_minutos=validacao_cfg.get("carga_horaria_min_minutos", 1),
    )

    return Config(
        caminho_catalogo_csv=_resolver_caminho(fontes["catalogo_csv"]),
        caminho_interacoes_json=_resolver_caminho(fontes["interacoes_json"]),
        caminho_comentarios_json=_resolver_caminho(fontes["comentarios_json"]),
        dir_processados=_resolver_caminho(saida["diretorio_processados"]),
        arquivo_resumo=_resolver_caminho(saida["arquivo_resumo"]),
        arquivo_rejeitados_catalogo=_resolver_caminho(saida["arquivo_rejeitados_catalogo"]),
        arquivo_rejeitados_interacoes=_resolver_caminho(saida["arquivo_rejeitados_interacoes"]),
        arquivo_rejeitados_comentarios=_resolver_caminho(saida["arquivo_rejeitados_comentarios"]),
        catalogo_tratado=_resolver_caminho(saida["catalogo_tratado"]),
        interacoes_tratadas=_resolver_caminho(saida["interacoes_tratadas"]),
        comentarios_tratados=_resolver_caminho(saida["comentarios_tratados"]),
        dir_logs=_resolver_caminho(logs["diretorio"]),
        arquivo_log=_resolver_caminho(logs["arquivo"]),
        nivel_log=logs.get("nivel", "INFO"),
        postgres=postgres,
        mongo=mongo,
        validacao=validacao,
    )
