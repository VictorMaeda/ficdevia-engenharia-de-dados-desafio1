# Desafio 1 — Fundamentos de Dados para IA

## Pipeline de Ingestão e Motor de Recomendação (PostgreSQL + MongoDB)

**Curso:** FIC DEV IA – Engenharia de Dados  
**Turno:** Vespertino

### Integrantes

- Milton Simplício Gonçalves Junior
- Victor Maeda Chinen
- Leonardo de Oliveira Ramos

Este repositório contém a implementação do pipeline completo do Desafio Prático 1, contemplando ingestão, validação e tratamento dos dados, persistência no PostgreSQL e MongoDB, geração de embeddings com `pgvector`, busca semântica, motor de recomendação, métricas, KPIs e dashboard no Apache Superset.

## Escopo implementado

| Requisito | Descrição | Status |
|-----------|-----------|--------|
| RF01 | Inicialização e configuração | ✅ |
| RF02 | Leitura das fontes de dados | ✅ |
| RF03 | Validação dos dados | ✅ |
| RF04 | Tratamento e padronização | ✅ |
| RF05 | Resumo da ingestão | ✅ |
| RF06 | Persistência no PostgreSQL | ✅ |
| RF07 | Persistência no MongoDB | ✅ |
| RF08 | Geração e Armazenamento de Embeddings (`pgvector`) | ✅ |
| RF09 | Busca por Similaridade Semântica em Linguagem Natural | ✅ |
| RF10 | Motor de recomendação (`Ivis`, `Icur`, `Iconc`) | ✅ |
| RF11 | Persistência das recomendações no PostgreSQL | ✅ |
| RF12 | Produção de métricas e KPIs | ✅ |
| RF13 | Dashboard no Apache Superset | ✅ |
| RF14 | Registro de execução e tempos das etapas | ✅ |

## Estrutura do projeto

```text
desafio_dados/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── config/
│   └── config.yaml
├── dados/
│   ├── brutos/            # arquivos de entrada originais
│   └── processados/       # gerado pela execução do pipeline
├── logs/                  # gerado pela execução do pipeline
├── sql/
│   ├── criar_banco.sql    # schema PostgreSQL / pgvector / recomendações
│   ├── consultas.sql      # consultas de apoio
│   └── views_dashboard.sql
├── mongodb/
│   └── consultas.js       # consultas de apoio no MongoDB
├── dashboard/
│   ├── evidencias/
│   └── exportacao/
├── documentacao/
│   ├── arquitetura.md
│   ├── modelo_de_dados.md
│   ├── kpis.md
│   ├── superset.md
│   └── uso_da_ia.md
└── src/
    ├── main.py            # ponto de entrada do pipeline
    ├── config.py          # carregamento de config.yaml + .env
    ├── logger.py
    ├── leitura/           # RF02
    ├── validacao/         # RF03
    ├── tratamento/        # RF04
    ├── resumo/            # RF05
    ├── saida/
    ├── persistencia/      # RF06 e RF07
    ├── recomendacao/      # RF10 e RF11
    └── ia/                # RF08 e RF09
```

## Dados de entrada

Os arquivos reais fornecidos para o desafio já estão em `dados/brutos/`, com os nomes esperados pelo `config/config.yaml`:

- `catalogo.csv`
- `interacoes.json`
- `comentarios.json`

> Não há uma fonte separada de usuários com nome/e-mail. A entidade `usuarios` no PostgreSQL é derivada dos `usuario_id` encontrados nas interações e nos comentários.

## Como executar

### 1. Pré-requisitos

- Python 3.11+
- Docker
- Docker Compose

### 2. Instalar dependências

Crie o ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Linux:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Crie o arquivo `.env` a partir do `.env.example` e configure os parâmetros necessários.

No Linux:

```bash
cp .env.example .env
```

No Windows, o arquivo também pode ser copiado manualmente ou pelo PowerShell.

### 4. Subir PostgreSQL, MongoDB e Superset via Docker

```bash
docker compose up -d
```

O ambiente utiliza:

- PostgreSQL com `pgvector`;
- MongoDB;
- Apache Superset;
- PostgreSQL separado para os metadados do Superset.

### 5. Executar o pipeline completo

```bash
python -m src.main
```

Também é possível executar separadamente:

```bash
python -m src.recomendacao.motor
```

```bash
python -m src.ia.embeddings
```

O sistema irá:

1. ler as três fontes de dados e informar a quantidade de registros de cada uma;
2. validar cada registro como válido, inválido, incompleto ou duplicado;
3. tratar e padronizar os registros válidos;
4. gravar em `dados/processados/` os dados tratados, registros rejeitados e o resumo da ingestão;
5. aplicar o schema e carregar os dados no PostgreSQL utilizando transações;
6. carregar os comentários e avaliações no MongoDB na coleção `comentarios_avaliacoes`;
7. calcular as pontuações de recomendação personalizadas utilizando `Ivis`, `Icur` e `Iconc`;
8. persistir as recomendações no PostgreSQL;
9. gerar embeddings vetoriais de 384 dimensões utilizando `sentence-transformers/all-MiniLM-L6-v2`;
10. armazenar os embeddings na tabela `conteudo_embeddings` utilizando `pgvector`;
11. demonstrar buscas por similaridade semântica em linguagem natural;
12. registrar as principais etapas e seus tempos de execução em log.

## Decisões de tratamento (RF04)

- espaços nas extremidades de campos textuais são removidos;
- `tipo`, `nivel` e `tags` são normalizados;
- datas são convertidas para formato padronizado;
- campos numéricos são convertidos para `int` ou `float`;
- valores ausentes em campos não obrigatórios são preservados como nulos;
- duplicidades são identificadas por chave de negócio e tratadas durante a carga;
- os arquivos originais permanecem preservados.

## Embeddings e Busca Semântica (RF08 e RF09)

Os embeddings dos conteúdos são gerados utilizando:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Cada vetor possui 384 dimensões.

O texto utilizado para geração do embedding é formado por:

```text
titulo + descricao
```

Os vetores são armazenados no PostgreSQL utilizando a extensão `pgvector`.

A busca semântica recebe consultas em linguagem natural e retorna os conteúdos mais semelhantes, apresentando:

- posição;
- identificador do conteúdo;
- similaridade;
- categoria;
- tipo;
- título.

## Motor de Recomendação (RF10 e RF11)

O motor utiliza a fórmula:

```text
Pontuação = ((Ivis + Icur) / 2) * 100 * Iconc
```

Onde:

- `Ivis`: afinidade do usuário com a categoria, baseada no tempo consumido;
- `Icur`: curtidas e avaliações positivas, considerando nota maior ou igual a 4;
- `Iconc`: filtro que remove conteúdos já concluídos pelo usuário.

As recomendações são persistidas no PostgreSQL contendo usuário, conteúdo, pontuação, posição, status e data de geração.

## Métricas, KPIs e Dashboard (RF12 e RF13)

As consultas e views utilizadas para análise estão em:

- `sql/consultas.sql`
- `sql/views_dashboard.sql`

A documentação dos indicadores está em:

- `documentacao/kpis.md`
- `documentacao/superset.md`

O dashboard final foi desenvolvido no Apache Superset e apresenta:

- total de usuários;
- total de interações;
- taxa de conclusão;
- avaliação média;
- interações por categoria;
- evolução mensal das interações;
- distribuição de notas por categoria;
- relação entre engajamento e conclusão.

Também foram adicionados filtros interativos por:

- categoria;
- tipo de conteúdo;
- nível.

A exportação e as evidências do dashboard estão disponíveis em:

```text
dashboard/exportacao/
dashboard/evidencias/
```

## Registro de execução (RF14)

O pipeline registra:

- início e término do processamento;
- arquivos processados;
- quantidade de registros lidos;
- registros rejeitados;
- falhas de conexão;
- falhas de persistência;
- falhas relacionadas aos embeddings;
- tempo de execução das principais etapas;
- tempo total do processamento.

Os logs são gravados em:

```text
logs/execucao.log
```

## Consultas de exemplo

- PostgreSQL: `sql/consultas.sql`
- MongoDB: `mongodb/consultas.js`

As consultas PostgreSQL incluem, entre outras:

- contagem de registros por tabela;
- conteúdos por categoria;
- interações por tipo;
- avaliação média;
- usuários mais ativos;
- taxa de conclusão;
- recomendações.

As consultas MongoDB incluem:

- comentários por conteúdo;
- busca por tag;
- filtro por nota;
- agregação por categoria.

## Tecnologias utilizadas

- Python
- PostgreSQL
- pgvector
- MongoDB
- Docker
- Docker Compose
- Sentence Transformers
- Apache Superset