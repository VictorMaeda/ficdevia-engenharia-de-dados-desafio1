# RF25 — Processamento Distribuído com Apache Beam

## Objetivo

Foi implementado um pipeline Apache Beam para processar o conjunto de interações da camada Silver em formato Parquet.

O pipeline executa uma agregação por `conteudo_id`, produzindo indicadores de engajamento por conteúdo.

A mesma regra de negócio foi executada com:

- DirectRunner;
- SparkRunner.

---

## Entrada

Dataset:

```text
dados/silver/interacoes_parquet/
```

Formato:

```text
Parquet
```

Quantidade de registros de entrada:

```text
1001 interações
```

O conjunto foi previamente gerado a partir de `silver.interacoes`.

---

## Regra de negócio

Os registros foram agrupados por:

```text
conteudo_id
```

Para cada conteúdo foram calculadas as seguintes métricas:

- total de interações;
- tempo total consumido em segundos;
- média do percentual de conclusão;
- quantidade de interações do tipo conclusão.

Fluxo lógico:

```text
Parquet Silver
      │
      ▼
Apache Beam
      │
      ▼
Agrupamento por conteudo_id
      │
      ├── total_interacoes
      ├── tempo_total_segundos
      ├── media_percentual_conclusao
      └── quantidade_conclusoes
      │
      ▼
Parquet agregado
```

---

## Implementação

Script utilizado:

```text
beam/pipeline_beam.py
```

Entrada:

```text
dados/silver/interacoes_parquet/*/*.parquet
```

Saída DirectRunner:

```text
beam/saida/direct/
```

Saída SparkRunner:

```text
beam/saida/spark/
```

Formato de saída:

```text
Parquet
```

---

## Ambiente

### Python

```text
Python 3.14.4
```

### Apache Beam

```text
Apache Beam 2.76.0
```

### Ambiente de execução

```text
WSL
```

---

## Execução com DirectRunner

Comando utilizado:

```bash
python desafio_dados_2/beam/pipeline_beam.py \
  --input '/mnt/c/Projeto/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/dados/silver/interacoes_parquet/*/*.parquet' \
  --output '/mnt/c/Projeto/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/beam/saida/direct/agregacao_conteudo' \
  --runner=DirectRunner
```

Durante a execução, o Apache Beam utilizou o PrismRunner internamente.

Resultado:

```text
Pipeline concluído com sucesso.
Tempo total: 4.014691 s
```

Validação:

```text
Linhas agregadas: 625
Total de interações representadas: 1001
```

Schema da saída:

```text
conteudo_id: int32
total_interacoes: int64
tempo_total_segundos: int64
media_percentual_conclusao: double
quantidade_conclusoes: int64
```

---

## Execução com SparkRunner

Configuração utilizada:

```text
Runner: SparkRunner
Spark master: local[4]
Environment type: LOOPBACK
```

Comando utilizado:

```bash
python desafio_dados_2/beam/pipeline_beam.py \
  --input '/mnt/c/Projeto/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/dados/silver/interacoes_parquet/*/*.parquet' \
  --output '/mnt/c/Projeto/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/beam/saida/spark/agregacao_conteudo' \
  --runner=SparkRunner \
  --spark_master_url='local[4]' \
  --environment_type=LOOPBACK
```

Resultado:

```text
Pipeline concluído com sucesso.
Tempo total: 28.215876 s
```

Validação:

```text
Linhas agregadas: 625
Total de interações representadas: 1001
```

Schema da saída:

```text
conteudo_id: int32
total_interacoes: int64
tempo_total_segundos: int64
media_percentual_conclusao: double
quantidade_conclusoes: int64
```

---

## Comparação dos runtimes

| Métrica | DirectRunner | SparkRunner |
|---|---:|---:|
| Registros de entrada | 1001 | 1001 |
| Linhas agregadas | 625 | 625 |
| Interações representadas | 1001 | 1001 |
| Tempo total | 4.014691 s | 28.215876 s |
| Formato de entrada | Parquet | Parquet |
| Formato de saída | Parquet | Parquet |

---

## Validação de equivalência

Os resultados produzidos pelos dois runtimes foram ordenados por `conteudo_id` e comparados.

Resultado:

```text
Linhas Direct: 625
Linhas Spark:  625
Mesmos conteudo_id: True
Mesmo total_interacoes: True
Mesmo tempo_total_segundos: True
Mesma quantidade_conclusoes: True
Maior diferença nas médias: 0.0
```

Portanto, os dois runtimes produziram exatamente a mesma regra de negócio e os mesmos resultados.

---

## Análise de desempenho

Neste experimento, o DirectRunner apresentou menor tempo de execução:

```text
DirectRunner: 4.014691 s
SparkRunner:  28.215876 s
```

O SparkRunner apresentou maior tempo principalmente devido ao custo de inicialização do runtime distribuído, incluindo a inicialização do Job Server, comunicação gRPC e preparação do ambiente Spark.

O conjunto utilizado possui apenas 1001 registros, volume pequeno demais para que o paralelismo do Spark compense esse custo inicial.

Em volumes maiores, o Spark tende a se tornar mais adequado quando o ganho de processamento paralelo supera o overhead de inicialização e coordenação.

Portanto, para este volume específico, o DirectRunner foi mais eficiente em tempo de execução.

Isso não invalida o uso do Spark, pois o objetivo do experimento foi comprovar que a mesma regra pode ser executada em runtimes distintos sem alteração da lógica do pipeline.

---

## Resultado

O RF25 foi validado com sucesso:

- pipeline Apache Beam implementado;
- entrada em Parquet;
- saída em Parquet;
- DirectRunner executado com sucesso;
- SparkRunner executado com sucesso;
- 1001 registros processados em ambos;
- 625 conteúdos agregados em ambos;
- resultados equivalentes entre os runtimes;
- tempos e configurações registrados.
