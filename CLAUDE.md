# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é

Sistema de conformidade EUDR para cacau (Transamazônica, PA). Documentos de uma cooperativa entram agrupados por produtor, são classificados e padronizados; talhões são cruzados contra bases públicas brasileiras; sai um dossiê de conformidade em PDF por lote de embarque, mantido sob vigilância contínua (embargo novo reabre e regenera dossiês sozinho).

## Precedência de documentação

Em conflito, esta é a ordem (o mais à esquerda ganha):

`docs/correcoes-spec_1.md` > `docs/contrato.md` (v2) > `SPEC.md` / `PRD.md` / `ADR.md` / `ARD.md` > `docs/duas-pernas.md` (desatualizado; só o enquadramento conceitual vale).

O contrato de dados (esquema, pastas, quem-escreve-onde) é **congelado** — mudança de esquema só via `db.py`, anunciada, nunca por um módulo isolado.

## Ambiente (crítico — não é opcional)

- Python 3.12 em `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (pode não estar no PATH; `demo/roteiro.sh` resolve sozinho).
- **DLLs bloqueadas por política do Windows**: `pyogrio`, `fiona` e **`pyarrow` não carregam**. Consequências:
  - geopandas não lê/escreve SHP/GPKG/GeoJSON → todo acesso geoespacial passa por `geo.py` (camadas em CSV com coluna `geom_wkt` → GeoDataFrame). Nunca chame `gpd.read_file`.
  - **Nunca instale pyarrow** (quebra o import do pandas). Por isso `app.py` não usa `st.dataframe`/`st.table` — tabelas são HTML.
- Streamlit 1.62: `st.iframe` não aceita `srcdoc`/`scrolling` como kwargs — `app.py` escolhe o motor de embed por introspecção de assinatura (`_motor_de_embutir`). Não "simplifique" isso.
- Todo `open()` com `encoding='utf-8'`; console Windows é cp1252 — CLIs forçam stdout UTF-8.
- A pasta é sincronizada pelo OneDrive (locks/latência possíveis em arquivos).

## Comandos

```bash
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"

bash demo/roteiro.sh              # teste de aceitação completo (re-seeda o banco!)
"$PY" seed.py                     # recria banco + dados semeados (semente fixa 20260830)
"$PY" ingestao.py --todos         # ingere os 60 produtores
"$PY" ingestao.py --validar-nomes # valida nomenclatura dos padronizados (exit 1 se inválido)
"$PY" verificacao.py --tudo       # roda as 7 checagens nos ~110 talhões + aptidão
"$PY" dossie.py --lote CAC-2026-114   # gera dossiê (HTML sempre; PDF via playwright)
"$PY" vigilancia.py --uma-vez     # um ciclo de vigilância (--intervalo N para laço)
streamlit run app.py              # interface (3 telas)

# Demo ao vivo (3 terminais): vigilancia.py | streamlit run app.py | demo/injetar_embargo.py
"$PY" demo/injetar_embargo.py --limpar   # reverte a injeção (a demo DEVE começar limpa)
```

Smoke da UI sem browser: `streamlit.testing.v1.AppTest` sobre `app.py`. Estado saudável pré-demo: 3 lotes em `atencao` (nunca `bloqueado` — se estiver, ver PRE-MORTEM.md).

## Arquitetura — o que não se descobre lendo um arquivo só

**Particionamento por tabela de escrita** (a fronteira entre módulos é o banco, não imports):

| Módulo | Escreve | Observação |
|---|---|---|
| `seed.py` (+ `db.py`) | cria tudo; `produtor`, `talhao`, `lote`, `lote_talhao` | só a Fundação altera esquema |
| `ingestao.py` | `documento` | |
| `verificacao.py` | `checagem`, `excecao`, `aptidao` | |
| `dossie.py` | `dossie` | nunca recalcula — fotografa o estado corrente |
| `vigilancia.py` / `app.py` | `lote.status` via `recalcular_status_lotes`; `app.py` atualiza `excecao` como ator **humano** | regeração sempre via `dossie.gerar_dossie` importado |

Todos gravam em `evento` (append-only — **nunca** apagar linha; alimenta o contador de autonomia, o bloco 7 do dossiê e o diff). Toda escrita passa por funções de `db.py`; funções públicas trocam dicts simples; datas ISO 8601 texto (`db.agora()`); IDs `uuid4().hex[:12]` (`db.novo_id()`).

**Duas pernas do EUDR** orientam tudo: perna A = livre de desmatamento (checagem 01); perna B = legalidade em 8 categorias a–h (checagens 02–07). Cada `checagem` carrega `perna`, `categoria` e `severidade` ('B' bloqueia aptidão / 'F' flag). `checagem.codigo` mistura agregados `'01'..'07'` e códigos de regra `'R01'..'R50'` — `recalcular_status_lotes` soma **só os agregados** (senão conta em dobro). Severidade B **não** derruba lote — derruba camada de `aptidao`; quem derruba lote são as checagens 01/02/04.

**Aptidão** é hierarquia de 5 camadas com alternativas por força probatória (`aptidao.forca`), não checklist — reprovar quem não tem matrícula é o anti-padrão que o produto existe para evitar.

**`excecao.tipo`** tem vocabulário fixo validado em `db.py`: `bloqueio` | `lacuna_sanavel` | `dispensa_documentada` | `nao_sanavel_pelo_produtor`. Contagem de "lacunas" em qualquer tela/dossiê soma **só** `lacuna_sanavel`.

**Laudos**: todo `checagem.texto` sai de `montar_laudo()` com 5 itens obrigatórios (o quê, contra qual base, **data da consulta**, resultado, conclusão). Base semeada é declarada como "FONTE SEMEADA" no próprio laudo (ADR-012: nunca simular dado como real). Base real única: embargos do Ibama (procedência em `dados/bases/R01_procedencia.json`); alertas, TI/UC/quilombo e Lista Suja são semeados, sempre sobre talhões **fora** dos lotes (senão a virada de cor da demo morre).

**Dossiê**: HTML gravado sempre, PDF em seguida (playwright/chromium) — HTML é o plano B de palco. Versionamento por `vN.estado.json` ao lado dos arquivos (o diff compara contra ele, não contra o banco). Aprovação gera versão nova sem marca d'água.

**`params/cacau.yml`** é o que torna a commodity trocável: tipos de documento + palavras-chave, produtividade, validades, conjunto mínimo. YAML incompleto **falha alto** (`validar_params()`) — nunca degrade isso para default silencioso. O bloco `r39_produtividade_maxima` está `ativa: false` de propósito (parâmetro não levantado; regra de ouro nº 8: número não levantado não vira parâmetro).

**Microcópia invariante** (docs/correcoes-spec_1.md §06): o sistema *marca, ordena e informa* — nunca "bloqueia/cancela/barra" na prosa; a lacuna é do documento, nunca da pessoa ("falta o CCIR de Antônio", jamais "Antônio está irregular"); perna A e perna B não se compensam.

## Antes de apresentar

Leia `PRE-MORTEM.md`: modos de falha com plano B de palco, checklist T-60 e os 3 comandos de recuperação.
