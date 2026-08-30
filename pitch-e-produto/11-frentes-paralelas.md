# Frentes Paralelas — briefs de pesquisa

*Evidence Autopilot EUDR · ATON · versão em markdown do artefato*
*Original com formatação: https://claude.ai/code/artifact/31ba96f9-920e-44f0-9a59-030efc3f51f4*

---

<div class="masthead">

<div class="wrap">

ATON · Evidence Autopilot EUDR · Sessões paralelas

# Frentes Paralelas

Sete briefs prontos para copiar e colar em sessões novas. Cada um carrega o contexto inteiro do projeto — não precisa explicar nada antes.

</div>

</div>

<div class="wrap" role="main">

<div class="section">

## Como rodar

<div class="howto">

1.  **Abra uma sessão nova por brief.** Cada bloco é autossuficiente: já traz o que é o produto, o que não fazemos, o contexto regulatório e os critérios do hackathon.
2.  **Cole o bloco inteiro como primeira mensagem.** Não resuma nem corte o contexto — é ele que impede a sessão de inventar um produto diferente.
3.  **Rode as quatro do primeiro nível ao mesmo tempo.** Elas não dependem umas das outras.
4.  **Deixe o pitch por último.** Ele consome o resultado das outras; rodar antes desperdiça.
5.  **Quando uma sessão voltar**, cole o resultado dela nas outras que ainda estiverem rodando, se for relevante. Os briefs são independentes, mas as descobertas não precisam ser.
6.  **Todo brief manda a sessão entregar só a posição final.** Nada de narrativa de processo nem de mudança de rota — esse material vira insumo do pitch, e a banca não precisa ver o caminho. A exceção marcada é a seção de limitações, que é de uso interno.

</div>

<div class="callout warn">

**Um aviso sobre a frente 04.** O red team foi escrito para ser desagradável de ler. Se a sessão voltar dizendo que o projeto está bem encaminhado, ela falhou — mande de volta. O objetivo é achar o furo antes do jurado, não confirmar que está tudo certo.

</div>

</div>

<div class="section">

## O mapa das sete frentes

<div class="tablewrap">

| Frente                          | Responde a                                          | Critério que fortalece     | Quando                                          |
|---------------------------------|-----------------------------------------------------|----------------------------|-------------------------------------------------|
| **01 · O problema e seu preço** | Quem sofre, como resolve hoje, quanto gasta.        | Problema e mercado · 20%   | <span class="pill ok">Agora</span>              |
| **02 · TAM, SAM, SOM**          | Qual o tamanho real do que estamos perseguindo.     | Potencial de negócio · 20% | <span class="pill ok">Agora</span>              |
| **03 · Panorama competitivo**   | Quem já vende isso e por que não somos redundantes. | Potencial de negócio · 20% | <span class="pill ok">Agora</span>              |
| **04 · Red team**               | Onde o projeto quebra.                              | Todos                      | <span class="pill ok">Agora</span>              |
| **05 · Taxonomia documental**   | Que documentos existem, com que campos e validade.  | Produto · 25%              | <span class="pill warn">Destrava a build</span> |
| **06 · Dataset da demo**        | A cooperativa sintética e os grupos de arquivos.    | Produto · 25%              | <span class="pill warn">Destrava a build</span> |
| **07 · Pitch e sabatina**       | Como contar e como sobreviver às perguntas.         | Pitch · 15%                | <span class="pill neutral">Por último</span>    |

</div>

Se só der para rodar três, rode **04, 03 e 02** — nessa ordem de importância. O red team protege tudo, o panorama competitivo é onde mora o risco que ninguém do time enxerga de dentro, e o sizing é a pergunta que o jurado de negócio faz primeiro.

</div>

<div class="tier">

<span class="t">Nível 1 · rodar agora, em paralelo</span><span class="d">quatro sessões independentes</span>

</div>

<div class="section">

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 01</span>

## O problema e seu preço

</div>

O critério de 20% pergunta explicitamente "quanto já se gasta com pessoas, consultorias ou serviços para executar esse trabalho". Hoje vocês têm uma faixa estimada por um escritório de advocacia e nada mais. Essa frente existe para transformar isso em números datados, citáveis e específicos do cacau.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR".

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas (termos de embargo do Ibama, alertas de desmatamento, CAR) e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque. Depois disso, vigia continuamente: se um novo embargo ou alerta atinge um talhão, o dossiê é reaberto e regerado sozinho.

O QUE NÃO FAZEMOS: não emitimos nem submetemos a Declaração de Due Diligence (DDS) no TRACES — quem faz isso é o importador europeu. Não cobramos documento de fornecedor. Não damos parecer jurídico nem certificação. Não regularizamos CAR.

CLIENTE-ALVO: cooperativas e exportadores de cacau mid-market no Brasil. Região da demo: Transamazônica, Pará.

CONTEXTO REGULATÓRIO: Regulamento (UE) 2023/1115, alterado pelo Reg. (UE) 2025/2650. Prazos: 30/12/2026 para grandes e médios, 30/06/2027 para micro e pequenos. O Brasil é classificado como país de "risco padrão". Uma DDS pode cobrir até 12 meses de remessas. Operadores devem conservar dados de fornecedores por 5 anos.

CRITÉRIOS DE AVALIAÇÃO DO HACKATHON: problema e mercado 20%, potencial de negócio 20%, produto e funcionamento 25%, grau de autonomia e substituição de trabalho 20%, pitch e clareza 15%.

SUA MISSÃO

Fazer uma investigação profunda que prove que o problema é real, frequente e caro. Quero munição para o pitch, não um ensaio.

Investigue, com busca na web:

1. QUEM SOFRE. Quantas cooperativas e exportadores de cacau existem no Brasil e onde estão. Quantos produtores de cacau, e qual a proporção de agricultura familiar. Quantos deles vendem ou querem vender para a Europa.

2. COMO SE RESOLVE HOJE. Mapeie o substituto atual: consultoria ambiental de adequação, certificadoras (Rainforest Alliance, Fair Trade, orgânico), programas de rastreabilidade dos próprios traders (Cargill, Barry Callebaut, Olam, Ofi), cooperativas que montaram time interno, planilha e WhatsApp. Para cada um: quem oferece, o que entrega, e onde falha.

3. QUANTO CUSTA. Este é o item mais importante. Procure preços reais: propostas públicas, editais, licitações, notícias com valores, tabelas de consultoria, projetos financiados (BNDES, Banco Mundial, FAO, IDH, Fundo Amazônia) que mencionem custo por produtor georreferenciado ou por cooperativa adequada. Se não achar preço direto, ache proxy defensável e diga que é proxy.

4. O CUSTO DE FALHAR. Quanto vale um contêiner de cacau, quanto custa um embarque parado, o que acontece com carga rejeitada na Europa. A multa do EUDR é de até 4% do faturamento no bloco — ache casos ou análises que estimem o impacto real.

5. A PRESSÃO JÁ CHEGOU? Procure evidência concreta de que compradores europeus já estão exigindo dados de fornecedores brasileiros: cláusulas contratuais, cartas, comunicados de traders, notícias de cooperativas se adequando, prazos internos de indústrias.

6. O PRECEDENTE. A Moratória da Soja e os protocolos de carne no Pará já forçaram rastreabilidade em cadeias brasileiras. O que aconteceu com o mercado de serviços de dados nessas cadeias? Quem ganhou dinheiro? Isso é a melhor analogia disponível para o que vai acontecer no cacau — investigue a fundo.

ENTREGÁVEL

Um documento com: (a) as seis seções acima, cada afirmação numérica com fonte em link e data; (b) uma lista final de 10 FATOS CITÁVEIS — frases curtas, com número e fonte, prontas para ir ao slide; (c) uma seção "o que eu não consegui provar", listando o que ficou sem fonte.

REGRAS

Pesquise antes de afirmar; não responda de memória. Toda afirmação numérica precisa de fonte com link e data. Marque explicitamente o que é dado verificado, o que é estimativa sua e o que é premissa. Prefira escrever "não encontrei" a preencher com número plausível — número inventado no pitch é morte na sabatina. Fontes brasileiras e primárias têm prioridade. Escreva em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 02</span>

## TAM, SAM, SOM

</div>

O erro clássico aqui é o número de cima para baixo — "o mercado global de compliance vale X bilhões, se pegarmos 1%…" — que qualquer jurado de negócio derruba em uma pergunta. O brief força construção de baixo para cima, com cada premissa numerada e atacável.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR".

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas (termos de embargo do Ibama, alertas de desmatamento, CAR) e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque. Depois disso, vigia continuamente: se um novo embargo ou alerta atinge um talhão, o dossiê é reaberto e regerado sozinho.

O QUE NÃO FAZEMOS: não emitimos nem submetemos a Declaração de Due Diligence (DDS) no TRACES — quem faz isso é o importador europeu. Não cobramos documento de fornecedor. Não damos parecer jurídico nem certificação. Não regularizamos CAR.

CLIENTE-ALVO: cooperativas e exportadores de cacau mid-market no Brasil. Região da demo: Transamazônica, Pará.

CONTEXTO REGULATÓRIO: Regulamento (UE) 2023/1115, alterado pelo Reg. (UE) 2025/2650. Prazos: 30/12/2026 para grandes e médios, 30/06/2027 para micro e pequenos. O Brasil é classificado como país de "risco padrão". Uma DDS pode cobrir até 12 meses de remessas. Operadores devem conservar dados de fornecedores por 5 anos.

MODELO DE RECEITA PREVISTO: taxa de ingestão e padronização cobrada por produtor processado; assinatura anual por fornecedor ativo vigiado; taxa por dossiê emitido; módulo de vigilância contínua.

CRITÉRIOS DE AVALIAÇÃO DO HACKATHON: problema e mercado 20%, potencial de negócio 20%, produto e funcionamento 25%, grau de autonomia e substituição de trabalho 20%, pitch e clareza 15%.

SUA MISSÃO

Construir um dimensionamento TAM / SAM / SOM que sobreviva a um jurado hostil.

Estrutura que eu quero:

TAM — o gasto anual com evidência e conformidade EUDR em toda a cadeia brasileira das commodities cobertas (cacau, café, soja, carne, madeira, borracha, palma). Não é o valor exportado; é o quanto se gasta ou se gastará com o trabalho de provar conformidade.

SAM — cacau e café, restrito a cooperativas e exportadores mid-market no Brasil que vendem à União Europeia. Justifique por que esse recorte e não outro.

SOM — o que é plausível capturar em 3 anos, partindo de uma região (Transamazônica ou Sul da Bahia) e de zero cliente. Seja duro: um SOM otimista destrói a credibilidade das outras duas.

REGRAS DE CONSTRUÇÃO

Construa de BAIXO PARA CIMA: número de clientes potenciais multiplicado por preço médio anual plausível. Depois faça uma checagem de sanidade de cima para baixo e mostre a divergência entre os dois métodos — se divergirem muito, discuta por quê em vez de esconder.

Toda premissa numerada (P1, P2, P3...), com fonte ou marcação clara de que é estimativa. Cada número final precisa ser rastreável até as premissas que o produziram. Mostre a fórmula, não só o resultado.

Faça três cenários: conservador, base e otimista. Diga qual usar no pitch e por quê.

ENTREGÁVEL

(a) A memória de cálculo completa, com premissas numeradas e fontes. (b) Os três números, em uma frase cada, do jeito que seriam ditos no palco. (c) Um quadro de sensibilidade mostrando quais duas ou três premissas mais mexem no resultado — são essas que o jurado vai atacar. (d) A resposta pronta para a pergunta "de onde saiu esse número?" para cada um dos três.

REGRAS GERAIS

Pesquise antes de afirmar; não responda de memória. Fonte com link e data para todo dado externo. Marque o que é dado, o que é estimativa e o que é premissa. Prefira "não encontrei" a inventar. Escreva em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 03</span>

## Panorama competitivo

</div>

É aqui que mora o risco que o time não enxerga de dentro. Software de conformidade EUDR não é terreno vazio — existe gente vendendo isso no Brasil e no mundo desde 2023. Pior: os grandes traders podem estar dando sistema de graça ao fornecedor, o que muda a natureza do negócio. Melhor descobrir isso agora do que na sabatina.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR".

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas (termos de embargo do Ibama, alertas de desmatamento, CAR) e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque. Depois disso, vigia continuamente: se um novo embargo ou alerta atinge um talhão, o dossiê é reaberto e regerado sozinho.

O QUE NÃO FAZEMOS: não emitimos nem submetemos a Declaração de Due Diligence (DDS) no TRACES — quem faz isso é o importador europeu. Não cobramos documento de fornecedor. Não damos parecer jurídico nem certificação. Não regularizamos CAR.

CLIENTE-ALVO: cooperativas e exportadores de cacau mid-market no Brasil. Região da demo: Transamazônica, Pará.

NOSSA APOSTA DE DIFERENCIAÇÃO (é isso que você precisa testar): (1) entregamos documentação organizada e não a declaração, o que nos tira da rota de colisão com quem submete no TRACES; (2) a vigilância é contínua, porque uma DDS pode cobrir 12 meses e nesse intervalo um talhão pode ser embargado sem ninguém notar; (3) atacamos a cadeia atomizada de pequenos, onde o custo por produtor inviabiliza consultoria.

CRITÉRIOS DE AVALIAÇÃO DO HACKATHON: problema e mercado 20%, potencial de negócio 20%, produto e funcionamento 25%, grau de autonomia e substituição de trabalho 20%, pitch e clareza 15%.

SUA MISSÃO

Mapear quem já vende isso e responder, sem gentileza, se somos redundantes.

1. MAPEIE OS CONCORRENTES, com nome. Procure em quatro grupos:
   - Plataformas brasileiras de rastreabilidade e compliance agro e ambiental.
   - Plataformas internacionais de due diligence EUDR e cadeia de suprimentos.
   - Provedores de dado geoespacial e alerta de desmatamento que estão subindo na cadeia de valor e vendendo conformidade.
   - Certificadoras e consultorias que estão digitalizando o serviço.

2. PARA CADA UM: o que faz exatamente, para quem vende, preço se for público ou inferível, em que geografia atua, se atende cacau, e qual o buraco que deixa.

3. A PERGUNTA MAIS PERIGOSA: os grandes traders e processadores de cacau (Cargill, Barry Callebaut, Olam/Ofi, Sucden, e no Brasil também as moageiras) já oferecem sistema de rastreabilidade próprio aos seus fornecedores, de graça ou embutido no contrato? Investigue isso a fundo. Se a resposta for sim e amplamente, o nosso mercado encolhe muito — e eu preciso saber agora. Avalie também se isso nos torna canal em vez de concorrente.

4. QUEM MORREU OU PIVOTOU. Procure startups de rastreabilidade agro que fecharam, foram compradas ou mudaram de rumo. O cemitério ensina mais que os vencedores.

5. VEREDITO. Depois de tudo: somos diferentes ou somos mais um? Responda em um parágrafo direto. Se formos redundantes, diga. Se houver um recorte onde somos genuinamente únicos, nomeie esse recorte com precisão.

ENTREGÁVEL

(a) Tabela comparativa dos concorrentes encontrados, com as colunas do item 2. (b) O veredito do item 5. (c) As TRÊS OBJEÇÕES COMPETITIVAS MAIS FORTES que um jurado poderia fazer, cada uma com a melhor resposta honesta disponível — e, quando não houver boa resposta, diga que não há. (d) Uma frase de posicionamento que sobreviva a essas três objeções.

REGRAS GERAIS

Pesquise antes de afirmar; não responda de memória. Nome de empresa sem link não vale. Marque o que é dado verificado e o que é inferência sua. Prefira "não encontrei" a inventar. Escreva em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 04</span>

## Red team

</div>

Escrito de propósito para ser hostil. A instrução mais importante do brief é a última: a sessão está proibida de terminar sem apontar o furo mais fatal. Vale rodar essa duas vezes, em sessões separadas, e comparar — furos diferentes costumam aparecer.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR". Preciso que você tente destruir este projeto antes que um jurado faça isso.

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas (termos de embargo do Ibama, alertas de desmatamento, CAR) e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque. Depois disso, vigia continuamente: se um novo embargo ou alerta atinge um talhão, o dossiê é reaberto e regerado sozinho.

O QUE NÃO FAZEMOS: não emitimos nem submetemos a Declaração de Due Diligence (DDS) no TRACES — quem faz isso é o importador europeu. Não cobramos documento de fornecedor. Não damos parecer jurídico nem certificação. Não regularizamos CAR.

ARQUITETURA EM QUATRO LAÇOS: (1) Ingestão — lê e padroniza os arquivos de cada produtor; (2) Verificação — cruza cada talhão contra embargo do Ibama, alerta de desmatamento pós-31/12/2020, CAR, validade documental e coerência entre área e volume declarado; (3) Vigilância — rotina diária que reabre dossiês quando o mundo muda; (4) Montagem — regenera o PDF versionado. O humano só entra na fila de exceções e na assinatura final.

CLIENTE-ALVO: cooperativas e exportadores de cacau mid-market no Brasil. Região da demo: Transamazônica, Pará.

CONTEXTO REGULATÓRIO: Regulamento (UE) 2023/1115, alterado pelo Reg. (UE) 2025/2650. Prazos: 30/12/2026 para grandes e médios, 30/06/2027 para micro e pequenos. O Brasil é país de "risco padrão". Uma DDS pode cobrir até 12 meses de remessas. Operadores devem conservar dados por 5 anos.

MODELO DE RECEITA: taxa de ingestão por produtor processado; assinatura anual por fornecedor vigiado; taxa por dossiê; módulo de vigilância.

RECURSOS: time pequeno, sem desenvolvedores dedicados, 2 dias, sem acesso a cliente real para validar.

CRITÉRIOS DE AVALIAÇÃO: problema e mercado 20%, potencial de negócio 20%, produto e funcionamento 25%, grau de autonomia e substituição de trabalho 20%, pitch e clareza 15%.

SUA MISSÃO

Ser o avaliador mais cético e mais bem informado da sala. Não me elogie, não equilibre críticas com pontos positivos, não termine com uma nota otimista. Seu único trabalho é achar onde isso quebra.

Ataque em sete frentes:

1. TESE REGULATÓRIA. Estamos lendo o regulamento certo? A obrigação que descrevemos existe mesmo do lado brasileiro, ou o peso está todo no importador europeu de um jeito que nos deixa vendendo para quem não é obrigado a comprar? Verifique o texto e a orientação da Comissão. Cheque também se houve mudança regulatória recente que enfraqueça a urgência — inclusive novos adiamentos ou simplificações.

2. QUEM PAGA. A cooperativa tem orçamento e autonomia para comprar software? Quem decide? Cooperativa de agricultura familiar no Pará compra SaaS? Se não, para quem estamos vendendo de verdade — e esse alguém quer isso?

3. PRODUTO E TÉCNICA. As bases públicas realmente sustentam as checagens? A lista de embargos do Ibama serve para o que dizemos? Dá para cruzar talhão contra CAR sem acesso privilegiado? A checagem de coerência de volume tem poder estatístico real ou é teatro? O que acontece quando o talhão é um ponto e não um polígono?

4. AUTONOMIA. O sistema é mesmo autônomo ou é um pipeline com nome bonito? Onde o humano vai acabar entrando muito mais do que admitimos? Quantas exceções por mil documentos isso geraria na vida real, e a cooperativa aguenta essa fila?

5. RESPONSABILIDADE. Se o dossiê estiver errado e a carga for barrada, de quem é a culpa? O selo de aprovação humana resolve juridicamente ou é fig leaf? Isso é seguro ou é passivo?

6. DEFENSIBILIDADE. O que impede uma consultoria, um trader ou uma plataforma existente de fazer o mesmo em três meses? O dado acumulado é mesmo um fosso ou é ilusão?

7. EXECUÇÃO. Esse escopo cabe em 2 dias com time pequeno e sem devs? O que provavelmente vai falhar no palco?

ENTREGÁVEL

(a) Lista priorizada de furos, cada um com: severidade (fatal, grave, incômodo), a evidência que sustenta a crítica, e o que faria esse furo desaparecer. (b) As 10 PERGUNTAS MAIS DURAS que um jurado poderia fazer, cada uma com uma nota de 0 a 5 de quão bem o projeto responde hoje. (c) A seção final obrigatória, chamada "O FURO MAIS FATAL": qual é o único problema que, se não for resolvido, condena o projeto — e por quê.

REGRAS

Pesquise para sustentar as críticas; crítica sem evidência é opinião. É proibido ser gentil, é proibido "por outro lado" e é proibido terminar sem preencher a seção do furo mais fatal. Se você concluir que o projeto está bem, você falhou na tarefa — procure mais fundo. Escreva em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

</div>

<div class="tier">

<span class="t">Nível 2 · destrava a construção</span><span class="d">rode em paralelo com o nível 1 se houver gente sobrando</span>

</div>

<div class="section">

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 05</span>

## Taxonomia documental do cacau

</div>

É o insumo direto do laço de ingestão: sem saber quais documentos existem, que campos cada um tem e qual regra de vigência se aplica, não dá para escrever o classificador nem o extrator. Essa frente vira esquema de dados no dia 1 e economiza horas.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR".

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque, mantido sob vigilância contínua.

O QUE NÃO FAZEMOS: não emitimos a Declaração de Due Diligence no TRACES, não damos parecer jurídico, não regularizamos CAR.

CONTEXTO REGULATÓRIO: Regulamento (UE) 2023/1115, alterado pelo Reg. (UE) 2025/2650. O EUDR exige, entre outras coisas, geolocalização das parcelas de produção, data ou intervalo de produção, quantidade, identificação do fornecedor, e prova de que a produção é legal na legislação do país de origem. O Brasil é país de "risco padrão", então não há via simplificada.

CADEIA: cacau, produtores pequenos, Transamazônica no Pará e Sul da Bahia.

SUA MISSÃO

Produzir a taxonomia completa dos documentos que circulam nessa cadeia e que servem de prova sob o EUDR. Isso vai virar o esquema de dados do nosso classificador.

Para CADA tipo de documento, levante:
- Nome oficial e como as pessoas realmente chamam ele no campo.
- Quem emite e como se obtém.
- Que campos ele contém (os que dá para extrair automaticamente).
- Regra de vigência: vence? em quanto tempo? como se sabe se está válido?
- Qual exigência do EUDR ele ajuda a satisfazer — seja específico, cite o artigo quando der.
- Como ele costuma chegar na prática: PDF gerado por sistema, digitalização, foto de celular, papel.
- Armadilhas de leitura: campos que confundem, versões antigas do layout, variações estaduais.

Comece pelo menos por estes e acrescente o que faltar: CAR (Cadastro Ambiental Rural), recibo e demonstrativo do SiCAR, CCIR, ITR, matrícula do imóvel ou documento de posse, contrato de compra e venda, nota fiscal de produtor rural, DAP ou CAF, licenças e autorizações ambientais estaduais, certificado de georreferenciamento SIGEF ou memorial descritivo, certificações voluntárias (Rainforest Alliance, orgânico, Fair Trade), declaração de não-desmatamento, e o que mais aparecer.

Depois, responda a três perguntas de desenho:
1. Qual é o CONJUNTO MÍNIMO de documentos que torna um produtor "apto" para compor um lote destinado à UE? Justifique.
2. Que documentos costumam FALTAR na prática em cooperativa de agricultura familiar no Pará? Essa lista vira nosso mapa de lacunas.
3. Que CONFLITOS entre documentos são detectáveis automaticamente? Exemplo: nome ou CPF do CAR diferente do da nota fiscal; área do CAR menor que a área declarada; matrícula de um município e CAR de outro. Liste o máximo de regras de inconsistência que conseguir imaginar — cada uma delas vira uma checagem do produto.

ENTREGÁVEL

(a) A tabela de tipos documentais com todos os campos acima, pronta para virar esquema. (b) O conjunto mínimo de aptidão. (c) A lista de lacunas típicas. (d) A lista de regras de inconsistência automática, numeradas. (e) Uma proposta de nomenclatura padronizada de arquivo, do tipo TIPO_PRODUTOR_DATA_VERSAO, que o sistema aplicaria ao renomear.

REGRAS

Pesquise antes de afirmar; documentos brasileiros mudam de layout e de exigência. Fonte com link para o que for regra formal. Marque o que é prática de campo e não norma. Prefira "não encontrei" a inventar campo que não existe. Escreva em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 06</span>

## Dataset da demo

</div>

Não é pesquisa, é construção — e é o gargalo do dia 1. Rodar isso em paralelo significa chegar na hora zero com a cooperativa sintética pronta, os conflitos já plantados sobre polígonos de embargo reais e os grupos de arquivos montados. Sessão que precisa executar código, não só escrever.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR": um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes fora de padrão — padroniza, cruza os talhões contra bases públicas (embargos do Ibama, alertas de desmatamento, CAR) e gera um dossiê de conformidade em PDF por lote de embarque, mantido sob vigilância contínua.

Preciso do conjunto de dados da demonstração, construído de verdade. Esta sessão é de execução, não de pesquisa.

SUA MISSÃO

Construir uma cooperativa de cacau fictícia, mas geograficamente real, e o acervo documental dela.

1. BASE GEOESPACIAL REAL. Baixe os termos de embargo do Ibama (dados abertos, shapefile de polígonos, download direto sem autenticação). Confira a data de atualização e a cobertura, e me diga o que encontrou — há indício de que os metadados públicos apontam atualização antiga, e preciso saber a verdade antes de construir em cima. Recorte a região da Transamazônica no Pará (Medicilândia, Altamira, Uruará, Brasil Novo).

2. A COOPERATIVA. Gere cerca de 60 produtores de cacau com nomes brasileiros plausíveis, CPF fictício mas com formato válido, e um a três talhões cada. Talhões entre 2 e 10 hectares, alguns como ponto e outros como polígono, todos dentro da região recortada. IMPORTANTE: posicione de três a cinco talhões DE PROPÓSITO sobrepostos a polígonos de embargo reais, e mais alguns na borda, quase tocando — a demo precisa de conflito verdadeiro e de caso limítrofe.

3. OS GRUPOS DE ARQUIVOS. Para cada produtor, monte um grupo de cinco a dez arquivos fora de padrão, como chegariam na vida real: nomes ruins (IMG_4471.jpg, doc scan 3.pdf, planilha final v2.xlsx, documento sem titulo.pdf), tipos misturados (PDF gerado, digitalização torta, foto de celular, planilha). Inclua deliberadamente: um arquivo ilegível, um documento vencido, um cujo CPF diverge do produtor do grupo, um duplicado com nome diferente, e um que não é documento nenhum (foto do cacau secando). Gere o conteúdo dos documentos de forma consistente com os dados do produtor.

4. OS LOTES. Componha três lotes de embarque, cada um agregando de 10 a 40 produtores, com sobreposição entre eles — pelo menos um produtor precisa estar em três lotes ao mesmo tempo, porque a demonstração depende de um embargo derrubar três dossiês de uma vez.

5. O EVENTO DA DEMO. Prepare um segundo recorte da base de embargos, ou um registro adicional, que represente "o novo embargo que entrou hoje" atingindo justamente aquele produtor presente nos três lotes. Precisa ser algo que eu possa injetar durante a apresentação para a vigilância detectar ao vivo.

ENTREGÁVEL

(a) Um script gerador reproduzível e comentado, com semente fixa, para eu poder regerar tudo. (b) Os arquivos de dados prontos: produtores, talhões em formato geoespacial, lotes, e as pastas de documentos por produtor. (c) Um relatório curto do que existe no dataset: quantos produtores, quantos talhões, quais estão em conflito e por quê, quais arquivos são as armadilhas plantadas e o que cada uma deve provocar no sistema. (d) O que você descobriu sobre a base do Ibama: formato real dos campos, data, cobertura, e qualquer surpresa.

REGRAS

Execute de verdade, não descreva o que faria. Se uma biblioteca faltar, instale. Se o download falhar, diga exatamente o que aconteceu em vez de simular o dado. Dados pessoais devem ser claramente fictícios. Comente o código em português do Brasil.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

</div>

<div class="tier">

<span class="t">Nível 3 · por último</span><span class="d">depende do que as outras trouxerem</span>

</div>

<div class="section">

<div class="brief">

<div class="brief-head">

<span class="brief-num">FRENTE 07</span>

## Pitch e sabatina

</div>

Vale 15% sozinho, mas na prática pesa mais: é através dele que o jurado enxerga os outros 85%. Rode só depois que as frentes 01 a 04 voltarem, colando os resultados delas dentro do brief — sem isso a sessão escreve um pitch genérico.

<div class="block">

<div class="block-bar">

<span class="n">Cole como primeira mensagem</span>

Copiar

</div>

``` brieftext
CONTEXTO DO PROJETO

Estou num hackathon de 2 dias (ATON) construindo o "Evidence Autopilot EUDR" e preciso do roteiro de pitch e da preparação para a sabatina.

O QUE É: um sistema que recebe os documentos que uma cooperativa de cacau já tem — subidos em grupo por produtor, com nomes de arquivo fora de padrão — identifica o tipo de cada arquivo, extrai os campos, padroniza, cruza os talhões contra bases públicas (termos de embargo do Ibama, alertas de desmatamento, CAR) e gera um DOSSIÊ DE CONFORMIDADE em PDF por lote de embarque. Depois disso, vigia continuamente: se um novo embargo ou alerta atinge um talhão, o dossiê é reaberto e regerado sozinho.

O QUE NÃO FAZEMOS: não emitimos nem submetemos a Declaração de Due Diligence no TRACES — quem faz isso é o importador europeu. Não cobramos documento de fornecedor. Não damos parecer jurídico nem certificação. Não regularizamos CAR.

O ARGUMENTO CENTRAL: a cooperativa brasileira nunca foi a emissora da declaração; ela é a fonte da prova, e quem não entrega a prova não embarca. Além disso, uma DDS pode cobrir até 12 meses de remessas — ou seja, o importador assina hoje e fica exposto por um ano, durante o qual um talhão pode ser embargado sem ninguém notar. A UE permitiu declarar uma vez por ano; nós somos o que torna isso seguro.

ROTEIRO ATUAL, 7 MINUTOS: (0:00) o problema com números; (0:45) o upload de arquivos fora de padrão e a ingestão rodando ao vivo; (2:15) o dossiê saindo pronto; (3:15) a vigilância detecta um novo embargo e derruba três lotes sozinha; (5:00) o humano resolve a exceção e assina; (6:00) modelo de receita e por que continuar depois do hackathon.

CRITÉRIOS DE AVALIAÇÃO: problema e mercado 20%, potencial de negócio 20%, produto e funcionamento 25%, grau de autonomia e substituição de trabalho 20%, pitch e clareza 15%. A pergunta que os jurados fazem é dupla: a equipe construiu algo relevante e funcional em dois dias, e vale a pena continuar construindo isso depois?

MATERIAL DE APOIO

[COLE AQUI o resultado da frente 01, sobre o problema e seu preço]
[COLE AQUI o resultado da frente 02, com TAM SAM SOM]
[COLE AQUI o resultado da frente 03, com o panorama competitivo]
[COLE AQUI o resultado da frente 04, com os furos do red team]

SUA MISSÃO

1. ESCREVER O ROTEIRO FALADO, minuto a minuto, na primeira pessoa do plural, pronto para ensaiar. Não bullet points: texto para ser dito. Marque onde a tela muda e onde a pessoa fala olhando para o jurado em vez de para a tela.

2. ENCONTRAR A FRASE. Uma única sentença que resuma o negócio e que o jurado consiga repetir para outro jurado depois. Me dê cinco opções e recomende uma.

3. MAPEAR CADA MINUTO A UM CRITÉRIO, e me mostrar quanto tempo estamos gastando em cada peso. Se estivermos gastando três minutos num critério que vale 15% e quarenta segundos num que vale 25%, aponte.

4. PREPARAR A SABATINA. Quinze perguntas duras, incluindo as que vierem do red team, cada uma com: a resposta em até trinta segundos, o que NÃO dizer, e — quando a resposta honesta for fraca — a melhor forma de admitir a limitação sem perder o jurado.

5. TRATAR O DESASTRE. O que dizer se a demo falhar ao vivo. Escreva as três frases de recuperação.

ENTREGÁVEL

(a) O roteiro falado completo, cronometrado. (b) As cinco frases-síntese com recomendação. (c) O mapa tempo por critério. (d) As quinze perguntas com respostas. (e) O plano de desastre.

REGRAS

Nada de jargão de startup vazio. Nada de superlativo sem número atrás. Se uma parte do pitch só funcionar com um dado que não temos, marque em destaque em vez de escrever a frase bonita. Escreva em português do Brasil, no registro de quem fala com gente do agro e com investidor na mesma sala.

FORMATO DA ENTREGA

O documento final deve conter APENAS a posição final e os dados concretos que a sustentam. Não narre seu processo, não escreva "inicialmente eu achava", não registre mudança de rota, não conte como chegou lá. Este material vira insumo direto do nosso pitch, e a banca não precisa ver o caminho — só a conclusão e a evidência que a sustenta. Escreva como quem já sabe.

A única exceção é a seção de limitações, incertezas e do que não foi possível provar, quando o brief pedir uma: essa é de uso interno nosso, e deve vir claramente marcada como tal, separada do resto.
```

Ver o brief inteiro

</div>

</div>

</div>

<div class="section">

## O que ficou de fora, e por quê

Três frentes que considerei e cortei, para vocês saberem que a escolha foi deliberada:

**Fontes de monitoramento regulatório.** O laço de vigilância precisa saber onde olhar — Diário Oficial, EUR-Lex, atos da Comissão, atualizações do Ibama e do DETER. É trabalho real, mas cabe dentro da frente 05 se vocês pedirem, e não vale uma sessão inteira agora.

**Validação com cliente real.** A frente mais valiosa de todas e a única que uma sessão de IA não resolve. Se alguém do time tiver qualquer contato numa cooperativa de cacau, numa certificadora ou numa consultoria ambiental, meia hora de telefone vale mais que as sete frentes somadas. Vale gastar um pedido no LinkedIn hoje.

**Nome e identidade.** Importa para o pitch, mas é decisão de gosto do time e não de pesquisa. Resolvam numa conversa de dez minutos, não numa sessão.

</div>

</div>
