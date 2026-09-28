# RF31 — Regras e Testes Automatizados de Qualidade de Dados

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Governança de Qualidade (DataOps)

A garantia de qualidade no pipeline é operacionalizada por um framework automatizado implementado em Python (`qualidade/executar_testes.py`) que audita as tabelas padronizadas da **Camada Silver** antes que os dados sejam agregados e disponibilizados na **Camada Gold**.

Para atender estritamente ao requisito **RF31**:
1. Foram implementadas **5 regras distribuídas pelas dimensões essenciais de qualidade**: Completude, Validade, Unicidade, Consistência e Integridade Referencial;
2. Cada teste possui **fórmula explícita, limite aceitável (threshold), severidade e ação de contingência**;
3. Os resultados de cada rodada de validação são persistidos individualmente com `id_execucao`, timestamp UTC, status e pontuação consolidada em `qualidade/resultados/`;
4. Falhas em regras de severidade **CRÍTICA** bloqueiam imediatamente o avanço do pipeline e a publicação na camada analítica Gold (*Quality Gate*).

---

## 2. Matriz Formal de Regras de Qualidade

```text
┌────────┬─────────────────────────────┬──────────────┬───────────────────┬──────────────┬─────────────┬────────────────────────────────────────────────────────┐
│ Código │ Nome da Regra               │ Dimensão     │ Tabela de Origem  │ Limite Mín.  │ Severidade  │ Ação de Contingência / Resolução                       │
├────────┼─────────────────────────────┼──────────────┼───────────────────┼──────────────┼─────────────┼────────────────────────────────────────────────────────┤
│ Q01    │ Completude de Interações    │ Completude   │ silver.interacoes │ 100.0%       │ CRÍTICA     │ Bloquear carga Gold; desviar nulos para quarentena.    │
│ Q02    │ Validade de Percentual      │ Validade     │ silver.interacoes │ 100.0%       │ ALTA        │ Alertar engenharia; descartar valores fora de [0, 100].│
│ Q03    │ Unicidade de Conteúdo       │ Unicidade    │ silver.catalogo   │ 100.0%       │ CRÍTICA     │ Bloquear publicação Gold; executar deduplicação MDM.   │
│ Q04    │ Consistência de Conclusão   │ Consistência │ silver.interacoes │ 98.0%        │ MÉDIA       │ Logar divergência e auditar regras de negócio na Silver│
│ Q05    │ Integridade Referencial     │ Integridade  │ silver.interacoes │ 100.0%       │ CRÍTICA     │ Bloquear carga Gold; rejeitar interações órfãs.        │
└────────┴─────────────────────────────┴──────────────┴───────────────────┴──────────────┴─────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Especificação Detalhada dos Testes

### Q01 — Completude dos Campos Obrigatórios de Interações
* **Dimensão:** Completude
* **Fonte Auditada:** `silver.interacoes`
* **Fórmula:**
  $$\text{Taxa de Completude} = \left( \frac{\text{Registros Válidos}}{\text{Total de Registros}} \right) \times 100$$
* **Campos Auditados:** `usuario_id`, `conteudo_id`, `tipo_interacao`, `data_hora`, `tempo_consumido`, `percentual_conclusao`, `execucao_id`, `data_hora_padronizacao`.
* **Critério de Invalidação:** Presença de valor `NULL` ou string vazia em qualquer dos atributos mandatórios.
* **Limite Mínimo Aceitável:** 100.0%
* **Severidade:** **CRÍTICA** (Gera bloqueio na orquestração).

### Q02 — Validade do Percentual de Conclusão
* **Dimensão:** Validade
* **Fonte Auditada:** `silver.interacoes`
* **Fórmula:**
  $$\text{Taxa de Validade} = \left( \frac{\text{Registros com } 0.00 \le \text{percentual} \le 100.00}{\text{Total de Registros}} \right) \times 100$$
* **Critério de Invalidação:** `percentual_conclusao < 0.00` ou `percentual_conclusao > 100.00`.
* **Limite Mínimo Aceitável:** 100.0%
* **Severidade:** **ALTA** (Registra incidente e notifica DataOps).

### Q03 — Unicidade da Chave Primária de Conteúdo
* **Dimensão:** Unicidade
* **Fonte Auditada:** `silver.catalogo`
* **Fórmula:**
  $$\text{Taxa de Unicidade} = \left( 1 - \frac{\text{Total} - \text{Total Distinto}}{\text{Total de Registros}} \right) \times 100$$
* **Critério de Invalidação:** Ocorrência de mais de uma linha com o mesmo `conteudo_id`.
* **Limite Mínimo Aceitável:** 100.0%
* **Severidade:** **CRÍTICA** (Bloqueio mandatório; viola integridade de dados mestres).

### Q04 — Consistência Lógica entre Conclusão e Percentual
* **Dimensão:** Consistência
* **Fonte Auditada:** `silver.interacoes`
* **Fórmula:**
  $$\text{Taxa de Consistência} = \left( \frac{\text{Registros Lógicos}}{\text{Total de Registros}} \right) \times 100$$
* **Regra de Negócio:** Se `tipo_interacao = 'conclusao'`, obrigatoriamente `percentual_conclusao = 100.00`.
* **Limite Mínimo Aceitável:** 98.0%
* **Severidade:** **MÉDIA** (Gera warning e relatório de divergência).

### Q05 — Integridade Referencial entre Interações e Catálogo
* **Dimensão:** Integridade Referencial
* **Fonte Auditada:** `silver.interacoes` (chave estrangeira `conteudo_id` contra `silver.catalogo.conteudo_id`)
* **Fórmula:**
  $$\text{Taxa de Integridade} = \left( 1 - \frac{\text{Interações com } \text{conteudo\_id} \text{ Inexistente}}{\text{Total de Interações}} \right) \times 100$$
* **Critério de Invalidação:** Interações apontando para cursos ou materiais não cadastrados no catálogo mestre.
* **Limite Mínimo Aceitável:** 100.0%
* **Severidade:** **CRÍTICA** (Bloqueio mandatório; evita métricas órfãs na Gold).

---

## 4. Evidência de Execução e Evolução Temporal

Execuções consecutivas do script `qualidade/executar_testes.py` demonstraram a estabilidade e a evolução das métricas no pipeline:

```text
================================================================================
RELATÓRIO DE QUALIDADE DE DADOS — PIPELINE GOVERNADO FIC DEV IA
Execução ID: EXEC_20260928_QUALIDADE_001 | Status: SUCESSO (100.000%)
================================================================================
[PASS] Q01_COMPLETUDE             | Esperado: 100.0% | Obtido: 100.000% | Válidos: 1001/1001
[PASS] Q02_VALIDADE_PERCENTUAL    | Esperado: 100.0% | Obtido: 100.000% | Válidos: 1001/1001
[PASS] Q03_UNICIDADE_CATALOGO     | Esperado: 100.0% | Obtido: 100.000% | Válidos: 1000/1000
[PASS] Q04_CONSISTENCIA_CONCLUSAO | Esperado:  98.0% | Obtido: 100.000% | Válidos: 1001/1001
[PASS] Q05_INTEGRIDADE_REFERENCIA | Esperado: 100.0% | Obtido: 100.000% | Válidos: 1001/1001
================================================================================
Resultado Final: QUALITY GATE APROVADO — Carga para a Camada Gold AUTORIZADA.
================================================================================
```

Os relatórios estruturados em JSON de cada execução estão versionados no diretório [`qualidade/resultados/`](file:///c:/Users/01923483102/Documents/pessoal/fic_dev_ia/ficdevia-engenharia-de-dados-desafio1/desafio_dados_2/qualidade/resultados/).
