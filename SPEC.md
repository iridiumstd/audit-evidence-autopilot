# SPEC — Evidence Autopilot EUDR

Especificação funcional e técnica. O *porquê de produto* está em `PRD.md`; as decisões de arquitetura em `ADR.md`; o catálogo de recursos externos em `ARD.md`.

> **Atualizado conforme contrato.md v2 e correcoes-spec_1.md (30/08/2026); em conflito, esses dois arquivos ganham.**

**Regra que governa este documento:** o contrato de dados da seção 2 é congelado. Nenhuma trilha o altera sozinha — mudança é decisão de PM, anunciada no grupo, com confirmação de quem depende do campo.

---

## 1 · Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.11+ | É onde estão geopandas, OCR e o ferramental de PDF. |
| Banco | SQLite, arquivo único em `dados/app.db` | Zero configuração, cabe no git, todo mundo abre pelo mesmo caminho. |
| Geoespacial | geopandas + shapely | `sjoin` resolve sobreposição em uma linha. |
| Leitura de documento | pdfplumber (PDF), pytesseract (imagem), pandas (planilha) | Instalam sem drama. Se o tesseract travar, essa máquina usa só PDF. |
| Dossiê | Template HTML (jinja2) → PDF (playwright) | HTML é fácil de iterar e é o plano B se o PDF quebrar na demo. |
| Interface | streamlit | Três telas em duas horas, sem front-end. |
| Agendamento | Laço com `sleep` em `vigilancia.py`, **não cron** | Em demo, cron é risco. Laço é visível e controlável. |

Ninguém instala biblioteca nova sem avisar. A primeira pergunta é sempre "dá para fazer com o que já tem?".

---

## 2 · Contrato de dados

### 2.1 Estrutura de pastas (fixa)

```text
dados/app.db                        banco SQLite, fonte única de verdade
dados/entrada/<produtor_slug>/      arquivos crus, como o usuário sobe
dados/padronizado/<produtor_slug>/  arquivos renomeados pelo sistema
dados/bases/                        shapefiles do Ibama e alertas
params/cacau.yml                    parâmetros da commodity
saida/dossies/<lote_codigo>/vN.pdf
saida/dossies/<lote_codigo>/vN.html
app.py                              interface streamlit
ingestao.py
verificacao.py
dossie.py
vigilancia.py
```

### 2.2 Esquema do banco (fixo — não renomeie campo nenhum)

```sql
produtor(id TEXT PK, nome, cpf, municipio, uf, cooperativa, slug)

talhao(id TEXT PK, produtor_id, nome, area_ha REAL,
       geom_wkt TEXT, tipo_geom TEXT,      -- 'ponto' | 'poligono'
       car_numero TEXT, car_situacao TEXT)

documento(id TEXT PK, produtor_id, talhao_id NULL,
          arquivo_origem TEXT, arquivo_padronizado TEXT,
          tipo TEXT,                        -- ver params/cacau.yml
          campos_json TEXT,                 -- campos extraidos
          data_emissao TEXT, data_validade TEXT,
          hash_sha256 TEXT,
          confianca REAL,                   -- 0.0 a 1.0
          status TEXT,                      -- 'ok'|'ilegivel'|'vencido'|'divergente'
          versao INTEGER)                   -- v01, v02… o anterior nunca é apagado

lote(id TEXT PK, codigo TEXT, commodity, safra, quantidade_kg REAL,
     comprador, data_embarque TEXT,
     status TEXT)                           -- 'verde'|'atencao'|'bloqueado'

lote_talhao(lote_id, talhao_id, quantidade_kg REAL)

checagem(id TEXT PK, talhao_id, codigo TEXT,   -- '01'..'07', ou codigo de regra 'R17' na 05
         perna TEXT,                            -- 'A' | 'B'
         categoria TEXT,                        -- 'A' (perna geometrica) ou 'a'..'h'
         severidade TEXT,                       -- 'B' bloqueia aptidao · 'F' flag para revisao humana
         resultado TEXT,                        -- 'conforme'|'excecao'|'bloqueio'
         texto TEXT, fonte TEXT, data_execucao TEXT, evidencia_json TEXT)

excecao(id TEXT PK, tipo TEXT, talhao_id NULL, documento_id NULL,
        lotes_afetados TEXT,                    -- ids separados por virgula
        descricao TEXT,
        status TEXT,                            -- 'aberta'|'resolvida'
        resolvido_por TEXT, resolvido_em TEXT)

aptidao(id TEXT PK, produtor_id TEXT, camada INTEGER,   -- 1..5
        satisfeita INTEGER,          -- 0/1
        via_documento_id TEXT,       -- qual documento fechou a camada
        forca TEXT,                  -- 'forte' | 'media' | 'fraca'
        avaliado_em TEXT)

dossie(id TEXT PK, lote_id, versao INTEGER, gerado_em TEXT,
       status TEXT,                             -- 'rascunho'|'aprovado'
       aprovado_por TEXT, hash_sha256 TEXT,
       caminho_pdf TEXT, caminho_html TEXT, diff TEXT)

evento(id TEXT PK, timestamp TEXT, ator TEXT,   -- 'sistema' | 'humano'
       acao TEXT, entidade TEXT, entidade_id TEXT, detalhe TEXT)
```

### Aptidão em 5 camadas

`aptidao` não é booleana por produtor — é uma linha por camada. O conjunto mínimo tem cinco camadas, e cada uma aceita alternativas em ordem de força probatória:

| # | Camada | Como fecha |
|---|---|---|
| 1 | Parcela geolocalizada — Art. 9(1)(d) + 2(28) | Polígono do talhão dentro do perímetro de um CAR não-cancelado. Ativo e Pendente passam; Cancelado e Suspenso reprovam. Ponto com 6 casas decimais só vale para talhão ≤ 4 ha. Única exigência sem substituto possível. |
| 2 | Direito de uso — Art. 9(1)(h) + 2(40)(a) | **Um**, nesta ordem: `matrícula em nome do produtor` → `título (TD, CDRU, CCU)` → `contrato ou declaração de posse corroborado por CCIR ou DITR/CIB em nome próprio`. |
| 3 | Identidade e vínculo — Art. 9(1)(e) | CPF válido + CAF ativo. Na falta: ficha de cooperado + inscrição estadual de produtor. |
| 4 | Transação, quantidade e data — Art. 9(1)(b), (d) | NF-e do produtor **ou** contranota da cooperativa nomeando o produtor como remetente, com romaneio vinculado quando existir. |
| 5 | Checagens negativas na data do dossiê — Art. 9(1)(g) + 10(2) | Geradas pelo sistema — ver "Duas naturezas de evidência" abaixo. |

A camada 2 é a crítica: um checklist rígido que exigisse matrícula reprovaria a maioria dos produtores da Amazônia por não ter um papel que a lei local não exige. `aptidao.forca` registra o degrau da hierarquia que fechou a camada — um lote fechado só com camadas 2 fracas é conforme, mas é o que precisa de atenção antes de assinar.

### Duas naturezas de evidência

A montagem do dossiê itera sobre as **oito categorias de legalidade (a–h)**, nunca sobre a lista de documentos, e cada categoria fecha por **documento entregue** ou por **checagem gerada**. As categorias (f), (g) e parte de (d) não têm documento positivo emitido para o produtor — não existe certidão ou órgão a procurar — e só fecham por checagem negativa georreferenciada (sobreposição de direitos, embargo, Lista Suja).

> **É evidência que o sistema gera, não que o produtor entrega.**

`checagem` ganha o campo `categoria` (a–h) para registrar isso. Consequência técnica: consulta datada envelhece sozinha — reexecutar não é um extra, é a manutenção da prova, e é de onde a vigilância contínua nasce.

### Vocabulário de `excecao.tipo`

Nem toda ausência é lacuna. `excecao.tipo` aceita quatro valores:

| Valor | Significa | Conta como lacuna no painel? |
|---|---|---|
| `bloqueio` | não embarca até resolver | sim |
| `lacuna_sanavel` | falta documento que o produtor pode conseguir | **sim — só este** |
| `dispensa_documentada` | ausência é a situação regular (licença ambiental, ASV, SIGEF) | não |
| `nao_sanavel_pelo_produtor` | CAR pendente de análise, e coisas do gênero | não |

**A contagem de lacunas do painel só soma `lacuna_sanavel`.**

### 2.3 Quem escreve onde — regra absoluta

| Trilha | Escreve | Lê |
|---|---|---|
| **0 · Fundação** | cria tudo; popula `produtor`, `talhao`, `lote`, `lote_talhao` | — |
| **A · Ingestão** | `documento` | `produtor`, `talhao` |
| **B · Verificação** | `checagem`, `excecao`, **`aptidao`** | `talhao`, `documento`, `lote_talhao` |
| **C · Dossiê** | `dossie` | tudo, **incluindo `aptidao`** |
| **D · Vigilância** | `lote.status`; reabre dossiê chamando a Trilha C | tudo |

**Todas** as trilhas escrevem em `evento` a cada ação. **Nunca apague linha de `evento`** — a trilha de auditoria é o que prova autonomia no palco.

### 2.4 Regras de ouro

- Nenhuma trilha edita arquivo `.py` de outra trilha.
- Toda função pública recebe e devolve dicts simples, nunca objetos.
- Toda escrita no banco passa por funções de `db.py`.
- Datas sempre em ISO 8601, texto: `'2026-08-30T14:22:00'`.
- IDs sempre string, gerados com `uuid4().hex[:12]`.

---

## 3 · Ingestão — `ingestao.py`

**Fronteira:** os arquivos chegam já agrupados por produtor, uma pasta por produtor. A atribuição vem do agrupamento, nunca de adivinhação.

### `processar_produtor(produtor_slug) -> dict`

1. Lê todos os arquivos de `dados/entrada/<produtor_slug>/`.
2. Por arquivo: calcula SHA-256; extrai texto (pdfplumber / pytesseract / pandas); identifica o **tipo** pelas palavras-chave de `params/cacau.yml`; extrai campos (número do documento, CPF/CNPJ do titular, nome, datas de emissão e validade, área, município); atribui **confiança** de 0 a 1.
3. Aplica o status:

   | Status | Condição |
   |---|---|
   | `ilegivel` | texto extraído vazio **ou** confiança < 0.4 |
   | `vencido` | `data_validade` anterior a hoje |
   | `divergente` | CPF ou nome no documento difere do produtor do grupo |
   | `ok` | nenhum dos anteriores |

   Tipo não reconhecido grava `tipo='desconhecido'`. **Não chutar.**
4. Copia para `dados/padronizado/<produtor_slug>/` com nomenclatura canônica:

   ```
   {TIPO}_{TITULAR-CPF}_{AAAAMMDD}_{vN}.{ext}

   CAR-DEM_70123456789_20260514_v02.pdf
   NFP_70123456789_20260812_v01.xml
   EMB_70123456789_20260830_v01.pdf
   NF-EXP_LOTE-2026-014_20260901_v01.xml
   ```

   - **TIPO** — vocabulário controlado: `CAR-REC CAR-DEM CCIR DITR CND-ITR MATR TIT POSSE SIGEF NFP NFA NF4 NF-ENT IE-PR CAF DAP ROM FCOOP LIC ASV EMB CERT-RA CERT-ORG CERT-FT DECL TRAB NF-EXP CFIT LAUDO`. Não classificado é `NAOCLASS` — nunca um palpite.
   - **TITULAR** — CPF de 11 dígitos, não nome. Nomes colidem e divergem entre documentos; o CPF é a chave de junção de todas as checagens. Documentos de lote: `LOTE-{id}`. Documentos da cooperativa: CNPJ.
   - **DATA** — data de emissão do documento, não a do upload. Se ilegível, data do upload com sufixo `u`.
   - **VERSÃO** — `v01`, `v02`… quando chega documento mais novo do mesmo tipo e titular. **O anterior nunca é apagado** — o EUDR exige guarda de cinco anos e a trilha de auditoria é parte do produto. `documento.versao` grava o número.
   - Nome original vai para `documento.arquivo_origem`, nunca para o nome novo. Extensão sempre verdadeira ao conteúdo — foto de DANFE é `.jpg`, não PDF requalificado.
   - Checagens geradas pelo sistema (`EMB`, `LAUDO`) datam do dia da execução — o versionamento delas **é** o registro da vigilância contínua.

   **Armadilha de parsing da NF-e:** na NF-e de pessoa física as séries ficam na faixa **920–969** e **o CPF entra com zeros à esquerda nas 14 posições do campo CNPJ da chave de acesso**. Parser que espera CNPJ erra o produtor em toda nota de produtor. Nota **modelo 4** (papel, legado) não tem chave de acesso. **CFOP 5102 ou 6102 é revenda** — atravessador, não produção própria; esse elo precisa ser reclassificado como intermediário, não descartado.
5. Grava uma linha em `documento` por arquivo e chama `registrar_evento` a cada arquivo.
6. Devolve: contagem de arquivos, contagem por status, e o **mapa de lacunas** — quais documentos do conjunto mínimo de `params/cacau.yml` faltam para esse produtor.

O mapa de lacunas é entregável, não detalhe.

### `processar_todos()`

Roda os 60 produtores e imprime resumo. **A saída de terminal vai ao vivo na apresentação** — legível e caprichada, progresso arquivo a arquivo.

**Pronto quando:** terminal limpo processa os 60 produtores, popula `documento`, cria os padronizados, e o resumo mostra pelo menos um `ilegivel`, um `vencido` e um `divergente`.

---

## 4 · Verificação — `verificacao.py`

Assinatura única: `checagem_NN(talhao_id) -> dict` com `resultado`, `texto`, `fonte`, `evidencia`.
Orquestrador: `verificar_talhao(talhao_id)` roda as sete e grava.

**Cada checagem declara a que perna pertence, e grava `categoria` e `severidade`.** As da perna A usam `categoria = 'A'`.

| Código | Nome | Perna | Categoria | Regra |
|---|---|---|---|---|
| 01 | Desmate pós-2020 | A | A | Interseção com alerta posterior a 31/12/2020 → `bloqueio` |
| 02 | Embargo do Ibama e LDI-PA | B | b, d | Interseção **por polígono e por CPF** → `bloqueio`; distância < 500 m → `excecao` |
| 03 | CAR e posse | B | a, b | CAR ativo, geometria compatível, hierarquia da camada 2 de aptidão; divergência de titular → `excecao` |
| 04 | Sobreposição de direitos | B | **d, f, g** | Interseção com TI, quilombo ou UC — **insubstituível: única prova possível de (f), (g) e parte de (d)** |
| 05 | Consistência documental | B | todas | R01–R50, cada uma marcada `B` (bloqueia aptidão) ou `F` (flag) |
| 06 | Coerência de volume e fiscal | B | h | Volume vs. área × produtividade de referência; NCM, CFOP, chave duplicada |
| 07 | **Lista Suja do MTE** | B | **e, f** | CPF de todos os elos do lote contra a Lista Suja vigente, matching por CPF, nunca por nome |

**Sobre a checagem 07:** é nova porque as categorias (e) trabalhista e (f) direitos humanos não têm documento positivo emitido para o produtor — não existe certidão pública de conformidade trabalhista para pessoa física sem empregados. A prova é Lista Suja + CAF + autodeclaração, e a Lista Suja é a parte automatizável: planilha semestral do MTE.

### 4.1 Checagem 02 — a que dispara na demo

Capriche na evidência: guarde **o número do termo de embargo** e **a área de interseção**. É a checagem do momento de 3:15.

### 4.2 Checagem 05 — a joia

Não é "o documento existe". É o cruzamento entre documentos do mesmo produtor, agora com **cinquenta regras, R01 a R50**, cada uma marcada `B` (bloqueia aptidão até resolver) ou `F` (flag para revisão humana), agrupadas em: identidade e titularidade, área e geometria, jurisdição e localização, vigência e tempo, volume e massa, documento fiscal. **Cada regra é uma função separada e numerada**, devolvendo dict com `resultado`, `texto`, `evidencia`, `codigo` (o código da regra) e `severidade`.

**Se não der para implementar as cinquenta**, estas nove cobrem as cinco camadas de aptidão e rodam sobre dado público real — todas severidade `B`:

| Regra | Sev. | O que checa |
|---|---|---|
| R17 | B | Polígono intersecta desmatamento PRODES/alerta validado pós-31/12/2020 — desqualificação automática |
| R16 | B | Polígono intersecta área embargada (Ibama ou LDI-PA) |
| R13 | B | Polígono do talhão não contido no perímetro do CAR declarado |
| R29 | B | CAR Cancelado (Suspenso ou Pendente por sobreposição grave = `F`, conforme o motivo) |
| R08 | B | CPF/CNPJ de qualquer elo do lote na Lista Suja vigente |
| R18 | B | Polígono intersecta Terra Indígena homologada/regularizada (delimitada/declarada = `F`) |
| R19 | B | Polígono intersecta UC de proteção integral (uso sustentável = `F`) |
| R01 | B | CPF do emitente da NF ≠ CPF do titular do CAR do talhão de origem (cônjuge co-titular do CAF como match secundário rebaixa para `F`) |
| R14 | B | Talhão > 4 ha entregue como ponto (viola o Art. 2(28)) |

**R39 está desligada.** Compararia a soma das notas do produtor contra área × produtividade máxima regional, mas esse parâmetro não foi levantado — ver regra de ouro nº 8 do contrato.md. Deixar desligada é melhor que inventar um número contestável.

**Nomenclatura v1, superada** — as sete regras originais, mantidas aqui só como histórico; foram substituídas pelo conjunto R01–R50 acima:

| Regra (v1) | O que detectava |
|---|---|
| R1 | CPF do CAR ≠ CPF da nota fiscal |
| R2 | Área declarada no talhão > área do CAR |
| R3 | Documento vencido na data prevista de embarque do lote |
| R4 | Município da matrícula ≠ município do CAR |
| R5 | Titular do arrendamento ≠ produtor do grupo |
| R6 | Documento do conjunto mínimo ausente |
| R7 | Dois documentos do mesmo tipo, números diferentes, datas próximas |

**Cada exceção precisa dizer, em português claro, qual documento conflita com qual.** O texto vai impresso no dossiê e é lido por um auditor. Tolerâncias numéricas são parâmetros de calibração em `params/cacau.yml`, não norma.

### 4.3 Checagem 06 — coerência de volume

Volume entregue pelo produtor no lote comparado com `área dos talhões × produtividade de referência da região`, lida de `params/cacau.yml`.

| Faixa | Resultado |
|---|---|
| > 150% do esperado | `excecao` |
| > 300% do esperado | `bloqueio` |

Evidência guarda os três números: área, produtividade, volume.

### 4.4 Orquestração

- `verificar_tudo()` — roda todos os talhões.
- `recalcular_status_lotes()` — define `lote.status` pelo **pior** resultado entre os talhões que o compõem: qualquer `bloqueio` → `bloqueado`; qualquer `excecao` → `atencao`; senão `verde`.

Cada execução grava em `checagem` com `data_execucao`, e cria `excecao` quando o resultado não for `conforme`. `registrar_evento` sempre.

### 4.5 Regra de escrita do laudo

Todo `checagem.texto` contém: **(1)** o que foi comparado, **(2)** contra qual base, **(3) em que data a consulta foi feita**, **(4)** o resultado, **(5)** a conclusão em uma frase. Sem a data, o laudo não presta.

**Pronto quando:** `verificar_tudo()` roda os ~100 talhões, grava as checagens, os 4 talhões plantados sobre embargo real saem como `bloqueio` na 02, os limítrofes como `excecao`, e pelo menos 3 regras distintas da 05 disparam.

---

## 5 · Dossiê — `dossie.py`

`gerar_dossie(lote_id) -> dict`. Lê o estado **corrente** e o congela numa versão nova. **O dossiê nunca recalcula nada** — fotografa o que a verificação já apurou, com a data de cada checagem carimbada.

### Os oito blocos, nesta ordem

| # | Bloco | Conteúdo |
|---|---|---|
| 1 | Identificação do lote | código, commodity, safra, quantidade, comprador, data prevista de embarque, versão, data de geração |
| 2 | Sumário de conformidade | semáforo **separado por perna** — desmatamento de um lado, legalidade do outro, com contagem de talhões conformes, em exceção e bloqueados. É a primeira página que alguém lê. |
| 3 | Cadeia de custódia | produtor → talhão → nota fiscal → lote → contêiner: uma linha por elo, com o documento que sustenta cada um |
| 4 | Geolocalização | coordenadas por talhão, tipo (ponto/polígono), área. Mapa se der tempo. |
| 5 | Laudo por checagem | para cada uma das seis: o que foi comparado, contra qual base, **em que data**, resultado e conclusão |
| 6 | Anexos indexados | cada documento com tipo, origem, data de coleta, validade e **hash SHA-256**. O hash é o que transforma pasta de PDF em prova. |
| 7 | Trilha de auditoria | da tabela `evento`: quem ou o quê fez o quê e quando, distinguindo `sistema` de `humano`, mais o diff em relação à versão anterior |
| 8 | Selo de aprovação | nome, cargo, carimbo temporal. Sem aprovação, sai com marca de água **RASCUNHO** bem visível. |

### Versionamento

Cada geração incrementa `dossie.versao` para aquele lote, salva em `saida/dossies/<codigo>/vN.pdf` e `vN.html`, calcula o hash do PDF, e grava `diff` em português dizendo o que mudou — por exemplo: *"talhão TAL-014 passou de conforme para bloqueio na checagem 02"*.

`aprovar_dossie(dossie_id, nome, cargo)` gera versão nova com status `aprovado` e sem a marca de água.

### Design

Sóbrio e denso, de documento oficial e não de apresentação. Serifada para texto, monoespaçada para números e hashes. Cabeçalho e rodapé com código do lote, versão e paginação em todas as páginas. Precisa parecer algo que um auditor europeu receberia.

**HTML é salvo sempre junto do PDF.** Se o PDF falhar na apresentação, mostra-se o HTML.

---

## 6 · Vigilância — `vigilancia.py`

Laço a cada N segundos (parametrizável; **5 na demo**):

1. Relê as bases em `dados/bases/` e detecta polígono de embargo ou alerta ainda não visto.
2. Para cada talhão afetado, chama `verificacao.verificar_talhao(talhao_id)` — importa e usa, não reimplementa.
3. Chama `verificacao.recalcular_status_lotes()`.
4. Para todo lote cujo status **piorou**, chama `dossie.gerar_dossie(lote_id)`.
5. Cria a exceção correspondente e registra evento a cada passo.
6. Imprime no terminal, legível e um pouco dramático, cada coisa que fez. Essa saída aparece na tela durante a apresentação.

---

## 7 · Interface — `app.py`

| Tela | Conteúdo |
|---|---|
| **1 · Lotes** | Lista com semáforo por lote, **separado por perna** (desmatamento e legalidade em colunas distintas). Clicar abre talhões, dossiês, histórico de versões e link para o PDF. |
| **2 · Fila de exceções** | **A tela principal do produto** — não um painel de status verde. Exceções abertas com tipo, o que foi encontrado, lotes afetados e evidência. Dois botões: *excluir talhão do lote* e *marcar como resolvida*, ambos gravando quem resolveu e quando, e disparando regeração do dossiê. |
| **3 · Dossiê** | Visualiza o dossiê de um lote, com seletor de versão, diff entre versões, e botão de aprovar que pede nome e cargo. |

**Em todas as telas, no topo — o contador de autonomia:**

> N verificações executadas · N documentos processados · N dossiês regerados · N exceções para humano

Lido direto da tabela `evento`. É a prova visual de autonomia. Grande e bonito — é o número que o jurado anota.

Se faltar tempo, a **fila de exceções** é a que precisa existir.

---

## 8 · Dados semeados — `seed.py`

Semente fixa. Base gerada pela Trilha 0:

- **60 produtores** com nomes brasileiros plausíveis, CPF fictício de formato válido, municípios da região recortada, slug sem acento.
- **1 a 3 talhões por produtor** (~100 no total), área entre 2 e 10 ha, mistura de ponto e polígono, todos dentro da região.
- **4 talhões de propósito sobrepostos a polígonos de embargo reais**, e outros **3 quase encostando na borda**, para testar caso limítrofe.
- **3 lotes de embarque**, cada um com 10 a 40 produtores, **com sobreposição**: pelo menos um produtor precisa estar nos três lotes ao mesmo tempo. *A demonstração depende de um embargo derrubar três dossiês de uma vez.*
- **5 a 10 arquivos por produtor** em `dados/entrada/<produtor_slug>/`, com nomes ruins de verdade: `IMG_4471.jpg`, `doc scan (3).pdf`, `planilha final v2.xlsx`, `documento sem titulo.pdf`.

### Armadilhas plantadas (em produtores diferentes)

| Armadilha | O que exercita |
|---|---|
| Um arquivo ilegível | status `ilegivel` |
| Um documento vencido | status `vencido`, regra R3 |
| Um com CPF divergente do produtor do grupo | status `divergente`, regra R1 |
| Um duplicado com nome diferente | regra R7 |
| Um que não é documento nenhum (foto do cacau secando) | `tipo='desconhecido'` |

---

## 9 · `params/cacau.yml`

O arquivo que permite trocar de commodity sem tocar no código. Contém:

- lista de **tipos de documento** esperados, com nome canônico e palavras-chave de identificação
- **produtividade de referência** em kg/ha por região (Pará ≈ 900, Bahia ≈ 270), usada na checagem 06
- **regras de validade** por tipo de documento, em dias
- o **conjunto mínimo** de documentos que torna um produtor apto

---

## 10 · Teste de aceitação

Um comando, em `demo/roteiro.sh`, desde a primeira hora — mesmo quebrado. É a definição de pronto do projeto inteiro:

```bash
python seed.py
python ingestao.py --todos
python verificacao.py --tudo
python dossie.py --lote CAC-2026-114
python demo/injetar_embargo.py
# vigilancia.py reage e regenera tres dossies
```

`demo/injetar_embargo.py` adiciona um polígono de embargo novo cobrindo justamente o talhão do produtor que está nos três lotes. É o que roda ao vivo na apresentação.

**Pronto quando:** com `vigilancia.py` num terminal e o streamlit noutro, executar `demo/injetar_embargo.py` faz o terminal reagir em segundos, três lotes mudarem de status na interface sem recarregar manualmente, uma exceção aparecer na fila, e três dossiês novos ficarem disponíveis.

---

## 11 · Pontos de junção

| Quando | O que tem que estar verdadeiro | Se não estiver |
|---|---|---|
| Fim da hora 3 | Trilha 0 entregue: banco criado, 60 produtores, ~100 talhões, 3 lotes com sobreposição, grupos de arquivos gerados, base do Ibama recortada. As outras quatro trilhas já rodam contra o banco real. | Todo mundo para e ajuda a Trilha 0. Nada mais importa até isso existir. |
| Fim da hora 6 | A grava checagens e exceções; B popula a tabela `documento`; C gera um PDF com dados reais de pelo menos um lote. | Corte a checagem 04 e reduza a 05 a três regras. Não corte a 02 nem a 06. |
| Fim da hora 9 | O cenário completo roda: injetar embargo derruba três lotes e regenera três dossiês, sem ninguém tocar em nada. | Grave o vídeo do que funciona e apresente com ele. Não tente consertar de madrugada. |
