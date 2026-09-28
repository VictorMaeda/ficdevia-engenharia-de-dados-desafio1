# RF27 — Implantação, Integração e Governança no OpenMetadata

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Implantação do OpenMetadata

O **OpenMetadata** foi selecionado como a plataforma unificada de governança de dados da instituição, sendo responsável por:
1. **Catalogação Técnica:** Descoberta e ingestão contínua de schemas, tabelas, views e tipos de dados do PostgreSQL (`pg_desafio2`);
2. **Glossário de Negócio:** Formalização de termos conceituais, métricas e seus respectivos responsáveis (stewards);
3. **Classificação e Tags:** Marcação de dados de acordo com sua criticidade (Tiers) e sensibilidade (LGPD / PII);
4. **Linhagem de Dados (Data Lineage):** Rastreabilidade de ponta a ponta desde as fontes em lote até os dashboards de tomada de decisão.

### Topologia de Implantação:
* **Serviço OpenMetadata Server:** Porta `8585` (API REST e Interface Web).
* **Repositório de Metadados:** PostgreSQL interno para persistência de entidades do catálogo.
* **Mecanismo de Busca e Indexação:** OpenSearch / ElasticSearch para busca em linguagem natural de ativos.
* **Ingestion Framework:** Python `openmetadata-ingestion` com conector nativo `postgresql+psycopg2`.

---

## 2. Conexão com o PostgreSQL e Ingestão Técnica

A integração foi parametrizada através da receita de ingestão [`ingestao_postgres.yaml`](file:///c:/Users/01923483102/Documents/pessoal/fic_dev_ia/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/openmetadata/ingestao_postgres.yaml):
* **Serviço Registrado:** `pg_desafio2_service`
* **Banco de Dados Ingerido:** `desafio2`
* **Schemas Conectados:**
  * `silver`: Dados limpos, tipados e validados pelo Apache Hop (`silver.catalogo`, `silver.comentarios`, `silver.interacoes`, `silver.recomendacoes`).
  * `gold`: Tabelas analíticas agregadas via Apache Beam (`gold.engajamento_conteudo`, `gold.engajamento_conteudo_mensal`) e views executivas (`gold.vw_resumo_categoria`, `gold.vw_ranking_engajamento`, `gold.vw_conteudos_atencao`).
  * `qualidade`: Tabelas de auditoria de testes e evolução de métricas (`qualidade.resultados`).

---

## 3. Atribuição de Proprietários (Data Owners) e Descrições

Para assegurar a responsabilização direta pelos ativos de informação, foram designados proprietários formais:

| Ativo de Dados | Schema | Tipo | Data Owner (Proprietário) | Finalidade do Ativo |
| :--- | :---: | :---: | :--- | :--- |
| `catalogo` | `silver` | Tabela | **Coordenação Pedagógica** (`pedagogico@ficdevia.edu.br`) | Tabela com metadados cadastrais dos cursos e autores. |
| `interacoes` | `silver` | Tabela | **Engenharia de Plataforma** (`eng.plataforma@ficdevia.edu.br`) | Registro de eventos brutos de clique, tempo e conclusão. |
| `engajamento_conteudo` | `gold` | Tabela | **Time de Analytics & IA** (`analytics@ficdevia.edu.br`) | Tabela consolidada de métricas agregadas por conteúdo. |
| `engajamento_conteudo_mensal` | `gold` | Tabela | **Time de Analytics & IA** (`analytics@ficdevia.edu.br`) | Série temporal para estudos de sazonalidade e retenção. |
| `vw_conteudos_atencao` | `gold` | View | **Gestão Acadêmica** (`gestao.academica@ficdevia.edu.br`) | View de alerta com cursos em risco pedagógico. |

---

## 4. Controles para Evitar que o Ambiente se Transforme em um *Data Swamp*

Um **Data Swamp** (pântano de dados) ocorre quando um Data Lake ou banco de dados acumula dados desestruturados, sem catalogação, sem validação de qualidade, sem donos conhecidos e sem contexto de negócio, tornando as informações inacessíveis ou perigosas para a tomada de decisão.

Na arquitetura do Desafio 2, foram implementados **5 controles estruturais rigorosos** para blindar o ambiente:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      CONTROLES INSTITUCIONAIS ANTI-DATA SWAMP                          │
├──────────────────────────┬─────────────────────────────────────────────────────────────┤
│ 1. Isolamento em         │ Dados brutos permanecem na camada Bronze sem acesso para    │
│    Camadas Estritas      │ usuários analíticos. O Superset conecta APENAS na Gold.     │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 2. Quarentena Automática │ Registros com inconsistências (nulos críticos, tipos        │
│    Impeditiva            │ inválidos) são desviados para quarentena no Hop, impedindo  │
│    (RF21 / RF23)         │ que dados corrompidos poluam as camadas de consumo.         │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 3. Gate de Qualidade com │ Antes da consolidação na Gold, 5 testes automatizados       │
│    Bloqueio (RF31)       │ validam completude, unicidade e integridade referencial.    │
│                          │ Falhas críticas abortam a publicação analítica.             │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 4. Política de Dono e    │ Nenhum ativo é promovido para a camada Silver ou Gold sem   │
│    Metadados Obrigatórios│ atribuição explícita de Proprietário, Descrição de Negócio  │
│    (RF27)                │ e Vinculação ao Glossário no OpenMetadata.                  │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 5. Minimização de Dados  │ Dados pessoais diretos (nomes, e-mails, IPs) são purgados  │
│    e LGPD (RF32 / RF33)  │ ou pseudonimizados na Silver, impedindo vazamentos na Gold. │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```
