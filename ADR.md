# ADR — Registro de decisões de arquitetura

Evidence Autopilot EUDR · ATON

Cada decisão aqui está **fechada**. Não abram nenhuma para discussão durante a construção — toda hora gasta escolhendo biblioteca é hora que não vira demo. Se uma precisar mudar, é decisão de PM, anunciada no grupo, e este arquivo ganha uma linha de revisão.

Estado possível: `aceita` · `revista` · `superada`.

---

## ADR-001 · O diferencial está na perna B, não na A

**Estado:** aceita

**Contexto.** O EUDR exige duas provas cumulativas: perna A (livre de desmatamento pós-31/12/2020, provada por geometria e satélite) e perna B (legalidade no país produtor, oito categorias, feita de documento). A perna A já é entregue de graça por Whisp/FAO, Global Forest Watch, Parque Cafeeiro e Cacaupará.

**Decisão.** Construir a perna A no mínimo defensável (uma checagem) e concentrar o esforço todo na perna B. **Cada checagem escrita declara a que perna pertence**, e as da perna B declaram a categoria.

**Consequência.** A arquitetura de `verificacao.py` é orientada por perna e categoria, não por fonte de dados. O sumário do dossiê é separado por perna, e o semáforo da tela de lotes também. Um avaliador consegue ver, em um relance, que estamos jogando no campo onde não há concorrente.

---

## ADR-002 · Cobertura parcial declarada, não escondida

**Estado:** revista — ver contrato.md v2 (R01–R50; a checagem 04 é insubstituível). A cobertura automatizável cresceu com a checagem 07 (Lista Suja, categorias e/f); ver ADR-018.

**Contexto.** Das oito categorias da perna B, quatro são automatizáveis contra base pública brasileira (1, 2, 4+7, 8). As categorias 3, 5 e 6 não são — no cacau, e no caso das 5, 6 e 7 em lugar nenhum, porque são inéditas em regulação europeia de importação e ninguém teve tempo de construir ferramenta.

**Decisão.** Automatizar quatro categorias e transformar as outras em **trilha documental organizada, datada e indexada dentro do dossiê**. Declarar isso explicitamente no produto e na apresentação.

**Consequência.** O dossiê tem uma seção de anexos indexados que é entregável de primeira classe, não sobra. A frase de posicionamento é "cobrimos quatro das oito e organizamos as outras quatro — nenhum concorrente cobre as oito", que é mais forte do que fingir cobertura total e ser desmentido por um jurado que conhece o regulamento.

---

## ADR-003 · Entrada agrupada por produtor — o sistema nunca adivinha dono

**Estado:** aceita

**Contexto.** Arquivos chegam com nomes ruins (`IMG_4471.jpg`, `doc scan (3).pdf`). A tentação é construir um classificador que descubra de quem é cada arquivo solto.

**Decisão.** O contrato de entrada exige **uma pasta por produtor**. A atribuição vem do agrupamento, nunca de inferência. O sistema padroniza o que veio dentro do grupo.

**Consequência.** Elimina uma classe inteira de erro silencioso — atribuir documento ao produtor errado é o tipo de falha que destrói a credibilidade de um dossiê de conformidade. Em compensação, exige do usuário um passo de organização mínima, o que é aceitável porque cooperativas já organizam por produtor. Também transforma a divergência de CPF dentro do grupo num **sinal útil** (status `divergente`) em vez de ruído.

---

## ADR-004 · A checagem 05 é cruzamento entre documentos, não checklist de existência

**Estado:** revista — ver contrato.md v2. O conjunto de regras deixou de ser R1–R7 e passou a R01–R50, com severidade B/F; as R1–R7 originais ficam marcadas como nomenclatura v1, superada, em SPEC.md.

**Contexto.** É trivial verificar que um documento existe. Toda plataforma de coordenada faz isso. O que nenhuma faz é comparar o CPF do CAR com o CPF da nota fiscal do mesmo produtor.

**Decisão.** A checagem 05 implementa **cada regra como função separada e numerada** (R1–R7 no mínimo), com dict de retorno padrão (`resultado`, `texto`, `evidencia`). Regras adicionais são bem-vindas e valem ponto.

**Consequência.** Regra nova é acréscimo de função, não refatoração — o custo marginal de expandir o diferencial é baixo, e dá para cortar regras sob pressão de tempo sem quebrar nada. Cada exceção precisa nomear, em português claro, **qual documento conflita com qual**, porque o texto vai impresso e é lido por um auditor.

---

## ADR-005 · Todo laudo carrega a data da consulta

**Estado:** aceita

**Contexto.** Um dossiê de conformidade é uma afirmação sobre o mundo num instante. Sem data, a afirmação não é verificável nem defensável.

**Decisão.** Todo `checagem.texto` contém cinco elementos obrigatórios: o que foi comparado, contra qual base, **em que data a consulta foi feita**, o resultado e a conclusão em uma frase. `checagem.data_execucao` é campo, não opcional.

**Consequência.** É o que dá validade jurídica ao instantâneo: o dossiê passa a ser um snapshot assinado de um estado verificado continuamente. Justifica arquiteturalmente a vigilância (ADR-008) — se a data importa, o dossiê envelhece, e se envelhece precisa se regenerar.

---

## ADR-006 · SQLite em arquivo único, esquema congelado

**Estado:** aceita

**Contexto.** Cinco pessoas construindo em paralelo, em sessões separadas, no mesmo repositório. O que mata construção paralela não é falta de gente — é deriva de contrato. Duas pessoas inventam nomes de campo diferentes e à noite nada conversa.

**Decisão.** SQLite em `dados/app.db`, esquema definido antes de qualquer outra coisa pela Trilha 0, **congelado**. Nenhum campo é renomeado sem decisão de PM anunciada no grupo, com confirmação de quem depende do campo. Toda escrita passa por funções de `db.py`. Toda função pública recebe e devolve **dicts simples, nunca objetos**. Datas em ISO 8601 texto; IDs em `uuid4().hex[:12]`.

**Consequência.** Zero configuração, o banco inteiro cabe no git, todos abrem pelo mesmo caminho. Dicts em vez de objetos significam que nenhuma trilha precisa importar o modelo de outra — a fronteira entre trilhas é o esquema, não o código. O custo é perder validação de tipo, aceitável na escala do projeto.

---

## ADR-007 · Particionamento por tabela de escrita

**Estado:** aceita

**Contexto.** Quatro trilhas gravando no mesmo banco simultaneamente, sem coordenação em tempo real.

**Decisão.** Cada trilha tem **tabelas de escrita exclusivas**: A escreve `documento`; B escreve `checagem` e `excecao`; C escreve `dossie`; D atualiza `lote.status` e reabre dossiê chamando a Trilha C. Nenhuma trilha edita arquivo `.py` de outra — importa e usa.

**Consequência.** Conflito de escrita é estruturalmente impossível, e a dependência entre trilhas vira dependência de dados, não de código. Uma trilha bloqueada por outra ainda desenvolve contra dados falsos no formato do contrato, e troca no ponto de junção.

---

## ADR-008 · Vigilância em laço, não cron

**Estado:** aceita

**Contexto.** O sistema precisa reagir a um embargo publicado depois do dossiê. Um agendador de sistema é a escolha convencional.

**Decisão.** Um laço com `sleep` dentro de `vigilancia.py`, intervalo parametrizável (5 segundos na demo). **Não cron.**

**Consequência.** Em demonstração ao vivo, cron é risco puro — invisível, difícil de depurar, dependente de ambiente. O laço é visível, controlável e imprime o que está fazendo, e essa saída de terminal é metade da demonstração. Em produção a decisão seria revista; aqui é deliberada.

---

## ADR-009 · `evento` é append-only

**Estado:** aceita

**Contexto.** A afirmação central do produto é autonomia: o sistema faz coisas sozinho. Afirmação sem prova não vale nada diante de um avaliador.

**Decisão.** Toda trilha grava em `evento` a cada ação, distinguindo ator `sistema` de `humano`. **Nenhuma linha de `evento` é apagada, nunca.**

**Consequência.** A tabela alimenta três coisas de uma vez: o bloco 7 do dossiê (trilha de auditoria), o contador de autonomia no topo de todas as telas, e o diff entre versões de dossiê. É a estrutura de dados que mais retorna por linha escrita.

---

## ADR-010 · O dossiê fotografa, nunca recalcula

**Estado:** aceita

**Contexto.** Seria natural o gerador de dossiê recalcular as checagens no momento da emissão, para garantir dado fresco.

**Decisão.** `gerar_dossie(lote_id)` lê o estado **corrente** apurado pela verificação e o congela numa versão nova. Não recalcula nada.

**Consequência.** Separa responsabilidade com clareza: verificação decide, dossiê registra. Torna o versionamento honesto — a versão N é o que o sistema sabia naquele momento, com a data de cada checagem carimbada, e o campo `diff` explica em português o que mudou desde a versão anterior. Também permite que a Trilha C seja construída antes da B ficar pronta, contra dados falsos no formato do contrato.

---

## ADR-011 · HTML e PDF salvos sempre juntos

**Estado:** aceita

**Contexto.** O dossiê em PDF é o entregável que o cliente compra e a imagem final da demonstração. Renderização de PDF é o passo mais frágil da cadeia.

**Decisão.** Template HTML com jinja2, renderizado a PDF com playwright, e o **HTML é gravado junto do PDF** em `saida/dossies/<codigo>/vN.html`. Ambos os caminhos ficam em `dossie`.

**Consequência.** Iterar design é barato (é HTML), e se o PDF quebrar na hora da apresentação mostra-se o HTML — a demo sobrevive. Custa um campo a mais no esquema e um arquivo a mais em disco.

---

## ADR-012 · Falhar alto em base externa; nunca simular dado

**Estado:** aceita

**Contexto.** As bases públicas brasileiras saem do ar, mudam de formato e de URL. É tentador gerar um polígono plausível para não travar o desenvolvimento.

**Decisão.** Se o download de uma base real falhar, **dizer exatamente o que aconteceu e parar**. Dado simulado só é permitido quando marcado como semeado no código, de forma explícita, e a distinção entre camada real e camada semeada aparece no laudo.

**Consequência.** Um dossiê que cita base pública e foi na verdade alimentado por dado inventado é fraude, não atalho. O custo é que uma base fora do ar bloqueia uma checagem — mitigado pela ordem de corte do PRD, e pelo `ARD.md`, que registra procedência, formato e data de cada recurso.

---

## ADR-013 · Degradação graciosa do OCR

**Estado:** aceita

**Contexto.** `pytesseract` depende de binário externo e falha de forma diferente em cada máquina. Cinco pessoas, cinco ambientes.

**Decisão.** Se o tesseract não instalar, a máquina trata imagem como `ilegivel` e segue. Ninguém gasta tempo com isso.

**Consequência.** `ilegivel` já é um status previsto e uma armadilha plantada de propósito nos dados semeados — a degradação cai num caminho que o produto já sabe tratar, e aparece na fila de exceções como trabalho para humano em vez de erro de sistema.

---

## ADR-014 · A commodity é parâmetro, não código

**Estado:** aceita

**Contexto.** O MVP é cacau na Transamazônica, mas o mercado é café, soja, borracha, madeira, gado.

**Decisão.** Tipos de documento e palavras-chave, produtividade de referência por região, regras de validade por tipo e conjunto mínimo de documentos ficam em `params/cacau.yml`. O código lê o arquivo; não conhece a commodity.

**Consequência.** Trocar de commodity é escrever um YAML novo. É a afirmação de escalabilidade do produto, sustentada por arquitetura e não por slide. Exige disciplina: nenhum limiar de commodity codificado em `.py`.

---

## ADR-015 · A fila de exceções é o produto, não o painel verde

**Estado:** revista — a ordem de corte que define o que cai antes da fila de exceções mudou. Ver contrato.md v2: cai primeiro o mapa do dossiê, depois telas 1 e 3, depois as regras F da checagem 05, depois o refinamento da checagem 03; a checagem 04 nunca cai (é insubstituível — ver ADR-018) e a 07 cai antes da 04, mas depois de tudo o resto.

**Contexto.** A interface natural para conformidade é um dashboard de status. Dashboards verdes não geram trabalho nem confiança.

**Decisão.** A tela 2, **fila de exceções**, é a tela principal. Lista o que precisa de humano, com evidência, lotes afetados e dois botões que gravam quem resolveu e quando, disparando regeração do dossiê. Se faltar tempo, é a única tela que precisa existir.

**Consequência.** Alinha a interface com a tese do produto: o sistema não substitui o humano, ele entrega ao humano apenas o que exige julgamento — e prova, pelo contador de autonomia, quanta coisa não exigiu. Define também a ordem de corte da interface: telas 1 e 3 caem antes da 2.

---

## ADR-016 · A saída de terminal é entregável

**Estado:** aceita

**Contexto.** Metade da demonstração acontece no terminal, não na interface. A saída impressa costuma ser tratada como resto de depuração.

**Decisão.** Toda trilha imprime progresso legível e caprichado — arquivo a arquivo na ingestão, passo a passo na vigilância. É requisito explícito nos prompts das quatro trilhas.

**Consequência.** Custa quase nada durante a construção e é o que torna a autonomia visível no palco. Se a interface travar, o terminal ainda conta a história.

---

## ADR-017 · Aptidão é hierarquia de 5 camadas, não checklist

**Estado:** aceita

**Contexto.** Se o produto tratar aptidão como uma lista de documentos obrigatórios, ele reprova exatamente a base que diz vir incluir. A camada crítica é o direito de uso (Art. 9(1)(h)): a FAQ da Comissão diz que, se a lei local não exige título formal para produzir e comercializar, o Regulamento também não exige — o que se pede é evidência do arranjo de uso. Matrícula é minoria na base, e o SIGEF só passa a ser obrigatório em 2029.

**Decisão.** O conjunto mínimo tem cinco camadas (parcela geolocalizada, direito de uso, identidade e vínculo, transação, checagens negativas), e cada camada aceita alternativas em ordem de força probatória — a camada 2 fecha por `matrícula` → `título` → `posse + CCIR/DITR em nome próprio`, nesta ordem. `aptidao` é tabela nova, com `camada`, `satisfeita`, `via_documento_id` e `forca` ('forte'|'media'|'fraca').

**Consequência.** Um lote fechado só com camadas fracas ainda é conforme, mas é o que precisa de atenção humana antes de assinar — a `forca` carrega essa informação sem transformar reprovação em regra. A Trilha B escreve `aptidao`; a Trilha C lê.

---

## ADR-018 · Duas naturezas de evidência: documento ou checagem gerada

**Estado:** aceita

**Contexto.** Três das oito categorias de legalidade — direitos humanos (f), consentimento prévio (g) e parte de direitos de terceiros (d) — não têm documento positivo emitido para o produtor: não há certidão a pedir nem órgão a procurar. Um dossiê que monte conformidade só percorrendo documentos entregues nunca fecha essas três categorias.

**Decisão.** A montagem do dossiê itera sobre as **oito categorias**, e cada uma fecha por **documento entregue** ou por **checagem gerada** — nunca só por documento. `checagem` ganha o campo `categoria` (a–h). A checagem 04 (sobreposição de direitos) é a prova das categorias (f), (g) e parte de (d); a checagem 07 (Lista Suja) cobre (e) e (f).

**Consequência.** *É evidência que o sistema gera, não que o produtor entrega* — frase que vai ao palco e ao spec. Justifica a vigilância contínua: consulta datada envelhece sozinha, e refazer é manutenção da prova, não extra.

---

## ADR-019 · Ausência nem sempre é lacuna

**Estado:** aceita

**Contexto.** Se o sistema tratar toda ausência de documento como pendência, cria a barreira que diz estar removendo. Licença ambiental, ASV, AUTEF e SIGEF ausentes são a situação normal na cacauicultura familiar; CAR "Pendente" é o estado do sistema (~0,4% de análise completa em dez anos), não falha do produtor.

**Decisão.** `excecao.tipo` ganha quatro valores: `bloqueio`, `lacuna_sanavel`, `dispensa_documentada` e `nao_sanavel_pelo_produtor` (CAR pendente e afins). **A contagem de lacunas do painel só soma `lacuna_sanavel`.**

**Consequência.** Distingue "não tem porque é dispensado" de "deveria ter e não tem", e tira do produtor a culpa por um estado que ele não controla (CAR pendente). Débito de ITR vira flag, nunca bloqueio.

---

## ADR-020 · O sistema não bloqueia, não cancela, não barra — marca, ordena e informa

**Estado:** aceita

**Contexto.** A cooperativa não emite a declaração de conformidade, então não tem autoridade sobre a carga. Um sistema que assuma esse poder promete o que não tem, e uma UX que trate a lacuna como culpa do produtor transforma a gestora numa fiscal e quebra a relação de confiança que sustenta a cooperativa.

**Decisão.** O sistema marca o talhão, identifica os lotes que dependem dele e refaz os dossiês — quem decide é sempre o humano. A microcópia é literal: "falta o CCIR de Antônio", nunca "Antônio está irregular". O estado é do documento, não da pessoa.

**Consequência.** Nenhuma tela usa linguagem de bloqueio, cancelamento ou proibição sobre o produtor. Toda ação automática do sistema é reversível e registrada em `evento`, distinguindo `sistema` de `humano`.

---

## ADR-021 · As duas provas não se compensam

**Estado:** aceita

**Contexto.** Desmatamento posterior a 31/12/2020 desqualifica a parcela pela condição do Art. 3(a), que é independente da legalidade documental — a tentação de deixar boa documentação (ASV legal, por exemplo) atenuar uma falha geométrica contradiria o próprio regulamento.

**Decisão.** Nenhuma tela e nenhuma regra pode deixar evidência de legalidade compensar falha geométrica. Desmatamento pós-2020 desqualifica a parcela inteira mesmo com ASV legal, e qualquer desmatamento na parcela desqualifica toda a produção dela, sem proporcionalidade.

**Consequência.** O sumário do dossiê mantém as pernas A e B separadas (ADR-001) até no semáforo — nunca soma ou compensa entre elas. A checagem 01 (perna A) e a checagem 04/05 (perna B) escrevem resultados independentes; `recalcular_status_lotes()` usa o pior resultado entre todos, não uma média.

---

## Decisões pendentes

| # | Questão em aberto | Quem destrava | Bloqueia |
|---|---|---|---|
| P-01 | Faixa defensável de produtividade em kg/ha para a Transamazônica | PM, 20 min de pesquisa | Limiares da checagem 06. **R39 desligada até o levantamento (regra de ouro nº 8).** |
| P-02 | O que Parque Cafeeiro e Cacaupará realmente emitem | PM, 20 min de pesquisa | Contorno exato do posicionamento (ADR-001) |
| P-03 | Camadas de TI, quilombo e UC: base real ou semeada no MVP | Trilha 0, ao recortar a região | Checagem 04, e o que o laudo declara como fonte |
