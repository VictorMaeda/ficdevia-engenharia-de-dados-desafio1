-- ============================================================
-- Script DDL idempotente - pg_desafio2
-- Cria (se nao existirem) os schemas bronze, silver e quarentena
-- e todas as tabelas correspondentes.
-- Pode ser executado quantas vezes forem necessarias sem erro.
-- ============================================================

-- ============================================================
-- SCHEMAS
-- ============================================================
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS quarentena;

-- ============================================================
-- BRONZE
-- ============================================================

-- bronze.catalogo
CREATE TABLE IF NOT EXISTS bronze.catalogo (
	conteudo_id text NULL,
	titulo text NULL,
	tipo text NULL,
	categoria text NULL,
	nivel text NULL,
	carga_horaria_min text NULL,
	data_publicacao text NULL,
	descricao text NULL,
	autor text NULL,
	origem_arquivo text NOT NULL,
	data_hora_ingestao timestamp DEFAULT now() NOT NULL,
	execucao_id text NOT NULL
);

-- bronze.comentarios
CREATE TABLE IF NOT EXISTS bronze.comentarios (
	id serial4 NOT NULL,
	conteudo_json jsonb NOT NULL,
	origem_arquivo varchar(100) NOT NULL,
	execucao_id varchar(50) NOT NULL,
	data_hora_ingestao timestamp DEFAULT now() NOT NULL,
	CONSTRAINT comentarios_pkey PRIMARY KEY (id)
);

-- bronze.interacoes
CREATE TABLE IF NOT EXISTS bronze.interacoes (
	id serial4 NOT NULL,
	conteudo_json jsonb NOT NULL,
	origem_arquivo varchar(100) NOT NULL,
	execucao_id varchar(50) NOT NULL,
	data_hora_ingestao timestamp DEFAULT now() NOT NULL,
	CONSTRAINT interacoes_pkey PRIMARY KEY (id)
);

-- bronze.recomendacoes
CREATE TABLE IF NOT EXISTS bronze.recomendacoes (
	usuario_id text NULL,
	conteudo_id text NULL,
	pontuacao text NULL,
	posicao text NULL,
	status text NULL,
	data_geracao text NULL,
	origem_arquivo text NOT NULL,
	data_hora_ingestao timestamp DEFAULT now() NOT NULL,
	execucao_id text NOT NULL
);

-- ============================================================
-- SILVER
-- ============================================================

-- silver.catalogo
CREATE TABLE IF NOT EXISTS silver.catalogo (
	titulo text NOT NULL,
	tipo text NULL,
	categoria text NULL,
	nivel text NULL,
	data_publicacao date NULL,
	descricao text NULL,
	autor text NULL,
	origem_arquivo text NULL,
	execucao_id text NULL,
	conteudo_id float8 NULL,
	carga_horaria_min float8 NULL
);

-- silver.comentarios
CREATE TABLE IF NOT EXISTS silver.comentarios (
	usuario_id int4 NULL,
	conteudo_id int4 NULL,
	avaliacao int2 NULL,
	comentario text NULL,
	"data" date NULL,
	execucao_id text NULL,
	data_hora_padronizacao timestamp DEFAULT now() NOT NULL
);

-- silver.interacoes
CREATE TABLE IF NOT EXISTS silver.interacoes (
	usuario_id int4 NULL,
	conteudo_id int4 NULL,
	tipo_interacao text NULL,
	data_hora timestamp NULL,
	tempo_consumido int4 NULL,
	percentual_conclusao numeric(5, 2) NULL,
	avaliacao_atribuida int2 NULL,
	execucao_id text NULL,
	data_hora_padronizacao timestamp DEFAULT now() NOT NULL
);

-- silver.recomendacoes
CREATE TABLE IF NOT EXISTS silver.recomendacoes (
	usuario_id int4 NULL,
	conteudo_id int4 NULL,
	pontuacao numeric(5, 2) NULL,
	posicao int4 NULL,
	status text NULL,
	data_geracao timestamp NULL,
	execucao_id text NULL,
	data_hora_padronizacao timestamp DEFAULT now() NOT NULL
);

-- ============================================================
-- QUARENTENA
-- ============================================================
-- Atencao: comentarios, interacoes e recomendacoes usam a MESMA
-- sequence gerada pela coluna bigserial de quarentena.catalogo
-- (quarentena.catalogo_registro_id_seq), entao catalogo precisa
-- ser criada primeiro.

-- quarentena.catalogo (cria a sequence catalogo_registro_id_seq)
CREATE TABLE IF NOT EXISTS quarentena.catalogo (
	registro_id bigserial NOT NULL,
	origem text NOT NULL,
	regra_violada text NOT NULL,
	data_erro timestamp DEFAULT now() NOT NULL,
	mensagem_erro text NULL,
	execucao_id text NULL,
	payload jsonb NULL,
	CONSTRAINT catalogo_pkey PRIMARY KEY (registro_id)
);

-- quarentena.comentarios (reaproveita a sequence de catalogo)
CREATE TABLE IF NOT EXISTS quarentena.comentarios (
	registro_id int8 DEFAULT nextval('quarentena.catalogo_registro_id_seq'::regclass) NOT NULL,
	origem text NOT NULL,
	regra_violada text NOT NULL,
	data_erro timestamp DEFAULT now() NOT NULL,
	mensagem_erro text NULL,
	execucao_id text NULL,
	payload jsonb NULL,
	CONSTRAINT comentarios_pkey PRIMARY KEY (registro_id)
);

-- quarentena.interacoes (reaproveita a sequence de catalogo)
CREATE TABLE IF NOT EXISTS quarentena.interacoes (
	registro_id int8 DEFAULT nextval('quarentena.catalogo_registro_id_seq'::regclass) NOT NULL,
	origem text NOT NULL,
	regra_violada text NOT NULL,
	data_erro timestamp DEFAULT now() NOT NULL,
	mensagem_erro text NULL,
	execucao_id text NULL,
	payload jsonb NULL,
	CONSTRAINT interacoes_pkey PRIMARY KEY (registro_id)
);

-- quarentena.recomendacoes (reaproveita a sequence de catalogo)
CREATE TABLE IF NOT EXISTS quarentena.recomendacoes (
	registro_id int8 DEFAULT nextval('quarentena.catalogo_registro_id_seq'::regclass) NOT NULL,
	origem text NOT NULL,
	regra_violada text NOT NULL,
	data_erro timestamp DEFAULT now() NOT NULL,
	mensagem_erro text NULL,
	execucao_id text NULL,
	payload jsonb NULL,
	CONSTRAINT recomendacoes_pkey PRIMARY KEY (registro_id)
);

-- ============================================================
-- GOLD
-- ============================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- ------------------------------------------------------------
-- gold.engajamento_conteudo
--
-- Granularidade:
--   1 linha = 1 conteudo_id
--
-- Origem:
--   agregacao Apache Beam + silver.catalogo
--
-- Medidas:
--   total_interacoes
--   tempo_total_segundos
--   media_percentual_conclusao
--   quantidade_conclusoes
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.engajamento_conteudo (
    conteudo_id int4 NOT NULL,
    titulo text NOT NULL,
    tipo text NULL,
    categoria text NULL,
    nivel text NULL,

    total_interacoes int8 NOT NULL,
    tempo_total_segundos int8 NOT NULL,
    media_percentual_conclusao numeric(7, 2) NULL,
    quantidade_conclusoes int8 NOT NULL,

    data_carga timestamp DEFAULT now() NOT NULL,

    CONSTRAINT engajamento_conteudo_pkey
        PRIMARY KEY (conteudo_id)
);


-- ------------------------------------------------------------
-- Visao resumida por categoria
--
-- Pergunta de negocio:
-- Quais categorias concentram mais engajamento?
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW gold.vw_resumo_categoria AS
SELECT
    categoria,

    COUNT(*) AS total_conteudos,

    SUM(total_interacoes) AS total_interacoes,

    SUM(tempo_total_segundos) AS tempo_total_segundos,

    ROUND(
        AVG(media_percentual_conclusao),
        2
    ) AS media_percentual_conclusao,

    SUM(quantidade_conclusoes) AS quantidade_conclusoes

FROM gold.engajamento_conteudo

GROUP BY categoria;


-- ------------------------------------------------------------
-- Ranking de engajamento por conteudo
--
-- Pergunta de negocio:
-- Quais conteudos apresentam maior volume de interacoes?
-- ------------------------------------------------------------

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

    RANK() OVER (
        ORDER BY total_interacoes DESC
    ) AS ranking_interacoes

FROM gold.engajamento_conteudo;

-- ============================================================
-- QUALIDADE DE DADOS
-- RF31
-- ============================================================

CREATE SCHEMA IF NOT EXISTS qualidade;


-- ------------------------------------------------------------
-- Historico dos testes de qualidade
--
-- Uma linha representa o resultado de um teste de qualidade
-- em uma determinada execucao e fonte.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS qualidade.resultados (
    id bigserial PRIMARY KEY,

    execucao_qualidade_id varchar(36) NOT NULL,
    execucao_dados_id text NULL,

    fonte text NOT NULL,
    teste_codigo varchar(50) NOT NULL,
    teste_nome text NOT NULL,
    dimensao varchar(30) NOT NULL,

    formula text NOT NULL,
    limite_aceitavel numeric(7, 3) NOT NULL,
    severidade varchar(20) NOT NULL,
    acao text NOT NULL,

    total_registros int8 NOT NULL,
    registros_invalidos int8 NOT NULL,
    valor_metrica numeric(7, 3) NOT NULL,

    status varchar(20) NOT NULL,

    data_execucao timestamp DEFAULT now() NOT NULL
);


-- ------------------------------------------------------------
-- Evolucao das metricas de qualidade
--
-- Q01 = completude dos dados de interacao
-- Q05 = integridade referencial com o catalogo
--
-- Estas duas metricas serao utilizadas para demonstrar
-- a evolucao historica exigida pelo RF31.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW qualidade.vw_evolucao_metricas AS
SELECT
    data_execucao,
    execucao_qualidade_id,
    execucao_dados_id,
    fonte,
    teste_codigo,
    teste_nome,
    dimensao,
    valor_metrica,
    limite_aceitavel,
    status
FROM qualidade.resultados
WHERE teste_codigo IN (
    'Q01_COMPLETUDE',
    'Q05_INTEGRIDADE_REFERENCIAL'
)
ORDER BY
    data_execucao,
    teste_codigo;
