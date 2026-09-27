\# RF24 — Formato Parquet e Particionamento



\## Dataset utilizado



Foi utilizado o conjunto `silver.interacoes`, contendo 1001 registros válidos após o processamento da camada Silver.



Campos exportados:



\- usuario\_id

\- conteudo\_id

\- tipo\_interacao

\- data\_hora

\- tempo\_consumido

\- percentual\_conclusao

\- avaliacao\_atribuida

\- execucao\_id

\- data\_hora\_padronizacao



Também foi criada a coluna derivada `ano\_mes`, utilizada exclusivamente para particionamento.



\---



\## Estratégia de particionamento



O conjunto Parquet foi particionado por `ano\_mes`, derivado do campo `data\_hora`.



Exemplo da estrutura:



```text

interacoes\_parquet/

├── ano\_mes=2026-01/

├── ano\_mes=2026-02/

├── ano\_mes=2026-03/

├── ano\_mes=2026-04/

├── ano\_mes=2026-05/

├── ano\_mes=2026-06/

├── ano\_mes=2026-07/

└── ano\_mes=2026-08/

```



A escolha foi feita porque as interações representam eventos temporais e análises futuras normalmente utilizam recortes por período.



Em volumes maiores, esse particionamento permite que ferramentas de processamento leiam apenas as partições necessárias, reduzindo a quantidade de dados varridos.



\---



\## Comparação CSV x Parquet



Foi utilizado exatamente o mesmo conjunto de 1001 registros para os dois formatos.



| Métrica | CSV | Parquet |

|---|---:|---:|

| Registros | 1001 | 1001 |

| Tamanho | 85.81 KB | 74.34 KB |

| Tempo de escrita | 0.007439 s | 0.010523 s |

| Tempo de leitura | 0.004176 s | 0.010228 s |



Redução de armazenamento obtida pelo Parquet:



\*\*13.37%\*\*



\---



\## Schema preservado no Parquet



O schema resultante foi:



```text

usuario\_id: int32

conteudo\_id: int32

tipo\_interacao: string

data\_hora: timestamp\[us]

tempo\_consumido: int32

percentual\_conclusao: decimal128(5, 2)

avaliacao\_atribuida: int16

execucao\_id: string

data\_hora\_padronizacao: timestamp\[us]

ano\_mes: string

```



Os tipos foram definidos explicitamente durante a exportação para evitar conversões automáticas inadequadas.



Por exemplo, `avaliacao\_atribuida` possui valores nulos e, sem definição explícita, poderia ser convertida para ponto flutuante. No arquivo Parquet final ela foi mantida como inteiro de 16 bits com suporte a valores nulos.



Os campos de auditoria também foram preservados:



\- `execucao\_id`

\- `data\_hora\_padronizacao`



\---



\## Compressão



Foi utilizada compressão:



```text

Snappy

```



A compressão Snappy foi escolhida por oferecer bom equilíbrio entre redução de tamanho e velocidade de leitura e escrita.



\---



\## Análise dos resultados



O Parquet apresentou redução de \*\*13.37% no tamanho em disco\*\* em relação ao CSV.



Entretanto, neste experimento, a leitura do CSV foi mais rápida:



```text

CSV:     0.004176 s

Parquet: 0.010228 s

```



A escrita do CSV também apresentou tempo ligeiramente menor:



```text

CSV:     0.007439 s

Parquet: 0.010523 s

```



Esse resultado não significa que o formato Parquet seja inadequado.



O conjunto utilizado possui apenas \*\*1001 registros\*\*, um volume muito pequeno para demonstrar plenamente as vantagens de um formato colunar.



Além disso, o Parquet foi dividido em diferentes partições mensais. Em um conjunto tão pequeno, o custo de descoberta das partições e abertura dos arquivos representa uma parcela significativa do tempo total de leitura.



Em volumes maiores, especialmente quando as consultas acessam somente determinadas colunas ou períodos específicos, o formato Parquet tende a se beneficiar de:



\- armazenamento colunar;

\- compressão;

\- schema explícito;

\- leitura seletiva de colunas;

\- leitura seletiva de partições;

\- menor volume de dados lidos em consultas analíticas.



Portanto, neste experimento, o principal benefício observado foi a redução de armazenamento e a preservação explícita do schema.



O ganho de desempenho de leitura não pôde ser demonstrado devido ao pequeno volume de dados utilizado.



\---



\## Limitações do experimento



As principais limitações identificadas foram:



1\. O conjunto possui apenas 1001 registros, o que é pequeno para uma comparação de desempenho entre formatos destinados a processamento analítico em escala.



2\. Os tempos medidos estão na ordem de milissegundos e podem sofrer influência de cache do sistema operacional, carga momentânea da máquina e inicialização das bibliotecas.



3\. O Parquet foi particionado por mês, gerando múltiplos arquivos pequenos. Em datasets reduzidos, isso aumenta proporcionalmente o overhead de leitura.



4\. A comparação realizou leitura completa do conjunto. Uma das principais vantagens do Parquet ocorre quando apenas algumas colunas ou partições são necessárias.



5\. As medições foram executadas em ambiente local de desenvolvimento e não representam diretamente o comportamento em infraestrutura distribuída ou em datasets de grande escala.



\---



\## Implementação



Script responsável pela exportação:



```text

beam/exportar\_parquet.py

```



Origem dos dados:



```text

PostgreSQL

└── silver.interacoes

```



Saída CSV:



```text

dados/silver/interacoes.csv

```



Saída Parquet:



```text

dados/silver/interacoes\_parquet/

```



Fluxo implementado:



```text

silver.interacoes

&#x20;       │

&#x20;       ▼

exportar\_parquet.py

&#x20;       │

&#x20;       ├── interacoes.csv

&#x20;       │

&#x20;       └── interacoes\_parquet/

&#x20;               │

&#x20;               ├── ano\_mes=2026-01/

&#x20;               ├── ano\_mes=2026-02/

&#x20;               ├── ano\_mes=2026-03/

&#x20;               └── ...

```



\---



\## Resultado



A exportação foi concluída com sucesso para os dois formatos.



Quantidade de registros:



```text

CSV:     1001

Parquet: 1001

```



Redução de armazenamento:



```text

13.37%

```



O experimento comprovou a geração de Parquet particionado, preservação de schema e auditoria, além da comparação objetiva com CSV utilizando o mesmo recorte da camada Silver.

