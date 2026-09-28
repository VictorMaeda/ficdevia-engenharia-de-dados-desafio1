# RF28 — Catálogo, Classificações e Glossário de Negócio no OpenMetadata

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Glossário de Negócio Corporativo

No OpenMetadata, o Glossário de Negócio unifica a linguagem conceitual entre a equipe de tecnologia, engenharia de dados, coordenação acadêmica e diretoria executiva, eliminando ambiguidades conceituais.

Foram definidos formalmente **4 termos de negócio essenciais**:

---

### Termo 1: Usuário Ativo (Active User)
* **Definição Conceitual:** Estudante regularmente matriculado que realizou ao menos uma interação mensurável (consumo de vídeo, áudio, leitura ou avaliação) em um determinado período de referência.
* **Regra de Cálculo / Fórmula:**
  $$\text{Usuários Ativos (Mês)} = \text{COUNT(DISTINCT } \text{usuario\_id}) \quad \text{onde } \text{data\_hora} \in [\text{início\_mês}, \text{fim\_mês}]$$
* **Responsável (Steward):** Coordenação de Gestão de Alunos (`gestao.alunos@ficdevia.edu.br`).
* **Ativos / Campos Associados:**
  * Tabela: `silver.interacoes` $\rightarrow$ Coluna: `usuario_id`
  * Tabela: `silver.comentarios` $\rightarrow$ Coluna: `usuario_id`

---

### Termo 2: Taxa de Conclusão (Completion Rate)
* **Definição Conceitual:** Percentual de sessões de consumo em que o estudante atingiu integralmente 100% da carga horária ou emitiu evento explícito de finalização em relação ao total de interações iniciadas.
* **Regra de Cálculo / Fórmula:**
  $$\text{Taxa de Conclusão (\%)} = \left( \frac{\sum \text{quantidade\_conclusoes}}{\sum \text{total\_interacoes}} \right) \times 100$$
* **Responsável (Steward):** Diretoria Pedagógica (`diretoria.pedagogica@ficdevia.edu.br`).
* **Ativos / Campos Associados:**
  * Tabela: `gold.engajamento_conteudo` $\rightarrow$ Coluna: `quantidade_conclusoes`, `total_interacoes`
  * View: `gold.vw_resumo_categoria` $\rightarrow$ Coluna: `taxa_conclusao_geral`
  * Dataset Virtual SQL Lab: `ds_virtual_desempenho_engajamento_conteudos` $\rightarrow$ Coluna: `taxa_conclusao_pct`

---

### Termo 3: Conversão de Recomendação (Recommendation Conversion Rate)
* **Definição Conceitual:** Proporção de conteúdos sugeridos pelo motor de recomendação inteligente que foram efetivamente clicados e consumidos pelo estudante no intervalo de até 7 dias após a geração da sugestão.
* **Regra de Cálculo / Fórmula:**
  $$\text{Taxa de Conversão (\%)} = \left( \frac{\text{COUNT(DISTINCT interações originadas de recomendação)}}{\text{COUNT(DISTINCT recomendações emitidas com status 'ativo')}} \right) \times 100$$
* **Responsável (Steward):** Time de Inteligência Artificial & Recomendação (`ia.recomendacao@ficdevia.edu.br`).
* **Ativos / Campos Associados:**
  * Tabela: `silver.recomendacoes` $\rightarrow$ Colunas: `status`, `pontuacao`, `posicao`
  * Tabela: `silver.interacoes` $\rightarrow$ Cruzamento por `(usuario_id, conteudo_id)`

---

### Termo 4: Tempo Médio de Engajamento por Conteúdo (Average Engagement Time)
* **Definição Conceitual:** Média aritmética da duração em minutos que os estudantes dedicam a cada sessão de estudo de um determinado título educacional.
* **Regra de Cálculo / Fórmula:**
  $$\text{Tempo Médio (min)} = \frac{\sum \text{tempo\_total\_segundos}}{\sum \text{total\_interacoes} \times 60}$$
* **Responsável (Steward):** Coordenação de Design Instrucional (`design.instrucional@ficdevia.edu.br`).
* **Ativos / Campos Associados:**
  * Tabela: `gold.engajamento_conteudo` $\rightarrow$ Colunas: `tempo_total_segundos`, `total_interacoes`
  * Dataset Virtual SQL Lab: `ds_virtual_desempenho_engajamento_conteudos` $\rightarrow$ Coluna: `tempo_medio_por_interacao_min`

---

## 2. Classificações Técnicas e de Sensibilidade (Tags)

No OpenMetadata, foram criadas taxonomias para assegurar conformidade com a LGPD e governança operacional de dados:

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TAXONOMIA E CLASSIFICAÇÃO DE CAMPOS                                       │
├─────────────────────┬───────────────────┬───────────────────────────────────────┬──────────────────────┤
│ Classificação / Tag │ Criticidade       │ Descrição da Política                 │ Campos Vinculados    │
├─────────────────────┼───────────────────┼───────────────────────────────────────┼──────────────────────┤
│ PII.Identifiable    │ Alta (LGPD)       │ Dados que identificam diretamente     │ `silver.catalogo`    │
│                     │                   │ ou indiretamente o indivíduo.         │ .`autor`             │
├─────────────────────┼───────────────────┼───────────────────────────────────────┼──────────────────────┤
│ PII.Pseudonymized   │ Moderada (LGPD)   │ Identificador submetido a tokenização │ `silver.interacoes`  │
│                     │                   │ reversível sob chave de segurança.    │ .`usuario_id`        │
├─────────────────────┼───────────────────┼───────────────────────────────────────┼──────────────────────┤
│ Tier.Tier1_Critical │ Estratégica       │ Ativos analíticos de missão crítica   │ `gold.engajamento_`  │
│                     │                   │ consumidos diretamente pela Diretoria │ `conteudo`           │
├─────────────────────┼───────────────────┼───────────────────────────────────────┼──────────────────────┤
│ Tier.Tier2_Standard │ Tática            │ Tabelas padronizadas de apoio que     │ `silver.catalogo`,   │
│                     │                   │ alimentam agregações intermediárias.  │ `silver.interacoes`  │
├─────────────────────┼───────────────────┼───────────────────────────────────────┼──────────────────────┤
│ DataQuality.Audited │ Operacional       │ Ativo validado pelo mecanismo         │ `silver.interacoes`, │
│                     │                   │ de testes de integridade e completude.│ `gold.engajamento_`  │
└─────────────────────┴───────────────────┴───────────────────────────────────────┴──────────────────────┘
```

---

## 3. Matriz de Vínculos: Termos, Tags e Esquemas

| Tabela / Visão | Coluna | Termo do Glossário Vinculado | Tags Aplicadas |
| :--- | :--- | :--- | :--- |
| `silver.catalogo` | `autor` | — | `PII.Identifiable`, `Tier.Tier2_Standard` |
| `silver.interacoes` | `usuario_id` | **Usuário Ativo** | `PII.Pseudonymized`, `DataQuality.Audited` |
| `silver.recomendacoes`| `status` | **Conversão de Recomendação** | `Tier.Tier2_Standard` |
| `gold.engajamento_conteudo` | `total_interacoes` | **Usuário Ativo** | `Tier.Tier1_Critical`, `DataQuality.Audited` |
| `gold.engajamento_conteudo` | `quantidade_conclusoes`| **Taxa de Conclusão** | `Tier.Tier1_Critical` |
| `gold.engajamento_conteudo` | `tempo_total_segundos` | **Tempo Médio de Engajamento**| `Tier.Tier1_Critical` |
| `gold.vw_resumo_categoria` | `taxa_conclusao_geral` | **Taxa de Conclusão** | `Tier.Tier1_Critical` |
