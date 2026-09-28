# RF16 — Storytelling Executivo com Dados

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  
**Versão:** 1.0 — 2026  

---

## 1. Pergunta Decisória Central

> **"Quais conteúdos e áreas do conhecimento concentram alta atração de alunos mas apresentam abandono crítico antes da conclusão, e quais ações pedagógicas e de recomendação personalizada devem ser acionadas pela diretoria para elevar a taxa de retenção da plataforma em 25%?"**

---

## 2. Contexto do Negócio

A plataforma educacional expandiu significativamente seu catálogo de cursos, trilhas, vídeos e podcasts após as entregas do Desafio 1. O volume de acessos diários e interações aumentou expressivamente, porém a coordenação acadêmica identificou que o crescimento de acessos não se traduziu proporcionalmente em conclusões de cursos e certificações.

Para responder a esse desafio institucional com rigor metodológico, consolidou-se a **Camada Gold** via pipeline automatizado (Apache Hop + Apache Beam + PostgreSQL), permitindo que decisões acadêmicas não dependam de intuições subjetivas, mas sim de dados auditados e governados.

---

## 3. Evidências: Sequência Lógica de Visualizações

A narrativa executiva desdobra-se em três visualizações integradas no Apache Superset:

### Visualização 1: Panorama Geral de Engajamento vs. Taxa de Conclusão por Categoria
* **Tipo:** Gráfico de Barras Compostas com Eixo Duplo (Volume de Interações vs. % Conclusão).
* **Fonte de Dados:** `gold.vw_resumo_categoria`.
* **Título Informativo:** *"Categorias de Tecnologia atraem 62% do tráfego total, mas possuem taxa de conclusão média 18 pontos percentuais inferior às áreas de Negócios e Gestão."*

| Categoria | Total de Conteúdos | Interações Totais | Horas Consumidas | Média Progresso (%) | Taxa Efetiva de Conclusão (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Data & Analytics** | 42 | 485 | 1.840 h | 48.2% | **24.5%** |
| **Inteligência Artificial** | 38 | 512 | 2.120 h | 44.7% | **21.8%** |
| **Engenharia de Software**| 35 | 390 | 1.450 h | 52.1% | **31.2%** |
| **Negócios & Gestão** | 20 | 180 | 720 h | 68.4% | **54.4%** |
| **Design & UX** | 15 | 140 | 510 h | 62.0% | **47.8%** |

* **Anotação Interpretativa:** Observa-se uma assimetria severa: os alunos entram em massa nos conteúdos mais técnicos (IA e Ciência de Dados), mas desistem no meio da jornada.

---

### Visualização 2: Dispersão e Matriz de Conteúdos que Merecem Atenção
* **Tipo:** Tabela de Dispersão / Quadrante Crítico com Ranking de Severidade.
* **Fonte de Dados:** `gold.vw_conteudos_atencao` e consulta do SQL Lab `ds_virtual_desempenho_engajamento_conteudos`.
* **Título Informativo:** *"Gargalo Focado: 5 títulos concentram mais de 35% de todo o abandono da plataforma."*

| ID Conteúdo | Título do Material | Categoria | Nível | Interações | Média Conclusão | Diferença p/ Média Geral | Status Diagnóstico |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **104** | *Deep Learning Prático com PyTorch* | IA | Avançado | 78 | 19.4% | **-28.8%** | Crítico: Alta Atração / Abandono Severo |
| **208** | *Pipelines Escaláveis com Apache Beam*| Dados | Avançado | 64 | 22.1% | **-26.1%** | Crítico: Barreira Cognitiva / Teoria densa |
| **115** | *Estatística Aplicada a Machine Learning*| Dados | Intermediário| 59 | 26.5% | **-21.7%** | Crítico: Gap de Pré-requisito Matemático |
| **302** | *Microsserviços com Docker e K8s* | Software | Intermediário| 51 | 29.0% | **-19.2%** | Crítico: Complexidade do Ambiente Local |
| **122** | *Modelagem Matemática de Redes Neurais*| IA | Avançado | 45 | 18.2% | **-30.0%** | Crítico: Formato estático sem labs guiados |

* **Anotação Interpretativa:** Estes conteúdos são chamarizes de novos alunos (alto clique e alto tempo inicial), porém a falta de suporte prático leva à frustração e abandono.

---

### Visualização 3: Eficiência Temporal e Conversão de Recomendações
* **Tipo:** Gráfico de Linhas Temporais com Faixas de Sazonalidade.
* **Fonte de Dados:** `gold.engajamento_conteudo_mensal` e dados de conversão de recomendações.
* **Título Informativo:** *"A recomendação dirigida de conteúdos preparatórios eleva a taxa de conclusão de cursos avançados de 21% para 46%."*

* **Comportamento Observado ao Longo dos Meses:**
  * Quando o aluno consome diretamente um curso avançado sem mediação pedagógica: taxa de conclusão de **21.8%**.
  * Quando o aluno recebe e aceita a recomendação do motor de um módulo nivelador ou artigo introdutório antes do curso avançado: taxa de conclusão sobe para **46.3%** (+112% de ganho relativo).

---

## 4. Descobertas e Insights Analíticos

1. **Ilusão de Engajamento por Visualizações:**  
   Métricas brutas de vaidade (como número de acessos ou cliques) mascaravam o problema real da instituição. O curso com maior número de interações na plataforma era justamente aquele com o segundo pior índice de conclusão.
2. **O Ponto de Ruptura (Drop-off Point):**  
   Ao analisar a `media_percentual_conclusao`, identificou-se que o abandono nos cursos de IA e Dados ocorre massivamente entre **25% e 40% do progresso**, momento em que as aulas deixam a teoria conceitual e exigem configuração de ambientes e codificação complexa.
3. **Poder das Recomendações de Nivelamento:**  
   Alunos que passaram por trilhas recomendadas com materiais preparatórios apresentaram tempo total de tela 35% mais longo e taxa de conclusão duas vezes maior.

---

## 5. Matriz de Fatos, Hipóteses e Recomendações

Para assegurar uma postura analítica madura e fundamentada, distinguimos com precisão o que foi comprovado por dados, o que constitui hipótese e o que é decisão sugerida:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              MATRIZ ANALÍTICA DECISÓRIA                                │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│     FATOS OBSERVADOS     │          HIPÓTESES          │     AÇÕES RECOMENDADAS        │
│   (Evidências na Gold)   │    (Causas Prováveis)       │       (Plano Tático)          │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 1. As categorias de IA e │ - Falta de pré-requisitos   │ 1. Reestruturação Pedagógica: │
│ Dados concentram 62% do  │   nivelados antes do início │    Incluir laboratórios de    │
│ tráfego, mas têm apenas  │   das aulas práticas.       │    código prontos no browser  │
│ 23% de conclusão média.  │ - Dificuldade de instalar e │    para os 5 conteúdos mais   │
│                          │   configurar ferramentas    │    críticos (ID 104, 208, 115,│
│                          │   locais nos computadores.  │    302 e 122).                │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 2. O abandono ocorre     │ - Transição muito brusca    │ 2. Ajuste do Motor de         │
│ entre 25% e 40% da carga │   entre conceitos teóricos  │    Recomendação:              │
│ horária dos cursos.      │   e exercícios complexos.   │    Disparar sugestão de curso │
│                          │                             │    nivelador sempre que o     │
│                          │                             │    aluno demonstrar estagnação│
│                          │                             │    no módulo introdutório.    │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 3. Alunos recomendados a │ - Trilhas guiadas conferem  │ 3. Alerta Automatizado:       │
│ conteúdos niveladores    │   maior segurança e reduzem │    Configurar no Superset     │
│ completam 112% mais.     │   a sobrecarga cognitiva.   │    disparo semanal quando a   │
│                          │                             │    taxa de conclusão de um    │
│                          │                             │    curso cair abaixo de 25%.  │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## 6. Ação Recomendada para a Diretoria Executiva

1. **Imediato (Semana 1):**  
   Ativar no Apache Superset o alerta semanal monitorando a view `gold.vw_conteudos_atencao`. Qualquer conteúdo com mais de 30 interações e conclusão inferior a 25% acionará a coordenação pedagógica.
2. **Curto Prazo (Mês 1):**  
   Intervenção nos 5 cursos mais críticos identificados no SQL Lab, gravando vídeos curtos de tira-dúvidas e fornecendo notebooks interativos pré-configurados.
3. **Médio Prazo (Trimestre 1):**  
   Incorporar no pipeline em lote o recálculo diário das recomendações baseado nos embeddings semânticos do Desafio 1, guiando os alunos em trilhas adaptativas.
