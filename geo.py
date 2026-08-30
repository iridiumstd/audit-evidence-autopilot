# -*- coding: utf-8 -*-
"""Acesso as camadas geoespaciais de dados/bases/.

Por que este modulo existe: esta maquina bloqueia as DLLs do GDAL por
politica de Controle de Aplicativo do Windows, entao pyogrio e fiona nao
carregam e geopandas nao consegue ler nem escrever SHP/GPKG/GeoJSON.
As camadas sao guardadas em CSV com coluna `geom_wkt`, que pandas + shapely
leem sem GDAL. Toda trilha que precisa de geometria chama daqui e recebe um
GeoDataFrame normal - ninguem precisa saber do detalhe.

Trilha B (verificacao 02) e Trilha D (vigilancia) usam `carregar_embargos()`.
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt as shapely_wkt

RAIZ = Path(__file__).resolve().parent
BASES = RAIZ / "dados" / "bases"

# Camada real do Ibama, recortada na Transamazonica pelo ferramentas/baixar_ibama.py
ARQUIVO_EMBARGOS = BASES / "embargos_ibama_transamazonica.csv"
# Poligonos injetados ao vivo pelo demo/injetar_embargo.py
ARQUIVO_INJETADOS = BASES / "embargos_injetados.csv"
# Fallback semeado - so existe se o download real tiver falhado
ARQUIVO_SEMEADO = BASES / "embargos_ibama_transamazonica_semeado.csv"

CRS_PADRAO = "EPSG:4326"


def ler_csv_wkt(caminho: Path, coluna_wkt: str = "geom_wkt") -> gpd.GeoDataFrame:
    """Le um CSV com coluna WKT e devolve GeoDataFrame em EPSG:4326."""
    df = pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8",
                     low_memory=False)
    geoms = df[coluna_wkt].map(
        lambda w: shapely_wkt.loads(w) if isinstance(w, str) and w.strip()
        else None)
    gdf = gpd.GeoDataFrame(df, geometry=list(geoms), crs=CRS_PADRAO)
    return gdf[gdf.geometry.notna()].copy()


def gravar_csv_wkt(gdf: gpd.GeoDataFrame, caminho: Path) -> Path:
    """Grava um GeoDataFrame como CSV com coluna geom_wkt."""
    saida = gdf.copy()
    saida["geom_wkt"] = saida.geometry.apply(lambda g: g.wkt)
    pd.DataFrame(saida.drop(columns="geometry")).to_csv(
        caminho, index=False, sep=";", encoding="utf-8")
    return caminho


def carregar_embargos(incluir_injetados: bool = True) -> gpd.GeoDataFrame:
    """Camada de embargos do Ibama que a checagem 02 consome.

    Junta a base real recortada com os poligonos injetados na demo.
    Cada linha carrega a coluna `fonte_camada`, que diz de onde veio, para o
    laudo poder declarar a procedencia (ADR-012: dado semeado sai declarado).
    """
    partes = []
    if ARQUIVO_EMBARGOS.exists():
        g = ler_csv_wkt(ARQUIVO_EMBARGOS)
        g["fonte_camada"] = "ibama_real"
        partes.append(g)
    elif ARQUIVO_SEMEADO.exists():
        g = ler_csv_wkt(ARQUIVO_SEMEADO)
        g["fonte_camada"] = "SEMEADO"  # dado fabricado - declarar no laudo
        partes.append(g)
    if incluir_injetados and ARQUIVO_INJETADOS.exists():
        g = ler_csv_wkt(ARQUIVO_INJETADOS)
        g["fonte_camada"] = "injetado_demo"
        partes.append(g)
    if not partes:
        raise FileNotFoundError(
            "Nenhuma camada de embargo em dados/bases/. "
            "Rode: python ferramentas/baixar_ibama.py")
    junto = pd.concat(partes, ignore_index=True)
    return gpd.GeoDataFrame(junto, geometry="geometry", crs=CRS_PADRAO)


def em_metros(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reprojeta para UTM 22S (EPSG:31982), que cobre a Transamazonica.

    Necessario para medir distancia em metros (regra dos 500 m da checagem 02)
    e area em hectares. Nao usa PROJ de disco: EPSG:31982 vem do pyproj.
    """
    return gdf.to_crs("EPSG:31982")


if __name__ == "__main__":
    g = carregar_embargos()
    print("embargos carregados: %d" % len(g))
    print(g["fonte_camada"].value_counts().to_string())
    print("bounds:", g.total_bounds)
