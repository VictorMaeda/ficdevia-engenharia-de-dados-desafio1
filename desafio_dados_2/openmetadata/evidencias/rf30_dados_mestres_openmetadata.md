# RF30 — Gestão de Dados Mestres (MDM) no OpenMetadata

**Programa:** FIC DEV IA — Programador de Sistemas com IA  
**Módulo:** Fundamentos de Dados para IA  
**Projeto:** Pipeline Governado, Escalável e Seguro de Conteúdos Educacionais  

---

## 1. Entidade Mestre: Conteúdo Educacional

A disciplina de **Master Data Management (MDM)** da plataforma FIC DEV IA define o **Conteúdo Educacional** como a entidade mestre central do ecossistema de dados.

| Parâmetro MDM | Especificação |
|:---|:---|
| **Nome da Entidade** | `ConteudoEducacional` |
| **Tabela Master (Golden Store)** | `silver.catalogo` |
| **Serviço OpenMetadata** | `pg_desafio2_service` |
| **FQN Completo** | `pg_desafio2_service.desafio_dados.silver.catalogo` |
| **Golden ID (PK Mestre)** | `conteudo_id` (surrogate key) |
| **Chave Natural de Negócio** | `hash(titulo_normalizado + autor_id + tipo_midia)` |
| **Steward Responsável** | Coordenação Pedagógica (`pedagogico@ficdevia.edu.br`) |

---

## 2. Atributos Essenciais e Papéis MDM

Cada coluna da tabela mestre `silver.catalogo` recebe uma **descrição de papel MDM** publicada no catálogo do OpenMetadata via API:

| Coluna | Tipo | Papel MDM | Obrigatório | Classificação LGPD |
|:---|:---|:---|:---:|:---|
| `conteudo_id` | integer | **Golden ID** | ✅ | — |
| `titulo` | varchar | **Atributo Master** | ✅ | — |
| `tipo` | varchar | **Atributo Master** | ✅ | — |
| `categoria` | varchar | **Atributo Master** | ✅ | — |
| `nivel` | varchar | **Atributo Master** | ✅ | — |
| `data_publicacao` | date | **Atributo Master** | ✅ | — |
| `autor` | varchar | **PII — Mascarado** | ❌ | `PII.Identifiable` |

---

## 3. Custom Properties Registradas no OpenMetadata

Para que o catálogo do OpenMetadata suporte a gestão MDM, foram criadas **4 Custom Properties** vinculadas ao tipo de entidade `table`:

```text
┌─────────────────────────────┬────────────────────────────────────────────────────────────────┐
│ Custom Property             │ Descrição / Propósito                                           │
├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ mdm_is_golden_record        │ Boolean: indica se a tabela hospeda o Golden Record MDM         │
├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ mdm_golden_id               │ Integer: conteudo_id canônico atribuído pelo processo MDM       │
├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ mdm_steward                 │ String: e-mail do responsável pela curadoria da entidade mestre │
├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ mdm_survivorship_rule       │ Markdown: regras de sobrevivência para resolução de conflitos   │
└─────────────────────────────┴────────────────────────────────────────────────────────────────┘
```

Script de execução:
```bash
python desafio_dados_2/openmetadata/registrar_dados_mestres_openmetadata.py
```

---

## 4. Regras de Correspondência (Matching) e Sobrevivência (Survivorship)

Quando dois ou mais registros representam o mesmo conteúdo com dados divergentes, o pipeline Bronze → Silver aplica as regras determinísticas:

### 4.1. Correspondência
1. **Exata:** `conteudo_id` idêntico → mesmo conteúdo.
2. **Fuzzy:** Similaridade ≥ 95% no `titulo_normalizado` (caixa baixa, sem acentos) + mesmo `autor` + mesmo `tipo`.

### 4.2. Sobrevivência

| Atributo | Regra de Sobrevivência |
|:---|:---|
| `titulo` | Prevalece o mais longo e descritivo (maior `LENGTH` não nulo) |
| `categoria` | Prevalece a do sistema acadêmico primário (`catalogo.csv`) |
| `nivel` | Prevalece o do registro com maior `data_publicacao` |
| `conteudo_id` (Golden ID) | Menor ID entre os registros duplicados |
| `autor` | Mascarado na Silver; prevalência irrelevante para análise |

### 4.3. Tabela de De-Para (XRef)

Após a deduplicação, um registro XRef é criado na tabela `quarentena.xref_conteudos_unificados` para remapear automaticamente interações, recomendações e comentários originalmente associados a IDs secundários para o Golden ID:

```sql
-- Estrutura da XRef (criada no DDL criar_banco.sql)
-- quarentena.xref_conteudos_unificados
-- conteudo_id_original | conteudo_id_golden | motivo_unificacao | data_unificacao
```

---

## 5. Sistemas Consumidores da Entidade Mestre

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ECOSSISTEMA DA ENTIDADE MESTRE: Conteúdo                     │
│                                                                                 │
│   [silver.catalogo]  ←── GOLDEN STORE (tabela mestre, MDM certificado)         │
│         │                                                                       │
│         ├──► silver.interacoes          (FK: conteudo_id, cardinalidade N:1)    │
│         ├──► silver.recomendacoes       (FK: conteudo_id, cardinalidade N:1)    │
│         ├──► silver.comentarios         (FK: conteudo_id, cardinalidade N:1)    │
│         ├──► gold.engajamento_conteudo  (FK: conteudo_id, cardinalidade 1:1)    │
│         ├──► Motor de Recomendação IA   (Consulta por categoria e nível)        │
│         └──► Apache Superset Dashboard  (Consumo analítico — tabelas Gold)      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Qualquer desatualização ou duplicidade em `silver.catalogo` se propagaria a **todas** essas camadas. Por isso o MDM com Golden Record é crítico para a integridade do ecossistema.

---

## 6. Política de Stewardship

| Responsabilidade | Área | Contato |
|:---|:---|:---|
| Aprovar inclusão de novos conteúdos | Coordenação Pedagógica | `pedagogico@ficdevia.edu.br` |
| Validar Golden Records pós-deduplicação | Engenharia de Plataforma | `eng.plataforma@ficdevia.edu.br` |
| Revisar taxonomia de categorias e níveis | Design Instrucional | `design.instrucional@ficdevia.edu.br` |
| Homologar mudanças na tabela mestre | Analytics & IA | `analytics@ficdevia.edu.br` |

**Frequência de revisão:** Trimestral  
**Processo de correção:**
```
Ticket Sistema Acadêmico
  → Reingere Bronze → Hop aplica Survivorship
  → Steward valida no OpenMetadata
  → Gold atualizada na próxima execução agendada
```

---

## 7. Evidência Técnica Gerada

Após a execução do script `registrar_dados_mestres_openmetadata.py`, são gerados:

| Arquivo | Conteúdo |
|:---|:---|
| `openmetadata/evidencias/rf30_dados_mestres_openmetadata.json` | Payload JSON completo com entidade mestre, custom properties e descrições de colunas |

Quando o servidor OpenMetadata estiver disponível (`http://localhost:8585`):
- As **Custom Properties** ficam visíveis na aba "Custom Properties" de qualquer tabela catalogada.
- A descrição MDM aparece nas colunas de `silver.catalogo` no catálogo.
- O **Data Owner** da tabela master é marcado como a Coordenação Pedagógica.
