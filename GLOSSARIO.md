# GLOSSÁRIO

Evidence Autopilot EUDR · ATON

Metade do time não conhece os termos regulatórios, e metade da plateia não conhece os termos do produto. Este arquivo serve aos dois lados.

Marcações: **`[código]`** aparece no código ou no esquema · **`[pitch]`** vale dizer em voz alta na apresentação.

---

## 1 · Regulação

**EUDR** — *EU Deforestation Regulation*. Regulamento europeu que condiciona a entrada de certas commodities no mercado da UE à prova de que não vieram de área desmatada e de que foram produzidas em conformidade com a lei do país produtor. **`[pitch]`**

**EUTR** — *EU Timber Regulation*, de 2013, antecessor do EUDR. Cobria só madeira, e já exigia as categorias 1 a 4 e 8 de legalidade. **As categorias 5, 6 e 7 do EUDR são inéditas em regulação europeia de importação** — por isso não existe ferramenta pronta para elas em lugar nenhum. **`[pitch]`**

**Perna A** — a prova de **livre de desmatamento**: nenhuma supressão de vegetação nativa no talhão após **31/12/2020**. Prova-se com geometria e satélite. Já é commodity gratuita. **`[código]`** `checagem.perna = 'A'` **`[pitch]`**

**Perna B** — a prova de **legalidade no país produtor**, em oito categorias. É feita de documento. É onde está o diferencial do produto. **`[código]`** `checagem.perna = 'B'` **`[pitch]`**

**As oito categorias** — a divisão da perna B: (1) direitos de uso da terra, (2) proteção ambiental, (3) regulação florestal, (4) direitos de terceiros, (5) direitos trabalhistas, (6) direitos humanos, (7) consentimento prévio livre e informado, (8) tributário, anticorrupção, comercial e aduaneiro. **Automatizamos quatro; as outras viram trilha documental indexada.** **`[pitch]`**

**Prova cumulativa** — as duas pernas valem juntas. Livre de desmatamento e ilegal não passa; legal e desmatado não passa.

**FPIC** — *Free, Prior and Informed Consent*, consentimento livre, prévio e informado. Categoria 7. Direito de comunidades tradicionais serem consultadas antes de atividade que as afete.

**Due diligence** — o dever do importador europeu de verificar, não de acreditar. É o que cria o mercado deste produto.

---

## 2 · Fundiário e geoespacial

**Talhão** — a unidade produtiva georreferenciada. Um produtor tem de 1 a 3. É a unidade sobre a qual toda checagem roda. **`[código]`** tabela `talhao`

**CAR** — Cadastro Ambiental Rural. Registro eletrônico obrigatório do imóvel rural, com a geometria e as áreas de APP e reserva legal. **O documento mais consumido do sistema** — três das sete regras da checagem 05 dependem dele.

**SICAR** — Sistema Nacional de Cadastro Ambiental Rural, onde se consulta a situação de um CAR. Um CAR pode existir e estar **inativo** — existir não é estar conforme.

**Matrícula do imóvel** — o registro do imóvel em cartório. Prova de propriedade.

**CCIR** — Certificado de Cadastro de Imóvel Rural, emitido pelo INCRA. Vincula o imóvel ao cadastro federal.

**ITR / DITR** — Imposto sobre a Propriedade Territorial Rural e sua declaração.

**NIRF** — Número do Imóvel na Receita Federal.

**SIGEF** — Sistema de Gestão Fundiária do INCRA, onde se certifica o georreferenciamento de um imóvel.

**CDRU / CCU** — Concessão de Direito Real de Uso e Contrato de Concessão de Uso, títulos usados em projeto de assentamento.

**Arrendamento, parceria, comodato** — formas de usar terra que não é sua. Se o titular do contrato não é o produtor do grupo, dispara a regra **R5**.

**APP** — Área de Preservação Permanente. **Reserva legal** — o percentual do imóvel que precisa manter vegetação nativa. Ambas aparecem no demonstrativo do CAR.

**TI / quilombo / UC** — terra indígena (FUNAI), território quilombola (INCRA), unidade de conservação (CNUC). Sobreposição com qualquer uma delas é o objeto da checagem 04.

**CNUC** — Cadastro Nacional de Unidades de Conservação.

**Shapefile** — formato de arquivo geoespacial vetorial. É como as bases do Ibama e do CNUC são publicadas. **`[código]`** vive em `dados/bases/`

**`sjoin`** — *spatial join*, a operação do geopandas que resolve "este talhão está dentro deste polígono?" em uma linha. **`[código]`**

**WKT** — *Well-Known Text*, a representação textual de uma geometria. É como a geometria do talhão é guardada no SQLite. **`[código]`** `talhao.geom_wkt`

**CRS** — *Coordinate Reference System*. Duas camadas em CRS diferentes produzem interseção errada silenciosamente. Verificar sempre.

---

## 3 · Ambiental e florestal

**Embargo do Ibama** — ato administrativo que proíbe o uso econômico de uma área por infração ambiental. Publicado como shapefile de polígonos, download direto e sem autenticação. **É o recurso R-01 do `ARD.md` e o gatilho da demonstração ao vivo.** **`[pitch]`**

**Termo de embargo** — o número que identifica um embargo. Vai na evidência da checagem 02; sem ele o laudo não serve de prova.

**Auto de infração** — a multa. Pode existir sem embargo, e vice-versa.

**ASV** — Autorização de Supressão de Vegetação. Desmate autorizado é legal; a checagem 01 olha desmate, não legalidade dele.

**PRA** — Programa de Regularização Ambiental. Caminho para regularizar passivo ambiental declarado no CAR.

**DOF / SINAFLOR** — Documento de Origem Florestal e o sistema que o emite. Categoria 3, não automatizada no cacau.

**PMFS** — Plano de Manejo Florestal Sustentável.

**Cabruca** — sistema de cultivo de cacau sob a sombra da mata nativa, típico da Bahia. Tem autorização de manejo específica, e é um caso em que "árvore em pé" e "produção agrícola" convivem — o que confunde análise de satélite ingênua. **`[pitch]`**

---

## 4 · Trabalhista, tributário e aduaneiro

**Lista suja** — o Cadastro de Empregadores que submeteram trabalhadores a condição análoga à escravidão. Lista pública, pequena, consultável por CPF/CNPJ. Candidata a automação futura.

**CNDT** — Certidão Negativa de Débitos Trabalhistas, do TST.

**CRF do FGTS** — Certificado de Regularidade do FGTS.

**NR-31** — norma regulamentadora de segurança e saúde no trabalho rural.

**eSocial** — sistema de registro de vínculos trabalhistas.

**CND** — Certidão Negativa de Débitos, nas esferas federal, estadual e municipal.

**FUNRURAL / SENAR** — contribuições incidentes sobre a produção rural.

**Nota fiscal de produtor rural** — **uma por entrega**, não uma por produtor. É o elo entre produtor e lote na cadeia de custódia, e insumo das regras R1 e R7.

**CEIS / CNEP** — Cadastro de Empresas Inidôneas e Suspensas e Cadastro Nacional de Empresas Punidas. Categoria 8, anticorrupção.

**RADAR / Siscomex** — habilitação e sistema para operar comércio exterior.

**DU-E** — Declaração Única de Exportação. Documento aduaneiro do embarque.

---

## 5 · Termos do produto

**Lote** — o agrupamento de entregas que vai num embarque. Tem de 10 a 40 produtores. **É a unidade do dossiê.** **`[código]`** tabela `lote`

**Sobreposição entre lotes** — um mesmo produtor pode estar em vários lotes. **É por isso que um embargo derruba três dossiês de uma vez** — a demonstração inteira depende disso. **`[pitch]`**

**Dossiê** — o PDF de conformidade por lote. Oito blocos, versionado, com hash por anexo. **É o entregável que o cliente compra.** **`[código]`** tabela `dossie`

**Snapshot assinado** — o que o dossiê é: uma fotografia datada de um estado verificado continuamente. **Sem a data da consulta, o laudo não presta.** **`[pitch]`**

**Checagem** — uma verificação sobre um talhão. Seis no MVP, cada uma declarando perna e categoria. **`[código]`** tabela `checagem`

**Laudo** — o campo `checagem.texto`. Precisa dizer o que foi comparado, contra qual base, **em que data**, o resultado e a conclusão em uma frase. É lido por um auditor.

**Exceção** — o que a máquina não decide sozinha e entrega ao humano. **`[código]`** tabela `excecao`

**Fila de exceções** — a tela principal do produto. Não é painel de status verde: é lista de trabalho. **`[pitch]`**

**Semáforo** — `verde` · `atencao` · `bloqueado`. O status de um lote é o **pior** resultado entre os talhões que o compõem. **`[código]`** `lote.status`

**Resultado de checagem** — `conforme` · `excecao` · `bloqueio`. **`[código]`** `checagem.resultado`

**Status de documento** — `ok` · `ilegivel` · `vencido` · `divergente`. **`[código]`** `documento.status`

**Mapa de lacunas** — quais documentos do conjunto mínimo faltam para um produtor. Saída da ingestão, entregável e não detalhe.

**Conjunto mínimo** — os documentos que tornam um produtor apto. Definido em `params/cacau.yml`; alimenta a regra R6. Ver `TAXONOMIA.md`.

**Checagem 05 / consistência documental** — a joia. Não é "o documento existe", é o cruzamento entre documentos do mesmo produtor: o CPF do CAR contra o CPF da nota fiscal, o município da matrícula contra o do CAR. **É o que nenhuma plataforma de coordenada consegue rodar.** **`[pitch]`**

**Trilha documental** — o que não automatizamos: documentos organizados, datados, indexados e com hash dentro do dossiê. Posição declarada, não limitação escondida. **`[pitch]`**

**Vigilância** — o laço que relê as bases, reverifica os talhões afetados e regenera os dossiês que pioraram. **É onde a autonomia fica visível.** **`[código]`** `vigilancia.py` **`[pitch]`**

**Contador de autonomia** — o número no topo de todas as telas, lido da tabela `evento`: *N verificações · N documentos · N dossiês regerados · N exceções para humano*. **É o número que o jurado anota.** **`[pitch]`**

**Trilha de auditoria** — a tabela `evento`, append-only, distinguindo ator `sistema` de `humano`. Alimenta o bloco 7 do dossiê, o contador e o diff entre versões. **Nenhuma linha é apagada, nunca.** **`[código]`**

**Diff de dossiê** — o texto em português que diz o que mudou entre versões: *"talhão TAL-014 passou de conforme para bloqueio na checagem 02"*.

**Armadilha plantada** — defeito inserido de propósito nos dados semeados para provar que a detecção funciona: um ilegível, um vencido, um com CPF divergente, um duplicado, um que não é documento.

**Trilha (de construção)** — a divisão de trabalho do time: 0 fundação, A ingestão, B verificação, C dossiê, D vigilância e telas. Cada uma tem tabelas de escrita exclusivas. Não confundir com **trilha documental** nem com **trilha de auditoria**.

---

## 6 · Concorrência e contexto

**Whisp / FAO** — ferramenta gratuita de análise de desmatamento por coordenada. Cobre a perna A.

**Global Forest Watch** — plataforma pública de monitoramento florestal. Cobre a perna A.

**Parque Cafeeiro · Cacaupará** — iniciativas brasileiras de rastreabilidade. **Pendência P-02 do `ADR.md`: confirmar o que emitem de fato** — define o contorno exato do posicionamento.

**"As plataformas gratuitas cobrem 2 das ~42 evidências"** — CAR e geolocalização. É a frase que separa este produto de um verificador de coordenada. **`[pitch]`**
