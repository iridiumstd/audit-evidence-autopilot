# Correções de Spec — o que a taxonomia mudou

*Evidence Autopilot EUDR · ATON · versão em markdown do artefato*
*Original com formatação: https://claude.ai/code/artifact/09a00e45-7b57-4e5b-90ef-ab93438a3b27*

---

<div role="main">

<div>

Evidence Autopilot EUDR · ATON · para quem está escrevendo PRD e spec

# Correções de spec

Sete coisas que a taxonomia documental e o perfil de cliente mudaram depois que as trilhas foram escritas. Cada uma é barata agora e cara depois — três mudam o modelo de dados, duas mudam o que o produto tem permissão de fazer, e uma corrige a ordem de corte do contrato.

</div>

<span class="pill stop">Bloqueia</span> se ficar errado, o produto contradiz a própria tese <span class="pill warn">Custa refatoração</span> dá para fazer depois, mas dói

<div class="section">

<div class="sec-head">

<span class="sec-num">00</span>

## O que este arquivo torna desatualizado

</div>

Leia isto antes de seguir qualquer um dos outros dois documentos do `docs/`.

<div class="tablewrap">

| Arquivo               | O que ficou desatualizado                                                                                                                                                                                        | Onde está o certo |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| `docs/duas-pernas.md` | **As sete regras de inconsistência** escritas à mão — substituídas por R01–R50, com severidade B/F. E a lista de 42 evidências: são **29 tipos documentais**, 25 na perna de legalidade, em 9 emissores.         | Seção **04**      |
| `docs/contrato.md`    | **A ordem de corte** (manda derrubar a checagem 04, que virou insubstituível), o **esquema em `db.py`** (faltam 3 campos e 1 tabela) e a **tabela de quem escreve onde** (a nova tabela `aptidao` não tem dono). | Seção **07**      |

</div>

O resto de ambos continua valendo. Em caso de conflito, **este arquivo ganha** — ele é posterior, e é a decisão da PM prevista na regra de ouro nº 7 do contrato.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">01</span>

## Aptidão é hierarquia de alternativas, não checklist

<span class="pill stop">Bloqueia</span>

</div>

Esta é a correção mais importante da lista. Se o spec descrever aptidão como uma lista de documentos obrigatórios, o produto exclui exatamente a base que a gente diz que vem incluir.

A taxonomia fechou o **conjunto mínimo em cinco camadas**, e cada camada aceita alternativas **em ordem de força probatória**. A camada crítica é a segunda:

<div class="do">

Camada 2 · direito de uso da área — Art. 9(1)(h)

**Um** entre, nesta ordem: `matrícula em nome do produtor` → `título (TD, CDRU, CCU)` → `contrato ou declaração de posse corroborado por CCIR ou DITR/CIB em nome próprio`.

</div>

<div class="why">

**Por que a hierarquia existe:** a FAQ da Comissão diz que, se a lei local não exige título formal para produzir e comercializar, o Regulamento também não exige — o que o Art. 9(1)(h) pede é evidência **do arranjo de uso**. E o arranjo real da Amazônia é posse mais cadastro fiscal em nome próprio. Matrícula é minoria na base, e o SIGEF só passa a ser obrigatório em 2029. Um checklist rígido reprovaria a maioria dos produtores por não ter um papel que a lei não exige deles.

</div>

As outras quatro, para o spec: **(1)** polígono dentro de CAR não-cancelado — Ativo e Pendente passam, Cancelado e Suspenso reprovam; ponto com 6 casas decimais só vale para talhão até 4 ha. **(3)** CPF válido mais CAF ativo, ou ficha de cooperado mais inscrição estadual. **(4)** NF-e do produtor *ou* contranota da cooperativa nomeando o produtor como remetente. **(5)** as checagens negativas, que são assunto do item 02.

### O que muda no banco

Não existe tabela de aptidão. Precisa existir, e ela não é booleana:

    CREATE TABLE aptidao(
      id TEXT PRIMARY KEY, produtor_id TEXT, camada INTEGER,   -- 1..5
      satisfeita INTEGER,          -- 0/1
      via_documento_id TEXT,       -- qual documento fechou a camada
      forca TEXT,                  -- 'forte' | 'media' | 'fraca'
      avaliado_em TEXT);

A `forca` importa: um lote fechado só com camadas 2 fracas é conforme, mas é o lote que a Cláudia quer ver antes de assinar.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">02</span>

## Existem dois tipos de evidência, e o modelo só prevê um

<span class="pill stop">Bloqueia</span>

</div>

Três das oito categorias de legalidade **não têm documento positivo emitido para o produtor**. Direitos humanos, consentimento prévio e parte de direitos de terceiros não se provam com papel — não há certidão a pedir nem órgão a procurar.

Provam-se por **checagem negativa georreferenciada**: o polígono não intersecta terra indígena, unidade de conservação de proteção integral ou território quilombola; não está sob embargo do Ibama ou da LDI-PA; o CPF não está na Lista Suja. E não existe certidão pública de conformidade trabalhista para pessoa física sem empregados — o substituto é o trio Lista Suja mais CAF mais autodeclaração.

<div class="why">

**O risco concreto:** se o dossiê montar a conformidade percorrendo os documentos entregues, essas três categorias **nunca fecham** — não porque falta documento, mas porque documento não é o instrumento. O time vai passar horas caçando um papel que não existe. Pior: a tela vai mostrar lacuna permanente em três categorias, e a demo cai.

</div>

<div class="do">

O que o spec precisa dizer

A montagem do dossiê itera sobre as **oito categorias**, e cada uma é satisfeita por documento *ou* por checagem — nunca só por documento. `checagem` ganha o campo `categoria` (a–h), hoje só tem `perna`. E a ficha da categoria mostra a origem da prova, porque é isso que o auditor vai querer ver.

</div>

Vale dizer no palco e escrever no spec com a mesma frase, porque ela é a tese do produto em uma linha: **é evidência que o sistema gera, não que o produtor entrega.** É também o motivo técnico da vigilância contínua — consulta datada envelhece sozinha, e refazer não é um extra, é a manutenção da prova.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">03</span>

## Ausência de documento nem sempre é lacuna

<span class="pill stop">Bloqueia</span>

</div>

Se o sistema tratar toda ausência como pendência, ele cria a barreira que a gente diz estar removendo. Quatro casos onde **não ter é a situação regular**:

<div class="tablewrap">

| Ausência                     | Estado correto                                                | Por quê                                                                                                                                                            |
|------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Licença ambiental**        | <span class="pill ok">Regular</span> com dispensa documentada | Cacauicultura familiar é tipicamente dispensada. A regra é distinguir "não tem porque é dispensado" de "deveria ter e não tem".                                    |
| **SIGEF**                    | <span class="pill ok">Esperado</span>                         | Obrigação só em 21/10/2029 (Dec. 12.689/2025). Em 2026, imóveis abaixo de 25 ha não estão obrigados. Vira lacuna só se o comprador exigir precisão de agrimensura. |
| **ASV / AUTEF**              | <span class="pill ok">Esperado</span>                         | SAF de cacau em área consolidada não exige, cabruca não suprime. Ausência é o cenário normal — a presença é que é rara.                                            |
| **CND-ITR** ou débito de ITR | <span class="pill warn">Flag</span>, nunca bloqueio           | Débito de ITR não torna a produção ilegal.                                                                                                                         |
| **CAR "Pendente"**           | <span class="pill warn">Registra condição e data</span>       | Cerca de 0,4% dos imóveis tiveram análise completa em dez anos. Pendente é o estado do sistema, não falha do produtor — e ele não tem como resolver.               |

</div>

<div class="do">

O que o spec precisa dizer

`excecao.tipo` precisa de pelo menos três valores distintos: `bloqueio`, `lacuna_sanavel` e `dispensa_documentada`. E um quarto que vale ouro na tela: `nao_sanavel_pelo_produtor`, para o CAR pendente. A contagem de lacunas do painel só soma `lacuna_sanavel`.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">04</span>

## As checagens agora têm 50 regras e duas severidades

<span class="pill warn">Custa refatoração</span>

</div>

O `docs/duas-pernas.md` que a Trilha B recebeu tem sete regras escritas por mim. A taxonomia entregou **cinquenta, de R01 a R50**, cada uma marcada como **B** (bloqueia aptidão até resolver) ou **F** (flag para revisão humana). Estão agrupadas em: identidade e titularidade, área e geometria, jurisdição, vigência, volume e massa, documento fiscal.

<div class="do">

O que muda no banco

`checagem` precisa de `severidade TEXT` com `'B'` ou `'F'`, e `codigo` passa a carregar o código da regra (`R17`, `R39`). Sem isso não há como o dossiê distinguir "não embarca" de "olhe isto antes de assinar" — que é exatamente a decisão que a tela da manhã apresenta à Cláudia.

</div>

Para o MVP, se não der para implementar as cinquenta, a ordem de valor é: **R17** (polígono intersecta desmatamento pós-31/12/2020 — desqualificação automática), **R16** (intersecta embargo), **R13** (talhão fora do perímetro do CAR), **R29** (CAR cancelado), **R08** (CPF na Lista Suja), **R18** e **R19** (terra indígena e unidade de conservação), **R01** (CPF da nota diverge do titular do CAR) e **R14** (talhão acima de 4 ha entregue como ponto). Essas nove cobrem as cinco camadas e rodam sobre dado público real.

<div class="why">

**Não hardcodar a R39.** Ela compara a soma das notas do produtor contra área × produtividade máxima regional — e a própria taxonomia registra que **esse parâmetro não foi levantado**. Deixar como parâmetro de calibração vazio, com a regra desligada, é melhor que inventar um número que a banca pode contestar.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">05</span>

## A nomenclatura e a armadilha de parsing da NF-e

<span class="pill warn">Custa refatoração</span>

</div>

O padrão está fechado e a Trilha A pode fixar hoje:

    {TIPO}_{TITULAR}_{AAAAMMDD}_{VERSAO}.{ext}

    CAR-DEM_70123456789_20260514_v02.pdf
    NFP_70123456789_20260812_v01.xml
    NF-EXP_LOTE-2026-014_20260901_v01.xml

- **TIPO** vem de vocabulário controlado (CAR-REC, CAR-DEM, CCIR, DITR, CND-ITR, MATR, TIT, POSSE, SIGEF, NFP, NFA, NF4, NF-ENT, IE-PR, CAF, ROM, FCOOP, LIC, ASV, EMB, CERT-RA, CERT-ORG, CERT-FT, DECL, TRAB, NF-EXP, CFIT, LAUDO). Não classificado é `NAOCLASS` — nunca um palpite.
- **TITULAR** é **CPF de 11 dígitos**, não nome. Nomes colidem e divergem entre documentos; o CPF é a chave de junção de todas as checagens.
- **DATA** é a de emissão do documento, não a do upload. Se ilegível, data do upload com sufixo `u`.
- **VERSÃO** incrementa quando chega documento mais novo do mesmo tipo e titular. **O anterior nunca é apagado** — o EUDR exige guarda de cinco anos, e a trilha de auditoria é parte do produto. `documento` precisa de `versao INTEGER`, hoje não tem.
- O nome original vai para metadado (`arquivo_origem` já existe), nunca para o nome novo. Extensão sempre verdadeira ao conteúdo — foto de DANFE é `.jpg`, não PDF requalificado.

<div class="why">

**A armadilha que vai custar horas se ninguém avisar:** na NF-e de pessoa física, as séries ficam na faixa **920–969** e **o CPF entra com zeros à esquerda nas 14 posições do campo CNPJ da chave de acesso**. Quem fizer o parser esperando CNPJ vai errar o produtor em toda nota de produtor. Outras duas: nota modelo 4 (papel) não tem chave de acesso, e **CFOP 5102 ou 6102 é revenda** — atravessador, não produção própria; esse elo quebra o vínculo com o talhão e precisa ser reclassificado, não descartado.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">06</span>

## O que o produto não tem permissão de fazer

<span class="pill stop">Bloqueia</span>

</div>

Estas quatro não são preferência de UX. São o posicionamento inteiro, e cada uma já tem consequência de tela.

### Nada é exigido do produtor

Sem app do produtor, sem formulário, sem login, sem cadastro que ele preencha. **Tudo entra pela mão da Cláudia**, com o material que já existe — foto de celular, PDF escaneado, papel digitalizado. Qualquer tela que comece pedindo polígono do talhão, planilha padronizada ou XML estruturado está pedindo o resultado em vez do insumo.

### A exceção é dela, e a lacuna não é culpa de ninguém

A relação da Cláudia com o cooperado é de confiança construída em anos. Um sistema que a transforme em fiscal quebra a cooperativa antes de resolver a papelada. Isso é literal na microcópia: *"falta o CCIR de Antônio"*, nunca *"Antônio está irregular"*. O estado é do documento, não da pessoa.

### O sistema não bloqueia, não cancela e não barra

Ele marca, ordena e informa — quem decide é sempre ela. Isso não é só delicadeza: **nós não emitimos a declaração**, então não temos autoridade nenhuma sobre a carga. Prometer poder que não temos derruba a credibilidade de tudo o que vem antes. O verbo certo é *marca o talhão, identifica os lotes que dependem dele e refaz os dossiês*.

### As duas provas não se compensam

Desmatamento posterior a 31/12/2020 desqualifica a parcela inteira **mesmo com ASV legal** — a condição do Art. 3(a) independe da legalidade. Nenhuma tela e nenhuma regra pode deixar evidência de legalidade compensar falha geométrica. E qualquer desmatamento na parcela desqualifica **toda a produção dela**, sem proporcionalidade.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">07</span>

## O que muda no contrato de construção

<span class="pill stop">Bloqueia</span>

</div>

O `docs/contrato.md` continua valendo inteiro, menos estes três pontos.

### 7.1 · A ordem de corte está errada agora

O contrato manda derrubar, como **segundo item** da lista de corte, a **checagem 04 — sobreposição de direitos** (terra indígena, unidade de conservação, território quilombola). Depois do item 02 deste arquivo, isso não pode mais acontecer: essa checagem é **a única prova possível das categorias (f), (g) e parte de (d)**. Se ela cai, três das oito categorias não fecham nunca — e o produto deixa de provar o que promete no palco.

<div class="do">

Ordem de corte corrigida — cai primeiro, do topo para baixo

1\. mapa dentro do dossiê · 2. telas 1 e 3 da interface · 3. as regras **F** da checagem 05, mantendo as nove regras **B** da seção 04 · 4. o refinamento da checagem 03 — mantenha o CAR; a hierarquia completa da camada 2 pode ficar simplificada.

**Nunca caem:** checagem 02 (embargo), **checagem 04 (sobreposição de direitos)**, checagem 06 (coerência de volume), fila de exceções, vigilância, dossiê em PDF.

</div>

### 7.2 · O esquema mudou — e isto é o anúncio da regra de ouro nº 7

A regra nº 7 diz que ninguém muda o esquema sozinho, que a mudança é decisão da PM e é anunciada no grupo. **Este documento é esse anúncio.** O `db.py` continua sendo a fonte única de verdade, e quem aplica as mudanças é a **Trilha 0** — não cada trilha por conta própria.

<div class="tablewrap">

| Onde                  | Mudança                                                                                                          | Vem da seção |
|-----------------------|------------------------------------------------------------------------------------------------------------------|--------------|
| nova tabela `aptidao` | `id, produtor_id, camada, satisfeita, via_documento_id, forca, avaliado_em`                                      | 01           |
| `checagem`            | `+ categoria TEXT` (a–h)                                                                                         | 02           |
| `checagem`            | `+ severidade TEXT` ('B' ou 'F'); `codigo` passa a ser o código da regra (`R17`)                                 | 04           |
| `documento`           | `+ versao INTEGER`                                                                                               | 05           |
| `excecao`             | `tipo` ganha vocabulário fixo: `bloqueio`, `lacuna_sanavel`, `dispensa_documentada`, `nao_sanavel_pelo_produtor` | 03           |

</div>

### 7.3 · A tabela de quem escreve onde ganha uma linha

`aptidao` é calculada a partir de `documento` mais `checagem` — então **quem escreve é a Trilha B** e quem lê é a C. E uma consequência para a Trilha 0: em `params/cacau.yml`, o parâmetro de produtividade máxima regional (usado pela R39) fica **vazio e com a regra desligada**.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">08</span>

## Duas coisas que mudaram fora do código

</div>

- **A citação dos 12 meses agora tem endereço.** Uma DDS pode cobrir múltiplos lotes por até um ano da submissão — é a **pergunta 5.19 do FAQ da Comissão, versão 4 (abr/2025)**, com base no Art. 4(3) e no Anexo II. Antes a gente citava fonte secundária. É a justificativa formal da vigilância contínua: quem assina fica exposto o ano inteiro.
- **O prazo que vale para a cooperativa é dez/2026, não jun/2027.** O prazo formal dela, como micro ou pequena, é junho de 2027 — mas quem compra dela é médio ou grande e precisa estar conforme em 30 de dezembro de 2026. O comprador não espera: a cobrança desce a cadeia um semestre antes. Isso muda o texto de urgência do PRD.

<div class="do">

Se der para fazer só uma coisa desta lista

Faça a **01** e a **02**. As duas são modelo de dados e as duas são a diferença entre um produto que inclui e um que reprova — que é a única coisa que este projeto promete.

</div>

</div>

</div>
