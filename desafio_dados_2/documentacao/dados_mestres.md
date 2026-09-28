# RF30 — Gestão de Dados Mestres (Master Data Management - MDM)

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Visão Geral da Entidade Mestre

No contexto do ecossistema educacional do projeto, a entidade central escolhida para a disciplina de **Dados Mestres (MDM)** é o **Conteúdo Educacional** (`Conteúdo`).

Esta entidade é referenciada transversalmente por:
* Catálogo de cursos e trilhas formativas;
* Eventos de interação e consumo dos alunos;
* Sessões de avaliação e comentários didáticos;
* Modelos preditivos e motores de recomendação;
* Painéis executivos de retenção escolar na Camada Gold.

---

## 2. Definição da Chave de Negócio e Atributos Essenciais

```text
┌─────────────────────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Parâmetro MDM                   │ Especificação Técnica e Negocial                                       │
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Entidade Mestre                 │ Conteúdo Educacional (Course / Educational Asset)                      │
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Chave de Negócio Natural        │ Normalização de (titulo_slug + autor_id + tipo)                        │
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Identificador Mestre (Golden ID)│ conteudo_id (Chave substituta unificada gerada em silver.catalogo)     │
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Fonte de Referência Primária    │ Sistema de Catálogo Acadêmico (dados/entrada/catalogo.csv)              │
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Atributos Essenciais            │ • titulo: Título oficial do conteúdo                                   │
│                                 │ • tipo: Formato instrucional (video, curso, podcast, artigo)           │
│                                 │ • categoria: Área temática do conhecimento                             │
│                                 │ • nivel: Complexidade pedagógica (basico, intermediario, avancado)     │
│                                 │ • data_publicacao: Data canônica de disponibilização                   │
│                                 │ • autor: Docente / Autor responsável                                   │
└─────────────────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Regras de Correspondência, Deduplicação e Sobrevivência (Survivorship)

Para resolver inconsistências decorrentes da ingestão de múltiplas fontes ou cadastros duplicados, o pipeline aplica as seguintes regras determinísticas na transição Bronze $\rightarrow$ Silver:

### 3.1. Regra de Correspondência (Matching)
1. **Correspondência Exata:** Se `conteudo_id` for idêntico.
2. **Correspondência Fuzzy / Fonética:** Similaridade textual $\ge 95\%$ no título padronizado (caixa baixa, remoção de acentos e caracteres especiais) associada ao mesmo autor e tipo de mídia.

### 3.2. Regra de Sobrevivência (Survivorship Rule)
Quando dois ou mais registros representam a mesma entidade de negócio com divergência de valores:
* **Título e Descrição:** Prevalece o registro com maior completude de caracteres (não nulo mais detalhado).
* **Categoria e Nível:** Prevalece a classificação mais recente (`data_publicacao` mais recente) originada do sistema acadêmico mestre.
* **Carga Horária:** Prevalece o valor numérico positivo não nulo verificado.
* **Chave Mestre Atribuída:** O menor `conteudo_id` original é preservado como *Golden Record*, e as ocorrências secundárias são unificadas na tabela de correspondência (*Cross-Reference / XRef*).

---

## 4. Demonstração Prática de Resolução de Conflito

Considere dois registros conflitantes recebidos na ingestão:

```text
REGISTRO A (Fonte: CSV Catálogo Antigo):
{
  "conteudo_id": 105,
  "titulo": "Pipelines e Transformações com Apache Hop",
  "tipo": "video",
  "categoria": "Engenharia de Dados",
  "nivel": "basico",
  "data_publicacao": "2025-01-10",
  "autor": "Carlos Eduardo"
}

REGISTRO B (Fonte: Cadastro Recente de Plataforma LMS):
{
  "conteudo_id": 892,
  "titulo": "Pipelines e Transformacoes com Apache Hop - Edição 2026",
  "tipo": "video",
  "categoria": "Data Engineering",
  "nivel": "intermediario",
  "data_publicacao": "2026-02-15",
  "autor": "Prof. Carlos Eduardo Silveira"
}
```

### Aplicação das Regras MDM no Pipeline:

1. **Correspondência:** O motor detecta similaridade de $92\%$ no título e equivalência do autor (`Carlos Eduardo` $\subset$ `Carlos Eduardo Silveira`).
2. **Sobrevivência:**
   * **Título Canônico:** `Pipelines e Transformações com Apache Hop - Edição 2026` (mais descritivo e atualizado).
   * **Categoria Padronizada:** `Engenharia de Dados` (mapeada a partir da taxonomia do glossário da Silver).
   * **Nível:** `intermediario` (registro mais recente de 2026).
   * **Golden ID Definido:** `conteudo_id = 105`.
3. **Registro Golden Consolidado na Camada Silver (`silver.catalogo`):**
   ```json
   {
     "conteudo_id": 105,
     "titulo": "Pipelines e Transformações com Apache Hop - Edição 2026",
     "tipo": "video",
     "categoria": "Engenharia de Dados",
     "nivel": "intermediario",
     "data_publicacao": "2026-02-15",
     "autor": "Prof. Carlos Eduardo Silveira",
     "origem_principal": "golden_record_mdm"
   }
   ```
4. **Tabela de De-Para (XRef):** Qualquer interação ou comentário associado originalmente ao `conteudo_id = 892` é automaticamente remapeado para `105`, impedindo fragmentação métrica na Camada Gold.
