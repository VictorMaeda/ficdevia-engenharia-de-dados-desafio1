#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: desafio_dados_2/openmetadata/cadastrar_glossario_metadados.py
REQUISITO: RF28 — Catálogo, Classificação e Glossário de Negócio
FINALIDADE: Script para registrar formalmente o Glossário de Negócio, Termos,
            Classificações (Tags) e Vínculos com Ativos no OpenMetadata via API.
            Suporta modo local (geração de payload JSON) e modo API REST.
==============================================================================
"""

import json
import os
import sys
from pathlib import Path
from urllib import request, error

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_METADATA_JSON = BASE_DIR / "openmetadata" / "evidencias" / "glossario_e_termos.json"

OPENMETADATA_HOST = os.getenv("OPENMETADATA_HOST", "http://localhost:8585")
OPENMETADATA_TOKEN = os.getenv("OPENMETADATA_JWT_TOKEN", "")

PAYLOAD_GLOSSARIO = {
    "name": "GlossarioEducacional",
    "displayName": "Glossário Corporativo de Métricas Educacionais",
    "description": "Termos oficiais de negócio, métricas de engajamento e regras de cálculo para a plataforma FIC DEV IA.",
    "owner": {
        "name": "coordenacao_pedagogica",
        "type": "team",
        "displayName": "Coordenação Pedagógica e Acadêmica"
    },
    "terms": [
        {
            "name": "UsuarioAtivo",
            "displayName": "Usuário Ativo",
            "description": "Estudante que registrou ao menos uma interação de consumo no período de referência.",
            "synonyms": ["Active User", "Aluno Engajado"],
            "calculationRule": "COUNT(DISTINCT usuario_id) WHERE data_hora BETWEEN inicio_mes AND fim_mes",
            "owner": "gestao.alunos@ficdevia.edu.br",
            "tags": ["Tier.Tier1_Critical", "DataQuality.Audited"],
            "associatedEntities": [
                "pg_desafio2_service.desafio2.silver.interacoes.usuario_id",
                "pg_desafio2_service.desafio2.gold.engajamento_conteudo.total_interacoes"
            ]
        },
        {
            "name": "TaxaConclusao",
            "displayName": "Taxa de Conclusão",
            "description": "Percentual de interações concluídas integralmente (100% de progresso) sobre o total iniciado.",
            "synonyms": ["Completion Rate", "Taxa de Finalização"],
            "calculationRule": "(SUM(quantidade_conclusoes) / SUM(total_interacoes)) * 100",
            "owner": "diretoria.pedagogica@ficdevia.edu.br",
            "tags": ["Tier.Tier1_Critical"],
            "associatedEntities": [
                "pg_desafio2_service.desafio2.gold.engajamento_conteudo.quantidade_conclusoes",
                "pg_desafio2_service.desafio2.gold.vw_resumo_categoria.taxa_conclusao_geral"
            ]
        },
        {
            "name": "ConversaoRecomendacao",
            "displayName": "Conversão de Recomendação",
            "description": "Proporção de sugestões emitidas pelo motor de IA que resultaram em consumo efetivo pelo estudante.",
            "synonyms": ["Recommendation Conversion", "Aproveitamento do Algoritmo"],
            "calculationRule": "(COUNT(DISTINCT recomendacoes_consumidas) / COUNT(DISTINCT recomendacoes_ativas)) * 100",
            "owner": "ia.recomendacao@ficdevia.edu.br",
            "tags": ["Tier.Tier2_Standard"],
            "associatedEntities": [
                "pg_desafio2_service.desafio2.silver.recomendacoes.status"
            ]
        },
        {
            "name": "TempoMedioEngajamento",
            "displayName": "Tempo Médio de Engajamento por Conteúdo",
            "description": "Duração média em minutos dedicada por sessão de estudo de um título educacional.",
            "synonyms": ["Average Engagement Time", "Tempo Médio de Sessão"],
            "calculationRule": "SUM(tempo_total_segundos) / (SUM(total_interacoes) * 60)",
            "owner": "design.instrucional@ficdevia.edu.br",
            "tags": ["Tier.Tier1_Critical"],
            "associatedEntities": [
                "pg_desafio2_service.desafio2.gold.engajamento_conteudo.tempo_total_segundos"
            ]
        }
    ],
    "classifications": [
        {
            "name": "PII",
            "description": "Classificação de Dados Pessoais e Privacidade sob LGPD",
            "tags": ["Identifiable", "Pseudonymized", "NonPII"]
        },
        {
            "name": "Tier",
            "description": "Nível de criticidade operacional e analítica do ativo",
            "tags": ["Tier1_Critical", "Tier2_Standard", "Tier3_Auxiliary"]
        }
    ]
}


def salvar_payload_local():
    OUTPUT_METADATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(PAYLOAD_GLOSSARIO, f, indent=2, ensure_ascii=False)
    print(f"[OK] Payload do Glossário e Classificações salvo com sucesso em:")
    print(f"     -> {OUTPUT_METADATA_JSON}")


def tentar_publicar_api():
    if not OPENMETADATA_TOKEN:
        print("[INFO] OPENMETADATA_JWT_TOKEN não informado. Publicação via API ignorada (payload salvo localmente).")
        return

    url = f"{OPENMETADATA_HOST}/api/v1/glossaries"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENMETADATA_TOKEN}"
    }

    req = request.Request(url, data=json.dumps(PAYLOAD_GLOSSARIO).encode("utf-8"), headers=headers, method="PUT")
    try:
        with request.urlopen(req, timeout=5) as resp:
            print(f"[OK] Glossário publicado no OpenMetadata com sucesso (Status: {resp.status}).")
    except (error.URLError, error.HTTPError, TimeoutError) as e:
        print(f"[AVISO] Não foi possível conectar ao servidor OpenMetadata em {OPENMETADATA_HOST}: {e}")
        print("        O arquivo local de evidências garante o registro para auditoria.")


def main():
    print("=" * 70)
    print("RF28 — CADASTRO DE GLOSSÁRIO E METADADOS NO OPENMETADATA")
    print("=" * 70)
    salvar_payload_local()
    tentar_publicar_api()
    print("=" * 70)


if __name__ == "__main__":
    main()
