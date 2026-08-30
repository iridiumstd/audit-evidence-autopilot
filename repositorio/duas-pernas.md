# As duas pernas do EUDR — referência para a Trilha B

Documento de apoio à implementação de `verificacao.py`.
Versão enxuta: só o que vira código. O material de pitch está no artifact.

---

## O enquadramento

O regulamento exige **duas provas cumulativas**:

- **Perna A — livre de desmatamento.** Nenhuma supressão de vegetação nativa
  no talhão após 31/12/2020. Prova-se com geometria e satélite.
  **Já é commodity gratuita** (Whisp/FAO, Global Forest Watch, Parque Cafeeiro,
  Cacaupará). Não é diferencial.

- **Perna B — legalidade no país produtor.** Avaliada em **oito categorias**.
  É feita de documento. **É onde está o diferencial do produto.**

Toda checagem implementada deve declarar a que perna pertence, e as da perna B
devem declarar a categoria.

---

## As oito categorias da perna B

| # | Categoria | Automatizável contra base pública? | No MVP |
|---|---|---|---|
| 1 | Direitos de uso da terra | Parcial — CAR e titularidade | ✅ checagem 03 |
| 2 | Proteção ambiental | Sim — embargos Ibama | ✅ checagem 02 |
| 3 | Regulação florestal | Não no cacau | ❌ trilha documental |
| 4 | Direitos de terceiros | Sim — TI, quilombo, UC | ✅ checagem 04 |
| 5 | Direitos trabalhistas | Parcial — lista suja, CNDT | ❌ trilha documental |
| 6 | Direitos humanos | Não | ❌ trilha documental |
| 7 | Consentimento prévio (FPIC) | Parcial — sobreposição | ✅ dentro da 04 |
| 8 | Tributário, anticorrupção, aduaneiro | Parcial — coerência fiscal | ✅ checagem 06 |

**Automatizamos 4 categorias. As outras viram trilha documental organizada,
datada e indexada dentro do dossiê.** Isso é posição declarada, não limitação
escondida — nenhum concorrente cobre as oito.

Nota histórica útil: as categorias 1 a 4 e 8 já existiam desde 2013 no EUTR,
mas só para madeira. As categorias 5, 6 e 7 são inéditas em regulação europeia
de importação — por isso não existe ferramenta pronta para elas em lugar nenhum.

---

## Evidências documentais por categoria

Mapeamento a validar pela frente de taxonomia. Use para nomear tipos de
documento em `params/cacau.yml` e para escrever as regras da checagem 05.

**1 · Uso da terra** — matrícula do imóvel; CCIR (INCRA); ITR e recibo da DITR;
certificação SIGEF; contrato de arrendamento, parceria ou comodato; título,
CDRU ou CCU em assentamento; declaração de posse.

**2 · Proteção ambiental** — CAR (recibo e demonstrativo); situação no SICAR;
análise de APP e Reserva Legal; licença ambiental estadual; outorga de água;
autorização de supressão de vegetação; adesão ao PRA; autos de infração e
embargos do Ibama.

**3 · Regulação florestal** — DOF/SINAFLOR; PMFS e autorização; autorização de
manejo de cabruca (Bahia).

**4 · Direitos de terceiros** — sobreposição com terra indígena (FUNAI);
com território quilombola (INCRA); com unidade de conservação (CNUC);
certidão de ações reais e possessórias.

**5 · Direitos trabalhistas** — Cadastro de Empregadores (lista suja); CNDT
(TST); CRF do FGTS; registro de empregados e eSocial; contratos de trabalho e
de safrista; conformidade com a NR-31; declaração de ausência de trabalho
infantil.

**6 · Direitos humanos** — política de direitos humanos do fornecedor;
consulta a ações civis públicas e listas de infratores.

**7 · Consentimento prévio, livre e informado** — protocolo de consulta da
comunidade; ata de consulta prévia; acordo de repartição de benefícios.

**8 · Tributário, anticorrupção, comercial e aduaneiro** — nota fiscal de
produtor rural (uma por entrega); inscrição estadual e situação do CPF/CNPJ;
CND federal, estadual e municipal; FUNRURAL e SENAR; habilitação RADAR/Siscomex;
DU-E e documentos de embarque; consulta CEIS e CNEP.

Total mapeado: ~42 evidências. As plataformas gratuitas cobrem 2 (CAR e
geolocalização).

---

## Checagem 05 — consistência documental

**A joia do produto.** Não é "o documento existe" — é o cruzamento entre
documentos do mesmo produtor. Implemente cada regra como função separada e
numerada, devolvendo dict com `resultado`, `texto`, `evidencia`.

| Regra | O que detecta | Severidade |
|---|---|---|
| R1 | CPF do CAR ≠ CPF da nota fiscal | exceção |
| R2 | Área declarada no talhão > área do CAR | exceção |
| R3 | Documento vencido na data prevista de embarque do lote | exceção |
| R4 | Município da matrícula ≠ município do CAR | exceção |
| R5 | Titular do arrendamento ≠ produtor do grupo | exceção |
| R6 | Documento do conjunto mínimo ausente | exceção |
| R7 | Dois documentos do mesmo tipo, números diferentes, datas próximas | exceção |

Regras adicionais valem ponto — quanto mais regras verdadeiras, maior o
diferencial. Sugestões para expandir: nome do titular divergente com CPF igual;
área somada dos talhões maior que a área total do imóvel no CAR; data de emissão
posterior à data de validade; documento cuja vigência não cobre o período de
produção declarado no lote; CAR com situação diferente de ativo.

**Cada exceção precisa dizer, em português claro, qual documento conflita com
qual.** O texto vai impresso no dossiê e é lido por um auditor.

---

## Regra de escrita dos laudos

Todo laudo gravado em `checagem.texto` precisa conter:

1. o que foi comparado,
2. contra qual base,
3. **em que data a consulta foi feita**,
4. o resultado,
5. a conclusão em uma frase.

A data é o que dá validade jurídica ao instantâneo — o dossiê é um snapshot
assinado de um estado verificado continuamente. Sem a data, o laudo não presta.
