# PRD — Evidence Autopilot EUDR

**Produto:** Evidence Autopilot EUDR
**Organização:** ATON
**Commodity do MVP:** cacau, região da Transamazônica (PA)
**Documento:** requisitos de produto. Para o *como*, ver `SPEC.md`; para o *porquê técnico*, ver `ADR.md`.

> **Atualizado conforme contrato.md v2 e correcoes-spec_1.md (30/08/2026); em conflito, esses dois arquivos ganham.**

---

## 1 · O problema

O EUDR exige do importador europeu **duas provas cumulativas** por lote:

- **Perna A — livre de desmatamento.** Nenhuma supressão de vegetação nativa no talhão após 31/12/2020. Prova-se com geometria e satélite.
- **Perna B — legalidade no país produtor.** Avaliada em **oito categorias**. É feita de documento.

A perna A **já é commodity gratuita** — Whisp/FAO, Global Forest Watch, Parque Cafeeiro, Cacaupará entregam. Não é diferencial.

A perna B não tem ferramenta. Uma cooperativa de cacau tem os documentos, mas espalhados, com nomes fora de padrão, sem cruzamento entre si e sem data de consulta. O trabalho de transformar isso em dossiê auditável é manual, caro e refeito a cada embarque — e envelhece: um embargo publicado depois do dossiê torna o dossiê falso sem ninguém perceber.

**A aposta do produto: o diferencial está na perna B, e dentro dela, na consistência entre documentos.**

**Urgência real.** O prazo formal da cooperativa, como micro ou pequena, é 30/06/2027. Mas isso não é o prazo que vale: quem compra dela é comprador médio ou grande, obrigado a estar conforme em **30/12/2026** — e o comprador não espera o prazo dela chegar, a cobrança desce a cadeia um semestre antes. É essa data, dez/2026, que dimensiona o projeto. (Citação dos 12 meses de vigência de uma DDS: FAQ da Comissão v4, abr/2025, pergunta 5.19, Art. 4(3) + Anexo II.)

## 2 · Quem usa

| Perfil | Dor | O que ganha |
|---|---|---|
| **Gestor de conformidade da cooperativa** | Monta dossiê à mão por lote, sem saber o que falta | Fila de exceções priorizada e mapa de lacunas por produtor |
| **Auditor / comprador europeu** | Recebe pasta de PDFs sem procedência nem data | Dossiê versionado, com hash por documento e data de cada consulta |
| **Produtor** | Não sabe qual papel está vencido ou divergente | Conjunto mínimo de documentos, com estado por documento |

## 3 · O que o produto faz

1. Recebe arquivos **já agrupados por produtor**, com nomes ruins.
2. Identifica o tipo de cada arquivo, extrai campos, padroniza a nomenclatura, calcula hash.
3. Cruza os talhões contra bases públicas brasileiras (embargos do Ibama, alertas de desmatamento, CAR, sobreposições de direitos).
4. Cruza os documentos **entre si**, dentro do mesmo produtor.
5. Emite um **dossiê de conformidade em PDF por lote de embarque**, versionado e assinado por hash.
6. Mantém tudo **sob vigilância contínua**: um embargo novo reabre e regenera sozinho os dossiês afetados.

### A fronteira de entrada — decisão de produto

O usuário entrega arquivos **agrupados por produtor, uma pasta por produtor**. A atribuição de um arquivo a um produtor vem do agrupamento, **nunca de adivinhação**. O sistema padroniza o que veio dentro do grupo; não descobre de quem é um arquivo solto. Isso elimina toda uma classe de erro silencioso.

## 4 · Cobertura declarada da perna B

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

**Automatizamos 4 categorias. As outras viram trilha documental organizada, datada e indexada dentro do dossiê.** É posição declarada, não limitação escondida — nenhum concorrente cobre as oito.

Contexto que sustenta a posição: as categorias 1–4 e 8 já existiam desde 2013 no EUTR, mas só para madeira. As categorias 5, 6 e 7 são inéditas em regulação europeia de importação — por isso não existe ferramenta pronta para elas em lugar nenhum.

Volume mapeado: **~42 evidências documentais** nas oito categorias. As plataformas gratuitas cobrem **2** (CAR e geolocalização).

## 5 · Escopo do MVP

**Dentro:**

- Ingestão de grupo de arquivos por produtor, com classificação, extração e padronização
- Sete checagens automáticas (uma da perna A, seis da perna B) — inclui a checagem 07, Lista Suja do MTE, por CPF de todos os elos do lote
- Checagem 05 de consistência documental, com regras R01–R50 (severidade B/F); no mínimo as nove regras B do contrato.md v2
- Tabela **aptidão em 5 camadas** — a aptidão de um produtor não é checklist de documentos obrigatórios, é hierarquia de alternativas por camada, e cada camada fecha por evidência de força diferente
- Duas naturezas de evidência para cada uma das oito categorias de legalidade: **documento entregue** ou **checagem gerada** — três categorias (f, g e parte de d) só fecham por checagem, porque não têm documento positivo emitido para o produtor. É evidência que o sistema gera, não que o produtor entrega.
- Dossiê em PDF + HTML, oito blocos, versionado, com hash
- Vigilância em laço que reabre e regenera dossiês
- Três telas: lotes, fila de exceções, dossiê

**Fora:**

- Categorias 3, 5 e 6 automatizadas — entram como trilha documental indexada
- Multi-commodity em produção (a troca é por `params/<commodity>.yml`, mas só cacau é validado)
- Autenticação, multi-tenant, cobrança
- Integração com sistema de gestão da cooperativa

## 6 · Critérios de sucesso

| # | Critério | Como se mede |
|---|---|---|
| S1 | Lixo entra, ficha padronizada sai | `processar_todos()` processa 60 produtores e detecta ao menos um ilegível, um vencido e um divergente |
| S2 | Conflito real aparece | Os 4 talhões plantados sobre embargo real saem como `bloqueio` na checagem 02 |
| S3 | Consistência documental funciona | Ao menos 3 regras distintas da checagem 05 disparam nos dados semeados |
| S4 | O dossiê parece documento oficial | PDF com os 8 blocos preenchidos, hash por anexo, data por checagem |
| S5 | **Autonomia é visível** | Injetar um embargo novo derruba 3 lotes e regenera 3 dossiês sem ninguém tocar em nada |
| S6 | A trilha de auditoria prova o S5 | Contador de autonomia lido da tabela `evento` |

**S5 é o critério que define o produto.** Sem ele, isto é um gerador de relatório.

## 7 · Regra de escrita dos laudos — requisito de produto, não de código

Todo laudo gravado em `checagem.texto` precisa conter:

1. o que foi comparado,
2. contra qual base,
3. **em que data a consulta foi feita**,
4. o resultado,
5. a conclusão em uma frase.

A data é o que dá validade jurídica ao instantâneo — o dossiê é um snapshot assinado de um estado verificado continuamente. **Sem a data, o laudo não presta.**

## 8 · Riscos e ordem de corte

| Risco | Mitigação |
|---|---|
| Base do Ibama fora do ar ou mudou de formato | Falhar alto e dizer o que aconteceu. **Nunca simular o dado.** |
| OCR (tesseract) não instala | Tratar imagem como `ilegivel` e seguir. Não gastar tempo. |
| PDF quebra na hora da demo | HTML é salvo sempre junto do PDF. Mostra-se o HTML. |
| Trilha B atrasa | É a mais crítica; recebe a pessoa mais forte. Sem ela não há conflito para mostrar. |
| Deriva de contrato entre trilhas | Esquema congelado; mudança só via PM, anunciada. |

**Ordem de corte, do primeiro a cair para o último:** mapa no dossiê → telas 1 e 3 → regras **F** da checagem 05 (mantendo as nove regras **B**) → refinamento da checagem 03 → checagem 07 (Lista Suja).

A checagem 07 é barata e fecha a categoria (e) — se o tempo apertar, ela cai antes da 04, mas só depois de tudo o que vem acima dela nesta lista.

**Nunca caem:** checagem 02 (embargo), **checagem 04 — sobreposição de direitos**, checagem 06, fila de exceções, vigilância, dossiê em PDF. A checagem 04 é a única prova possível das categorias (f), (g) e parte de (d) — se ela cair, três das oito categorias de legalidade não fecham nunca e o produto deixa de provar o que promete no palco.

## 9 · Pendências de negócio a destravar

Duas tarefas de vinte minutos que valem mais que duas horas de código:

1. Abrir o **Parque Cafeeiro** e o **Cacaupará** e registrar o que eles realmente emitem — define o contorno exato do "já é commodity gratuita".
2. Confirmar uma **faixa defensável de produtividade em kg/ha para a Transamazônica** — a checagem 06 depende dela. Referência de partida: Pará ≈ 900 kg/ha, Bahia ≈ 270 kg/ha.

Ambas ficam registradas em `FONTES-DE-DADOS.md` quando resolvidas.
