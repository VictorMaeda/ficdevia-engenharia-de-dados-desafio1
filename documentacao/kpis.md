# Métricas e KPIs do Dashboard

Este documento descreve as métricas e os indicadores-chave de desempenho (KPIs) utilizados no dashboard do projeto **Pipeline de Recomendação e Dashboard de Conteúdos Educacionais**.

Os indicadores foram definidos a partir dos dados armazenados no PostgreSQL após o processo de ingestão, validação, tratamento e persistência.

> Os valores apresentados neste documento são valores de referência obtidos com a base atual do projeto e podem mudar caso novos dados sejam carregados posteriormente.

---

## 1. Métricas Operacionais

### 1.1 Total de Usuários

**Tipo:** Métrica operacional

**Objetivo:**  
Identificar o tamanho da base de usuários presente no sistema.

**Fórmula:**

```text
Total de Usuários = quantidade de registros na tabela usuarios
```

**Fonte de dados:**

- Tabela: `usuarios`
- Campo principal: `usuario_id`

**Periodicidade:**  
Atualizada a cada nova execução do pipeline de dados.

**Interpretação:**  
Representa a quantidade total de usuários identificados nas fontes de dados e persistidos no PostgreSQL.

**Valor de referência atual:**

```text
150 usuários
```

---

### 1.2 Total de Interações

**Tipo:** Métrica operacional

**Objetivo:**  
Mensurar o volume total de atividades realizadas pelos usuários sobre os conteúdos educacionais.

**Fórmula:**

```text
Total de Interações = quantidade de registros na tabela interacoes
```

**Fonte de dados:**

- Tabela: `interacoes`
- Campo principal: `interacao_id`

**Periodicidade:**  
Atualizada a cada nova execução do pipeline de dados.

**Interpretação:**  
Quanto maior o número de interações, maior é o volume de atividade registrado na plataforma.

As interações podem incluir eventos como:

- visualização;
- início;
- conclusão;
- curtida;
- compartilhamento;
- avaliação.

**Valor de referência atual:**

```text
1.000 interações
```

---

## 2. KPIs

### 2.1 Taxa de Conclusão

**Tipo:** KPI de engajamento

**Objetivo:**  
Medir a proporção de relações entre usuário e conteúdo que chegaram à conclusão completa.

**Fórmula:**

```text
Taxa de Conclusão (%) =

Pares distintos usuário/conteúdo concluídos
------------------------------------------------ x 100
Pares distintos usuário/conteúdo com interação
```

Um par usuário/conteúdo é considerado concluído quando o conteúdo atingiu `percentual_conclusao = 100`.

A utilização de pares distintos evita que múltiplas interações realizadas pelo mesmo usuário com o mesmo conteúdo provoquem duplicidade no cálculo.

**Fonte de dados:**

- Tabela: `interacoes`
- Campos:
  - `usuario_id`
  - `conteudo_id`
  - `percentual_conclusao`

**Periodicidade:**  
Atualizada a cada nova execução do pipeline de dados.

**Interpretação:**

- valores maiores indicam maior capacidade dos conteúdos de serem consumidos até o final;
- valores menores podem indicar abandono, conteúdos muito extensos ou menor aderência aos interesses dos usuários.

**Valor de referência atual:**

```text
Pares usuário/conteúdo com interação: 998
Pares concluídos:                     154

Taxa de Conclusão ≈ 15,43%
```

---

### 2.2 Avaliação Média dos Conteúdos

**Tipo:** KPI de qualidade percebida

**Objetivo:**  
Mensurar a percepção média dos usuários sobre a qualidade dos conteúdos avaliados.

**Fórmula:**

```text
Avaliação Média =

Soma das notas
---------------------
Total de avaliações
```

**Fonte de dados:**

- Tabela: `avaliacoes_resumo`
- Campo: `nota`

**Periodicidade:**  
Atualizada a cada nova execução do pipeline de dados.

**Interpretação:**

As notas variam de 1 a 5.

Quanto mais próximo de 5 estiver o indicador, maior é a avaliação média dos conteúdos pelos usuários.

**Valor de referência atual:**

```text
Avaliação média = 4,15 / 5
```

---

### 2.3 Taxa de Avaliações Positivas

**Tipo:** KPI complementar de satisfação

**Objetivo:**  
Identificar qual percentual das avaliações realizadas pelos usuários pode ser considerado positivo.

Neste projeto, são consideradas positivas as avaliações com nota maior ou igual a 4.

**Fórmula:**

```text
Taxa de Avaliações Positivas (%) =

Avaliações com nota >= 4
-------------------------- x 100
Total de avaliações
```

**Fonte de dados:**

- Tabela: `avaliacoes_resumo`
- Campo: `nota`

**Periodicidade:**  
Atualizada a cada nova execução do pipeline de dados.

**Interpretação:**

Uma taxa elevada indica que a maior parte das avaliações demonstra satisfação com os conteúdos disponibilizados.

**Valor de referência atual:**

```text
Notas 4: 327
Notas 5: 464

Avaliações positivas: 791
Total de avaliações:  1.000

Taxa de Avaliações Positivas = 79,10%
```

---

## 3. Métricas Auxiliares

Além das métricas e KPIs principais, o dashboard poderá utilizar métricas auxiliares para fornecer maior contexto às análises.

### 3.1 Total de Conteúdos

Quantidade total de conteúdos cadastrados.

**Fonte de dados:**

- Tabela: `conteudos`
- Campo principal: `conteudo_id`

**Valor de referência atual:**

```text
1.000 conteúdos
```

---

### 3.2 Conteúdos com Interação

Quantidade de conteúdos distintos que possuem pelo menos uma interação registrada.

**Fonte de dados:**

- Tabela: `interacoes`
- Campo: `conteudo_id`

**Valor de referência atual:**

```text
625 conteúdos
```

---

### 3.3 Total de Avaliações

Quantidade de avaliações disponíveis na tabela `avaliacoes_resumo`.

**Fonte de dados:**

- Tabela: `avaliacoes_resumo`
- Campo principal: `avaliacao_resumo_id`

**Valor de referência atual:**

```text
1.000 avaliações
```

---

### 3.4 Total de Recomendações

Quantidade de recomendações geradas e persistidas pelo motor de recomendação.

**Fonte de dados:**

- Tabela: `recomendacoes`
- Campo principal: `recomendacao_id`

Este indicador será disponibilizado após a implementação e execução da etapa de geração de recomendações.

---

## 4. Dimensões de Análise

As métricas e KPIs poderão ser analisados por diferentes dimensões no Apache Superset.

As principais dimensões previstas são:

- categoria do conteúdo;
- tipo do conteúdo;
- nível do conteúdo;
- período da interação.

Essas dimensões permitirão comparar o comportamento dos usuários entre diferentes grupos de conteúdos.

---

## 5. Perguntas de Negócio

O dashboard será desenvolvido para auxiliar na resposta das seguintes perguntas.

### 5.1 Quais categorias e tipos de conteúdo apresentam maior engajamento e melhor taxa de conclusão?

Essa análise permite identificar quais grupos de conteúdo apresentam maior atividade dos usuários e maior capacidade de serem consumidos até o final.

---

### 5.2 Como o volume de interações dos usuários evolui ao longo do tempo?

Essa análise permite identificar tendências de crescimento, queda ou variações no consumo da plataforma ao longo do período analisado.

---

### 5.3 Quais categorias apresentam melhor percepção de qualidade segundo as avaliações dos usuários?

Essa análise permite comparar a satisfação dos usuários entre diferentes categorias de conteúdo.

---

## 6. Período Atual da Base

Na execução utilizada como referência para elaboração deste documento, as interações disponíveis estão compreendidas entre:

```text
Primeira interação: 01/01/2026
Última interação:   25/08/2026
```

Foram identificados:

```text
150 usuários
1.000 conteúdos
625 conteúdos com pelo menos uma interação
1.000 interações
998 pares distintos usuário/conteúdo
1.000 avaliações
```

Esses números representam o estado atual da base e devem ser recalculados caso o conjunto de dados seja atualizado.

---

## 7. Resumo dos Indicadores

| Indicador | Tipo | Valor de referência |
|---|---|---:|
| Total de Usuários | Métrica operacional | 150 |
| Total de Interações | Métrica operacional | 1.000 |
| Taxa de Conclusão | KPI | 15,43% |
| Avaliação Média | KPI | 4,15 / 5 |
| Taxa de Avaliações Positivas | KPI complementar | 79,10% |
| Total de Conteúdos | Métrica auxiliar | 1.000 |
| Conteúdos com Interação | Métrica auxiliar | 625 |
| Total de Avaliações | Métrica auxiliar | 1.000 |