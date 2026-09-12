-- ============================================================
-- Consultas de apoio - RF06 (permitir consultar os registros armazenados)
-- ============================================================

-- Quantidade de registros por tabela
SELECT 'usuarios' AS tabela, COUNT(*) FROM usuarios
UNION ALL
SELECT 'conteudos', COUNT(*) FROM conteudos
UNION ALL
SELECT 'categorias', COUNT(*) FROM categorias
UNION ALL
SELECT 'interacoes', COUNT(*) FROM interacoes
UNION ALL
SELECT 'avaliacoes_resumo', COUNT(*) FROM avaliacoes_resumo
UNION ALL
SELECT 'recomendacoes', COUNT(*) FROM recomendacoes;

-- Conteúdos por categoria
SELECT c.nome AS categoria, COUNT(*) AS quantidade_conteudos
FROM conteudos co
JOIN categorias c ON c.categoria_id = co.categoria_id
GROUP BY c.nome
ORDER BY quantidade_conteudos DESC;

-- Interações por tipo
SELECT tipo_interacao, COUNT(*) AS quantidade
FROM interacoes
GROUP BY tipo_interacao
ORDER BY quantidade DESC;

-- Avaliação média por conteúdo (top 10)
SELECT co.conteudo_id, co.titulo, ROUND(AVG(a.nota), 2) AS avaliacao_media, COUNT(*) AS qtd_avaliacoes
FROM avaliacoes_resumo a
JOIN conteudos co ON co.conteudo_id = a.conteudo_id
GROUP BY co.conteudo_id, co.titulo
ORDER BY avaliacao_media DESC, qtd_avaliacoes DESC
LIMIT 10;

-- Usuários mais ativos (por quantidade de interações)
SELECT usuario_id, COUNT(*) AS quantidade_interacoes
FROM interacoes
GROUP BY usuario_id
ORDER BY quantidade_interacoes DESC
LIMIT 10;

-- Taxa de conclusão por conteúdo
SELECT co.conteudo_id, co.titulo,
       COUNT(*) FILTER (WHERE i.tipo_interacao = 'conclusao') AS concluidos,
       COUNT(DISTINCT i.usuario_id) AS usuarios_unicos,
       ROUND(
           COUNT(*) FILTER (WHERE i.tipo_interacao = 'conclusao')::NUMERIC
           / NULLIF(COUNT(DISTINCT i.usuario_id), 0) * 100, 2
       ) AS taxa_conclusao_pct
FROM interacoes i
JOIN conteudos co ON co.conteudo_id = i.conteudo_id
GROUP BY co.conteudo_id, co.titulo
ORDER BY taxa_conclusao_pct DESC NULLS LAST
LIMIT 10;
