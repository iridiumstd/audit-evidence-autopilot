# Correções de spec

**Evidence Autopilot EUDR · ATON · para quem está escrevendo PRD e spec**

Sete coisas que a taxonomia documental e o perfil de cliente mudaram depois que as trilhas foram escritas. Cada uma é barata agora e cara depois — três mudam o modelo de dados, duas mudam o que o produto tem permissão de fazer, e uma corrige a ordem de corte do contrato.

Legenda: **[BLOQUEIA]** = se ficar errado, o produto contradiz a própria tese · **[REFATORAÇÃO]** = dá para fazer depois, mas dói.

---

## ⚠ O que este arquivo torna desatualizado

Leia isto antes de seguir qualquer um dos outros dois documentos do `docs/`.

| Arquivo | O que ficou desatualizado | Onde está o certo |
|---|---|---|
| `docs/duas-pernas.md` | **As sete regras de inconsistência** escritas à mão. Foram substituídas por R01–R50, com severidade B/F. A lista de 42 evidências também: são **29 tipos documentais**, 25 na perna de legalidade, em 9 emissores. | Seção **04** deste arquivo |
| `docs/contrato.md` | **A ordem de corte** (manda derrubar a checagem 04, que virou insubstituível), o **esquema em `db.py`** (faltam 3 campos e 1 tabela) e a **tabela de quem escreve onde** (a nova tabela `aptidao` não tem dono) | Seção **07** deste arquivo |

O resto de ambos continua valendo. Em caso de conflito entre um deles e este arquivo, **este arquivo ganha** — ele é posterior e é a decisão da PM prevista na regra de ouro nº 7 do contrato.

---

## 01 · Aptidão é hierarquia de alternativas, não checklist  **[BLOQUEIA]**

Esta é a correção mais importante da lista. Se o spec descrever aptidão como uma lista de documentos obrigatórios, o produto exclui exatamente a base que a gente diz que vem incluir.

A taxonomia fechou o **conjunto mínimo em cinco camadas**, e cada camada aceita alternativas **em ordem de força probatória**. A camada crítica é a segunda:

> **Camada 2 · direito de uso da área — Art. 9(1)(h)**
> **Um** entre, nesta ordem: `matrícula em nome do produtor` → `título (TD, CDRU, CCU)` → `contrato ou declaração de posse corroborado por CCIR ou DITR/CIB em nome próprio`.

**Por que a hierarquia existe:** a FAQ da Comissão diz que, se a lei local não exige título formal para produzir e comercializar, o Regulamento também não exige — o que o Art. 9(1)(h) pede é evidência *do arranjo de uso*. E o arranjo real da Amazônia é posse mais cadastro fiscal em nome próprio. Matrícula é minoria na base e o SIGEF só passa a ser obrigatório em 2029. Um checklist rígido reprovaria a maioria dos produtores por não ter um papel que a lei não exige deles.

As outras quatro camadas:

| # | Camada | Como fecha |
|---|---|---|
| 1 | Parcela geolocalizada — Art. 9(1)(d) + 2(28) | Polígono do talhão dentro do perímetro de um CAR não-cancelado. **Ativo e Pendente passam; Cancelado e Suspenso reprovam.** Ponto com 6 casas decimais só vale para talhão ≤ 4 ha. Única exigência sem substituto possível. |
| 2 | Direito de uso — Art. 9(1)(h) + 2(40)(a) | Ver hierarquia acima. |
| 3 | Identidade e vínculo — Art. 9(1)(e) | CPF válido + CAF ativo. Na falta: ficha de cooperado + inscrição estadual de produtor. |
| 4 | Transação, quantidade e data — Art. 9(1)(b), (d) | NF-e do produtor **ou** contranota da cooperativa nomeando o produtor como remetente, com romaneio vinculado quando existir. |
| 5 | Checagens negativas na data do dossiê — Art. 9(1)(g) + 10(2) | Geradas pelo sistema. Ver item 02. |

### O que muda no banco

Não existe tabela de aptidão. Precisa existir, e ela não é booleana:

```sql
CREATE TABLE aptidao(
  id TEXT PRIMARY KEY, produtor_id TEXT, camada INTEGER,   -- 1..5
  satisfeita INTEGER,          -- 0/1
  via_documento_id TEXT,       -- qual documento fechou a camada
  forca TEXT,                  -- 'forte' | 'media' | 'fraca'
  avaliado_em TEXT);
```

A `forca` importa: um lote fechado só com camadas 2 fracas é conforme, mas é o lote que a Cláudia quer ver antes de assinar.

---

## 02 · Existem dois tipos de evidência, e o modelo só prevê um  **[BLOQUEIA]**

Três das oito categorias de legalidade **não têm documento positivo emitido para o produtor**. Direitos humanos (f), consentimento prévio (g) e parte de direitos de terceiros (d) não se provam com papel — não há certidão a pedir nem órgão a procurar.

Provam-se por **checagem negativa georreferenciada**:

- o polígono não intersecta terra indígena, unidade de conservação de proteção integral ou território quilombola;
- não está sob embargo do Ibama nem da LDI-PA (cruzar **por polígono**, não só por CPF — embargos aparecem com CPF divergente: posseiro, herdeiro, meeiro);
- o CPF não está na Lista Suja do MTE.

E não existe certidão pública de conformidade trabalhista para pessoa física sem empregados — o substituto é o trio Lista Suja + CAF + autodeclaração.

**O risco concreto:** se o dossiê montar a conformidade percorrendo os documentos entregues, essas três categorias **nunca fecham** — não porque falta documento, mas porque documento não é o instrumento. O time vai passar horas caçando um papel que não existe. Pior: a tela vai mostrar lacuna permanente em três categorias, e a demo cai.

### O que o spec precisa dizer

A montagem do dossiê itera sobre as **oito categorias**, e cada uma é satisfeita por documento **ou** por checagem — nunca só por documento.

`checagem` ganha o campo `categoria` (a–h); hoje só tem `perna`. A ficha da categoria mostra a origem da prova, porque é isso que o auditor vai querer ver.

> **É evidência que o sistema gera, não que o produtor entrega.**

Essa frase vai para o palco e para o spec com as mesmas palavras. É também o motivo técnico da vigilância contínua: consulta datada envelhece sozinha, e refazer não é um extra — é a manutenção da prova.

---

## 03 · Ausência de documento nem sempre é lacuna  **[BLOQUEIA]**

Se o sistema tratar toda ausência como pendência, ele cria a barreira que a gente diz estar removendo.

| Ausência | Estado correto | Por quê |
|---|---|---|
| **Licença ambiental** | Regular, com dispensa documentada | Cacauicultura familiar é tipicamente dispensada. Distinguir "não tem porque é dispensado" de "deveria ter e não tem". |
| **SIGEF** | Esperado | Obrigação só em 21/10/2029 (Dec. 12.689/2025). Em 2026, imóveis < 25 ha não estão obrigados. Vira lacuna só se o comprador exigir precisão de agrimensura. |
| **ASV / AUTEF** | Esperado | SAF de cacau em área consolidada não exige; cabruca não suprime. Ausência é o cenário normal — a presença é que é rara. |
| **CND-ITR / débito de ITR** | Flag, nunca bloqueio | Débito de ITR não torna a produção ilegal. |
| **CAR "Pendente"** | Registra condição e data | ~0,4% dos imóveis tiveram análise completa em dez anos. Pendente é o estado do sistema, não falha do produtor — e ele não tem como resolver. |

### O que muda no banco

`excecao.tipo` precisa de pelo menos quatro valores distintos:

- `bloqueio`
- `lacuna_sanavel`
- `dispensa_documentada`
- `nao_sanavel_pelo_produtor` — para o CAR pendente

**A contagem de lacunas do painel só soma `lacuna_sanavel`.**

---

## 04 · As checagens agora têm 50 regras e duas severidades  **[REFATORAÇÃO]**

O `docs/duas-pernas.md` que a Trilha B recebeu tem sete regras escritas à mão. A taxonomia entregou **cinquenta, de R01 a R50**, cada uma marcada como **B** (bloqueia aptidão até resolver) ou **F** (flag para revisão humana). Estão agrupadas em: identidade e titularidade, área e geometria, jurisdição e localização, vigência e tempo, volume e massa, documento fiscal.

### O que muda no banco

`checagem` precisa de `severidade TEXT` com `'B'` ou `'F'`, e `codigo` passa a carregar o código da regra (`R17`, `R39`). Sem isso não há como o dossiê distinguir "não embarca" de "olhe isto antes de assinar" — que é exatamente a decisão que a tela da manhã apresenta à Cláudia.

### Se não der para implementar as cinquenta

Ordem de valor para o MVP — estas nove cobrem as cinco camadas e rodam sobre dado público real:

| Regra | Sev. | O que checa |
|---|---|---|
| R17 | B | Polígono intersecta desmatamento PRODES/alerta validado pós-31/12/2020 — desqualificação automática |
| R16 | B | Polígono intersecta área embargada (Ibama ou LDI-PA) |
| R13 | B | Polígono do talhão não contido no perímetro do CAR declarado |
| R29 | B | CAR Cancelado |
| R08 | B | CPF/CNPJ de qualquer elo do lote na Lista Suja vigente |
| R18 | B | Polígono intersecta Terra Indígena homologada/regularizada (delimitada/declarada = F) |
| R19 | B | Polígono intersecta UC de proteção integral (uso sustentável = F) |
| R01 | B | CPF do emitente da NF ≠ CPF do titular do CAR do talhão de origem |
| R14 | B | Talhão > 4 ha entregue como ponto (viola Art. 2(28)) |

### Não hardcodar a R39

A R39 compara a soma das notas do produtor contra área × produtividade máxima regional — e a própria taxonomia registra que **esse parâmetro não foi levantado**. Deixar como parâmetro de calibração vazio, com a regra desligada, é melhor que inventar um número que a banca pode contestar.

---

## 05 · Nomenclatura e a armadilha de parsing da NF-e  **[REFATORAÇÃO]**

Padrão fechado; a Trilha A pode fixar hoje:

```
{TIPO}_{TITULAR}_{AAAAMMDD}_{VERSAO}.{ext}

CAR-DEM_70123456789_20260514_v02.pdf
NFP_70123456789_20260812_v01.xml
EMB_70123456789_20260830_v01.pdf
NF-EXP_LOTE-2026-014_20260901_v01.xml
```

- **TIPO** — vocabulário controlado: `CAR-REC CAR-DEM CCIR DITR CND-ITR MATR TIT POSSE SIGEF NFP NFA NF4 NF-ENT IE-PR CAF DAP ROM FCOOP LIC ASV EMB CERT-RA CERT-ORG CERT-FT DECL TRAB NF-EXP CFIT LAUDO`. Não classificado é `NAOCLASS` — nunca um palpite.
- **TITULAR** — **CPF de 11 dígitos**, não nome. Nomes colidem e divergem entre documentos; o CPF é a chave de junção de todas as checagens. Documentos de lote: `LOTE-{id}`. Documentos da cooperativa: CNPJ.
- **DATA** — data de emissão do documento, não a do upload. Se ilegível, data do upload com sufixo `u`.
- **VERSÃO** — `v01`, `v02`… quando chega documento mais novo do mesmo tipo e titular. **O anterior nunca é apagado** — o EUDR exige guarda de cinco anos e a trilha de auditoria é parte do produto. `documento` precisa de `versao INTEGER`; hoje não tem.
- Nome original vai para metadado (`arquivo_origem`, já existe), nunca para o nome novo. Extensão sempre verdadeira ao conteúdo — foto de DANFE é `.jpg`, não PDF requalificado.
- Checagens geradas pelo sistema (`EMB`, `LAUDO`) datam do dia da execução — o versionamento delas **é** o registro da vigilância contínua.

### A armadilha que vai custar horas se ninguém avisar

Na NF-e de pessoa física, as séries ficam na faixa **920–969** e **o CPF entra com zeros à esquerda nas 14 posições do campo CNPJ da chave de acesso**. Quem escrever o parser esperando CNPJ vai errar o produtor em toda nota de produtor.

Mais duas:

- Nota **modelo 4** (papel, legado) não tem chave de acesso.
- **CFOP 5102 ou 6102 é revenda** — atravessador, não produção própria. Esse elo quebra o vínculo com o talhão e precisa ser **reclassificado como intermediário**, não descartado.

---

## 06 · O que o produto não tem permissão de fazer  **[BLOQUEIA]**

Não são preferências de UX. São o posicionamento inteiro, e cada uma já tem consequência de tela.

### Nada é exigido do produtor

Sem app do produtor, sem formulário, sem login, sem cadastro que ele preencha. **Tudo entra pela mão da Cláudia**, com o material que já existe — foto de celular, PDF escaneado, papel digitalizado. Qualquer tela que comece pedindo polígono do talhão, planilha padronizada ou XML estruturado está pedindo o resultado em vez do insumo.

### A exceção é dela, e a lacuna não é culpa de ninguém

A relação da Cláudia com o cooperado é de confiança construída em anos. Um sistema que a transforme em fiscal quebra a cooperativa antes de resolver a papelada. Isso é literal na microcópia:

> "falta o CCIR de Antônio" — nunca "Antônio está irregular".

O estado é do documento, não da pessoa.

### O sistema não bloqueia, não cancela e não barra

Ele **marca, ordena e informa** — quem decide é sempre ela. Não é só delicadeza: **nós não emitimos a declaração**, então não temos autoridade nenhuma sobre a carga. Prometer poder que não temos derruba a credibilidade de tudo o que vem antes. O verbo certo é *marca o talhão, identifica os lotes que dependem dele e refaz os dossiês*.

### As duas provas não se compensam

Desmatamento posterior a 31/12/2020 desqualifica a parcela inteira **mesmo com ASV legal** — a condição do Art. 3(a) independe da legalidade. Nenhuma tela e nenhuma regra pode deixar evidência de legalidade compensar falha geométrica. E qualquer desmatamento na parcela desqualifica **toda a produção dela**, sem proporcionalidade.

---

## 07 · O que muda no contrato de construção  **[BLOQUEIA]**

O `docs/contrato.md` continua valendo inteiro, menos estes três pontos.

### 7.1 · A ordem de corte está errada agora

O contrato manda derrubar, como segundo item da lista de corte, a **checagem 04 — sobreposição de direitos** (terra indígena, unidade de conservação, território quilombola). Depois do item 02 deste arquivo, isso não pode mais acontecer: **essa checagem é a única prova possível das categorias (f), (g) e parte de (d)**. Se ela cai, três das oito categorias de legalidade não fecham nunca, e o produto deixa de provar o que promete no palco.

**Ordem de corte corrigida** — cai primeiro, do topo para baixo:

1. mapa dentro do dossiê
2. telas 1 e 3 da interface
3. as regras **F** da checagem 05 (mantenha as nove regras **B** listadas na seção 04)
4. o refinamento da checagem 03 — mantenha o CAR; a hierarquia completa da camada 2 pode ficar simplificada

**Nunca caem:** checagem 02 (embargo), **checagem 04 (sobreposição de direitos)**, checagem 06 (coerência de volume), fila de exceções, vigilância, dossiê em PDF.

### 7.2 · O esquema mudou — e isto é o anúncio da regra de ouro nº 7

A regra nº 7 do contrato diz que ninguém muda o esquema sozinho, que a mudança é decisão da PM e é anunciada no grupo. **Este arquivo é esse anúncio.** `db.py` continua sendo a fonte única de verdade — quem aplica as mudanças é a **Trilha 0**, não cada trilha por conta própria.

| Onde | Mudança | Vem da seção |
|---|---|---|
| nova tabela `aptidao` | `id, produtor_id, camada, satisfeita, via_documento_id, forca, avaliado_em` | 01 |
| `checagem` | `+ categoria TEXT` (a–h) | 02 |
| `checagem` | `+ severidade TEXT` ('B' ou 'F'); `codigo` passa a ser o código da regra (`R17`) | 04 |
| `documento` | `+ versao INTEGER` | 05 |
| `excecao` | `tipo` ganha vocabulário fixo: `bloqueio`, `lacuna_sanavel`, `dispensa_documentada`, `nao_sanavel_pelo_produtor` | 03 |

### 7.3 · A tabela de quem escreve onde ganha uma linha

`aptidao` é calculada a partir de `documento` mais `checagem`, então **quem escreve é a Trilha B** e quem lê é a C.

| Trilha | Escreve | Lê |
|---|---|---|
| **B · Verificação** | `checagem`, `excecao`, **`aptidao`** | `talhao`, `documento`, `lote_talhao` |
| **C · Dossiê** | `dossie` | tudo, **incluindo `aptidao`** |

Uma consequência para a Trilha 0: em `params/cacau.yml`, o parâmetro de produtividade máxima regional (usado pela R39) fica **vazio e com a regra desligada** — ver seção 04.

---

## 08 · Duas coisas que mudaram fora do código

- **A citação dos 12 meses agora tem endereço.** Uma DDS pode cobrir múltiplos lotes e remessas por até um ano da submissão — é a **pergunta 5.19 do FAQ da Comissão, versão 4 (abr/2025)**, com base no Art. 4(3) e no Anexo II. Antes citávamos fonte secundária. É a justificativa formal da vigilância contínua: quem assina fica exposto o ano inteiro.
- **O prazo que vale para a cooperativa é dez/2026, não jun/2027.** O prazo formal dela, como micro ou pequena, é 30/06/2027 — mas quem compra dela é médio ou grande e precisa estar conforme em 30/12/2026. O comprador não espera: a cobrança desce a cadeia um semestre antes. Isso muda o texto de urgência do PRD.

---

## Se der para fazer só uma coisa desta lista

Faça a **01** e a **02**. As duas são modelo de dados e as duas são a diferença entre um produto que inclui e um que reprova — que é a única coisa que este projeto promete.
