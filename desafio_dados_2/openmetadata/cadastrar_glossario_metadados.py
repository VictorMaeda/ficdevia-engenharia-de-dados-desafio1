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

DEFAULT_BOT_TOKEN = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJlbWFpbCI6ImluZ2VzdGlvbi1ib3RAb3Blbm1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3OTA2NTA4ODcsImV4cCI6bnVsbH0.M_n_0uOPhIgbXq-k7I1REzMJ1MM9zzTyjV7uHgRjqKITpV1HfmLiZPeuxitUJ7x6H4fMspQNcEIyGe5zqAKHltrWilNP5KdlMn5XxsBglzzAKpr4QF3gowbF5GfyOLiRxBtr_iV0C8t2QFg_nHz0WLRVWeBzYLjcNjikwAc4pTuR12iIj5uo-KYvizV4kq6rKrEEVG6-H8ojae4YkDc1tcJzwx2OJ1eBxpoqF-VLTFtvsMWsgaVoxmNwi7D6eOIN7QUHklMiOmIk32HZehJD9OyqU0cNC36imNA0Syo8JINlSQMHBu4H1CjOamjnhevbjrSg7idkWBTvE1yrw26PEg"
OPENMETADATA_HOST = os.getenv("OPENMETADATA_HOST", "http://localhost:8585")
OPENMETADATA_TOKEN = os.getenv("OPENMETADATA_JWT_TOKEN", DEFAULT_BOT_TOKEN)

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
    try:
        import requests
        import base64
    except ImportError:
        print("[AVISO] Pacote 'requests' não encontrado. Pulando publicação via API.")
        return

    host = OPENMETADATA_HOST
    token = OPENMETADATA_TOKEN

    if not token:
        try:
            login_resp = requests.post(
                f"{host}/api/v1/users/login",
                json={
                    "email": "admin@openmetadata.org",
                    "password": base64.b64encode(b"admin").decode()
                },
                timeout=5
            )
            if login_resp.status_code == 200:
                token = login_resp.json().get("accessToken", "")
                print("[OK] Autenticado com sucesso como admin no OpenMetadata.")
        except Exception as e:
            pass

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url_g = f"{host}/api/v1/glossaries"
    payload_g = {
        "name": PAYLOAD_GLOSSARIO["name"],
        "displayName": PAYLOAD_GLOSSARIO["displayName"],
        "description": PAYLOAD_GLOSSARIO["description"]
    }

    try:
        resp = requests.put(url_g, json=payload_g, headers=headers, timeout=5)
        if resp.status_code in (200, 201):
            print(f"[OK] Glossário '{PAYLOAD_GLOSSARIO['name']}' registrado no OpenMetadata (Status: {resp.status_code}).")
            glossary_fqn = resp.json().get("name", PAYLOAD_GLOSSARIO["name"])

            for term in PAYLOAD_GLOSSARIO["terms"]:
                payload_t = {
                    "name": term["name"],
                    "displayName": term["displayName"],
                    "description": term["description"],
                    "glossary": glossary_fqn
                }
                resp_t = requests.put(f"{host}/api/v1/glossaryTerms", json=payload_t, headers=headers, timeout=5)
                if resp_t.status_code in (200, 201):
                    print(f"     -> Termo '{term['displayName']}' publicado com sucesso.")
                else:
                    print(f"     [AVISO] Falha ao publicar termo '{term['displayName']}' (Status: {resp_t.status_code}).")
        else:
            print(f"[INFO] Servidor OpenMetadata em {host} retornou status {resp.status_code}. Evidências locais preservadas.")
    except Exception as e:
        print(f"[AVISO] Não foi possível conectar ao servidor OpenMetadata em {host}: {e}")
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
