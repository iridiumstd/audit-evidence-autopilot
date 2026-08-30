# Evidence Autopilot EUDR — fundação (Trilha 0)

Documentos que mandam, em ordem de precedência: `docs/correcoes-spec_1.md` e
`docs/contrato.md` (v2 — ganham de todo o resto em caso de conflito), depois
`PRD.md` (por quê), `SPEC.md` (contrato de dados e como), `ADR.md` (decisões
travadas), `ARD.md` (recursos externos), `TAXONOMIA.md` (tipos de documento),
`ordem-de-construcao.md` (as cinco trilhas) e `docs/duas-pernas.md`
(enquadramento conceitual das duas provas; desatualizado nas regras).

Este README explica só uma coisa: **quem escreve onde**.

---

## Quem escreve onde — regra absoluta

| Trilha | Arquivo dela | Escreve em | Lê |
|---|---|---|---|
| **0 · Fundação** | `db.py`, `geo.py`, `seed.py`, `params/cacau.yml`, `ferramentas/`, `demo/` | cria tudo; popula `produtor`, `talhao`, `lote`, `lote_talhao`; escreve `dados/bases/` e `dados/entrada/` | — |
| **A · Ingestão** | `ingestao.py` | `documento`, `dados/padronizado/` | `produtor`, `talhao`, `params/cacau.yml`, `dados/entrada/` |
| **B · Verificação** | `verificacao.py` | `checagem`, `excecao` | `talhao`, `documento`, `dados/bases/` |
| **C · Dossiê** | `dossie.py` | `dossie`, `saida/dossies/` | tudo |
| **D · Vigilância** | `vigilancia.py` | `lote.status`; reabre dossiê chamando a Trilha C | tudo |
| **Interface** | `app.py` | nada além de resolver exceção | tudo |

Três regras que não se negociam:

1. **Nenhuma trilha edita o `.py` de outra trilha.** `db.py` e `geo.py` são
   compartilhados e só a Trilha 0 os altera, avisando no grupo.
2. **Toda escrita no banco passa por uma função de `db.py`.** Ninguém abre
   `sqlite3` na mão.
3. **Toda trilha chama `db.registrar_evento(...)` a cada ação.** Nunca apague
   linha de `evento` — é a trilha de auditoria que prova autonomia no palco.

```python
import db
db.registrar_evento("sistema", "checagem_executada", "talhao", talhao_id,
                    "Checagem 02 contra embargos do Ibama: bloqueio")
```

---

## Estrutura de pastas (contrato — `SPEC.md` §2.1)

```text
dados/app.db                        banco SQLite, fonte única de verdade
dados/entrada/<produtor_slug>/      arquivos crus, como o usuário sobe
dados/padronizado/<produtor_slug>/  arquivos renomeados pelo sistema
dados/bases/                        bases externas (Ibama, alertas)
dados/semente.json                  ficha do que a semente plantou (conflitos)
params/cacau.yml                    parâmetros da commodity
docs/contrato.md                    contrato de construção v2
docs/correcoes-spec_1.md            correções de spec (precedência máxima)
docs/duas-pernas.md                 enquadramento das duas provas
saida/dossies/<lote_codigo>/vN.pdf
saida/dossies/<lote_codigo>/vN.html
app.py                              interface streamlit          (Interface)
ingestao.py                                                      (Trilha A)
verificacao.py                                                   (Trilha B)
dossie.py                                                        (Trilha C)
vigilancia.py                                                    (Trilha D)
db.py                               acesso ao banco              (Trilha 0)
geo.py                              acesso às camadas geo        (Trilha 0)
seed.py                             base semeada                 (Trilha 0)
demo/injetar_embargo.py             gatilho da demo ao vivo      (Trilha 0)
demo/roteiro.sh                     teste de aceitação           (Trilha 0)
ferramentas/baixar_ibama.py         recurso R-01, download real  (Trilha 0)
ferramentas/semear_embargo_fallback.py  camada SEMEADA de emergência
ferramentas/testar_fundacao.py      testes do contrato           (Trilha 0)
```

---

## Como começar (qualquer trilha)

```bash
pip install geopandas shapely pyyaml fpdf2 requests pandas openpyxl pillow
python ferramentas/baixar_ibama.py      # base real do Ibama, recortada
python seed.py                          # 60 produtores, talhões, 3 lotes, arquivos
python ferramentas/testar_fundacao.py   # confere o contrato

bash demo/roteiro.sh --base             # os três acima, de uma vez
bash demo/roteiro.sh                    # o roteiro completo do SPEC.md §10
```

`seed.py` **apaga e recria** `dados/app.db` e `dados/entrada/`. Rode antes de
começar, não no meio do trabalho de outra pessoa.

---

## API de `db.py`

Tudo recebe e devolve **dicts simples**. IDs são `uuid4().hex[:12]`. Datas são
ISO 8601 em texto.

```python
db.criar_esquema()
db.inserir_documento({...}) -> dict          # também: _produtor _talhao _lote
                                             # _lote_talhao _checagem _excecao _dossie
db.buscar_talhao(id) -> dict
db.buscar_produtor_por_slug(slug) -> dict
db.buscar_lote_por_codigo("CAC-2026-114") -> dict
db.listar_talhoes(produtor_id=None) -> list[dict]
db.listar_excecoes(status="aberta") -> list[dict]
db.atualizar("lote", lote_id, {"status": "bloqueado"}) -> dict
db.talhoes_do_lote(lote_id) -> list[dict]
db.lotes_do_talhao(talhao_id) -> list[dict]   # é o que faz 1 embargo derrubar 3 lotes
db.produtores_do_lote(lote_id) -> list[dict]
db.proxima_versao_dossie(lote_id) -> int
db.contadores_autonomia() -> dict             # os 4 números do topo da interface
db.consultar(sql, params) -> list[dict]       # leitura livre
```

---

## API de `geo.py`

**Por que existe:** esta máquina bloqueia as DLLs do GDAL por política de
Controle de Aplicativo do Windows. `pyogrio` e `fiona` não carregam, então
geopandas **não lê nem escreve SHP, GPKG ou GeoJSON aqui**. As camadas ficam em
CSV com coluna `geom_wkt`, que `pandas` + `shapely` leem sem GDAL. Ninguém
precisa saber disso: chame `geo.carregar_embargos()` e receba um GeoDataFrame.

```python
import geo
emb = geo.carregar_embargos()          # base real + polígonos injetados na demo
emb_m = geo.em_metros(emb)             # EPSG:31982, para medir metros e hectares
geo.ler_csv_wkt(caminho)               # qualquer camada em CSV+WKT
geo.gravar_csv_wkt(gdf, caminho)
```

Cada linha traz `fonte_camada`: `ibama_real`, `injetado_demo` ou `SEMEADO`.
**O laudo tem de declarar a fonte** (`ADR-012`): dado semeado sai declarado,
nunca disfarçado de real.

---

## Base do Ibama (recurso R-01)

O SHP-ZIP anunciado no portal de dados abertos está **morto (HTTP 404)**. Os
mesmos termos de embargo estão publicados em CSV no mesmo dataset, com
geometria, e esses respondem — é a origem usada. Procedência completa,
incluindo hashes e o registro do link morto, em
`dados/bases/R01_procedencia.json`.

Se um dia o download inteiro falhar, `ferramentas/baixar_ibama.py` grava o erro
literal em `dados/bases/R01_FALHA.txt` e sai com código 1 — **não simula dado**.
Só então `ferramentas/semear_embargo_fallback.py` cria uma camada fabricada,
com sufixo `_semeado` no nome do arquivo e `TIPO_AREA='SEMEADO'` em cada linha.

---

## `dados/semente.json`

A ficha do que a semente plantou: contagens, o produtor que está nos três
lotes, os talhões sobre embargo, os limítrofes e as cinco armadilhas
documentais com o produtor de cada uma. As Trilhas A e B usam para conferir se
o que era para disparar disparou.
