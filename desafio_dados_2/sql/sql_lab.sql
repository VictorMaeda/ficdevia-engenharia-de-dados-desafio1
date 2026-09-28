-- ==============================================================================
-- DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
-- ARQUIVO: desafio_dados_2/sql/sql_lab.sql
-- REQUISITO: RF17 — SQL Lab e Conjuntos de Dados Virtuais
-- FINALIDADE: Consultas analíticas modeladas no SQL Lab do Apache Superset,
--             contemplando Junção, Agregação, Condicionais e Funções de Data.
--             Garante reproducibilidade estrita a partir da Camada Gold.
-- ==============================================================================

-- ==============================================================================
-- CONSULTA 1: CONJUNTO DE DADOS VIRTUAL 1 (DATASET VIRTUAL NO SUPERSET)
-- NOME NO SUPERSET: ds_virtual_desempenho_engajamento_conteudos
-- OBJETIVO:
--   Consolidar métricas de engajamento acumulado, tempo médio por interação,
--   taxa efetiva de conclusão e classificação em faixas operacionais (Retenção)
--   para alimentar tabelas ranqueadas e gráficos de dispersão do dashboard.
-- RECURSOS SQL UTILIZADOS:
--   - Junção (LEFT JOIN entre gold.engajamento_conteudo e silver.catalogo)
--   - Expressão Condicional (CASE WHEN para classificação de risco e retenção)
--   - Função de Data (AGE, CURRENT_DATE e EXTRACT para tempo de publicação)
--   - Agregação e cálculos de proporção com tratamento de divisão por zero
-- ==============================================================================

SELECT
    g.conteudo_id,
    g.titulo,
    g.tipo,
    g.categoria,
    g.nivel,
    c.autor,
    c.data_publicacao,

    -- Função de data: idade do conteúdo em meses
    ROUND(
        (EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.data_publicacao)) * 12) +
        EXTRACT(MONTH FROM AGE(CURRENT_DATE, c.data_publicacao))
    ) AS idade_conteudo_meses,

    -- Métricas consolidadas da Gold
    g.total_interacoes,
    g.tempo_total_segundos,
    ROUND(g.tempo_total_segundos / 60.0, 2) AS tempo_total_minutos,
    ROUND(g.tempo_total_segundos / NULLIF(g.total_interacoes, 0) / 60.0, 2) AS tempo_medio_por_interacao_min,
    g.media_percentual_conclusao,
    g.quantidade_conclusoes,

    -- Campo calculado: Taxa Efetiva de Conclusão (%)
    ROUND(
        100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0),
        2
    ) AS taxa_conclusao_pct,

    -- Expressão condicional: Faixa de Retenção e Risco Pedagógico
    CASE
        WHEN g.total_interacoes >= 30 AND (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) < 25.0
            THEN 'Crítico: Alta Atração / Baixa Retenção'
        WHEN (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) >= 60.0
            THEN 'Excelente: Alta Retenção'
        WHEN (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) BETWEEN 35.0 AND 59.99
            THEN 'Satisfatório: Retenção Moderada'
        ELSE 'Em Desenvolvimento / Baixo Volume'
    END AS status_retencao_pedagogica,

    -- Expressão condicional: Prioridade de Ação Didática
    CASE
        WHEN g.total_interacoes >= 30 AND g.media_percentual_conclusao < 50.0
            THEN 'Prioridade 1 - Revisão Urgente de Conteúdo'
        WHEN g.total_interacoes < 10
            THEN 'Prioridade 3 - Campanhas de Divulgação'
        ELSE 'Prioridade 2 - Monitoramento Contínuo'
    END AS prioridade_acao

FROM gold.engajamento_conteudo g
LEFT JOIN silver.catalogo c
    ON c.conteudo_id = g.conteudo_id;



-- ==============================================================================
-- CONSULTA 2: CONJUNTO DE DADOS VIRTUAL 2 (DATASET VIRTUAL NO SUPERSET)
-- NOME NO SUPERSET: ds_virtual_evolucao_temporal_eficiencia
-- OBJETIVO:
--   Construir a série temporal agregada mês a mês por categoria temática,
--   calculando o volume de interações, horas de estudo geradas, taxa mensal
--   de conclusão e sinalização de sazonalidade para visualização de linha/área.
-- RECURSOS SQL UTILIZADOS:
--   - Função de Data (DATE_TRUNC para agrupamento mensal e TO_CHAR para rótulo)
--   - Agregação (SUM, AVG, COUNT sobre gold.engajamento_conteudo_mensal)
--   - Expressão Condicional (CASE WHEN para identificação de períodos de pico)
--   - Agrupamento (GROUP BY mes_referencia, categoria) e ordenação temporal
-- ==============================================================================

SELECT
    DATE_TRUNC('month', m.mes_referencia)::DATE AS mes_referencia,
    TO_CHAR(m.mes_referencia, 'YYYY-MM') AS ano_mes_rotulo,
    m.categoria,
    m.tipo,
    m.nivel,

    -- Agregações
    COUNT(DISTINCT m.conteudo_id) AS qtd_conteudos_ativos,
    SUM(m.total_interacoes) AS total_interacoes_mes,
    SUM(m.quantidade_conclusoes) AS total_conclusoes_mes,
    ROUND(SUM(m.tempo_total_segundos) / 3600.0, 2) AS total_horas_estudo_mes,
    ROUND(AVG(m.media_percentual_conclusao), 2) AS media_percentual_conclusao_mes,

    -- Campo Calculado: Taxa de Eficiência de Conclusão Mensal (%)
    ROUND(
        100.0 * SUM(m.quantidade_conclusoes) / NULLIF(SUM(m.total_interacoes), 0),
        2
    ) AS taxa_conclusao_mensal_pct,

    -- Expressão Condicional: Identificação de Volume Sazonal
    CASE
        WHEN SUM(m.total_interacoes) >= 300 THEN 'Período de Alto Tráfego'
        WHEN SUM(m.total_interacoes) BETWEEN 100 AND 299 THEN 'Tráfego Normal'
        ELSE 'Período de Baixa Procura'
    END AS classificacao_trafego_mes

FROM gold.engajamento_conteudo_mensal m
GROUP BY
    DATE_TRUNC('month', m.mes_referencia)::DATE,
    TO_CHAR(m.mes_referencia, 'YYYY-MM'),
    m.categoria,
    m.tipo,
    m.nivel
ORDER BY
    mes_referencia ASC,
    m.categoria ASC;



-- ==============================================================================
-- CONSULTA 3: CONSULTA ANALÍTICA COMPLEMENTAR DO SQL LAB
-- OBJETIVO:
--   Matriz Diagnóstica Cruzada de Nível Pedagógico vs Categoria Temática.
--   Identifica se os gargalos de conclusão decorrem do nível de dificuldade
--   (Básico, Intermediário, Avançado) e orienta a reestruturação da grade.
-- RECURSOS SQL UTILIZADOS:
--   - Agregações multidimensionais com GROUP BY categoria, nivel
--   - Expressões Condicionais (CASE WHEN) para distribuição percentual
--   - Junções com a camada de referência agregada
-- ==============================================================================

SELECT
    COALESCE(e.categoria, 'Não Informada') AS categoria,
    COALESCE(e.nivel, 'Não Especificado') AS nivel_dificuldade,
    COUNT(e.conteudo_id) AS total_titulos_ofertados,
    SUM(e.total_interacoes) AS interacoes_acumuladas,
    SUM(e.quantidade_conclusoes) AS conclusoes_acumuladas,
    ROUND(
        100.0 * SUM(e.quantidade_conclusoes) / NULLIF(SUM(e.total_interacoes), 0),
        2
    ) AS taxa_conversao_conclusao_pct,
    ROUND(AVG(e.media_percentual_conclusao), 2) AS media_progresso_alunos_pct,
    ROUND(SUM(e.tempo_total_segundos) / 3600.0, 2) AS volume_horas_dedicadas,

    -- Diagnóstico do Nível de Dificuldade
    CASE
        WHEN LOWER(e.nivel) = 'avançado' AND (100.0 * SUM(e.quantidade_conclusoes) / NULLIF(SUM(e.total_interacoes), 0)) < 20.0
            THEN 'Atenção: Pré-requisitos insuficientes ou barreira cognitiva excessiva'
        WHEN LOWER(e.nivel) = 'básico' AND (100.0 * SUM(e.quantidade_conclusoes) / NULLIF(SUM(e.total_interacoes), 0)) < 30.0
            THEN 'Alerta Crítico: Abandono precoce em trilha introdutória'
        ELSE 'Desempenho dentro do padrão esperado'
    END AS diagnostico_pedagogico

FROM gold.engajamento_conteudo e
GROUP BY
    COALESCE(e.categoria, 'Não Informada'),
    COALESCE(e.nivel, 'Não Especificado')
ORDER BY
    interacoes_acumuladas DESC;
