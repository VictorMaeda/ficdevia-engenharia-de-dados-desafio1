# RF27 — Implantação, Integração e Governança no OpenMetadata

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Implantação do OpenMetadata

O **OpenMetadata** foi selecionado como a plataforma unificada de governança de dados da instituição, sendo responsável por:

1. **Catalogação Técnica:** Descoberta e ingestão contínua de schemas, tabelas, views e tipos de dados do PostgreSQL (`desafio_dados`);
2. **Glossário de Negócio:** Formalização de 4 termos conceituais, métricas e seus respectivos responsáveis (stewards) — RF28;
3. **Classificação e Tags:** Marcação de dados de acordo com criticidade (Tiers) e sensibilidade LGPD (PII) — RF28;
4. **Linhagem de Dados (Data Lineage):** Rastreabilidade ponta a ponta desde fontes em lote até dashboards — RF29;
5. **Dados Mestres (MDM):** Custom Properties e Golden Record da entidade Conteúdo Educacional — RF30.

### Topologia de Implantação

| Componente | Imagem Docker | Porta | Finalidade |
|:---|:---|:---:|:---|
| OpenMetadata Server | `docker.getcollate.io/openmetadata/server:1.3.1` | 8585 | API REST + Interface Web |
| MySQL (repositório interno) | `mysql:8.0.35` | 3307 | Persistência de entidades do catálogo |
| OpenSearch (índice de busca) | `opensearchproject/opensearch:2.7.0` | 9200 | Busca em linguagem natural de ativos |

**Para subir:** `docker compose -f desafio_dados_2/openmetadata/docker-compose-openmetadata.yml up -d`  
**URL de acesso:** `http://localhost:8585` — credenciais `admin` / `admin`

---

## 2. Conexão com o PostgreSQL e Ingestão Técnica

A integração com o PostgreSQL foi configurada em dois níveis:

### 2.1. Receita de Ingestão YAML (`ingestao_postgres.yaml`)

```yaml
source:
  type: postgres
  serviceName: pg_desafio2_service
  sourceConfig:
    config:
      type: DatabaseMetadata
      schemaFilterPattern:
        includes: [silver, gold, qualidade]
        excludes: [information_schema, pg_catalog]
      includeViews: true
      markDeletedTables: true
```

### 2.2. Bootstrap via API REST (`configurar_openmetadata.py`)

O script `configurar_openmetadata.py` registra programaticamente via API:

| Etapa | Endpoint | Descrição |
|:---|:---|:---|
| 1 | `PUT /api/v1/services/databaseServices` | Registra o serviço `pg_desafio2_service` |
| 2 | `PUT /api/v1/services/ingestionPipelines` | Cria pipeline de ingestão diário (06:00) |
| 3 | `PUT /api/v1/services/dashboardServices` | Registra o serviço `superset_desafio2_service` |
| 4 | `PUT /api/v1/lineage` | Publica 3 arestas de linhagem (Bronze→Silver→Gold→Superset) |
| 5 | Local | Salva evidência JSON em `openmetadata/evidencias/` |

**Execução:**
```bash
python desafio_dados_2/openmetadata/configurar_openmetadata.py
```

### 2.3. Schemas e Ativos Catalogados

| Schema | Tipo de Ativos | Descrição |
|:---|:---|:---|
| `silver` | Tabelas | `catalogo`, `interacoes`, `comentarios`, `recomendacoes` — dados padronizados e validados |
| `gold` | Tabelas + Views | `engajamento_conteudo`, `engajamento_conteudo_mensal`, `vw_*` — ativos analíticos |
| `qualidade` | Tabela | `resultados` — auditoria dos testes de qualidade Q01-Q05 |

---

## 3. Atribuição de Proprietários (Data Owners) e Descrições

Para assegurar responsabilização direta pelos ativos de informação, foram designados proprietários formais:

| Ativo de Dados | Schema | Tipo | Data Owner | Finalidade |
|:---|:---:|:---:|:---|:---|
| `catalogo` | `silver` | Tabela | Coordenação Pedagógica | Metadados cadastrais dos cursos e autores |
| `interacoes` | `silver` | Tabela | Engenharia de Plataforma | Eventos brutos de clique, tempo e conclusão |
| `recomendacoes` | `silver` | Tabela | Time de IA | Histórico de sugestões geradas pelo algoritmo |
| `comentarios` | `silver` | Tabela | Gestão Acadêmica | Avaliações qualitativas dos estudantes |
| `engajamento_conteudo` | `gold` | Tabela | Analytics & IA | KPIs consolidados por conteúdo |
| `engajamento_conteudo_mensal` | `gold` | Tabela | Analytics & IA | Série temporal para sazonalidade e retenção |
| `vw_conteudos_atencao` | `gold` | View | Gestão Acadêmica | Alerta com cursos em risco pedagógico |

> **Política:** Nenhum ativo é promovido para Silver ou Gold sem atribuição explícita de proprietário, descrição de negócio e vinculação ao Glossário (para colunas PII).

---

## 4. Controles para Evitar que o Ambiente se Transforme em um *Data Swamp*

Um **Data Swamp** (pântano de dados) ocorre quando um Data Lake acumula dados desestruturados, sem catalogação, sem validação, sem donos conhecidos e sem contexto de negócio — tornando as informações inacessíveis ou perigosas para a tomada de decisão.

Foram implementados **5 controles estruturais rigorosos**:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      CONTROLES INSTITUCIONAIS ANTI-DATA SWAMP                          │
├──────────────────────────┬─────────────────────────────────────────────────────────────┤
│ 1. Isolamento em         │ Dados brutos permanecem na camada Bronze sem acesso para    │
│    Camadas Estritas      │ usuários analíticos. O Superset conecta APENAS na Gold.     │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 2. Quarentena Automática │ Registros com inconsistências (nulos críticos, tipos        │
│    Impeditiva (RF23)     │ inválidos) são desviados para quarentena no Hop, impedindo  │
│                          │ que dados corrompidos poluam as camadas de consumo.         │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 3. Gate de Qualidade com │ Antes da consolidação na Gold, 5 testes automatizados       │
│    Bloqueio (RF31)       │ validam completude, unicidade e integridade referencial.    │
│                          │ Falhas críticas (Q01, Q03, Q05) abortam a publicação.       │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 4. Política de Dono e    │ Nenhum ativo é promovido para Silver ou Gold sem:           │
│    Metadados Obrigatórios│ • Data Owner atribuído no OpenMetadata                     │
│    (RF27)                │ • Descrição de negócio preenchida                          │
│                          │ • Tag de classificação aplicada (Tier/PII)                 │
│                          │ • Termo do Glossário vinculado (para colunas PII)           │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 5. Minimização de Dados  │ Dados pessoais diretos (nomes, usuário_id originais) são   │
│    e LGPD (RF32/RF33)    │ mascarados/pseudonimizados na Silver antes de qualquer     │
│                          │ promoção. A camada Gold não contém nenhum dado pessoal.    │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 5. Pipeline de Ingestão Automático (Agendamento Diário)

O pipeline de ingestão criado via API (`desafio2_postgres_metadata_ingestion`) executa diariamente às **06:00**, garantindo que:

- Novas tabelas ou views adicionadas ao banco são automaticamente descobertas;
- Comentários DDL adicionados às colunas (`COMMENT ON COLUMN`) são propagados ao catálogo;
- Tabelas removidas recebem marcação `markDeletedTables = true` no catálogo;
- O histórico de ingestões fica visível no painel "Ingestion Pipelines" do OpenMetadata.

---

## 6. Governança de Dados Mestres no Catálogo (RF30 — Integração)

A entidade mestre **Conteúdo Educacional** é gerenciada no OpenMetadata via:

- **Custom Properties** da tabela `silver.catalogo`: `mdm_is_golden_record`, `mdm_golden_id`, `mdm_steward`, `mdm_survivorship_rule`;
- **Descrições de Coluna** com papel MDM explícito (Golden ID, Atributo Master, PII — Mascarado);
- **Tag** `Tier.Tier1_Critical` na tabela master.

**Script de execução:**
```bash
python desafio_dados_2/openmetadata/registrar_dados_mestres_openmetadata.py
```

**Evidência:** `openmetadata/evidencias/rf30_dados_mestres_openmetadata.json` e `rf30_dados_mestres_openmetadata.md`

---

## 7. Resumo dos Scripts e Evidências OpenMetadata

| Script / Arquivo | RF | Finalidade |
|:---|:---:|:---|
| `configurar_openmetadata.py` | RF27 | Bootstrap: serviço PG, Superset, pipeline ingestão e linhagem |
| `cadastrar_glossario_metadados.py` | RF28 | 4 Termos de negócio + 2 Classificações (PII, Tier) |
| `registrar_dados_mestres_openmetadata.py` | RF30 | MDM: Custom Properties e descrições de colunas |
| `ingestao_postgres.yaml` | RF27 | Receita YAML para ingestion CLI |
| `linhagem_pipeline.json` | RF29 | Linhagem manual JSON (importável pela UI) |
| `evidencias/rf27_configuracao_openmetadata.json` | RF27 | Evidência do bootstrap via API |
| `evidencias/rf28_glossario_e_classificacoes.md` | RF28 | Glossário, tags e matriz de vínculos |
| `evidencias/rf29_linhagem.md` | RF29 | Diagrama Mermaid + rastreabilidade bottom-up |
| `evidencias/rf30_dados_mestres_openmetadata.md` | RF30 | Entidade mestre, survivorship e custom properties |
