# Modelo de Dados — Etapa até o PostgreSQL

> Preencher/ajustar com o diagrama final (DER) da equipe. Este arquivo
> descreve o modelo lógico implementado em `sql/criar_banco.sql`.

## Entidades

| Entidade             | Descrição                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `categorias`         | Áreas temáticas dos conteúdos (derivadas do catálogo).                     |
| `usuarios`           | Identificadores de usuário observados nas interações/comentários.          |
| `conteudos`          | Catálogo de conteúdos educacionais (cursos, vídeos, artigos, podcasts).     |
| `interacoes`         | Eventos de consumo (visualização, início, conclusão, curtida etc.).        |
| `avaliacoes_resumo`  | Resumo relacional das avaliações/comentários no PostgreSQL (contagens e joins simples). O documento completo — com texto, tags e a categoria denormalizada — fica no MongoDB (coleção `comentarios_avaliacoes`). |
| `recomendacoes`      | Reservada para a próxima etapa do desafio (RF10/RF11).                     |

## Observação importante sobre `usuarios`

As fontes de dados fornecidas (`interacoes.json` e
`comentarios.json`) trazem apenas o identificador do
usuário — não há um cadastro com nome, e-mail etc. Por isso a entidade
`usuarios` é **derivada**: cada `usuario_id` observado gera uma linha,
com `primeira_ocorrencia` (data/hora do primeiro registro em que o
usuário aparece) e `origem_primeiro_registro` (`interacao` ou
`comentario`).

## Relacionamentos

- `conteudos.categoria_id` → `categorias.categoria_id`
- `interacoes.usuario_id` → `usuarios.usuario_id`
- `interacoes.conteudo_id` → `conteudos.conteudo_id`
- `avaliacoes_resumo.usuario_id` → `usuarios.usuario_id`
- `avaliacoes_resumo.conteudo_id` → `conteudos.conteudo_id`
- `recomendacoes.usuario_id` → `usuarios.usuario_id`
- `recomendacoes.conteudo_id` → `conteudos.conteudo_id`

## Diagrama (a incluir)

Adicionar aqui o diagrama entidade-relacionamento (pode ser exportado
de uma ferramenta como dbdiagram.io, draw.io etc.) e um `modelo_de_dados.pdf`
correspondente, conforme pedido nos entregáveis do desafio.

## MongoDB — coleção `comentarios_avaliacoes` (RF07)

Cada documento representa um comentário/avaliação de um usuário sobre
um conteúdo, no formato:

```json
{
  "usuario_id": 104,
  "conteudo_id": 28,
  "avaliacao": 5,
  "comentario": "Conteúdo introdutório, claro e objetivo.",
  "tags": ["didatico", "iniciante", "python"],
  "data": "2026-08-20",
  "categoria": "Engenharia de Dados"
}
```

**Por que MongoDB e não apenas PostgreSQL?** O documento tem uma
estrutura semiestruturada — texto livre (`comentario`) e uma lista de
tamanho variável (`tags`) — que se encaixa naturalmente em um modelo
de documento, sem exigir uma tabela extra de tags/relacionamento N:N
para o mesmo propósito. O PostgreSQL guarda apenas o **resumo
relacional** (`avaliacoes_resumo`: usuário, conteúdo, nota, data),
suficiente para joins e KPIs; o MongoDB guarda o **documento
completo**, otimizado para buscas por tag, filtro por nota e leitura
do texto do comentário.

**Por que denormalizar `categoria` no documento?** Isso evita que a
consulta de agregação por categoria (RF07) precise recorrer ao
PostgreSQL a cada execução — o preço é manter a categoria atualizada
caso ela mude no catálogo (aceitável neste escopo, dado que o
catálogo é reprocessado a cada execução do pipeline).

Índices criados (ver `src/persistencia/mongo_repo.py`):
- único em `(usuario_id, conteudo_id, data)` — evita duplicidade em reexecuções;
- `conteudo_id`, `tags`, `avaliacao`, `categoria` — para as consultas exigidas pelo RF07.
