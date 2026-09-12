"""
Gera dados FICTÍCIOS de entrada para o pipeline, simulando as fontes
descritas no enunciado (seção 6):
  - catalogo_conteudos.csv
  - usuarios.csv               (fonte extra, para dar contexto aos usuários)
  - interacoes_usuarios.json
  - comentarios_avaliacoes.json

Propositalmente injeta alguns registros "sujos" (duplicados, incompletos,
inválidos) para que a etapa de validação (RF03) tenha o que classificar.

Uso:
    python -m scripts.gerar_dados_ficticios
"""
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

fake = Faker("pt_BR")
random.seed(42)
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
BRUTOS_DIR = BASE_DIR / "dados" / "brutos"

TIPOS = ["curso", "video", "artigo", "podcast"]
NIVEIS = ["basico", "intermediario", "avancado"]
CATEGORIAS = [
    "Banco de Dados", "Inteligencia Artificial", "Programacao",
    "Ciencia de Dados", "DevOps", "Redes", "Seguranca da Informacao",
]
TIPOS_INTERACAO = [
    "visualizacao", "inicio", "conclusao", "curtida", "avaliacao", "compartilhamento",
]

N_USUARIOS = 40
N_CONTEUDOS = 60
N_INTERACOES = 500
N_COMENTARIOS = 120


def gerar_catalogo():
    registros = []
    for cid in range(1, N_CONTEUDOS + 1):
        categoria = random.choice(CATEGORIAS)
        titulo = f"{fake.catch_phrase()} em {categoria}"
        registros.append({
            "conteudo_id": cid,
            "titulo": titulo,
            "tipo": random.choice(TIPOS),
            "categoria": categoria,
            "nivel": random.choice(NIVEIS),
            "carga_horaria_min": random.randint(5, 240),
            "data_publicacao": fake.date_between(start_date="-2y", end_date="today").isoformat(),
            "descricao": fake.paragraph(nb_sentences=3),
            "autor": fake.name(),
        })

    # --- injeta sujeira proposital ---
    # duplicado exato
    registros.append(dict(registros[0]))
    # incompleto (sem descricao e autor)
    incompleto = dict(registros[5])
    incompleto["conteudo_id"] = N_CONTEUDOS + 1
    incompleto["descricao"] = ""
    incompleto["autor"] = ""
    registros.append(incompleto)
    # inválido (tipo fora do domínio, carga horária negativa)
    invalido = dict(registros[10])
    invalido["conteudo_id"] = N_CONTEUDOS + 2
    invalido["tipo"] = "webinar-ao-vivo"
    invalido["carga_horaria_min"] = -15
    registros.append(invalido)
    # inválido (data mal formatada)
    invalido2 = dict(registros[15])
    invalido2["conteudo_id"] = N_CONTEUDOS + 3
    invalido2["data_publicacao"] = "31/02/2026"
    registros.append(invalido2)
    # com espaços/maiúsculas inconsistentes (tratamento, não invalidação)
    sujo = dict(registros[20])
    sujo["conteudo_id"] = N_CONTEUDOS + 4
    sujo["titulo"] = "   Título   Com Espaços Extras  "
    sujo["tipo"] = "CURSO"
    sujo["nivel"] = " Básico "
    registros.append(sujo)

    caminho = BRUTOS_DIR / "catalogo_conteudos.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)
    print(f"[gerado] {caminho} ({len(registros)} registros)")
    return registros


def gerar_usuarios():
    registros = []
    for uid in range(1, N_USUARIOS + 1):
        registros.append({
            "usuario_id": uid,
            "nome": fake.name(),
            "email": fake.unique.email(),
            "data_cadastro": fake.date_between(start_date="-3y", end_date="today").isoformat(),
        })

    # duplicado
    registros.append(dict(registros[1]))
    # incompleto (sem email)
    incompleto = dict(registros[3])
    incompleto["usuario_id"] = N_USUARIOS + 1
    incompleto["email"] = ""
    registros.append(incompleto)
    # inválido (email mal formatado)
    invalido = dict(registros[6])
    invalido["usuario_id"] = N_USUARIOS + 2
    invalido["email"] = "nao-e-um-email"
    registros.append(invalido)

    caminho = BRUTOS_DIR / "usuarios.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)
    print(f"[gerado] {caminho} ({len(registros)} registros)")
    return registros


def gerar_interacoes(usuarios, conteudos):
    ids_usuarios = [u["usuario_id"] for u in usuarios[:N_USUARIOS]]
    ids_conteudos = [c["conteudo_id"] for c in conteudos[:N_CONTEUDOS]]

    registros = []
    for _ in range(N_INTERACOES):
        tipo = random.choice(TIPOS_INTERACAO)
        registro = {
            "usuario_id": random.choice(ids_usuarios),
            "conteudo_id": random.choice(ids_conteudos),
            "tipo_interacao": tipo,
            "data_hora": fake.date_time_between(start_date="-6M", end_date="now").isoformat(),
            "tempo_consumido_min": round(random.uniform(0, 120), 1),
            "percentual_conclusao": round(random.uniform(0, 100), 1),
            "avaliacao": random.randint(1, 5) if tipo == "avaliacao" else None,
        }
        registros.append(registro)

    # --- sujeira proposital ---
    dup = dict(registros[0])
    registros.append(dup)  # duplicado exato

    incompleto = dict(registros[1])
    incompleto["data_hora"] = None
    registros.append(incompleto)

    invalido_ref = dict(registros[2])
    invalido_ref["conteudo_id"] = 99999  # referência inexistente
    registros.append(invalido_ref)

    invalido_dominio = dict(registros[3])
    invalido_dominio["tipo_interacao"] = "compra"  # fora do domínio
    registros.append(invalido_dominio)

    invalido_percentual = dict(registros[4])
    invalido_percentual["percentual_conclusao"] = 150  # fora do intervalo
    registros.append(invalido_percentual)

    caminho = BRUTOS_DIR / "interacoes_usuarios.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=str)
    print(f"[gerado] {caminho} ({len(registros)} registros)")
    return registros


def gerar_comentarios(usuarios, conteudos):
    ids_usuarios = [u["usuario_id"] for u in usuarios[:N_USUARIOS]]
    ids_conteudos = [c["conteudo_id"] for c in conteudos[:N_CONTEUDOS]]
    tags_possiveis = ["didatico", "iniciante", "avancado", "python", "sql", "pratico", "denso"]

    registros = []
    for _ in range(N_COMENTARIOS):
        registros.append({
            "usuario_id": random.choice(ids_usuarios),
            "conteudo_id": random.choice(ids_conteudos),
            "avaliacao": random.randint(1, 5),
            "comentario": fake.sentence(nb_words=10),
            "tags": random.sample(tags_possiveis, k=random.randint(1, 3)),
            "data": fake.date_between(start_date="-6M", end_date="today").isoformat(),
        })

    # sujeira proposital
    invalido = dict(registros[0])
    invalido["avaliacao"] = 9  # fora do intervalo 1-5
    registros.append(invalido)

    incompleto = dict(registros[1])
    incompleto["comentario"] = ""
    registros.append(incompleto)

    caminho = BRUTOS_DIR / "comentarios_avaliacoes.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=str)
    print(f"[gerado] {caminho} ({len(registros)} registros)")
    return registros


def main():
    BRUTOS_DIR.mkdir(parents=True, exist_ok=True)
    conteudos = gerar_catalogo()
    usuarios = gerar_usuarios()
    gerar_interacoes(usuarios, conteudos)
    gerar_comentarios(usuarios, conteudos)
    print("\nDados fictícios gerados com sucesso em dados/brutos/.")


if __name__ == "__main__":
    main()
