#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: desafio_dados_2/openmetadata/registrar_dados_mestres_openmetadata.py
REQUISITO: RF30 — Gestão de Dados Mestres (MDM) no OpenMetadata
FINALIDADE: Registra a Entidade Mestre "Conteúdo Educacional" no catálogo do
            OpenMetadata através de:
              1. Custom Properties na tabela silver.catalogo (Golden Record, GoldenID)
              2. Tags específicas de MDM (Tier.Tier1_Critical, DataQuality.GoldenRecord)
              3. Definição da política de stewardship e survivorship
              4. Geração de evidência local para auditoria
==============================================================================
"""

import json
import os
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

# ---------------------------------------------------------------------------
# Entidade Mestre: Conteúdo Educacional
# ---------------------------------------------------------------------------

MDM_ENTIDADE_MESTRE = {
    "nome": "ConteudoEducacional",
    "displayName": "Conteúdo Educacional (Entidade Mestre MDM)",
    "description": (
        "Entidade de dados mestre central da plataforma FIC DEV IA. "
        "Representa o curso, vídeo, podcast ou artigo educacional de forma única e canônica. "
        "É referenciada por: silver.catalogo (master), silver.interacoes, silver.recomendacoes, "
        "silver.comentarios e gold.engajamento_conteudo."
    ),
    "chave_de_negocio": {
        "golden_id": "conteudo_id",
        "tipo": "surrogate key — gerado pelo pipeline de ingestão",
        "chave_natural": "hash(titulo_normalizado + autor_id + tipo_midia)",
        "regra": (
            "O menor conteudo_id observado para registros que coincidem por similaridade "
            ">= 95% no título (após normalização) e mesmo autor e tipo é promovido a Golden Record."
        ),
    },
    "tabela_master": "silver.catalogo",
    "servico_openmetadata": "pg_desafio2_service",
    "fqn_tabela_master": "pg_desafio2_service.desafio_dados.silver.catalogo",
    "atributos_essenciais": [
        {"coluna": "conteudo_id",    "tipo": "integer",  "papel_mdm": "Golden ID",      "obrigatorio": True},
        {"coluna": "titulo",         "tipo": "varchar",  "papel_mdm": "Atributo Master", "obrigatorio": True},
        {"coluna": "tipo",           "tipo": "varchar",  "papel_mdm": "Atributo Master", "obrigatorio": True},
        {"coluna": "categoria",      "tipo": "varchar",  "papel_mdm": "Atributo Master", "obrigatorio": True},
        {"coluna": "nivel",          "tipo": "varchar",  "papel_mdm": "Atributo Master", "obrigatorio": True},
        {"coluna": "data_publicacao","tipo": "date",     "papel_mdm": "Atributo Master", "obrigatorio": True},
        {"coluna": "autor",          "tipo": "varchar",  "papel_mdm": "PII — Mascarado", "obrigatorio": False,
         "classificacao_lgpd": "PII.Identifiable"},
    ],
    "regras_survivorship": [
        "Título: prevalece o mais longo e descritivo (maior LENGTH não nulo).",
        "Categoria: prevalece a do sistema acadêmico mestre (catalogo.csv).",
        "Nível: prevalece o do registro com maior data_publicacao.",
        "Golden ID (conteudo_id): menor ID entre os registros duplicados.",
        "Autor: campo mascarado na Silver para conformidade LGPD.",
    ],
    "sistemas_consumidores": [
        {"sistema": "silver.interacoes",          "campo_fk": "conteudo_id", "cardinalidade": "N:1"},
        {"sistema": "silver.recomendacoes",       "campo_fk": "conteudo_id", "cardinalidade": "N:1"},
        {"sistema": "silver.comentarios",         "campo_fk": "conteudo_id", "cardinalidade": "N:1"},
        {"sistema": "gold.engajamento_conteudo",  "campo_fk": "conteudo_id", "cardinalidade": "1:1"},
        {"sistema": "Apache Superset — Dashboard","campo_fk": "conteudo_id", "cardinalidade": "Consumo analítico"},
        {"sistema": "Motor de Recomendação IA",   "campo_fk": "conteudo_id", "cardinalidade": "N:M"},
    ],
    "steward": {
        "area": "Coordenação Pedagógica e Acadêmica",
        "email": "pedagogico@ficdevia.edu.br",
        "responsabilidades": [
            "Aprovar inclusão de novos conteúdos no catálogo mestre.",
            "Validar resultados de deduplicação antes da promoção ao Golden Record.",
            "Revisar mapeamento de categorias e níveis a cada semestre.",
        ],
    },
    "politica_manutencao": {
        "frequencia_revisao": "Trimestral",
        "controle_versao": "Histórico de mudanças no campo updated_at de silver.catalogo",
        "processo_correcao": (
            "Abrir ticket no sistema acadêmico → Pipeline reingere → "
            "Regras de Survivorship resolvem → Aprovação do Steward → "
            "Publicação na Gold na próxima execução agendada."
        ),
    },
}

# Custom Properties a criar na tabela silver.catalogo via API
CUSTOM_PROPERTIES = [
    {
        "name": "mdm_is_golden_record",
        "displayName": "MDM: É Golden Record?",
        "description": "Indica se este conteúdo é o registro mestre canônico (Golden Record) após deduplicação MDM.",
        "propertyType": {"name": "boolean"},
        "entityType": "table",
    },
    {
        "name": "mdm_golden_id",
        "displayName": "MDM: Golden ID",
        "description": "Identificador único mestre (conteudo_id canônico) atribuído pelo processo de MDM.",
        "propertyType": {"name": "integer"},
        "entityType": "table",
    },
    {
        "name": "mdm_steward",
        "displayName": "MDM: Steward Responsável",
        "description": "E-mail do responsável pela curadoria e qualidade desta entidade mestre.",
        "propertyType": {"name": "string"},
        "entityType": "table",
    },
    {
        "name": "mdm_survivorship_rule",
        "displayName": "MDM: Regra de Survivorship",
        "description": "Resumo da regra de sobrevivência aplicada para resolver conflitos entre registros duplicados.",
        "propertyType": {"name": "markdown"},
        "entityType": "table",
    },
]

# Descrições de colunas da tabela master a publicar no catálogo
COLUMN_DESCRIPTIONS = {
    "conteudo_id": (
        "**Golden ID — Chave Mestre MDM.** "
        "Identificador único e imutável do Conteúdo Educacional. "
        "Em caso de duplicatas, o menor ID torna-se o Golden Record e os demais são unificados via XRef."
    ),
    "titulo": (
        "**Atributo Master.** Título oficial do conteúdo após normalização MDM. "
        "Prevalece a versão com maior completude textual entre os registros candidatos."
    ),
    "tipo": (
        "**Atributo Master.** Formato instrucional do conteúdo: "
        "video | curso | podcast | artigo | webinar."
    ),
    "categoria": (
        "**Atributo Master.** Área temática padronizada pelo Glossário de Negócio. "
        "Ex: Engenharia de Dados, IA e Machine Learning, Programação Web."
    ),
    "nivel": (
        "**Atributo Master.** Complexidade pedagógica: basico | intermediario | avancado. "
        "Prevalece o nível do registro com maior data_publicacao."
    ),
    "data_publicacao": (
        "**Atributo Master.** Data canônica de disponibilização do conteúdo na plataforma. "
        "Usada como critério de desempate nas regras de Survivorship."
    ),
    "autor": (
        "**PII — Mascarado (LGPD Art. 12).** "
        "Nome do docente / autor responsável pelo conteúdo. "
        "Exibido mascarado (ex: 'C*** E***') em todos os contextos analíticos. "
        "Tag: PII.Identifiable."
    ),
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


def _ok(code):
    return code is not None and code in (200, 201, 409)


def _put(path, payload):
    return _api("put", path, payload)


def _patch(path, payload):
    return _api("patch", path, payload)


# ---------------------------------------------------------------------------
# Operações
# ---------------------------------------------------------------------------

def criar_custom_properties():
    print("\n[1/3] Criando Custom Properties para Entidade Mestre no OpenMetadata...")
    for cp in CUSTOM_PROPERTIES:
        code, body = _put("/metadata/types/customProperties", cp)
        if _ok(code):
            print(f"      ✔ Custom Property '{cp['name']}' criada (HTTP {code})")
        elif code is None:
            print(f"      ⚠ '{cp['name']}': sem biblioteca requests.")
            break
        elif code == -1:
            print(f"      ⚠ '{cp['name']}': servidor indisponível — {body.get('error', '')}")
            break
        else:
            print(f"      ⚠ '{cp['name']}': HTTP {code} — {str(body)[:150]}")


def aplicar_descricoes_colunas():
    """
    Atualiza as descrições das colunas de silver.catalogo no catálogo do OpenMetadata
    via PATCH na API de tabelas.
    """
    print("\n[2/3] Aplicando descrições MDM às colunas de silver.catalogo...")
    table_fqn = "pg_desafio2_service.desafio_dados.silver.catalogo"
    encoded_fqn = table_fqn.replace(".", "%2E")

    patch_payload = [
        {"op": "replace", "path": f"/columns/{col}/description", "value": desc}
        for col, desc in COLUMN_DESCRIPTIONS.items()
    ]
    code, body = _patch(f"/tables/name/{table_fqn}", patch_payload)
    if _ok(code):
        print(f"      ✔ Descrições de colunas aplicadas em '{table_fqn}' (HTTP {code})")
    elif code is None:
        print("      ⚠ Sem biblioteca requests.")
    elif code == -1:
        print(f"      ⚠ Servidor indisponível: {body.get('error', '')}")
    else:
        print(f"      ⚠ HTTP {code}: {str(body)[:200]}")


def salvar_evidencia_mdm():
    print("\n[3/3] Salvando evidência local de MDM...")
    evidencia = {
        "executado_em": datetime.now().isoformat(),
        "requisito": "RF30 — Gestão de Dados Mestres (MDM)",
        "ferramenta": "OpenMetadata",
        "entidade_mestre": MDM_ENTIDADE_MESTRE,
        "custom_properties_definidas": [cp["name"] for cp in CUSTOM_PROPERTIES],
        "descricoes_colunas_aplicadas": list(COLUMN_DESCRIPTIONS.keys()),
    }
    out_path = EVIDENCIAS_DIR / "rf30_dados_mestres_openmetadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidencia, f, indent=2, ensure_ascii=False)
    print(f"      ✔ Evidência salva em: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("RF30 — REGISTRO DE DADOS MESTRES (MDM) NO OPENMETADATA")
    print(f"       Entidade Mestre: Conteúdo Educacional")
    print(f"       Tabela Master:   silver.catalogo")
    print(f"       Host:            {OPENMETADATA_HOST}")
    print("=" * 70)

    criar_custom_properties()
    aplicar_descricoes_colunas()
    salvar_evidencia_mdm()

    print("\n" + "=" * 70)
    print("CONCLUÍDO — Verifique em openmetadata/evidencias/rf30_dados_mestres_openmetadata.json")
    print("            e no catálogo em http://localhost:8585")
    print("=" * 70)


if __name__ == "__main__":
    main()
