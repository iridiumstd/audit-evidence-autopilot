# -*- coding: utf-8 -*-
"""demo/injetar_embargo.py - o gatilho da apresentacao ao vivo.

Adiciona um poligono de embargo NOVO cobrindo justamente o talhao do produtor
que esta nos TRES lotes. A Trilha D (vigilancia.py) rele dados/bases/ a cada
ciclo, ve um poligono que ainda nao tinha visto, reverifica os talhoes
afetados, recalcula o status dos lotes e regera os tres dossies.

O poligono injetado e escrito em dados/bases/embargos_injetados.csv, camada
separada da base real. geo.carregar_embargos() junta as duas e marca cada
linha com `fonte_camada`, para o laudo poder declarar que aquele poligono veio
da injecao de demonstracao e nao do Ibama (ADR-012: dado fabricado sai
declarado, nunca disfarcado de real).

Uso:
    python demo/injetar_embargo.py            # injeta
    python demo/injetar_embargo.py --limpar   # remove a injecao
"""
import sys
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
from shapely import wkt as shapely_wkt  # noqa: E402

import db  # noqa: E402
import geo  # noqa: E402


def talhao_alvo() -> dict:
    """O maior talhao do produtor que aparece nos tres lotes.

    Nao le a ficha semente.json de proposito: consulta o banco, para que o
    script continue certo mesmo se a semente mudar.
    """
    linhas = db.consultar(
        "SELECT t.*, p.nome AS produtor_nome, p.slug AS produtor_slug, "
        "       COUNT(DISTINCT lt.lote_id) AS qtd_lotes "
        "FROM talhao t "
        "JOIN produtor p ON p.id = t.produtor_id "
        "JOIN lote_talhao lt ON lt.talhao_id = t.id "
        "GROUP BY t.id "
        "HAVING qtd_lotes >= 3 "
        "ORDER BY t.area_ha DESC LIMIT 1")
    if not linhas:
        raise SystemExit(
            "Nenhum talhao em tres lotes. Rode 'python seed.py' antes.")
    return linhas[0]


def limpar() -> int:
    """Remove a camada injetada, para reiniciar a demo."""
    if geo.ARQUIVO_INJETADOS.exists():
        geo.ARQUIVO_INJETADOS.unlink()
        print("[INJECAO] camada de embargos injetados removida")
        db.registrar_evento("humano", "embargo_injetado_removido", "base",
                            None, "demo/injetar_embargo.py --limpar")
    else:
        print("[INJECAO] nada a remover")
    return 0


def main() -> int:
    if "--limpar" in sys.argv:
        return limpar()

    alvo = talhao_alvo()
    lotes = db.lotes_do_talhao(alvo["id"])

    print("=" * 72)
    print(" INJECAO DE EMBARGO - demonstracao ao vivo")
    print("=" * 72)
    print(" produtor : %s" % alvo["produtor_nome"])
    print(" talhao   : %s  (%.2f ha, %s)"
          % (alvo["nome"], alvo["area_ha"], alvo["tipo_geom"]))
    print(" lotes afetados (%d): %s"
          % (len(lotes), ", ".join(l["codigo"] for l in lotes)))

    # Poligono do embargo: envolve o talhao inteiro com folga de ~150 m,
    # para a intersecao ser inequivoca e a area de intersecao ser a do talhao.
    geom_talhao = shapely_wkt.loads(alvo["geom_wkt"])
    poligono = geom_talhao.buffer(geo_folga := 150.0 / 111_320.0)
    if geom_talhao.geom_type == "Point":
        # talhao pontual: raio equivalente a area declarada, mais a folga
        raio = ((alvo["area_ha"] * 10_000 / 3.14159) ** 0.5) / 111_320.0
        poligono = geom_talhao.buffer(raio + geo_folga)

    hoje = date.today()
    num_tad = "DEMO-%s" % hoje.strftime("%Y%m%d")
    area_ha = round(alvo["area_ha"] + 3.5, 2)

    registro = {
        "SEQ_TAD": "999999",
        "NUM_TAD": num_tad,
        "DAT_EMBARGO": hoje.isoformat(),
        "NOME_EMBARGADO": alvo["produtor_nome"],
        "CPF_CNPJ_EMBARGADO": "",
        "MUNICIPIO": "",
        "UF": "PA",
        "QTD_AREA_EMBARGADA": str(area_ha),
        "DES_TAD": ("Embargo injetado para demonstracao ao vivo do Evidence "
                    "Autopilot. NAO E DADO DO IBAMA."),
        "TIPO_AREA": "DEMONSTRACAO",
        "SIT_DESEMBARGO": "NAO",
        "ULTIMA_ATUALIZACAO_RELATORIO": datetime.now().replace(
            microsecond=0).isoformat(),
        "origem_geometria": "injetado sobre o talhao %s" % alvo["id"],
        "talhao_alvo_id": alvo["id"],
    }
    gdf = gpd.GeoDataFrame([registro], geometry=[poligono], crs=geo.CRS_PADRAO)
    if geo.ARQUIVO_INJETADOS.exists():
        antigo = geo.ler_csv_wkt(geo.ARQUIVO_INJETADOS)
        antigo = antigo[antigo["NUM_TAD"] != num_tad]
        gdf = gpd.GeoDataFrame(
            pd.concat([antigo.drop(columns=["fonte_camada"], errors="ignore"),
                       gdf], ignore_index=True),
            geometry="geometry", crs=geo.CRS_PADRAO)
    geo.gravar_csv_wkt(gdf, geo.ARQUIVO_INJETADOS)

    db.registrar_evento(
        "humano", "embargo_injetado", "talhao", alvo["id"],
        "Termo %s (%.2f ha) injetado sobre o talhao %s de %s. "
        "Lotes potencialmente afetados: %s"
        % (num_tad, area_ha, alvo["nome"], alvo["produtor_nome"],
           ", ".join(l["codigo"] for l in lotes)))

    print("\n [OK] termo %s gravado em dados/bases/%s"
          % (num_tad, geo.ARQUIVO_INJETADOS.name))
    print(" A vigilancia deve reagir no proximo ciclo (5 s na demo).")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
