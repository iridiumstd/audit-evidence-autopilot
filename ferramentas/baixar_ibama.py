# -*- coding: utf-8 -*-
"""Recurso R-01 do ARD.md - Termos de embargo do Ibama. DADO REAL.

Protocolo de descoberta (ARD.md secao 2), passos 1 a 6.

Passo 1 - Localizar
  A ficha R-01 aponta para o dataset CKAN
  https://dadosabertos.ibama.gov.br/dataset/termos-de-embargo
  cujo recurso SHP-ZIP anunciado
  (pamgia.ibama.gov.br/geoservicos/arquivos/adm_embargo_ibama_a.shp.zip)
  responde HTTP 404 - link morto no portal. Registrado em R01_procedencia.json.
  O mesmo dataset publica os termos em CSV, com geometria, e esses respondem.
  Sao a origem usada aqui. Dado real do Ibama, nao semeado.

Passo 2 - Baixar (download direto, sem autenticacao)
  termo_embargo.csv  - uma linha por termo, com MUNICIPIO, UF, NUM_TAD,
                       QTD_AREA_EMBARGADA e GEOM_AREA_EMBARGADA
  coordenadas.csv    - vertices por poligono de cada termo

Passo 5 - Recortar: Medicilandia, Altamira, Uruara, Brasil Novo (PA)
Passo 6 - Versionar: arquivo com data no nome, mais um atalho estavel.

Se o download falhar, este script registra o erro literal e sai com codigo 1.
NAO simula dado. A camada semeada de emergencia vive em
ferramentas/semear_embargo_fallback.py e sai com sufixo _semeado.
"""
import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
BASES = RAIZ / "dados" / "bases"
BASES.mkdir(parents=True, exist_ok=True)

PAGINA = "https://dadosabertos.ibama.gov.br/dataset/termos-de-embargo"
URL_SHP_MORTA = ("https://pamgia.ibama.gov.br/geoservicos/arquivos/"
                 "adm_embargo_ibama_a.shp.zip")
URL_TERMOS = ("https://dadosabertos.ibama.gov.br/dados/SIFISC/termo_embargo/"
              "termo_embargo/termo_embargo.csv")
URL_COORD = ("https://dadosabertos.ibama.gov.br/dados/SIFISC/termo_embargo/"
             "coordenadas/coordenadas.csv")

MUNICIPIOS = {"MEDICILANDIA", "ALTAMIRA", "URUARA", "BRASIL NOVO"}


def sem_acento(valor) -> str:
    """Maiusculo, sem acento, sem espaco nas pontas."""
    s = str(valor or "").upper().strip()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def num(valor):
    """Converte texto numerico brasileiro (virgula decimal) em float."""
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def baixar(url: str, destino: Path) -> dict:
    """Baixa um arquivo em pedacos e devolve dict de procedencia."""
    print("[R-01] baixando " + url)
    resp = requests.get(url, timeout=1800, stream=True,
                        headers={"User-Agent": "EvidenceAutopilot/0.1"})
    resp.raise_for_status()
    ultima_mod = resp.headers.get("Last-Modified")
    total = 0
    with open(destino, "wb") as fh:
        for pedaco in resp.iter_content(chunk_size=1024 * 512):
            fh.write(pedaco)
            total += len(pedaco)
    sha = hashlib.sha256(destino.read_bytes()).hexdigest()
    print("[R-01]   %s: %.1f MB  Last-Modified=%s  sha256=%s..."
          % (destino.name, total / 1024 / 1024, ultima_mod, sha[:16]))
    return {"url": url, "arquivo": destino.name, "bytes": total,
            "sha256": sha, "last_modified_http": ultima_mod}


def main() -> int:
    import pandas as pd
    import geopandas as gpd
    from shapely import wkt as shapely_wkt
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    proc = {
        "recurso": "R-01 termos de embargo Ibama",
        "pagina_dataset": PAGINA,
        "shp_zip_anunciado": URL_SHP_MORTA,
        "shp_zip_estado": "HTTP 404 - link morto no portal em 2026-08-30",
        "baixado_em": datetime.now(timezone.utc).isoformat(),
        "origem_real": True,
        "arquivos": [],
    }

    bruto = BASES / "bruto"
    bruto.mkdir(exist_ok=True)
    csv_termos = bruto / "termo_embargo.csv"
    csv_coord = bruto / "coordenadas.csv"

    try:
        for url, dest in ((URL_TERMOS, csv_termos), (URL_COORD, csv_coord)):
            if dest.exists() and dest.stat().st_size > 100_000:
                print("[R-01] %s ja existe, reaproveitando" % dest.name)
                proc["arquivos"].append({
                    "url": url, "arquivo": dest.name,
                    "bytes": dest.stat().st_size,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                })
            else:
                proc["arquivos"].append(baixar(url, dest))
    except Exception as erro:  # noqa: BLE001 - o erro literal e o entregavel
        msg = "%s: %s" % (type(erro).__name__, erro)
        (BASES / "R01_FALHA.txt").write_text(
            "FALHA no download de R-01 (termos de embargo do Ibama)\n"
            "quando: %s\nerro literal: %s\n"
            % (datetime.now(timezone.utc).isoformat(), msg), encoding="utf-8")
        print("[R-01] FALHA: " + msg, file=sys.stderr)
        return 1

    # ------------------ passo 3 - inspecionar ------------------
    df = pd.read_csv(csv_termos, sep=";", dtype=str, encoding="utf-8",
                     low_memory=False, on_bad_lines="skip")
    campos = list(df.columns)
    print("\n[R-01] INSPECAO")
    print("[R-01] total de termos de embargo no Brasil: %d" % len(df))
    print("[R-01] campos (%d): %s" % (len(campos), campos))

    col_data = next((c for c in campos if "ULTIMA_ATUALIZACAO" in c), None)
    data_base = str(df[col_data].dropna().max()) if col_data else None
    print("[R-01] data real de atualizacao da base (%s): %s"
          % (col_data, data_base))

    df["_UF"] = df["UF"].map(sem_acento)
    df["_MUN"] = df["MUNICIPIO"].map(sem_acento)
    pa = df[df["_UF"] == "PA"]
    print("[R-01] termos no Para: %d" % len(pa))
    recorte = pa[pa["_MUN"].isin(MUNICIPIOS)].copy()
    print("[R-01] termos na Transamazonica (4 municipios): %d" % len(recorte))
    por_municipio = {m: int((recorte["_MUN"] == m).sum())
                     for m in sorted(MUNICIPIOS)}
    for m, q in por_municipio.items():
        print("[R-01]    %-14s %d" % (m, q))

    # ------------------ geometria ------------------
    # Ordem de preferencia:
    #  1. WKT do poligono ja presente em GEOM_AREA_EMBARGADA
    #  2. vertices de coordenadas.csv, montados em poligono
    #  3. ponto NUM_LONGITUDE_TAD/NUM_LATITUDE_TAD bufferizado pela area
    #     declarada em QTD_AREA_EMBARGADA (hectares)
    coord = pd.read_csv(csv_coord, sep=";", dtype=str, encoding="utf-8",
                        low_memory=False, on_bad_lines="skip")
    coord_por_tad = {}
    if "SEQ_TAD" in coord.columns:
        alvo = set(recorte["SEQ_TAD"].dropna())
        sub = coord[coord["SEQ_TAD"].isin(alvo)]
        for chave, g in sub.groupby(["SEQ_TAD", "SEQ_POLIGONO"], dropna=False):
            pts = [(num(a), num(b))
                   for a, b in zip(g["LONGITUDE"], g["LATITUDE"])]
            pts = [p for p in pts if p[0] is not None and p[1] is not None]
            if len(pts) >= 3:
                coord_por_tad.setdefault(chave[0], []).append(Polygon(pts))
    print("[R-01] termos do recorte com poligono em coordenadas.csv: %d"
          % len(coord_por_tad))

    geoms, origem_geom = [], []
    for _, linha in recorte.iterrows():
        g = None
        fonte = "GEOM_AREA_EMBARGADA"
        w = linha.get("GEOM_AREA_EMBARGADA")
        if isinstance(w, str) and w.strip() and w.strip().lower() != "nan":
            try:
                g = shapely_wkt.loads(w)
            except Exception:  # noqa: BLE001
                g = None
        if g is None and linha.get("SEQ_TAD") in coord_por_tad:
            polys = coord_por_tad[linha["SEQ_TAD"]]
            g = unary_union(polys)
            fonte = "coordenadas.csv"
        if g is None:
            lon, lat = (num(linha.get("NUM_LONGITUDE_TAD")),
                        num(linha.get("NUM_LATITUDE_TAD")))
            area_ha = num(linha.get("QTD_AREA_EMBARGADA")) or 50.0
            if (lon is not None and lat is not None
                    and -75 < lon < -30 and -35 < lat < 6):
                raio_m = max(150.0, (area_ha * 10_000 / 3.14159) ** 0.5)
                g = Point(lon, lat).buffer(raio_m / 111_320.0, quad_segs=16)
                fonte = "ponto TAD bufferizado pela area declarada"
        geoms.append(g)
        origem_geom.append(fonte if g is not None else "sem geometria")

    recorte["origem_geometria"] = origem_geom
    gdf = gpd.GeoDataFrame(recorte, geometry=geoms, crs="EPSG:4326")
    antes = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print("[R-01] termos com geometria utilizavel: %d de %d" % (len(gdf), antes))
    print(gdf["origem_geometria"].value_counts().to_string())

    gdf = gdf.drop(columns=["_UF", "_MUN"])
    for c in gdf.columns:  # GPKG nao gosta de tipo misto: tudo vira texto
        if c != "geometry":
            gdf[c] = gdf[c].astype(str)

    # Formato de saida: CSV com coluna geom_wkt.
    # Esta maquina bloqueia as DLLs do GDAL por politica de Controle de
    # Aplicativo do Windows, entao pyogrio e fiona nao carregam e GPKG/SHP nao
    # podem ser escritos nem lidos aqui. WKT em CSV e lido por pandas +
    # shapely, que funcionam. ferramentas/geo.py encapsula a leitura e devolve
    # um GeoDataFrame normal para as trilhas B e D.
    gdf = gdf.copy()
    gdf["geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt)
    tabela = pd.DataFrame(gdf.drop(columns="geometry"))

    versao = datetime.now().strftime("%Y%m%d")
    saida = BASES / ("embargos_ibama_transamazonica_%s.csv" % versao)
    tabela.to_csv(saida, index=False, sep=";", encoding="utf-8")
    tabela.to_csv(BASES / "embargos_ibama_transamazonica.csv",
                  index=False, sep=";", encoding="utf-8")
    print("[R-01] recorte salvo: %s (+ atalho estavel)" % saida.name)

    proc.update({
        "crs": "EPSG:4326",
        "campos": campos,
        "coluna_data_atualizacao": col_data,
        "data_atualizacao_base": data_base,
        "total_termos_brasil": int(len(df)),
        "termos_para": int(len(pa)),
        "termos_transamazonica": int(len(recorte)),
        "termos_com_geometria": int(len(gdf)),
        "por_municipio": por_municipio,
        "arquivo_recorte": saida.name,
        "formato_saida": ("CSV com coluna geom_wkt - GDAL bloqueado por "
                          "politica de Controle de Aplicativo do Windows "
                          "nesta maquina, entao SHP/GPKG nao sao gravaveis"),
    })
    (BASES / "R01_procedencia.json").write_text(
        json.dumps(proc, ensure_ascii=False, indent=2), encoding="utf-8")
    # Deu certo: apaga o registro de falha de uma tentativa anterior, para
    # nenhuma trilha achar que a base esta indisponivel.
    falha_antiga = BASES / "R01_FALHA.txt"
    if falha_antiga.exists():
        falha_antiga.unlink()
    print("[R-01] procedencia registrada em dados/bases/R01_procedencia.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
