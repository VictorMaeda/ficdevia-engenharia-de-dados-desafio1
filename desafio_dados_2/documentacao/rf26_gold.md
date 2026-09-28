\# RF26 — Camada Gold para Consumo Analítico



\## Objetivo



A camada Gold foi construída para disponibilizar dados consolidados e orientados às perguntas de negócio, evitando que ferramentas analíticas consultem diretamente a camada Bronze.



O fluxo utilizado foi:



```text

Bronze

&#x20; ↓

Silver

&#x20; ↓

Parquet

&#x20; ↓

Apache Beam

&#x20; ↓

Parquet agregado

&#x20; ↓

Gold

&#x20; ↓

SQL Lab / Superset

```



\---



\## Tabela principal



Foi criada a tabela:



```text

gold.engajamento\_conteudo

```



\### Granularidade



Cada linha representa:



```text

1 conteúdo identificado por conteudo\_id

```



Após a carga foram produzidas:



```text

625 linhas

```



correspondentes a 625 conteúdos distintos que possuem interações válidas.



\---



\## Chave



A chave primária da tabela é:



```text

conteudo\_id

```



Ela identifica unicamente cada conteúdo na camada Gold.



\---



\## Dimensões



As informações descritivas são provenientes de `silver.catalogo`.



Campos utilizados:



\- conteudo\_id

\- titulo

\- tipo

\- categoria

\- nivel



Esses campos permitem analisar as métricas de engajamento por diferentes dimensões de negócio.



\---



\## Medidas



A tabela Gold contém as seguintes medidas:



\### total\_interacoes



Quantidade total de interações associadas ao conteúdo.



Regra:



```text

COUNT(interações)

```



\### tempo\_total\_segundos



Soma do tempo consumido em todas as interações do conteúdo.



Regra:



```text

SUM(tempo\_consumido)

```



\### media\_percentual\_conclusao



Média do percentual de conclusão das interações do conteúdo.



Regra:



```text

SUM(percentual\_conclusao)

/

quantidade de interações com percentual preenchido

```



O valor é arredondado para duas casas decimais durante a carga da Gold.



\### quantidade\_conclusoes



Quantidade de interações classificadas como:



```text

tipo\_interacao = "conclusão"

```



\---



\## Auditoria da carga



A tabela possui o campo:



```text

data\_carga

```



Ele registra automaticamente a data e hora em que o registro foi carregado na camada Gold.



\---



\## Carga da Gold



O script responsável é:



```text

beam/carregar\_gold.py

```



A entrada utilizada é o Parquet produzido pelo pipeline Apache Beam executado com DirectRunner:



```text

beam/saida/direct/agregacao\_conteudo-00000-of-00001.parquet

```



Esse arquivo é enriquecido com as dimensões provenientes de:



```text

silver.catalogo

```



A carga utiliza:



```text

TRUNCATE + INSERT

```



antes da gravação dos registros.



Essa estratégia torna a carga completa reproduzível e evita duplicação em reexecuções sucessivas.



\---



\## Validação da carga



Resultado obtido:



```text

Conteúdos Gold:          625

Interações representadas: 1001

Total de conclusões:      154

```



Os 1001 registros válidos da `silver.interacoes` continuam representados na camada Gold após a agregação.



\---



\## View de ranking de engajamento



Foi criada:



```text

gold.vw\_ranking\_engajamento

```



\### Pergunta de negócio



```text

Quais conteúdos apresentam maior volume de interações?

```



Campos disponíveis:



\- conteudo\_id

\- titulo

\- tipo

\- categoria

\- nivel

\- total\_interacoes

\- tempo\_total\_segundos

\- media\_percentual\_conclusao

\- quantidade\_conclusoes

\- ranking\_interacoes



O ranking utiliza:



```sql

RANK() OVER (

&#x20;   ORDER BY total\_interacoes DESC

)

```



Empates recebem a mesma posição.



Na execução validada, três conteúdos apresentaram cinco interações e compartilharam a primeira posição.



\---



\## View de resumo por categoria



Foi criada:



```text

gold.vw\_resumo\_categoria

```



\### Pergunta de negócio



```text

Quais categorias concentram mais engajamento?

```



A view apresenta:



\- total de conteúdos;

\- total de interações;

\- tempo total consumido;

\- média do percentual de conclusão dos conteúdos;

\- quantidade de conclusões.



Resultado da execução:



| Categoria | Conteúdos | Interações | Tempo total (s) | Média conclusão (%) | Conclusões |

|---|---:|---:|---:|---:|---:|

| Business Intelligence | 78 | 145 | 22937 | 53.92 | 21 |

| DevOps \& Cloud | 79 | 141 | 16114 | 58.19 | 26 |

| Inteligência Artificial | 83 | 128 | 12367 | 55.71 | 19 |

| Banco de Dados | 81 | 128 | 15179 | 54.51 | 23 |

| Engenharia de Dados | 80 | 121 | 27164 | 50.16 | 17 |

| Ciência de Dados | 75 | 120 | 15854 | 56.54 | 17 |

| Segurança \& Governança | 79 | 114 | 23055 | 49.24 | 10 |

| Programação \& Software | 70 | 104 | 12236 | 55.15 | 21 |



Totais reconciliados:



```text

Conteúdos:  625

Interações: 1001

Conclusões: 154

```



\---



\## Observação sobre a média por categoria



A coluna `media\_percentual\_conclusao` da view por categoria é calculada como a média das médias dos conteúdos:



```sql

AVG(media\_percentual\_conclusao)

```



Portanto, cada conteúdo possui o mesmo peso na média da categoria, independentemente de sua quantidade de interações.



Essa definição deve ser mantida documentada para evitar interpretação equivocada do indicador.



\---



\## Consumo analítico



A camada Gold foi preparada para ser utilizada diretamente por:



```text

Apache Superset

SQL Lab

```



Os dashboards e consultas analíticas deverão utilizar:



```text

gold.engajamento\_conteudo

gold.vw\_ranking\_engajamento

gold.vw\_resumo\_categoria

```



e não consultar diretamente as tabelas da camada Bronze.



\---



\## Resultado



O RF26 foi validado com sucesso:



\- schema Gold criado;

\- tabela analítica criada;

\- granularidade definida;

\- chave primária definida;

\- dimensões e medidas consolidadas;

\- carga derivada da Silver e do processamento Beam;

\- 625 conteúdos carregados;

\- 1001 interações reconciliadas;

\- views orientadas às perguntas de negócio criadas;

\- estrutura pronta para SQL Lab e Apache Superset.

