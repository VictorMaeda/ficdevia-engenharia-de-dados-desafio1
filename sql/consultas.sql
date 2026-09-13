-- ============================================================
-- CONSULTAS DE APOIO E ANALÍTICAS
-- Pipeline de Recomendação e Dashboard de Conteúdos Educacionais
-- ============================================================


-- ============================================================
-- 1. CONSULTAS DE APOIO - RF06
-- Permitir consultar os registros armazenados
-- ============================================================


-- ------------------------------------------------------------
-- 1.1 Quantidade de registros por tabela
-- ------------------------------------------------------------

SELECT 'usuarios' AS tabela, COUNT(*) AS quantidade
FROM usuarios

UNION ALL

SELECT 'conteudos', COUNT(*)
FROM conteudos

UNION ALL

SELECT 'categorias', COUNT(*)
FROM categorias

UNION ALL

SELECT 'interacoes', COUNT(*)
FROM interacoes

UNION ALL

SELECT 'avaliacoes_resumo', COUNT(*)
FROM avaliacoes_resumo

UNION ALL

SELECT 'recomendacoes', COUNT(*)
FROM recomendacoes;


-- ------------------------------------------------------------
-- 1.2 Conteúdos por categoria
-- ------------------------------------------------------------

SELECT
    c.nome AS categoria,
    COUNT(*) AS quantidade_conteudos
FROM conteudos co
JOIN categorias c
    ON c.categoria_id = co.categoria_id
GROUP BY c.nome
ORDER BY quantidade_conteudos DESC;


-- ------------------------------------------------------------
-- 1.3 Conteúdos por tipo
-- ------------------------------------------------------------

SELECT
    tipo,
    COUNT(*) AS quantidade
FROM conteudos
GROUP BY tipo
ORDER BY quantidade DESC;


-- ------------------------------------------------------------
-- 1.4 Conteúdos por nível
-- ------------------------------------------------------------

SELECT
    nivel,
    COUNT(*) AS quantidade
FROM conteudos
GROUP BY nivel
ORDER BY quantidade DESC;


-- ------------------------------------------------------------
-- 1.5 Interações por tipo
-- ------------------------------------------------------------

SELECT
    tipo_interacao,
    COUNT(*) AS quantidade
FROM interacoes
GROUP BY tipo_interacao
ORDER BY quantidade DESC;


-- ------------------------------------------------------------
-- 1.6 Avaliação média por conteúdo - Top 10
-- ------------------------------------------------------------

SELECT
    co.conteudo_id,
    co.titulo,
    ROUND(AVG(a.nota), 2) AS avaliacao_media,
    COUNT(*) AS quantidade_avaliacoes
FROM avaliacoes_resumo a
JOIN conteudos co
    ON co.conteudo_id = a.conteudo_id
GROUP BY
    co.conteudo_id,
    co.titulo
ORDER BY
    avaliacao_media DESC,
    quantidade_avaliacoes DESC
LIMIT 10;


-- ------------------------------------------------------------
-- 1.7 Usuários mais ativos - Top 10
-- ------------------------------------------------------------

SELECT
    usuario_id,
    COUNT(*) AS quantidade_interacoes
FROM interacoes
GROUP BY usuario_id
ORDER BY quantidade_interacoes DESC
LIMIT 10;


-- ============================================================
-- 2. MÉTRICAS OPERACIONAIS - RF12
-- ============================================================


-- ------------------------------------------------------------
-- 2.1 Total de usuários
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_usuarios
FROM usuarios;


-- ------------------------------------------------------------
-- 2.2 Total de interações
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_interacoes
FROM interacoes;


-- ------------------------------------------------------------
-- 2.3 Total de conteúdos
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_conteudos
FROM conteudos;


-- ------------------------------------------------------------
-- 2.4 Conteúdos que possuem pelo menos uma interação
-- ------------------------------------------------------------

SELECT
    COUNT(DISTINCT conteudo_id) AS conteudos_com_interacao
FROM interacoes;


-- ------------------------------------------------------------
-- 2.5 Total de avaliações
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_avaliacoes
FROM avaliacoes_resumo;


-- ------------------------------------------------------------
-- 2.6 Total de recomendações
-- O valor permanecerá zero até a execução do motor de
-- recomendação.
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_recomendacoes
FROM recomendacoes;


-- ============================================================
-- 3. KPIs - RF12
-- ============================================================


-- ------------------------------------------------------------
-- 3.1 KPI - Taxa global de conclusão
--
-- Considera pares distintos usuario/conteudo para impedir que
-- múltiplas interações do mesmo usuário com o mesmo conteúdo
-- provoquem duplicidade no indicador.
-- ------------------------------------------------------------

SELECT
    COUNT(
        DISTINCT (usuario_id, conteudo_id)
    ) AS pares_com_interacao,

    COUNT(
        DISTINCT (usuario_id, conteudo_id)
    ) FILTER (
        WHERE percentual_conclusao = 100
    ) AS pares_concluidos,

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
    ) AS taxa_conclusao_pct

FROM interacoes;


-- ------------------------------------------------------------
-- 3.2 KPI - Avaliação média
-- ------------------------------------------------------------

SELECT
    ROUND(AVG(nota), 2) AS avaliacao_media,
    COUNT(*) AS total_avaliacoes
FROM avaliacoes_resumo;


-- ------------------------------------------------------------
-- 3.3 KPI complementar - Taxa de avaliações positivas
--
-- São consideradas positivas as avaliações com nota >= 4.
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_avaliacoes,

    COUNT(*) FILTER (
        WHERE nota >= 4
    ) AS avaliacoes_positivas,

    ROUND(
        COUNT(*) FILTER (
            WHERE nota >= 4
        )::NUMERIC
        /
        NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS taxa_avaliacoes_positivas_pct

FROM avaliacoes_resumo;


-- ============================================================
-- 4. CONSULTAS ANALÍTICAS PARA O DASHBOARD
-- ============================================================


-- ------------------------------------------------------------
-- 4.1 Interações por categoria
--
-- Utilizada para analisar o volume de atividade dos usuários
-- em cada categoria de conteúdo.
-- ------------------------------------------------------------

SELECT
    ca.categoria_id,
    ca.nome AS categoria,
    COUNT(i.interacao_id) AS total_interacoes,
    COUNT(DISTINCT i.usuario_id) AS usuarios_distintos,
    COUNT(DISTINCT i.conteudo_id) AS conteudos_com_interacao
FROM categorias ca
JOIN conteudos co
    ON co.categoria_id = ca.categoria_id
LEFT JOIN interacoes i
    ON i.conteudo_id = co.conteudo_id
GROUP BY
    ca.categoria_id,
    ca.nome
ORDER BY total_interacoes DESC;


-- ------------------------------------------------------------
-- 4.2 Interações por tipo de conteúdo
-- ------------------------------------------------------------

SELECT
    co.tipo,
    COUNT(i.interacao_id) AS total_interacoes,
    COUNT(DISTINCT i.usuario_id) AS usuarios_distintos,
    COUNT(DISTINCT i.conteudo_id) AS conteudos_com_interacao
FROM conteudos co
LEFT JOIN interacoes i
    ON i.conteudo_id = co.conteudo_id
GROUP BY co.tipo
ORDER BY total_interacoes DESC;


-- ------------------------------------------------------------
-- 4.3 Interações por nível de conteúdo
-- ------------------------------------------------------------

SELECT
    co.nivel,
    COUNT(i.interacao_id) AS total_interacoes,
    COUNT(DISTINCT i.usuario_id) AS usuarios_distintos,
    COUNT(DISTINCT i.conteudo_id) AS conteudos_com_interacao
FROM conteudos co
LEFT JOIN interacoes i
    ON i.conteudo_id = co.conteudo_id
GROUP BY co.nivel
ORDER BY total_interacoes DESC;


-- ------------------------------------------------------------
-- 4.4 Evolução diária das interações
-- ------------------------------------------------------------

SELECT
    DATE(data_hora) AS data,
    COUNT(*) AS total_interacoes,
    COUNT(DISTINCT usuario_id) AS usuarios_distintos
FROM interacoes
GROUP BY DATE(data_hora)
ORDER BY data;


-- ------------------------------------------------------------
-- 4.5 Evolução mensal das interações
-- ------------------------------------------------------------

SELECT
    DATE_TRUNC('month', data_hora)::DATE AS mes,
    COUNT(*) AS total_interacoes,
    COUNT(DISTINCT usuario_id) AS usuarios_distintos
FROM interacoes
GROUP BY DATE_TRUNC('month', data_hora)
ORDER BY mes;


-- ------------------------------------------------------------
-- 4.6 Taxa de conclusão por categoria
-- ------------------------------------------------------------

SELECT
    ca.categoria_id,
    ca.nome AS categoria,

    COUNT(
        DISTINCT (i.usuario_id, i.conteudo_id)
    ) AS pares_com_interacao,

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

FROM categorias ca
JOIN conteudos co
    ON co.categoria_id = ca.categoria_id
JOIN interacoes i
    ON i.conteudo_id = co.conteudo_id
GROUP BY
    ca.categoria_id,
    ca.nome
ORDER BY taxa_conclusao_pct DESC;


-- ------------------------------------------------------------
-- 4.7 Taxa de conclusão por tipo de conteúdo
-- ------------------------------------------------------------

SELECT
    co.tipo,

    COUNT(
        DISTINCT (i.usuario_id, i.conteudo_id)
    ) AS pares_com_interacao,

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

FROM conteudos co
JOIN interacoes i
    ON i.conteudo_id = co.conteudo_id
GROUP BY co.tipo
ORDER BY taxa_conclusao_pct DESC;


-- ------------------------------------------------------------
-- 4.8 Avaliação média por categoria
-- ------------------------------------------------------------

SELECT
    ca.categoria_id,
    ca.nome AS categoria,
    ROUND(AVG(a.nota), 2) AS avaliacao_media,
    COUNT(*) AS total_avaliacoes
FROM avaliacoes_resumo a
JOIN conteudos co
    ON co.conteudo_id = a.conteudo_id
JOIN categorias ca
    ON ca.categoria_id = co.categoria_id
GROUP BY
    ca.categoria_id,
    ca.nome
ORDER BY avaliacao_media DESC;


-- ------------------------------------------------------------
-- 4.9 Taxa de avaliações positivas por categoria
-- ------------------------------------------------------------

SELECT
    ca.categoria_id,
    ca.nome AS categoria,

    COUNT(*) AS total_avaliacoes,

    COUNT(*) FILTER (
        WHERE a.nota >= 4
    ) AS avaliacoes_positivas,

    ROUND(
        COUNT(*) FILTER (
            WHERE a.nota >= 4
        )::NUMERIC
        /
        NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS taxa_avaliacoes_positivas_pct

FROM avaliacoes_resumo a
JOIN conteudos co
    ON co.conteudo_id = a.conteudo_id
JOIN categorias ca
    ON ca.categoria_id = co.categoria_id
GROUP BY
    ca.categoria_id,
    ca.nome
ORDER BY taxa_avaliacoes_positivas_pct DESC;


-- ------------------------------------------------------------
-- 4.10 Taxa de conclusão por conteúdo - Top 10
--
-- Versão revisada da consulta originalmente presente neste
-- arquivo, utilizando pares distintos usuário/conteúdo.
-- ------------------------------------------------------------

SELECT
    co.conteudo_id,
    co.titulo,

    COUNT(
        DISTINCT (i.usuario_id, i.conteudo_id)
    ) AS pares_com_interacao,

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
GROUP BY
    co.conteudo_id,
    co.titulo
ORDER BY
    taxa_conclusao_pct DESC,
    pares_com_interacao DESC
LIMIT 10;


-- ============================================================
-- 5. CONSULTAS DE APOIO PARA RECOMENDAÇÕES
--
-- Serão úteis após a execução da etapa de recomendação.
-- Enquanto a tabela estiver vazia, as consultas retornarão
-- zero registros ou valores nulos.
-- ============================================================


-- ------------------------------------------------------------
-- 5.1 Total de recomendações
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_recomendacoes
FROM recomendacoes;


-- ------------------------------------------------------------
-- 5.2 Distribuição das recomendações por status
-- ------------------------------------------------------------

SELECT
    status,
    COUNT(*) AS quantidade
FROM recomendacoes
GROUP BY status
ORDER BY quantidade DESC;


-- ------------------------------------------------------------
-- 5.3 Pontuação média das recomendações
-- ------------------------------------------------------------

SELECT
    ROUND(AVG(pontuacao), 2) AS pontuacao_media,
    COUNT(*) AS total_recomendacoes
FROM recomendacoes;


-- ------------------------------------------------------------
-- 5.4 Recomendações por categoria
-- ------------------------------------------------------------

SELECT
    ca.nome AS categoria,
    COUNT(*) AS total_recomendacoes,
    ROUND(AVG(r.pontuacao), 2) AS pontuacao_media
FROM recomendacoes r
JOIN conteudos co
    ON co.conteudo_id = r.conteudo_id
JOIN categorias ca
    ON ca.categoria_id = co.categoria_id
GROUP BY ca.nome
ORDER BY total_recomendacoes DESC;