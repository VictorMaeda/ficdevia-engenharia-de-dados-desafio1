# Apache Superset — Dashboard de Conteúdos Educacionais

Este documento descreve a configuração, execução e estrutura do dashboard desenvolvido no Apache Superset para o projeto **Pipeline de Recomendação e Dashboard de Conteúdos Educacionais**.

O dashboard utiliza dados persistidos no PostgreSQL e preparados por meio de views analíticas específicas para consumo no Superset.

---

## 1. Objetivo

O dashboard foi desenvolvido para disponibilizar uma visão analítica dos conteúdos educacionais, permitindo acompanhar:

- volume de usuários e interações;
- taxa de conclusão dos conteúdos;
- avaliação média;
- distribuição das avaliações;
- evolução temporal das interações;
- comportamento por categoria;
- relação entre engajamento e conclusão.

Também foram incluídos filtros interativos para permitir diferentes recortes dos dados.

---

## 2. Arquitetura Utilizada

A estrutura utilizada para a execução local é:

```text
Docker Compose
│
├── PostgreSQL
│   └── Banco: desafio_dados
│
├── MongoDB
│
├── PostgreSQL de metadados do Superset
│   └── Banco interno do Superset
│
└── Apache Superset
    └── Dashboard de Conteúdos Educacionais
```

O PostgreSQL principal do projeto e o Superset são executados na mesma rede Docker.

Por esse motivo, dentro do Superset, o serviço PostgreSQL principal é acessado pelo hostname:

```text
postgres
```

e não por:

```text
localhost
```

---

## 3. Pré-requisitos

Para executar o ambiente são necessários:

- Docker Desktop;
- Docker Compose;
- arquivo `.env` configurado;
- portas locais disponíveis:
  - PostgreSQL: `5432`;
  - MongoDB: `27017`;
  - Superset: `8088`.

---

## 4. Variáveis de Ambiente

O arquivo `.env.example` contém exemplos das variáveis utilizadas.

As principais variáveis relacionadas ao Superset são:

```env
SUPERSET_PORT=8088

SUPERSET_META_DB=superset
SUPERSET_META_USER=superset
SUPERSET_META_PASSWORD=troque_esta_senha

SUPERSET_SECRET_KEY=troque_esta_chave_por_uma_chave_aleatoria

SUPERSET_ADMIN_USERNAME=admin
SUPERSET_ADMIN_PASSWORD=troque_esta_senha
SUPERSET_ADMIN_FIRSTNAME=Admin
SUPERSET_ADMIN_LASTNAME=Superset
SUPERSET_ADMIN_EMAIL=admin@example.com
```

O arquivo `.env` real não deve ser versionado.

A chave secreta pode ser gerada localmente com:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 5. Subindo o Ambiente

Na raiz do projeto:

```powershell
docker compose up -d postgres mongo superset_meta_db
```

Depois, caso seja a primeira execução do Superset, é necessário inicializar seu banco interno.

### 5.1 Aplicar as migrations

```powershell
docker compose run --rm superset superset db upgrade
```

### 5.2 Criar o usuário administrador

Exemplo:

```powershell
docker compose run --rm superset superset fab create-admin `
  --username admin `
  --firstname Admin `
  --lastname Superset `
  --email admin@example.com `
  --password admin
```

A senha utilizada deve ser definida de acordo com o ambiente local.

### 5.3 Inicializar permissões e roles

```powershell
docker compose run --rm superset superset init
```

### 5.4 Subir o Superset

```powershell
docker compose up -d superset
```

Para verificar os serviços:

```powershell
docker compose ps
```

---

## 6. Acesso ao Superset

Após a inicialização, o Superset pode ser acessado em:

```text
http://localhost:8088
```

O login deve utilizar o usuário administrador criado na etapa de inicialização.

---

## 7. Conexão com o PostgreSQL

Dentro do Superset foi criada uma conexão com o banco principal do projeto.

Configuração utilizada:

```text
Display Name: Desafio Dados
Host: postgres
Port: 5432
Database: desafio_dados
Username: desafio_user
Password: definida no arquivo .env
```

O hostname `postgres` corresponde ao nome do serviço definido no `docker-compose.yml`.

---

## 8. Views Analíticas

As views utilizadas pelo Superset estão definidas em:

```text
sql/views_dashboard.sql
```

Foram criadas as seguintes views:

### `vw_metricas_dashboard`

Disponibiliza os principais indicadores globais:

- total de usuários;
- total de conteúdos;
- total de interações;
- conteúdos com interação;
- total de avaliações;
- total de recomendações;
- pares usuário/conteúdo;
- pares concluídos;
- taxa de conclusão;
- avaliação média;
- taxa de avaliações positivas.

---

### `vw_interacoes_dashboard`

View principal para análises de interação.

Contém informações como:

- usuário;
- conteúdo;
- categoria;
- tipo;
- nível;
- tipo de interação;
- data da interação;
- tempo consumido;
- percentual de conclusão.

É utilizada para análises de:

- interações por categoria;
- evolução temporal;
- filtros por categoria, tipo e nível.

---

### `vw_avaliacoes_dashboard`

View preparada para análises de satisfação.

Contém:

- usuário;
- conteúdo;
- categoria;
- tipo;
- nível;
- nota;
- data da avaliação;
- indicador de avaliação positiva.

É utilizada principalmente na distribuição das notas.

---

### `vw_desempenho_categoria`

View agregada por categoria.

Contém:

- total de conteúdos;
- conteúdos com interação;
- total de interações;
- usuários distintos;
- pares usuário/conteúdo;
- pares concluídos;
- taxa de conclusão;
- total de avaliações;
- avaliação média;
- taxa de avaliações positivas.

É utilizada para análises cruzadas de desempenho por categoria.

---

### `vw_recomendacoes_dashboard`

View preparada para consumo dos resultados do motor de recomendação.

Contém:

- usuário;
- conteúdo;
- título;
- categoria;
- tipo;
- nível;
- pontuação;
- posição;
- status;
- data de geração.

Essa view passa a retornar dados após a execução da etapa de recomendação.

---

## 9. Datasets do Superset

Foram cadastrados os seguintes datasets:

```text
vw_metricas_dashboard
vw_interacoes_dashboard
vw_avaliacoes_dashboard
vw_desempenho_categoria
```

A view de recomendações poderá ser cadastrada após a disponibilização dos dados da etapa de recomendação.

---

## 10. Dashboard

Nome:

```text
Dashboard de Conteúdos Educacionais
```

O dashboard foi publicado no Superset após sua validação.

---

## 11. Métricas e KPIs

Os detalhes completos das métricas e KPIs estão documentados em:

```text
documentacao/kpis.md
```

Os principais indicadores exibidos são:

### Total de Usuários

Quantidade total de usuários persistidos no PostgreSQL.

Valor de referência:

```text
150
```

### Total de Interações

Quantidade total de interações registradas.

Valor de referência:

```text
1.000
```

### Taxa de Conclusão

Percentual de pares distintos usuário/conteúdo que atingiram 100% de conclusão.

Valor de referência:

```text
15,43%
```

### Avaliação Média

Média das notas registradas.

Valor de referência:

```text
4,15 / 5
```

---

## 12. Visualizações

### 12.1 Interações por Categoria

Gráfico de barras horizontal que apresenta a quantidade total de interações em cada categoria.

Permite identificar quais áreas apresentam maior volume de atividade.

---

### 12.2 Evolução Mensal das Interações

Gráfico de linha que apresenta a evolução das interações ao longo dos meses.

Permite observar crescimento, queda ou variações no consumo da plataforma.

---

### 12.3 Distribuição de Notas (1–5) por Categoria

Gráfico de barras horizontais 100% empilhadas.

Cada categoria apresenta sua distribuição percentual entre:

```text
1
2
3
4
5
```

As notas são apresentadas em ordem crescente, facilitando a leitura da progressão entre avaliações negativas e positivas.

O uso da distribuição permite enxergar diferenças que não seriam visíveis utilizando apenas a média das notas.

---

### 12.4 Engajamento × Conclusão por Categoria

Gráfico de dispersão que cruza:

```text
Eixo X: total de interações
Eixo Y: taxa de conclusão
Dimensão: categoria
```

O objetivo é analisar simultaneamente o volume de atividade e a capacidade de conclusão dos conteúdos de cada categoria.

---

## 13. Filtros Interativos

Foram implementados os seguintes filtros:

### Categoria

Permite selecionar uma ou mais categorias.

### Tipo de Conteúdo

Permite filtrar por tipo de conteúdo, como:

```text
curso
artigo
vídeo
podcast
```

### Nível

Permite selecionar:

```text
básico
intermediário
avançado
```

Os filtros atuam sobre os gráficos analíticos compatíveis.

Os cards superiores permanecem globais e representam os indicadores gerais da base.

---

## 14. Organização do Dashboard

O dashboard foi organizado em três áreas principais:

### Visão Geral

Apresenta os principais indicadores da plataforma:

- total de usuários;
- total de interações;
- taxa de conclusão;
- avaliação média.

### Engajamento

Apresenta:

- interações por categoria;
- evolução mensal das interações.

### Qualidade e Insights

Apresenta:

- distribuição das avaliações;
- relação entre engajamento e conclusão.

---

## 15. Principais Insights

A análise atual permite destacar alguns padrões.

### Programação & Software

Apresenta o menor volume de interações entre as categorias analisadas, mas possui a maior taxa de conclusão.

Isso indica que, embora tenha menor volume de acesso, os usuários que interagem com esses conteúdos apresentam maior tendência de conclusão.

---

### DevOps & Cloud

Apresenta volume elevado de interações e uma das maiores taxas de conclusão.

Por outro lado, a distribuição de avaliações apresenta desempenho inferior às categorias mais bem avaliadas.

Esse comportamento sugere que os conteúdos possuem relevância e engajamento, mas podem existir oportunidades de melhoria na percepção de qualidade.

---

### Segurança & Governança

Apresenta taxa de conclusão significativamente inferior às demais categorias.

Esse comportamento pode indicar:

- maior dificuldade;
- menor aderência dos conteúdos;
- conteúdos mais extensos;
- necessidade de revisão da experiência de aprendizagem.

Esse resultado pode ser utilizado como ponto de partida para investigação adicional.

---

### Ciência de Dados

Apresenta uma das melhores percepções de qualidade segundo as avaliações dos usuários.

Entretanto, sua taxa de conclusão não está entre as maiores.

Isso demonstra que satisfação e conclusão não necessariamente apresentam o mesmo comportamento.

---

## 16. Exportação

A exportação oficial do dashboard está armazenada em:

```text
dashboard/exportacao/dashboard_conteudos_educacionais.zip
```

O ZIP foi gerado utilizando:

```text
Dashboard
→ Download
→ Export YAML
```

O pacote contém definições de:

```text
dashboard
charts
datasets
database
metadata
```

e pode ser utilizado para importação em outra instalação compatível do Apache Superset.

---

## 17. Evidências

As evidências visuais estão disponíveis em:

```text
dashboard/evidencias/dashboard_conteudos_educacionais.jpg
dashboard/evidencias/dashboard_conteudos_educacionais.pdf
```

A imagem pode ser utilizada no README e em documentação.

O PDF fornece uma versão completa do dashboard para consulta ou apresentação.

---

## 18. Importação do Dashboard

Para restaurar o dashboard em outra instalação do Superset:

1. iniciar o Superset;
2. configurar o acesso ao PostgreSQL;
3. acessar a opção de importação do Superset;
4. selecionar:

```text
dashboard/exportacao/dashboard_conteudos_educacionais.zip
```

5. confirmar as configurações da conexão;
6. validar os datasets e gráficos importados.

As credenciais reais do banco não devem ser versionadas no repositório.

---

## 19. Recomendações

A tabela e a view de recomendações já estão previstas na arquitetura:

```text
recomendacoes
vw_recomendacoes_dashboard
```

Após a execução do motor de recomendação será possível incluir análises adicionais, como:

- total de recomendações;
- pontuação média;
- recomendações por categoria;
- distribuição por status;
- conteúdos mais recomendados.

Essa integração pode ser realizada sem alterar as visualizações atuais do dashboard.

---

## 20. Arquivos Relacionados

```text
docker-compose.yml
.env.example
superset/Dockerfile
superset/superset_config.py
sql/consultas.sql
sql/views_dashboard.sql
documentacao/kpis.md
documentacao/superset.md
dashboard/exportacao/dashboard_conteudos_educacionais.zip
dashboard/evidencias/dashboard_conteudos_educacionais.jpg
dashboard/evidencias/dashboard_conteudos_educacionais.pdf
```