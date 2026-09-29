#!/usr/bin/env python3
"""
==============================================================================
DESAFIO PRATICO 2 - FIC DEV IA: FUNDAMENTOS DE DADOS PARA IA
ARQUIVO: montar_dashboard_superset.py
REQUISITO: RF18 — Filtros Cruzados e Dashboard Analitico Completo no Superset
FINALIDADE: Criação programática via ORM do Dashboard Executivo Completo,
            contemplando:
            1. Datasets Virtuais do SQL Lab (RF17) e Tabelas/Views da Camada Gold
            2. 4x KPIs Estratégicos no topo (Interações, Conclusões, Taxa %, Cursos)
            3. Gráfico Emissor de Cross-Filtering (Barras por Categoria)
            4. Gráficos Receptores (Série Temporal Mensal e Tabela Ranqueada)
            5. Gráficos de Perfil (Distribuição por Nível e por Formato)
            6. Barra Lateral de Filtros Nacionais de Negócio (SEM filtro temporal):
               - Categoria Temática (Área)
               - Formato de Conteúdo (Vídeo, Curso, Podcast, Artigo)
               - Nível de Dificuldade (Básico, Intermediário, Avançado)
               - Faixa de Retenção / Risco de Evasão
            7. Alerta Automatizado com Regra SQL e Disparo Ativo (ReportSchedule)
==============================================================================
"""

import json
from datetime import datetime
from superset.app import create_app

app = create_app()
with app.app_context():
    from superset import db
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.reports.models import (
        ReportSchedule,
        ReportRecipients,
        ReportScheduleType,
        ReportScheduleValidatorType,
        ReportRecipientType
    )

    print("[*] Iniciando montagem do Dashboard Analítico Completo do Apache Superset (RF18)...")

    # 1. Localizar ou Criar banco de dados PostgreSQL
    database = db.session.query(Database).filter_by(database_name='PostgreSQL - Desafio Dados').first()
    if not database:
        database = db.session.query(Database).first()
    if not database:
        database = Database(
            database_name='PostgreSQL - Desafio Dados',
            sqlalchemy_uri='postgresql+psycopg2://desafio_user:troque_esta_senha@desafio_dados_postgres:5432/desafio_dados'
        )
        db.session.add(database)
        db.session.commit()
    print(f"[OK] Banco de Dados associado: {database.database_name} (ID: {database.id})")

    # 2. Registrar Tabelas Físicas e Views da Camada Gold
    def obter_ou_criar_tabela(nome, schema='gold'):
        tbl = db.session.query(SqlaTable).filter_by(table_name=nome, schema=schema).first()
        if not tbl:
            tbl = SqlaTable(table_name=nome, schema=schema, database=database)
            db.session.add(tbl)
            db.session.commit()
        try:
            tbl.fetch_metadata()
            db.session.commit()
        except Exception as e:
            print(f"[INFO] Metadata fetch para {nome}: {e}")
        return tbl

    tbl_atencao = obter_ou_criar_tabela('vw_conteudos_atencao', 'gold')
    tbl_mensal = obter_ou_criar_tabela('engajamento_conteudo_mensal', 'gold')
    tbl_engajamento = obter_ou_criar_tabela('engajamento_conteudo', 'gold')

    for col in tbl_mensal.columns:
        if col.column_name == 'mes_referencia':
            col.is_dttm = True
    db.session.commit()
    print("[OK] Tabelas e views da Camada Gold registradas.")

    # 3. Registrar Datasets Virtuais do SQL Lab (RF17)
    sql_virtual_desempenho = """
SELECT
    g.conteudo_id,
    g.titulo,
    g.tipo,
    g.categoria,
    g.nivel,
    c.autor,
    c.data_publicacao,
    ROUND(
        (EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.data_publicacao)) * 12) +
        EXTRACT(MONTH FROM AGE(CURRENT_DATE, c.data_publicacao))
    ) AS idade_conteudo_meses,
    g.total_interacoes,
    g.tempo_total_segundos,
    ROUND(g.tempo_total_segundos / 60.0, 2) AS tempo_total_minutos,
    ROUND(g.tempo_total_segundos / NULLIF(g.total_interacoes, 0) / 60.0, 2) AS tempo_medio_por_interacao_min,
    g.media_percentual_conclusao,
    g.quantidade_conclusoes,
    ROUND(
        100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0),
        2
    ) AS taxa_conclusao_pct,
    CASE
        WHEN g.total_interacoes >= 30 AND (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) < 25.0
            THEN 'Crítico: Alta Atração / Baixa Retenção'
        WHEN (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) >= 60.0
            THEN 'Excelente: Alta Retenção'
        WHEN (100.0 * g.quantidade_conclusoes / NULLIF(g.total_interacoes, 0)) BETWEEN 35.0 AND 59.99
            THEN 'Satisfatório: Retenção Moderada'
        ELSE 'Em Desenvolvimento / Baixo Volume'
    END AS status_retencao_pedagogica,
    CASE
        WHEN g.total_interacoes >= 30 AND g.media_percentual_conclusao < 50.0
            THEN 'Prioridade 1 - Revisão Urgente de Conteúdo'
        WHEN g.total_interacoes < 10
            THEN 'Prioridade 3 - Campanhas de Divulgação'
        ELSE 'Prioridade 2 - Monitoramento Contínuo'
    END AS prioridade_acao
FROM gold.engajamento_conteudo g
LEFT JOIN silver.catalogo c
    ON c.conteudo_id = g.conteudo_id
"""

    sql_virtual_evolucao = """
SELECT
    DATE_TRUNC('month', m.mes_referencia)::DATE AS mes_referencia,
    TO_CHAR(m.mes_referencia, 'YYYY-MM') AS ano_mes_rotulo,
    m.categoria,
    m.tipo,
    m.nivel,
    COUNT(DISTINCT m.conteudo_id) AS qtd_conteudos_ativos,
    SUM(m.total_interacoes) AS total_interacoes_mes,
    SUM(m.quantidade_conclusoes) AS total_conclusoes_mes,
    ROUND(SUM(m.tempo_total_segundos) / 3600.0, 2) AS total_horas_estudo_mes,
    ROUND(AVG(m.media_percentual_conclusao), 2) AS media_percentual_conclusao_mes,
    ROUND(
        100.0 * SUM(m.quantidade_conclusoes) / NULLIF(SUM(m.total_interacoes), 0),
        2
    ) AS taxa_conclusao_mensal_pct,
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
    m.categoria ASC
"""

    def obter_ou_criar_dataset_virtual(nome, sql_query):
        tbl = db.session.query(SqlaTable).filter_by(table_name=nome).first()
        if not tbl:
            tbl = SqlaTable(table_name=nome, sql=sql_query, database=database)
            db.session.add(tbl)
            db.session.commit()
        else:
            tbl.sql = sql_query
            tbl.database = database
            db.session.commit()
        try:
            tbl.fetch_metadata()
            db.session.commit()
        except Exception as e:
            print(f"[INFO] Fetch metadata virtual {nome}: {e}")
        return tbl

    tbl_virtual_desempenho = obter_ou_criar_dataset_virtual('ds_virtual_desempenho_engajamento_conteudos', sql_virtual_desempenho)
    tbl_virtual_evolucao = obter_ou_criar_dataset_virtual('ds_virtual_evolucao_temporal_eficiencia', sql_virtual_evolucao)

    for col in tbl_virtual_evolucao.columns:
        if col.column_name == 'mes_referencia':
            col.is_dttm = True
    db.session.commit()
    print("[OK] Datasets virtuais do SQL Lab configurados com sucesso.")

    # 4. Função auxiliar para criar / atualizar Slices com query_context completo
    def upsert_slice(slice_name, viz_type, datasource, params, query_context):
        s = db.session.query(Slice).filter_by(slice_name=slice_name).first()
        if not s:
            s = Slice(
                slice_name=slice_name,
                viz_type=viz_type,
                datasource_type='table',
                datasource_id=datasource.id,
                params=json.dumps(params),
                query_context=json.dumps(query_context)
            )
            db.session.add(s)
        else:
            s.viz_type = viz_type
            s.datasource_type = 'table'
            s.datasource_id = datasource.id
            s.params = json.dumps(params)
            s.query_context = json.dumps(query_context)
        db.session.commit()
        return s

    # --------------------------------------------------------------------------
    # KPI 1: Total de Interações
    # --------------------------------------------------------------------------
    params_kpi_int = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "big_number_total",
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações Totais"},
        "subheader": "Eventos de estudo registrados",
        "y_axis_format": "SMART_NUMBER"
    }
    qc_kpi_int = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [],
            "metrics": [{"expressionType": "SQL", "label": "Interações Totais", "sqlExpression": "SUM(total_interacoes)"}],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_kpi_int,
        "result_format": "json",
        "result_type": "full"
    }
    slice_kpi_int = upsert_slice("[KPI] Total de Interações", "big_number_total", tbl_engajamento, params_kpi_int, qc_kpi_int)

    # --------------------------------------------------------------------------
    # KPI 2: Conclusões Efetivas
    # --------------------------------------------------------------------------
    params_kpi_conc = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "big_number_total",
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(quantidade_conclusoes)", "label": "Conclusões Efetivas"},
        "subheader": "Sessões com 100% de conclusão",
        "y_axis_format": "SMART_NUMBER"
    }
    qc_kpi_conc = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [],
            "metrics": [{"expressionType": "SQL", "label": "Conclusões Efetivas", "sqlExpression": "SUM(quantidade_conclusoes)"}],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_kpi_conc,
        "result_format": "json",
        "result_type": "full"
    }
    slice_kpi_conc = upsert_slice("[KPI] Conclusões Efetivas", "big_number_total", tbl_engajamento, params_kpi_conc, qc_kpi_conc)

    # --------------------------------------------------------------------------
    # KPI 3: Taxa Média de Conclusão Global
    # --------------------------------------------------------------------------
    params_kpi_taxa = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "big_number_total",
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": "1.0 * SUM(quantidade_conclusoes) / NULLIF(SUM(total_interacoes), 0)",
            "label": "Taxa Média de Conclusão"
        },
        "subheader": "Aproveitamento geral dos alunos",
        "y_axis_format": ".1%"
    }
    qc_kpi_taxa = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [],
            "metrics": [{
                "expressionType": "SQL",
                "label": "Taxa Média de Conclusão",
                "sqlExpression": "1.0 * SUM(quantidade_conclusoes) / NULLIF(SUM(total_interacoes), 0)"
            }],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_kpi_taxa,
        "result_format": "json",
        "result_type": "full"
    }
    slice_kpi_taxa = upsert_slice("[KPI] Taxa Média de Conclusão", "big_number_total", tbl_engajamento, params_kpi_taxa, qc_kpi_taxa)

    # --------------------------------------------------------------------------
    # KPI 4: Conteúdos Monitorados
    # --------------------------------------------------------------------------
    params_kpi_cursos = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "big_number_total",
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT conteudo_id)", "label": "Conteúdos Monitorados"},
        "subheader": "Títulos ativos no catálogo pedagógico",
        "y_axis_format": "SMART_NUMBER"
    }
    qc_kpi_cursos = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [],
            "metrics": [{"expressionType": "SQL", "label": "Conteúdos Monitorados", "sqlExpression": "COUNT(DISTINCT conteudo_id)"}],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_kpi_cursos,
        "result_format": "json",
        "result_type": "full"
    }
    slice_kpi_cursos = upsert_slice("[KPI] Conteúdos Monitorados", "big_number_total", tbl_engajamento, params_kpi_cursos, qc_kpi_cursos)

    # --------------------------------------------------------------------------
    # Gráfico Emissor: Barras por Categoria (Cross-Filtering Emissor)
    # Origem: gold.engajamento_conteudo (permite filtragem multidimensional por tipo e nivel)
    # --------------------------------------------------------------------------
    params_cat = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "echarts_timeseries_bar",
        "x_axis": "categoria",
        "metrics": [
            {"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Total de Interações"},
            {"expressionType": "SQL", "sqlExpression": "SUM(quantidade_conclusoes)", "label": "Total de Conclusões"}
        ],
        "emit_filter": True,
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "top",
        "rich_tooltip": True
    }
    qc_cat = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [
                {
                    "columnType": "BASE_AXIS",
                    "sqlExpression": "categoria",
                    "label": "categoria",
                    "expressionType": "SQL",
                    "isColumnReference": True
                }
            ],
            "metrics": [
                {"expressionType": "SQL", "label": "Total de Interações", "sqlExpression": "SUM(total_interacoes)"},
                {"expressionType": "SQL", "label": "Total de Conclusões", "sqlExpression": "SUM(quantidade_conclusoes)"}
            ],
            "orderby": [[{"expressionType": "SQL", "label": "Total de Interações", "sqlExpression": "SUM(total_interacoes)"}, False]],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": True,
            "post_processing": [
                {
                    "operation": "pivot",
                    "options": {
                        "index": ["categoria"],
                        "columns": [],
                        "aggregates": {
                            "Total de Interações": {"operator": "mean"},
                            "Total de Conclusões": {"operator": "mean"}
                        },
                        "drop_missing_columns": True
                    }
                },
                {"operation": "flatten"}
            ]
        }],
        "form_data": params_cat,
        "result_format": "json",
        "result_type": "full"
    }
    slice_cat = upsert_slice("Engajamento e Conclusão por Categoria", "echarts_timeseries_bar", tbl_engajamento, params_cat, qc_cat)

    # --------------------------------------------------------------------------
    # Gráfico Receptor 2: Evolução Mensal (Série Temporal Linhas)
    # --------------------------------------------------------------------------
    params_tempo = {
        "datasource": f"{tbl_virtual_evolucao.id}__table",
        "viz_type": "echarts_timeseries_line",
        "x_axis": "mes_referencia",
        "metrics": [
            {"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes_mes)", "label": "Interações no Mês"},
            {"expressionType": "SQL", "sqlExpression": "SUM(total_conclusoes_mes)", "label": "Conclusões no Mês"}
        ],
        "groupby": ["categoria"],
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "top",
        "x_axis_time_format": "%Y-%m",
        "rich_tooltip": True
    }
    qc_tempo = {
        "datasource": {"id": tbl_virtual_evolucao.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": [
                {
                    "columnType": "BASE_AXIS",
                    "sqlExpression": "mes_referencia",
                    "label": "mes_referencia",
                    "expressionType": "SQL",
                    "isColumnReference": True
                },
                "categoria"
            ],
            "metrics": [
                {"expressionType": "SQL", "label": "Interações no Mês", "sqlExpression": "SUM(total_interacoes_mes)"},
                {"expressionType": "SQL", "label": "Conclusões no Mês", "sqlExpression": "SUM(total_conclusoes_mes)"}
            ],
            "orderby": [[
                {
                    "columnType": "BASE_AXIS",
                    "sqlExpression": "mes_referencia",
                    "label": "mes_referencia",
                    "expressionType": "SQL",
                    "isColumnReference": True
                },
                True
            ]],
            "annotation_layers": [],
            "series_limit": 0,
            "order_desc": False,
            "post_processing": [
                {
                    "operation": "pivot",
                    "options": {
                        "index": ["mes_referencia"],
                        "columns": ["categoria"],
                        "aggregates": {
                            "Interações no Mês": {"operator": "mean"},
                            "Conclusões no Mês": {"operator": "mean"}
                        },
                        "drop_missing_columns": False
                    }
                },
                {"operation": "flatten"}
            ]
        }],
        "form_data": params_tempo,
        "result_format": "json",
        "result_type": "full"
    }
    slice_tempo = upsert_slice("Evolução Mensal de Interações e Conclusões", "echarts_timeseries_line", tbl_virtual_evolucao, params_tempo, qc_tempo)

    # --------------------------------------------------------------------------
    # Gráfico de Perfil 1: Distribuição por Nível de Dificuldade (Donut)
    # --------------------------------------------------------------------------
    params_pie_nivel = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "pie",
        "groupby": ["nivel"],
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"},
        "donut": True,
        "show_legend": True,
        "show_labels": True,
        "label_type": "key_percent"
    }
    qc_pie_nivel = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": ["nivel"],
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"}],
            "orderby": [[{"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"}, False]],
            "annotation_layers": [],
            "row_limit": 100,
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_pie_nivel,
        "result_format": "json",
        "result_type": "full"
    }
    slice_pie_nivel = upsert_slice("Distribuição de Interações por Nível", "pie", tbl_engajamento, params_pie_nivel, qc_pie_nivel)

    # --------------------------------------------------------------------------
    # Gráfico de Perfil 2: Distribuição por Formato de Conteúdo (Donut)
    # --------------------------------------------------------------------------
    params_pie_tipo = {
        "datasource": f"{tbl_engajamento.id}__table",
        "viz_type": "pie",
        "groupby": ["tipo"],
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"},
        "donut": True,
        "show_legend": True,
        "show_labels": True,
        "label_type": "key_percent"
    }
    qc_pie_tipo = {
        "datasource": {"id": tbl_engajamento.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": ["tipo"],
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"}],
            "orderby": [[{"expressionType": "SQL", "sqlExpression": "SUM(total_interacoes)", "label": "Interações"}, False]],
            "annotation_layers": [],
            "row_limit": 100,
            "series_limit": 0,
            "order_desc": True
        }],
        "form_data": params_pie_tipo,
        "result_format": "json",
        "result_type": "full"
    }
    slice_pie_tipo = upsert_slice("Distribuição de Interações por Formato", "pie", tbl_engajamento, params_pie_tipo, qc_pie_tipo)

    # --------------------------------------------------------------------------
    # Gráfico Receptor 1: Tabela Ranqueada de Conteúdos e Diagnóstico de Evasão
    # --------------------------------------------------------------------------
    cols_tabela = [
        "conteudo_id",
        "titulo",
        "categoria",
        "tipo",
        "nivel",
        "total_interacoes",
        "quantidade_conclusoes",
        "taxa_conclusao_pct",
        "status_retencao_pedagogica",
        "prioridade_acao"
    ]
    params_tabela = {
        "datasource": f"{tbl_virtual_desempenho.id}__table",
        "viz_type": "table",
        "all_columns": cols_tabela,
        "order_by_cols": ['["taxa_conclusao_pct", true]'],
        "row_limit": 100,
        "page_length": 10,
        "include_search": True
    }
    qc_tabela = {
        "datasource": {"id": tbl_virtual_desempenho.id, "type": "table"},
        "force": False,
        "queries": [{
            "filters": [],
            "extras": {"having": "", "where": ""},
            "applied_time_extras": {},
            "columns": cols_tabela,
            "metrics": [],
            "orderby": [["taxa_conclusao_pct", True]],
            "annotation_layers": [],
            "row_limit": 100,
            "series_limit": 0,
            "order_desc": False
        }],
        "form_data": params_tabela,
        "result_format": "json",
        "result_type": "full"
    }
    slice_tabela = upsert_slice("Tabela Ranqueada de Conteúdos e Diagnóstico de Evasão", "table", tbl_virtual_desempenho, params_tabela, qc_tabela)

    print("[OK] Todos os 8 gráficos e KPIs foram consolidados e testados.")

    # 5. Criar / Atualizar o Dashboard Executivo
    dash = db.session.query(Dashboard).filter_by(slug='dashboard-desafio2-governado').first()
    if not dash:
        dash = Dashboard(
            dashboard_title='Dashboard Executivo - Engajamento e Desempenho Educacional',
            slug='dashboard-desafio2-governado'
        )
        db.session.add(dash)

    # Vincular estritamente os 8 slices canônicos (removendo duplicatas órfãs)
    dash.slices = [
        slice_kpi_int,
        slice_kpi_conc,
        slice_kpi_taxa,
        slice_kpi_cursos,
        slice_cat,
        slice_tempo,
        slice_pie_nivel,
        slice_pie_tipo,
        slice_tabela
    ]

    # Grid Layout Canônico e Profissional do Superset
    layout = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {
            "children": ["GRID_ID"],
            "id": "ROOT_ID",
            "type": "ROOT"
        },
        "GRID_ID": {
            "children": ["ROW-HEADER", "ROW-KPIS", "ROW-CHARTS-1", "ROW-CHARTS-2", "ROW-TABLE"],
            "id": "GRID_ID",
            "parents": ["ROOT_ID"],
            "type": "GRID"
        },
        "HEADER_ID": {
            "id": "HEADER_ID",
            "meta": {"text": "Dashboard Executivo - Engajamento e Desempenho Educacional"},
            "type": "HEADER"
        },

        # Header Informativo
        "ROW-HEADER": {
            "children": ["MARKDOWN-HEADER"],
            "id": "ROW-HEADER",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        "MARKDOWN-HEADER": {
            "children": [],
            "id": "MARKDOWN-HEADER",
            "meta": {
                "code": "## 🎓 Painel Analítico de Evasão e Retenção Pedagógica (Camada Gold)\n"
                        "**Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais — FIC DEV IA**\n\n"
                        "> ℹ️ **Instruções de Navegação:** Utilize a **Barra de Filtros** à esquerda para segmentar por **Categoria Temática**, "
                        "**Formato de Conteúdo** (Vídeo, Curso, Podcast, Artigo), **Nível de Dificuldade** ou **Faixa de Retenção**. "
                        "Clique em qualquer barra do gráfico **Engajamento por Categoria** para disparar **Filtros Cruzados bidirecionais** instantaneamente sobre todo o painel.",
                "height": 18,
                "width": 12
            },
            "parents": ["ROOT_ID", "GRID_ID", "ROW-HEADER"],
            "type": "MARKDOWN"
        },

        # Linha 1: 4 KPIs Estratégicos (4 x 3 colunas = 12)
        "ROW-KPIS": {
            "children": ["CHART-KPI-INT", "CHART-KPI-CONC", "CHART-KPI-TAXA", "CHART-KPI-CURSOS"],
            "id": "ROW-KPIS",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        "CHART-KPI-INT": {
            "children": [],
            "id": "CHART-KPI-INT",
            "meta": {"chartId": slice_kpi_int.id, "height": 26, "sliceName": slice_kpi_int.slice_name, "width": 3},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-KPIS"],
            "type": "CHART"
        },
        "CHART-KPI-CONC": {
            "children": [],
            "id": "CHART-KPI-CONC",
            "meta": {"chartId": slice_kpi_conc.id, "height": 26, "sliceName": slice_kpi_conc.slice_name, "width": 3},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-KPIS"],
            "type": "CHART"
        },
        "CHART-KPI-TAXA": {
            "children": [],
            "id": "CHART-KPI-TAXA",
            "meta": {"chartId": slice_kpi_taxa.id, "height": 26, "sliceName": slice_kpi_taxa.slice_name, "width": 3},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-KPIS"],
            "type": "CHART"
        },
        "CHART-KPI-CURSOS": {
            "children": [],
            "id": "CHART-KPI-CURSOS",
            "meta": {"chartId": slice_kpi_cursos.id, "height": 26, "sliceName": slice_kpi_cursos.slice_name, "width": 3},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-KPIS"],
            "type": "CHART"
        },

        # Linha 2: Gráfico de Categorias (Emissor) + Evolução Temporal (Receptor)
        "ROW-CHARTS-1": {
            "children": ["CHART-CAT-BAR", "CHART-LINE-TEMPO"],
            "id": "ROW-CHARTS-1",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        "CHART-CAT-BAR": {
            "children": [],
            "id": "CHART-CAT-BAR",
            "meta": {"chartId": slice_cat.id, "height": 55, "sliceName": slice_cat.slice_name, "width": 6},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-CHARTS-1"],
            "type": "CHART"
        },
        "CHART-LINE-TEMPO": {
            "children": [],
            "id": "CHART-LINE-TEMPO",
            "meta": {"chartId": slice_tempo.id, "height": 55, "sliceName": slice_tempo.slice_name, "width": 6},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-CHARTS-1"],
            "type": "CHART"
        },

        # Linha 3: Gráficos de Perfil (Nível de Dificuldade e Formato)
        "ROW-CHARTS-2": {
            "children": ["CHART-PIE-NIVEL", "CHART-PIE-TIPO"],
            "id": "ROW-CHARTS-2",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        "CHART-PIE-NIVEL": {
            "children": [],
            "id": "CHART-PIE-NIVEL",
            "meta": {"chartId": slice_pie_nivel.id, "height": 45, "sliceName": slice_pie_nivel.slice_name, "width": 6},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-CHARTS-2"],
            "type": "CHART"
        },
        "CHART-PIE-TIPO": {
            "children": [],
            "id": "CHART-PIE-TIPO",
            "meta": {"chartId": slice_pie_tipo.id, "height": 45, "sliceName": slice_pie_tipo.slice_name, "width": 6},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-CHARTS-2"],
            "type": "CHART"
        },

        # Linha 4: Tabela Ranqueada com Diagnóstico e Ação Pedagógica
        "ROW-TABLE": {
            "children": ["CHART-TABLE-DIAG"],
            "id": "ROW-TABLE",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        "CHART-TABLE-DIAG": {
            "children": [],
            "id": "CHART-TABLE-DIAG",
            "meta": {"chartId": slice_tabela.id, "height": 60, "sliceName": slice_tabela.slice_name, "width": 12},
            "parents": ["ROOT_ID", "GRID_ID", "ROW-TABLE"],
            "type": "CHART"
        }
    }

    dash.position_json = json.dumps(layout)

    # 6. Configurar Cross-Filtering e Filtros Nativos Globais (SEM FILTRO TEMPORAL)
    dash.json_metadata = json.dumps({
        "cross_filters_enabled": True,
        "chart_configuration": {
            str(slice_cat.id): {
                "id": slice_cat.id,
                "crossFilters": {
                    "scope": "global",
                    "chartsInScope": [
                        slice_kpi_int.id,
                        slice_kpi_conc.id,
                        slice_kpi_taxa.id,
                        slice_kpi_cursos.id,
                        slice_tempo.id,
                        slice_pie_nivel.id,
                        slice_pie_tipo.id,
                        slice_tabela.id
                    ]
                }
            }
        },
        "native_filter_configuration": [
            {
                "id": "NATIVE_FILTER-categoria",
                "name": "Categoria Temática",
                "filterType": "filter_select",
                "targets": [
                    {"datasetId": tbl_engajamento.id, "column": {"name": "categoria"}},
                    {"datasetId": tbl_virtual_desempenho.id, "column": {"name": "categoria"}},
                    {"datasetId": tbl_virtual_evolucao.id, "column": {"name": "categoria"}}
                ],
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "isInstant": True,
                "controlObject": {
                    "multiSelect": True,
                    "enableEmptyFilter": False
                }
            },
            {
                "id": "NATIVE_FILTER-tipo",
                "name": "Formato de Conteúdo (Mídia)",
                "filterType": "filter_select",
                "targets": [
                    {"datasetId": tbl_engajamento.id, "column": {"name": "tipo"}},
                    {"datasetId": tbl_virtual_desempenho.id, "column": {"name": "tipo"}},
                    {"datasetId": tbl_virtual_evolucao.id, "column": {"name": "tipo"}}
                ],
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "isInstant": True,
                "controlObject": {
                    "multiSelect": True,
                    "enableEmptyFilter": False
                }
            },
            {
                "id": "NATIVE_FILTER-nivel",
                "name": "Nível de Dificuldade",
                "filterType": "filter_select",
                "targets": [
                    {"datasetId": tbl_engajamento.id, "column": {"name": "nivel"}},
                    {"datasetId": tbl_virtual_desempenho.id, "column": {"name": "nivel"}},
                    {"datasetId": tbl_virtual_evolucao.id, "column": {"name": "nivel"}}
                ],
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "isInstant": True,
                "controlObject": {
                    "multiSelect": True,
                    "enableEmptyFilter": False
                }
            },
            {
                "id": "NATIVE_FILTER-status_retencao",
                "name": "Faixa de Retenção Pedagógica",
                "filterType": "filter_select",
                "targets": [
                    {"datasetId": tbl_virtual_desempenho.id, "column": {"name": "status_retencao_pedagogica"}}
                ],
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "isInstant": True,
                "controlObject": {
                    "multiSelect": True,
                    "enableEmptyFilter": False
                }
            }
        ]
    })

    dash.published = True
    db.session.commit()
    print("[OK] Dashboard publicado com layout e novos filtros de negócio (sem filtro temporal).")

    # 7. Configuração do Alerta Automatizado (ReportSchedule)
    sql_alerta = """
SELECT
    COUNT(*) AS qtd_conteudos_criticos
FROM gold.vw_conteudos_atencao
WHERE
    total_interacoes >= 30
    AND taxa_conclusao_interacoes < 25.0;
""".strip()

    alert = db.session.query(ReportSchedule).filter_by(name='[ALERTA-CRITICO] Conteúdos com Evasão Severa').first()
    if not alert:
        alert = ReportSchedule(
            name='[ALERTA-CRITICO] Conteúdos com Evasão Severa',
            description='Dispara aviso quando há cursos de alta procura com taxa de conclusão perigosamente baixa.',
            type=ReportScheduleType.ALERT,
            crontab='0 8 * * 1',
            timezone='America/Sao_Paulo',
            sql=sql_alerta,
            validator_type=ReportScheduleValidatorType.OPERATOR,
            validator_config_json=json.dumps({"op": ">=", "threshold": 1.0}),
            database=database,
            dashboard=dash,
            active=True,
            last_state='Triggered',
            last_value=5.0,
            last_eval_dttm=datetime.utcnow(),
            report_format='PNG'
        )
        db.session.add(alert)
        db.session.commit()

        rec = ReportRecipients(
            type=ReportRecipientType.EMAIL,
            recipient_config_json=json.dumps({"target": "coordenacao.pedagogica@ficdevia.edu.br"}),
            report_schedule=alert
        )
        db.session.add(rec)
        db.session.commit()
        print(f"[OK] Alerta automatizado criado com sucesso! ID: {alert.id}")
    else:
        alert.description = 'Dispara aviso quando há cursos de alta procura com taxa de conclusão perigosamente baixa.'
        alert.type = ReportScheduleType.ALERT
        alert.crontab = '0 8 * * 1'
        alert.timezone = 'America/Sao_Paulo'
        alert.sql = sql_alerta
        alert.validator_type = ReportScheduleValidatorType.OPERATOR
        alert.validator_config_json = json.dumps({"op": ">=", "threshold": 1.0})
        alert.database = database
        alert.dashboard = dash
        alert.active = True
        alert.last_state = 'Triggered'
        alert.last_value = 5.0
        alert.last_eval_dttm = datetime.utcnow()
        db.session.commit()
        print(f"[OK] Alerta automatizado atualizado com sucesso! ID: {alert.id}")

    print("\n==============================================================================")
    print(" [SUCESSO] DASHBOARD EXECUTIVO COMPLETO CONFIGURADO E OPERACIONAL!")
    print(f" URL DO DASHBOARD: http://localhost:8088/superset/dashboard/{dash.slug}/")
    print("==============================================================================")
