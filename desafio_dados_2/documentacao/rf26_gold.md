# RF26 — Camada Gold para Consumo Analítico

## Objetivo

A camada Gold foi construída para disponibilizar dados consolidados e orientados às perguntas de negócio, evitando que ferramentas analíticas consultem diretamente as camadas Bronze ou Silver.

O fluxo operacional utilizado é:

```text
Bronze
  ↓
Silver
  ↓
Testes de qualidade
  ↓
Parquet
  ↓
Apache Beam
  ↓
Parquet agregado
  ↓
Carga Gold
  ├── gold.engajamento_conteudo
  └── gold.engajamento_conteudo_mensal
  ↓
Views analíticas
  ↓
SQL Lab / Apache Superset
```

---

## Estruturas da camada Gold

A implementação possui duas tabelas analíticas principais:

```text
gold.engajamento_conteudo
gold.engajamento_conteudo_mensal
```

Também foram criadas as seguintes views:

```text
gold.vw_ranking_engajamento
gold.vw_resumo_categoria
gold.vw_conteudos_atencao
```

---

# 1. Gold consolidada por conteúdo

## Tabela

```text
gold.engajamento_conteudo
```

## Granularidade

Cada linha representa:

```text
1 conteúdo identificado por conteudo_id
```

Na execução validada foram produzidos:

```text
625 registros
```

correspondentes a 625 conteúdos distintos que possuem interações válidas.

## Chave

A chave primária é:

```text
conteudo_id
```

## Dimensões

As informações descritivas são provenientes de:

```text
silver.catalogo
```

Dimensões utilizadas:

```text
conteudo_id
titulo
tipo
categoria
nivel
```

## Medidas

### total_interacoes

Quantidade total de interações associadas ao conteúdo.

Regra conceitual:

```text
COUNT(interações)
```

### tempo_total_segundos

Soma do tempo consumido nas interações do conteúdo.

Regra:

```text
SUM(tempo_consumido)
```

### media_percentual_conclusao

Média do percentual de conclusão das interações do conteúdo.

Regra:

```text
SUM(percentual_conclusao)
/
quantidade de interações com percentual preenchido
```

O resultado é armazenado com duas casas decimais na camada Gold.

### quantidade_conclusoes

Quantidade de interações classificadas como:

```text
tipo_interacao = "conclusão"
```

## Auditoria

A tabela possui:

```text
data_carga
```

Esse campo registra automaticamente a data e hora da publicação do registro na camada Gold.

---

# 2. Gold mensal por conteúdo

## Tabela

```text
gold.engajamento_conteudo_mensal
```

Essa estrutura complementa a Gold consolidada permitindo análises temporais.

## Granularidade

Cada linha representa:

```text
1 conteúdo em 1 mês
```

A chave primária composta é:

```text
mes_referencia + conteudo_id
```

## Dimensões

```text
mes_referencia
conteudo_id
titulo
tipo
categoria
nivel
```

## Medidas

```text
total_interacoes
tempo_total_segundos
media_percentual_conclusao
quantidade_conclusoes
```

## Origem

A agregação mensal é produzida diretamente a partir de:

```text
silver.interacoes
+
silver.catalogo
```

O mês de referência é calculado a partir de:

```text
data_hora
```

utilizando o primeiro dia de cada mês como referência.

Exemplo:

```text
2026-01-01
2026-02-01
...
2026-08-01
```

## Resultado validado

A execução produziu:

```text
Registros mensais: 935
Meses distintos:   8
Interações:         1001
Conclusões:         154
```

Os 935 registros representam combinações distintas de:

```text
conteúdo + mês
```

Por isso esse valor é maior que os 625 conteúdos da Gold consolidada.

---

# 3. Distribuição temporal

A Gold mensal produziu os seguintes resultados:

| Mês | Conteúdos com interação | Interações | Conclusões | Média de conclusão (%) |
|---|---:|---:|---:|---:|
| 2026-01 | 120 | 123 | 22 | 57.01 |
| 2026-02 | 133 | 147 | 23 | 56.83 |
| 2026-03 | 114 | 124 | 20 | 51.86 |
| 2026-04 | 112 | 119 | 12 | 52.46 |
| 2026-05 | 129 | 139 | 21 | 51.34 |
| 2026-06 | 123 | 133 | 16 | 50.99 |
| 2026-07 | 112 | 119 | 18 | 57.80 |
| 2026-08 | 92 | 97 | 22 | 57.64 |

Essa estrutura permite construir no Superset análises como:

- evolução mensal do volume de interações;
- evolução das conclusões;
- comportamento da conclusão média ao longo do tempo;
- comparação entre categorias e conteúdos por período.

---

# 4. Processo de carga da Gold

O script responsável é:

```text
beam/carregar_gold.py
```

No workflow do Apache Hop, a entrada utilizada é o Parquet produzido pela execução operacional do Apache Beam:

```text
runtime/beam/*.parquet
```

O arquivo agregado pelo Beam é utilizado para popular:

```text
gold.engajamento_conteudo
```

As dimensões descritivas são enriquecidas com:

```text
silver.catalogo
```

A tabela mensal é calculada a partir de:

```text
silver.interacoes
+
silver.catalogo
```

---

# 5. Carga atômica e idempotência

A carga utiliza estratégia de carga completa:

```text
TRUNCATE + INSERT
```

As duas tabelas são limpas dentro da mesma transação:

```sql
TRUNCATE TABLE
    gold.engajamento_conteudo,
    gold.engajamento_conteudo_mensal;
```

Somente depois são gravadas novamente.

Essa estratégia possui dois objetivos:

```text
1. evitar duplicação em reexecuções;
2. garantir que as duas granularidades representem o mesmo snapshot da Silver.
```

O `commit` ocorre somente após a carga e as validações das duas estruturas.

Portanto, se ocorrer uma falha durante a publicação da Gold mensal, a transação inteira pode sofrer rollback e a Gold não fica parcialmente atualizada.

---

# 6. Validação e reconciliação

A execução validada apresentou:

```text
Gold consolidada:
  registros:   625
  interações: 1001
  conclusões:  154

Gold mensal:
  registros:   935
  meses:          8
  interações: 1001
  conclusões:  154
```

A carga possui validações que comparam a agregação mensal com a saída do Apache Beam.

As seguintes condições devem ser verdadeiras:

```text
SUM(gold mensal.total_interacoes)
=
SUM(Beam.total_interacoes)

SUM(gold mensal.quantidade_conclusoes)
=
SUM(Beam.quantidade_conclusoes)
```

Na execução validada:

```text
Beam interações:       1001
Gold mensal interações: 1001

Beam conclusões:        154
Gold mensal conclusões: 154
```

Portanto, não houve perda nem duplicação das medidas durante a mudança de granularidade.

---

# 7. View de ranking de engajamento

Foi criada:

```text
gold.vw_ranking_engajamento
```

## Pergunta de negócio

```text
Quais conteúdos apresentam maior volume de interações?
```

Campos disponíveis:

```text
conteudo_id
titulo
tipo
categoria
nivel
total_interacoes
tempo_total_segundos
media_percentual_conclusao
quantidade_conclusoes
ranking_interacoes
```

O ranking utiliza:

```sql
RANK() OVER (
    ORDER BY total_interacoes DESC
)
```

Empates recebem a mesma posição.

Na execução validada, três conteúdos apresentaram cinco interações e compartilharam a primeira posição.

---

# 8. View de resumo por categoria

Foi criada:

```text
gold.vw_resumo_categoria
```

## Pergunta de negócio

```text
Quais categorias concentram mais engajamento?
```

A view disponibiliza:

```text
total de conteúdos
total de interações
tempo total consumido
média do percentual de conclusão
quantidade de conclusões
```

Resultado da execução:

| Categoria | Conteúdos | Interações | Tempo total (s) | Média conclusão (%) | Conclusões |
|---|---:|---:|---:|---:|---:|
| Business Intelligence | 78 | 145 | 22937 | 53.92 | 21 |
| DevOps & Cloud | 79 | 141 | 16114 | 58.19 | 26 |
| Inteligência Artificial | 83 | 128 | 12367 | 55.71 | 19 |
| Banco de Dados | 81 | 128 | 15179 | 54.51 | 23 |
| Engenharia de Dados | 80 | 121 | 27164 | 50.16 | 17 |
| Ciência de Dados | 75 | 120 | 15854 | 56.54 | 17 |
| Segurança & Governança | 79 | 114 | 23055 | 49.24 | 10 |
| Programação & Software | 70 | 104 | 12236 | 55.15 | 21 |

Totais reconciliados:

```text
Conteúdos:  625
Interações: 1001
Conclusões: 154
```

## Observação sobre a média por categoria

A coluna:

```text
media_percentual_conclusao
```

da view por categoria é calculada como:

```sql
AVG(media_percentual_conclusao)
```

sobre os conteúdos.

Portanto, cada conteúdo possui o mesmo peso nessa média, independentemente de sua quantidade de interações.

Essa definição deve permanecer documentada para evitar interpretação incorreta do indicador.

---

# 9. View de conteúdos que merecem atenção

Foi criada:

```text
gold.vw_conteudos_atencao
```

## Pergunta de negócio

```text
Quais conteúdos recebem engajamento acima da média,
mas apresentam percentual de conclusão abaixo da média geral?
```

A regra utilizada é:

```text
total_interacoes >= média geral de interações
AND
media_percentual_conclusao < média geral de conclusão
```

Os limites são calculados dinamicamente a partir da própria Gold, evitando a utilização de valores arbitrários fixos.

Na execução validada, as referências eram aproximadamente:

```text
Média geral de interações: 1.60
Média geral de conclusão: 54.15%
```

A view também disponibiliza:

```text
taxa_conclusao_interacoes
media_interacoes_geral
media_conclusao_geral
diferenca_interacoes_media
diferenca_conclusao_media
```

Essa visão não classifica automaticamente um conteúdo como ruim.

Ela funciona como um sinal analítico para identificar conteúdos que atraem interações, mas apresentam comportamento de conclusão inferior à referência geral, permitindo investigação posterior.

---

# 10. Consumo no SQL Lab e Apache Superset

A camada Gold foi preparada para consumo direto por:

```text
Apache Superset
SQL Lab
```

As consultas e dashboards podem utilizar:

```text
gold.engajamento_conteudo
gold.engajamento_conteudo_mensal
gold.vw_ranking_engajamento
gold.vw_resumo_categoria
gold.vw_conteudos_atencao
```

A camada Bronze não deve ser utilizada diretamente como fonte dos dashboards.

A tabela mensal é especialmente adequada para:

```text
gráficos de linha
séries temporais
comparações mês a mês
evolução de interações
evolução de conclusões
```

As views consolidadas permitem rankings, comparações entre categorias e identificação de conteúdos que merecem investigação.

---

# 11. Integração com o workflow Apache Hop

A carga da Gold é executada pelo workflow após:

```text
Bronze
  ↓
Silver
  ↓
Qualidade
  ↓
Exportação Parquet
  ↓
Apache Beam DirectRunner
  ↓
Carga Gold
```

A action:

```text
Carga Gold
```

executa:

```text
beam/carregar_gold.py
```

utilizando:

```text
runtime/beam/*.parquet
```

Na execução validada pelo Apache Hop foram registrados:

```text
Linhas agregadas no Beam:        625
Interações representadas:       1001
Conclusões representadas:        154

Gold consolidada - registros:     625
Gold mensal - registros:          935
Gold mensal - meses:                8
Gold mensal - interações:        1001
Gold mensal - conclusões:         154
```

A action terminou com:

```text
Exit code da Carga Gold: 0
```

e o workflow seguiu para:

```text
Sucesso - Gold concluida
```

---

# Resultado

O RF26 foi implementado e validado com:

```text
schema Gold criado;

Gold consolidada por conteúdo;

Gold mensal por conteúdo e mês;

granularidades documentadas;

chaves definidas;

dimensões e medidas documentadas;

carga idempotente;

publicação atômica das duas tabelas;

reconciliação entre Beam e Gold;

625 conteúdos consolidados;

935 combinações conteúdo/mês;

8 meses de dados;

1001 interações reconciliadas;

154 conclusões reconciliadas;

ranking de engajamento;

resumo por categoria;

view de conteúdos que merecem atenção;

integração com Apache Hop;

estrutura disponível para SQL Lab e Apache Superset.
```