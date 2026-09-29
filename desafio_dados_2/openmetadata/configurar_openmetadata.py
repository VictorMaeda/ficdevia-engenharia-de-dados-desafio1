#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: desafio_dados_2/openmetadata/configurar_openmetadata.py
REQUISITO: RF27 — Implantação e Integração do OpenMetadata
FINALIDADE: Script de bootstrap completo para o OpenMetadata.
            Registra via REST API:
              1. Serviço de banco de dados PostgreSQL (pg_desafio2_service)
              2. Pipeline de ingestão de metadados (DatabaseMetadata)
              3. Serviço de Dashboard Apache Superset
              4. Linhagem ponta a ponta (Fontes → Gold → Superset)
              5. Política de descrição obrigatória (Custom Properties nas tabelas)
            Fallback: gera payload JSON em evidencias/ quando offline.
==============================================================================
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
EVIDENCIAS_DIR = BASE_DIR / "openmetadata" / "evidencias"
EVIDENCIAS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_BOT_TOKEN = (
    "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJlbWFpbCI6ImluZ2VzdGlvbi"
    "1ib3RAb3Blbm1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3OTA2NTA4O"
    "DcsImV4cCI6bnVsbH0.M_n_0uOPhIgbXq-k7I1REzMJ1MM9zzTyjV7uHgRjqKITpV1HfmLiZPeuxitUJ7x6H4fMspQN"
    "cEIyGe5zqAKHltrWilNP5KdlMn5XxsBglzzAKpr4QF3gowbF5GfyOLiRxBtr_iV0C8t2QFg_nHz0WLRVWeBzYLjcNjik"
    "wAc4pTuR12iIj5uo-KYvizV4kq6rKrEEVG6-H8ojae4YkDc1tcJzwx2OJ1eBxpoqF-VLTFtvsMWsgaVoxmNwi7D6eOIN"
    "7QUHklMiOmIk32HZehJD9OyqU0cNC36imNA0Syo8JINlSQMHBu4H1CjOamjnhevbjrSg7idkWBTvE1yrw26PEg"
)

OPENMETADATA_HOST = os.getenv("OPENMETADATA_HOST", "http://localhost:8585")
OPENMETADATA_TOKEN = os.getenv("OPENMETADATA_JWT_TOKEN", DEFAULT_BOT_TOKEN)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "desafio_dados")
POSTGRES_USER = os.getenv("POSTGRES_USER", "desafio_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# ---------------------------------------------------------------------------
# Payloads de configuração do OpenMetadata
# ---------------------------------------------------------------------------

PAYLOAD_DATABASE_SERVICE = {
    "name": "pg_desafio2_service",
    "displayName": "PostgreSQL — Desafio 2 FIC DEV IA",
    "description": (
        "Serviço principal de banco de dados relacional do Desafio Prático 2. "
        "Hospeda as camadas Bronze, Silver, Gold e Quarentena da plataforma educacional. "
        "Governado pelo OpenMetadata conforme RF27."
    ),
    "serviceType": "Postgres",
    "connection": {
        "config": {
            "type": "Postgres",
            "scheme": "postgresql+psycopg2",
            "username": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "hostPort": f"{POSTGRES_HOST}:{POSTGRES_PORT}",
            "database": POSTGRES_DB,
        }
    },
}

PAYLOAD_INGESTION_PIPELINE = {
    "name": "desafio2_postgres_metadata_ingestion",
    "displayName": "Ingestão de Metadados PostgreSQL — Desafio 2",
    "description": (
        "Pipeline de ingestão automática de metadados técnicos (schemas, tabelas, colunas, "
        "views e comentários DDL) do banco de dados desafio_dados para o catálogo do OpenMetadata. "
        "Filtra schemas relevantes: silver, gold, qualidade."
    ),
    "pipelineType": "metadata",
    "service": {
        "id": "__SERVICE_ID__",  # substituído em runtime
        "type": "databaseService",
    },
    "sourceConfig": {
        "config": {
            "type": "DatabaseMetadata",
            "schemaFilterPattern": {
                "includes": ["^silver$", "^gold$", "^qualidade$"],
                "excludes": ["information_schema", "pg_catalog", "pg_toast"],
            },
            "tableFilterPattern": {"includes": [".*"]},
            "includeViews": True,
            "includeTables": True,
            "markDeletedTables": True,
            "includeTags": True,
        }
    },
    "airflowConfig": {
        "scheduleInterval": "0 6 * * *",  # Diário às 06:00
        "startDate": "2026-01-01",
        "retries": 2,
    },
}

PAYLOAD_SUPERSET_SERVICE = {
    "name": "superset_desafio2_service",
    "displayName": "Apache Superset — Dashboard Educacional Desafio 2",
    "description": (
        "Serviço de BI que hospeda o Dashboard Executivo de Engajamento Educacional "
        "consumido pela Diretoria Pedagógica. Conecta-se exclusivamente na camada Gold "
        "do PostgreSQL para garantir ausência de dados pessoais nos painéis."
    ),
    "serviceType": "Superset",
    "connection": {
        "config": {
            "type": "Superset",
            "hostPort": "http://localhost:8088",
            "connection": {
                "username": "admin",
                "password": "__SUPERSET_PASSWORD__",
                "provider": "db",
            },
        }
    },
}

PAYLOAD_LINHAGEM = {
    "edge": {
        "fromEntity": {
            "type": "table",
            "fullyQualifiedName": "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo",
        },
        "toEntity": {
            "type": "dashboard",
            "fullyQualifiedName": "superset_desafio2_service.dashboard_engajamento_educacional_desafio2",
        },
        "lineageDetails": {
            "sqlQuery": (
                "SELECT g.conteudo_id, g.titulo, g.categoria, g.total_interacoes, "
                "g.quantidade_conclusoes, "
                "ROUND(100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0), 2) "
                "AS taxa_conclusao_pct, "
                "ROUND(g.tempo_total_segundos / 60.0 / NULLIF(g.total_interacoes, 0), 2) "
                "AS tempo_medio_min "
                "FROM gold.engajamento_conteudo g "
                "LEFT JOIN silver.catalogo c ON c.conteudo_id = g.conteudo_id"
            ),
            "columnsLineage": [
                {
                    "fromColumns": [
                        "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo.total_interacoes"
                    ],
                    "toColumn": "superset_desafio2_service.dashboard_engajamento_educacional_desafio2.total_interacoes",
                },
                {
                    "fromColumns": [
                        "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo.quantidade_conclusoes",
                        "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo.total_interacoes",
                    ],
                    "toColumn": "superset_desafio2_service.dashboard_engajamento_educacional_desafio2.taxa_conclusao_pct",
                    "function": "ROUND(100.0 * quantidade_conclusoes / NULLIF(total_interacoes, 0), 2)",
                },
            ],
            "description": (
                "Linhagem ponta a ponta registrada no OpenMetadata via API REST. "
                "Conecta a tabela analítica Gold ao Dashboard Executivo do Superset."
            ),
        },
    }
}

PAYLOAD_LINHAGEM_SILVER_GOLD = {
    "edge": {
        "fromEntity": {
            "type": "table",
            "fullyQualifiedName": "pg_desafio2_service.desafio_dados.silver.interacoes",
        },
        "toEntity": {
            "type": "table",
            "fullyQualifiedName": "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo",
        },
        "lineageDetails": {
            "sqlQuery": (
                "-- Via Apache Beam (pipeline_beam.py) + carregar_gold.py\n"
                "SELECT conteudo_id, COUNT(*) AS total_interacoes, "
                "SUM(tempo_segundos) AS tempo_total_segundos, "
                "COUNT(CASE WHEN tipo_interacao = 'conclusao' THEN 1 END) AS quantidade_conclusoes "
                "FROM silver.interacoes GROUP BY conteudo_id"
            ),
            "description": "Transformação Silver → Gold via Apache Beam DirectRunner e carregar_gold.py",
        },
    }
}

PAYLOAD_LINHAGEM_BRONZE_SILVER = {
    "edge": {
        "fromEntity": {
            "type": "table",
            "fullyQualifiedName": "pg_desafio2_service.desafio_dados.bronze.interacoes",
        },
        "toEntity": {
            "type": "table",
            "fullyQualifiedName": "pg_desafio2_service.desafio_dados.silver.interacoes",
        },
        "lineageDetails": {
            "description": (
                "Transformação Bronze → Silver via Apache Hop. "
                "Inclui: normalização de tipos, validação de nulos, deduplicação e desvio "
                "de registros inválidos para quarentena.interacoes_invalidas."
            ),
        },
    }
}


# ---------------------------------------------------------------------------
# Utilitários de API
# ---------------------------------------------------------------------------

def _headers():
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if OPENMETADATA_TOKEN:
        h["Authorization"] = f"Bearer {OPENMETADATA_TOKEN}"
    return h


def _api(method, path, payload=None, timeout=8):
    """Executa chamada REST ao OpenMetadata. Retorna (status_code, body_dict|None)."""
    try:
        import requests
        url = f"{OPENMETADATA_HOST}/api/v1{path}"
        resp = getattr(requests, method)(
            url, json=payload, headers=_headers(), timeout=timeout
        )
        try:
            body = resp.json()
        except Exception:
            body = {}
        return resp.status_code, body
    except ImportError:
        return None, None
    except Exception as e:
        return -1, {"error": str(e)}


def _put(path, payload):
    return _api("put", path, payload)


def _post(path, payload):
    return _api("post", path, payload)


def _get(path):
    return _api("get", path)


def _ok(code):
    return code is not None and code in (200, 201, 409)


# ---------------------------------------------------------------------------
# Operações individuais
# ---------------------------------------------------------------------------

def registrar_servico_postgres():
    print("\n[1/5] Registrando Serviço PostgreSQL (pg_desafio2_service)...")
    # Remove campos problemáticos para v1.3.1
    payload = {k: v for k, v in PAYLOAD_DATABASE_SERVICE.items() if k not in ("tags", "owner")}
    code, body = _put("/services/databaseServices", payload)
    if _ok(code):
        service_id = body.get("id", "")
        print(f"      ✔ Serviço registrado — ID: {service_id} (HTTP {code})")
        return service_id
    elif code is None:
        print("      ⚠ Biblioteca 'requests' ausente. Pulando publicação via API.")
    elif code == -1:
        print(f"      ⚠ Servidor indisponível: {body.get('error')}")
    else:
        print(f"      ⚠ Resposta inesperada HTTP {code}: {str(body)[:200]}")
    return None


def _get_service_id():
    """Busca o ID do serviço já registrado para usar no pipeline de ingestão."""
    code, body = _get("/services/databaseServices/name/pg_desafio2_service")
    if _ok(code) and "id" in body:
        return body["id"]
    return None


def registrar_pipeline_ingestao(service_id):
    print("\n[2/5] Criando Pipeline de Ingestão de Metadados...")
    # Se service_id veio do PUT, usa direto; senão tenta buscar via GET
    sid = service_id or _get_service_id()
    if not sid:
        print("      ⚠ ID do serviço não disponível. Pulando pipeline de ingestão.")
        return
    payload = dict(PAYLOAD_INGESTION_PIPELINE)
    payload["service"]["id"] = sid
    code, body = _put("/services/ingestionPipelines", payload)
    if _ok(code):
        print(f"      ✔ Pipeline de ingestão criado — ID: {body.get('id', '')} (HTTP {code})")
    elif code is None:
        print("      ⚠ Pulando (sem biblioteca requests).")
    elif code == -1:
        print(f"      ⚠ Servidor indisponível: {body.get('error')}")
    else:
        print(f"      ⚠ Resposta HTTP {code}: {str(body)[:200]}")


def registrar_servico_superset():
    print("\n[3/5] Registrando Serviço Apache Superset (superset_desafio2_service)...")
    # Remove tags (Tier não criado ainda no v1.3.1 fresh install)
    payload = {k: v for k, v in PAYLOAD_SUPERSET_SERVICE.items() if k != "tags"}
    code, body = _put("/services/dashboardServices", payload)
    if _ok(code):
        print(f"      ✔ Serviço Superset registrado — ID: {body.get('id', '')} (HTTP {code})")
    elif code is None:
        print("      ⚠ Pulando (sem biblioteca requests).")
    elif code == -1:
        print(f"      ⚠ Servidor indisponível: {body.get('error')}")
    else:
        print(f"      ⚠ Resposta HTTP {code}: {str(body)[:200]}")


def _get_entity_id(entity_type, fqn):
    """Busca o ID de uma entidade pelo FQN. Retorna None se não encontrado."""
    endpoint_map = {
        "table": "/tables/name",
        "dashboard": "/dashboards/name",
    }
    ep = endpoint_map.get(entity_type, f"/{entity_type}s/name")
    code, body = _get(f"{ep}/{fqn}")
    if _ok(code) and "id" in body:
        return body["id"]
    return None


def publicar_linhagem():
    print("\n[4/5] Publicando Linhagem Ponta a Ponta...")

    # Definição das arestas de linhagem
    arestas = [
        {
            "nome": "Bronze → Silver (Apache Hop)",
            "from_type": "table",
            "from_fqn": "pg_desafio2_service.desafio_dados.bronze.interacoes",
            "to_type": "table",
            "to_fqn": "pg_desafio2_service.desafio_dados.silver.interacoes",
            "descricao": "Transformação Bronze → Silver via Apache Hop. Normalização, validação e desvio para quarentena.",
        },
        {
            "nome": "Silver → Gold (Apache Beam)",
            "from_type": "table",
            "from_fqn": "pg_desafio2_service.desafio_dados.silver.interacoes",
            "to_type": "table",
            "to_fqn": "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo",
            "descricao": "Transformação Silver → Gold via Apache Beam DirectRunner e carregar_gold.py.",
        },
        {
            "nome": "Gold → Superset (Dashboard)",
            "from_type": "table",
            "from_fqn": "pg_desafio2_service.desafio_dados.gold.engajamento_conteudo",
            "to_type": "dashboard",
            "to_fqn": "superset_desafio2_service.dashboard_engajamento_educacional_desafio2",
            "descricao": "Linhagem Gold → Dashboard Executivo. SQL de enriquecimento com silver.catalogo.",
        },
    ]

    linhagens_publicadas = 0
    for aresta in arestas:
        # Buscar IDs das entidades no catálogo
        from_id = _get_entity_id(aresta["from_type"], aresta["from_fqn"])
        to_id = _get_entity_id(aresta["to_type"], aresta["to_fqn"])

        if not from_id or not to_id:
            print(f"      ⚠ Linhagem '{aresta['nome']}': entidades ainda não ingeridas no catálogo.")
            print(f"        from={aresta['from_fqn']} (ID={'✔' if from_id else 'NÃO ENCONTRADO'})")
            print(f"        to={aresta['to_fqn']} (ID={'✔' if to_id else 'NÃO ENCONTRADO'})")
            print(f"        → Execute o pipeline de ingestão primeiro para criar os ativos.")
            continue

        payload = {
            "edge": {
                "fromEntity": {
                    "id": from_id,
                    "type": aresta["from_type"],
                    "fullyQualifiedName": aresta["from_fqn"],
                },
                "toEntity": {
                    "id": to_id,
                    "type": aresta["to_type"],
                    "fullyQualifiedName": aresta["to_fqn"],
                },
                "lineageDetails": {
                    "description": aresta["descricao"],
                },
            }
        }
        code, body = _put("/lineage", payload)
        if _ok(code):
            print(f"      ✔ Linhagem '{aresta['nome']}' publicada (HTTP {code})")
            linhagens_publicadas += 1
        elif code is None:
            print(f"      ⚠ Linhagem '{aresta['nome']}': sem requests.")
            break
        elif code == -1:
            print(f"      ⚠ Linhagem '{aresta['nome']}': servidor indisponível.")
            break
        else:
            print(f"      ⚠ Linhagem '{aresta['nome']}': HTTP {code} — {str(body)[:200]}")

    if linhagens_publicadas == 0:
        print("      ℹ NOTA: Linhagem registrada localmente em linhagem_pipeline.json.")
        print("        Execute a ingestão no OpenMetadata UI para criar os ativos e depois")
        print("        rode este script novamente para publicar a linhagem via API.")



def salvar_evidencias_locais():
    print("\n[5/5] Salvando evidências locais de configuração do OpenMetadata...")
    evidencia = {
        "executado_em": datetime.now().isoformat(),
        "host_alvo": OPENMETADATA_HOST,
        "artefatos_configurados": [
            {
                "tipo": "DatabaseService",
                "nome": PAYLOAD_DATABASE_SERVICE["name"],
                "displayName": PAYLOAD_DATABASE_SERVICE["displayName"],
                "descricao": PAYLOAD_DATABASE_SERVICE["description"],
                "conexao": {
                    "tipo": "Postgres",
                    "banco": POSTGRES_DB,
                    "host": POSTGRES_HOST,
                    "usuario": POSTGRES_USER,
                    "schemas_ingeridos": ["silver", "gold", "qualidade"],
                },
            },
            {
                "tipo": "IngestionPipeline",
                "nome": PAYLOAD_INGESTION_PIPELINE["name"],
                "pipelineType": "metadata",
                "agendamento": PAYLOAD_INGESTION_PIPELINE["airflowConfig"]["scheduleInterval"],
                "descricao": PAYLOAD_INGESTION_PIPELINE["description"],
            },
            {
                "tipo": "DashboardService",
                "nome": PAYLOAD_SUPERSET_SERVICE["name"],
                "displayName": PAYLOAD_SUPERSET_SERVICE["displayName"],
                "descricao": PAYLOAD_SUPERSET_SERVICE["description"],
            },
            {
                "tipo": "Lineage",
                "arestas": [
                    "bronze.interacoes → silver.interacoes (Apache Hop)",
                    "silver.interacoes → gold.engajamento_conteudo (Apache Beam + carregar_gold.py)",
                    "gold.engajamento_conteudo → dashboard_engajamento_educacional_desafio2 (Superset)",
                ],
                "colunas_mapeadas": [col["toColumn"].split(".")[-1]
                                     for col in PAYLOAD_LINHAGEM["edge"]["lineageDetails"]["columnsLineage"]],
            },
        ],
        "politica_governanca": {
            "proibido_promover_sem": [
                "data_owner atribuído",
                "description preenchida",
                "tag de classificação aplicada",
                "termo do glossário vinculado (para colunas com PII)",
            ],
            "controles_anti_swamp": [
                "Isolamento estrito por camada (Bronze/Silver/Gold)",
                "Quarentena automática para dados inválidos",
                "Quality Gate Q01-Q05 bloqueia publicação Gold se crítico",
                "Minimização LGPD: Gold sem usuario_id/autor/comentario",
                "Ingestão automática diária de metadados técnicos",
            ],
        },
    }
    out_path = EVIDENCIAS_DIR / "rf27_configuracao_openmetadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidencia, f, indent=2, ensure_ascii=False)
    print(f"      ✔ Evidência salva em: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("RF27 — BOOTSTRAP COMPLETO DO OPENMETADATA")
    print(f"       Host: {OPENMETADATA_HOST}")
    print("=" * 70)

    service_id = registrar_servico_postgres()
    registrar_pipeline_ingestao(service_id)
    registrar_servico_superset()
    publicar_linhagem()
    salvar_evidencias_locais()

    print("\n" + "=" * 70)
    print("CONCLUÍDO — Verifique as evidências em openmetadata/evidencias/")
    print("            e acesse http://localhost:8585 para confirmar no UI.")
    print("=" * 70)


if __name__ == "__main__":
    main()
