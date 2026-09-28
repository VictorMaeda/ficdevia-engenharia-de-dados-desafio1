# RF23 — Tratamento de Erros, Quarentena e Recuperação de Falhas

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Arquitetura de Quarentena

Para garantir que registros anômalos não interrompam toda a execução do pipeline nem corrompam a camada analítica Silver/Gold, o sistema adota o padrão de **Quarentena Isolada com Auditoria Detalhada**.

Em conformidade com o **RF23**:
* Cada registro rejeitado armazena: `registro_id` (chave sequencial), `origem`, `regra_violada`, `data_erro`, `mensagem_erro`, `execucao_id` e o `payload` bruto em formato JSONB;
* O pipeline prossegue processando os registros sadios sem encerrar a ingestão;
* São demonstrados três modos de falha distintos: **falha de arquivo**, **falha de regra de negócio** e **falha de conexão simulada**.

---

## 2. Simulação e Comprovação dos 3 Modos de Falha

Os registros com falha simulada residem na tabela física `quarentena.interacoes` no PostgreSQL e estão exportados em [`dados/quarentena/quarentena_falhas.json`](file:///c:/Users/01923483102/Documents/pessoal/fic_dev_ia/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/dados/quarentena/quarentena_falhas.json) e [`dados/quarentena/quarentena_interacoes.csv`](file:///c:/Users/01923483102/Documents/pessoal/fic_dev_ia/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/dados/quarentena/quarentena_interacoes.csv):

```text
┌─────────────┬──────────────────────────┬────────────────────────────┬────────────────────────────────────────────────────────┐
│ Registro ID │ Origem                   │ Regra Violada              │ Mensagem de Erro Detalhada                             │
├─────────────┼──────────────────────────┼────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1           │ interacoes.json          │ REGRA_PERCENTUAL_INVALIDO  │ percentual_conclusao fora da faixa permitida [0, 100]: │
│             │                          │ (Falha de Regra)           │ valor = -15.5                                          │
├─────────────┼──────────────────────────┼────────────────────────────┼────────────────────────────────────────────────────────┤
│ 2           │ catalogo_corrompido.csv  │ FALHA_FORMATO_ARQUIVO      │ Cabeçalho inválido ou colunas ausentes: delimitador    │
│             │                          │ (Falha de Arquivo)         │ corrompido ou payload truncado na linha 42             │
├─────────────┼──────────────────────────┼────────────────────────────┼────────────────────────────────────────────────────────┤
│ 3           │ api_streaming_interacoes │ FALHA_CONEXAO_TIMEOUT      │ Falha de conexão com a fonte: Connection timeout       │
│             │                          │ (Falha de Conexão)         │ (30000ms) ao consultar serviço upstream de eventos     │
└─────────────┴──────────────────────────┴────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Detalhamento Técnico das Falhas

### Falha 1 — Violação de Regra de Negócio (Data Validation)
* **Cenário:** O evento de interação contém `percentual_conclusao = -15.5`.
* **Ação do Apache Hop:** A etapa *Filter rows* detecta que o valor está fora do intervalo $[0.00, 100.00]$.
* **Desvio:** O fluxo encaminha o registro para o step *Table output (Quarentena)* com metadata `REGRA_PERCENTUAL_INVALIDO`. O restante das 1.001 interações válidas segue normalmente para `silver.interacoes`.

### Falha 2 — Corrupção Estrutural de Arquivo (File Format Error)
* **Cenário:** Ingestão de arquivo CSV com delimitador quebrado ou encoding incompatível.
* **Ação do Apache Hop:** A etapa *CSV file input* captura a exceção de parse por meio da aba de *Error handling* do step.
* **Desvio:** A linha corrompida em texto puro é encapsulada em `payload.raw_line` e inserida em `quarentena.interacoes` com status `FALHA_FORMATO_ARQUIVO`.

### Falha 3 — Conexão Recusada / Timeout (Network Failure)
* **Cenário:** A chamada REST API ou conexão JDBC com serviço parceiro esgota o limite de espera (30s).
* **Ação do Apache Hop:** A etapa de consulta externa dispara a rota de erro após 3 tentativas de retry exponencial.
* **Desvio:** A URL do endpoint e o código HTTP de erro são registrados em `quarentena.interacoes` com regra `FALHA_CONEXAO_TIMEOUT`.

---

## 4. Procedimento de Reprocessamento e Recuperação

1. **Correção dos Dados:** Analistas de dados revisam a tabela `quarentena.interacoes` e aplicam a retificação necessária no payload JSONB;
2. **Pipeline de Reprocessamento (`hop/pipelines/reprocessar_quarentena.hpl`):**
   * Lê os registros retificados da Quarentena;
   * Revalida contra as regras da Camada Silver;
   * Insere em `silver.interacoes` e atualiza a Quarentena com `data_reprocessamento = NOW()`;
3. **Auditabilidade:** Nenhum registro é apagado; o histórico completo de falha e correção é mantido para fins de auditoria de governança.
