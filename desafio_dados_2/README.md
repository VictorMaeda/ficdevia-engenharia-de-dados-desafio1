# Desafio Prático 2 — Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais

**Curso:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Turno:** Vespertino  
**Versão:** 1.0 — 2026  

---

## 1. Visão Geral e Arquitetura Simplificada

Este projeto evolui a solução funcional construída no **Desafio Prático 1**, estabelecendo um pipeline automatizado, governado e escalável com dados organizados nas camadas **Bronze**, **Silver** e **Gold**, orquestração visual no **Apache Hop**, processamento distribuído com **Apache Beam**, catálogo e governança no **OpenMetadata**, controles de qualidade de dados e conformidade estrita com a **LGPD**.

### Simplificação Arquitetural Unificada (Zero Redundância)
Para eliminar complexidade desnecessária e conflitos de portas, toda a infraestrutura foi consolidada em um único ambiente Docker:
* **PostgreSQL Unificado (porta `5432`):** Um único servidor de banco de dados (`desafio_dados_postgres`), segregando os dados por *schemas*:
  * `public`: Dados e tabelas originais do Desafio 1 (`conteudos`, `interacoes`, `recomendacoes`, `embeddings`);
  * `bronze`: Cópia auditada dos dados ingeridos via Apache Hop;
  * `silver`: Dados tratados, deduplicados e tipados;
  * `quarentena`: Registros inconsistentes desviados para análise sem travar o pipeline;
  * `gold`: Tabelas analíticas (`engajamento_conteudo`) e visões agregadas para consumo;
  * `qualidade`: Registro histórico dos 5 testes automatizados de qualidade.
* **Apache Superset (porta `8088`):** Conectado diretamente ao PostgreSQL na mesma rede interna, consumindo as visões da Camada Gold via SQL Lab e dashboards interativos.
* **MongoDB (porta `27017`):** Persistência de comentários e dados semiestruturados de continuidade.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARQUITETURA UNIFICADA E SIMPLIFICADA                            │
│                                                                                        │
│   Fontes (CSV/JSON/DB)                                                                 │
│           │                                                                            │
│           ▼                                                                            │
│   [ Apache Hop ] ──────► bronze.* (auditoria)                                          │
│           │                                                                            │
│           ├────────────► quarentena.* (erros/falhas)                                   │
│           ▼                                                                            │
│       silver.*                                                                         │
│           │                                                                            │
│           ▼                                                                            │
│   [ Apache Beam ] ─────► Parquet Particionado (ano_mes)                                │
│           │                                                                            │
│           ▼                                                                            │
│        gold.*  ◄─────── Gate de Qualidade (5 Testes - RF31)                            │
│           │                                                                            │
│           ├───► [ SQL Lab & Datasets Virtuais ]                                        │
│           │                                                                            │
│           └───► [ Apache Superset Dashboard ] (Filtros Cruzados & Alertas)             │
│                                                                                        │
│   Governança Transversal: OpenMetadata (Catálogo, 4 Termos, Linhagem e LGPD)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Registro de Versões das Ferramentas (RF15)

| Componente | Ferramenta / Imagem | Versão Homologada |
| :--- | :--- | :--- |
| **Banco Relacional / Vetorial** | PostgreSQL + pgvector | `16.0` (`pgvector/pgvector:pg16`) |
| **Banco NoSQL Semiestruturado** | MongoDB | `7.0` |
| **Orquestração e ETL** | Apache Hop | `2.10.0` / Java 17 |
| **Processamento Distribuído** | Apache Beam | `2.58.0` / PyArrow |
| **BI e Consumo Executivo** | Apache Superset | `4.1.0` / Python 3.10 |
| **Plataforma de Governança** | OpenMetadata | `1.3.1` (Especificação & Ingestão) |

---

## 3. Guia Rápido de Execução

### Passo 1: Subir os Serviços (Apenas 1 comando na raiz)
```bash
docker compose up -d
```
Todos os serviços (`postgres`, `mongo`, `superset`, `superset_meta_db`) sobem de forma integrada.

### Passo 2: Inicializar os Schemas do Desafio 2 (Idempotente)
No PowerShell, execute a partir da raiz:
```powershell
Get-Content desafio_dados_2\sql\criar_banco.sql -Raw | docker exec -i desafio_dados_postgres psql -U desafio_user -d desafio_dados
```

### Passo 3: Executar a Exportação Parquet e Benchmark (RF24)
```bash
python desafio_dados_2/beam/exportar_parquet.py
```

### Passo 4: Executar o Pipeline Distribuído com Apache Beam (RF25)
```bash
python desafio_dados_2/beam/pipeline_beam.py --input "desafio_dados_2/dados/silver/interacoes_parquet/*.parquet" --output "desafio_dados_2/beam/saida/direct/engajamento"
```

### Passo 5: Carregar a Camada Gold (RF26)
```bash
python desafio_dados_2/beam/carregar_gold.py
```

### Passo 6: Executar os Testes Automatizados de Qualidade (RF31)
```bash
python desafio_dados_2/qualidade/executar_testes.py
```

### Passo 7: Registrar Metadados e Glossário no OpenMetadata (RF28)
```bash
python desafio_dados_2/openmetadata/cadastrar_glossario_metadados.py
```

### Passo 8: Acessar o Apache Superset (RF16, RF17, RF18)
1. Acesse no navegador: `http://localhost:8088`
2. Credenciais: `admin` / `troque_esta_senha`
3. O banco `PostgreSQL - Desafio Dados` já está configurado no SQL Lab;
4. Execute as consultas de [`desafio_dados_2/sql/sql_lab.sql`](sql/sql_lab.sql) e salve como datasets virtuais.

---

## 4. Mapeamento de Requisitos e Entregáveis

| Requisito | Descrição | Onde Encontrar no Repositório | Status |
| :--- | :--- | :--- | :---: |
| **RF15** | Continuidade, Configurações e Versões | [`.env`](.env), [`project-config.json`](project-config.json), [README.md](README.md) | ✅ Concluído |
| **RF16** | Storytelling Executivo com Dados | [`documentacao/storytelling.md`](documentacao/storytelling.md), [`documentacao/storytelling.pdf`](documentacao/storytelling.pdf) | ✅ Concluído |
| **RF17** | SQL Lab e Datasets Virtuais | [`sql/sql_lab.sql`](sql/sql_lab.sql), [`sql/camada_gold.sql`](sql/camada_gold.sql) | ✅ Concluído |
| **RF18** | Filtros Cruzados e Alertas no Superset | [`superset/exportacao_e_evidencias/rf18_filtros_e_alertas.md`](superset/exportacao_e_evidencias/rf18_filtros_e_alertas.md), [`superset/exportacao_e_evidencias/dashboard_desafio2_engajamento.zip`](superset/exportacao_e_evidencias/dashboard_desafio2_engajamento.zip) | ✅ Concluído |
| **RF19** | Definição da Arquitetura ETL / ELT / Híbrida | [`documentacao/arquitetura.md`](documentacao/arquitetura.md), [`documentacao/arquitetura.pdf`](documentacao/arquitetura.pdf) | ✅ Concluído |
| **RF20** | Pipeline Bronze no Apache Hop | [`hop/pipelines/bronze_*.hpl`](hop/pipelines/), [`dados/bronze/`](dados/bronze/) | ✅ Concluído |
| **RF21** | Pipeline Silver e Padronização | [`hop/pipelines/silver_*.hpl`](hop/pipelines/), [`dados/silver/`](dados/silver/) | ✅ Concluído |
| **RF22** | Workflow e Orquestração Automatizada | [`hop/workflows/workflow_master_pipeline.hwf`](hop/workflows/workflow_master_pipeline.hwf), [`hop/workflows/orquestracao_bronze_silver.hwf`](hop/workflows/orquestracao_bronze_silver.hwf) | ✅ Concluído |
| **RF23** | Tratamento de Erros, Quarentena e Recuperação | [`hop/evidencias/rf23_quarentena_e_erros.md`](hop/evidencias/rf23_quarentena_e_erros.md), [`dados/quarentena/`](dados/quarentena/) | ✅ Concluído |
| **RF24** | Formato Parquet e Particionamento (ano_mes) | [`beam/exportar_parquet.py`](beam/exportar_parquet.py), [`beam/evidencias/rf24_parquet.md`](beam/evidencias/rf24_parquet.md), [`dados/silver/interacoes_parquet/`](dados/silver/interacoes_parquet/) | ✅ Concluído |
| **RF25** | Processamento Distribuído com Apache Beam | [`beam/pipeline.py`](beam/pipeline.py), [`beam/pipeline_beam.py`](beam/pipeline_beam.py), [`beam/evidencias/rf25_beam.md`](beam/evidencias/rf25_beam.md) | ✅ Concluído |
| **RF26** | Camada Gold para Consumo Analítico | [`sql/camada_gold.sql`](sql/camada_gold.sql), [`dados/gold/`](dados/gold/), [`documentacao/rf26_gold.md`](documentacao/rf26_gold.md) | ✅ Concluído |
| **RF27** | Implantação e Integração OpenMetadata | [`openmetadata/evidencias/rf27_implantacao_e_governanca.md`](openmetadata/evidencias/rf27_implantacao_e_governanca.md), [`openmetadata/ingestao_postgres.yaml`](openmetadata/ingestao_postgres.yaml) | ✅ Concluído |
| **RF28** | Catálogo, Classificação e Glossário (4 Termos) | [`openmetadata/evidencias/rf28_glossario_e_classificacoes.md`](openmetadata/evidencias/rf28_glossario_e_classificacoes.md), [`openmetadata/evidencias/glossario_e_termos.json`](openmetadata/evidencias/glossario_e_termos.json) | ✅ Concluído |
| **RF29** | Linhagem de Dados Ponta a Ponta | [`documentacao/linhagem.md`](documentacao/linhagem.md), [`documentacao/linhagem.pdf`](documentacao/linhagem.pdf), [`openmetadata/evidencias/rf29_linhagem.md`](openmetadata/evidencias/rf29_linhagem.md) | ✅ Concluído |
| **RF30** | Dados Mestres (Master Data Management - MDM) | [`documentacao/dados_mestres.md`](documentacao/dados_mestres.md), [`documentacao/dados_mestres.pdf`](documentacao/dados_mestres.pdf) | ✅ Concluído |
| **RF31** | Qualidade de Dados (5 Testes & Histórico) | [`qualidade/regras.md`](qualidade/regras.md), [`qualidade/executar_testes.py`](qualidade/executar_testes.py), [`qualidade/resultados/`](qualidade/resultados/) | ✅ Concluído |
| **RF32** | Inventário de Dados Pessoais e ROPA (LGPD) | [`lgpd/inventario_de_dados.md`](lgpd/inventario_de_dados.md) | ✅ Concluído |
| **RF33** | Mascaramento, Pseudonimização e Hashing | [`lgpd/tecnicas_de_protecao.md`](lgpd/tecnicas_de_protecao.md), [`lgpd/demonstrar_protecao_lgpd.py`](lgpd/demonstrar_protecao_lgpd.py) | ✅ Concluído |
| **RF34** | Evidências e Critérios de Aceite Consolidados | Todos os artefatos organizados conforme a Seção 11 do edital | ✅ Concluído |

---

## 5. Estrutura Completa dos Entregáveis (Seção 11 do Edital)

A organização das pastas no repositório segue estritamente a árvore solicitada no edital:

```text
desafio_dados_2/
├── README.md                                 # Guia mestre, arquitetura, versões e instruções
├── requirements.txt                          # Dependências de execução (Apache Beam, Pandas, PyArrow, etc.)
├── project-config.json                       # Configurações do projeto e metadados
├── docker-compose.yml                        # Infraestrutura unificada (Postgres, Mongo, Superset)
├── dados/
│   ├── bronze/                               # Amostras auditadas da ingestão bruta (CSV/JSON)
│   ├── silver/                               # Dados padronizados, validados e Parquet particionado
│   ├── gold/                                 # Tabelas e visões analíticas exportadas
│   └── quarentena/                           # Registros inconsistentes desviados com causa e timestamp
├── hop/
│   ├── environments/                         # Configurações e variáveis de ambiente Hop
│   ├── pipelines/                            # Pipelines HPL de ingestão Bronze e conformidade Silver
│   ├── workflows/                            # Workflows HWF orquestradores (workflow_master_pipeline.hwf)
│   └── evidencias/                           # Evidências de testes de falha, quarentena e reprocessamento
├── beam/
│   ├── pipeline.py                           # Pipeline distribuído Apache Beam (PyArrow/Parquet)
│   ├── pipeline_beam.py                      # Pipeline Beam com DirectRunner e Spark
│   ├── exportar_parquet.py                   # Script de conversão Silver -> Parquet e benchmark
│   └── evidencias/                           # Evidências RF24 (Parquet vs CSV) e RF25 (Direct vs Spark)
├── sql/
│   ├── criar_banco.sql                       # DDL dos schemas e tabelas unificadas
│   ├── camada_gold.sql                       # Modelagem dimensional e visões da Camada Gold
│   └── sql_lab.sql                           # Consultas analíticas e datasets virtuais do SQL Lab
├── superset/
│   └── exportacao_e_evidencias/
│       ├── dashboard_desafio2_engajamento.zip # Pacote ZIP nativo exportado do Apache Superset
│       ├── rf18_filtros_e_alertas.md          # Evidências detalhadas dos filtros e alertas
│       └── dashboard_export_config.json      # Metadados e JSON dos slices
├── openmetadata/
│   ├── ingestao_postgres.yaml                # Especificação de ingestão do conector PostgreSQL
│   ├── cadastrar_glossario_metadados.py       # Script de cadastro do glossário de negócio
│   └── evidencias/
│       ├── rf27_implantacao_e_governanca.md  # Implantação e políticas contra Data Swamp
│       ├── rf28_glossario_e_classificacoes.md# 4 Termos de negócio, regras e sensibilidade
│       ├── rf29_linhagem.md                  # Linhagem ponta a ponta e rastreabilidade
│       └── glossario_e_termos.json           # Definição canônica dos termos
├── qualidade/
│   ├── regras.md                             # Especificação formal dos 5 testes (Q01 a Q05)
│   ├── executar_testes.py                    # Script de validação automática e gate da Gold
│   └── resultados/                           # Logs JSON históricos de execuções de qualidade
├── lgpd/
│   ├── inventario_de_dados.md                # ROPA, bases legais, retenção e finalidade
│   ├── tecnicas_de_protecao.md               # Mascaramento, HMAC-SHA256 e Salt Hashing
│   └── demonstrar_protecao_lgpd.py           # Script comprovatório de proteção no consumo
└── documentacao/
    ├── arquitetura.md & arquitetura.pdf       # Definição e justificativa ETL/ELT/Híbrida
    ├── linhagem.md & linhagem.pdf             # Diagrama de linhagem e auditoria
    ├── storytelling.md & storytelling.pdf     # Narrativa executiva orientada a decisão
    ├── dados_mestres.md & dados_mestres.pdf   # Entidade mestre, deduplicação e sobrevivência
    └── rf31_qualidade.md & qualidade.pdf      # Relatório executivo da qualidade de dados
```

---

## 6. Roteiro Sugerido para Apresentação (15 Minutos - Seção 12)

Para a banca avaliadora, a equipe deverá conduzir a demonstração de 15 minutos dividida conforme o edital:

| Tempo | Bloco Temático | Conteúdo a Demonstrar | Artefatos de Suporte |
| :---: | :--- | :--- | :--- |
| **2 min** | **Problema & Arquitetura** | Situação-problema da plataforma, continuidade do Desafio 1 e justificativa da Arquitetura Híbrida (Medallion: Bronze/Silver/Gold). | [`documentacao/arquitetura.pdf`](documentacao/arquitetura.pdf) |
| **4 min** | **Apache Hop & Orquestração** | Pipelines de ingestão bruta (Bronze), padronização e regras de negócio (Silver), desvio automático para Quarentena sem travar o fluxo e reprocessamento. | [`hop/workflows/workflow_master_pipeline.hwf`](hop/workflows/workflow_master_pipeline.hwf), [`hop/evidencias/rf23_quarentena_e_erros.md`](hop/evidencias/rf23_quarentena_e_erros.md) |
| **2 min** | **Parquet & Apache Beam** | Vantagens do formato colunar Parquet particionado por `ano_mes` (compressão e ganho de leitura); execução do pipeline Beam em DirectRunner e Spark. | [`beam/evidencias/rf24_parquet.md`](beam/evidencias/rf24_parquet.md), [`beam/evidencias/rf25_beam.md`](beam/evidencias/rf25_beam.md) |
| **3 min** | **Governança & Qualidade** | Catálogo no OpenMetadata, os 4 termos de negócio, linhagem do dado, dados mestres (MDM) e os 5 testes de qualidade como Quality Gate da Camada Gold. | [`openmetadata/evidencias/`](openmetadata/evidencias/), [`qualidade/regras.md`](qualidade/regras.md), [`documentacao/dados_mestres.pdf`](documentacao/dados_mestres.pdf) |
| **2 min** | **Privacidade & LGPD** | Inventário ROPA, minimização de dados, mascaramento dinâmico no consumo, pseudonimização com HMAC e hashing irreversível de identificadores. | [`lgpd/inventario_de_dados.md`](lgpd/inventario_de_dados.md), [`lgpd/demonstrar_protecao_lgpd.py`](lgpd/demonstrar_protecao_lgpd.py) |
| **2 min** | **Consumo & Storytelling** | Demonstração do Dashboard no Apache Superset: storytelling executivo, filtros cruzados interativos, alerta acionado em tempo real e apoio da IA no desenvolvimento. | [`http://localhost:8088`](http://localhost:8088), [`documentacao/storytelling.pdf`](documentacao/storytelling.pdf) |

