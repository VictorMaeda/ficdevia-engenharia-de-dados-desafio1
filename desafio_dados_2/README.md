# Desafio Prático 2 — Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais

**Curso:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Versão:** 1.0 — 2026  
**Branch:** `lor-superset`

---

## Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Registro de Versões das Ferramentas (RF15)](#2-registro-de-versões-das-ferramentas-rf15)
3. [Pré-requisitos](#3-pré-requisitos)
4. [Configuração Inicial](#4-configuração-inicial)
5. [Guia Completo de Execução — Ponta a Ponta](#5-guia-completo-de-execução--ponta-a-ponta)
6. [Executar Etapas Isoladas](#6-executar-etapas-isoladas)
7. [Mapeamento de Requisitos e Entregáveis](#7-mapeamento-de-requisitos-e-entregáveis)
8. [Estrutura de Diretórios](#8-estrutura-de-diretórios)
9. [Governança e LGPD](#9-governança-e-lgpd)
10. [Roteiro para Apresentação](#10-roteiro-para-apresentação)

---

## 1. Visão Geral e Arquitetura

Este projeto evolui a solução do **Desafio Prático 1**, implementando um pipeline automatizado, governado e escalável com dados organizados nas camadas **Bronze**, **Silver** e **Gold** (Arquitetura Medallion).

### Arquitetura Híbrida (ETL + ELT)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       ARQUITETURA UNIFICADA — DESAFIO 2                         │
│                                                                                 │
│   FONTES (Desafio 1)                                                            │
│   catalogo.csv │ interacoes.json │ comentarios.json │ PostgreSQL public.*       │
│          │                                                                      │
│          ▼  [Apache Hop — ETL: Extrai e carrega bruto]                          │
│   ┌─────────────────────────────────────────────────────┐                      │
│   │  CAMADA BRONZE (schemas bronze.*)                   │                      │
│   │  Cópia fiel com campos de auditoria:                │                      │
│   │  origem_arquivo, data_hora_ingestao, execucao_id    │                      │
│   └─────────────────────────────────────────────────────┘                      │
│          │                                                                      │
│          ▼  [Apache Hop — ELT: Transforma no banco]                             │
│   ┌─────────────────────────────────────────────────────┐                      │
│   │  CAMADA SILVER (schemas silver.*)                   │                      │
│   │  Dados padronizados, tipados, deduplicados           │                      │
│   │            │                                        │                      │
│   │            ▼ Registros inválidos                    │                      │
│   │  ┌─────────────────────────┐                        │                      │
│   │  │  QUARENTENA (schema     │                        │                      │
│   │  │  quarentena.*)          │                        │                      │
│   │  │  3 tipos de falha (RF23)│                        │                      │
│   │  └─────────────────────────┘                        │                      │
│   └─────────────────────────────────────────────────────┘                      │
│          │                                                                      │
│          ▼  [exportar_parquet.py — RF24]                                        │
│   Parquet particionado por ano_mes (Snappy)                                    │
│          │                                                                      │
│          ▼  [Apache Beam — RF25]                                                │
│   DirectRunner / SparkRunner → beam/saida/direct/*.parquet                     │
│          │                                                                      │
│          ▼  [carregar_gold.py — RF26]                                           │
│   ┌─────────────────────────────────────────────────────┐                      │
│   │  CAMADA GOLD (schema gold.*)                        │                      │
│   │  engajamento_conteudo │ engajamento_conteudo_mensal │                      │
│   │  vw_resumo_categoria  │ vw_ranking_engajamento      │                      │
│   │  vw_conteudos_atencao                               │                      │
│   │         │                                           │                      │
│   │         ▼ Quality Gate (RF31)                       │                      │
│   │  5 Testes: Q01-Q05 (bloqueia se crítico)            │                      │
│   └─────────────────────────────────────────────────────┘                      │
│          │                                                                      │
│          ├──► [SQL Lab + Datasets Virtuais — RF17]                              │
│          │                                                                      │
│          └──► [Apache Superset — RF16, RF18]                                   │
│               Dashboard │ Filtros Cruzados │ Alertas                           │
│                                                                                 │
│   GOVERNANÇA TRANSVERSAL (OpenMetadata — RF27/28/29)                           │
│   Catálogo │ Glossário (4 termos) │ Linhagem │ Dados Mestres │ LGPD            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Justificativa da Arquitetura Híbrida

A solução adota **Arquitetura Híbrida (ETL → ELT)**:

| Etapa | Abordagem | Justificativa |
|-------|-----------|---------------|
| Bronze (ingestão) | **ETL** | Extrai e transforma minimamente antes de carregar — preserva campos de auditoria |
| Silver (conformidade) | **ELT** | Carrega bruto e transforma dentro do PostgreSQL — aproveita power do banco |
| Gold (agregação) | **ELT** | Cálculos pesados delegados ao Apache Beam + SQL no PostgreSQL |

---

## 2. Registro de Versões das Ferramentas (RF15)

| Componente | Ferramenta / Imagem | Versão Homologada |
|---|---|---|
| **Banco Relacional** | PostgreSQL + pgvector | `16.0` (`pgvector/pgvector:pg16`) |
| **Banco NoSQL** | MongoDB | `7.0` |
| **Orquestração e ETL** | Apache Hop | `2.10.0` / Java 17 |
| **Processamento Distribuído** | Apache Beam | `2.76.0` |
| **Formato Colunar** | Apache PyArrow | `25.0.1` |
| **BI e Dashboard** | Apache Superset | `4.1.0` |
| **Governança** | OpenMetadata | `1.3.1` (especificação) |
| **Python** | CPython | `3.11+` |

---

## 3. Pré-requisitos

### Ferramentas obrigatórias

| Ferramenta | Versão mínima | Verificação |
|---|---|---|
| Python | 3.11 | `python3 --version` |
| Docker | 24.x | `docker --version` |
| Docker Compose | 2.x (plugin) | `docker compose version` |
| Git | 2.x | `git --version` |
| psql (opcional) | 16 | `psql --version` |

---

## 4. Configuração Inicial

### 4.1 Clonar e acessar o projeto

```bash
# O projeto já está no branch lor-superset
git checkout lor-superset

# Navegar para a raiz do repositório
cd ficdevia-engenharia-de-dados-desafio1
```

### 4.2 Criar o arquivo `.env`

**Opção A — Usar .env da raiz do repositório (Desafio 1 + 2 integrado):**
```bash
cp .env.example .env
# Edite o arquivo .env com seus valores reais
nano .env
```

**Opção B — Usar .env somente para o Desafio 2:**
```bash
cp desafio_dados_2/.env.example desafio_dados_2/.env
nano desafio_dados_2/.env
```

**Configurações mínimas obrigatórias no `.env`:**
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=desafio_dados
POSTGRES_USER=desafio_user
POSTGRES_PASSWORD=ESCOLHA_UMA_SENHA_FORTE

# Chaves LGPD (RF33) — mantenha em segredo
LGPD_PEPPER_KEY=seu_pepper_secreto_aqui
LGPD_SALT_SECRET=seu_salt_secreto_aqui

# Superset
SUPERSET_SECRET_KEY=gere_com_openssl_rand_base64_32
SUPERSET_ADMIN_PASSWORD=ESCOLHA_UMA_SENHA_FORTE
```

### 4.3 Criar e ativar ambiente virtual Python

```bash
# Na raiz do repositório (ou dentro de desafio_dados_2/)
python3 -m venv .venv

# Linux/macOS:
source .venv/bin/activate

# Windows (PowerShell):
# .\.venv\Scripts\Activate.ps1
```

### 4.4 Instalar dependências Python

```bash
# Para o Desafio 2:
pip install -r desafio_dados_2/requirements.txt

# Para o Desafio 1 + 2 integrado:
pip install -r requirements.txt
pip install -r desafio_dados_2/requirements.txt
```

---

## 5. Guia Completo de Execução — Ponta a Ponta

> **Importante:** As etapas têm dependências. O script `executar_pipeline_completo.sh` gerencia isso automaticamente. Se preferir executar manualmente, siga a ordem abaixo.

### Passo 1 — Subir os serviços Docker (Infraestrutura)

Execute a partir da **raiz do repositório** (usa o `docker-compose.yml` principal que tem PostgreSQL + MongoDB + Superset):

```bash
# Na raiz do repositório:
docker compose up -d

# Verificar se todos os serviços subiram:
docker compose ps
```

**Aguardar** até que os healthchecks passem (≈ 30 segundos). Os serviços disponíveis serão:

| Serviço | Endereço |
|---|---|
| PostgreSQL | `localhost:5432` |
| MongoDB | `localhost:27017` |
| Apache Superset | `http://localhost:8088` |

### Passo 2 — Inicializar os Schemas do Desafio 2 (DDL idempotente)

```bash
# Linux/macOS:
cat desafio_dados_2/sql/criar_banco.sql | \
  docker exec -i desafio_dados_postgres \
  psql -U desafio_user -d desafio_dados

# Windows (PowerShell):
Get-Content desafio_dados_2\sql\criar_banco.sql -Raw | `
  docker exec -i desafio_dados_postgres `
  psql -U desafio_user -d desafio_dados
```

Este comando cria os schemas `bronze`, `silver`, `quarentena`, `gold` e `qualidade` com todas as tabelas e views. É **idempotente** — pode ser executado múltiplas vezes sem erro.

### Passo 3 — Executar o Pipeline do Desafio 1 (dados de origem)

```bash
# Ativa o venv se ainda não estiver ativo
source .venv/bin/activate

# Executa o pipeline completo do Desafio 1
python -m src.main
```

Isso popula as tabelas `public.conteudos`, `public.interacoes`, `public.recomendacoes` e os dados de origem.

### Passo 4 — Carga Bronze e Exportação de Amostras (RF20, RF23, RF34)

```bash
python desafio_dados_2/dados/carregar_e_exportar_amostras.py
```

Este script:
- Lê `catalogo.csv`, `interacoes.json` e `comentarios.json`
- Insere em `bronze.catalogo`, `bronze.interacoes`, `bronze.comentarios`
- Simula 3 falhas de quarentena (regra inválida, arquivo corrompido, timeout de conexão)
- Exporta amostras físicas para `dados/bronze/`, `dados/silver/`, `dados/gold/`, `dados/quarentena/`

### Passo 5 — Exportar Parquet e Medir Benchmark (RF24)

```bash
python desafio_dados_2/beam/exportar_parquet.py
```

Gera:
- `dados/silver/interacoes.csv` — referência CSV
- `dados/silver/interacoes_parquet/ano_mes=*/` — Parquet particionado por mês (Snappy)
- Imprime comparativo de tamanho e tempo de leitura CSV vs Parquet

### Passo 6 — Pipeline Apache Beam com DirectRunner (RF25)

```bash
python desafio_dados_2/beam/pipeline_beam.py \
  --input "desafio_dados_2/dados/silver/interacoes_parquet" \
  --output "desafio_dados_2/beam/saida/direct/engajamento" \
  --runner DirectRunner
```

Lê Parquet da Silver, agrega por `conteudo_id` e grava em Parquet na pasta `beam/saida/direct/`.

**Executar com SparkRunner (opcional, requer Spark instalado):**
```bash
python desafio_dados_2/beam/pipeline_beam.py \
  --input "desafio_dados_2/dados/silver/interacoes_parquet" \
  --output "desafio_dados_2/beam/saida/spark/engajamento" \
  --runner SparkRunner \
  --spark_master "local[2]"
```

### Passo 7 — Carregar a Camada Gold (RF26)

```bash
python desafio_dados_2/beam/carregar_gold.py
```

Lê os Parquet do Beam, faz JOIN com `silver.catalogo` e popula:
- `gold.engajamento_conteudo` — KPIs consolidados por conteúdo
- `gold.engajamento_conteudo_mensal` — série temporal por mês e conteúdo

A carga é **atômica** (só commita se todas as validações passarem).

### Passo 8 — Testes de Qualidade / Quality Gate (RF31)

```bash
python desafio_dados_2/qualidade/executar_testes.py
```

Executa 5 testes automatizados:

| Código | Dimensão | Severidade |
|--------|----------|-----------|
| Q01_COMPLETUDE | Completude | **CRÍTICA** |
| Q02_VALIDADE_PERCENTUAL | Validade | ALTA |
| Q03_UNICIDADE_CATALOGO | Unicidade | **CRÍTICA** |
| Q04_CONSISTENCIA_CONCLUSAO | Consistência | MÉDIA |
| Q05_INTEGRIDADE_REFERENCIAL | Integridade Referencial | **CRÍTICA** |

Se qualquer teste CRÍTICO falhar, o script retorna **exit code 1** e bloqueia a publicação da Gold.

### Passo 9 — Demonstração de Proteção de Dados (RF33)

```bash
python desafio_dados_2/lgpd/demonstrar_protecao_lgpd.py
```

Demonstra as 3 técnicas de proteção:
1. **Mascaramento** — nomes com asteriscos (campo `autor`)
2. **Pseudonimização** — HMAC-SHA256 determinístico (campo `usuario_id`)
3. **Hashing com Salt** — SHA-256 irreversível (campo `comentario`)

### Passo 10 — Registrar Glossário no OpenMetadata (RF28)

```bash
python desafio_dados_2/openmetadata/cadastrar_glossario_metadados.py
```

> Se a instância OpenMetadata não estiver disponível, o script registra as definições localmente em `openmetadata/evidencias/`.

### Passo 11 — Acessar o Apache Superset (RF16, RF17, RF18)

1. Acesse: **http://localhost:8088**
2. Credenciais: `admin` / `troque_esta_senha` (ou conforme seu `.env`)
3. No **SQL Lab**, execute as consultas de `desafio_dados_2/sql/sql_lab.sql`
4. Salve as consultas 1 e 2 como **Datasets Virtuais** no Superset
5. Crie o dashboard com os 9 gráficos conforme `superset/exportacao_e_evidencias/`
6. Configure os **filtros cruzados** e o **alerta** conforme `superset/exportacao_e_evidencias/rf18_filtros_e_alertas.md`

---

## 6. Executar Etapas Isoladas

Use o script unificado para executar qualquer etapa individualmente:

```bash
# Dar permissão de execução (uma única vez)
chmod +x desafio_dados_2/executar_pipeline_completo.sh

# Executar tudo (ponta a ponta)
./desafio_dados_2/executar_pipeline_completo.sh

# Executar apenas uma etapa
./desafio_dados_2/executar_pipeline_completo.sh parquet
./desafio_dados_2/executar_pipeline_completo.sh beam
./desafio_dados_2/executar_pipeline_completo.sh gold
./desafio_dados_2/executar_pipeline_completo.sh qualidade
./desafio_dados_2/executar_pipeline_completo.sh lgpd
./desafio_dados_2/executar_pipeline_completo.sh openmetadata
./desafio_dados_2/executar_pipeline_completo.sh amostras
```

---

## 7. Mapeamento de Requisitos e Entregáveis

| Req | Descrição | Artefatos | Status |
|-----|-----------|-----------|--------|
| **RF15** | Continuidade, configurações e versões | `.env.example`, `project-config.json`, este README | ✅ |
| **RF16** | Storytelling executivo | `documentacao/storytelling.md`, `documentacao/storytelling.pdf` | ✅ |
| **RF17** | SQL Lab e datasets virtuais (3 consultas, 2 datasets) | `sql/sql_lab.sql`, `sql/camada_gold.sql` | ✅ |
| **RF18** | Filtros cruzados e alerta configurado | `superset/exportacao_e_evidencias/rf18_filtros_e_alertas.md` | ✅ |
| **RF19** | Definição da arquitetura ETL/ELT/Híbrida | `documentacao/arquitetura.md`, `documentacao/arquitetura.pdf` | ✅ |
| **RF20** | Pipeline Bronze no Apache Hop | `hop/pipelines/bronze_*.hpl`, `dados/bronze/` | ✅ |
| **RF21** | Pipeline Silver e padronização | `hop/pipelines/silver_*.hpl`, `dados/silver/` | ✅ |
| **RF22** | Workflow e orquestração automatizada | `hop/workflows/workflow_master_pipeline.hwf` | ✅ |
| **RF23** | Erros, quarentena (3 falhas) e recuperação | `hop/evidencias/rf23_quarentena_e_erros.md`, `dados/quarentena/` | ✅ |
| **RF24** | Parquet particionado e benchmark | `beam/exportar_parquet.py`, `beam/evidencias/rf24_parquet.md` | ✅ |
| **RF25** | Apache Beam (DirectRunner + SparkRunner) | `beam/pipeline_beam.py`, `beam/evidencias/rf25_beam.md` | ✅ |
| **RF26** | Camada Gold para consumo analítico | `sql/camada_gold.sql`, `dados/gold/`, `documentacao/rf26_gold.md` | ✅ |
| **RF27** | OpenMetadata implantação e integração | `openmetadata/ingestao_postgres.yaml`, `openmetadata/evidencias/` | ✅ |
| **RF28** | Catálogo, classificação e glossário (4 termos) | `openmetadata/evidencias/rf28_glossario_e_classificacoes.md` | ✅ |
| **RF29** | Linhagem ponta a ponta | `documentacao/linhagem.md`, `openmetadata/evidencias/rf29_linhagem.md` | ✅ |
| **RF30** | Dados mestres (MDM — entidade Conteúdo) | `documentacao/dados_mestres.md`, `documentacao/dados_mestres.pdf` | ✅ |
| **RF31** | Qualidade de dados (5 testes + gate Gold) | `qualidade/regras.md`, `qualidade/executar_testes.py` | ✅ |
| **RF32** | Inventário LGPD e ROPA | `lgpd/inventario_de_dados.md` | ✅ |
| **RF33** | Mascaramento, pseudonimização e hashing | `lgpd/tecnicas_de_protecao.md`, `lgpd/demonstrar_protecao_lgpd.py` | ✅ |
| **RF34** | Evidências e critérios de aceite | Todos os artefatos acima | ✅ |

---

## 8. Estrutura de Diretórios

```
desafio_dados_2/
├── README.md                                 ← Guia mestre (este arquivo)
├── requirements.txt                          ← Dependências Python
├── project-config.json                       ← Config Apache Hop (variáveis de projeto)
├── docker-compose.yml                        ← Infraestrutura standalone do Desafio 2
├── .env.example                              ← Template de variáveis (copie para .env)
├── executar_pipeline_completo.sh             ← Script unificado de execução
│
├── dados/
│   ├── entrada/                              ← Fontes do Desafio 1 (catalogo.csv, interacoes.json, comentarios.json)
│   ├── bronze/                               ← Amostras auditadas da ingestão bruta
│   ├── silver/                               ← Dados padronizados + Parquet particionado
│   ├── gold/                                 ← Tabelas e visões analíticas exportadas
│   └── quarentena/                           ← Registros inválidos com causa e timestamp
│       (carregar_e_exportar_amostras.py)     ← Script de carga Bronze + exportação de amostras
│
├── hop/
│   ├── environments/                         ← Config de ambiente Hop (local.example.json)
│   ├── metadata/rdbms/                       ← Conexão PostgreSQL (pg_desafio2.json)
│   ├── pipelines/                            ← Pipelines HPL (bronze_*.hpl, silver_*.hpl)
│   ├── workflows/                            ← Workflows HWF (workflow_master_pipeline.hwf)
│   └── evidencias/rf23_quarentena_e_erros.md ← Evidências de erro e recuperação
│
├── beam/
│   ├── pipeline.py                           ← Pipeline Beam (DirectRunner)
│   ├── pipeline_beam.py                      ← Pipeline Beam (Direct + Spark)
│   ├── exportar_parquet.py                   ← Silver → Parquet + benchmark (RF24)
│   ├── carregar_gold.py                      ← Parquet Beam → Gold PostgreSQL (RF26)
│   ├── saida/                                ← Parquet gerado pelo Beam
│   └── evidencias/                           ← rf24_parquet.md, rf25_beam.md
│
├── sql/
│   ├── criar_banco.sql                       ← DDL idempotente de todos os schemas e tabelas
│   ├── camada_gold.sql                       ← Modelagem Gold e visões analíticas
│   └── sql_lab.sql                           ← 3 consultas SQL Lab + 2 datasets virtuais (RF17)
│
├── superset/
│   ├── montar_dashboard_superset.py          ← Script de montagem via API do Superset
│   └── exportacao_e_evidencias/
│       ├── dashboard_desafio2_engajamento.zip ← Export nativo do Superset
│       ├── rf18_filtros_e_alertas.md         ← Evidências de filtros cruzados e alerta
│       └── dashboard_export_config.json      ← Metadados e JSON dos charts
│
├── openmetadata/
│   ├── ingestao_postgres.yaml                ← Spec do conector PostgreSQL
│   ├── cadastrar_glossario_metadados.py      ← Script de cadastro via API
│   ├── linhagem_pipeline.json                ← Definição manual de linhagem
│   └── evidencias/
│       ├── rf27_implantacao_e_governanca.md  ← Implantação e política anti-Data Swamp
│       ├── rf28_glossario_e_classificacoes.md← 4 Termos de negócio e sensibilidade
│       ├── rf29_linhagem.md                  ← Linhagem ponta a ponta
│       └── glossario_e_termos.json           ← Termos canônicos (JSON)
│
├── qualidade/
│   ├── regras.md                             ← Especificação formal dos 5 testes (Q01–Q05)
│   ├── executar_testes.py                    ← Quality Gate automático (RF31)
│   └── resultados/                           ← Logs JSON históricos de execução
│
├── lgpd/
│   ├── inventario_de_dados.md                ← ROPA, bases legais, retenção e finalidade
│   ├── tecnicas_de_protecao.md               ← Mascaramento, HMAC e hashing (RF33)
│   └── demonstrar_protecao_lgpd.py           ← Demo das 3 técnicas de proteção
│
└── documentacao/
    ├── arquitetura.md / arquitetura.pdf       ← ETL/ELT/Híbrida (RF19)
    ├── linhagem.md / linhagem.pdf             ← Diagrama de linhagem (RF29)
    ├── storytelling.md / storytelling.pdf     ← Narrativa executiva (RF16)
    ├── dados_mestres.md / dados_mestres.pdf   ← MDM — Entidade Conteúdo (RF30)
    ├── rf26_gold.md                           ← Documentação da Camada Gold
    ├── rf31_qualidade.md / qualidade.pdf      ← Relatório de qualidade
    └── gerar_pdfs.py                          ← Gerador de PDFs a partir dos .md
```

---

## 9. Governança e LGPD

### Dados Pessoais Identificados (RF32)

| Campo | Tabela | Classificação | Técnica de Proteção (RF33) |
|-------|--------|---------------|---------------------------|
| `usuario_id` | interacoes, recomendacoes | Identificador Direto | **Pseudonimização** HMAC-SHA256 |
| `autor` | silver.catalogo | Identificador Indireto | **Mascaramento** dinâmico |
| `comentario` | silver.comentarios | Dado Pessoal (conteúdo) | **Hashing** SHA-256 + salt |

### Minimização na Camada Gold (RF32)

A tabela `gold.engajamento_conteudo` **não contém** `usuario_id`, `autor` nem `comentario`. O dashboard consome exclusivamente a Gold.

### Salts e Chaves (RF33)

- `LGPD_PEPPER_KEY` — variável de ambiente, nunca no repositório
- `LGPD_SALT_SECRET` — variável de ambiente, nunca no repositório
- Nenhum dado pessoal real foi utilizado no desafio (todos fictícios)

---

## 10. Roteiro para Apresentação

| Tempo | Bloco | O que demonstrar | Artefato |
|-------|-------|-----------------|----------|
| **2 min** | Situação-problema e arquitetura | Continuidade do Desafio 1, justificativa híbrida | `documentacao/arquitetura.pdf` |
| **4 min** | Apache Hop — Bronze, Silver, Gold e erros | Pipelines HPL, workflow HWF, quarentena simulada e reprocessamento | `hop/workflows/workflow_master_pipeline.hwf`, `hop/evidencias/` |
| **2 min** | Parquet e Apache Beam | Benchmark CSV x Parquet, execução DirectRunner | `beam/evidencias/rf24_parquet.md`, `beam/evidencias/rf25_beam.md` |
| **3 min** | OpenMetadata e qualidade | Catálogo, 4 termos, linhagem, dados mestres, 5 testes Quality Gate | `openmetadata/evidencias/`, `qualidade/regras.md` |
| **2 min** | LGPD | Inventário ROPA, demonstração das 3 técnicas, Gold sem dados pessoais | `lgpd/`, `python lgpd/demonstrar_protecao_lgpd.py` |
| **2 min** | Superset e storytelling | Dashboard ao vivo, filtros cruzados, alerta, narrativa executiva, uso de IA | `http://localhost:8088`, `documentacao/storytelling.pdf` |

---

## Decisões de Arquitetura e Limitações

### Decisões

- **PostgreSQL único com múltiplos schemas** — elimina overhead de múltiplos bancos, facilita JOINs entre camadas e simplifica a orquestração.
- **Parquet particionado por `ano_mes`** — permite pushdown de predicados temporais no Beam e no Superset, reduzindo leitura de dados irrelevantes.
- **Apache Beam com DirectRunner** como padrão de demonstração — evita dependência de cluster Spark em ambiente local; SparkRunner documentado como alternativa.
- **Quality Gate no scripts Python** em vez de triggers SQL — permite logging correlacionado por `execucao_id` e integração com OpenMetadata.

### Limitações

- A instância OpenMetadata não é incluída no `docker-compose.yml` por exigir +4 GB de RAM (Elasticsearch, MySQL). Os metadados são registrados via API quando disponível e como JSON local quando não.
- O SparkRunner requer instalação local do Apache Spark. A configuração de cluster é documentada mas não homologada neste ambiente.
- Os pipelines `.hpl` e `.hwf` do Apache Hop são executáveis via interface gráfica do Hop ou via linha de comando (`hop-run.sh`). A execução visual requer download separado do Apache Hop 2.10.0.
