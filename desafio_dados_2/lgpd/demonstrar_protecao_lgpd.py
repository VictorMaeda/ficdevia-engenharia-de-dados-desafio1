#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: demonstrar_protecao_lgpd.py
REQUISITO: RF33 — Mascaramento, Pseudonimização e Hashing
FINALIDADE: Demonstrar na prática a aplicação das 3 técnicas de proteção
            sobre dados pessoais com isolamento de chave/salt.
==============================================================================
"""

import os
import hmac
import hashlib
import re

# Segredo isolado de ambiente (ou valor padrão seguro para teste)
PEPPER_KEY = os.getenv("LGPD_PEPPER_KEY", "segredo_pepper_fic_dev_ia_2026").encode("utf-8")
SALT_SECRET = os.getenv("LGPD_SALT_SECRET", "salt_corporativo_desafio2_k9")

def mascarar_nome(nome: str) -> str:
    """Substitui caracteres centrais das palavras por asteriscos."""
    if not nome:
        return "N***"
    palavras = nome.strip().split()
    mascaradas = []
    for p in palavras:
        if len(p) <= 2:
            mascaradas.append(p[0] + "*")
        else:
            mascaradas.append(p[0] + "*" * (len(p) - 1))
    return " ".join(mascaradas)

def pseudonimizar_usuario(usuario_id: int) -> str:
    """Gera token determinístico curto usando HMAC-SHA256."""
    msg = str(usuario_id).encode("utf-8")
    token_hex = hmac.new(PEPPER_KEY, msg, digestmod=hashlib.sha256).hexdigest()[:12]
    return f"usr_{token_hex}"

def gerar_hash_salt(texto: str, salt: str = None) -> tuple[str, str]:
    """Gera hash SHA-256 irreversível com salt."""
    if not salt:
        salt = hashlib.md5((SALT_SECRET + texto[:5]).encode("utf-8")).hexdigest()[:8]
    payload = f"{salt}:{texto}".encode("utf-8")
    hash_sha256 = hashlib.sha256(payload).hexdigest()
    return hash_sha256, salt

def main():
    print("=" * 80)
    print(" DEMONSTRAÇÃO DE TÉCNICAS DE PROTEÇÃO DE DADOS — LGPD (RF33)")
    print("=" * 80)

    # 1. Mascaramento
    nomes_teste = [
        "Prof. Carlos Eduardo Silveira",
        "Dra. Maria Helena Costa",
        "João da Silva"
    ]
    print("\n1. MASCARAMENTO DINÂMICO DE NOMES (Campo: autor):")
    for n in nomes_teste:
        print(f"   Original:  '{n}'")
        print(f"   Mascarado: '{mascarar_nome(n)}'\n")

    # 2. Pseudonimização
    ids_teste = [1042, 1053, 2088, 1053] # Note 1053 repetido para demonstrar determinismo
    print("2. PSEUDONIMIZAÇÃO DETERMINÍSTICA (Campo: usuario_id):")
    for uid in ids_teste:
        print(f"   ID Real: {uid:4d}  ->  Pseudônimo: {pseudonimizar_usuario(uid)}")

    # 3. Hashing com Salt
    comentarios_teste = [
        "Gostei muito da aula de Apache Hop ministrada em 15/03!",
        "Excelente explicação sobre a modelagem dimensional no Superset."
    ]
    print("\n3. HASHING IRREVERSÍVEL COM SALT (Campo: comentario):")
    for c in comentarios_teste:
        h, s = gerar_hash_salt(c)
        print(f"   Comentário: '{c[:45]}...'")
        print(f"   Salt:        {s}")
        print(f"   Hash SHA256: {h}\n")

    print("=" * 80)
    print(" [SUCESSO] Demonstração das técnicas do RF33 finalizada com êxito!")
    print("=" * 80)

if __name__ == "__main__":
    main()
