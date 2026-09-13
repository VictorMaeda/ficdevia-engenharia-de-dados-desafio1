-- ============================================================
-- VIEWS ANALÍTICAS PARA O APACHE SUPERSET
-- Pipeline de Recomendação e Dashboard de Conteúdos Educacionais
--
-- Objetivo:
-- Disponibilizar conjuntos de dados preparados para criação
-- de métricas, KPIs, gráficos e filtros no Apache Superset.
-- ============================================================


-- ============================================================
-- 1. VIEW DE INTERAÇÕES
--
-- Uma linha por interação, enriquecida com os dados do
-- conteúdo e da categoria.
--
-- Será a principal fonte para:
-- - total de interações;
-- - usuários distintos;
-- - interações por categoria;
-- - interações por tipo;
-- - interações por nível;
-- - evolução temporal;
-- - análises de conclusão.
-- ============================================================

CREATE OR REPLACE VIEW vw_interacoes_dashboard AS
SELECT
    i.interacao_id,
    i.usuario_id,
    i.conteudo_id,

    -- Identificador auxiliar para o par usuário/conteúdo.
    -- Útil para contagens distintas no Superset.
    CONCAT(i.usuario_id, '-', i.conteudo_id) AS usuario_conteudo,

    co.titulo,
    co.tipo,
    co.nivel,
    co.carga_horaria_min,
    co.data_publicacao,

    ca.categoria_id,
    ca.nome AS categoria,

    i.tipo_interacao,
    i.data_hora,
    i.data_hora::DATE AS data_interacao,

    i.tempo_consumido_min,
    i.percentual_conclusao,
    i.avaliacao,

    CASE
        WHEN i.percentual_conclusao = 100 THEN 1
        ELSE 0
    END AS concluido

FROM interacoes i

JOIN conteudos co
    ON co.conteudo_id = i.conteudo_id

JOIN categorias ca
    ON ca.categoria_id = co.categoria_id;


-- ============================================================
-- 2. VIEW DE AVALIAÇÕES
--
-- Uma linha por avaliação, enriquecida com informações do
-- conteúdo.
--
-- Será utilizada principalmente para:
-- - avaliação média;
-- - avaliações por categoria;
-- - taxa de avaliações positivas;
-- - filtros por categoria, tipo e nível.
-- ============================================================

CREATE OR REPLACE VIEW vw_avaliacoes_dashboard AS
SELECT
    a.avaliacao_resumo_id,
    a.usuario_id,
    a.conteudo_id,

    co.titulo,
    co.tipo,
    co.nivel,

    ca.categoria_id,
    ca.nome AS categoria,

    a.nota,
    a.data_avaliacao,

    CASE
        WHEN a.nota >= 4 THEN 1
        ELSE 0
    END AS avaliacao_positiva

FROM avaliacoes_resumo a

JOIN conteudos co
    ON co.conteudo_id = a.conteudo_id

JOIN categorias ca
    ON ca.categoria_id = co.categoria_id;


-- ============================================================
-- 3. VIEW DE MÉTRICAS E KPIs GERAIS
--
-- Retorna uma única linha contendo os principais números
-- utilizados nos cartões do dashboard.
-- ============================================================

CREATE OR REPLACE VIEW vw_metricas_dashboard AS
SELECT

    -- --------------------------------------------------------
    -- Métricas operacionais
    -- --------------------------------------------------------

    (
        SELECT COUNT(*)
        FROM usuarios
    ) AS total_usuarios,

    (
        SELECT COUNT(*)
        FROM conteudos
    ) AS total_conteudos,

    (
        SELECT COUNT(*)
        FROM interacoes
    ) AS total_interacoes,

    (
        SELECT COUNT(DISTINCT conteudo_id)
        FROM interacoes
    ) AS conteudos_com_interacao,

    (
        SELECT COUNT(*)
        FROM avaliacoes_resumo
    ) AS total_avaliacoes,

    (
        SELECT COUNT(*)
        FROM recomendacoes
    ) AS total_recomendacoes,


    -- --------------------------------------------------------
    -- KPI: Taxa de conclusão
    -- --------------------------------------------------------

    (
        SELECT COUNT(
            DISTINCT (usuario_id, conteudo_id)
        )
        FROM interacoes
    ) AS pares_usuario_conteudo,

    (
        SELECT COUNT(
            DISTINCT (usuario_id, conteudo_id)
        )
        FROM interacoes
        WHERE percentual_conclusao = 100
    ) AS pares_concluidos,

    (
        SELECT
            ROUND(
                COUNT(
                    DISTINCT (usuario_id, conteudo_id)
                ) FILTER (
                    WHERE percentual_conclusao = 100
                )::NUMERIC
                /
                NULLIF(
                    COUNT(
                        DISTINCT (usuario_id, conteudo_id)
                    ),
                    0
                )
                * 100,
                2
            )
        FROM interacoes
    ) AS taxa_conclusao_pct,


    -- --------------------------------------------------------
    -- KPI: Avaliação média
    -- --------------------------------------------------------

    (
        SELECT ROUND(AVG(nota), 2)
        FROM avaliacoes_resumo
    ) AS avaliacao_media,


    -- --------------------------------------------------------
    -- KPI: Taxa de avaliações positivas
    -- --------------------------------------------------------

    (
        SELECT
            ROUND(
                COUNT(*) FILTER (
                    WHERE nota >= 4
                )::NUMERIC
                /
                NULLIF(COUNT(*), 0)
                * 100,
                2
            )
        FROM avaliacoes_resumo
    ) AS taxa_avaliacoes_positivas_pct;


-- ============================================================
-- 4. VIEW DE DESEMPENHO POR CATEGORIA
--
-- Reúne em uma única fonte os principais indicadores
-- analíticos de cada categoria.
--
-- As interações e avaliações são agregadas separadamente
-- antes da junção para evitar duplicação de registros.
-- ============================================================

CREATE OR REPLACE VIEW vw_desempenho_categoria AS

WITH conteudos_categoria AS (

    SELECT
        categoria_id,
        COUNT(*) AS total_conteudos
    FROM conteudos
    GROUP BY categoria_id

),

interacoes_categoria AS (

    SELECT
        co.categoria_id,

        COUNT(*) AS total_interacoes,

        COUNT(
            DISTINCT i.usuario_id
        ) AS usuarios_distintos,

        COUNT(
            DISTINCT i.conteudo_id
        ) AS conteudos_com_interacao,

        COUNT(
            DISTINCT (i.usuario_id, i.conteudo_id)
        ) AS pares_usuario_conteudo,

        COUNT(
            DISTINCT (i.usuario_id, i.conteudo_id)
        ) FILTER (
            WHERE i.percentual_conclusao = 100
        ) AS pares_concluidos,

        ROUND(
            COUNT(
                DISTINCT (i.usuario_id, i.conteudo_id)
            ) FILTER (
                WHERE i.percentual_conclusao = 100
            )::NUMERIC
            /
            NULLIF(
                COUNT(
                    DISTINCT (i.usuario_id, i.conteudo_id)
                ),
                0
            )
            * 100,
            2
        ) AS taxa_conclusao_pct

    FROM interacoes i

    JOIN conteudos co
        ON co.conteudo_id = i.conteudo_id

    GROUP BY co.categoria_id

),

avaliacoes_categoria AS (

    SELECT
        co.categoria_id,

        COUNT(*) AS total_avaliacoes,

        ROUND(
            AVG(a.nota),
            2
        ) AS avaliacao_media,

        COUNT(*) FILTER (
            WHERE a.nota >= 4
        ) AS avaliacoes_positivas,

        ROUND(
            COUNT(*) FILTER (
                WHERE a.nota >= 4
            )::NUMERIC
            /
            NULLIF(
                COUNT(*),
                0
            )
            * 100,
            2
        ) AS taxa_avaliacoes_positivas_pct

    FROM avaliacoes_resumo a

    JOIN conteudos co
        ON co.conteudo_id = a.conteudo_id

    GROUP BY co.categoria_id

)

SELECT
    ca.categoria_id,
    ca.nome AS categoria,

    COALESCE(
        cc.total_conteudos,
        0
    ) AS total_conteudos,

    COALESCE(
        ic.conteudos_com_interacao,
        0
    ) AS conteudos_com_interacao,

    COALESCE(
        ic.total_interacoes,
        0
    ) AS total_interacoes,

    COALESCE(
        ic.usuarios_distintos,
        0
    ) AS usuarios_distintos,

    COALESCE(
        ic.pares_usuario_conteudo,
        0
    ) AS pares_usuario_conteudo,

    COALESCE(
        ic.pares_concluidos,
        0
    ) AS pares_concluidos,

    COALESCE(
        ic.taxa_conclusao_pct,
        0
    ) AS taxa_conclusao_pct,

    COALESCE(
        ac.total_avaliacoes,
        0
    ) AS total_avaliacoes,

    ac.avaliacao_media,

    COALESCE(
        ac.avaliacoes_positivas,
        0
    ) AS avaliacoes_positivas,

    COALESCE(
        ac.taxa_avaliacoes_positivas_pct,
        0
    ) AS taxa_avaliacoes_positivas_pct

FROM categorias ca

LEFT JOIN conteudos_categoria cc
    ON cc.categoria_id = ca.categoria_id

LEFT JOIN interacoes_categoria ic
    ON ic.categoria_id = ca.categoria_id

LEFT JOIN avaliacoes_categoria ac
    ON ac.categoria_id = ca.categoria_id;


-- ============================================================
-- 5. VIEW DE RECOMENDAÇÕES
--
-- Preparada para receber os registros produzidos pelo motor
-- de recomendação do projeto.
--
-- Enquanto a tabela recomendacoes estiver vazia, esta view
-- também retornará zero registros.
-- ============================================================

CREATE OR REPLACE VIEW vw_recomendacoes_dashboard AS
SELECT
    r.recomendacao_id,
    r.usuario_id,
    r.conteudo_id,

    co.titulo,
    co.tipo,
    co.nivel,

    ca.categoria_id,
    ca.nome AS categoria,

    r.pontuacao,
    r.posicao,
    r.status,
    r.data_geracao

FROM recomendacoes r

JOIN conteudos co
    ON co.conteudo_id = r.conteudo_id

JOIN categorias ca
    ON ca.categoria_id = co.categoria_id;