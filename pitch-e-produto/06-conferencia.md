# Lista de Conferência — outputs e testes

*Evidence Autopilot EUDR · ATON · versão em markdown do artefato*
*Original com formatação: https://claude.ai/code/artifact/4fd6ad7c-d0ba-4a6a-9121-544b07520bab*

---

<div role="main">

<div>

Evidence Autopilot EUDR · ATON · conferência de entrega

# Lista de conferência

O que tem que sair do sistema, o que tem que estar dentro do dossiê, e como conferir cada coisa. A coluna que importa é a última: **o que reprova** — é ela que transforma esta lista em teste em vez de desejo.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">01</span>

## Os cinco outputs — não é só o dossiê

</div>

O dossiê é o entregável que o cliente compra, mas sozinho ele não prova autopilot. São cinco saídas, e a demo precisa das cinco.

<div class="tablewrap">

| Output                        | Natureza                                                                    | Onde vive                          | Para que serve na demo                                                            |
|-------------------------------|-----------------------------------------------------------------------------|------------------------------------|-----------------------------------------------------------------------------------|
| **1 · Ficha do produtor**     | <span class="pill ok">Viva</span> permanente, muda quando chega documento   | Tela                               | Prova que a ingestão funcionou: entrou pasta bagunçada, saiu ficha organizada     |
| **2 · Dossiê do lote**        | <span class="pill warn">Congelada</span> recorte de um instante, versionada | PDF **e** HTML em `saida/dossies/` | É o produto. É o que aparece na tela no fim                                       |
| **3 · Fila de exceções**      | <span class="pill ok">Viva</span> ordenada por severidade                   | Tela                               | Prova que o sistema decide o que merece atenção humana — e que não decide sozinho |
| **4 · Trilha de eventos**     | Append-only, nunca apagada                                                  | Tabela `evento` + contador na tela | **É o que prova autonomia no palco.** Sem contador, "autopilot" é palavra         |
| **5 · Arquivos padronizados** | Espelho em disco                                                            | `dados/padronizado/<produtor>/`    | Output invisível e o mais convincente: abrir a pasta e ver os nomes certos        |

</div>

<div class="box">

O output que quase sempre é esquecido

O **5**. Vale abrir a pasta ao vivo na demo, lado a lado com a pasta de entrada. `foto_2843.jpg` virando `CAR-DEM_70123456789_20260514_v01.pdf` é a coisa mais fácil de entender do produto inteiro, e não custa nenhum slide.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">02</span>

## Ficha do produtor — o que tem que ter

</div>

<div class="tablewrap">

| Bloco                  | Conteúdo mínimo                                                                | Reprova se                                               |
|------------------------|--------------------------------------------------------------------------------|----------------------------------------------------------|
| **Identificação**      | Nome, CPF, município e UF, cooperativa                                         | CPF ausente — é a chave de junção de todas as checagens  |
| **Talhões**            | Um por linha, com área, tipo de geometria e número do CAR                      | Talhão acima de 4 ha guardado como ponto                 |
| **Documentos**         | Tipo, versão, data de emissão, vigência, hash, e o nome original preservado    | Versão anterior apagada ao chegar a nova                 |
| **Aptidão**            | As **cinco camadas**, cada uma com o documento que a fechou e a força da prova | Camada 2 exigir matrícula em vez de aceitar a hierarquia |
| **Categorias**         | As **oito**, com veredito e **origem da prova** — documento ou checagem        | Mostrar cinco categorias, ou não distinguir a origem     |
| **Lacunas**            | Separadas por tipo: sanável, dispensa documentada, não sanável pelo produtor   | Contar dispensa de licença ambiental como lacuna         |
| **Última verificação** | Data e hora da execução mais recente das checagens                             | Ausente — sem data não há prova, só opinião              |

</div>

<div class="box stop">

O teste de linguagem, que vale por todos os outros

Leia qualquer texto da ficha em voz alta. Se em algum lugar estiver escrito *"Antônio está irregular"* em vez de *"falta o CCIR de Antônio"*, a tela reprova mesmo que o dado esteja certo. **O estado é do documento, nunca da pessoa** — e é isso que impede o produto de transformar a Cláudia em fiscal dos cooperados.

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">03</span>

## Dossiê do lote — as oito seções

</div>

Um PDF por lote, regenerado a cada mudança, com número de versão — e sempre com um HTML gêmeo salvo junto, para a demo sobreviver se o PDF falhar.

<div class="tablewrap">

| \#  | Seção                       | Conteúdo mínimo                                                                                                                                                        | Reprova se                                                                                                          |
|-----|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| 1   | **Identificação do lote**   | ID, commodity, código NC, quantidade em kg, safra, exportador, comprador, data prevista de embarque, **versão e data de geração**                                      | Sem número de versão — é o que prova que o dossiê é vivo                                                            |
| 2   | **Sumário de conformidade** | Veredito primeiro, contagem depois. Separado nas duas provas: **livre de desmatamento** e **requisitos de legalidade**, com talhões conformes, em exceção e bloqueados | Misturar as duas provas num semáforo só, ou dar número antes de veredito                                            |
| 3   | **Cadeia de custódia**      | Produtor → talhão → nota fiscal → ponto de recepção → lote → contêiner. Uma linha por elo, **com o documento que sustenta cada um**                                    | Elo sem documento, ou intermediário (CFOP 5102/6102) escondido em vez de marcado                                    |
| 4   | **Geolocalização**          | Coordenadas por talhão com **6 casas decimais**; polígono acima de 4 ha, ponto abaixo. Mapa com as camadas checadas                                                    | Menos de 6 casas decimais em qualquer coordenada                                                                    |
| 5   | **Laudo por checagem**      | O que foi comparado, **contra qual base**, **em que data**, o resultado e a conclusão escrita. Uma entrada por checagem, com categoria e severidade                    | **Laudo sem data.** A data é o que dá validade ao recorte — sem ela o dossiê não é evidência                        |
| 6   | **Anexos indexados**        | Tipo, origem, data de coleta, validade e **hash SHA-256** de cada arquivo                                                                                              | Sem hash — é o que transforma uma pasta de PDFs em prova auditável                                                  |
| 7   | **Trilha de auditoria**     | Quem ou o quê alterou o quê e quando, distinguindo **sistema de humano**, com o diff entre versões                                                                     | Não distinguir ator sistema de ator humano                                                                          |
| 8   | **Selo de aprovação**       | Nome, cargo e carimbo temporal de quem aprovou                                                                                                                         | Dossiê sair aprovado sozinho. **Sem selo humano ele é rascunho** — a responsabilidade legal é do cliente, não nossa |

</div>

<div class="box">

A pergunta que a banca pode fazer sobre o formato

Por que dossiê por **lote** e não painel por fornecedor? Porque é o que a cadeia usa: a DDS é emitida por lote e enviada ao cliente na entrega. E nenhuma plataforma gratuita produz esse artefato — o Parque Cafeeiro emite declaração **por imóvel**, com validade de 180 dias. **Lote é a unidade do comércio; imóvel é a unidade do cadastro.**

</div>

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">04</span>

## Fila de exceções e trilha de eventos

</div>

### Fila de exceções <span class="tag">a tela da manhã</span>

<div class="tablewrap">

| Tem que ter                                                                            | Reprova se                                                         |
|----------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Uma linha por exceção, com o que aconteceu, quando, e **quais lotes dependem daquilo** | Não mostrar os lotes afetados — é a informação que faz ela decidir |
| Ordenada por severidade: **bloqueio antes de flag**                                    | Ordenar por data ou alfabeticamente                                |
| Uma ação humana explícita por linha                                                    | Virar painel de métricas. **Não é painel — é decisão**             |
| Só `lacuna_sanavel` conta no número de lacunas                                         | Somar dispensas e pendências de CAR no contador                    |

</div>

### Trilha de eventos <span class="tag">a prova de autonomia</span>

- **Toda** ação escreve em `evento`, com `ator` igual a `'sistema'` ou `'humano'`. Nenhuma linha é apagada, nunca.
- A tela mostra um **contador de ações executadas pelo sistema** — é o número que sustenta a palavra "autopilot" no palco. Sem ele, é adjetivo.
- O diff entre versões do dossiê sai daqui, e é o que faz a v2 significar alguma coisa.

</div>

<div class="section">

<div class="sec-head">

<span class="sec-num">05</span>

## Os seis testes de conferência

</div>

Rodem estes antes do ensaio. Cada um leva menos de dois minutos e cada um pega uma classe inteira de erro.

1.  **Procure uma data em cada laudo.** Abra o PDF, vá na seção 5 e confira que toda entrada tem a data da consulta. Laudo sem data não é evidência — é opinião com aparência de relatório. É o erro mais comum e o mais fatal.
2.  **Conte as categorias.** Tem que haver **oito**, não cinco. Se alguma sumiu, a montagem está iterando sobre documentos em vez de categorias.
3.  **Ache uma categoria fechada por checagem, não por documento.** Direitos humanos ou consulta às comunidades. Se as duas aparecerem como lacuna permanente, a correção do conjunto mínimo não foi implementada — e essas categorias não vão fechar nunca.
4.  **Injete o embargo e cronometre.** Rode `demo/injetar_embargo.py` e confira: o talhão é marcado, os lotes que dependem dele são identificados, e sai **v2 com diff**, sem ninguém tocar em nada. Se precisar de um clique, não é autopilot.
5.  **Mude um byte de um anexo.** O dossiê tem que acusar divergência de hash. Se não acusar, o hash está sendo gravado mas não conferido — e a seção 6 vira decoração.
6.  **Leia a tela em voz alta procurando culpa.** Qualquer frase que responsabilize o produtor em vez do documento reprova, mesmo com o dado certo.

<div class="box stop">

O teste que resume todos

Peguem **um produtor que tenha só posse, sem matrícula e sem licença ambiental** — que é o caso da maioria da base real. Se o sistema aprovar esse produtor, com a prova de cada uma das oito categorias e a data de cada consulta, o MVP está de pé. **Se reprovar, a gente construiu a barreira que diz estar removendo** — e aí não importa o resto.

</div>

</div>

</div>
