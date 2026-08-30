# O Dia Seguinte — plano, decisões e horários

*Evidence Autopilot EUDR · ATON · versão em markdown do artefato*
*Original com formatação: https://claude.ai/code/artifact/70ec4dfd-3912-45d7-a4e0-97f004ea76b1*

---

<div class="masthead">

<div class="wrap">

Evidence Autopilot EUDR · Plano de retomada · ATON

# O Dia Seguinte

Estado do projeto, o que já está decidido e não se reabre, as quatro decisões que faltam com recomendação, e as seis horas com dono e hora marcada.

</div>

</div>

<div class="wrap">

[Onde estamos](#estado) [Já decidido](#fechado) [O que falta decidir](#decisoes) [As 6 horas](#horas) [Quem lê o quê](#leitura) [Riscos e plano B](#riscos)

</div>

<div class="wrap" role="main">

<div id="estado" class="section">

<div class="sec-head">

<span class="sec-num">01</span>

## Onde estamos, numa tela

</div>

Leia isto e você sabe tudo. As três frentes de pesquisa voltaram, a construção está rodando, e o que falta é decisão e palco.

<div class="tablewrap">

| Frente                   | Estado                                     | O que produziu                                                                                                                              |
|--------------------------|--------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| **Problema e preço**     | <span class="pill ok">Fechada</span>       | Dez fatos citáveis com fonte, custo de adequação por produtor, precedente da soja e da carne.                                               |
| **TAM, SAM, SOM**        | <span class="pill ok">Fechada</span>       | R\$ 130 mi, R\$ 21 mi e R\$ 1,8 mi, com 18 premissas rastreáveis e três cenários. E a métrica da missão: R\$ 12 a 83 por produtor incluído. |
| **Panorama competitivo** | <span class="pill ok">Fechada</span>       | ~50 plataformas na matriz das duas pernas. Veredito: a perna B automatizada é um clube de quatro, e nenhum atende a cadeia atomizada.       |
| **Red team**             | <span class="pill ok">Fechada</span>       | Furos priorizados e as dez perguntas mais duras. O furo mais fatal: quem paga.                                                              |
| **Duas pernas**          | <span class="pill ok">Fechada</span>       | A estrutura da tese. 42 evidências mapeadas, 2 cobertas pelos gratuitos, e o precedente do EUTR mostrando que três categorias são inéditas. |
| **Construção**           | <span class="pill warn">Rodando</span>     | Cinco trilhas, contrato de dados fixo, <span class="mono">db.py</span> e <span class="mono">docs/</span> entregues.                         |
| **Entrevista de campo**  | <span class="pill warn">A agendar</span>   | Roteiro pronto e autossuficiente para a PO conduzir. **Depende de agenda de terceiro — dispare primeiro.**                                  |
| **Pitch e deck**         | <span class="pill stop">Não começou</span> | Bloqueado nas decisões da seção 03.                                                                                                         |
| **Sabatina**             | <span class="pill stop">Não começou</span> | Insumo pronto: as dez perguntas do red team.                                                                                                |

</div>

<div class="callout ok">

**A boa notícia para dizer no começo da manhã:** a parte difícil acabou. Vocês têm uma tese defensável, com fonte primária do lado comprador, um mapeamento competitivo que encontrou o vazio, e números construídos de baixo para cima. Falta contar. Time que chega nesse ponto às seis horas do fim costuma chegar bem.

</div>

</div>

<div id="fechado" class="section">

<div class="sec-head">

<span class="sec-num">02</span>

## Já decidido — não se reabre

</div>

Leia esta lista em voz alta na abertura da manhã. Metade do tempo perdido em hackathon é rediscussão do que já foi resolvido por alguém que não estava na sala.

- **A tese é as duas pernas.** Perna A, desmatamento, virou commodity gratuita e não é nosso diferencial. Perna B, legalidade em oito categorias, é documental e não tem dono. É por aí que o pitch abre.
- **O ICP é um formato de cadeia**, não uma commodity: muitos fornecedores pequenos, documento em papel, um agregador que carrega a prova. Soja e pecuária estão explicitamente fora.
- **Não emitimos DDS** e não submetemos nada no TRACES. Somos a camada de prova e a memória de cinco anos.
- **Não cobramos documento de fornecedor** no MVP. Entregamos o mapa de lacunas; a cobrança é o módulo seguinte.
- **O contrato de entrada** é arquivo agrupado por produtor, fora de padrão. Não prometemos adivinhar dono de arquivo solto.
- **A região da demo é a Transamazônica.** Isso foi fechado quando a construção começou a semear os dados — reabrir agora joga fora a base inteira.
- **A unidade é o lote de embarque**, não o imóvel. É a diferença nossa para o Parque Cafeeiro, que emite por imóvel com validade de 180 dias.
- **Automatizamos quatro das oito categorias.** As outras viram trilha documental organizada. Isso é posição declarada, não limitação escondida.
- **A stack e o contrato de dados** estão fixados em <span class="mono">docs/contrato.md</span>. Mudança de campo é decisão da PM, anunciada.

</div>

<div id="decisoes" class="section">

<div class="sec-head">

<span class="sec-num">03</span>

## As quatro decisões que faltam

</div>

Trinta minutos de reunião, time todo, você conduzindo. Cada uma tem recomendação — a reunião é para confirmar ou discordar com motivo, não para explorar do zero.

<div class="dec">

<div class="dec-head">

<span class="k">DECISÃO 1</span>

### Quem é o pagador

<span class="t">10 min · bloqueia o pitch</span>

</div>

<div class="dec-body">

O agregador — cooperativa ou exportador — ou o comprador que assina a declaração? O red team apontou isso como o furo mais fatal, e a evidência do café colombiano sugere que o comprador internaliza o custo. No cacau paraense, a pressão sobre a cooperativa vem da moageira, não do importador europeu.

**Recomendação: manter o agregador como cliente, e o comprador como segundo pagador declarado.** Três motivos. O dimensionamento inteiro foi construído sobre o agregador — mudar agora invalida o SAM seis horas antes do pitch. A resposta ao "por que ele pagaria" já existe e é forte: o protocolo da indústria de cacau recomenda que não responder ao questionário constitua quebra de contrato, e o guia do governo holandês diz ao exportador que, sem a informação pronta, o comprador para de comprar. E o comprador entra no pitch como upside, não como pivô — a Cargill já contratou empresa para mapear fornecedor indireto, o que prova que o bolso existe.

</div>

</div>

<div class="dec">

<div class="dec-head">

<span class="k">DECISÃO 2</span>

### Qual história do cacau se conta

<span class="t">10 min · bloqueia o pitch</span>

</div>

<div class="dec-body">

O Brasil é importador líquido de amêndoas e cerca de 95% do cacau paraense vai para as moageiras em Ilhéus. A cooperativa da demo quase não exporta direto. São duas narrativas possíveis: a dor presente — a moageira já cobra geolocalização do cooperado, porque ela exporta derivado e a exigência desce até o talhão — ou o upside: quase nada do cacau brasileiro entra na Europa hoje, e se a conta cair, entra.

**Recomendação: decidir isto depois da entrevista, e deixar as duas versões prontas.** A pergunta 2 do roteiro da PO — "alguém pediu documento ou coordenada do senhor nos últimos dois anos?" — responde exatamente isso. Se vier sim, vocês abrem com a dor presente e uma frase citada de produtor real, que é a abertura mais forte possível. Se vier não, abrem com o prazo de dezembro e o upside. **Peça à pessoa do deck para deixar o slide de abertura com as duas versões** e trocar em cinco minutos.

</div>

</div>

<div class="dec">

<div class="dec-head">

<span class="k">DECISÃO 3</span>

### O que é a demo no palco

<span class="t">5 min · define o que os construtores otimizam</span>

</div>

<div class="dec-body">

Mockup navegável, vídeo gravado do sistema real, ou demonstração ao vivo. Você disse que provavelmente vira mockup.

**Recomendação: vídeo gravado, com mockup como plano B.** Um vídeo de noventa segundos do sistema real rodando tem o realismo da demo ao vivo e a confiabilidade do slide — e o critério de produto vale 25%, com a banca explicitamente perguntando se a equipe construiu algo funcional ou só slides. **Comunique isso às trilhas hoje cedo:** muda o que elas otimizam, porque a saída de terminal e as três telas passam a ser cenário de filmagem. Se às quatro horas não houver o que filmar, aí sim mockup — e a decisão de virar tem que ser sua, não do cansaço.

</div>

</div>

<div class="dec">

<div class="dec-head">

<span class="k">DECISÃO 4</span>

### Papéis no palco

<span class="t">5 min · você decide, não é debate</span>

</div>

<div class="dec-body">

Quem apresenta, quem opera a tela, quem responde pergunta técnica, quem responde pergunta de negócio.

**Recomendação: uma pessoa apresenta o tempo todo** — alternar narrador em sete minutos quebra o fio. Uma segunda opera a tela e não fala. Na sabatina, duas pessoas respondem e o resto fica quieto: uma para produto e técnica, uma para mercado e negócio. Combine o gesto de passar a bola. **E defina o suplente de cada papel** — em hackathon alguém sempre some na hora.

</div>

</div>

<div class="callout warn">

**Uma quinta que não é decisão de time e você resolve sozinha:** o nome. "Evidence Autopilot" é claro em inglês e estranho na boca de um gerente de cooperativa em Medicilândia. Se ninguém tiver paixão pelo assunto, mantenha e siga — nome não decide hackathon, e trocar agora obriga a mexer em todos os artefatos.

</div>

</div>

<div id="horas" class="section">

<div class="sec-head">

<span class="sec-num">04</span>

## As seis horas, com dono

</div>

Duas coisas têm hora marcada e não podem escorregar: a entrevista, porque depende de agenda de terceiro, e o primeiro ensaio, porque é o que revela o que falta.

<div class="tablewrap">

| Hora      | O quê                                                                           | Quem                   | Sai com                                      |
|-----------|---------------------------------------------------------------------------------|------------------------|----------------------------------------------|
| 0:00–0:30 | Abertura: ler a lista do que já está decidido, e fechar as quatro decisões      | Time todo, você conduz | Quatro decisões fechadas e escritas no grupo |
| 0:30–0:45 | **Disparar o convite da entrevista** e combinar horário                         | PO                     | Entrevista marcada para até as 3h            |
| 0:45–1:00 | Comunicar às trilhas a decisão da demo e o que precisa estar filmável           | Você                   | Construtores sabendo o que otimizar          |
| 1:00–3:00 | Narrativa do pitch, minuto a minuto, com as duas aberturas                      | Uma pessoa             | Roteiro falado, pronto para virar slide      |
| 1:00–3:00 | Deck, em paralelo, seguindo a narrativa conforme ela sai                        | Uma pessoa             | Slides até o minuto 5                        |
| 1:00–3:00 | Sabatina: as dez perguntas do red team com resposta escrita                     | Uma pessoa             | Respostas de 30 segundos, e o que não dizer  |
| 3:00–4:00 | **Entrevista acontece.** Transcrição das quatro frases na hora seguinte         | PO                     | Frases literais no grupo                     |
| 3:00–4:00 | Próximos passos do produto, enquadrados como "por que continuar depois do ATON" | Você                   | Um slide, três marcos                        |
| 4:00–4:30 | Escolher a abertura conforme a resposta da entrevista; gravar o vídeo da demo   | Você + construtores    | Vídeo de 90 segundos ou decisão de mockup    |
| 4:30–5:30 | **Primeiro ensaio completo, cronometrado**, com sabatina simulada               | Time todo              | Lista do que corrigir                        |
| 5:30–6:00 | Ajuste, segundo e terceiro ensaios, congelar tudo                               | Time todo              | Nada mais muda                               |

</div>

<div class="callout stop">

**A regra que salva a apresentação: às 5h30 tudo congela.** Slide, código, número, frase. O que não estiver pronto não entra. Time que mexe no deck vinte minutos antes de subir apresenta um deck que ninguém ensaiou — e isso aparece. Anuncie esse horário logo na abertura da manhã, para não ter que impor depois.

</div>

<div class="callout">

**A partir das 4h30, ninguém mais programa.** É contraintuitivo e é o que separa demo boa de demo travada. Os construtores viram plateia crítica no ensaio — eles são quem melhor sabe onde o sistema pode falhar e que pergunta técnica é perigosa.

</div>

</div>

<div id="leitura" class="section">

<div class="sec-head">

<span class="sec-num">05</span>

## Quem lê o quê

</div>

Ninguém lê tudo. Mande para cada pessoa só o que ela precisa, com o tempo de leitura declarado — isso muda a taxa de quem realmente lê.

<div class="tablewrap">

| Pessoa                   | Lê                                                                                                                                 | Tempo  |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------|--------|
| Todo mundo, na abertura  | A seção 02 desta página, em voz alta                                                                                               | 3 min  |
| Quem escreve a narrativa | Documento do MVP, seções 1, 2, 11 e 12. Mais o das duas pernas, inteiro.                                                           | 25 min |
| Quem monta o deck        | Só a narrativa, conforme ela sai. Não precisa ler pesquisa.                                                                        | —      |
| Quem escreve a sabatina  | Red team inteiro, e o das duas pernas                                                                                              | 20 min |
| PO, antes da entrevista  | Roteiro da entrevista, que é autossuficiente                                                                                       | 10 min |
| Construtores             | <span class="mono">docs/contrato.md</span> e o prompt da trilha. Trilha B lê também <span class="mono">docs/duas-pernas.md</span>. | 5 min  |
| Quem apresenta           | A narrativa e a sabatina. Nada mais — carregar pesquisa na cabeça atrapalha no palco.                                              | —      |

</div>

Os documentos completos ficam como fonte de consulta para a sabatina, não como leitura obrigatória. Se um jurado perguntar algo específico, a pessoa procura ali durante a pergunta seguinte — é para isso que eles existem.

</div>

<div id="riscos" class="section">

<div class="sec-head">

<span class="sec-num">06</span>

## Riscos e planos B

</div>

<div class="grid g2">

<div class="card">

<span class="label">Risco alto</span>

### A entrevista não sai

É o mais provável de todos: depende de agenda de outra pessoa, num dia útil qualquer.

**Plano B:** abrir com o prazo e o upside, e responder à pergunta "vocês falaram com cliente?" com honestidade — "não conseguimos até aqui, e é a primeira coisa que faremos na semana que vem; o que temos é fonte primária do lado comprador". Admitir com plano soa melhor que rodeio.

</div>

<div class="card">

<span class="label">Risco médio</span>

### A construção não chega a rodar inteira

Cinco trilhas paralelas, meio dia. É plausível que a vigilância não feche.

**Plano B:** filmar o que existir. Um terminal mostrando as checagens rodando sobre embargo real e um PDF saindo já prova produto funcionando. O momento da cascata vira narração sobre o mockup.

</div>

<div class="card">

<span class="label">Risco médio</span>

### Perguntam do Parque Cafeeiro ou do Cacaupará

É a pergunta mais provável de um jurado bem informado do agro.

**Resposta pronta:** os dois cobrem a perna do desmatamento e uma parte pequena da legalidade; o Parque Cafeeiro emite por imóvel com validade de 180 dias, não por lote de embarque. São insumo nosso, não concorrente. Quem responde é a pessoa de negócio.

</div>

<div class="card">

<span class="label">Risco baixo, dano alto</span>

### Duas pessoas respondem juntas na sabatina

Acontece sempre, e passa impressão de time desalinhado mesmo quando a resposta está certa.

**Prevenção:** combinar o gesto de passar a bola no ensaio, e treinar a frase "deixa que a \[nome\] responde essa". Custa dois minutos de ensaio.

</div>

</div>

<div class="callout warn">

**O número que ainda é estimativa e pode ser cobrado:** a produtividade de referência da Transamazônica, que sustenta a checagem de coerência de volume. Temos cerca de 900 kg por hectare como ordem de grandeza publicada para o Pará. Se alguém do time conseguir uma fonte melhor em vinte minutos, vale — e se não, a resposta honesta no palco é dizer que é ordem de grandeza e que a régua é regionalizável por parâmetro.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">07</span>

## Antes de você dormir

</div>

Três coisas de cinco minutos que fazem a manhã começar sem atrito.

- **Mande esta página no grupo agora**, com uma linha: "leiam a seção 02 antes de a gente começar; o resto eu conduzo."
- **Escreva o nome de quem faz o quê** na tabela das seis horas e mande junto. Tarefa sem dono às 2h da manhã é tarefa órfã às 10h.
- **Deixe a mensagem de convite da entrevista já escrita** e combine com a PO que ela dispara às 8h. É a única coisa do dia que depende de terceiro.

<div class="callout ok">

E então durma. Você tem três frentes de pesquisa fechadas, uma tese que sobreviveu a um red team, e cinco trilhas construindo. O que falta amanhã é decidir quatro coisas e contar bem uma história que já está de pé.

</div>

</div>

</div>
