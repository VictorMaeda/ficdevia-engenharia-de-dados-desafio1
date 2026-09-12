-- ============================================================
-- Desafio 1 - Fundamentos de Dados para IA
-- Script de criação do schema no PostgreSQL
--
-- Entidades mínimas exigidas: usuário, conteúdo, categoria,
-- interação, recomendação.
--
-- Observação sobre "usuarios": as fontes de dados fornecidas
-- (interacoes_usuarios.json e comentarios_avaliacoes.json) trazem
-- apenas o identificador do usuário, sem nome/e-mail cadastral.
-- Por isso a entidade "usuarios" é derivada (populada a partir dos
-- ids encontrados nas interações/comentários), guardando metadados
-- que podem ser calculados a partir dos próprios dados.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS categorias (
    categoria_id        SERIAL PRIMARY KEY,
    nome                 TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id           INTEGER PRIMARY KEY,
    primeira_ocorrencia   TIMESTAMP,
    origem_primeiro_registro TEXT
);

CREATE TABLE IF NOT EXISTS conteudos (
    conteudo_id           INTEGER PRIMARY KEY,
    titulo                 TEXT NOT NULL,
    tipo                    TEXT NOT NULL
                                CHECK (tipo IN ('curso', 'video', 'artigo', 'podcast')),
    categoria_id            INTEGER NOT NULL REFERENCES categorias (categoria_id),
    nivel                   TEXT NOT NULL
                                CHECK (nivel IN ('basico', 'intermediario', 'avancado')),
    carga_horaria_min       INTEGER NOT NULL CHECK (carga_horaria_min > 0),
    data_publicacao         DATE,
    descricao               TEXT,
    autor                   TEXT
);

CREATE TABLE IF NOT EXISTS interacoes (
    interacao_id             SERIAL PRIMARY KEY,
    usuario_id                 INTEGER NOT NULL REFERENCES usuarios (usuario_id),
    conteudo_id                 INTEGER NOT NULL REFERENCES conteudos (conteudo_id),
    tipo_interacao               TEXT NOT NULL
                                      CHECK (tipo_interacao IN
                                          ('visualizacao', 'inicio', 'conclusao',
                                           'curtida', 'avaliacao', 'compartilhamento')),
    data_hora                    TIMESTAMP NOT NULL,
    tempo_consumido_min          NUMERIC(10, 2) NOT NULL CHECK (tempo_consumido_min >= 0),
    percentual_conclusao         NUMERIC(5, 2) NOT NULL
                                      CHECK (percentual_conclusao BETWEEN 0 AND 100),
    avaliacao                    SMALLINT CHECK (avaliacao BETWEEN 1 AND 5),
    UNIQUE (usuario_id, conteudo_id, tipo_interacao, data_hora)
);

-- Comentários/avaliações também ficam refletidos aqui de forma resumida
-- (a persistência completa dos documentos ocorre no MongoDB, próxima etapa).
CREATE TABLE IF NOT EXISTS avaliacoes_resumo (
    avaliacao_resumo_id     SERIAL PRIMARY KEY,
    usuario_id                INTEGER NOT NULL REFERENCES usuarios (usuario_id),
    conteudo_id                INTEGER NOT NULL REFERENCES conteudos (conteudo_id),
    nota                        SMALLINT NOT NULL CHECK (nota BETWEEN 1 AND 5),
    data_avaliacao               DATE,
    UNIQUE (usuario_id, conteudo_id, data_avaliacao)
);

-- Reservado para a próxima etapa do desafio (não utilizado nesta fase).
CREATE TABLE IF NOT EXISTS recomendacoes (
    recomendacao_id      SERIAL PRIMARY KEY,
    usuario_id             INTEGER NOT NULL REFERENCES usuarios (usuario_id),
    conteudo_id             INTEGER NOT NULL REFERENCES conteudos (conteudo_id),
    pontuacao                NUMERIC(5, 2) NOT NULL CHECK (pontuacao BETWEEN 0 AND 100),
    posicao                   INTEGER NOT NULL CHECK (posicao > 0),
    status                    TEXT NOT NULL CHECK (status IN ('positivo', 'estavel', 'negativo')),
    data_geracao              TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, conteudo_id, data_geracao)
);

CREATE INDEX IF NOT EXISTS idx_interacoes_usuario ON interacoes (usuario_id);
CREATE INDEX IF NOT EXISTS idx_interacoes_conteudo ON interacoes (conteudo_id);
CREATE INDEX IF NOT EXISTS idx_conteudos_categoria ON conteudos (categoria_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_resumo_conteudo ON avaliacoes_resumo (conteudo_id);
CREATE INDEX IF NOT EXISTS idx_recomendacoes_usuario ON recomendacoes (usuario_id);

-- ------------------------------------------------------------
-- Reservado para a próxima etapa do desafio (RF08 - embeddings):
--   CREATE EXTENSION IF NOT EXISTS vector;
--   CREATE TABLE conteudo_embeddings (
--       conteudo_id INTEGER PRIMARY KEY REFERENCES conteudos(conteudo_id),
--       modelo      TEXT NOT NULL,
--       embedding   vector(384)
--   );
-- ------------------------------------------------------------

COMMIT;
