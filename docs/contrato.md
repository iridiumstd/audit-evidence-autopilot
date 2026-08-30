# Contrato de construção — leia antes de escrever qualquer linha

Este arquivo existe para impedir que cinco trilhas paralelas colidam.
**O esquema das tabelas está em `db.py` e é a única fonte de verdade.**
Aqui fica o que o código não consegue expressar.

> **Versão 2 — 30/08/2026.** Reescrito depois da frente de taxonomia documental.
> Mudaram o esquema (3 campos e 1 tabela), a tabela de quem escreve onde, a lista
> de checagens (entrou a 07), os invariantes do produto e a ordem de corte.
> **Este arquivo é autossuficiente: trabalhe por ele.**

---

## Estrutura de pastas (fixa)

```
dados/app.db                        banco SQLite, fonte única de verdade
dados/entrada/<produtor_slug>/      arquivos crus, como o usuário sobe
dados/padronizado/<produtor_slug>/  arquivos renomeados pelo sistema
dados/bases/                        camadas geoespaciais (embargo, alertas, TI, UC)
params/cacau.yml                    parâmetros da commodity
saida/dossies/<lote_codigo>/vN.pdf  e vN.html
docs/                               contrato.md · duas-pernas.md
demo/injetar_embargo.py             o gatilho da apresentação
demo/roteiro.sh                     o teste de aceitação

db.py  ingestao.py  verificacao.py  dossie.py  vigilancia.py  app.py  seed.py
```

**Precedência:** em caso de conflito, **este arquivo ganha** sobre
`duas-pernas.md`, que está desatualizado nas regras e na cobertura por categoria.
Use o `duas-pernas.md` só para o enquadramento conceitual das duas provas.

---

## Quem escreve onde — regra absoluta

| Trilha | Escreve nas tabelas | Lê | Arquivos que edita |
|---|---|---|---|
| **0 · Fundação** | cria tudo; popula `produtor`, `talhao`, `lote`, `lote_talhao` | — | `db.py`, `seed.py`, `params/`, `demo/` |
| **A · Ingestão** | `documento` | `produtor`, `talhao` | `ingestao.py` |
| **B · Verificação** | `checagem`, `excecao`, **`aptidao`** | `talhao`, `documento`, `lote_talhao` | `verificacao.py` |
| **C · Dossiê** | `dossie` | tudo, **incluindo `aptidao`** | `dossie.py`, templates |
| **D · Vigilância e telas** | `lote.status`; chama C para regerar | tudo | `vigilancia.py`, `app.py` |

**Todas** as trilhas escrevem em `evento` a cada ação, chamando
`db.registrar_evento(ator, acao, entidade, entidade_id, detalhe)`.

`ator` é sempre `'sistema'` ou `'humano'`. Nunca apague linha de `evento`:
a trilha de auditoria é o que prova autonomia no palco, e alimenta o contador
da interface via `db.contadores()`.

---

## Mudanças de esquema — aplicadas pela Trilha 0, só por ela

Isto é o anúncio previsto na regra de ouro nº 7. Ninguém aplica por conta própria:
cinco pessoas mexendo em `db.py` ao mesmo tempo é exatamente o que este arquivo existe para impedir.

```sql
-- NOVA
CREATE TABLE IF NOT EXISTS aptidao(
  id TEXT PRIMARY KEY, produtor_id TEXT, camada INTEGER,   -- 1..5
  satisfeita INTEGER,          -- 0/1
  via_documento_id TEXT,       -- qual documento fechou a camada
  forca TEXT,                  -- 'forte' | 'media' | 'fraca'
  avaliado_em TEXT);

-- ALTERAÇÕES
checagem   + categoria TEXT     -- 'A' (perna geométrica) ou 'a'..'h'
checagem   + severidade TEXT    -- 'B' bloqueia · 'F' flag
checagem     codigo             -- passa a ser o código da regra: 'R17'
documento  + versao INTEGER     -- v01, v02… o anterior nunca é apagado
excecao      tipo               -- vocabulário fixo, ver abaixo
```

`excecao.tipo` só aceita quatro valores:

| Valor | Significa | Conta como lacuna no painel? |
|---|---|---|
| `bloqueio` | não embarca até resolver | sim |
| `lacuna_sanavel` | falta documento que o produtor pode conseguir | **sim — só este** |
| `dispensa_documentada` | ausência é a situação regular (licença, ASV, SIGEF) | não |
| `nao_sanavel_pelo_produtor` | CAR pendente de análise, e coisas do gênero | não |

---

## As sete checagens

Toda checagem grava `categoria` e `severidade`. As de perna A usam `categoria = 'A'`.

| # | O que faz | Categorias | Fonte |
|---|---|---|---|
| **01** | Geolocalização e desmatamento: polígono com 6 casas decimais, talhão > 4 ha exige polígono, cruzamento com PRODES e alerta MapBiomas validado pós-31/12/2020 | A | PRODES/INPE, MapBiomas |
| **02** | Embargo: Ibama e LDI-PA, **por polígono e por CPF** | b, d | shapefile Ibama, LDI SEMAS-PA |
| **03** | CAR e direito de uso: CAR não-cancelado, talhão dentro do perímetro, hierarquia da camada 2 | a, b | SiCAR, documentos |
| **04** | Sobreposição de direitos: terra indígena, UC de proteção integral, território quilombola | **d, f, g** | FUNAI, CNUC, INCRA |
| **05** | Consistência documental: regras R01–R50, cada uma marcada B ou F | todas | interno |
| **06** | Coerência de volume e fiscal: lote vs NFs, chave duplicada, NCM, CFOP | h | interno |
| **07** | **Lista Suja do MTE, por CPF de todos os elos do lote** | **e, f** | MTE, planilha semestral |

**A checagem 07 é nova.** Foi criada porque as categorias (e) trabalhista e
(f) direitos humanos não têm documento positivo emitido para o produtor — não
existe certidão pública de conformidade trabalhista para pessoa física sem
empregados. A prova é Lista Suja + CAF + autodeclaração, e a parte automatizável
é a Lista Suja. É barata: planilha semestral, matching **por CPF, nunca por nome**.

### As nove regras que a checagem 05 tem que ter

O conjunto completo é R01–R50, em seis grupos: identidade e titularidade, área e
geometria, jurisdição, vigência, volume e massa, documento fiscal. Se não der
tempo de implementar todas, **estas nove são as que cobrem as cinco camadas e
rodam sobre dado público real**. Todas são severidade `B`.

| Regra | O que checa |
|---|---|
| **R17** | Polígono intersecta desmatamento PRODES ou alerta validado **pós-31/12/2020** — desqualificação automática do Art. 9(1)(d) |
| **R16** | Polígono intersecta área embargada (Ibama ou LDI-PA) |
| **R13** | Polígono do talhão não contido no perímetro do CAR declarado |
| **R29** | CAR com condição **Cancelado**. Suspenso ou Pendente por sobreposição grave = `F`; o motivo da pendência decide |
| **R08** | CPF ou CNPJ de qualquer elo do lote presente na Lista Suja vigente |
| **R18** | Polígono intersecta Terra Indígena homologada ou regularizada. Delimitada ou declarada = `F` |
| **R19** | Polígono intersecta UC de proteção integral. Uso sustentável = `F`, conferir plano de manejo ou CDRU |
| **R01** | CPF do emitente da NF ≠ CPF do titular do CAR do talhão de origem. Cônjuge co-titular do CAF como match secundário rebaixa para `F` |
| **R14** | Talhão maior que 4 ha entregue como ponto — viola o Art. 2(28) |

Tolerâncias numéricas são parâmetros de calibração em `params/cacau.yml`, não norma.
A **R39** (soma das notas do produtor contra área × produtividade máxima regional)
fica **desligada**: o parâmetro de produtividade não foi levantado — ver regra de ouro nº 8.

### As duas naturezas de evidência

Toda categoria fecha por **documento entregue** ou por **checagem gerada** — e a
montagem do dossiê itera sobre as **oito categorias**, nunca sobre a lista de
documentos. As categorias **(f)**, **(g)** e parte de **(d)** só fecham por
checagem: não existe papel para elas.

> É evidência que o sistema gera, não que o produtor entrega.

Consequência técnica: consulta datada envelhece sozinha. Reexecutar não é um
extra — é a manutenção da prova, e é de onde a vigilância contínua nasce.

---

## Invariantes do produto — o código não tem permissão de quebrar

Não são preferência de UX. São o posicionamento, e cada uma tem consequência de código.

1. **Nada é exigido do produtor.** Sem app do produtor, sem formulário, sem login,
   sem cadastro que ele preencha. Tudo entra pela mão da cooperativa, com o
   material que já existe. Toda tela que comece pedindo polígono, planilha
   padronizada ou XML estruturado está pedindo o resultado em vez do insumo.
2. **Aptidão é hierarquia, não checklist.** A camada 2 aceita
   `matrícula` → `título` → `posse + CCIR ou DITR em nome próprio`. Reprovar
   quem não tem matrícula é construir a barreira que o produto existe para
   remover.
3. **Ausência nem sempre é lacuna.** Licença ambiental, ASV e SIGEF ausentes são
   a situação regular na cacauicultura familiar. Débito de ITR é flag, não bloqueio.
4. **A lacuna é do documento, não da pessoa.** Microcópia literal:
   "falta o CCIR de Antônio", nunca "Antônio está irregular".
5. **O sistema não bloqueia, não cancela e não barra.** Ele marca, ordena e
   informa; quem decide é sempre o humano. Não emitimos a declaração, então não
   temos autoridade sobre a carga.
6. **As duas provas não se compensam.** Desmatamento pós-31/12/2020 desqualifica
   a parcela inteira **mesmo com ASV legal**, e desqualifica **toda a produção
   dela**, sem proporcionalidade. Nenhuma regra pode deixar evidência de
   legalidade compensar falha geométrica.

---

## Nomenclatura de arquivo — Trilha A

```
{TIPO}_{TITULAR}_{AAAAMMDD}_{VERSAO}.{ext}

CAR-DEM_70123456789_20260514_v02.pdf
NFP_70123456789_20260812_v01.xml
NF-EXP_LOTE-2026-014_20260901_v01.xml
```

- **TIPO** — vocabulário controlado: `CAR-REC CAR-DEM CCIR DITR CND-ITR MATR TIT
  POSSE SIGEF NFP NFA NF4 NF-ENT IE-PR CAF DAP ROM FCOOP LIC ASV EMB CERT-RA
  CERT-ORG CERT-FT DECL TRAB NF-EXP CFIT LAUDO`. Não classificado é `NAOCLASS` —
  nunca um palpite.
- **TITULAR** — CPF de 11 dígitos. Nomes colidem; o CPF é a chave de junção de
  todas as checagens. Documentos de lote: `LOTE-{id}`. Da cooperativa: CNPJ.
- **DATA** — emissão do documento, não upload. Ilegível: data do upload com sufixo `u`.
- **VERSÃO** — incrementa por tipo e titular. **O anterior nunca é apagado**:
  o EUDR exige guarda de 5 anos e a trilha de auditoria é parte do produto.
- Nome original vai para `documento.arquivo_origem`, nunca para o nome novo.
  Extensão verdadeira ao conteúdo — foto de DANFE é `.jpg`.

**Armadilha de parsing:** na NF-e de pessoa física as séries ficam na faixa
**920–969** e **o CPF entra com zeros à esquerda nas 14 posições do campo CNPJ
da chave de acesso**. Parser que espera CNPJ erra o produtor em toda nota.
Nota modelo 4 não tem chave. **CFOP 5102/6102 é revenda** — atravessador:
reclassifique o elo como intermediário, não descarte.

---

## Regras de ouro

1. **Ninguém edita arquivo `.py` de outra trilha.** Precisa de algo de outra
   trilha? Importe e use. Se a função ainda não existe, escreva uma falsa com a
   mesma assinatura e troque no ponto de junção.
2. **Toda escrita no banco passa por `db.py`.** Nada de `sqlite3` solto.
3. **Toda função pública recebe e devolve `dict` simples**, nunca objeto.
4. **Datas sempre em ISO 8601 como texto:** `'2026-08-30T14:22:00'`. Use `db.agora()`.
5. **IDs sempre string**, gerados com `db.novo_id()`.
6. **Nenhuma biblioteca nova sem avisar no grupo.** Primeira pergunta:
   dá para fazer com o que já tem?
7. **Ninguém muda o esquema sozinho.** Mudança de campo é decisão da PM,
   anunciada no grupo, e quem depende do campo confirma que viu.
8. **Nenhum número inventado vira parâmetro.** Se a fonte não foi levantada,
   o parâmetro fica vazio e a regra desligada. Vale hoje para a produtividade
   máxima regional da R39.

---

## Stack decidida — não reabra

Python 3.11+ · SQLite em `dados/app.db` · geopandas e shapely ·
pdfplumber para PDF e pytesseract para imagem · template HTML renderizado a PDF
com playwright · streamlit para a interface · vigilância como laço com sleep,
não cron.

O dossiê salva **sempre HTML junto com o PDF**: se o PDF falhar na
apresentação, mostramos o HTML e a demo sobrevive.

---

## Teste de aceitação do projeto inteiro

Está em `demo/roteiro.sh`. Mantenha-o desde a primeira hora, mesmo quebrado.

```sh
python seed.py
python ingestao.py --todos
python verificacao.py --tudo
python dossie.py --lote CAC-2026-114
python demo/injetar_embargo.py
# vigilancia.py reage: 3 lotes sao marcados, 3 dossies sao regerados sozinhos
```

Quando isso roda limpo do começo ao fim, o MVP está pronto.

---

## Ordem de corte, se atrasar

Cai primeiro, do topo para baixo:

1. mapa dentro do dossiê
2. telas 1 e 3 da interface
3. as regras **F** da checagem 05 — mantenha as nove **B** da tabela acima
4. o refinamento da checagem 03 — mantenha o CAR; a hierarquia completa da
   camada 2 pode ficar simplificada

**Nunca caem:** checagem 01 (desmatamento), checagem 02 (embargo),
**checagem 04 (sobreposição de direitos)**, checagem 06 (coerência de volume),
fila de exceções, vigilância, dossiê em PDF.

> **Por que a 04 saiu da lista de corte:** ela é a única prova possível das
> categorias (f), (g) e parte de (d). Se cair, três das oito categorias de
> legalidade não fecham nunca e o produto deixa de provar o que promete no palco.
> A checagem 07 (Lista Suja) é barata e fecha (e) — se o tempo apertar, ela cai
> antes da 04, mas depois de tudo no item 4.

A saída de terminal é entregável: metade da demonstração é terminal, não
interface. Faça o que você imprime ser legível e caprichado.
