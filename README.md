# Desafio 1 — Fundamentos de Dados para IA
## Pipeline de Ingestão e Motor de Recomendação (PostgreSQL + MongoDB)

Este repositório contém a implementação **da ingestão até a persistência no PostgreSQL e no MongoDB** (RF01 a RF07), além do **Motor de Recomendação Personalizado e sua Persistência no PostgreSQL** (RF10 e RF11).

## Escopo implementado

| Requisito | Descrição                                             | Status |
|-----------|--------------------------------------------------------|--------|
| RF01      | Inicialização e configuração                            | ✅ |
| RF02      | Leitura das fontes de dados                              | ✅ |
| RF03      | Validação dos dados                                      | ✅ |
| RF04      | Tratamento e padronização                                | ✅ |
| RF05      | Resumo da ingestão                                       | ✅ |
| RF06      | Persistência no PostgreSQL                               | ✅ |
| RF07      | Persistência no MongoDB                                  | ✅ |
| RF10      | Motor de recomendação (Fórmula $I_{vis}$, $I_{cur}$, $I_{conc}$) | ✅ |
| RF11      | Persistência das recomendações no PostgreSQL            | ✅ |
| RF08/RF09 | Embeddings / busca semântica, KPIs e dashboard          | ⏳ próxima etapa |

## Estrutura do projeto

```
desafio_dados/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── config/
│   └── config.yaml
├── dados/
│   ├── brutos/            # arquivos de entrada originais (nunca alterados)
│   └── processados/       # gerado pela execução do pipeline
├── logs/                  # gerado pela execução do pipeline
├── sql/
│   ├── criar_banco.sql    # schema do PostgreSQL (RF06 / RF11)
│   └── consultas.sql      # consultas de apoio
├── mongodb/
│   └── consultas.js       # consultas de apoio no MongoDB (RF07)
├── documentacao/
│   ├── modelo_de_dados.md
│   └── uso_da_ia.md       # registro de uso de IA (seção 10 do edital)
└── src/
    ├── main.py            # ponto de entrada do pipeline (python -m src.main)
    ├── config.py          # carregamento de config.yaml + .env
    ├── logger.py
    ├── leitura/           # RF02
    ├── validacao/         # RF03
    ├── tratamento/        # RF04
    ├── resumo/            # RF05
    ├── saida/             # gravação dos dados tratados/rejeitados
    ├── persistencia/      # RF06 (PostgreSQL) e RF07 (MongoDB)
    └── recomendacao/      # RF10 e RF11 (motor.py)
```

## Dados de entrada

Os arquivos reais fornecidos para o desafio já estão em
`dados/brutos/`, com os nomes esperados pelo `config/config.yaml`:

- `catalogo.csv`
- `interacoes.json`
- `comentarios.json`

> Não há uma fonte separada de "usuários" com nome/e-mail: a entidade
> `usuarios` no PostgreSQL é derivada dos `usuario_id` encontrados nas
> interações e nos comentários (ver `documentacao/modelo_de_dados.md`).

## Como executar

### 1. Pré-requisitos

- Python 3.11+
- Docker (opcional, para subir o PostgreSQL local rapidamente)

### 2. Instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env com usuário/senha/host do PostgreSQL
```

### 4. Subir o PostgreSQL e o MongoDB (opcional, via Docker)

```bash
docker compose up -d postgres mongo
```

### 5. Executar o pipeline de ingestão e o motor de recomendação

```bash
# Executa a ingestão e tratamento dos dados
python -m src.main

# Executa a geração e persistência das recomendações (RF10 e RF11)
python -m src.recomendacao.motor
```

O sistema irá:
1. ler as três fontes de dados e informar a quantidade de registros de cada uma;
2. validar cada registro (válido / inválido / incompleto / duplicado);
3. tratar e padronizar os registros válidos;
4. gravar em `dados/processados/`: dados tratados, registros rejeitados (com motivo) e o resumo da ingestão;
5. aplicar o schema e carregar os dados no PostgreSQL, dentro de transações;
6. carregar os comentários/avaliações no MongoDB (coleção `comentarios_avaliacoes`), evitando duplicidade em reexecuções;
7. calcular as pontuações de recomendação personalizadas ($I_{vis}$, $I_{cur}$, $I_{conc}$) e persistir a ordenação/status na tabela `recomendacoes` no PostgreSQL;
8. registrar cada etapa em `logs/execucao.log`.

> **Nenhuma saída é versionada no repositório**: os arquivos em
> `dados/processados/` e `logs/` são gerados pela execução do
> pipeline (ver `.gitignore`).

## Decisões de tratamento (RF04)

- espaços nas extremidades de campos textuais são removidos;
- `tipo`, `nivel` e `tags` são normalizados (minúsculas, sem acentos);
- datas são convertidas para o formato ISO;
- campos numéricos são convertidos para `int`/`float`;
- valores ausentes em campos não obrigatórios são preservados como
  nulos (não são inventados);
- duplicidades são identificadas por chave de negócio (ex.:
  `usuario_id + conteudo_id + tipo_interacao + data_hora` para
  interações) e descartadas na carga.

## Consultas de exemplo

- PostgreSQL: ver `sql/consultas.sql` (contagem por tabela, conteúdos por categoria, interações por tipo, avaliação média, usuários mais ativos, taxa de conclusão e recomendações).
- MongoDB: ver `mongodb/consultas.js` (comentários por conteúdo, busca por tag, filtro por nota, agregação por categoria).

