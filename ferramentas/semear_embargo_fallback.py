# -*- coding: utf-8 -*-
"""CAMADA SEMEADA DE EMERGENCIA - NAO E DADO DO IBAMA.

!!! ATENCAO !!!
Todo poligono gerado por este script e FABRICADO. Nao corresponde a termo de
embargo nenhum. Serve exclusivamente para desbloquear as Trilhas A, B, C e D
caso ferramentas/baixar_ibama.py falhe e a base real fique indisponivel.

Regra do ADR-012, respeitada aqui de tres formas:
  1. o arquivo de saida leva o sufixo _semeado no nome;
  2. cada linha carrega TIPO_AREA='SEMEADO' e DES_TAD dizendo que e fabricado;
  3. geo.carregar_embargos() marca a camada com fonte_camada='SEMEADO', e o
     laudo da checagem 02 tem de declarar isso.

Enquanto dados/bases/embargos_ibama_transamazonica.csv (real) existir,
geo.carregar_embargos() ignora esta camada. Ela so entra em cena na ausencia
da real.

Uso:
    python ferramentas/semear_embargo_fallback.py
"""
import random
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import geopandas as gpd  # noqa: E402
from shapely.geometry import Point  # noqa: E402

import geo  # noqa: E402

SEMENTE = 20260830

# Envelope aproximado da Transamazonica no recorte do MVP:
# Medicilandia, Altamira, Uruara e Brasil Novo (PA).
BBOX = (-54.30, -3.95, -51.80, -2.85)   # lon_min, lat_min, lon_max, lat_max
QUANTIDADE = 120


def main() -> int:
    if geo.ARQUIVO_EMBARGOS.exists():
        print("A base REAL do Ibama existe em dados/bases/%s."
              % geo.ARQUIVO_EMBARGOS.name)
        print("Nao ha motivo para semear. Abortando de proposito.")
        print("Se voce quer mesmo semear, apague a base real antes.")
        return 1

    rnd = random.Random(SEMENTE)
    lon_min, lat_min, lon_max, lat_max = BBOX
    registros, geoms = [], []
    for i in range(QUANTIDADE):
        centro = Point(rnd.uniform(lon_min, lon_max),
                       rnd.uniform(lat_min, lat_max))
        area_ha = round(rnd.uniform(15.0, 400.0), 2)
        raio = ((area_ha * 10_000 / 3.14159) ** 0.5) / 111_320.0
        geoms.append(centro.buffer(raio, quad_segs=12))
        registros.append({
            "SEQ_TAD": "S%06d" % i,
            "NUM_TAD": "SEMEADO-%04d" % i,
            "DAT_EMBARGO": (date(2021, 1, 1)).isoformat(),
            "NOME_EMBARGADO": "DADO FABRICADO - SEM CORRESPONDENCIA REAL",
            "CPF_CNPJ_EMBARGADO": "",
            "MUNICIPIO": rnd.choice(["MEDICILANDIA", "ALTAMIRA", "URUARA",
                                     "BRASIL NOVO"]),
            "UF": "PA",
            "QTD_AREA_EMBARGADA": str(area_ha),
            "DES_TAD": ("POLIGONO SEMEADO pelo Evidence Autopilot porque o "
                        "download da base real do Ibama falhou. NAO E DADO "
                        "DO IBAMA. Ver dados/bases/R01_FALHA.txt."),
            "TIPO_AREA": "SEMEADO",
            "SIT_DESEMBARGO": "NAO",
            "origem_geometria": "SEMEADO - circulo em posicao sorteada",
        })

    gdf = gpd.GeoDataFrame(registros, geometry=geoms, crs=geo.CRS_PADRAO)
    geo.gravar_csv_wkt(gdf, geo.ARQUIVO_SEMEADO)
    print("[SEMEADO] %d poligonos FABRICADOS em dados/bases/%s"
          % (len(gdf), geo.ARQUIVO_SEMEADO.name))
    print("[SEMEADO] Declare isso no laudo. Nao apresente como dado do Ibama.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
