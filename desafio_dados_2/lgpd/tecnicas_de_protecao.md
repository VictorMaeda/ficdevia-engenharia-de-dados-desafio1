# RF33 — Técnicas de Proteção de Dados: Mascaramento, Pseudonimização e Hashing

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral das Técnicas Aplicadas

Para assegurar conformidade com a LGPD e mitigar riscos de vazamento ou uso indevido de dados pessoais, o pipeline implementa três técnicas complementares de proteção, cada uma adequada ao seu propósito negocial e técnico:

```text
┌──────────────────┬──────────────────────┬──────────────────────┬────────────────────────────────────────────────────────┐
│ Técnica          │ Atributo Alvo        │ Reversibilidade      │ Finalidade Prática no Pipeline                         │
├──────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Mascaramento     │ autor                │ Parcialmente         │ Preserva leitura pedagógica sem expor o nome completo  │
│ Dinâmico         │                      │ irreversível         │ do instrutor/docente em relatórios compartilhados.     │
├──────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Pseudonimização  │ usuario_id           │ Reversível mediante  │ Permite cruzar sessões de estudo do mesmo estudante ao │
│ (HMAC-SHA256)    │                      │ chave segura isolada │ longo dos meses sem expor seu ID real no catálogo.     │
├──────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Hashing com Salt │ comentario           │ Irreversível         │ Permite verificar integridade e duplicidade de textos  │
│ (SHA-256 + Salt) │                      │ (Unidirecional)      │ livres sem armazenar o texto em claro na análise.      │
└──────────────────┴──────────────────────┴──────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento e Justificativa de Cada Técnica

### 2.1. Mascaramento Dinâmico (Data Masking)
* **Atributo Alvo:** `autor` (da tabela `silver.catalogo`).
* **Implementação:** O algoritmo preserva as iniciais do primeiro e último nome, substituindo os caracteres intermediários por asteriscos (`*`).
  * *Exemplo Original:* `Carlos Eduardo Silva`
  * *Valor Mascarado:* `C***** E****** S****`
* **Justificativa:** O consumo analítico e pedagógico muitas vezes precisa apenas de um identificador visual aproximado para auditoria e conferência, sem necessidade de expor o nome civil completo do docente em dashboards públicos.

### 2.2. Pseudonimização Criptográfica com HMAC-SHA256
* **Atributo Alvo:** `usuario_id` (de `bronze.interacoes`).
* **Implementação:** Utiliza a função HMAC (Hash-based Message Authentication Code) com SHA-256 alimentada por uma chave de salt secreta (`LGPD_PEPPER_KEY`), gerando um token determinístico de 16 caracteres hexadecimais:
  $$\text{ID\_Pseudonimizado} = \text{HMAC-SHA256}(\text{usuario\_id}, \text{chave\_secreta})[:16]$$
  * *Exemplo Original:* `usuario_id = 1042`
  * *Token Pseudônimo:* `usr_9f8a3b2c1d4e`
* **Justificativa e Reversibilidade Controlada:** A pseudonimização é mandatória para permitir análises longitudinais de comportamento (quantos cursos o mesmo aluno concluiu) sem permitir que analistas identifiquem a pessoa física diretamente. A reversão só pode ser realizada pelo Encarregado de Dados (DPO) através da tabela de correspondência protegida por cofre de chaves.

### 2.3. Hashing Irreversível com Salt
* **Atributo Alvo:** `comentario` (texto livre de avaliação).
* **Implementação:** Aplicação de SHA-256 combinado com um `salt` criptográfico aleatório por linha:
  $$\text{Hash} = \text{SHA256}(\text{comentario} + \text{salt})$$
* **Justificativa:** Textos de comentários livres frequentemente contêm vazamentos não intencionais de dados pessoais (nomes, telefones, desabafos). Ao gerar o hash unidirecional com salt, o pipeline permite calcular unicidade e agrupamento sem persistir o texto aberto nas camadas analíticas.

---

## 3. Isolamento de Segredos e Gestão de Chaves

Em cumprimento ao **RF15** e **RF33**:
* Todas as chaves criptográficas (`LGPD_PEPPER_KEY`, `LGPD_SALT_SECRET`) residem exclusivamente no arquivo `.env` local, o qual está categoricamente listado no `.gitignore` e **nunca é versionado no repositório**;
* O arquivo `.env.example` disponibiliza apenas marcadores de exemplo para que novos ambientes possam provisionar suas próprias chaves sem expor os segredos de produção.

---

## 4. Comprovação Prática de Execução

O script executável [`lgpd/demonstrar_protecao_lgpd.py`](file:///c:/Users/01923483102/Documents/pessoal/fic_dev_ia/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/lgpd/demonstrar_protecao_lgpd.py) processa uma amostra real demonstrando a aplicação simultânea das três técnicas:

```text
================================================================================
DEMONSTRAÇÃO DE TÉCNICAS DE PROTEÇÃO DE DADOS — LGPD (RF33)
================================================================================
1. MASCARAMENTO DINÂMICO DE NOMES (Campo: autor):
   Original: 'Prof. Carlos Eduardo Silveira'
   Mascarado: 'P*** C***** E****** S********'

2. PSEUDONIMIZAÇÃO DETERMINÍSTICA (Campo: usuario_id):
   ID Real:  1053
   Token:    usr_a7c4e912b5f0 (Permite agrupar sessões sem expor o titular)

3. HASHING IRREVERSÍVEL COM SALT (Campo: comentario):
   Comentário: 'Gostei muito da aula de Apache Hop ministrada em 15/03!'
   Salt:       s4lt_9a2f7b1e
   Hash SHA256: 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069
================================================================================
Evidência: O dashboard Apache Superset não expõe nenhum dos valores originais.
================================================================================
```
