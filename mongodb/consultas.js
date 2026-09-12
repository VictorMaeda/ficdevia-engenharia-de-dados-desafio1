// ============================================================
// Consultas de apoio - RF07 (MongoDB)
// Banco: desafio_dados | Coleção: comentarios_avaliacoes
//
// Uso (mongosh):
//   mongosh "mongodb://localhost:27017/desafio_dados" mongodb/consultas.js
// ou copie/cole os comandos abaixo em um shell já conectado ao banco.
// ============================================================

// Selecionar o banco
use("desafio_dados");

// ------------------------------------------------------------
// Inserir um documento (exemplo — a carga real é feita pelo pipeline
// Python, em src/persistencia/mongo_repo.py::inserir_documentos)
// ------------------------------------------------------------
db.comentarios_avaliacoes.updateOne(
  { usuario_id: 104, conteudo_id: 28, data: "2026-08-20" },
  {
    $setOnInsert: {
      usuario_id: 104,
      conteudo_id: 28,
      avaliacao: 5,
      comentario: "Conteudo introdutorio, claro e objetivo.",
      tags: ["didatico", "iniciante", "python"],
      data: "2026-08-20",
      categoria: "Engenharia de Dados",
    },
  },
  { upsert: true }
);

// ------------------------------------------------------------
// Consultar comentários de um determinado conteúdo
// ------------------------------------------------------------
db.comentarios_avaliacoes.find({ conteudo_id: 28 });

// ------------------------------------------------------------
// Localizar documentos por tag
// ------------------------------------------------------------
db.comentarios_avaliacoes.find({ tags: "iniciante" });

// ------------------------------------------------------------
// Filtrar avaliações pela nota (ex.: nota >= 4)
// ------------------------------------------------------------
db.comentarios_avaliacoes.find({ avaliacao: { $gte: 4 } });

// Filtrar por uma nota exata
db.comentarios_avaliacoes.find({ avaliacao: 5 });

// ------------------------------------------------------------
// Agregar a quantidade de comentários/avaliações por categoria
// ------------------------------------------------------------
db.comentarios_avaliacoes.aggregate([
  { $group: { _id: "$categoria", quantidade: { $sum: 1 } } },
  { $sort: { quantidade: -1 } },
  { $project: { _id: 0, categoria: "$_id", quantidade: 1 } },
]);

// ------------------------------------------------------------
// Extras úteis
// ------------------------------------------------------------

// Avaliação média por conteúdo
db.comentarios_avaliacoes.aggregate([
  { $group: { _id: "$conteudo_id", media: { $avg: "$avaliacao" }, qtd: { $sum: 1 } } },
  { $sort: { media: -1 } },
  { $limit: 10 },
]);

// Quantidade total de documentos na coleção
db.comentarios_avaliacoes.countDocuments({});

// Índices existentes na coleção (criados por src/persistencia/mongo_repo.py)
db.comentarios_avaliacoes.getIndexes();
