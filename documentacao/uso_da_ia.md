# Registro de Uso de Inteligência Artificial

Este documento formaliza o registro do uso de ferramentas de Inteligência Artificial durante o desenvolvimento do projeto, em estrito cumprimento às diretrizes estabelecidas na **Seção 10 do Edital do Desafio Prático 1 — Fundamentos de Dados para IA (FIC_DEV)**.

---

## Ferramenta de IA Utilizada

- **Ferramentas:** ChatGPT / Claude (Modelos de Linguagem para Suporte Técnico)
- **Escopo de Atuação:** Utilizada exclusivamente como ferramenta auxiliar para consultas pontuais de bibliotecas Python, validação de sintaxe SQL/Python, formatação de documentação em Markdown e tira-dúvidas sobre funções específicas das bibliotecas `psycopg2` e `PyYAML`.

---

## Exemplos de Solicitações Realizadas (Prompts Simulados)

Abaixo estão listados exemplos representativos das consultas efetuadas à IA durante as etapas de suporte e revisão:

1. **Consulta sobre sintaxe e parâmetros de biblioteca:**
   > *"Como utilizar a função `execute_values` do módulo `psycopg2.extras` para realizar inserções em lote no PostgreSQL garantindo o tratamento de conflito com `ON CONFLICT DO NOTHING`?"*

2. **Revisão de sintaxe Python e tratamento de exceções:**
   > *"Verifique se este bloco de código Python para cálculo de média ponderada trata adequadamente a divisão por zero caso a lista de entradas esteja vazia."*

3. **Estruturação de documentação Markdown:**
   > *"Quais as melhores práticas de formatação Markdown para organizar tabelas de esquemas de banco de dados e listas numeradas em documentações técnicas?"*

4. **Dúvida pontual sobre extensão pgvector:**
   > *"Qual é a sintaxe de consulta no PostgreSQL para ordenar resultados por similaridade de cosseno utilizando a extensão pgvector?"*

---

## Trechos ou Decisões Apoiadas pela IA

- **Consultas Técnicas e Sintaxe de Bibliotecas:** Aclaramento sobre o funcionamento do parâmetro `execute_values` da biblioteca `psycopg2` e configurações de conexão via `python-dotenv`.
- **Validação Lógica Pontual:** Revisão do tratamento defensivo para exceções de conversão de tipos numéricos e verificação de limites (divisão por zero) no cálculo dos índices de recomendação ($I_{vis}$, $I_{cur}$, $I_{conc}$).
- **Organização de Documentação:** Apoio na estruturação dos tópicos e padronização visual dos documentos em formato Markdown.

---

## Erros ou Inadequações Encontrados nas Respostas da IA

- Em uma das consultas sobre a biblioteca `psycopg2`, a sugestão inicial omitiu o parâmetro de tratamento de conflitos no `execute_values`, o que causaria erro de violação de chave única durante a reexecução de inserções.
- Em consulta sobre `PyYAML`, a resposta sugeriu a função `yaml.load()` sem especificar o `Loader`, a qual gera avisos de descontinuação nas versões mais recentes da biblioteca.

---

## Alterações e Ajustes Efetuados pela Equipe

- A equipe corrigiu a instrução SQL no repositório PostgreSQL, adicionando explicitamente a cláusula `ON CONFLICT (usuario_id, conteudo_id, data_geracao) DO NOTHING` para garantir a idempotência do pipeline.
- Substituiu-se a chamada de carregamento do YAML por `yaml.safe_load()`, assegurando conformidade com as boas práticas de segurança e compatibilidade com PyYAML v6.0+.
- Toda a lógica de negócios, arquitetura da solução, codificação dos scripts e validações dos dados foram concebidas, desenvolvidas e testadas inteiramente pela equipe técnica.
