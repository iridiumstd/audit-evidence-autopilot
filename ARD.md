# ARD — Agentic Resource Discovery

Evidence Autopilot EUDR · ATON

Catálogo dos recursos externos que o sistema descobre, busca, valida, versiona e vigia. **É o documento que sustenta a frase "contra qual base" de todo laudo** (ver `ADR-005`). Sem ele, `checagem.fonte` é texto solto.

Complementa: `PRD.md` (por que), `SPEC.md` (como), `ADR.md` (decisões travadas).

---

## 1 · Por que este documento existe

Um dossiê de conformidade afirma coisas sobre o mundo. Cada afirmação precisa apontar para um recurso externo real, com procedência, formato conhecido e data de consulta. Três problemas tornam isso difícil:

1. **As bases brasileiras mudam** — saem do ar, trocam de URL, mudam de esquema de campo, atualizam em cadência irregular.
2. **Nem toda base é acessível por máquina** — algumas são consulta manual com captcha, outras exigem certificado.
3. **O sistema é autônomo** — a Trilha D relê as bases em laço e precisa saber o que é *novo* desde a última passada.

Este arquivo é onde cada recurso ganha uma ficha, e onde o estado de descoberta fica registrado em vez de morar na cabeça de quem baixou.

**Regra que governa tudo aqui, de `ADR-012`: se um recurso real falhar, diga exatamente o que aconteceu. Nunca simule o dado.** Camada semeada é permitida, mas precisa estar marcada como semeada no código **e** declarada no laudo.

---

## 2 · Protocolo de descoberta

Todo recurso passa por sete passos. A Trilha 0 executa para os recursos do MVP; qualquer recurso novo segue o mesmo caminho.

| Passo | O que fazer | Registro |
|---|---|---|
| **1 · Localizar** | Achar a origem oficial. Portal de dados abertos antes de raspagem; raspagem antes de consulta manual. | URL na ficha |
| **2 · Baixar** | Download direto, sem autenticação quando possível. Se falhar, registrar o erro literal. | `estado` da ficha |
| **3 · Inspecionar** | Abrir e responder: qual a **data real de atualização**, quais são os **campos**, e **quantos registros** existem no recorte de interesse. | Seção "o que a inspeção revelou" |
| **4 · Registrar procedência** | Origem, data de download, hash do arquivo baixado, formato, CRS quando geoespacial. | `dados/bases/` + ficha |
| **5 · Recortar** | Reduzir ao recorte do MVP — Transamazônica: Medicilândia, Altamira, Uruará, Brasil Novo. | Arquivo em `dados/bases/` |
| **6 · Versionar** | O arquivo recortado é imutável. Atualização gera arquivo novo, não sobrescreve. | Nome com data |
| **7 · Vigiar** | Declarar como a Trilha D detecta registro **ainda não visto** nesse recurso. | Seção "estratégia de vigilância" |

---

## 3 · Catálogo do MVP — recursos automatizados

| ID | Recurso | Órgão | Categoria EUDR | Consome | Acesso | Estado |
|---|---|---|---|---|---|---|
| **R-01** | Termos de embargo | Ibama | 2 · proteção ambiental | checagem 02 | Download direto, shapefile, sem autenticação | **Confirmado** |
| **R-02** | Alertas de desmatamento | a confirmar | perna A | checagem 01 | a confirmar | A descobrir |
| **R-03** | CAR / SICAR | SFB / estados | 1 · uso da terra | checagem 03 | a confirmar | A descobrir |
| **R-04** | Terras indígenas | FUNAI | 4 · direitos de terceiros | checagem 04 | a confirmar | A descobrir |
| **R-05** | Territórios quilombolas | INCRA | 4 · direitos de terceiros | checagem 04 | a confirmar | A descobrir |
| **R-06** | Unidades de conservação | CNUC / MMA | 4 · direitos de terceiros | checagem 04 | a confirmar | A descobrir |

**Recorte geográfico de todos:** Medicilândia, Altamira, Uruará, Brasil Novo (PA).

---

### R-01 · Termos de embargo do Ibama

**Estado:** confirmado — é o único recurso com origem verificada antes da construção.

| Campo | Valor |
|---|---|
| Origem | `https://dadosabertos.ibama.gov.br/dataset/termos-de-embargo` |
| Formato | Shapefile de polígonos |
| Autenticação | Nenhuma, download direto |
| Destino | `dados/bases/` |
| Consumidor | Checagem 02 (perna B, categoria 2) |
| Criticidade | **Máxima** — é o recurso do momento de 3:15 da demonstração |

**O que a inspeção revelou** — preenchido pela Trilha 0 em 2026-08-30. Script:
`ferramentas/baixar_ibama.py`. Procedência com hashes: `dados/bases/R01_procedencia.json`.

> **Correção de origem.** O recurso SHP-ZIP anunciado no dataset
> (`https://pamgia.ibama.gov.br/geoservicos/arquivos/adm_embargo_ibama_a.shp.zip`)
> responde **HTTP 404** — link morto no portal, confirmado também pela API CKAN
> `package_show`, que só lista esse recurso para o formato geoespacial.
> Os mesmos termos de embargo estão publicados **em CSV, com geometria**, no
> mesmo portal, e esses respondem. É a origem real usada:
> `.../dados/SIFISC/termo_embargo/termo_embargo/termo_embargo.csv` (163 MB) e
> `.../dados/SIFISC/termo_embargo/coordenadas/coordenadas.csv` (7,7 MB).
> Download direto, sem autenticação, como a ficha previa. **Dado real, não semeado.**

- **data real de atualização da base:** `2026-05-03 18:56:39` (campo
  `ULTIMA_ATUALIZACAO_RELATORIO`; cabeçalho HTTP `Last-Modified` de 03/05/2026
  concorda). A página CKAN mostra `28/03/2024`, que é a data do *metadado*, não
  a do dado — **é o CSV que está corrente, não a página**.
- **lista de campos (51):** `SEQ_TAD, DES_STATUS_FORMULARIO,
  DES_STATUS_FORMULARIO_AIE, SIT_CANCELADO, NUM_TAD, SER_TAD, COD_SUBSTITUICAO,
  DAT_EMBARGO, DAT_IMPRESSAO, FORMA_ENTREGA, NUM_PESSOA_EMBARGO, NOME_EMBARGADO,
  CPF_CNPJ_EMBARGADO, NUM_PROCESSO, DES_TAD, COD_MUNICIPIO, MUNICIPIO, UF,
  DES_LOCALIZACAO, NUM_LONGITUDE_TAD, NUM_LATITUDE_TAD, DETER_PRODES,
  ID_POLIGONO, EMBARGA_POLIGONO, QTD_AREA_EMBARGADA, NOME_IMOVEL, TIPO_AREA,
  GEOM_AREA_EMBARGADA, DAT_ULT_ALTER_GEOM, UNID_APRESENTACAO, UNID_CONTROLE,
  SIT_DESEMBARGO, TIPO_DESEMBARGO, DAT_DESEMBARGO, DES_DESEMBARGO,
  SEQ_AUTO_INFRACAO, NUM_AUTO_INFRACAO, SEQ_NOTIFICACAO, SEQ_ACAO_FISCALIZATORIA,
  CD_ACAO_FISCALIZATORIA, OPERACAO, SEQ_ORDEM_FISCALIZACAO, ORDEM_FISCALIZACAO,
  UNID_ORDENADORA, SEQ_SOLICITACAO_RECURSO, SOLICITACAO_RECURSO,
  OPERACAO_SOL_RECURSO, DAT_ULT_ALTERACAO, TIPO_ALTERACAO,
  JUSTIFICATIVA_ALTERACAO, ULTIMA_ATUALIZACAO_RELATORIO`
- **total no Brasil:** `113.878` termos
- **quantidade de polígonos no Pará:** `19.433` termos
- **quantidade no recorte da Transamazônica:** `3.284` termos —
  Altamira 2.209 · Uruará 766 · Medicilândia 186 · Brasil Novo 123.
  Destes, **3.162 têm geometria utilizável**: 2.417 com polígono em
  `GEOM_AREA_EMBARGADA` e 745 reconstruídos do ponto `NUM_LONGITUDE_TAD` /
  `NUM_LATITUDE_TAD` bufferizado pela área declarada em `QTD_AREA_EMBARGADA`.
  A coluna `origem_geometria` do recorte diz, linha a linha, qual dos dois foi —
  **o laudo da checagem 02 deve declarar isso** quando a geometria for
  reconstruída, porque um buffer de ponto não é o contorno real do embargo.
- **CRS:** `EPSG:4326` (longitude/latitude em graus decimais). Para medir os
  500 m da regra limítrofe e a área de interseção, reprojetar para
  `EPSG:31982` (UTM 22S) — `geo.em_metros()` faz isso.

**Formato do recorte:** `dados/bases/embargos_ibama_transamazonica_AAAAMMDD.csv`,
CSV com coluna `geom_wkt`, mais o atalho estável sem data.
Não é shapefile porque **esta máquina bloqueia as DLLs do GDAL** por política
de Controle de Aplicativo do Windows: `pyogrio` e `fiona` não carregam, e
geopandas não grava nem lê SHP/GPKG/GeoJSON aqui. `geo.carregar_embargos()`
esconde o detalhe e devolve um GeoDataFrame normal.

**Campo que dá o número do termo:** `NUM_TAD`. É ele que vai na evidência da
checagem 02, junto com a área de interseção.

**Evidência a guardar na checagem 02:** número do termo de embargo e área de interseção. Sem esses dois, o laudo não serve como prova.

**Estratégia de vigilância:** a Trilha D relê o arquivo em `dados/bases/` a cada ciclo e compara o conjunto de polígonos com o que já viu. Polígono não visto dispara `verificar_talhao` nos talhões afetados.

**Injeção controlada:** `demo/injetar_embargo.py` adiciona um polígono novo cobrindo o talhão do produtor que está nos três lotes. É o gatilho da demonstração ao vivo — e é também o teste de vigilância no dia a dia.

---

### R-02 · Alertas de desmatamento

**Estado:** a descobrir. Único recurso da perna A.

| Campo | Valor |
|---|---|
| Origem | a confirmar |
| Formato esperado | camada geoespacial de alertas com data |
| Consumidor | Checagem 01 (perna A) |
| Requisito funcional | precisa permitir filtrar alertas **posteriores a 31/12/2020** |

Como a perna A já é commodity gratuita (`ADR-001`), este recurso é mínimo defensável: um alerta com data, intersectável. Não vale investir mais que o necessário.

**Estratégia de vigilância:** mesma do R-01 — alerta ainda não visto dispara reverificação.

---

### R-03 · CAR / SICAR

**Estado:** a descobrir.

| Campo | Valor |
|---|---|
| Origem | a confirmar |
| Consumidor | Checagem 03 (perna B, categoria 1) |
| Requisito funcional | número do CAR, situação (ativo ou não), geometria do imóvel, titular |

A checagem 03 precisa de três coisas: CAR **ativo**, geometria compatível com o talhão, e titular coerente com o produtor. Se a base real não fornecer titular por máquina, a comparação de titular migra para a checagem 05 (cruzamento entre o documento de CAR ingerido e os demais documentos do produtor), que não depende de base externa.

**Nota de arquitetura:** o CAR aparece duas vezes no produto — como base externa (aqui) e como documento ingerido (regras R1, R2 e R4 da checagem 05). São caminhos independentes. Se este recurso falhar, o produto não fica cego: a consistência documental continua funcionando.

---

### R-04 · Terras indígenas (FUNAI) · R-05 · Territórios quilombolas (INCRA) · R-06 · Unidades de conservação (CNUC)

**Estado:** a descobrir. Alimentam a mesma checagem.

| Campo | Valor |
|---|---|
| Consumidor | Checagem 04 (perna B, categorias 4 e 7) |
| Requisito funcional | camada de polígonos intersectável, com identificação do território |

**Decisão pendente P-03 do `ADR.md`:** se as camadas reais não estiverem disponíveis no prazo, a checagem 04 usa **camadas semeadas** — e o código precisa deixar explícito qual é qual, e o laudo precisa declarar que a fonte é semeada. Camada semeada apresentada como real é fraude (`ADR-012`).

A checagem 04 está entre as que **nunca caem** na ordem de corte (`docs/correcoes-spec_1.md` §7.1) — ela é a única prova possível das categorias (f), (g) e parte de (d). Quem cai antes dela, na ordem corrigida, são as regras F da checagem 05 e o refinamento da checagem 03. Se a descoberta destes três recursos consumir mais de uma hora, corte antes de comprometer a 02 e a 06.

---

## 4 · Recursos da trilha documental — não automatizados no MVP

As categorias 3, 5 e 6 e parte da 8 não têm automação no MVP (`ADR-002`). Os documentos abaixo entram no dossiê como **anexos indexados, datados e com hash** — organizados, não verificados contra base.

Este é o mapeamento a validar pela frente de taxonomia, e é o que nomeia os tipos de documento em `params/cacau.yml`.

**Categoria 1 · Uso da terra** — matrícula do imóvel; CCIR (INCRA); ITR e recibo da DITR; certificação SIGEF; contrato de arrendamento, parceria ou comodato; título, CDRU ou CCU em assentamento; declaração de posse.

**Categoria 2 · Proteção ambiental** — CAR (recibo e demonstrativo); situação no SICAR; análise de APP e Reserva Legal; licença ambiental estadual; outorga de água; autorização de supressão de vegetação; adesão ao PRA; autos de infração e embargos do Ibama.

**Categoria 3 · Regulação florestal** — DOF/SINAFLOR; PMFS e autorização; autorização de manejo de cabruca (Bahia).

**Categoria 4 · Direitos de terceiros** — sobreposição com terra indígena (FUNAI); com território quilombola (INCRA); com unidade de conservação (CNUC); certidão de ações reais e possessórias.

**Categoria 5 · Direitos trabalhistas** — Cadastro de Empregadores (lista suja); CNDT (TST); CRF do FGTS; registro de empregados e eSocial; contratos de trabalho e de safrista; conformidade com a NR-31; declaração de ausência de trabalho infantil.

**Categoria 6 · Direitos humanos** — política de direitos humanos do fornecedor; consulta a ações civis públicas e listas de infratores.

**Categoria 7 · Consentimento prévio, livre e informado** — protocolo de consulta da comunidade; ata de consulta prévia; acordo de repartição de benefícios.

**Categoria 8 · Tributário, anticorrupção, comercial e aduaneiro** — nota fiscal de produtor rural (uma por entrega); inscrição estadual e situação do CPF/CNPJ; CND federal, estadual e municipal; FUNRURAL e SENAR; habilitação RADAR/Siscomex; DU-E e documentos de embarque; consulta CEIS e CNEP.

**Total mapeado: ~42 evidências. As plataformas gratuitas cobrem 2** (CAR e geolocalização).

### Candidatos a automação futura

Ordenados por relação valor/esforço, para depois do MVP:

| Recurso | Categoria | Por que é bom candidato |
|---|---|---|
| Lista suja do trabalho escravo | 5 | Lista pública, pequena, consulta por CPF/CNPJ |
| CEIS e CNEP | 8 | Portal da Transparência, consulta por CPF/CNPJ |
| CNDT (TST) | 5 | Certidão emitida por consulta, formato estável |
| Situação de CPF/CNPJ | 8 | Já é insumo da checagem 05 |

---

## 5 · Ficha de recurso — modelo para acréscimos

Todo recurso novo entra com esta ficha preenchida. Ficha incompleta significa recurso não descoberto, e recurso não descoberto não é citado em laudo.

```text
ID              R-NN
Recurso         nome corrente
Órgão           quem publica
Categoria EUDR  1..8, ou 'perna A'
Consumidor      qual checagem usa
Origem          URL exata
Formato         shapefile | csv | json | html | pdf
Autenticação    nenhuma | token | certificado | manual
Acesso          download direto | api | raspagem | consulta manual
Atualização     cadência real observada
Estado          confirmado | a descobrir | indisponível | semeado
Baixado em      ISO 8601
Hash do arquivo SHA-256
CRS             quando geoespacial
Campos          lista observada na inspeção
Registros       total, e total no recorte
Vigilância      como detectar registro ainda não visto
Falha conhecida o que já quebrou e o que fazer
```

---

## 6 · Como o recurso aparece no produto

O caminho de um recurso até o auditor europeu, e onde cada elo é registrado:

```text
ARD (procedência)
  └─> dados/bases/<arquivo recortado e datado>
        └─> checagem.fonte + checagem.data_execucao   (verificacao.py)
              └─> checagem.texto: "comparado X contra base Y em DD/MM/AAAA..."
                    └─> dossiê, bloco 5 · laudo por checagem
                          └─> auditor lê e consegue refazer a consulta
```

O elo que costuma faltar é o terceiro. `checagem.fonte` precisa nomear o recurso **e** sua data de download — não basta escrever "Ibama".

**Recurso semeado** percorre o mesmo caminho, com `Estado: semeado` na ficha e declaração explícita no texto do laudo.

---

## 7 · Estado de descoberta — a preencher na hora 1

Checklist que a Trilha 0 fecha antes do primeiro ponto de junção. Vale para o time inteiro como fonte de verdade sobre o que existe de real no banco.

- [ ] R-01 baixado, inspecionado e recortado; data de atualização, campos e contagem registrados na ficha
- [ ] R-02 localizado ou declarado indisponível
- [ ] R-03 localizado ou rebaixado para caminho documental
- [ ] R-04, R-05 e R-06 localizados ou declarados semeados, com marcação explícita no código
- [ ] `params/cacau.yml` com os tipos de documento nomeados a partir da seção 4
- [ ] Produtividade de referência confirmada para a Transamazônica (pendência P-01 do `ADR.md`; partida: PA ≈ 900 kg/ha, BA ≈ 270 kg/ha)
- [ ] Parque Cafeeiro e Cacaupará inspecionados — o que emitem de fato (pendência P-02)

Item não fechado é item declarado em voz alta no ponto de junção, não item escondido.
