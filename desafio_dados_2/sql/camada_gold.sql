-- ==============================================================================
-- DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
-- ARQUIVO: desafio_dados_2/sql/camada_gold.sql
-- REQUISITOS: RF17, RF26
-- FINALIDADE: Definicao DDL e visões analiticas da Camada Gold para consumo
--             no SQL Lab e Apache Superset.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- ------------------------------------------------------------------------------
-- 1. TABELA CONSOLIDADA: gold.engajamento_conteudo
-- Granularidade: 1 linha por conteudo_id
-- Origem: Agregacao Apache Beam sobre silver.interacoes enriquecida com silver.catalogo
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.engajamento_conteudo (
    conteudo_id INT4 NOT NULL,
    titulo TEXT NOT NULL,
    tipo TEXT NULL,
    categoria TEXT NULL,
    nivel TEXT NULL,
    total_interacoes INT8 NOT NULL,
    tempo_total_segundos INT8 NOT NULL,
    media_percentual_conclusao NUMERIC(7, 2) NULL,
    quantidade_conclusoes INT8 NOT NULL,
    data_carga TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT engajamento_conteudo_pkey PRIMARY KEY (conteudo_id)
);

COMMENT ON TABLE gold.engajamento_conteudo IS 'Consolidado analítico de engajamento acumulado por conteúdo educacional';
COMMENT ON COLUMN gold.engajamento_conteudo.conteudo_id IS 'Identificador mestre do conteúdo';
COMMENT ON COLUMN gold.engajamento_conteudo.total_interacoes IS 'Volume total de eventos de consumo registrados';
COMMENT ON COLUMN gold.engajamento_conteudo.tempo_total_segundos IS 'Tempo acumulado de visualização/interação em segundos';
COMMENT ON COLUMN gold.engajamento_conteudo.media_percentual_conclusao IS 'Média percentual de conclusão das sessões do conteúdo';
COMMENT ON COLUMN gold.engajamento_conteudo.quantidade_conclusoes IS 'Número de sessões concluídas integralmente (100%)';


-- ------------------------------------------------------------------------------
-- 2. TABELA TEMPORAL: gold.engajamento_conteudo_mensal
-- Granularidade: 1 linha por mes_referencia e conteudo_id
-- Objetivo: Analise de series temporais, sazonalidade e evolucao no Superset
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.engajamento_conteudo_mensal (
    mes_referencia DATE NOT NULL,
    conteudo_id INT4 NOT NULL,
    titulo TEXT NOT NULL,
    tipo TEXT NULL,
    categoria TEXT NULL,
    nivel TEXT NULL,
    total_interacoes INT8 NOT NULL,
    tempo_total_segundos INT8 NOT NULL,
    media_percentual_conclusao NUMERIC(7, 2) NULL,
    quantidade_conclusoes INT8 NOT NULL,
    data_carga TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT engajamento_conteudo_mensal_pkey PRIMARY KEY (mes_referencia, conteudo_id)
);

COMMENT ON TABLE gold.engajamento_conteudo_mensal IS 'Série temporal mensal de consumo e engajamento por conteúdo';


-- ------------------------------------------------------------------------------
-- 3. VISAO ANALITICA: gold.vw_resumo_categoria
-- Pergunta de Negocio: Quais categorias concentram maior engajamento e conclusão?
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.vw_resumo_categoria AS
SELECT
    categoria,
    COUNT(*) AS total_conteudos,
    SUM(total_interacoes) AS total_interacoes,
    SUM(tempo_total_segundos) AS tempo_total_segundos,
    ROUND(AVG(media_percentual_conclusao), 2) AS media_percentual_conclusao,
    SUM(quantidade_conclusoes) AS quantidade_conclusoes,
    ROUND(
        100.0 * SUM(quantidade_conclusoes) / NULLIF(SUM(total_interacoes), 0),
        2
    ) AS taxa_conclusao_geral
FROM gold.engajamento_conteudo
GROUP BY categoria;

COMMENT ON VIEW gold.vw_resumo_categoria IS 'Visão agregada por categoria temática de conteúdo educacional';


-- ------------------------------------------------------------------------------
-- 4. VISAO ANALITICA: gold.vw_ranking_engajamento
-- Pergunta de Negocio: Ranking geral de conteudos por volume de interacao
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.vw_ranking_engajamento AS
SELECT
    conteudo_id,
    titulo,
    tipo,
    categoria,
    nivel,
    total_interacoes,
    tempo_total_segundos,
    media_percentual_conclusao,
    quantidade_conclusoes,
    ROUND(
        100.0 * quantidade_conclusoes / NULLIF(total_interacoes, 0),
        2
    ) AS taxa_conclusao,
    RANK() OVER (ORDER BY total_interacoes DESC) AS ranking_interacoes,
    DENSE_RANK() OVER (ORDER BY tempo_total_segundos DESC) AS ranking_tempo_consumido
FROM gold.engajamento_conteudo;

COMMENT ON VIEW gold.vw_ranking_engajamento IS 'Classificação ordinal de conteúdos por interações e tempo total';


-- ------------------------------------------------------------------------------
-- 5. VISAO ANALITICA: gold.vw_conteudos_atencao
-- Pergunta de Negocio: Quais conteudos atraem muitos cliques mas retem pouco?
-- Criterio: Interacoes >= media_geral AND conclusao < media_geral
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.vw_conteudos_atencao AS
WITH referencia AS (
    SELECT
        AVG(total_interacoes)::NUMERIC AS media_interacoes_geral,
        AVG(media_percentual_conclusao)::NUMERIC AS media_conclusao_geral
    FROM gold.engajamento_conteudo
    WHERE media_percentual_conclusao IS NOT NULL
)
SELECT
    e.conteudo_id,
    e.titulo,
    e.tipo,
    e.categoria,
    e.nivel,
    e.total_interacoes,
    e.tempo_total_segundos,
    e.media_percentual_conclusao,
    e.quantidade_conclusoes,
    ROUND(
        100.0 * e.quantidade_conclusoes / NULLIF(e.total_interacoes, 0),
        2
    ) AS taxa_conclusao_interacoes,
    ROUND(r.media_interacoes_geral, 2) AS media_interacoes_geral,
    ROUND(r.media_conclusao_geral, 2) AS media_conclusao_geral,
    ROUND(e.total_interacoes - r.media_interacoes_geral, 2) AS diferenca_interacoes_media,
    ROUND(e.media_percentual_conclusao - r.media_conclusao_geral, 2) AS diferenca_conclusao_media
FROM gold.engajamento_conteudo e
CROSS JOIN referencia r
WHERE e.total_interacoes >= r.media_interacoes_geral
  AND e.media_percentual_conclusao < r.media_conclusao_geral;

COMMENT ON VIEW gold.vw_conteudos_atencao IS 'Conteúdos com alta atração e baixo aproveitamento/conclusão (críticos para pedagogia)';
