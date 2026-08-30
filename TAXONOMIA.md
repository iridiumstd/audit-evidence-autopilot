# TAXONOMIA — tipos de documento

Evidence Autopilot EUDR · ATON · commodity: cacau

Este arquivo é o **insumo direto de `params/cacau.yml`**. Fixa o nome canônico de cada tipo de documento, as palavras-chave que o identificam, os campos que se extrai dele e o papel que ele cumpre nas checagens.

Sem ele, a Trilha A grava `tipo='nota_fiscal'` e a Trilha B procura `tipo='nf_produtor'`, e nada cruza.

> **Estado do documento.** As colunas *palavras-chave*, *campos* e *validade* são **proposta a validar** pela frente de taxonomia contra documentos reais da cooperativa. Os **nomes canônicos são fixos desde já** — são eles que entram no contrato entre trilhas. Validade em dias é proposta operacional, **não parecer jurídico**: cada linha marcada `a confirmar` precisa de confirmação antes de ir a produção.

---

## 1 · Regras de nomenclatura

**Nome canônico (o valor de `documento.tipo`):** minúsculo, sem acento, separado por `_`. Nunca muda depois de publicado aqui.

**Arquivo padronizado em `dados/padronizado/<produtor_slug>/`:**

```text
TIPO_SLUGPRODUTOR_AAAAMMDD_vN.ext
```

`AAAAMMDD` é a **data de emissão** do documento. Sem data de emissão legível, usa-se a data de ingestão e o documento vai com confiança reduzida.

**Tipo não reconhecido grava `tipo='desconhecido'`. Não chutar** — um documento mal tipado é pior que um documento não tipado, porque entra nas regras da checagem 05 e gera exceção falsa.

---

## 2 · Catálogo de tipos

Colunas: **cat.** = categoria EUDR da perna B · **mín.** = pertence ao conjunto mínimo · **regras** = quais regras da checagem 05 consomem o documento.

### Categoria 1 · Direitos de uso da terra

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `matricula_imovel` | Matrícula do imóvel | matrícula, cartório, registro de imóveis, livro nº | número da matrícula, cartório, município, proprietário, área | sem validade | ✅ | R4 |
| `ccir` | CCIR (INCRA) | CCIR, certificado de cadastro de imóvel rural, INCRA | código do imóvel, titular, área total, município | exercício anual · *a confirmar* | ✅ | R2 |
| `itr` | ITR / recibo da DITR | ITR, imposto territorial rural, DITR, NIRF | NIRF, exercício, titular, área | exercício anual · *a confirmar* | — | — |
| `sigef` | Certificação SIGEF | SIGEF, georreferenciamento, certificação, memorial descritivo | código da parcela, área, titular | sem validade | — | R2 |
| `contrato_arrendamento` | Arrendamento, parceria ou comodato | arrendamento, parceria agrícola, comodato, arrendatário | arrendador, arrendatário, vigência início e fim, área | vigência do contrato | condicional | **R5** |
| `titulo_assentamento` | Título, CDRU ou CCU | CDRU, CCU, assentamento, título de domínio, lote nº | número do lote, projeto de assentamento, beneficiário | sem validade | condicional | — |
| `declaracao_posse` | Declaração de posse | declaração de posse, posseiro, ocupação mansa e pacífica | declarante, área, município, testemunhas | *a confirmar* | condicional | — |

`condicional`: entra no conjunto mínimo conforme a forma de ocupação — quem arrenda precisa de `contrato_arrendamento`; quem é assentado precisa de `titulo_assentamento`; quem tem matrícula própria não precisa de nenhum dos dois.

### Categoria 2 · Proteção ambiental

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `car_recibo` | Recibo de inscrição no CAR | CAR, cadastro ambiental rural, recibo de inscrição, PA-\* | número do CAR, CPF do titular, município, área, data | sem validade | ✅ | **R1, R2, R4** |
| `car_demonstrativo` | Demonstrativo do CAR | demonstrativo, situação do cadastro, SICAR | número do CAR, situação, área de APP, reserva legal | *a confirmar* | ✅ | R2 |
| `licenca_ambiental` | Licença ambiental estadual | licença de operação, SEMAS, LO, LP, LI | número, órgão, validade, empreendimento | por licença | — | R3 |
| `outorga_agua` | Outorga de uso de água | outorga, recurso hídrico, captação | número, validade, vazão | por outorga | — | R3 |
| `asv` | Autorização de supressão de vegetação | ASV, supressão de vegetação, autorização de desmate | número, área autorizada, validade | por autorização | — | R3 |
| `adesao_pra` | Adesão ao PRA | PRA, programa de regularização ambiental, termo de compromisso | número, data de adesão, situação | *a confirmar* | — | — |
| `auto_infracao` | Auto de infração / embargo | auto de infração, embargo, Ibama, termo de embargo | número do termo, data, área embargada | sem validade | — | — |

`car_recibo` é o documento mais consumido do sistema — três das sete regras da checagem 05 dependem dele. Se um produtor não tem CAR ingerido, R1, R2 e R4 ficam mudas para ele, e isso precisa aparecer como lacuna, não como conformidade.

### Categoria 3 · Regulação florestal — trilha documental

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `dof` | DOF / SINAFLOR | DOF, documento de origem florestal, SINAFLOR | número, produto, origem, destino, validade | por documento | — | — |
| `pmfs` | PMFS e autorização | PMFS, plano de manejo florestal sustentável | número, área, validade | por plano | — | — |
| `manejo_cabruca` | Autorização de manejo de cabruca | cabruca, manejo, cacau cabruca | número, área, validade | por autorização | — | — |

Não automatizados no MVP. Entram como anexo indexado, datado e com hash.

### Categoria 4 e 7 · Direitos de terceiros e consentimento prévio — trilha documental

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `certidao_acoes_reais` | Certidão de ações reais e possessórias | ações reais, possessórias, certidão, distribuidor | número, comarca, resultado, data | *a confirmar* | — | R3 |
| `protocolo_consulta` | Protocolo de consulta da comunidade | protocolo de consulta, comunidade, consulta prévia | comunidade, data | sem validade | — | — |
| `ata_consulta_previa` | Ata de consulta prévia | ata, consulta livre prévia e informada, FPIC | data, participantes, deliberação | sem validade | — | — |
| `acordo_reparticao` | Acordo de repartição de benefícios | repartição de benefícios, acordo | partes, vigência | vigência | — | — |

A sobreposição geográfica com TI, quilombo e UC é checada por base externa (checagem 04, recursos R-04/R-05/R-06 do `ARD.md`), não por estes documentos. Estes sustentam a parte que máquina nenhuma decide.

### Categoria 5 · Direitos trabalhistas — trilha documental

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `cndt` | Certidão negativa de débitos trabalhistas | CNDT, débitos trabalhistas, TST | número, data de emissão, validade, resultado | *a confirmar* | — | R3 |
| `crf_fgts` | CRF do FGTS | CRF, FGTS, regularidade, Caixa | número, validade, resultado | *a confirmar* | — | R3 |
| `registro_empregados` | Registro de empregados / eSocial | eSocial, registro de empregados, CTPS | empregador, quantidade | *a confirmar* | — | — |
| `contrato_trabalho` | Contrato de trabalho ou de safrista | contrato de trabalho, safrista, safra | empregado, vigência | vigência | — | — |
| `nr31` | Conformidade com a NR-31 | NR-31, segurança rural, SESMT | data, responsável | *a confirmar* | — | — |
| `decl_trabalho_infantil` | Declaração de ausência de trabalho infantil | trabalho infantil, declaração, menor de idade | declarante, data | *a confirmar* | — | — |

Consulta ao Cadastro de Empregadores (lista suja) é candidata a automação futura — ver `ARD.md`, seção 4.

### Categoria 6 · Direitos humanos — trilha documental

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `politica_direitos_humanos` | Política de direitos humanos do fornecedor | política, direitos humanos, código de conduta | emissor, data | *a confirmar* | — | — |
| `consulta_acp` | Consulta a ações civis públicas | ação civil pública, ACP, MPF | número, resultado, data | *a confirmar* | — | — |

### Categoria 8 · Tributário, anticorrupção, comercial e aduaneiro

| Nome canônico | Documento | Palavras-chave | Campos a extrair | Validade | mín. | regras |
|---|---|---|---|---|---|---|
| `nota_fiscal_produtor` | Nota fiscal de produtor rural | nota fiscal, produtor rural, NFP-e, natureza da operação | número, série, CPF/CNPJ do emitente, data, quantidade, valor | sem validade | ✅ | **R1, R7** |
| `inscricao_estadual` | Inscrição estadual / situação CPF-CNPJ | inscrição estadual, SEFAZ, situação cadastral | número, situação, titular | *a confirmar* | — | — |
| `cnd_federal` | CND federal | certidão negativa, débitos federais, Receita Federal | número, validade, resultado | *a confirmar* | — | R3 |
| `cnd_estadual` | CND estadual | certidão negativa, SEFAZ, débitos estaduais | número, validade, resultado | *a confirmar* | — | R3 |
| `cnd_municipal` | CND municipal | certidão negativa, prefeitura, tributos municipais | número, validade, resultado | *a confirmar* | — | R3 |
| `funrural_senar` | FUNRURAL e SENAR | FUNRURAL, SENAR, contribuição | competência, valor | *a confirmar* | — | — |
| `radar_siscomex` | Habilitação RADAR/Siscomex | RADAR, Siscomex, habilitação, modalidade | número, modalidade, situação | *a confirmar* | — | — |
| `due_embarque` | DU-E e documentos de embarque | DU-E, declaração única de exportação, conhecimento de embarque, contêiner | número, data, contêiner, destino | sem validade | — | — |
| `consulta_ceis_cnep` | Consulta CEIS e CNEP | CEIS, CNEP, portal da transparência, inidôneo | resultado, data | *a confirmar* | — | — |

`nota_fiscal_produtor` é **uma por entrega**, não uma por produtor. R7 (dois documentos do mesmo tipo com números diferentes e datas próximas) precisa tratar este tipo como esperado-múltiplo, ou vai gerar falso positivo em todo produtor que entregou duas vezes na mesma semana.

### Tipos especiais

| Nome canônico | Quando | Efeito |
|---|---|---|
| `desconhecido` | Nenhuma palavra-chave bateu | Não entra em regra nenhuma; aparece no mapa de lacunas |
| `nao_documento` | Foto, imagem sem texto útil | Idem; é uma das armadilhas plantadas (foto do cacau secando) |

---

## 3 · Conjunto mínimo — proposta

O que torna um produtor **apto** para entrar num lote. Alimenta a regra **R6** (documento do conjunto mínimo ausente) e o mapa de lacunas da ingestão.

| Nome canônico | Por quê |
|---|---|
| `car_recibo` | Base da categoria 2 e insumo de R1, R2 e R4 |
| `car_demonstrativo` | Situação do cadastro — CAR inativo não sustenta conformidade |
| `matricula_imovel` **ou** `titulo_assentamento` **ou** `declaracao_posse` | Prova de uso da terra, categoria 1 |
| `contrato_arrendamento` | **Só se** a área for arrendada — condicional, e é o que R5 verifica |
| `ccir` | Vínculo do imóvel com o INCRA |
| `nota_fiscal_produtor` | Uma por entrega no lote; sem ela não há cadeia de custódia |

**A validar com a cooperativa.** Um conjunto mínimo grande demais reprova todo mundo e a fila de exceções vira ruído; pequeno demais e o dossiê não sustenta auditoria. Comece por este e ajuste pelo que os dados reais mostrarem.

---

## 4 · Esqueleto de `params/cacau.yml`

A Trilha 0 escreve o arquivo; esta é a forma esperada.

```yaml
commodity: cacau
regiao_padrao: transamazonica

produtividade_kg_ha:          # checagem 06 — ver pendencia P-01 do ADR.md
  PA: 900                     # a confirmar
  BA: 270                     # a confirmar
  limiar_excecao: 1.5         # acima de 150% do esperado
  limiar_bloqueio: 3.0        # acima de 300% do esperado

tipos:
  car_recibo:
    nome: "Recibo de inscricao no CAR"
    categoria: 2
    palavras_chave: ["CAR", "cadastro ambiental rural", "recibo de inscricao"]
    campos: [numero_car, cpf_titular, municipio, area_ha, data_emissao]
    validade_dias: null
  nota_fiscal_produtor:
    nome: "Nota fiscal de produtor rural"
    categoria: 8
    palavras_chave: ["nota fiscal", "produtor rural", "NFP-e"]
    campos: [numero, serie, cpf_emitente, data_emissao, quantidade_kg, valor]
    validade_dias: null
    multiplo_esperado: true   # nao dispara R7 sozinho
  # ... um bloco por tipo da secao 2

conjunto_minimo:
  obrigatorios: [car_recibo, car_demonstrativo, ccir, nota_fiscal_produtor]
  um_de: [[matricula_imovel, titulo_assentamento, declaracao_posse]]
  condicionais:
    contrato_arrendamento: "quando area arrendada"

confianca:
  limiar_ilegivel: 0.4
```

---

## 5 · Pendências desta taxonomia

| # | Pendência | Quem fecha |
|---|---|---|
| T-01 | Confirmar validade em dias de cada `a confirmar` — nenhum valor aqui é parecer jurídico | Frente de taxonomia |
| T-02 | Validar palavras-chave contra documentos reais da cooperativa; a lista atual é derivada de nome de documento, não de layout observado | Frente de taxonomia + Trilha A |
| T-03 | Fechar o conjunto mínimo com a cooperativa | PM |
| T-04 | Decidir se `car_recibo` e `car_demonstrativo` são tipos separados ou um só com campos distintos | Trilha A, na primeira hora |
