# Interface — conceitos de tela

*Evidence Autopilot EUDR · ATON · versão em markdown do artefato*
*Original com formatação: https://claude.ai/code/artifact/4d5ff711-8959-4794-9d06-b4cfd104de81*

---

<div class="masthead">

<div class="wrap">

Evidence Autopilot EUDR · Briefing de interface · para o designer

# Esboço da Interface

Quatro telas, e o problema de design que as define: o produto trabalha enquanto ninguém olha, e isso é difícil de mostrar numa tela parada.

</div>

</div>

<div class="wrap" role="main">

<div class="section">

<div class="sec-head">

<span class="sec-num">01</span>

## O problema de design, antes das telas

</div>

Tudo o que este produto vende acontece quando o usuário não está olhando. Ele coleta, verifica, vigia e regenera sozinho. Quando a pessoa abre a tela, o trabalho já foi feito.

Isso inverte a lógica de quase todo software de gestão. O padrão é uma interface que mostra *tudo* e espera que você trabalhe nela. Aqui, a interface precisa mostrar **que não há nada para você fazer** — e ainda assim provar que muita coisa aconteceu.

Daí saem três princípios que valem mais que qualquer escolha de cor:

<div class="grid g3">

<div class="card">

<span class="label">Princípio 1</span>

### Todo estado carrega tempo

Nunca "conforme". Sempre "conforme, verificado há 2 horas". Sem a marca de tempo, o usuário não distingue um sistema vivo de um relatório velho — e é essa distinção que ele está comprando.

</div>

<div class="card">

<span class="label">Princípio 2</span>

### A tela cheia é a fila, não o painel

A home é a fila de exceções, e o estado saudável dela é **vazia**. Um painel de status verde diz "olhe para mim"; uma fila vazia diz "eu cuido, você decide quando eu chamar".

</div>

<div class="card">

<span class="label">Princípio 3</span>

### Dois requisitos, sempre lado a lado

Nunca um semáforo só. "Livre de desmatamento" e "Requisitos de legalidade" em colunas separadas, com a **contagem de evidências** em cada uma. São as palavras do próprio regulamento, e a assimetria dos números é o argumento.

</div>

</div>

<div class="callout">

**A assimetria é intencional e deve ser visível.** A coluna de desmatamento tem pouca evidência e fica quase sempre verde — é checagem barata, que várias plataformas fazem de graça. A de legalidade tem o dobro ou o triplo de evidências e é onde mora o amarelo e o vermelho. Quando o designer olhar para a tela de lotes e vir uma coluna curta e calma ao lado de uma longa e agitada, está certo: essa imagem *é* o pitch, e ela dispensa legenda.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">02</span>

## Tela 1 · A fila — e seu estado vazio

</div>

A tela inicial. Mostro as duas versões porque o estado vazio é, na minha leitura, a melhor ideia de design que este produto tem.

<div class="mock">

<div class="m-top">

<span class="m-logo">Evidence Autopilot</span>

<div class="m-nav">

<span class="on">Fila</span>LotesProdutoresDossiês

</div>

<div class="m-count">

**1.284** verificações hoje · **41** documentos lidos · **3** dossiês regerados

</div>

</div>

<div class="m-body">

3 coisas precisam de você

Coop. Transamazônica · 60 produtores vigiados · última varredura há 4 minutos

<div class="m-row crit">

<span class="m-id">TAL-014</span>

<div class="m-main">

**Embargo novo sobre talhão de José R. Marinho** Termo 8842/2026 do Ibama, sobreposição de 1,8 ha · afeta 3 lotes

</div>

<span class="chip stop">Bloqueio</span> <span class="m-when">há 4 min</span> <span class="m-btn solid">Resolver</span>

</div>

<div class="m-row att">

<span class="m-id">DOC-2291</span>

<div class="m-main">

**CPF do CAR diverge da nota fiscal** Maria Aparecida S. — CAR em nome de terceiro · pode ser arrendamento

</div>

<span class="chip warn">Revisão</span> <span class="m-when">há 2 h</span> <span class="m-btn">Resolver</span>

</div>

<div class="m-row att">

<span class="m-id">TAL-037</span>

<div class="m-main">

**Volume entregue acima do que a área comporta** 4,2 ha entregaram o equivalente a 31 ha na safra · 740% do esperado

</div>

<span class="chip warn">Revisão</span> <span class="m-when">há 6 h</span> <span class="m-btn">Resolver</span>

</div>

<div class="m-feed">

<div class="fh">

<span class="dot"></span>Enquanto isso, sem precisar de você

</div>

<div class="fl">

<span class="ft">14:22</span>Varredura de embargos concluída — **60 talhões** verificados, 1 alteração

</div>

<div class="fl">

<span class="ft">14:22</span>Dossiês **CAC-2026-114**, **117** e **121** regerados para a versão 4

</div>

<div class="fl">

<span class="ft">11:05</span>7 documentos de **Antônio B. da Cruz** lidos e padronizados

</div>

<div class="fl">

<span class="ft">09:30</span>Alertas de desmatamento atualizados — nenhuma alteração

</div>

</div>

</div>

</div>

Estado normal: a fila com o que exige decisão, e embaixo o registro do que o sistema fez sozinho.

<div class="mock">

<div class="m-top">

<span class="m-logo">Evidence Autopilot</span>

<div class="m-nav">

<span class="on">Fila</span>LotesProdutoresDossiês

</div>

<div class="m-count">

**1.284** verificações hoje · **41** documentos lidos · **0** pendências

</div>

</div>

<div class="m-body">

<div class="m-empty">

<div class="big">

Nada precisa de você agora.

</div>

Os 3 lotes abertos estão com dossiê completo e verificado. A última varredura foi há 4 minutos e não encontrou alteração.

<span class="m-btn">Ver o que foi feito hoje</span>

</div>

<div class="m-feed">

<div class="fh">

<span class="dot"></span>Últimas 24 horas

</div>

<div class="fl">

<span class="ft">14:22</span>Varredura de embargos — **60 talhões**, nenhuma alteração

</div>

<div class="fl">

<span class="ft">11:05</span>7 documentos lidos e padronizados

</div>

<div class="fl">

<span class="ft">09:30</span>2 certidões vencendo em 30 dias — sinalizadas na ficha, sem bloqueio

</div>

</div>

</div>

</div>

Estado vazio: o produto entregando o que promete. É a tela que o cliente mais vai ver, e a que mais precisa ser bem feita.

<div class="callout warn">

**Para o designer, a instrução mais importante desta página:** o estado vazio não é uma tela de erro nem um placeholder. É o produto funcionando. Ele merece mais cuidado tipográfico que qualquer outra tela, e não pode parecer que faltou carregar alguma coisa.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">03</span>

## Tela 2 · Lotes, com os dois requisitos

</div>

É aqui que a assinatura visual do produto aparece, e é a tela que vai para o slide.

<div class="mock">

<div class="m-top">

<span class="m-logo">Evidence Autopilot</span>

<div class="m-nav">

Fila<span class="on">Lotes</span>ProdutoresDossiês

</div>

<div class="m-count">

safra 2026 · **3** lotes abertos

</div>

</div>

<div class="m-body">

Lotes de embarque

Cada lote carrega o estado corrente dos talhões que o compõem

<div class="m-row crit">

<span class="m-id">CAC-2026-114</span>

<div class="m-main">

**38 produtores · 12.500 kg**Embarque previsto 18/09 · Barry Callebaut

</div>

<div class="pernas">

<div class="perna g">

<span class="pl">LIVRE DE DESMATAMENTO</span><span class="pv">Conforme</span><span class="pn">96 evidências</span>

</div>

<div class="perna r">

<span class="pl">REQUISITOS DE LEGALIDADE</span><span class="pv">1 bloqueio</span><span class="pn">214 evid. · 7 lacunas</span>

</div>

</div>

<span class="m-when">v4 · há 4 min</span>

</div>

<div class="m-row crit">

<span class="m-id">CAC-2026-117</span>

<div class="m-main">

**22 produtores · 8.100 kg**Embarque previsto 02/10 · Cargill

</div>

<div class="pernas">

<div class="perna g">

<span class="pl">LIVRE DE DESMATAMENTO</span><span class="pv">Conforme</span><span class="pn">61 evidências</span>

</div>

<div class="perna r">

<span class="pl">REQUISITOS DE LEGALIDADE</span><span class="pv">1 bloqueio</span><span class="pn">137 evid. · 4 lacunas</span>

</div>

</div>

<span class="m-when">v4 · há 4 min</span>

</div>

<div class="m-row att">

<span class="m-id">CAC-2026-121</span>

<div class="m-main">

**31 produtores · 10.900 kg**Embarque previsto 14/10 · ofi

</div>

<div class="pernas">

<div class="perna g">

<span class="pl">LIVRE DE DESMATAMENTO</span><span class="pv">Conforme</span><span class="pn">84 evidências</span>

</div>

<div class="perna y">

<span class="pl">REQUISITOS DE LEGALIDADE</span><span class="pv">2 revisões</span><span class="pn">186 evid. · 11 lacunas</span>

</div>

</div>

<span class="m-when">v4 · há 4 min</span>

</div>

<div class="m-row fine">

<span class="m-id">CAC-2026-108</span>

<div class="m-main">

**17 produtores · 5.400 kg**Embarcado 22/08 · dossiê arquivado por 5 anos

</div>

<div class="pernas">

<div class="perna g">

<span class="pl">LIVRE DE DESMATAMENTO</span><span class="pv">Conforme</span><span class="pn">44 evidências</span>

</div>

<div class="perna g">

<span class="pl">REQUISITOS DE LEGALIDADE</span><span class="pv">Conforme</span><span class="pn">98 evid. · 0 lacunas</span>

</div>

</div>

<span class="m-when">v6 · aprovado</span>

</div>

</div>

</div>

Três lotes caindo juntos por causa de um talhão só — o efeito em cascata, que é o clímax da demo.

<div class="callout">

**O número e o veredito são coisas diferentes.** O status é a conclusão da categoria; a contagem é o trabalho por trás dela. E "lacuna" não é o mesmo que não-conforme: uma categoria pode estar verde em tudo o que foi verificado e ainda ter documentos que não existem. Em desmatamento não há lacuna, porque a base está sempre disponível para consulta — em legalidade, o que falta é justamente o que a cooperativa precisa ir buscar, e é o número mais acionável do produto.

**Detalhe que carrega a tese:** a coluna de desmatamento mostra número pequeno e verde; a de legalidade, número grande e com bloqueio ou revisão. Não force simetria visual entre as duas — a diferença entre elas é o argumento. E note o último lote, já embarcado: ele continua na tela porque a lei obriga conservar por cinco anos, e vigilância que não para é o que sustenta a receita recorrente.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">04</span>

## Tela 3 · Ficha do produtor, antes e depois

</div>

É onde a ingestão fica visível. Mostrar o antes e o depois lado a lado explica o produto sem uma palavra.

<div class="mock">

<div class="m-top">

<span class="m-logo">Evidence Autopilot</span>

<div class="m-nav">

FilaLotes<span class="on">Produtores</span>Dossiês

</div>

<div class="m-count">

60 produtores · **52** aptos

</div>

</div>

<div class="m-body">

Antônio B. da Cruz

Medicilândia, PA · 3 talhões · 7,4 ha · presente nos lotes 114, 117 e 121

<div class="m-two">

<div class="m-panel">

<div class="ph">

Como chegou — 7 arquivos

</div>

<div class="m-doc">

<span class="dn">IMG_4471.jpg</span><span class="dm">2,1 MB</span>

</div>

<div class="m-doc">

<span class="dn">doc scan (3).pdf</span><span class="dm">840 KB</span>

</div>

<div class="m-doc">

<span class="dn">WhatsApp Image 2026-03-11.jpeg</span><span class="dm">1,4 MB</span>

</div>

<div class="m-doc">

<span class="dn">planilha final v2.xlsx</span><span class="dm">24 KB</span>

</div>

<div class="m-doc">

<span class="dn">documento sem titulo.pdf</span><span class="dm">310 KB</span>

</div>

<div class="m-doc">

<span class="dn">foto roça.jpg</span><span class="dm">3,0 MB</span>

</div>

<div class="m-doc">

<span class="dn">CCF_000121.pdf</span><span class="dm">512 KB</span>

</div>

</div>

<div class="m-panel">

<div class="ph">

Como ficou — lido em 41 segundos

</div>

<div class="m-doc">

<span class="chip ok">CAR</span><span class="dn">CAR_antonio-cruz_20240318_v1</span><span class="dm">vál.</span>

</div>

<div class="m-doc">

<span class="chip ok">Matrícula</span><span class="dn">MATRICULA_antonio-cruz_20190402_v1</span><span class="dm">vál.</span>

</div>

<div class="m-doc">

<span class="chip ok">NF produtor</span><span class="dn">NFP_antonio-cruz_20260311_v1</span><span class="dm">vál.</span>

</div>

<div class="m-doc">

<span class="chip warn">Vencido</span><span class="dn">CCIR_antonio-cruz_20230115_v1</span><span class="dm">exp.</span>

</div>

<div class="m-doc">

<span class="chip stop">Ilegível</span><span class="dn">— não foi possível ler</span><span class="dm">rev.</span>

</div>

<div class="m-doc">

<span class="chip mut">Não é doc</span><span class="dn">foto roça.jpg — arquivada</span><span class="dm">—</span>

</div>

</div>

</div>

<div class="m-panel" style="margin-top:12px">

<div class="ph">

O que falta para ficar apto

</div>

<div class="m-doc">

<span class="chip warn">Falta</span><span class="dn">Certidão negativa de débitos trabalhistas (CNDT)</span><span class="dm">cat. 5</span>

</div>

<div class="m-doc">

<span class="chip warn">Renovar</span><span class="dn">CCIR vencido em 15/01/2026</span><span class="dm">cat. 1</span>

</div>

</div>

</div>

</div>

Lixo à esquerda, ficha padronizada à direita, e embaixo o mapa de lacunas — sem cobrar ninguém.

<div class="callout">

**Para o designer:** a coluna da esquerda precisa parecer desagradável de propósito — nomes truncados, tamanhos em megabytes, nenhuma ordem. É o contraste que faz o trabalho. E o "lido em 41 segundos" no cabeçalho da direita não é enfeite: é o número que substitui o trabalho de uma pessoa.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">05</span>

## Tela 4 · Dossiê e suas versões

</div>

A tela que prova que o documento é vivo. Cada versão diz por que existiu.

<div class="mock">

<div class="m-top">

<span class="m-logo">Evidence Autopilot</span>

<div class="m-nav">

FilaLotesProdutores<span class="on">Dossiês</span>

</div>

<div class="m-count">

CAC-2026-114 · **4** versões

</div>

</div>

<div class="m-body">

Dossiê de conformidade · CAC-2026-114

38 produtores · 12.500 kg · Barry Callebaut · embarque previsto 18/09

<div class="m-ver now">

<span class="vn">v4</span>

<div class="vd">

**Rascunho — aguarda aprovação**  
<span style="color:#7A736A">Talhão TAL-014 passou de conforme para bloqueio na checagem 02 (embargo Ibama, termo 8842/2026)</span>

</div>

<span class="chip stop">Bloqueado</span> <span class="m-when">há 4 min · sistema</span>

</div>

<div class="m-ver">

<span class="vn">v3</span>

<div class="vd">

Aprovado por Cláudia Menezes, gerente de qualidade  
<span style="color:#7A736A">2 documentos novos de Antônio B. da Cruz incorporados</span>

</div>

<span class="chip ok">Aprovado</span> <span class="m-when">11/03 · humano</span>

</div>

<div class="m-ver">

<span class="vn">v2</span>

<div class="vd">

Regerado automaticamente  
<span style="color:#7A736A">CCIR de 3 produtores marcado como vencido</span>

</div>

<span class="chip mut">Substituída</span> <span class="m-when">28/02 · sistema</span>

</div>

<div class="m-ver">

<span class="vn">v1</span>

<div class="vd">

Primeira geração  
<span style="color:#7A736A">38 produtores, 96 talhões verificados</span>

</div>

<span class="chip mut">Substituída</span> <span class="m-when">14/02 · sistema</span>

</div>

<div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">

<span class="m-btn solid">Abrir PDF da v4</span> <span class="m-btn">Comparar v3 e v4</span> <span class="m-btn">Aprovar e selar</span>

</div>

</div>

</div>

Cada versão com o motivo dela e o autor — sistema ou humano. É a trilha de auditoria virando interface.

<div class="callout">

**A coluna "sistema ou humano" não é detalhe técnico.** Ela é a prova visual de autonomia: numa lista de quatro versões, três foram feitas pelo sistema sozinho. Se o designer tiver que escolher o que destacar nesta tela, é isso.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">06</span>

## O que está fixo e o que o designer decide

</div>

<div class="grid g2">

<div class="card">

### Fixo — vem do produto, não é gosto

- Duas colunas em toda tela com status, com o nome do regulamento — "Livre de desmatamento" e "Requisitos de legalidade" — e a contagem de evidências em cada
- Marca de tempo em todo estado: "verificado há X"
- A fila como tela inicial, com estado vazio trabalhado
- Distinção visível entre ação do sistema e ação humana
- Contador de autonomia sempre visível no topo
- Três níveis semânticos: conforme, revisão, bloqueio

</div>

<div class="card">

### Livre — e onde queremos a opinião dele

- Toda a paleta. Os tons aqui são de rascunho, não de marca
- Tipografia inteira
- Como o registro de atividade aparece — linha do tempo, feed, outra coisa
- Como mostrar o mapa e a sobreposição de embargo
- Densidade: isso é ferramenta de trabalho diário, não vitrine
- O que acontece no celular — o gerente de cooperativa vive no celular

</div>

</div>

<div class="callout stop">

**O aviso que evita retrabalho amanhã:** isto é esboço de PM, não de designer. As telas existem para ele ter algo com que discordar, não para ele reproduzir. Se ele quiser reorganizar tudo, ótimo — desde que os seis itens da coluna "fixo" sobrevivam, porque cada um deles carrega um pedaço do argumento comercial.

</div>

<div class="callout warn">

**E a prioridade, se ele só tiver tempo para uma tela:** a fila com o estado vazio. É a que o cliente mais vê, é a que comunica autonomia, e é a única que não existe em nenhum concorrente — todos eles entregam painel, e painel é o oposto do que estamos vendendo.

</div>

</div>

</div>
