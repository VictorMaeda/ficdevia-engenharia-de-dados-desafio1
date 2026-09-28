# RF32 — Inventário de Dados Pessoais e Conformidade com a LGPD

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral e Princípios de Proteção de Dados

A arquitetura do pipeline educacional foi desenhada em estrita aderência à **Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 - LGPD)**, guiando-se pelos princípios da **finalidade**, **adequação**, **necessidade (minimização de dados)** e **segurança**.

Para garantir governança integral:
1. **Dados Estritamente Fictícios:** Toda a base de dados utiliza registros sintéticos; nenhum dado pessoal de titular real foi ingerido ou processado.
2. **Minimização na Camada Gold:** A camada de consumo analítico (Superset) é desprovida de qualquer dado pessoal identificável direto (`nome`, `e-mail`, `documento`). Apenas métricas agregadas por `conteudo_id`, `categoria` e identificadores pseudonimizados transitam para o consumo da diretoria acadêmica.
3. **Mapeamento e Classificação:** Todos os atributos pessoais foram inventariados e classificados tecnicamente no catálogo de metadados.

---

## 2. Inventário de Atributos e Avaliação de Impacto (ROPA)

```text
┌──────────────────┬─────────────────┬──────────────────────┬──────────────────────┬────────────────────────────────┬──────────────────────────┬─────────────────┬───────────┐
│ Campo            │ Tabela de Origem│ Classificação LGPD   │ Finalidade Negocial  │ Base Legal (Art. 7º LGPD)      │ Nível de Acesso          │ Retenção        │ Proteção  │
├──────────────────┼─────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────┼──────────────────────────┼─────────────────┼───────────┤
│ usuario_id       │ interacoes      │ Identificador        │ Rastrear sessões de  │ Execução de Contrato           │ Engenharia de Dados      │ 5 anos após     │ Pseudoni- │
│                  │ comentarios     │ Indireto (PII)       │ aprendizagem e nota  │ (Art. 7º, V)                   │ (Restrito / Chave)       │ encerramento    │ mização   │
├──────────────────┼─────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────┼──────────────────────────┼─────────────────┼───────────┤
│ autor            │ catalogo        │ Dado Pessoal         │ Atribuição de crédito│ Execução de Contrato /         │ Público / Consumo        │ Vitalício ao    │ Mascara-  │
│                  │                 │ Direto (PII)         │ de autoria docente   │ Legítimo Interesse             │ Acadêmico                │ conteúdo        │ mento Par.│
├──────────────────┼─────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────┼──────────────────────────┼─────────────────┼───────────┤
│ comentario       │ comentarios     │ Dado Não Estruturado │ Coletar feedback     │ Consentimento /                │ Docentes / Coordenação   │ 2 anos após     │ Hashing   │
│                  │                 │ (Potencial Sensível) │ didático e dúvidas   │ Legítimo Interesse             │ de Curso                 │ publicação      │ SHA-256   │
├──────────────────┼─────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────┼──────────────────────────┼─────────────────┼───────────┤
│ avaliacao        │ comentarios     │ Dado Comportamental  │ Medir satisfação com │ Legítimo Interesse             │ Analistas de Dados       │ 3 anos          │ Agregação │
│                  │ interacoes      │ (Opinião / Feedback) │ a metodologia        │ (Art. 7º, IX)                  │ e Pedagogia              │ na Gold         │ Estatística│
├──────────────────┼─────────────────┼──────────────────────┼──────────────────────┼────────────────────────────────┼──────────────────────────┼─────────────────┼───────────┤
│ data_hora        │ interacoes      │ Dado Temporal        │ Auditoria de acessos │ Cumprimento de Obrigação Legal │ Engenharia de Dados      │ 6 meses (Marco  │ Truncamento│
│                  │                 │ e consumo            │ e segurança          │ (Marco Civil / Art. 7º, II)    │ e Segurança da Info      │ Civil da Internet) mensal |
└──────────────────┴─────────────────┴──────────────────────┴──────────────────────┴────────────────────────────────┴──────────────────────────┴─────────────────┴───────────┘
```

---

## 3. Diretrizes de Ciclo de Vida e Minimização

1. **Camada Bronze:** Mantém os dados brutos ingeridos com retenção de segurança em esquema segregado, acessível estritamente por pipelines com credenciais de serviço.
2. **Camada Silver:** Aplica técnicas ativas de **Pseudonimização** e **Mascaramento** durante o processamento Apache Hop. Registros contendo valores fora de padrão ou potenciais violações são segregados na **Quarentena**.
3. **Camada Gold:** Nenhuma coluna de dados pessoais diretos é persistida. Todas as entidades analíticas operam sobre `conteudo_id` e métricas sumarizadas (`total_interacoes`, `quantidade_conclusoes`, `taxa_conclusao_pct`).
4. **Governança no OpenMetadata:** Todos os campos classificados como PII recebem a tag de governança `TIER.Tier1` e classificação `PII.Sensitive` ou `PII.NonSensitive`, garantindo visibilidade institucional dos fluxos de dados pessoais.
