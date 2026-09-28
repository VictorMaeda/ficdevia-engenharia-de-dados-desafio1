# RF18 — Filtros Cruzados e Configuração de Alertas no Apache Superset

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Implementação no Apache Superset

No Apache Superset, a camada de consumo foi configurada para fornecer uma experiência analítica de padrão executivo e pedagógico para a tomada de decisão da diretoria acadêmica, apoiando-se diretamente nos dados consolidados da **Camada Gold**.

Para atender estritamente ao requisito **RF18**, foram implementados:
1. **Filtros Globais de Negócio (Filter Bar Lateral):** Segmentação multidimensional por Dimensões de Negócio e Pedagógicas:
   * **Categoria Temática** (`categoria`);
   * **Formato de Conteúdo / Mídia** (`tipo`: Vídeo, Curso, Podcast, Artigo);
   * **Nível de Dificuldade** (`nivel`: Básico, Intermediário, Avançado);
   * **Faixa de Retenção Pedagógica** (`status_retencao_pedagogica`: Crítico, Excelente, Satisfatório, Em Desenvolvimento).
2. **Filtros Cruzados Interativos (Cross-Filtering):** Interação bidirecional entre visualizações nativas do dashboard (clique na barra da categoria recalcula todo o painel);
3. **Alerta Mensurável Automatizado (Alerts & Reports):** Monitoramento contínuo de conteúdos críticos com notificação dirigida por e-mail;
4. **Painel Analítico Completo (9 Componentes Integrados):** 4 KPIs estratégicos, gráficos de tendência, distribuição multidimensional e matriz de diagnóstico de evasão.

* **URL do Dashboard:** `http://localhost:8088/superset/dashboard/dashboard-desafio2-governado/`
* **Status:** Publicado (`published = True`), responsivo e validado sem erros de renderização.

---

## 2. Arquitetura Completa de Visualizações do Dashboard

O dashboard conta com 9 componentes analíticos integrados de forma responsiva:

| ID | Nome do Componente | Tipo de Visualização | Dataset de Origem | Função Analítica |
|---|---|---|---|---|
| **1** | `[KPI] Total de Interações` | `big_number_total` | `gold.engajamento_conteudo` | Volume bruto de eventos de estudo registrados (1.182 interações). |
| **2** | `[KPI] Conclusões Efetivas` | `big_number_total` | `gold.engajamento_conteudo` | Sessões concluídas integralmente em 100% (168 conclusões). |
| **3** | `[KPI] Taxa Média de Conclusão` | `big_number_total` | `gold.engajamento_conteudo` | Aproveitamento percentual global formatado (`14.2%`). |
| **4** | `[KPI] Conteúdos Monitorados` | `big_number_total` | `gold.engajamento_conteudo` | Total de títulos ativos no catálogo acadêmico (625 conteúdos). |
| **5** | `Engajamento e Conclusão por Categoria` | `echarts_timeseries_bar` | `gold.engajamento_conteudo` | **Emissor do Cross-Filter:** Volume de interações e conclusões por área temática. |
| **6** | `Evolução Mensal de Interações e Conclusões` | `echarts_timeseries_line` | `ds_virtual_evolucao_temporal_eficiencia` | **Receptor do Cross-Filter:** Série temporal com tendência mensal de engajamento. |
| **7** | `Distribuição de Interações por Nível` | `pie` (donut) | `gold.engajamento_conteudo` | Proporção de consumo entre Básico (38.8%), Intermediário (35.0%) e Avançado (26.1%). |
| **8** | `Distribuição de Interações por Formato` | `pie` (donut) | `gold.engajamento_conteudo` | Segmentação por formato: Vídeos (363), Podcasts (282), Cursos (275) e Artigos (262). |
| **9** | `Tabela Ranqueada de Conteúdos e Diagnóstico de Evasão` | `table` | `ds_virtual_desempenho_engajamento_conteudos` | **Receptor do Cross-Filter:** Tabela com busca, paginação e matriz de intervenção didática. |

---

## 3. Filtros Globais do Dashboard (Filter Bar Lateral)

Em conformidade com as diretrizes de usabilidade executiva, o painel foca estritamente em **dimensões categóricas e pedagógicas de negócio**, sem dependência de seletores temporais:

* **Filtro de Categoria Temática (Dimensão de Negócio):**
  * **Campo de Referência:** `categoria` (valores: `Engenharia de Dados`, `Inteligência Artificial`, `Ciência de Dados`, `Banco de Dados`, `DevOps & Cloud`, `Programação & Software`, `Business Intelligence`, `Segurança & Governança`).
  * **Tipo de Controle:** Seleção múltipla com busca rápida e suporte a seleção total (`Select All`).
* **Filtro de Formato de Conteúdo / Mídia:**
  * **Campo de Referência:** `tipo` (valores: `Vídeo`, `Curso`, `Podcast`, `Artigo`).
  * **Tipo de Controle:** Seleção múltipla com aplicação instantânea.
  * **Objetivo:** Permitir ao comitê pedagógico isolar o comportamento de engajamento por tipo de recurso instrucional.
* **Filtro de Nível de Dificuldade:**
  * **Campo de Referência:** `nivel` (valores: `Básico`, `Intermediário`, `Avançado`).
  * **Tipo de Controle:** Seleção múltipla com busca rápida.
* **Filtro de Faixa de Retenção Pedagógica (Risco de Evasão):**
  * **Campo de Referência:** `status_retencao_pedagogica`.
  * **Valores:** `Crítico: Alta Atração / Baixa Retenção`, `Excelente: Alta Retenção`, `Satisfatório: Retenção Moderada`, `Em Desenvolvimento / Baixo Volume`.
  * **Tipo de Controle:** Seleção múltipla instantânea, permitindo filtrar diretamente os conteúdos com sinal vermelho.

**Escopo de Aplicação:** Os filtros são aplicados simultaneamente a todos os gráficos que compartilham as dimensões na camada Gold.

---

## 4. Configuração de Filtros Cruzados (Cross-Filtering)

O **Cross-Filtering** permite que o usuário clique em um elemento de um gráfico (por exemplo, na barra correspondente à categoria *"Engenharia de Dados"* ou *"Inteligência Artificial"*) e todos os outros gráficos do dashboard sejam automaticamente filtrados para exibir exclusivamente os dados daquela categoria selecionada.

### Como foi configurado no Superset:
1. Habilitação global via metadados: `"cross_filters_enabled": true`.
2. **Gráfico Emissor:** *Engajamento e Conclusão por Categoria* (gráfico com flag `emit_filter = True`).
3. **Gráficos Receptores:**
   * *Tabela Ranqueada de Conteúdos e Diagnóstico de Evasão* (dataset virtual `ds_virtual_desempenho_engajamento_conteudos`).
   * *Evolução Mensal de Interações e Conclusões* (dataset virtual `ds_virtual_evolucao_temporal_eficiencia`).
   * *KPIs e Gráficos de Distribuição de Perfil* que compartilham a dimensão no escopo global.

### Demonstração do Fluxo Interativo:
* Ao clicar na barra da categoria desejada:
  1. A tabela de conteúdos abaixo exibe de imediato apenas os cursos daquela área específica;
  2. O gráfico de série temporal filtra as linhas para demonstrar o comportamento mensal daquela área;
  3. Os KPIs e fatias de nível/formato refletem a volumetria da categoria filtrada;
  4. Um indicador visual de filtro ativo surge na barra superior com o botão para desfazer o filtro cruzado (`Clear filter`).

---

## 5. Configuração do Alerta Automatizado (Alerts & Reports)

Para garantir que a coordenação pedagógica atue tempestivamente em casos de retenção anômala, foi configurado um alerta baseado em limites mensuráveis (SQL-based alert).

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   CONFIGURAÇÃO DO ALERTA NO SUPERSET                   │
├───────────────────────┬────────────────────────────────────────────────┤
│ Campo de Configuração │ Valor Definido / Justificativa                 │
├───────────────────────┼────────────────────────────────────────────────┤
│ Nome do Alerta        │ [ALERTA-CRITICO] Conteúdos com Evasão Severa   │
│ Descrição             │ Dispara aviso quando há cursos de alta procura │
│                       │ com taxa de conclusão perigosamente baixa.     │
│ Banco de Dados        │ PostgreSQL (pg_desafio2 / Camada Gold)         │
│ Tipo de Disparo       │ Alert (disparo condicional por SQL)            │
│ Periodicidade (Cron)  │ 0 8 * * 1 (Toda segunda-feira, às 08:00 AM)    │
│ Destinatário          │ coordenacao.pedagogica@ficdevia.edu.br         │
│ Canal de Notificação  │ E-mail / Slack Webhook                         │
│ Limiar de Condição    │ Valor retornado pela consulta >= 1             │
│ Estado Atual          │ Triggered (Disparado com valor 5.0)            │
└───────────────────────┴────────────────────────────────────────────────┘
```

### Consulta SQL de Avaliação da Condição de Disparo:

```sql
-- Avaliação de conteúdos com alta atração e conclusão crítica
SELECT
    COUNT(*) AS qtd_conteudos_criticos
FROM gold.vw_conteudos_atencao
WHERE
    total_interacoes >= 30
    AND taxa_conclusao_interacoes < 25.0;
```

### Condição de Disparo e Ação Esperada:
* **Condição Algébrica:** Se `qtd_conteudos_criticos >= 1`.
* **Ação Esperada:** Enviar notificação com o relatório contendo a lista dos IDs, títulos, taxa de conclusão e sugestão de intervenção didática imediata (tutoria ativa e nivelamento pedagógico).

---

## 6. Comprovação da Avaliação da Condição de Disparo

Quando executada sobre a base de dados populada da Camada Gold, a consulta retorna:

```text
 qtd_conteudos_criticos
------------------------
                      5
(1 row)
```

**Resultado do Teste de Disparo:**
* **Condição:** `5 >= 1` $\rightarrow$ **VERDADEIRO (TRIGGER ACTIVATED)**.
* O Superset avalia a regra com sucesso e sinaliza o estado do alerta como **`Triggered`** (Disparado), gerando o payload de envio com os dados dos cursos em alerta.

---

## 7. Validação Técnica de Execução dos Gráficos (Zero Erros)

Todos os 9 gráficos foram validados via motor de execução de consultas do Superset (`ChartDataCommand`), garantindo retorno de dados sem falhas de renderização:

```text
Total charts on dashboard layout: 9
✅ Chart 30 ([KPI] Total de Interações): SUCCESS! Rows=1
✅ Chart 31 ([KPI] Conclusões Efetivas): SUCCESS! Rows=1
✅ Chart 32 ([KPI] Taxa Média de Conclusão): SUCCESS! Rows=1
✅ Chart 33 ([KPI] Conteúdos Monitorados): SUCCESS! Rows=1
✅ Chart 1  (Engajamento e Conclusão por Categoria): SUCCESS! Rows=8
✅ Chart 6  (Evolução Mensal de Interações e Conclusões): SUCCESS! Rows=8
✅ Chart 17 (Distribuição de Interações por Nível): SUCCESS! Rows=3
✅ Chart 18 (Distribuição de Interações por Formato): SUCCESS! Rows=4
✅ Chart 7  (Tabela Ranqueada de Conteúdos e Diagnóstico de Evasão): SUCCESS! Rows=100
```
