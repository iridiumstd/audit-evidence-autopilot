# PRE-MORTEM — Evidence Autopilot EUDR

**Premissa do exercício.** É amanhã, 15h. A apresentação acabou de falhar na frente da banca.
Ninguém precisa descobrir o motivo depois: os motivos plausíveis estão todos abaixo, escritos
antes. Cada linha tem sinal precoce, o que fazer **hoje** e o que fazer **ao vivo em menos de
30 segundos**.

Este é documento de guerra. Não descreve o produto, descreve como ele morre.

Escala de probabilidade: **alta** = já aconteceu pelo menos uma vez nesta máquina ·
**média** = condição existe e não está mitigada · **baixa** = precisa de coincidência.

---

## Regra de ouro do palco

Três frases que salvam qualquer situação, decoradas antes de subir:

1. **"Isso é exatamente o que o sistema deve fazer: falhar alto e dizer o quê."** — vale para
   qualquer erro que apareça em vermelho no terminal. A tese do produto é *nunca simular o dado*
   (PRD §8). Um erro visível é coerente com a tese; um número inventado seria a falha real.
2. **"Tenho o HTML."** — o PDF é opcional, o HTML é sempre salvo.
3. **"Isso está declarado no laudo."** — camadas semeadas, pendências P-01/P-02 e a procedência
   da base do Ibama estão documentadas, não escondidas.

Nunca dizer no palco: "estranho", "isso funcionava", "deixa eu tentar de novo" (mais de uma vez),
"não sei por quê".

---

## A · Ambiente e máquina

| Causa da falha | Prob. | Sinal precoce | Mitigação preventiva (HOJE) | Plano B no palco (<30s) |
|---|---|---|---|---|
| **Máquina hiberna / suspende e derruba o websocket do streamlit** — a tela congela ou vira "Connection error" no meio da fala | **alta** (já ocorreu em teste) | Ícone de "running" some; tela para de atualizar; timestamp do rodapé congela | Plano de energia em **Alto desempenho**, suspensão e hibernação em *Nunca*, desligar tela em *Nunca*; desativar suspensão no fechamento da tampa; manter o notebook **na tomada**; mover o mouse a cada bloco de fala | F5 na aba do navegador. O streamlit reconecta e o estado vem do SQLite, não da sessão. Falar por cima: "a fonte de verdade é o banco, a tela é só leitura" |
| **DLL bloqueada pela política do Windows (GDAL/pyogrio/fiona, pyarrow)** volta a aparecer — import quebra em `geo.py` ou em `pandas` | média | `OSError`/`ImportError` de DLL logo no primeiro import de qualquer script | **Não instalar nada** hoje. Não reinstalar pyarrow em hipótese alguma (quebra `import pandas` em todas as trilhas). Rodar `roteiro.sh --base` uma vez com o ambiente exatamente como vai estar amanhã | Não depurar no palco. Ir para o **caminho já executado**: dossiês e capturas já gerados (`saida/dossies/`, `tela1..tela3*.png`). "A camada geoespacial roda em CSV+WKT justamente porque o ambiente da cliente é hostil — está no ADR" |
| **Reboot pendente (McAfee desinstalado) muda o comportamento do ambiente** — algo que funcionava hoje deixa de funcionar amanhã, ou vice-versa | média | Qualquer diferença entre o comportamento de ontem e o de hoje | **Rebootar hoje**, e depois do reboot rodar o roteiro completo **inteiro**. Nunca rebootar entre o último ensaio e a apresentação | Se o ambiente mudou e algo quebra: caminho já executado (dossiês + capturas). Não tentar reinstalar nada |
| **MAX_PATH do Windows estoura** com nomes de arquivo >~190 chars em `dados/entrada/` — a ingestão explode | média (achado do red team, **sem conserto**) | `FileNotFoundError`/`OSError [Errno 2]` com caminho longuíssimo no log da Trilha A | Varrer `dados/entrada/` hoje e **renomear/remover** qualquer arquivo com nome absurdo. Não subir arquivo novo depois disso | Não rodar ingestão ao vivo. A demo ao vivo é vigilância→dossiê, que não depende de ingestão. "A ingestão já rodou; o que vamos ver é a reação" |
| **OneDrive trava o arquivo ou introduz latência** — `app.db` bloqueado, arquivo "sendo sincronizado", escrita falha | média | Ícone de nuvem girando; `database is locked`; salvamento de dossiê lento demais | **Pausar a sincronização do OneDrive** antes de começar (Pausar por 2 horas) e confirmar que o ícone está pausado. Não abrir `app.db` em nenhum visualizador | Se der `database is locked`: fechar o terceiro terminal, aguardar 2s, repetir a injeção. Uma vez só |
| **Rede do local cai ou é cativa** — telemetria do streamlit tenta rede, polui o console e atrasa o start | média | Linhas de telemetria/erro de rede no terminal do streamlit no boot | Criar `.streamlit/config.toml` com `gatherUsageStats = false`; **rodar tudo offline no ensaio** para provar que nada depende de rede | Ignorar e seguir — nada da demo depende de rede. Se perguntarem: "o sistema é local por decisão; a base externa é baixada e versionada, não consultada ao vivo" |
| **Projetor/resolução quebra o layout** — tabelas HTML do app cortadas ou ilegíveis | média | Só aparece ao plugar o projetor | Plugar o projetor **antes**, ajustar zoom do navegador (67–80%) e deixar salvo; testar o contraste do semáforo no projetor (cor lavada) | Ctrl+menos/mais. Se o semáforo não distingue no projetor, **ler os rótulos em voz alta** em vez de apontar a cor |
| **Terminal com encoding errado** — acentos viram lixo na saída da vigilância, que é metade da demo | baixa | `?` ou `Ã©` na primeira linha impressa | `PYTHONIOENCODING=utf-8` já exportado pelo roteiro; exportar também nos terminais manuais | Seguir. Ler o log em voz alta. Se estiver ilegível demais, usar `--sem-cor` e narrar pela tela do streamlit |

---

## B · Demo ao vivo e timing

| Causa da falha | Prob. | Sinal precoce | Mitigação preventiva (HOJE) | Plano B no palco (<30s) |
|---|---|---|---|---|
| **Os lotes já começam `bloqueado`** — a virada de cor, que é o clímax, simplesmente não acontece | **alta** (é o erro mais fácil de cometer: rodar a injeção "só para testar" e não reverter) | Tela 1 abre com vermelho antes de qualquer injeção | Estado inicial obrigatório: **todos os lotes em `atencao`, nunca `bloqueado`**. Rodar a reversão e **conferir a Tela 1 com os próprios olhos** como último passo antes de subir. Nunca rodar injeção "de teste" depois disso | Reverter ao vivo (~9,5s) enquanto fala: "vou devolver a base ao estado de ontem para vocês verem a reação acontecer". A reversão é ela mesma uma demonstração de reversibilidade — **transformar o erro no argumento** |
| **A injeção não produz reação visível** — vigilância não acorda, ou já tinha visto aquele polígono | média | Terminal 1 imprime o ciclo sem nenhuma linha de mudança | Antes de subir, `python vigilancia.py --reset-estado` e depois deixar o laço rodando; garantir que `dados/vigilancia_estado.json` está coerente com a base atual | Não mexer no estado no palco. Ir para a **Tela 3** e mostrar o **diff entre versões de dossiê** já existente: "aqui está o mesmo mecanismo, na versão que ele gerou às [hora]" |
| **Latência maior que o ensaio** — reação ~1s, 3 dossiês em ~9,6s viram 30s+ e o silêncio mata a sala | média | Primeira geração de dossiê do dia sempre é a mais lenta (chromium frio) | **Aquecer**: gerar um dossiê descartável antes da apresentação para o chromium já estar carregado. Ensaiar a fala que cobre os ~10 segundos | Falar por cima com conteúdo preparado: o que o sistema está fazendo agora — reverificar talhões, recalcular status, regerar dossiê versionado. **Nunca olhar para o terminal em silêncio** |
| **Popover do seletor de lote/versão fecha sozinho** ao coincidir com o auto-refresh de 5s | média (comportamento conhecido) | O popover pisca e fecha ao clicar | **Desligar o auto-refresh no toggle da sidebar** antes de entrar na Tela 3 | Desligar o toggle e reabrir o seletor. Uma tentativa. Se insistir, abrir o HTML do dossiê direto de `saida/dossies/` |
| **PDF via playwright/chromium falha** (chromium não abre, timeout) | média | Erro do playwright no terminal; PDF não aparece na pasta | Confirmar hoje que o chromium do playwright está instalado e que o último dossiê gerou PDF **e** HTML | "O HTML é salvo sempre — é o que o auditor lê de qualquer forma." Abrir o HTML. Está previsto no PRD §8, não é improviso |
| **Terminal errado / comando errado sob pressão** — digitar no terminal da vigilância e matar o laço | média | Ctrl+C acidental; o laço para de imprimir | Três terminais **rotulados** (título da janela: 1-VIGILANCIA, 2-STREAMLIT, 3-GATILHO); comandos já digitados e **não executados**, só apertar Enter | Se matou a vigilância: relançar sem `--reset-estado` e sem alarde. Ela retoma do estado salvo |
| **Dossiê de 121+ páginas** — o avaliador se perde e a demo vira scroll | média | Só aparece se alguém pedir para ver o dossiê inteiro | Deixar **abertas em abas separadas** as 3 páginas que importam: sumário por perna, a exceção do embargo, e a trilha de auditoria (bloco 7) | Não rolar. Ir direto para a aba do bloco 7: "121 páginas porque é evidência; o que vocês querem ver está aqui" |
| **Demo estoura o tempo** e não sobra minuto para a fila de exceções, que é a tela principal do produto | média | O ensaio não cabendo no tempo | Cronometrar hoje e cortar na ordem: mapa → Tela 1 → detalhe de regras F. **A fila de exceções nunca cai** | Pular direto para a Tela 2. É ela que carrega a tese, não o semáforo |

---

## C · Dados e bases externas

| Causa da falha | Prob. | Sinal precoce | Mitigação preventiva (HOJE) | Plano B no palco (<30s) |
|---|---|---|---|---|
| **CSVs do Ibama somem/ficam ilegíveis e a vigilância loga milhares de "poligono removido"** como se fossem revogações legítimas — o terminal fica alarmante na frente da banca | **alta** se alguém mexer em `dados/bases/` (achado do red team, **sem conserto**) | Ciclo da vigilância cospe centenas de linhas de remoção de uma vez | **Congelar `dados/bases/`**: nada é apagado, movido ou re-baixado hoje. Fazer **cópia de segurança da pasta** fora do OneDrive. Não rodar `ferramentas/baixar_ibama.py` amanhã | Ctrl+C no terminal 1, restaurar a pasta do backup, relançar. Falar: "a vigilância hoje não distingue base indisponível de embargo revogado — é o achado nº 1 do nosso próprio red team e está documentado; note que **a checagem 02 falha alto**, então nunca gera falso conforme" |
| **Link SHP oficial do Ibama continua 404** e alguém da banca testa | média | Já é fato conhecido | Ter `dados/bases/R01_procedencia.json` aberto em uma aba, com a data real de atualização (**2026-05-03**) | "O SHP oficial está fora do ar; usamos o CSV alternativo, com procedência versionada em `R01_procedencia.json` e data de consulta impressa em todo laudo (ADR-005). Nunca simulamos o dado" |
| **Planilha .xlsx ilegível sai com extensão `.pdf`** na pasta padronizada e alguém abre | média (achado do red team, **sem conserto**) | Arquivo `.pdf` que não abre em visualizador | Não abrir a pasta `dados/padronizado/` no palco | "O sniff é por conteúdo, não por extensão — o classificador acertou o tipo e errou o sufixo. Confunde humano, não confunde o sistema. Está na nossa lista de correções" |
| **YAML de parâmetros corrompido / sem `conjunto_minimo`** | baixa (**já corrigido**: agora falha alto, antes dava falso apto) | Erro explícito na carga de `params/cacau.yml` | Não editar `params/cacau.yml` hoje. Ter cópia | "Isso era uma quebra de red team: YAML incompleto dava falso apto. Corrigimos para falhar alto. Falso apto é o único erro inaceitável neste produto" |
| **Slug de produtor inexistente** passado a um script | baixa (**já corrigido**: dava traceback) | Mensagem de erro tratada | Usar apenas os slugs do roteiro | Mostrar como argumento de robustez — é uma correção de red team, não um bug vivo |
| **Camadas semeadas (TI/UC/quilombo, Lista Suja) confundidas com base real** pela banca | média | Pergunta direta da banca | Ter a declaração do laudo pronta e localizada | Ver seção D, pergunta "cadê a Lista Suja real?" |

---

## D · Produto e credibilidade perante a banca

A demo pode rodar perfeita e a apresentação ainda falhar aqui. Estas são as perguntas que
derrubam, com a resposta pronta. Responder **em uma frase, sem defensiva, e devolver ao ponto forte**.

| Causa da falha | Prob. | Sinal precoce | Mitigação preventiva (HOJE) | Plano B no palco (<30s) |
|---|---|---|---|---|
| **"Isso não é só um wrapper de shapefile / de mapa?"** | **alta** | Banca focada demais no mapa e no polígono | Abrir com a perna B, não com o mapa. O mapa é o primeiro item da ordem de corte por um motivo | "O mapa é a perna A — e ela já vem de graça de Whisp/FAO, GFW, Parque Cafeeiro, Cacaupará. Construímos a perna A no mínimo defensável e **todo o resto do esforço está na perna B**: legalidade documental, oito categorias, R01–R50. É onde não há concorrente. Nosso diferencial não é ver o polígono, é comparar o CPF do CAR com o CPF da nota fiscal" |
| **"Cadê a Lista Suja real? E as camadas de TI/UC/quilombo?"** | **alta** | Pergunta inevitável de jurado que conhece o regulamento | Deixar a declaração de camadas semeadas visível no laudo, não escondida em nota de rodapé | "São **semeadas, e declaradas como tal no próprio laudo**. A arquitetura é a mesma: a checagem 07 cruza por CPF de todos os elos, a 04 cruza por polígono. Trocar a semente pela base oficial é substituir um arquivo em `dados/bases/`. O que estamos provando aqui é o mecanismo — e preferimos declarar a semente a fingir cobertura e ser desmentidos" |
| **"Quem assina a DDS? Vocês estão emitindo declaração de conformidade?"** | **alta** | Pergunta de risco jurídico, sempre vem | Alinhar a microcopia: o sistema **marca, ordena e informa; nunca bloqueia, cancela ou barra** | "Ninguém do sistema assina. **Quem assina é a gestora**, e é decisão dela por design (`correcoes-spec_1.md` §06). O produto entrega evidência datada e versionada para que a assinatura seja defensável — `bloqueado` existe só como valor técnico de semáforo, nunca como ato" |
| **"Vocês cobrem as oito categorias?"** — resposta errada aqui destrói a credibilidade inteira | **alta** | Tentação de dizer "sim" | Decorar a frase de posicionamento do ADR-002 | "**Quatro das oito automatizadas contra base pública brasileira; as outras quatro viram trilha documental organizada, datada e indexada dentro do dossiê.** Nenhum concorrente cobre as oito. Fingir cobertura total é ser desmentido por quem lê o regulamento" |
| **"E a produtividade kg/ha? Esses volumes fecham?"** (P-01 não levantada, R39 desligada) | média | Jurado com background agronômico | Saber de cor que R39 está **desligada e declarada** | "A R39 está desligada porque a produtividade de referência da Transamazônica ainda não foi levantada — é a pendência P-01, declarada. Preferimos regra desligada a regra com número inventado. A checagem 06 continua fechando volume contra NF, chave duplicada, NCM e CFOP" |
| **"Vocês validaram com Parque Cafeeiro / Cacaupará?"** (P-02 não inspecionados) | média | Pergunta de benchmark competitivo | Ter a resposta pronta, sem improviso | "Ainda não inspecionamos — é a pendência P-02. Mas o posicionamento não depende disso: ambos jogam na perna A, que é onde decidimos **não** competir" |
| **"Como sei que o sistema fez isso sozinho e não vocês na mão?"** | média | Ceticismo sobre autonomia | Contador de autonomia no topo de todas as telas, lido direto de `evento` (append-only) | "A tabela `evento` é append-only e distingue ator `sistema` de `humano`. O contador no topo lê dela. O bloco 7 do dossiê é a trilha de auditoria completa — dá para conferir linha a linha quem fez o quê e quando" |
| **"E se a base mudar depois que o dossiê foi emitido?"** | média | É exatamente a demo — mas só funciona se ela rodar | A demo já responde. Se a demo falhou, responder com o diff de versões | "Todo laudo carrega a data da consulta (ADR-005). Se a data importa, o dossiê envelhece; se envelhece, precisa se regenerar — por isso existe a vigilância. Aqui está o diff entre a v01 e a v02 do mesmo lote" |
| **Excesso de jargão interno** (trilhas, R39, camada 2, perna B) numa banca que não leu nada | média | Olhares vazios, ninguém pergunta nada | Ensaiar a versão sem sigla: "duas provas", "documento que comprova o direito de usar a terra" | Reformular na hora com um exemplo concreto: "falta o CCIR do Antônio" em vez de "lacuna sanável na camada 2" |

---

## Checklist de 1 hora antes — executável, na ordem

Não pular passo. Não improvisar ordem.

**T-60 · Ambiente**
1. Reboot já feito? Se não, **não rebootar mais**.
2. Notebook na tomada. Plano de energia → Alto desempenho. Suspender: Nunca. Hibernar: Nunca. Tela: Nunca. Tampa: não faz nada.
3. **Pausar sincronização do OneDrive** (2 horas). Confirmar o ícone pausado.
4. Fechar tudo que não é a demo: Teams, Slack, atualizações, outros navegadores.
5. Notificações do Windows → **Assistente de Foco / Não perturbe ligado**.
6. Confirmar `.streamlit/config.toml` com `gatherUsageStats = false`.

**T-50 · Dados congelados**
7. Copiar `dados/bases/` para um backup **fora do OneDrive** (ex.: `C:\demo-backup\bases\`).
8. Copiar `dados/app.db` para o mesmo backup.
9. **Não** rodar `ferramentas/baixar_ibama.py`. Não editar `params/cacau.yml`. Não subir arquivo novo em `dados/entrada/`.
10. Varrer `dados/entrada/` procurando nome de arquivo longo demais (>~190 chars) — remover se houver.

**T-45 · Roteiro completo, uma vez**
11. `bash demo/roteiro.sh` — completo. Ler o total de falhas. **Esperado: 0.**
12. Se falhar algum passo, **não improvisar correção**: restaurar do backup e repetir uma vez. Se falhar de novo, a demo do dia é o caminho já executado (dossiês + capturas).

**T-30 · Estado inicial da demo**
13. `python vigilancia.py --reset-estado --uma-vez` (fotografa a base, não reage).
14. **Reverter a injeção do embargo.** Confirmar que os 3 lotes estão em `atencao` — **nunca** `bloqueado`.
15. Gerar um dossiê descartável para **aquecer o chromium** do playwright. Confirmar que saiu PDF **e** HTML.

**T-20 · Palco**
16. Plugar o projetor. Ajustar resolução e zoom do navegador (67–80%). Conferir o semáforo no projetor.
17. Abrir os **três terminais rotulados**: `1-VIGILANCIA`, `2-STREAMLIT`, `3-GATILHO`.
18. Terminal 1: `python vigilancia.py` — deixar rodando e imprimindo ciclos limpos.
19. Terminal 2: `streamlit run app.py`. Abrir no navegador. **Desligar o toggle de auto-refresh na sidebar.**
20. Terminal 3: digitar `python demo/injetar_embargo.py` e **não apertar Enter**.

**T-10 · Abas e conferência final**
21. Abas abertas e na ordem: Tela 1 (lotes) · Tela 2 (fila de exceções) · Tela 3 (dossiê) · dossiê HTML no bloco 7 · `dados/bases/R01_procedencia.json`.
22. **Olhar a Tela 1 com os próprios olhos.** Todos em `atencao`. Se algum estiver `bloqueado`, reverter agora.
23. Ler em voz alta as três frases da "Regra de ouro do palco".
24. A partir daqui: **não tocar em mais nada.** Mover o mouse a cada 2 minutos para a máquina não dormir.

---

## Os 3 comandos de recuperação rápida

Decorados. Escritos em papel. Executados sem hesitar e sem explicar antes.

**1 · Reverter o estado da demo** (~9,5s) — para quando os lotes já estão bloqueados, ou depois de qualquer teste acidental.
```
python demo/injetar_embargo.py --limpar
```
> Fala de cobertura: *"Vou devolver a base ao estado de ontem para vocês verem a reação acontecer ao vivo."*

**2 · Ressincronizar a vigilância com a base** — para quando a vigilância não reage, ou está cuspindo remoções em massa.
```
python vigilancia.py --reset-estado --uma-vez
```
> Fala de cobertura: *"Estou pedindo para ele refotografar a base — o primeiro ciclo em estado limpo só observa, não reage."*
> Se o problema foi base sumida: antes disso, restaurar `dados/bases/` do backup.

**3 · Regerar o dossiê de um lote na mão** (~3s/lote) — para quando a tela não mostra a versão nova.
```
python dossie.py --lote CAC-2026-114
```
> Fala de cobertura: *"O dossiê é sempre regerado a partir do banco, nunca editado — por isso posso pedir de novo sem risco."*
> O HTML sai sempre, mesmo que o PDF falhe: `saida/dossies/CAC-2026-114/`.

**Fallback absoluto**, se os três falharem: fechar o navegador, abrir as capturas
`tela1-lotes.png`, `tela2-excecoes-final.png`, `tela3-dossie-aprovado.png` e o dossiê HTML já
gerado. Narrar por cima. Uma demo gravada apresentada com segurança vence uma demo ao vivo
apresentada com pânico.
