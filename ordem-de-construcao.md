# Ordem de Construção

> Evidence Autopilot EUDR · Pacote de construção · ATON

Contrato de dados fixo, quatro trilhas paralelas, um prompt pronto por trilha.
Escrito para você distribuir agora e não precisar mediar integração depois.

---

## 00 · Como usar isto, em três minutos

O que mata construção paralela em hackathon não é falta de gente — é deriva de
contrato. Duas pessoas inventam nomes de campo diferentes e às sete da noite nada
conversa. Por isso o esquema está fixado aqui, e é idêntico em todos os prompts.

**Passo 1 — Alguém roda a Trilha 0.**
Sozinha, primeiro, antes de qualquer outra. Cria o repositório, o banco, o esquema
e os dados semeados. Leva cerca de duas horas. **Nada mais começa antes de ela
terminar** — mas os outros já podem ler o prompt deles.

**Passo 2 — As trilhas A a D em paralelo.**
Uma pessoa por trilha, cada uma numa sessão própria, cada uma com seu prompt.
Todas escrevem no mesmo banco, em tabelas diferentes. Ninguém edita arquivo de outro.

**Passo 3 — Três pontos de junção.**
Fim da hora 3, da hora 6 e da hora 9. Em cada um, uma pessoa roda o comando de
verificação da seção 05 e diz em voz alta o que passou.

**Se o time tiver menos de quatro pessoas:** junte C com D (dossiê e vigilância são
o mesmo perfil) e depois A com B. Com duas pessoas fica A+B numa e C+D na outra.
Com uma pessoa, a ordem é 0, B, C, A, D — e a interface morre primeiro.

---

## 01 · Decisões técnicas já tomadas

Não abram nenhuma dessas para discussão. Toda hora gasta escolhendo biblioteca é
hora que não vira demo.

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.11+ | É onde estão geopandas, OCR e o ferramental de PDF. |
| Banco | SQLite, arquivo único em `dados/app.db` | Zero configuração, o arquivo inteiro cabe no git, e todo mundo abre com o mesmo caminho. |
| Geoespacial | geopandas + shapely | O `sjoin` resolve as checagens de sobreposição em uma linha. |
| Leitura de documento | pdfplumber para PDF, pytesseract para imagem | Instalam sem drama. Se o tesseract travar em alguém, essa pessoa usa só PDF e segue. |
| Dossiê | Template HTML → PDF com playwright | O template é HTML: fácil de iterar, bonito de graça. E se o PDF quebrar na hora da demo, mostra o HTML — a demo sobrevive. |
| Interface | streamlit | Três telas em duas horas, sem front-end. |
| Agendamento | Um script `vigilancia.py` rodado em laço, não cron | Em demo, cron é risco. Laço com sleep é visível e controlável. |

**Regra de ouro para os vibecoders:** ninguém instala biblioteca nova sem avisar no
grupo. Se faltar algo, a primeira pergunta é "dá para fazer com o que já tem?".
Em quase todos os casos dá.

---

## 02 · O contrato de dados

Este bloco é idêntico dentro de todos os prompts. É a única coisa que ninguém pode
alterar sozinho — mudança aqui é decisão de PM, anunciada no grupo.

```text
ESTRUTURA DE PASTAS (fixa)

  dados/app.db                      banco SQLite, fonte única de verdade
  dados/entrada/<produtor_slug>/    arquivos crus, como o usuário sobe
  dados/padronizado/<produtor_slug>/ arquivos renomeados pelo sistema
  dados/bases/                      shapefiles do Ibama e alertas
  params/cacau.yml                  parâmetros da commodity
  saida/dossies/<lote_codigo>/vN.pdf
  saida/dossies/<lote_codigo>/vN.html
  app.py                            interface streamlit
  ingestao.py  verificacao.py  dossie.py  vigilancia.py

ESQUEMA DO BANCO (fixo — não renomeie campo nenhum)

  produtor(id TEXT PK, nome, cpf, municipio, uf, cooperativa, slug)

  talhao(id TEXT PK, produtor_id, nome, area_ha REAL,
         geom_wkt TEXT, tipo_geom TEXT,        -- 'ponto' | 'poligono'
         car_numero TEXT, car_situacao TEXT)

  documento(id TEXT PK, produtor_id, talhao_id NULL,
            arquivo_origem TEXT, arquivo_padronizado TEXT,
            tipo TEXT,                          -- ver params/cacau.yml
            campos_json TEXT,                   -- campos extraidos
            data_emissao TEXT, data_validade TEXT,
            hash_sha256 TEXT, confianca REAL,   -- 0.0 a 1.0
            status TEXT)                        -- 'ok'|'ilegivel'|'vencido'|'divergente'

  lote(id TEXT PK, codigo TEXT, commodity, safra,
       quantidade_kg REAL, comprador, data_embarque TEXT,
       status TEXT)                             -- 'verde'|'atencao'|'bloqueado'

  lote_talhao(lote_id, talhao_id, quantidade_kg REAL)

  checagem(id TEXT PK, talhao_id, codigo TEXT,  -- '01'..'06'
           perna TEXT,                          -- 'A' | 'B'
           resultado TEXT,                      -- 'conforme'|'excecao'|'bloqueio'
           texto TEXT, fonte TEXT, data_execucao TEXT,
           evidencia_json TEXT)

  excecao(id TEXT PK, tipo TEXT, talhao_id NULL, documento_id NULL,
          lotes_afetados TEXT,                  -- ids separados por virgula
          descricao TEXT, status TEXT,          -- 'aberta'|'resolvida'
          resolvido_por TEXT, resolvido_em TEXT)

  dossie(id TEXT PK, lote_id, versao INTEGER, gerado_em TEXT,
         status TEXT,                           -- 'rascunho'|'aprovado'
         aprovado_por TEXT, hash_sha256 TEXT,
         caminho_pdf TEXT, caminho_html TEXT, diff TEXT)

  evento(id TEXT PK, timestamp TEXT, ator TEXT, -- 'sistema' | 'humano'
         acao TEXT, entidade TEXT, entidade_id TEXT, detalhe TEXT)

QUEM ESCREVE ONDE — regra absoluta, evita conflito

  Trilha 0  cria tudo, popula produtor, talhao, lote, lote_talhao
  Trilha A  escreve documento; le produtor, talhao
  Trilha B  escreve checagem, excecao; le talhao, documento
  Trilha C  escreve dossie; le tudo; nao escreve em mais nada
  Trilha D  atualiza lote.status e reabre dossie chamando a Trilha C

  TODAS as trilhas escrevem em evento a cada acao. Nunca apague linha
  de evento: a trilha de auditoria e' o que prova autonomia no palco.

REGRAS DE OURO

  - Nenhuma trilha edita arquivo .py de outra trilha.
  - Toda funcao publica recebe e devolve dicts simples, nunca objetos.
  - Toda escrita no banco passa por funcoes de db.py (Trilha 0 cria).
  - Datas sempre em ISO 8601, texto: '2026-08-30T14:22:00'.
  - IDs sempre string, gerados com uuid4().hex[:12].
```

---

## 03 · As cinco trilhas

| Trilha | Entrega | Depende de | Horas |
|---|---|---|---|
| **0 · Fundação** | Repo, banco, esquema, dados semeados, parâmetros da commodity | — | 2 |
| **A · Ingestão** | Lê grupo de arquivos, classifica, extrai, padroniza, grava `documento` | Trilha 0 | 4–5 |
| **B · Verificação** | As seis checagens sobre talhão, gera `checagem` e `excecao` | Trilha 0 | 5–6 |
| **C · Dossiê** | Template HTML, versionamento, hash, PDF | Trilha 0 (pode simular B) | 4–5 |
| **D · Vigilância e telas** | Laço que reabre dossiês, três telas, contador de autonomia | B e C, no fim | 4–5 |

**A trilha B é a mais crítica e a mais difícil.** Coloque nela a pessoa mais forte
tecnicamente. Se B atrasar, a demo não tem conflito para mostrar e o pitch perde o
momento de 3:15. Se qualquer outra atrasar, dá para contornar.

### TRILHA 0 · Fundação — *primeiro, sozinha*

Sem isso, quatro pessoas inventam quatro esquemas. Duas horas aqui economizam a
noite inteira.

Cole como primeira mensagem:

```text
Você vai construir a fundação de um projeto de hackathon. Outras quatro pessoas
vão programar em cima do que você entregar nas próximas duas horas, em sessões
separadas. Sua entrega é o contrato que impede todas elas de colidirem.

O PRODUTO: "Evidence Autopilot EUDR". Uma cooperativa de cacau da Transamazônica
sobe os documentos que já tem, agrupados por produtor e com nomes fora de padrão.
O sistema identifica o tipo de cada arquivo, extrai campos, padroniza, cruza os
talhões contra bases públicas brasileiras e gera um dossiê de conformidade em PDF
por lote de embarque — mantido sob vigilância contínua, de modo que um embargo
novo reabre e regenera os dossiês afetados sozinho.

STACK JÁ DECIDIDA — não questione: Python 3.11+, SQLite em dados/app.db,
geopandas + shapely, pdfplumber e pytesseract, template HTML renderizado a PDF
com playwright, interface em streamlit.

[COLE AQUI O BLOCO "CONTRATO DE DADOS" DA SEÇÃO 02]

SUA MISSÃO, nesta ordem:

1. Crie a estrutura de pastas exata do contrato e um README curto que explique
   quem escreve onde.

2. Escreva db.py com: criação do esquema exatamente como no contrato; funções
   simples de inserir e consultar cada tabela, sempre recebendo e devolvendo
   dicts; e uma função registrar_evento(ator, acao, entidade, entidade_id,
   detalhe) que TODAS as trilhas vão chamar.

3. Baixe os termos de embargo do Ibama, que são shapefile de polígonos com
   download direto e sem autenticação, em
   https://dadosabertos.ibama.gov.br/dataset/termos-de-embargo
   Abra, me diga a data real de atualização, quais são os campos e quantos
   polígonos existem no Pará. Recorte a região da Transamazônica (Medicilândia,
   Altamira, Uruará, Brasil Novo) e salve em dados/bases/. Se o download falhar,
   diga exatamente o que aconteceu — não simule o dado.

4. Gere a base semeada com semente fixa, em seed.py:
   - 60 produtores com nomes brasileiros plausíveis, CPF fictício de formato
     válido, municípios da região recortada, slug sem acento.
   - 1 a 3 talhões por produtor, área entre 2 e 10 hectares, mistura de ponto e
     polígono, todos dentro da região.
   - IMPORTANTE: posicione 4 talhões DE PROPÓSITO sobrepostos a polígonos de
     embargo reais, e outros 3 quase encostando na borda, para testar caso
     limítrofe.
   - 3 lotes de embarque, cada um com 10 a 40 produtores, COM SOBREPOSIÇÃO
     entre eles: pelo menos um produtor precisa estar nos três lotes ao mesmo
     tempo. A demonstração depende de um embargo derrubar três dossiês de uma vez.

5. Gere os grupos de arquivos em dados/entrada/<produtor_slug>/, de 5 a 10
   arquivos por produtor, com nomes ruins de verdade: IMG_4471.jpg,
   doc scan (3).pdf, planilha final v2.xlsx, documento sem titulo.pdf.
   Conteúdo consistente com os dados do produtor. Plante deliberadamente, em
   produtores diferentes: um arquivo ilegível, um documento vencido, um cujo CPF
   diverge do produtor do grupo, um duplicado com nome diferente, e um que não é
   documento nenhum (foto do cacau secando).

6. Escreva params/cacau.yml com:
   - a lista de tipos de documento esperados, com nome canônico e palavras-chave
     que ajudam a identificar cada um;
   - produtividade de referência em kg por hectare por região (Pará ≈ 900,
     Bahia ≈ 270), usada na checagem de coerência de volume;
   - regras de validade por tipo de documento em dias;
   - o conjunto mínimo de documentos que torna um produtor apto.
   Este arquivo é o que permite trocar de commodity sem tocar no código.

7. Escreva demo/injetar_embargo.py: um script que adiciona um polígono de
   embargo novo cobrindo justamente o talhão do produtor que está nos três
   lotes. É o que vamos rodar ao vivo na apresentação.

8. Faça um commit e me entregue: a estrutura criada, o que descobriu sobre a
   base do Ibama, quantos produtores e talhões existem, quais estão em conflito
   e por quê, e quais arquivos são as armadilhas plantadas.

REGRAS

Execute de verdade, não descreva o que faria. Se faltar biblioteca, instale.
Comente o código em português. Não implemente ingestão, verificação, dossiê nem
interface — são de outras pessoas. Sua entrega é fundação e dados, só.
```

### TRILHA A · Ingestão — *laço 01*

É a parte que o jurado vê nos primeiros noventa segundos da demo: lixo entra, ficha
padronizada sai.

Cole como primeira mensagem:

```text
Você vai construir o módulo de INGESTÃO de um projeto de hackathon. Outras
pessoas estão construindo verificação, dossiê e interface em paralelo, no mesmo
repositório. Você escreve APENAS ingestao.py e o que ele precisar.

O PRODUTO: "Evidence Autopilot EUDR". Uma cooperativa de cacau sobe os documentos
que já tem, agrupados por produtor e com nomes fora de padrão. O sistema
identifica o tipo de cada arquivo, extrai campos, padroniza, cruza talhões contra
bases públicas e gera um dossiê de conformidade por lote — sob vigilância
contínua.

STACK JÁ DECIDIDA — não questione: Python 3.11+, SQLite em dados/app.db,
pdfplumber para PDF, pytesseract para imagem. Se o tesseract não instalar na sua
máquina, trate imagem como "ilegível" e siga — não gaste tempo com isso.

[COLE AQUI O BLOCO "CONTRATO DE DADOS" DA SEÇÃO 02]

O CONTRATO DE ENTRADA DO PRODUTO — respeite a fronteira:
O usuário entrega arquivos JÁ AGRUPADOS POR PRODUTOR, numa pasta por produtor.
A atribuição a quem pertence vem do agrupamento, NÃO de adivinhação. Você nunca
precisa descobrir de quem é um arquivo solto. O que você faz é padronizar o que
veio dentro do grupo.

SUA MISSÃO — escreva ingestao.py com a função
processar_produtor(produtor_slug) -> dict, que:

1. Lê todos os arquivos de dados/entrada/<produtor_slug>/.

2. Para cada arquivo: calcula hash SHA-256; extrai o texto (pdfplumber para PDF,
   pytesseract para imagem, pandas para planilha); identifica o TIPO usando as
   palavras-chave de params/cacau.yml; extrai os campos que importam (número do
   documento, CPF/CNPJ do titular, nome, datas de emissão e validade, área,
   município); atribui uma confiança de 0 a 1.

3. Aplica as regras de status:
   - 'ilegivel'    texto extraído vazio ou confiança abaixo de 0.4
   - 'vencido'     data_validade anterior a hoje
   - 'divergente'  CPF ou nome no documento diferente do produtor do grupo
   - 'ok'          nenhum dos anteriores
   Quando o tipo não for reconhecido, grave tipo='desconhecido' e NÃO chute.

4. Copia o arquivo para dados/padronizado/<produtor_slug>/ com nomenclatura
   canônica: TIPO_SLUGPRODUTOR_AAAAMMDD_vN.ext

5. Grava uma linha em documento por arquivo, e chama registrar_evento a cada
   arquivo processado.

6. Devolve um dict com: quantos arquivos, quantos por status, e o MAPA DE
   LACUNAS — quais documentos do conjunto mínimo de params/cacau.yml estão
   faltando para esse produtor. O mapa de lacunas é entregável, não detalhe.

Escreva também processar_todos() que roda os 60 produtores e imprime um resumo.

CRITÉRIO DE PRONTO

Rodar processar_todos() em terminal limpo processa os 60 produtores, popula a
tabela documento, cria os arquivos padronizados, e o resumo mostra pelo menos um
ilegível, um vencido e um divergente — que são armadilhas plantadas de propósito
nos dados semeados. Imprima o progresso arquivo a arquivo: essa saída de terminal
vai ao vivo na apresentação, então faça-a legível e um pouco bonita.

REGRAS

Execute de verdade e teste com os dados que existem. Não edite db.py,
verificacao.py, dossie.py, vigilancia.py nem app.py — são de outras pessoas.
Toda escrita no banco passa pelas funções de db.py. Comente em português.
```

### TRILHA B · Verificação — *a mais crítica*

É o coração técnico e o que sustenta o diferencial: a checagem 05, de consistência
entre documentos, é a que nenhuma plataforma de coordenada consegue rodar.

Cole como primeira mensagem:

```text
Você vai construir o módulo de VERIFICAÇÃO de um projeto de hackathon — a peça
mais importante do produto. Outras pessoas fazem ingestão, dossiê e interface em
paralelo. Você escreve APENAS verificacao.py.

O PRODUTO: "Evidence Autopilot EUDR". Documentos de uma cooperativa de cacau são
padronizados, os talhões são cruzados contra bases públicas brasileiras, e um
dossiê de conformidade por lote de embarque é gerado e mantido sob vigilância.

O ENQUADRAMENTO QUE DEFINE SUA ARQUITETURA: o regulamento europeu tem DUAS
PERNAS cumulativas. Perna A é livre de desmatamento pós-31/12/2020, provada por
geometria e satélite — e essa perna virou commodity gratuita, várias plataformas
públicas já entregam. Perna B é LEGALIDADE na legislação do país produtor, em
oito categorias, e é feita de documento. Nosso diferencial está na perna B.
Portanto: cada checagem que você escrever precisa declarar a que perna pertence.

STACK JÁ DECIDIDA: Python 3.11+, SQLite em dados/app.db, geopandas + shapely.

[COLE AQUI O BLOCO "CONTRATO DE DADOS" DA SEÇÃO 02]

SUA MISSÃO — escreva verificacao.py com uma função por checagem, todas com a
mesma assinatura: checagem_NN(talhao_id) -> dict com resultado, texto, fonte,
evidencia. E verificar_talhao(talhao_id) que roda as seis e grava.

  01 · DESMATE PÓS-2020 — perna A
     Cruza a geometria do talhão com as camadas de alerta de desmatamento em
     dados/bases/. Resultado 'bloqueio' se houver interseção com alerta posterior
     a 31/12/2020.

  02 · EMBARGO DO IBAMA — perna B, categoria ambiental
     sjoin do talhão com os polígonos de embargo do Ibama. Interseção =
     'bloqueio'. Distância menor que 500 m = 'excecao' (caso limítrofe).
     Esta é a checagem que dispara ao vivo na demonstração. Capriche na
     evidência: guarde o número do termo de embargo e a área de interseção.

  03 · CAR E POSSE — perna B, uso da terra
     CAR ativo, geometria compatível com o talhão, e titular do CAR coerente com
     o produtor. Divergência de titular = 'excecao'.

  04 · SOBREPOSIÇÃO DE DIREITOS — perna B, direitos de terceiros
     Interseção com terra indígena, território quilombola ou unidade de
     conservação. Use camadas semeadas se as reais não estiverem disponíveis, e
     deixe claro no código qual é qual.

  05 · CONSISTÊNCIA DOCUMENTAL — perna B, transversal — ESTA É A JOIA
     Não é "o documento existe". É o cruzamento entre documentos do mesmo
     produtor. Implemente cada regra como função separada e numerada:
       R1 CPF do CAR diferente do CPF da nota fiscal
       R2 área declarada no talhão maior que a área do CAR
       R3 documento vencido na data prevista de embarque do lote
       R4 município da matrícula diferente do município do CAR
       R5 titular do contrato de arrendamento diferente do produtor do grupo
       R6 documento do conjunto mínimo ausente
       R7 dois documentos do mesmo tipo com números diferentes e datas próximas
     Cada regra violada vira uma exceção com descrição em português claro,
     dizendo qual documento conflita com qual. Adicione outras regras que
     conseguir imaginar — quanto mais, melhor, é aqui que está o diferencial.

  06 · COERÊNCIA DE VOLUME — perna B, tributário
     Volume entregue pelo produtor no lote comparado com área dos talhões vezes
     a produtividade de referência da região, lida de params/cacau.yml.
     Acima de 150% do esperado = 'excecao'. Acima de 300% = 'bloqueio'.
     Guarde na evidência os três números: área, produtividade e volume.

Escreva também verificar_tudo() que roda todos os talhões, e
recalcular_status_lotes() que define lote.status a partir do pior resultado
entre os talhões que o compõem: qualquer bloqueio deixa o lote 'bloqueado',
qualquer exceção deixa 'atencao', senão 'verde'.

CADA execução grava em checagem com data_execucao, e cria excecao quando o
resultado não for 'conforme'. Chame registrar_evento sempre.

CRITÉRIO DE PRONTO

verificar_tudo() roda os ~100 talhões em terminal limpo, grava as checagens, e o
resumo mostra os 4 talhões que os dados semeados plantaram sobre embargo real
aparecendo como 'bloqueio' na checagem 02, mais os casos limítrofes como
'excecao'. E pelo menos três regras diferentes da checagem 05 disparando.

REGRAS

Execute de verdade contra os dados que existem. Não edite arquivos de outras
trilhas. O texto de cada laudo precisa ser legível por humano e citar a base
consultada e a data — ele vai impresso no dossiê. Comente em português.
```

### TRILHA C · Dossiê — *laço 04*

É o entregável que o cliente compra e a imagem final da demo. Pode começar antes da
B ficar pronta, usando dados falsos no formato do contrato.

Cole como primeira mensagem:

```text
Você vai construir o gerador de DOSSIÊ de um projeto de hackathon. Outras pessoas
fazem ingestão, verificação e interface em paralelo. Você escreve APENAS dossie.py
e os templates dele.

O PRODUTO: "Evidence Autopilot EUDR". Documentos de uma cooperativa de cacau são
padronizados, os talhões cruzados contra bases públicas brasileiras, e o
resultado vira um dossiê de conformidade em PDF por lote de embarque — versionado
e regenerado sozinho quando o mundo muda.

STACK JÁ DECIDIDA: Python 3.11+, SQLite em dados/app.db, template HTML com
jinja2, renderizado a PDF com playwright. Salve SEMPRE o HTML junto com o PDF: se
o PDF falhar na apresentação, mostramos o HTML.

[COLE AQUI O BLOCO "CONTRATO DE DADOS" DA SEÇÃO 02]

SUA MISSÃO — escreva dossie.py com gerar_dossie(lote_id) -> dict, que lê o estado
CORRENTE e o congela numa versão nova. O dossiê nunca recalcula nada: ele fotografa
o que a verificação já apurou, com a data de cada checagem carimbada.

O PDF tem oito blocos, nesta ordem:

  1 IDENTIFICAÇÃO DO LOTE — código, commodity, safra, quantidade, comprador,
    data prevista de embarque, número da versão e data de geração.
  2 SUMÁRIO DE CONFORMIDADE — semáforo do lote SEPARADO POR PERNA: desmatamento
    de um lado, legalidade do outro, com contagem de talhões conformes, em
    exceção e bloqueados. É a primeira página que alguém lê.
  3 CADEIA DE CUSTÓDIA — produtor, talhão, nota fiscal, lote, contêiner: uma
    linha por elo, com o documento que sustenta cada um.
  4 GEOLOCALIZAÇÃO — tabela de coordenadas por talhão, com tipo (ponto ou
    polígono) e área. Se der tempo, um mapa simples.
  5 LAUDO POR CHECAGEM — para cada uma das seis: o que foi comparado, contra
    qual base, EM QUE DATA, o resultado e o texto da conclusão. A data é o que
    dá validade ao instantâneo.
  6 ANEXOS INDEXADOS — cada documento com tipo, origem, data de coleta,
    validade e hash SHA-256. O hash é o que transforma pasta de PDF em prova.
  7 TRILHA DE AUDITORIA — a partir da tabela evento: quem ou o quê fez o quê e
    quando, distinguindo 'sistema' de 'humano', e o diff em relação à versão
    anterior.
  8 SELO DE APROVAÇÃO — nome, cargo e carimbo temporal. Sem aprovação, o
    documento sai com marca d'água RASCUNHO bem visível.

VERSIONAMENTO: cada geração incrementa dossie.versao para aquele lote, salva em
saida/dossies/<codigo>/vN.pdf e vN.html, calcula o hash do PDF, e grava o campo
diff em português dizendo o que mudou desde a versão anterior — por exemplo
"talhão TAL-014 passou de conforme para bloqueio na checagem 02".

Faça também aprovar_dossie(dossie_id, nome, cargo), que gera uma versão nova com
status 'aprovado' e sem a marca d'água.

DESIGN: sóbrio e denso, de documento oficial e não de apresentação. Fonte serifada
para texto, monoespaçada para números e hashes. Cabeçalho e rodapé com código do
lote, versão e paginação em todas as páginas. Precisa parecer algo que um auditor
europeu receberia.

CRITÉRIO DE PRONTO

gerar_dossie() de um lote qualquer produz PDF e HTML completos, com os oito
blocos preenchidos. Se a tabela checagem ainda estiver vazia porque a outra
trilha não terminou, gere dados falsos NO FORMATO EXATO DO CONTRATO para
desenvolver, e apague-os antes de entregar.

REGRAS

Execute de verdade e abra o PDF para conferir. Não edite arquivos de outras
trilhas. Você só ESCREVE na tabela dossie. Comente em português.
```

### TRILHA D · Vigilância e telas — *fecha a demo*

É onde a autonomia fica visível. O momento de 3:15 da apresentação inteiro mora aqui.

Cole como primeira mensagem:

```text
Você vai construir a VIGILÂNCIA e a INTERFACE de um projeto de hackathon. Outras
pessoas fazem ingestão, verificação e dossiê em paralelo. Você escreve APENAS
vigilancia.py e app.py.

O PRODUTO: "Evidence Autopilot EUDR". Documentos de uma cooperativa de cacau são
padronizados, talhões cruzados contra bases públicas, e um dossiê de conformidade
por lote é gerado — e mantido vivo: quando um embargo novo atinge um talhão, os
dossiês afetados são reabertos e regenerados sozinhos.

O QUE VOCÊ CONSTRÓI É O CLÍMAX DA APRESENTAÇÃO. No minuto 3:15 da demo, alguém
injeta um embargo novo e, sem ninguém tocar em nada, um talhão é rebaixado, TRÊS
lotes caem para bloqueado, uma exceção entra na fila e três dossiês são
regenerados. Construa pensando nesse momento.

STACK JÁ DECIDIDA: Python 3.11+, SQLite em dados/app.db, streamlit para a
interface. Agendamento é um laço com sleep dentro de vigilancia.py, NÃO cron.

[COLE AQUI O BLOCO "CONTRATO DE DADOS" DA SEÇÃO 02]

PARTE 1 — vigilancia.py

Um laço que a cada N segundos (parametrizável, use 5 na demo):
  1. Relê as bases em dados/bases/ e detecta se há polígono de embargo ou alerta
     que ainda não foi visto.
  2. Para cada talhão afetado, chama verificacao.verificar_talhao(talhao_id) —
     a função é de outra trilha, importe e use, não reimplemente.
  3. Chama verificacao.recalcular_status_lotes().
  4. Para todo lote cujo status PIOROU, chama dossie.gerar_dossie(lote_id) —
     também de outra trilha.
  5. Cria a exceção correspondente e registra evento a cada passo.
  6. Imprime no terminal, de forma legível e um pouco dramática, cada coisa que
     fez. Essa saída aparece na tela durante a apresentação.

Enquanto as outras trilhas não entregarem, use funções falsas com a mesma
assinatura para poder desenvolver, e troque no ponto de junção.

PARTE 2 — app.py, três telas em streamlit

  TELA 1 · LOTES — lista com semáforo por lote, SEPARADO POR PERNA (desmatamento
  e legalidade em colunas distintas). Clicar num lote abre os talhões que o
  compõem e os dossiês gerados, com histórico de versões e link para o PDF.

  TELA 2 · FILA DE EXCEÇÕES — é a tela principal do produto, não um painel de
  status verde. Lista as exceções abertas, com tipo, o que foi encontrado, os
  lotes afetados, e a evidência. Cada uma tem dois botões: "excluir talhão do
  lote" e "marcar como resolvida", ambos gravando quem resolveu e quando, e
  disparando regeração do dossiê.

  TELA 3 · DOSSIÊ — visualiza o dossiê de um lote, com seletor de versão, o diff
  entre versões, e um botão de aprovar que pede nome e cargo.

  EM TODAS AS TELAS, no topo, o CONTADOR DE AUTONOMIA:
  "N verificações executadas · N documentos processados · N dossiês regerados ·
   N exceções para humano"
  Ele é lido direto da tabela evento e é a prova visual de autonomia. Faça-o
  grande e bonito — é o número que o jurado anota.

CRITÉRIO DE PRONTO

Com vigilancia.py rodando num terminal e o streamlit noutro, executar
demo/injetar_embargo.py faz o terminal reagir em segundos, três lotes mudarem de
status na interface sem recarregar manualmente, uma exceção aparecer na fila, e
três dossiês novos ficarem disponíveis. Ensaie isso até sair liso.

REGRAS

Execute de verdade. Não edite ingestao.py, verificacao.py nem dossie.py —
importe e use. Priorize a fila de exceções sobre as outras telas: se faltar
tempo, é a que precisa existir. Comente em português.
```

---

## 04 · Pontos de junção

Três paradas obrigatórias. Em cada uma, uma pessoa roda o comando, e o time responde
em voz alta: passou ou não passou.

| Quando | O que tem que estar verdadeiro | Se não estiver |
|---|---|---|
| Fim da hora 3 | Trilha 0 entregue: banco criado, 60 produtores, ~100 talhões, 3 lotes com sobreposição, grupos de arquivos gerados, base do Ibama recortada. As outras quatro trilhas já rodam contra o banco real. | Todo mundo para e ajuda a Trilha 0. Nada mais importa até isso existir. |
| Fim da hora 6 | A grava checagens e exceções; B popula a tabela `documento`; C gera um PDF com dados reais de pelo menos um lote. | Corte a checagem 04 e reduza a 05 a três regras. Não corte a 02 nem a 06. |
| Fim da hora 9 | O cenário completo roda: injetar embargo derruba três lotes e regenera três dossiês, sem ninguém tocar em nada. | Grave o vídeo do que funciona e apresente com ele. Não tente consertar de madrugada. |

**O teste de aceitação, um comando.** Deixe isto num arquivo `demo/roteiro.sh` desde
a primeira hora, mesmo quebrado. Ele é a definição de pronto do projeto inteiro:

```bash
python seed.py
python ingestao.py --todos
python verificacao.py --tudo
python dossie.py --lote CAC-2026-114
python demo/injetar_embargo.py
# vigilancia.py reage e regenera tres dossies
```

---

## 05 · O que você, como PM, controla

**Só você muda o contrato.**
Se alguém pedir para renomear um campo, a resposta padrão é não. Se for inevitável,
você anuncia no grupo, e quem depende daquele campo confirma que viu. Uma mudança de
esquema não anunciada custa duas horas de integração.

**A ordem de corte é sua.**
Nesta ordem, do primeiro a cair para o último: mapa no dossiê, checagem 04, telas 1 e 3,
regras extras da 05, checagem 03. **Nunca caem:** checagem 02, checagem 06, fila de
exceções, vigilância, dossiê em PDF.

**Alguém ensaia enquanto os outros constroem.**
A partir da hora 6, uma pessoa deixa de programar e passa a ensaiar a apresentação com
o que existe. É contraintuitivo e é o que separa demo boa de demo travada.

**A saída de terminal é entregável.**
Metade da demonstração é terminal, não interface. Peça explicitamente a cada trilha que
a saída impressa seja legível e caprichada — está nos prompts, mas cobre.

**Duas coisas de vinte minutos que valem mais que duas horas de código, e que só você
pode destravar:** alguém abrir o Parque Cafeeiro e o Cacaupará para ver o que eles
realmente emitem, e alguém confirmar uma faixa defensável de produtividade em quilos
por hectare para a Transamazônica, que a checagem 06 precisa. Distribua as duas agora,
para quem não está numa trilha.
