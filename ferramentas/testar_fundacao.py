# -*- coding: utf-8 -*-
"""Testa a entrega da Trilha 0 contra o contrato do SPEC.md.

Nao e teste de unidade: e a checagem de que a fundacao que as outras quatro
trilhas vao consumir esta de pe. Roda depois de seed.py.

    python ferramentas/testar_fundacao.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import geopandas as gpd  # noqa: E402
import yaml  # noqa: E402
from shapely import wkt as shapely_wkt  # noqa: E402

import db  # noqa: E402
import geo  # noqa: E402

falhas = []
avisos = []


def checar(condicao, descricao, detalhe=""):
    marca = "OK  " if condicao else "FALHA"
    print("  [%s] %s%s" % (marca, descricao,
                           ("  -> " + detalhe) if detalhe else ""))
    if not condicao:
        falhas.append(descricao)
    return condicao


def main() -> int:
    print("=" * 72)
    print(" TESTES DA FUNDACAO - Trilha 0")
    print("=" * 72)

    # --- esquema ------------------------------------------------------------
    print("\n1. Esquema do banco (SPEC.md 2.2)")
    tabelas = {r["name"] for r in db.consultar(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for t in db.COLUNAS:
        checar(t in tabelas, "tabela '%s' existe" % t)
    for tabela, esperadas in db.COLUNAS.items():
        reais = [r["name"] for r in db.consultar(
            "PRAGMA table_info(%s)" % tabela)]
        checar(reais == esperadas, "colunas de '%s' na ordem do contrato"
               % tabela, "" if reais == esperadas else str(reais))

    # --- contagens ----------------------------------------------------------
    print("\n2. Contagens da base semeada (SPEC.md 8)")
    n_prod = db.contar("produtor")
    n_talh = db.contar("talhao")
    n_lote = db.contar("lote")
    checar(n_prod == 60, "60 produtores", str(n_prod))
    checar(80 <= n_talh <= 180, "1 a 3 talhoes por produtor", str(n_talh))
    checar(n_lote == 3, "3 lotes de embarque", str(n_lote))

    slugs = [p["slug"] for p in db.listar_produtores()]
    checar(len(set(slugs)) == 60, "slugs unicos")
    checar(all(s == s.lower() and s.isascii() for s in slugs),
           "slug sem acento e minusculo")

    talhoes = db.listar_talhoes()
    checar(all(2.0 <= t["area_ha"] <= 10.0 for t in talhoes),
           "area de todo talhao entre 2 e 10 ha")
    tipos = {t["tipo_geom"] for t in talhoes}
    checar(tipos == {"ponto", "poligono"}, "mistura de ponto e poligono",
           str(sorted(tipos)))

    # --- lotes --------------------------------------------------------------
    print("\n3. Lotes e sobreposicao (SPEC.md 8)")
    lotes = db.listar_lotes()
    checar(any(l["codigo"] == "CAC-2026-114" for l in lotes),
           "existe o lote CAC-2026-114 do roteiro")
    for l in lotes:
        n = len(db.produtores_do_lote(l["id"]))
        checar(10 <= n <= 40, "lote %s com 10 a 40 produtores" % l["codigo"],
               str(n))

    tres = db.consultar(
        "SELECT p.nome, p.slug, COUNT(DISTINCT lt.lote_id) AS q "
        "FROM lote_talhao lt JOIN talhao t ON t.id = lt.talhao_id "
        "JOIN produtor p ON p.id = t.produtor_id "
        "GROUP BY p.id HAVING q >= 3")
    checar(len(tres) >= 1, "pelo menos um produtor nos TRES lotes",
           ", ".join(x["nome"] for x in tres))

    # --- geometria contra a base real do Ibama ------------------------------
    print("\n4. Conflitos geograficos plantados (SPEC.md 8)")
    embargos = geo.carregar_embargos(incluir_injetados=False)
    checar(len(embargos) > 0, "camada de embargos carregada",
           "%d poligonos, fonte=%s"
           % (len(embargos), embargos["fonte_camada"].iloc[0]))
    if embargos["fonte_camada"].iloc[0] == "SEMEADO":
        avisos.append("A camada de embargo em uso e SEMEADA, nao real.")

    gtal = gpd.GeoDataFrame(
        talhoes, geometry=[shapely_wkt.loads(t["geom_wkt"]) for t in talhoes],
        crs=geo.CRS_PADRAO)
    gtal_m = geo.em_metros(gtal)
    emb_m = geo.em_metros(embargos)
    uniao = emb_m.geometry.union_all()

    sobre = gtal_m[gtal_m.geometry.intersects(uniao)]
    checar(len(sobre) >= 4, "pelo menos 4 talhoes SOBRE embargo real",
           "%d" % len(sobre))

    fora = gtal_m[~gtal_m.geometry.intersects(uniao)].copy()
    fora["dist_m"] = fora.geometry.distance(uniao)
    perto = fora[fora["dist_m"] < 500.0]
    checar(len(perto) >= 3, "pelo menos 3 talhoes a menos de 500 m da borda",
           "%d (distancias: %s)"
           % (len(perto), ", ".join("%.0f m" % d
                                    for d in sorted(perto["dist_m"])[:6])))

    # --- ficha da semente ---------------------------------------------------
    print("\n5. Ficha da semente e params")
    ficha = json.loads((RAIZ / "dados" / "semente.json").read_text("utf-8"))
    checar(len(ficha["talhoes_sobre_embargo"]) == 4,
           "ficha declara os 4 talhoes sobrepostos")
    checar(len(ficha["talhoes_limitrofes_500m"]) == 3,
           "ficha declara os 3 talhoes limitrofes")
    arm = ficha["armadilhas_documentais"]
    for chave in ("ilegivel", "vencido", "cpf_divergente", "duplicado",
                  "nao_documento"):
        checar(chave in arm, "armadilha '%s' plantada" % chave,
               arm.get(chave, {}).get("produtor", ""))
    produtores_armadilha = [v.get("produtor") for v in arm.values()]
    checar(len(set(produtores_armadilha)) == len(produtores_armadilha),
           "cada armadilha em um produtor DIFERENTE")

    params = yaml.safe_load(
        (RAIZ / "params" / "cacau.yml").read_text("utf-8"))
    checar(params["produtividade_kg_ha"]["PA"] == 900, "produtividade PA 900")
    checar(params["produtividade_kg_ha"]["BA"] == 270, "produtividade BA 270")
    checar(params["produtividade_kg_ha"]["limiar_excecao"] == 1.5,
           "limiar de excecao 1.5")
    checar(params["produtividade_kg_ha"]["limiar_bloqueio"] == 3.0,
           "limiar de bloqueio 3.0")
    checar(len(params["tipos"]) >= 30, "catalogo com todos os tipos",
           "%d tipos" % len(params["tipos"]))
    checar(all("palavras_chave" in v and "validade_dias" in v
               for v in params["tipos"].values()),
           "todo tipo tem palavras_chave e validade_dias")
    checar("conjunto_minimo" in params, "conjunto minimo definido")

    # --- arquivos de entrada -----------------------------------------------
    print("\n6. Arquivos crus em dados/entrada/")
    pastas = list((RAIZ / "dados" / "entrada").iterdir())
    checar(len(pastas) == 60, "uma pasta por produtor", str(len(pastas)))
    contagens = {p.name: len(list(p.iterdir())) for p in pastas}
    fora_faixa = {k: v for k, v in contagens.items() if not 5 <= v <= 12}
    checar(not fora_faixa, "5 a 10 arquivos por produtor (ate 12 com as "
           "armadilhas extras)", str(fora_faixa))

    # --- trilha de auditoria ------------------------------------------------
    print("\n7. Trilha de auditoria")
    checar(db.contar("evento") >= 2, "eventos registrados pelo seed",
           str(db.contar("evento")))
    contadores = db.contadores_autonomia()
    checar(set(contadores) == {"verificacoes_executadas",
                               "documentos_processados", "dossies_regerados",
                               "excecoes_para_humano"},
           "contadores de autonomia disponiveis para a interface")

    print("\n" + "=" * 72)
    for a in avisos:
        print(" AVISO: %s" % a)
    if falhas:
        print(" %d FALHA(S):" % len(falhas))
        for f in falhas:
            print("   - %s" % f)
        print("=" * 72)
        return 1
    print(" TUDO CERTO. A fundacao esta de pe.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
