# -*- coding: utf-8 -*-
"""verificacao.py - Trilha B (Verificacao). Implementa o SPEC.md secao 4 (v2).

As SETE checagens, as regras R01-R50 da checagem 05, a aptidao em cinco
camadas, o orquestrador e o recalculo de status dos lotes.

Assinatura unica (SPEC 4):
    checagem_NN(talhao_id) -> {resultado, texto, fonte, evidencia,
                               perna, categoria, severidade,
                               tipo_excecao, natureza}

`categoria` e 'A' (perna geometrica) ou uma letra de 'a' a 'h' (legalidade).
`severidade` e 'B' (bloqueia aptidao ate resolver) ou 'F' (flag para revisao).
`tipo_excecao` e um dos quatro valores fixos de db.TIPOS_EXCECAO; a natureza
antiga do achado ('embargo_ibama', 'desmate_pos_2020'...) vive em `natureza`,
vai para a evidencia e para o prefixo da descricao - nunca para `excecao.tipo`.

Regra de escrita do laudo (SPEC 4.5) - inegociavel. Todo `texto` diz:
    (1) o que foi comparado
    (2) contra qual base
    (3) em que DATA a consulta foi feita
    (4) o resultado
    (5) a conclusao em uma frase
A funcao `montar_laudo()` abaixo e a unica forma de montar texto de checagem
neste arquivo justamente para que nenhuma das seis possa esquecer a data.

ADR-012: dado semeado nunca e apresentado como real. As camadas das checagens
01 e 04 nao tem recurso confirmado no ARD.md (R-02, R-04, R-05, R-06 estao
"a descobrir"), entao sao geradas aqui com sufixo `_semeado` no arquivo, com
`FONTE_SEMEADA` no codigo e com a frase "FONTE SEMEADA" no laudo.

Somente as tabelas `checagem`, `excecao` e `aptidao` sao escritas
(contrato.md v2), e sempre por funcoes de db.py. `registrar_evento` sempre.

INVARIANTES DE MICROCOPIA (contrato.md v2, invariantes 4 e 3) - o laudo e a
descricao da excecao falam do DOCUMENTO, nunca da pessoa: "falta o CCIR de
Antonio", jamais "Antonio esta irregular". Ausencia de licenca ambiental, ASV
e SIGEF e a situacao REGULAR da cacauicultura familiar: vira excecao do tipo
`dispensa_documentada`, que o painel nao conta como lacuna.

CLI:
    python verificacao.py --tudo
    python verificacao.py --talhao <id>
    python verificacao.py --lotes
    python verificacao.py --aptidao
"""
import argparse
import json
import math
import random
import re
import sys
from datetime import date, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml
from shapely import wkt as shapely_wkt
from shapely.geometry import Polygon

import db
import geo

RAIZ = Path(__file__).resolve().parent
BASES = RAIZ / "dados" / "bases"
PARAMS = RAIZ / "params" / "cacau.yml"
PROCEDENCIA_R01 = BASES / "R01_procedencia.json"

# Camadas sem recurso confirmado no ARD - geradas semeadas, declaradas no laudo
ARQUIVO_ALERTAS_SEMEADO = BASES / "alertas_desmatamento_semeado.csv"
ARQUIVO_PROTEGIDAS_SEMEADO = BASES / "areas_protegidas_semeado.csv"
# Checagem 07 - Lista Suja do MTE. A planilha semestral oficial ainda nao foi
# baixada (recurso a descobrir), entao a lista e SEMEADA e declarada no laudo.
ARQUIVO_LISTA_SUJA_SEMEADO = BASES / "lista_suja_mte_semeado.csv"

# Marcador unico usado no texto do laudo toda vez que a base nao e real.
FONTE_SEMEADA = "FONTE SEMEADA (dado fabricado para a demonstracao, "\
                "nao e base oficial - ADR-012)"

CRS_METRICO = "EPSG:31982"   # UTM 22S, para medir metros e hectares

SEMENTE = 20260830           # semente fixa: as camadas semeadas sao estaveis

# ---------------------------------------------------------------------------
# Categoria e severidade por checagem (correcoes-spec_1.md 02 e 04, SPEC 4)
# ---------------------------------------------------------------------------
# 'A' e a perna geometrica; 'a'..'h' sao as oito categorias de legalidade.
CATEGORIA_CHECAGEM = {
    "01": "A",        # desmate pos-2020 - perna geometrica, sem categoria b-h
    "02": "b,d",      # embargo: protecao ambiental e direitos de terceiros
    "03": "a,b",      # CAR e direito de uso
    "04": "d,f,g",    # sobreposicao: terceiros, direitos humanos, consulta
    "05": "todas",    # consistencia documental e transversal
    "06": "h",        # tributario, comercial e aduaneiro
    "07": "e,f",      # trabalhista e direitos humanos
}

# Nome legivel da categoria, para o laudo e para o dossie.
NOME_CATEGORIA = {
    "A": "perna geometrica (desmatamento)",
    "a": "uso da terra",
    "b": "protecao ambiental",
    "c": "florestal",
    "d": "direitos de terceiros",
    "e": "trabalhista",
    "f": "direitos humanos",
    "g": "consentimento previo, livre e informado",
    "h": "tributario, comercial e aduaneiro",
}

# Severidade padrao da checagem quando o resultado nao e conforme.
# 'B' bloqueia a aptidao ate resolver; 'F' e flag para revisao humana.
SEVERIDADE_CHECAGEM = {
    "01": "B", "02": "B", "03": "B", "04": "B",
    "05": "B", "06": "F", "07": "B",
}


# ===========================================================================
# Parametros e utilidades
# ===========================================================================
_cache = {}


def validar_params(dados: dict) -> dict:
    """Falha alto e claro quando o cacau.yml perde uma chave essencial.

    Sem `conjunto_minimo` as regras R48 e R12 avaliariam uma lista vazia e
    devolveriam CONFORME sem ter checado nada - conforme silencioso, que este
    sistema nunca pode produzir (mesmo principio do ADR-012 para as bases).
    """
    if not isinstance(dados, dict):
        raise ValueError("params/cacau.yml nao carregou como mapa YAML valido")
    minimo = dados.get("conjunto_minimo")
    if not isinstance(minimo, dict) or not minimo.get("obrigatorios"):
        raise ValueError(
            "params/cacau.yml invalido: falta a chave 'conjunto_minimo' com a "
            "lista 'obrigatorios'. Sem ela as regras de conjunto minimo "
            "documental (R48/R12) nao podem ser avaliadas e nenhum resultado "
            "'conforme' seria confiavel. Restaure a chave em params/cacau.yml.")
    return dados


def carregar_params() -> dict:
    """Le params/cacau.yml uma vez por processo."""
    if "params" not in _cache:
        with open(PARAMS, encoding="utf-8") as f:
            _cache["params"] = validar_params(yaml.safe_load(f))
    return _cache["params"]


def hoje() -> str:
    """Data da consulta, ISO. E o item (3) do laudo - sem ela nada presta."""
    return date.today().isoformat()


def data_base_r01() -> str:
    """Data de atualizacao declarada da base de embargos do Ibama."""
    if "r01" not in _cache:
        info = {}
        if PROCEDENCIA_R01.exists():
            info = json.loads(PROCEDENCIA_R01.read_text(encoding="utf-8"))
        _cache["r01"] = info
    return _cache["r01"].get("data_atualizacao_base", "desconhecida")


def montar_laudo(comparado: str, base: str, resultado: str,
                 conclusao: str, data_consulta: str = None) -> str:
    """Monta o texto da checagem no formato obrigatorio do SPEC 4.5.

    Passa a data explicitamente para dentro da frase - e o item que o SPEC
    chama de indispensavel ("sem a data, o laudo nao presta").
    """
    return (
        "Comparado: %s. "
        "Base consultada: %s. "
        "Data da consulta: %s. "
        "Resultado: %s. "
        "Conclusao: %s"
    ) % (comparado, base, data_consulta or hoje(), resultado, conclusao)


def _num(valor, padrao=None):
    """Converte para float aceitando '1.234,56', '1234.56', None e lixo."""
    if valor is None:
        return padrao
    if isinstance(valor, (int, float)):
        return None if isinstance(valor, float) and math.isnan(valor) \
            else float(valor)
    texto = str(valor).strip()
    if not texto:
        return padrao
    texto = re.sub(r"[^\d,.\-]", "", texto)
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return padrao


def _digitos(valor) -> str:
    """So os digitos - normaliza CPF/CNPJ escritos de jeitos diferentes."""
    return re.sub(r"\D", "", str(valor or ""))


def _data(valor):
    """Converte texto para date, aceitando ISO e dd/mm/aaaa. None se falhar."""
    if not valor:
        return None
    texto = str(valor).strip()[:19]
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S",
                    "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto[:len(datetime.now()
                                                .strftime(formato))],
                                     formato).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        return None


def _normalizar_nome(nome: str) -> str:
    """Nome sem acento, sem pontuacao, minusculo - para comparar titulares."""
    import unicodedata
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-zA-Z ]", " ", texto).lower()
    return " ".join(texto.split())


def _campos(documento: dict) -> dict:
    """Le documento.campos_json com tolerancia a nulo e a JSON quebrado."""
    bruto = documento.get("campos_json")
    if not bruto:
        return {}
    try:
        valor = json.loads(bruto)
        return valor if isinstance(valor, dict) else {}
    except (ValueError, TypeError):
        return {}


# A Trilha A grava os campos extraidos com nomes proprios, que nem sempre
# coincidem com os nomes canonicos de params/cacau.yml (ela grava `cpf` onde o
# YAML preve `cpf_titular`, `numero` onde preve `numero_car`, e assim por
# diante). Este mapa e a ponte entre os dois vocabularios: a Trilha B le pelo
# nome canonico e cai nos apelidos que existirem, sem editar arquivo de outra
# trilha.
APELIDOS_CAMPO = {
    "cpf_titular": ["cpf_titular", "cpf", "cpf_cnpj", "cpf_emitente"],
    "cpf_emitente": ["cpf_emitente", "cpf", "cpf_cnpj", "cpf_titular"],
    "numero_car": ["numero_car", "numero"],
    "numero_matricula": ["numero_matricula", "numero"],
    "numero": ["numero", "numero_car", "numero_matricula"],
    "proprietario": ["proprietario", "titular", "nome", "declarante"],
    "titular": ["titular", "proprietario", "nome", "declarante"],
    "arrendatario": ["arrendatario", "titular", "nome"],
    "municipio": ["municipio"],
    "situacao": ["situacao", "car_situacao"],
    "area_ha": ["area_ha", "area_total_ha", "area_autorizada_ha"],
    "area_total_ha": ["area_total_ha", "area_ha"],
    "quantidade_kg": ["quantidade_kg"],
    "serie": ["serie"],
    "vigencia_inicio": ["vigencia_inicio"],
    "vigencia_fim": ["vigencia_fim"],
}


def _campo(campos: dict, nome: str):
    """Le um campo pelo nome canonico, aceitando os apelidos da Trilha A."""
    for chave in APELIDOS_CAMPO.get(nome, [nome]):
        valor = campos.get(chave)
        if valor not in (None, "", []):
            return valor
    return None


def _cita_talhao(documento: dict, talhao: dict) -> bool:
    """O documento se refere a este talhao?

    A ingestao grava `talhao_citado` com o nome do talhao a que o documento se
    refere. Sem isso, documentos de talhoes diferentes do mesmo produtor
    seriam comparados entre si e toda area pareceria divergente.
    """
    citado = _campos(documento).get("talhao_citado")
    if citado:
        return _normalizar_nome(citado) == _normalizar_nome(talhao.get("nome"))
    # sem talhao citado, o documento vale para o produtor inteiro
    return documento.get("talhao_id") in (None, "", talhao.get("id"))


def _geom_talhao(talhao: dict):
    """Geometria shapely do talhao, ou None se o WKT estiver ausente/quebrado."""
    bruto = talhao.get("geom_wkt")
    if not bruto:
        return None
    try:
        return shapely_wkt.loads(bruto)
    except Exception:
        return None


def _gdf_talhao(talhao: dict):
    """GeoDataFrame de uma linha, em EPSG:4326, com o talhao."""
    g = _geom_talhao(talhao)
    if g is None:
        return None
    return gpd.GeoDataFrame([{"talhao_id": talhao["id"]}], geometry=[g],
                            crs=geo.CRS_PADRAO)


def _sem_geometria(codigo, perna, categoria, talhao_id, base):
    """Resultado padrao quando o talhao nao tem geometria utilizavel.

    Nao e conforme: e lacuna. Vira excecao para o humano resolver.
    """
    return {
        "resultado": "excecao",
        "perna": perna,
        "categoria": categoria,
        "fonte": base,
        "texto": montar_laudo(
            comparado="geometria do talhao %s" % talhao_id,
            base=base,
            resultado="talhao sem geometria valida em `talhao.geom_wkt`",
            conclusao="nao foi possivel executar a checagem geoespacial; "
                      "lacuna cadastral que exige revisao humana."),
        "evidencia": {"motivo": "geometria ausente ou invalida"},
    }


# ===========================================================================
# Camadas semeadas - ADR-012: marcadas no codigo e declaradas no laudo
# ===========================================================================
def _grade_de_poligonos(gdf_talhoes, quantidade, sementinha, lado_graus,
                        deslocamento):
    """Gera poligonos cobrindo parcialmente talhoes escolhidos por sorteio.

    Usado SO para fabricar as camadas semeadas das checagens 01 e 04, para as
    quais nao existe recurso confirmado no ARD.md. Semente fixa, resultado
    reproduzivel.
    """
    aleatorio = random.Random(sementinha)
    escolhidos = aleatorio.sample(range(len(gdf_talhoes)),
                                  min(quantidade, len(gdf_talhoes)))
    poligonos = []
    for i in escolhidos:
        centro = gdf_talhoes.geometry.iloc[i].centroid
        dx = aleatorio.uniform(-deslocamento, deslocamento)
        dy = aleatorio.uniform(-deslocamento, deslocamento)
        x, y = centro.x + dx, centro.y + dy
        meia = lado_graus / 2.0
        poligonos.append(Polygon([
            (x - meia, y - meia), (x + meia, y - meia),
            (x + meia, y + meia), (x - meia, y + meia)]))
    return poligonos


def _todos_talhoes_gdf():
    """GeoDataFrame com os talhoes do banco (cacheado no processo)."""
    if "talhoes_gdf" in _cache:
        return _cache["talhoes_gdf"]
    linhas = db.listar("talhao")
    registros, geoms = [], []
    for t in linhas:
        g = _geom_talhao(t)
        if g is None:
            continue
        registros.append({"talhao_id": t["id"], "nome": t["nome"]})
        geoms.append(g)
    gdf = gpd.GeoDataFrame(registros, geometry=geoms, crs=geo.CRS_PADRAO)
    _cache["talhoes_gdf"] = gdf
    return gdf


def _talhoes_fora_de_lote_gdf():
    """Talhoes que NAO estao em nenhum lote - o unico alvo licito das camadas
    semeadas.

    Motivo (defeito B2): dado fabricado nao pode decidir o resultado da
    demonstracao. Se um alerta semeado ou uma TI semeada cai sobre talhao de
    lote, os tres lotes saem bloqueados antes da apresentacao e a virada de cor
    do `demo/injetar_embargo.py` - que e o momento da demo - deixa de existir.
    O embargo REAL do Ibama continua valendo sobre qualquer talhao: quem nao
    pode inventar bloqueio e a base semeada.
    """
    if "talhoes_fora_gdf" in _cache:
        return _cache["talhoes_fora_gdf"]
    em_lote = {linha["talhao_id"] for linha in
               db.consultar("SELECT DISTINCT talhao_id FROM lote_talhao")}
    todos = _todos_talhoes_gdf()
    fora = todos[~todos["talhao_id"].isin(em_lote)].reset_index(drop=True)
    _cache["talhoes_fora_gdf"] = fora
    return fora


def garantir_camada_alertas() -> Path:
    """Camada da checagem 01. R-02 esta 'a descobrir' no ARD.md -> SEMEADA."""
    if ARQUIVO_ALERTAS_SEMEADO.exists():
        return ARQUIVO_ALERTAS_SEMEADO
    talhoes = _talhoes_fora_de_lote_gdf()
    aleatorio = random.Random(SEMENTE + 1)
    # ~0.0025 grau ~ 275 m de lado; deslocamento pequeno = sobreposicao parcial
    poligonos = _grade_de_poligonos(talhoes, quantidade=5,
                                    sementinha=SEMENTE + 1,
                                    lado_graus=0.0025, deslocamento=0.0009)
    linhas = []
    for i, poly in enumerate(poligonos, start=1):
        # metade dos alertas e anterior ao corte de 31/12/2020, para exercitar
        # os dois lados da regra da perna A
        ano = aleatorio.choice([2018, 2019, 2021, 2022, 2023, 2024, 2025])
        linhas.append({
            "id_alerta": "ALERTA-SEMEADO-%03d" % i,
            "data_deteccao": "%d-%02d-%02d" % (
                ano, aleatorio.randint(1, 12), aleatorio.randint(1, 28)),
            "sistema": "SEMEADO (sem recurso real - ARD R-02 a descobrir)",
            "area_alerta_ha": round(poly.area * 1.23e10 / 1e4, 2),
            "fonte_camada": "SEMEADO",
            "geometry": poly,
        })
    gdf = gpd.GeoDataFrame(linhas, geometry="geometry", crs=geo.CRS_PADRAO)
    BASES.mkdir(parents=True, exist_ok=True)
    geo.gravar_csv_wkt(gdf, ARQUIVO_ALERTAS_SEMEADO)
    return ARQUIVO_ALERTAS_SEMEADO


def garantir_camada_protegidas() -> Path:
    """Camada da checagem 04. R-04/R-05/R-06 'a descobrir' -> SEMEADA."""
    if ARQUIVO_PROTEGIDAS_SEMEADO.exists():
        return ARQUIVO_PROTEGIDAS_SEMEADO
    # so talhoes fora de lote - ver _talhoes_fora_de_lote_gdf (defeito B2)
    talhoes = _talhoes_fora_de_lote_gdf()
    aleatorio = random.Random(SEMENTE + 2)
    poligonos = _grade_de_poligonos(talhoes, quantidade=4,
                                    sementinha=SEMENTE + 2,
                                    lado_graus=0.0060, deslocamento=0.0020)
    # `categoria_area` e o atributo que permite separar R18 de R19: sem ele
    # nao da para saber se a TI e homologada (B) ou apenas declarada (F), nem
    # se a UC e de protecao integral (B) ou de uso sustentavel (F). O ciclo
    # alterna as categorias justamente para exercitar os dois lados da regra.
    tipos = [
        ("terra_indigena", "TI SEMEADA %s", "FUNAI (nao consultada - semeado)",
         ["homologada", "declarada"]),
        ("territorio_quilombola", "Quilombo SEMEADO %s",
         "INCRA (nao consultado - semeado)", ["titulado", "em_processo"]),
        ("unidade_conservacao", "UC SEMEADA %s",
         "CNUC/MMA (nao consultado - semeado)",
         ["protecao_integral", "uso_sustentavel"]),
    ]
    linhas = []
    for i, poly in enumerate(poligonos, start=1):
        tipo, molde, orgao, categorias = tipos[i % len(tipos)]
        linhas.append({
            "id_area": "PROT-SEMEADO-%03d" % i,
            "tipo_area": tipo,
            "categoria_area": categorias[(i // len(tipos)) % len(categorias)],
            "nome_area": molde % chr(64 + i),
            "orgao": orgao,
            "categoria_eudr": "4 e 7",
            "fonte_camada": "SEMEADO",
            "geometry": poly,
        })
    _ = aleatorio  # semente ja consumida em _grade_de_poligonos
    gdf = gpd.GeoDataFrame(linhas, geometry="geometry", crs=geo.CRS_PADRAO)
    BASES.mkdir(parents=True, exist_ok=True)
    geo.gravar_csv_wkt(gdf, ARQUIVO_PROTEGIDAS_SEMEADO)
    return ARQUIVO_PROTEGIDAS_SEMEADO


def carregar_alertas():
    if "alertas" not in _cache:
        _cache["alertas"] = geo.ler_csv_wkt(garantir_camada_alertas())
    return _cache["alertas"]


def carregar_protegidas():
    if "protegidas" not in _cache:
        _cache["protegidas"] = geo.ler_csv_wkt(garantir_camada_protegidas())
    return _cache["protegidas"]


def garantir_lista_suja() -> Path:
    """Lista Suja do MTE da checagem 07 - SEMEADA e declarada como tal.

    A planilha semestral oficial do MTE nao foi baixada (recurso a descobrir
    no ARD.md), entao a lista e fabricada aqui com um ou dois CPFs de
    produtores que NAO compoem nenhum lote - pelo mesmo motivo do defeito B2:
    dado semeado nao decide o resultado da demonstracao. O matching e sempre
    por CPF, nunca por nome (nomes colidem e divergem entre documentos).
    """
    if ARQUIVO_LISTA_SUJA_SEMEADO.exists():
        return ARQUIVO_LISTA_SUJA_SEMEADO
    em_lote = {linha["produtor_id"] for linha in db.consultar(
        "SELECT DISTINCT t.produtor_id FROM talhao t "
        "JOIN lote_talhao lt ON lt.talhao_id = t.id")}
    candidatos = [p for p in db.listar_produtores()
                  if p["id"] not in em_lote and _digitos(p.get("cpf"))]
    candidatos.sort(key=lambda p: p["id"])
    escolhidos = candidatos[:2]
    linhas = []
    for i, p in enumerate(escolhidos, start=1):
        linhas.append({
            "cpf_cnpj": _digitos(p.get("cpf")),
            "nome_referencia": p.get("nome"),   # informativo: NAO e chave
            "uf": p.get("uf") or "PA",
            "ano_inclusao": 2025,
            "numero_inscricao": "MTE-SEMEADO-%03d" % i,
            "fonte_camada": "SEMEADO",
        })
    BASES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas, columns=[
        "cpf_cnpj", "nome_referencia", "uf", "ano_inclusao",
        "numero_inscricao", "fonte_camada"]).to_csv(
        ARQUIVO_LISTA_SUJA_SEMEADO, index=False, encoding="utf-8")
    return ARQUIVO_LISTA_SUJA_SEMEADO


def carregar_lista_suja() -> dict:
    """Mapa CPF/CNPJ (so digitos) -> registro da Lista Suja semeada."""
    if "lista_suja" not in _cache:
        caminho = garantir_lista_suja()
        registros = {}
        if caminho.exists():
            tabela = pd.read_csv(caminho, dtype=str, encoding="utf-8")
            for _, linha in tabela.iterrows():
                chave = _digitos(linha.get("cpf_cnpj"))
                if chave:
                    registros[chave] = {k: (None if pd.isna(v) else str(v))
                                        for k, v in linha.items()}
        _cache["lista_suja"] = registros
    return _cache["lista_suja"]


def carregar_embargos_metrico():
    """Embargos ja reprojetados para metros - reprojetar 3.162 geometrias por
    talhao seria o gargalo do verificar_tudo()."""
    if "embargos_m" not in _cache:
        bruto = geo.carregar_embargos()
        _cache["embargos_bruto"] = bruto
        _cache["embargos_m"] = geo.em_metros(bruto)
    return _cache["embargos_m"]


def carregar_embargos_por_cpf() -> dict:
    """Indice CPF/CNPJ (so digitos) -> termos de embargo do recorte inteiro.

    O cruzamento da checagem 02 e "por poligono E POR CPF" (contrato v2,
    linha 02). Este indice cobre TODOS os termos do recorte, nao apenas os
    que caem perto do talhao: o embargo em nome do produtor pode estar em
    outra area, e e exatamente esse o caso que a interseccao geometrica nao
    enxerga (posseiro, herdeiro, meeiro - CPF divergente).
    """
    if "embargos_por_cpf" not in _cache:
        carregar_embargos_metrico()          # popula tambem `embargos_bruto`
        bruto = _cache["embargos_bruto"]
        indice = {}
        for _, linha in bruto.iterrows():
            chave = _digitos(linha.get("CPF_CNPJ_EMBARGADO"))
            if not chave:
                continue
            indice.setdefault(chave, []).append({
                "num_tad": str(linha.get("NUM_TAD") or "sem numero"),
                "embargado": str(linha.get("NOME_EMBARGADO") or ""),
                "cpf_cnpj_embargado": chave,
                "municipio": str(linha.get("MUNICIPIO") or ""),
                "uf": str(linha.get("UF") or ""),
                "data_embargo": str(linha.get("DAT_EMBARGO") or ""),
                "area_embargada": str(linha.get("QTD_AREA_EMBARGADA") or ""),
                "fonte_camada": str(linha.get("fonte_camada") or ""),
            })
        _cache["embargos_por_cpf"] = indice
    return _cache["embargos_por_cpf"]


def _casas_decimais_minimas(wkt_texto: str):
    """Menor numero de casas decimais entre as coordenadas de um WKT.

    Serve a checagem 01: o Art. 2(28) exige o ponto com SEIS casas decimais.
    Coordenada com menos casas nao identifica a parcela com a precisao que o
    Regulamento pede - e defeito de dado, nao de geometria, e por isso e
    apenas DETECTADO aqui (nenhuma geometria e alterada).
    """
    if not wkt_texto:
        return None
    numeros = re.findall(r"-?\d+(?:\.\d+)?", str(wkt_texto))
    if not numeros:
        return None
    casas = [len(n.split(".")[1]) if "." in n else 0 for n in numeros]
    return min(casas) if casas else None


def limpar_cache_geo():
    """A vigilancia injeta poligono novo em disco; isso descarta o cache."""
    for chave in ("embargos_m", "embargos_bruto", "embargos_por_cpf",
                  "alertas", "protegidas",
                  "talhoes_gdf", "talhoes_fora_gdf", "lista_suja"):
        _cache.pop(chave, None)


# ===========================================================================
# Checagem 01 - Desmate pos-2020 (perna A)
# ===========================================================================
def checagem_01(talhao_id: str) -> dict:
    """Interseccao com alerta de desmatamento posterior a 31/12/2020.

    Perna A. Nao tem categoria (categoria e coisa da perna B).
    Camada SEMEADA - ARD R-02 ainda esta 'a descobrir'.
    """
    perna, categoria = "A", CATEGORIA_CHECAGEM["01"]
    params = carregar_params()
    corte = params["desmatamento"]["data_corte"]
    base = ("camada de alertas de desmatamento `%s` - %s"
            % (ARQUIVO_ALERTAS_SEMEADO.name, FONTE_SEMEADA))
    talhao = db.buscar_talhao(talhao_id)
    alvo = _gdf_talhao(talhao)
    if alvo is None:
        return _sem_geometria("01", perna, categoria, talhao_id, base)

    # --- precisao da coordenada: Art. 2(28) exige SEIS casas decimais -------
    # Talhao entregue como ponto com coordenada truncada nao identifica a
    # parcela com a precisao que o Regulamento pede. So DETECTAMOS: nenhuma
    # geometria e alterada aqui (contrato v2, checagem 01 / camada 1).
    casas_exigidas = 6
    casas = _casas_decimais_minimas(talhao.get("geom_wkt"))
    ponto = (talhao.get("tipo_geom") or "").strip().lower() == "ponto"
    precisao_insuficiente = bool(
        ponto and casas is not None and casas < casas_exigidas)

    alertas = carregar_alertas()
    tocados = gpd.sjoin(alertas, alvo, how="inner", predicate="intersects")
    data_corte = _data(corte)
    posteriores = []
    for _, linha in tocados.iterrows():
        deteccao = _data(linha.get("data_deteccao"))
        if deteccao and data_corte and deteccao > data_corte:
            posteriores.append(linha)

    if not posteriores and precisao_insuficiente:
        # Sem desmate posterior ao corte, mas a coordenada do ponto nao tem as
        # seis casas decimais do Art. 2(28): excecao F (flag para revisao),
        # nunca bloqueio - o defeito e de PRECISAO do dado, nao de legalidade.
        return {
            "resultado": "excecao", "perna": perna, "categoria": categoria,
            "severidade": "F", "fonte": base,
            "texto": montar_laudo(
                comparado="a coordenada declarada do talhao %s, entregue como "
                          "ponto, contra a precisao de %d casas decimais que "
                          "o Art. 2(28) do Regulamento (UE) 2023/1115 exige "
                          "da geolocalizacao da parcela; e contra os alertas "
                          "de supressao posteriores a %s"
                          % (talhao["nome"], casas_exigidas, corte),
                base=base + "; e o texto do Art. 2(28) quanto a precisao",
                resultado="nenhum alerta posterior ao corte intersecta o "
                          "talhao, mas a coordenada tem apenas %d casa(s) "
                          "decimal(is) - abaixo das %d exigidas"
                          % (casas, casas_exigidas),
                conclusao="falta precisao na coordenada do talhao: com menos "
                          "de %d casas decimais o ponto nao localiza a "
                          "parcela como o Art. 2(28) pede, e a checagem "
                          "geoespacial fica sem base confiavel - EXCECAO "
                          "para recoleta da coordenada (o dado nao foi "
                          "alterado)." % casas_exigidas),
            "evidencia": {"alertas_intersectados": int(len(tocados)),
                          "alertas_pos_corte": 0,
                          "motivo_excecao": "precisao_coordenada",
                          "casas_decimais": casas,
                          "casas_decimais_exigidas": casas_exigidas,
                          "tipo_geom": talhao.get("tipo_geom"),
                          "data_corte": corte,
                          "fonte_camada": "SEMEADO"},
        }

    if not posteriores:
        anteriores = len(tocados)
        return {
            "resultado": "conforme", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="poligono do talhao %s (%s, %.2f ha) contra alertas "
                          "de supressao de vegetacao com data posterior a %s"
                          % (talhao["nome"], talhao["tipo_geom"],
                             talhao["area_ha"] or 0.0, corte),
                base=base,
                resultado="nenhum alerta posterior ao corte intersecta o "
                          "talhao (%d alerta(s) anteriores ao corte no "
                          "entorno)" % anteriores,
                conclusao="talhao atende a perna A (livre de desmatamento "
                          "pos-2020) segundo a camada consultada, que e "
                          "semeada e precisa ser trocada por base oficial "
                          "antes de valer como prova."),
            "evidencia": {"alertas_intersectados": int(len(tocados)),
                          "alertas_pos_corte": 0,
                          "data_corte": corte,
                          "fonte_camada": "SEMEADO"},
        }

    ids = [str(l.get("id_alerta")) for l in posteriores]
    datas = [str(l.get("data_deteccao")) for l in posteriores]
    area_m2 = 0.0
    try:
        alvo_m = alvo.to_crs(CRS_METRICO)
        recorte = gpd.GeoDataFrame(
            posteriores, geometry="geometry",
            crs=geo.CRS_PADRAO).to_crs(CRS_METRICO)
        area_m2 = float(recorte.intersection(
            alvo_m.geometry.iloc[0]).area.sum())
    except Exception:
        area_m2 = 0.0

    return {
        "resultado": "bloqueio", "perna": perna, "categoria": categoria,
        "fonte": base,
        "texto": montar_laudo(
            comparado="poligono do talhao %s (%.2f ha) contra alertas de "
                      "supressao de vegetacao posteriores a %s"
                      % (talhao["nome"], talhao["area_ha"] or 0.0, corte),
            base=base,
            resultado="%d alerta(s) posteriores ao corte intersectam o talhao "
                      "(%s; deteccao em %s), somando %.4f ha de area comum"
                      % (len(posteriores), ", ".join(ids), ", ".join(datas),
                         area_m2 / 10000.0),
            conclusao="ha indicio de desmatamento apos 31/12/2020 dentro do "
                      "talhao: o lote fica BLOQUEADO na perna A ate que a "
                      "camada oficial confirme ou afaste o alerta (a camada "
                      "usada aqui e semeada)."),
        "evidencia": {"alertas_pos_corte": ids, "datas_deteccao": datas,
                      "area_intersecao_ha": round(area_m2 / 10000.0, 4),
                      "data_corte": corte, "fonte_camada": "SEMEADO",
                      # o bloqueio por desmate e mais grave e prevalece, mas a
                      # falta de precisao fica registrada na evidencia
                      "precisao_insuficiente": precisao_insuficiente,
                      "casas_decimais": casas,
                      "casas_decimais_exigidas": casas_exigidas},
    }


# ===========================================================================
# Checagem 02 - Embargo do Ibama (perna B, categoria 2) - a da demo
# ===========================================================================
def checagem_02(talhao_id: str) -> dict:
    """Interseccao com embargo -> bloqueio; distancia < 500 m -> excecao.

    Evidencia obrigatoria: NUM_TAD (numero do termo de embargo) e area de
    interseccao. E a checagem do momento de 3:15 da demonstracao.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["02"]
    params = carregar_params()
    limite_m = float(params["embargo"]["distancia_excecao_m"])
    # A LDI-PA (Lista de Areas Embargadas da SEMAS-PA) NAO foi consultada: a
    # base ainda esta 'a descobrir' no ARD.md. Isso vai declarado no laudo,
    # como a checagem 03 declara que o SICAR nao foi consultado online -
    # nenhuma base semeada e inventada no lugar dela (ADR-012).
    RESSALVA_LDI = ("; a LDI-PA (Lista de Areas Embargadas da SEMAS-PA) NAO "
                    "foi consultada nesta execucao - a fonte ainda esta 'a "
                    "descobrir' no ARD.md, entao o cruzamento estadual "
                    "continua pendente e o resultado abaixo cobre apenas o "
                    "embargo federal do Ibama")
    base = ("Termos de embargo do Ibama (ARD R-01, "
            "dados abertos SIFISC/termo_embargo, recorte da Transamazonica, "
            "base atualizada em %s)%s" % (data_base_r01(), RESSALVA_LDI))

    talhao = db.buscar_talhao(talhao_id)
    alvo = _gdf_talhao(talhao)
    if alvo is None:
        return _sem_geometria("02", perna, categoria, talhao_id, base)

    # --- cruzamento POR CPF, no recorte inteiro (contrato v2, linha 02) -----
    # Embargo em nome do produtor pode estar em OUTRA area: posseiro, herdeiro
    # e meeiro aparecem com CPF divergente do titular do poligono. Por isso o
    # indice cobre todos os termos do recorte, e nao so a vizinhanca.
    produtor = db.buscar_produtor(talhao.get("produtor_id")) or {}
    cpf_produtor = _digitos(produtor.get("cpf"))
    termos_mesmo_cpf = (carregar_embargos_por_cpf().get(cpf_produtor, [])
                        if cpf_produtor else [])

    def _excecao_por_cpf(embargos_avaliados, distancia_minima):
        """Match por CPF SEM interseccao geometrica: excecao de severidade F.

        Nao e bloqueio: o embargo esta em nome do produtor, mas em OUTRA
        area - nada prova, por si, que o talhao deste lote esteja embargado.
        E flag para revisao humana (quem decide e sempre o humano,
        invariante 5), e a microcopia fala do embargo, nunca da pessoa.
        """
        tads = ", ".join(t["num_tad"] for t in termos_mesmo_cpf)
        locais = ", ".join(sorted({("%s/%s" % (t["municipio"], t["uf"])).strip("/")
                                   for t in termos_mesmo_cpf if t["municipio"]}))
        return {
            "resultado": "excecao", "perna": perna, "categoria": categoria,
            "severidade": "F", "fonte": base,
            "texto": montar_laudo(
                comparado="o CPF do produtor do talhao %s (%s) contra o campo "
                          "CPF_CNPJ_EMBARGADO de TODOS os termos de embargo do "
                          "recorte, e nao apenas dos que tocam o poligono - o "
                          "cruzamento da checagem 02 e por poligono E por CPF"
                          % (talhao["nome"], cpf_produtor),
                base=base,
                resultado="nenhum termo de embargo intersecta o talhao, mas "
                          "%d termo(s) (TAD %s) estao registrados sob o mesmo "
                          "CPF%s"
                          % (len(termos_mesmo_cpf), tads,
                             " - em %s" % locais if locais else ""),
                conclusao="ha embargo em nome do produtor sobre OUTRA area: o "
                          "talhao deste lote nao esta sob o poligono "
                          "embargado, entao nao ha bloqueio, mas o vinculo "
                          "por CPF (posseiro, herdeiro ou meeiro aparecem com "
                          "CPF divergente) precisa ser conferido antes do "
                          "embarque - EXCECAO de severidade F para revisao "
                          "humana."),
            "evidencia": {
                "embargos_avaliados": int(embargos_avaliados),
                "distancia_minima_m": distancia_minima,
                "area_intersecao_ha": 0.0,
                "motivo_excecao": "match_por_cpf_sem_intersecao",
                "cpf_produtor": cpf_produtor,
                "termos_mesmo_cpf": termos_mesmo_cpf,
                "num_tad": [t["num_tad"] for t in termos_mesmo_cpf],
                "ldi_pa_consultada": False,
                "data_atualizacao_base": data_base_r01()},
        }

    embargos_m = carregar_embargos_metrico()
    alvo_m = alvo.to_crs(CRS_METRICO)
    geom_m = alvo_m.geometry.iloc[0]

    # Recorte por caixa envolvente antes de medir - 3.162 geometrias por talhao
    # medidas uma a uma inviabilizariam verificar_tudo().
    vizinhanca = embargos_m[embargos_m.geometry.intersects(
        geom_m.buffer(limite_m * 2))]

    if vizinhanca.empty:
        if termos_mesmo_cpf:
            return _excecao_por_cpf(0, None)
        return {
            "resultado": "conforme", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="geometria do talhao %s (%s, %.2f ha) contra os "
                          "poligonos de termos de embargo do Ibama, medindo "
                          "interseccao e distancia em EPSG:31982"
                          % (talhao["nome"], talhao["tipo_geom"],
                             talhao["area_ha"] or 0.0),
                base=base,
                resultado="nenhum termo de embargo intersecta o talhao nem "
                          "fica a menos de %.0f m dele" % limite_m,
                conclusao="talhao livre de embargo do Ibama na data da "
                          "consulta - categoria 2 (protecao ambiental) "
                          "conforme."),
            "evidencia": {"embargos_avaliados": 0,
                          "distancia_minima_m": None,
                          "limite_proximidade_m": limite_m,
                          "cpf_produtor": cpf_produtor,
                          "termos_mesmo_cpf": [],
                          "ldi_pa_consultada": False,
                          "data_atualizacao_base": data_base_r01()},
        }

    # --- interseccao: bloqueio ---
    sobrepostos = vizinhanca[vizinhanca.geometry.intersects(geom_m)]
    if not sobrepostos.empty:
        detalhes = []
        area_total_m2 = 0.0
        for _, linha in sobrepostos.iterrows():
            try:
                area = float(linha.geometry.intersection(geom_m).area)
            except Exception:
                area = 0.0
            area_total_m2 += area
            detalhes.append({
                "num_tad": str(linha.get("NUM_TAD") or "sem numero"),
                "serie_tad": str(linha.get("SER_TAD") or ""),
                "embargado": str(linha.get("NOME_EMBARGADO") or ""),
                "cpf_cnpj_embargado": str(
                    linha.get("CPF_CNPJ_EMBARGADO") or ""),
                "municipio": str(linha.get("MUNICIPIO") or ""),
                "data_embargo": str(linha.get("DAT_EMBARGO") or ""),
                "area_intersecao_ha": round(area / 10000.0, 4),
                "origem_geometria": str(linha.get("origem_geometria") or ""),
                "fonte_camada": str(linha.get("fonte_camada") or ""),
            })
        tads = ", ".join(d["num_tad"] for d in detalhes)
        area_ha = area_total_m2 / 10000.0
        pct = (area_ha / talhao["area_ha"] * 100.0) if talhao.get("area_ha") \
            else 0.0
        ressalva = _ressalva_geometria(detalhes)
        injetado = any(d["fonte_camada"] == "injetado_demo" for d in detalhes)
        return {
            "resultado": "bloqueio", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="geometria do talhao %s (%s, %.2f ha) contra os "
                          "poligonos de termos de embargo do Ibama, medindo "
                          "a area comum em EPSG:31982"
                          % (talhao["nome"], talhao["tipo_geom"],
                             talhao["area_ha"] or 0.0),
                base=base + (" + poligono injetado ao vivo na demonstracao"
                             if injetado else ""),
                resultado="o talhao INTERSECTA %d termo(s) de embargo "
                          "(TAD %s), com %.4f ha de area comum, equivalente a "
                          "%.1f%% do talhao%s"
                          % (len(detalhes), tads, area_ha, pct, ressalva),
                conclusao="plantio sobre area embargada pelo Ibama: o talhao "
                          "esta BLOQUEADO e todo lote que o contenha nao pode "
                          "ser embarcado ate o desembargo ou a exclusao do "
                          "talhao do lote."),
            "evidencia": {
                "num_tad": [d["num_tad"] for d in detalhes],
                "area_intersecao_ha": round(area_ha, 4),
                "percentual_do_talhao": round(pct, 2),
                "termos": detalhes,
                # o cruzamento por CPF corre sempre, mesmo quando ha
                # interseccao: diz se o embargo esta ou nao no nome do produtor
                "cpf_produtor": cpf_produtor,
                "termos_mesmo_cpf": termos_mesmo_cpf,
                "ldi_pa_consultada": False,
                "data_atualizacao_base": data_base_r01(),
                "crs_medicao": CRS_METRICO,
            },
        }

    # --- proximidade: excecao ---
    distancias = vizinhanca.geometry.distance(geom_m)
    minima = float(distancias.min())
    if minima < limite_m:
        proximos = vizinhanca[distancias < limite_m]
        detalhes = []
        for indice, linha in proximos.iterrows():
            detalhes.append({
                "num_tad": str(linha.get("NUM_TAD") or "sem numero"),
                "embargado": str(linha.get("NOME_EMBARGADO") or ""),
                "municipio": str(linha.get("MUNICIPIO") or ""),
                "data_embargo": str(linha.get("DAT_EMBARGO") or ""),
                "distancia_m": round(float(distancias.loc[indice]), 1),
                "origem_geometria": str(linha.get("origem_geometria") or ""),
                "fonte_camada": str(linha.get("fonte_camada") or ""),
            })
        detalhes.sort(key=lambda d: d["distancia_m"])
        tads = ", ".join(d["num_tad"] for d in detalhes)
        ressalva = _ressalva_geometria(detalhes)
        return {
            "resultado": "excecao", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="geometria do talhao %s (%s, %.2f ha) contra os "
                          "poligonos de termos de embargo do Ibama, medindo a "
                          "distancia em metros em EPSG:31982"
                          % (talhao["nome"], talhao["tipo_geom"],
                             talhao["area_ha"] or 0.0),
                base=base,
                resultado="nao ha interseccao, mas %d termo(s) de embargo "
                          "(TAD %s) estao a menos de %.0f m do talhao - a "
                          "menor distancia e de %.1f m%s"
                          % (len(detalhes), tads, limite_m, minima, ressalva),
                conclusao="caso limitrofe: o talhao encosta em area embargada "
                          "e a precisao da geometria nao permite afirmar que "
                          "esta fora - EXCECAO para conferencia humana em "
                          "campo antes de liberar o lote."),
            "evidencia": {
                "num_tad": [d["num_tad"] for d in detalhes],
                "area_intersecao_ha": 0.0,
                "distancia_minima_m": round(minima, 1),
                "limite_proximidade_m": limite_m,
                "termos": detalhes,
                "cpf_produtor": cpf_produtor,
                "termos_mesmo_cpf": termos_mesmo_cpf,
                "ldi_pa_consultada": False,
                "data_atualizacao_base": data_base_r01(),
                "crs_medicao": CRS_METRICO,
            },
        }

    if termos_mesmo_cpf:
        return _excecao_por_cpf(int(len(vizinhanca)), round(minima, 1))

    return {
        "resultado": "conforme", "perna": perna, "categoria": categoria,
        "fonte": base,
        "texto": montar_laudo(
            comparado="geometria do talhao %s (%s, %.2f ha) contra os "
                      "poligonos de termos de embargo do Ibama, medindo "
                      "interseccao e distancia em EPSG:31982"
                      % (talhao["nome"], talhao["tipo_geom"],
                         talhao["area_ha"] or 0.0),
            base=base,
            resultado="nenhuma interseccao; o embargo mais proximo esta a "
                      "%.1f m, acima do limite de %.0f m" % (minima, limite_m),
            conclusao="talhao livre de embargo do Ibama na data da consulta - "
                      "categoria 2 (protecao ambiental) conforme."),
        "evidencia": {"embargos_avaliados": int(len(vizinhanca)),
                      "distancia_minima_m": round(minima, 1),
                      "limite_proximidade_m": limite_m,
                      "cpf_produtor": cpf_produtor,
                      "termos_mesmo_cpf": [],
                      "ldi_pa_consultada": False,
                      "data_atualizacao_base": data_base_r01()},
    }


def _ressalva_geometria(detalhes: list) -> str:
    """Declara no laudo quando a geometria do embargo e buffer do ponto TAD.

    A base do Ibama traz parte dos termos so com a coordenada do TAD; a
    Trilha 0 reconstruiu um circulo com a area declarada. Isso muda o peso da
    prova e por isso vai escrito no laudo, nunca escondido.
    """
    reconstruidos = [d["num_tad"] for d in detalhes
                     if "buffer" in (d.get("origem_geometria") or "").lower()]
    if not reconstruidos:
        return ""
    return (" [ressalva de procedencia: a geometria do(s) termo(s) %s nao e "
            "poligono oficial - foi reconstruida como circulo a partir do "
            "ponto do TAD e da area embargada declarada, entao o limite tem "
            "incerteza posicional]" % ", ".join(reconstruidos))


# ===========================================================================
# Checagem 03 - CAR e posse (perna B, categoria 1)
# ===========================================================================
def checagem_03(talhao_id: str) -> dict:
    """CAR ativo, geometria compativel e titular coerente.

    O SICAR (ARD R-03) ainda esta 'a descobrir', entao a consulta e feita
    contra o cadastro local do talhao cruzado com os documentos de CAR que a
    Trilha A extraiu. Isso vai declarado no laudo - nao ha consulta online.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["03"]
    base = ("cadastro interno do talhao (`talhao.car_numero` / "
            "`talhao.car_situacao`) cruzado com os documentos de CAR "
            "extraidos pela ingestao; o SICAR nao foi consultado online "
            "(ARD R-03 ainda 'a descobrir')")

    talhao = db.buscar_talhao(talhao_id)
    produtor = db.buscar_produtor(talhao["produtor_id"]) or {}
    documentos = db.listar_documentos(talhao["produtor_id"])
    docs_car = [d for d in documentos
                if d.get("tipo") in ("car_recibo", "car_demonstrativo")]

    achados, evidencia = [], {
        "car_numero": talhao.get("car_numero"),
        "car_situacao": talhao.get("car_situacao"),
        "area_talhao_ha": talhao.get("area_ha"),
        "documentos_car_encontrados": len(docs_car),
    }
    resultado = "conforme"
    severidade = "F"
    # Classificacao da excecao (correcoes-spec_1.md 03): por padrao a ausencia
    # de documento e lacuna que o produtor consegue sanar.
    tipo_excecao = "lacuna_sanavel"

    # (a) CAR informado?
    if not talhao.get("car_numero"):
        resultado = "excecao"
        severidade = "B"
        achados.append("falta o numero do CAR no cadastro deste talhao")

    # (b) situacao do CAR - R29. Cancelado e Suspenso reprovam a camada 1 da
    # aptidao (severidade B). Pendente NAO e falha do produtor: cerca de 0,4%
    # dos imoveis tiveram analise completa em dez anos, e ele nao tem como
    # resolver - por isso severidade F e tipo `nao_sanavel_pelo_produtor`.
    situacao = (talhao.get("car_situacao") or "").strip().lower()
    if situacao in ("cancelado", "suspenso"):
        resultado = "excecao"
        severidade = "B"
        achados.append(
            "o CAR %s registra a condicao '%s'; nessa condicao o cadastro nao "
            "sustenta a camada 1 da aptidao"
            % (talhao.get("car_numero") or "(sem numero)",
               talhao.get("car_situacao")))
    elif situacao == "pendente":
        resultado = "excecao"
        tipo_excecao = "nao_sanavel_pelo_produtor"
        achados.append(
            "o CAR %s esta com analise 'Pendente' no orgao ambiental - a "
            "condicao e registrada com a data da consulta e nao depende de "
            "nenhum documento que o produtor possa apresentar"
            % (talhao.get("car_numero") or "(sem numero)"))
    elif situacao and situacao != "ativo":
        resultado = "excecao"
        achados.append("o CAR registra a condicao '%s', que nao e 'Ativo' "
                       "nem 'Pendente'" % talhao.get("car_situacao"))

    # (c) documento comprobatorio do CAR
    if not docs_car:
        if resultado == "conforme":
            resultado = "excecao"
        severidade = "B"
        achados.append("falta o recibo ou o demonstrativo do CAR de %s"
                       % (produtor.get("nome") or talhao["produtor_id"]))
    else:
        # (d) numero do CAR do documento bate com o do talhao?
        numeros_doc = set()
        for d in docs_car:
            numero = _campo(_campos(d), "numero_car")
            if numero:
                numeros_doc.add(str(numero).strip().upper())
        evidencia["numeros_car_nos_documentos"] = sorted(numeros_doc)
        alvo = str(talhao.get("car_numero") or "").strip().upper()
        if alvo and numeros_doc and alvo not in numeros_doc:
            resultado = "excecao"
            severidade = "B"
            achados.append(
                "o CAR do talhao (%s) nao aparece em nenhum documento de CAR "
                "entregue (os documentos trazem: %s) - falta o recibo do CAR "
                "que corresponde a este talhao"
                % (alvo, ", ".join(sorted(numeros_doc))))

        # (e) titular coerente - divergencia de titular e excecao pelo SPEC
        cpf_produtor = _digitos(produtor.get("cpf"))
        for d in docs_car:
            campos = _campos(d)
            cpf_doc = _digitos(_campo(campos, "cpf_titular"))
            if cpf_produtor and cpf_doc and cpf_doc != cpf_produtor:
                resultado = "excecao"
                severidade = "B"
                achados.append(
                    "o CPF do titular no documento de CAR '%s' (%s) difere do "
                    "CPF cadastrado para %s (%s)"
                    % (d.get("arquivo_origem"), _campo(campos, "cpf_titular"),
                       produtor.get("nome"), produtor.get("cpf")))
            # (f) area do CAR menor que a area do talhao
            # so compara area com o documento que se refere a ESTE talhao
            area_car = (_num(_campo(campos, "area_ha"))
                        if _cita_talhao(d, talhao) else None)
            area_talhao = _num(talhao.get("area_ha"))
            if area_car and area_talhao and area_talhao > area_car * 1.02:
                resultado = "excecao"
                achados.append(
                    "a area do talhao (%.2f ha) e maior que a area do imovel "
                    "declarada no CAR '%s' (%.2f ha)"
                    % (area_talhao, d.get("arquivo_origem"), area_car))

    # Se ha mais de um achado, a excecao deixa de ser "so o CAR pendente" e
    # volta a ser lacuna que o produtor pode sanar.
    if tipo_excecao == "nao_sanavel_pelo_produtor" and len(achados) > 1:
        tipo_excecao = "lacuna_sanavel"
    evidencia["achados"] = achados
    evidencia["severidade"] = severidade
    evidencia["r29_condicao_car"] = talhao.get("car_situacao")
    if resultado == "conforme":
        texto = montar_laudo(
            comparado="numero e situacao do CAR do talhao %s, area cadastrada "
                      "(%.2f ha) e CPF do titular contra os %d documento(s) "
                      "de CAR do produtor %s"
                      % (talhao["nome"], talhao.get("area_ha") or 0.0,
                         len(docs_car), produtor.get("nome") or "?"),
            base=base,
            resultado="CAR %s com situacao '%s', titular coerente com o "
                      "produtor e area compativel"
                      % (talhao.get("car_numero"), talhao.get("car_situacao")),
            conclusao="direito de uso da terra sustentado pelo CAR na data da "
                      "consulta - categoria 1 conforme, sujeita a confirmacao "
                      "no SICAR quando o recurso R-03 for habilitado.")
    else:
        texto = montar_laudo(
            comparado="numero e situacao do CAR do talhao %s, area cadastrada "
                      "(%.2f ha) e CPF do titular contra os %d documento(s) "
                      "de CAR do produtor %s"
                      % (talhao["nome"], talhao.get("area_ha") or 0.0,
                         len(docs_car), produtor.get("nome") or "?"),
            base=base,
            resultado="%d ponto(s) a resolver na documentacao: %s"
                      % (len(achados), "; ".join(achados)),
            conclusao="o vinculo entre o talhao, o CAR e o titular ainda nao "
                      "esta documentado - EXCECAO registrada para que os "
                      "papeis faltantes sejam reunidos antes do embarque.")
    return {"resultado": resultado, "perna": perna, "categoria": categoria,
            "severidade": severidade, "tipo_excecao": tipo_excecao,
            "fonte": base, "texto": texto, "evidencia": evidencia}


# ===========================================================================
# Checagem 04 - Sobreposicao de direitos (perna B, categorias 4 e 7)
# ===========================================================================
# Rebaixamento por categoria da area, direto do contrato v2 (tabela das nove
# regras B). Categoria nao informada nao rebaixa: na duvida, fica em B e o
# humano decide - nenhuma severidade e afrouxada por falta de dado.
CATEGORIAS_AREA_F = {
    # R18 - TI: so homologada ou regularizada e B; o resto e flag
    "terra_indigena": ("delimitada", "declarada", "em_estudo",
                       "identificada"),
    # R19 - UC: protecao integral e B; uso sustentavel e flag
    "unidade_conservacao": ("uso_sustentavel",),
    # quilombo: titulo constituido e B; processo em curso e flag
    "territorio_quilombola": ("em_processo", "em_estudo"),
}


def _severidade_area_protegida(tipo_area: str, categoria_area: str) -> str:
    """'B' ou 'F' conforme a categoria da area sobreposta (contrato v2)."""
    tipo = (tipo_area or "").strip().lower()
    categoria = (categoria_area or "").strip().lower()
    return "F" if categoria in CATEGORIAS_AREA_F.get(tipo, ()) else "B"


def checagem_04(talhao_id: str) -> dict:
    """Interseccao com terra indigena, territorio quilombola ou UC.

    Camada SEMEADA - ARD R-04 (FUNAI), R-05 (INCRA) e R-06 (CNUC) ainda estao
    'a descobrir'. Declarado no laudo, conforme ADR-012.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["04"]
    base = ("camada de areas protegidas `%s` (terra indigena, territorio "
            "quilombola e unidade de conservacao) - %s"
            % (ARQUIVO_PROTEGIDAS_SEMEADO.name, FONTE_SEMEADA))

    talhao = db.buscar_talhao(talhao_id)
    alvo = _gdf_talhao(talhao)
    if alvo is None:
        return _sem_geometria("04", perna, categoria, talhao_id, base)

    protegidas = carregar_protegidas()
    tocadas = gpd.sjoin(protegidas, alvo, how="inner", predicate="intersects")

    if tocadas.empty:
        return {
            "resultado": "conforme", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="poligono do talhao %s (%s, %.2f ha) contra os "
                          "limites de terras indigenas, territorios "
                          "quilombolas e unidades de conservacao"
                          % (talhao["nome"], talhao["tipo_geom"],
                             talhao["area_ha"] or 0.0),
                base=base,
                resultado="nenhuma sobreposicao com area de direito de "
                          "terceiros",
                conclusao="nao ha indicio de conflito com direitos de "
                          "terceiros nem gatilho de consulta previa (FPIC) - "
                          "categorias 4 e 7 conformes, ressalvado que a "
                          "camada usada e semeada e nao substitui FUNAI, "
                          "INCRA e CNUC."),
            "evidencia": {"areas_intersectadas": 0, "fonte_camada": "SEMEADO"},
        }

    alvo_m = alvo.to_crs(CRS_METRICO)
    geom_m = alvo_m.geometry.iloc[0]
    detalhes = []
    for _, linha in tocadas.iterrows():
        try:
            recorte = gpd.GeoSeries([linha.geometry], crs=geo.CRS_PADRAO) \
                .to_crs(CRS_METRICO).iloc[0]
            area = float(recorte.intersection(geom_m).area)
        except Exception:
            area = 0.0
        categoria_area = str(linha.get("categoria_area") or "").strip().lower()
        detalhes.append({
            "id_area": str(linha.get("id_area")),
            "tipo_area": str(linha.get("tipo_area")),
            "categoria_area": categoria_area or "nao_informada",
            "nome_area": str(linha.get("nome_area")),
            "orgao": str(linha.get("orgao")),
            "area_intersecao_ha": round(area / 10000.0, 4),
            "severidade_regra": _severidade_area_protegida(
                str(linha.get("tipo_area")), categoria_area),
            "fonte_camada": "SEMEADO",
        })
    tipos = sorted({d["tipo_area"] for d in detalhes})
    # O rebaixamento e POR AREA, com a categoria de cada uma (contrato v2):
    #   R18 - TI homologada/regularizada = B; delimitada/declarada = F
    #   R19 - UC de protecao integral    = B; uso sustentavel      = F
    # Quilombo titulado e direito territorial constituido = B.
    grave = any(d["severidade_regra"] == "B" for d in detalhes)
    resultado = "bloqueio" if grave else "excecao"
    severidade = "B" if grave else "F"
    area_total = sum(d["area_intersecao_ha"] for d in detalhes)
    nomes = ", ".join("%s (%s, categoria %s, severidade %s)"
                      % (d["nome_area"], d["tipo_area"], d["categoria_area"],
                         d["severidade_regra"])
                      for d in detalhes)
    return {
        "resultado": resultado, "perna": perna, "categoria": categoria,
        "severidade": severidade, "fonte": base,
        "texto": montar_laudo(
            comparado="poligono do talhao %s (%s, %.2f ha) contra os limites "
                      "de terras indigenas, territorios quilombolas e "
                      "unidades de conservacao"
                      % (talhao["nome"], talhao["tipo_geom"],
                         talhao["area_ha"] or 0.0),
            base=base,
            resultado="o talhao sobrepoe %d area(s) de direito de terceiros - "
                      "%s - somando %.4f ha de area comum"
                      % (len(detalhes), nomes, area_total),
            conclusao=("plantio dentro de area cuja categoria ja constitui "
                       "direito de terceiro ou protecao integral (R18 de TI "
                       "homologada/regularizada, R19 de UC de protecao "
                       "integral ou quilombo titulado): talhao BLOQUEADO ate "
                       "manifestacao do orgao competente e consulta livre, "
                       "previa e informada (FPIC)."
                       if grave else
                       "a sobreposicao e com area de categoria que admite uso "
                       "regulado (TI apenas delimitada/declarada, UC de uso "
                       "sustentavel ou quilombo em processo): rebaixa para "
                       "severidade F e exige conferir plano de manejo, CDRU "
                       "ou autorizacao de uso - EXCECAO para analise "
                       "humana.")),
        "evidencia": {"areas": detalhes, "tipos": tipos,
                      "area_intersecao_total_ha": round(area_total, 4),
                      "fonte_camada": "SEMEADO"},
    }


# ===========================================================================
# Checagem 05 - Consistencia documental (perna B, transversal) - a joia
# ===========================================================================
# Cada regra e uma funcao separada e numerada, recebe o contexto do produtor
# e devolve {resultado, texto, evidencia}. O texto diz, em portugues claro,
# QUAL documento conflita com QUAL - e lido por um auditor no dossie.
#
# Contexto (dict) que toda regra recebe:
#   produtor, talhao, documentos (lista), por_tipo (dict tipo -> lista),
#   lotes (lotes do talhao), params

def _ctx_documental(talhao_id: str, delegadas: dict = None) -> dict:
    """Contexto das regras. `delegadas` traz o resultado ja calculado das
    checagens geoespaciais (01, 02, 03, 04, 07) para que as regras R13, R16,
    R17, R18, R19, R29 e R08 registrem o achado SEM refazer o processamento
    geometrico - a orientacao da spec v2 e nao duplicar trabalho."""
    talhao = db.buscar_talhao(talhao_id)
    produtor = db.buscar_produtor(talhao["produtor_id"]) or {}
    documentos = db.listar_documentos(talhao["produtor_id"])
    por_tipo = {}
    for d in documentos:
        por_tipo.setdefault(d.get("tipo") or "desconhecido", []).append(d)
    return {"talhao": talhao, "produtor": produtor, "documentos": documentos,
            "por_tipo": por_tipo, "lotes": db.lotes_do_talhao(talhao_id),
            "delegadas": delegadas or {}, "params": carregar_params()}


def _ok(texto: str, evidencia: dict = None) -> dict:
    return {"resultado": "conforme", "texto": texto,
            "evidencia": evidencia or {}}


def _falha(texto: str, evidencia: dict = None,
           resultado: str = "excecao") -> dict:
    return {"resultado": resultado, "texto": texto,
            "evidencia": evidencia or {}}


def regra_01_cpf_car_vs_nota(ctx: dict) -> dict:
    """R01 - CPF do CAR diferente do CPF da nota fiscal do produtor."""
    cars = ctx["por_tipo"].get("car_recibo", [])
    notas = ctx["por_tipo"].get("nota_fiscal_produtor", [])
    if not cars or not notas:
        return _ok("R01 nao avaliada: o produtor nao tem ao mesmo tempo recibo "
                   "de CAR e nota fiscal de produtor para cruzar.",
                   {"cars": len(cars), "notas": len(notas)})
    conflitos = []
    for car in cars:
        cpf_car = _digitos(_campo(_campos(car), "cpf_titular"))
        if not cpf_car:
            continue
        for nota in notas:
            cpf_nota = _digitos(_campo(_campos(nota), "cpf_emitente"))
            if cpf_nota and cpf_nota != cpf_car:
                conflitos.append({
                    "documento_car": car.get("arquivo_origem"),
                    "cpf_no_car": _campo(_campos(car), "cpf_titular"),
                    "documento_nota": nota.get("arquivo_origem"),
                    "cpf_na_nota": _campo(_campos(nota), "cpf_emitente"),
                    "documento_id_car": car.get("id"),
                    "documento_id_nota": nota.get("id")})
    if not conflitos:
        return _ok("R01 conforme: o CPF do titular do CAR e o CPF do emitente "
                   "das notas fiscais coincidem.", {"conflitos": 0})
    frases = ["o recibo de CAR '%s' esta no CPF %s, mas a nota fiscal de "
              "produtor '%s' foi emitida pelo CPF %s"
              % (c["documento_car"], c["cpf_no_car"], c["documento_nota"],
                 c["cpf_na_nota"]) for c in conflitos]
    return _falha("R01 - titularidade divergente entre CAR e nota fiscal: %s. "
                  "O cacau esta sendo vendido por pessoa diferente da que "
                  "responde pelo imovel." % "; ".join(frases),
                  {"conflitos": conflitos})


def regra_02_area_talhao_vs_car(ctx: dict) -> dict:
    """R11 - Area declarada no talhao maior que a area do CAR."""
    area_talhao = _num(ctx["talhao"].get("area_ha"))
    fontes = []
    for tipo in ("car_recibo", "car_demonstrativo", "ccir", "sigef"):
        for d in ctx["por_tipo"].get(tipo, []):
            # apenas documentos que se referem a ESTE talhao: a ingestao grava
            # um documento por talhao, entao comparar com o documento de outro
            # talhao do mesmo produtor produziria divergencia falsa
            if not _cita_talhao(d, ctx["talhao"]):
                continue
            area = _num(_campo(_campos(d), "area_ha"))
            if area:
                fontes.append((tipo, d, area))
    if not area_talhao or not fontes:
        return _ok("R11 nao avaliada: nao ha area de imovel declarada em "
                   "documento de CAR, CCIR ou SIGEF para comparar com a area "
                   "do talhao.", {"area_talhao_ha": area_talhao,
                                  "fontes": len(fontes)})
    conflitos = [{"tipo_documento": t, "documento": d.get("arquivo_origem"),
                  "documento_id": d.get("id"), "area_documento_ha": a,
                  "area_talhao_ha": area_talhao}
                 for t, d, a in fontes if area_talhao > a * 1.02]
    if not conflitos:
        return _ok("R11 conforme: a area do talhao (%.2f ha) cabe dentro da "
                   "area do imovel declarada nos documentos."
                   % area_talhao, {"area_talhao_ha": area_talhao})
    frases = ["o talhao %s declara %.2f ha, mas o documento '%s' (%s) declara "
              "apenas %.2f ha para o imovel"
              % (ctx["talhao"]["nome"], c["area_talhao_ha"], c["documento"],
                 c["tipo_documento"], c["area_documento_ha"])
              for c in conflitos]
    return _falha("R11 - area incompativel: %s. A area produtiva informada nao "
                  "cabe no imovel cadastrado." % "; ".join(frases),
                  {"conflitos": conflitos})


def regra_03_vencido_no_embarque(ctx: dict) -> dict:
    """R31 - Documento vencido na data prevista de embarque do lote."""
    if not ctx["lotes"]:
        return _ok("R31 nao avaliada: o talhao nao esta alocado a nenhum lote "
                   "com data de embarque prevista.", {})
    vencidos = []
    for lote in ctx["lotes"]:
        embarque = _data(lote.get("data_embarque"))
        if not embarque:
            continue
        for d in ctx["documentos"]:
            if d.get("tipo") in ("desconhecido", "nao_documento"):
                continue
            validade = _data(d.get("data_validade"))
            if validade and validade < embarque:
                vencidos.append({
                    "documento": d.get("arquivo_origem"),
                    "documento_id": d.get("id"),
                    "tipo": d.get("tipo"),
                    "data_validade": d.get("data_validade"),
                    "lote": lote.get("codigo"),
                    "data_embarque": lote.get("data_embarque"),
                    "dias_de_atraso": (embarque - validade).days})
    if not vencidos:
        return _ok("R31 conforme: todos os documentos com validade seguem "
                   "vigentes nas datas de embarque previstas dos lotes.",
                   {"lotes_avaliados": len(ctx["lotes"])})
    frases = ["o documento '%s' (%s) vence em %s, %d dias antes do embarque "
              "do lote %s previsto para %s"
              % (v["documento"], v["tipo"], v["data_validade"],
                 v["dias_de_atraso"], v["lote"], v["data_embarque"])
              for v in vencidos]
    return _falha("R31 - documento vencido no embarque: %s. O lote sairia com "
                  "documentacao expirada." % "; ".join(frases),
                  {"conflitos": vencidos})


def regra_04_municipio_matricula_vs_car(ctx: dict) -> dict:
    """R21 - Municipio da matricula diferente do municipio do CAR."""
    matriculas = ctx["por_tipo"].get("matricula_imovel", [])
    cars = ctx["por_tipo"].get("car_recibo", [])
    if not matriculas or not cars:
        return _ok("R21 nao avaliada: falta matricula do imovel ou recibo de "
                   "CAR para comparar o municipio.",
                   {"matriculas": len(matriculas), "cars": len(cars)})
    conflitos = []
    for m in matriculas:
        mun_m = _normalizar_nome(_campo(_campos(m), "municipio"))
        if not mun_m:
            continue
        for c in cars:
            mun_c = _normalizar_nome(_campo(_campos(c), "municipio"))
            if mun_c and mun_c != mun_m:
                conflitos.append({
                    "documento_matricula": m.get("arquivo_origem"),
                    "municipio_matricula": _campo(_campos(m), "municipio"),
                    "documento_car": c.get("arquivo_origem"),
                    "municipio_car": _campo(_campos(c), "municipio"),
                    "documento_id_matricula": m.get("id"),
                    "documento_id_car": c.get("id")})
    if not conflitos:
        return _ok("R21 conforme: matricula e CAR apontam para o mesmo "
                   "municipio.", {"conflitos": 0})
    frases = ["a matricula '%s' registra o imovel em %s, enquanto o recibo de "
              "CAR '%s' registra em %s"
              % (c["documento_matricula"], c["municipio_matricula"],
                 c["documento_car"], c["municipio_car"]) for c in conflitos]
    return _falha("R21 - municipio divergente entre matricula e CAR: %s. Os "
                  "dois documentos podem nao se referir ao mesmo imovel."
                  % "; ".join(frases), {"conflitos": conflitos})


def regra_05_titular_arrendamento(ctx: dict) -> dict:
    """R22 - Titular do arrendamento diferente do produtor do grupo."""
    contratos = ctx["por_tipo"].get("contrato_arrendamento", [])
    if not contratos:
        return _ok("R22 nao avaliada: o produtor nao apresentou contrato de "
                   "arrendamento, parceria ou comodato.", {})
    nome_produtor = _normalizar_nome(ctx["produtor"].get("nome"))
    conflitos = []
    for c in contratos:
        arrendatario = _campo(_campos(c), "arrendatario")
        alvo = _normalizar_nome(arrendatario)
        if alvo and nome_produtor and alvo != nome_produtor:
            conflitos.append({"documento": c.get("arquivo_origem"),
                              "documento_id": c.get("id"),
                              "arrendatario_no_contrato": arrendatario,
                              "produtor_do_grupo": ctx["produtor"].get("nome")})
    if not conflitos:
        return _ok("R22 conforme: o arrendatario do contrato e o proprio "
                   "produtor do grupo.", {"contratos": len(contratos)})
    frases = ["o contrato '%s' tem como arrendatario '%s', mas os arquivos "
              "foram entregues no grupo do produtor '%s'"
              % (c["documento"], c["arrendatario_no_contrato"],
                 c["produtor_do_grupo"]) for c in conflitos]
    return _falha("R22 - arrendatario divergente: %s. Quem detem o direito de "
                  "uso da terra nao e quem esta vendendo a producao."
                  % "; ".join(frases), {"conflitos": conflitos})


def regra_06_conjunto_minimo(ctx: dict) -> dict:
    """R48 - Documento do conjunto minimo ausente."""
    minimo = ctx["params"].get("conjunto_minimo", {})
    obrigatorios = minimo.get("obrigatorios", [])
    grupos_um_de = minimo.get("um_de", [])
    tipos_disponiveis = {t for t, lista in ctx["por_tipo"].items() if lista}
    nomes = {chave: valor.get("nome", chave)
             for chave, valor in ctx["params"].get("tipos", {}).items()}

    faltando = [t for t in obrigatorios if t not in tipos_disponiveis]
    grupos_vazios = []
    for grupo in grupos_um_de:
        if not any(t in tipos_disponiveis for t in grupo):
            grupos_vazios.append(grupo)

    if not faltando and not grupos_vazios:
        return _ok("R48 conforme: o produtor tem todos os documentos do "
                   "conjunto minimo de `params/cacau.yml`.",
                   {"tipos_presentes": sorted(tipos_disponiveis)})

    partes = []
    if faltando:
        partes.append("faltam os documentos obrigatorios: %s"
                      % ", ".join(nomes.get(t, t) for t in faltando))
    for grupo in grupos_vazios:
        partes.append("nao foi apresentado nenhum documento de posse dentre "
                      "%s" % " / ".join(nomes.get(t, t) for t in grupo))
    total = len(ctx["documentos"])
    return _falha(
        "R48 - lacuna no conjunto minimo de %s (%d documento(s) processado(s) "
        "no total): %s. Sao os papeis que ainda faltam reunir para o lote "
        "fechar - a pendencia e do documento, nao da pessoa."
        % (ctx["produtor"].get("nome") or "?", total, "; ".join(partes)),
        {"faltando": faltando, "grupos_sem_documento": grupos_vazios,
         "documentos_do_produtor": total,
         "tipos_presentes": sorted(tipos_disponiveis)})


def regra_07_duplicidade_suspeita(ctx: dict) -> dict:
    """R46 - Dois documentos do mesmo tipo, numeros diferentes, datas proximas.

    `nota_fiscal_produtor` e `due_embarque` tem `multiplo_esperado: true` em
    params/cacau.yml: ter varias e o normal, entao esses tipos nao disparam a
    regra so por quantidade. Para eles, a suspeita e outra - mesmo numero
    repetido, tratada na regra R45.
    """
    tipos_param = ctx["params"].get("tipos", {})
    janela_dias = 30
    conflitos = []
    for tipo, docs in ctx["por_tipo"].items():
        if tipo in ("desconhecido", "nao_documento") or len(docs) < 2:
            continue
        if tipos_param.get(tipo, {}).get("multiplo_esperado"):
            continue  # multiplo e esperado: nao dispara por haver varios
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                a, b = docs[i], docs[j]
                num_a = str(_campo(_campos(a), "numero")
                            or "").strip()
                num_b = str(_campo(_campos(b), "numero")
                            or "").strip()
                if not num_a or not num_b or num_a == num_b:
                    continue
                da, dbb = _data(a.get("data_emissao")), _data(b.get(
                    "data_emissao"))
                if da and dbb and abs((da - dbb).days) > janela_dias:
                    continue
                conflitos.append({
                    "tipo": tipo,
                    "documento_a": a.get("arquivo_origem"), "numero_a": num_a,
                    "data_a": a.get("data_emissao"),
                    "documento_b": b.get("arquivo_origem"), "numero_b": num_b,
                    "data_b": b.get("data_emissao"),
                    "documento_id_a": a.get("id"), "documento_id_b": b.get("id")})
    if not conflitos:
        return _ok("R46 conforme: nao ha dois documentos do mesmo tipo unico "
                   "com numeros diferentes emitidos em datas proximas.",
                   {"janela_dias": janela_dias})
    nomes = {c: v.get("nome", c) for c, v in tipos_param.items()}
    frases = ["'%s' (numero %s, emitido em %s) e '%s' (numero %s, emitido em "
              "%s) sao ambos do tipo %s"
              % (c["documento_a"], c["numero_a"], c["data_a"],
                 c["documento_b"], c["numero_b"], c["data_b"],
                 nomes.get(c["tipo"], c["tipo"])) for c in conflitos]
    return _falha("R46 - duplicidade suspeita: %s. Documentos de tipo unico "
                  "com numeros diferentes e datas proximas indicam via "
                  "substituida, retificacao nao informada ou documento "
                  "montado." % "; ".join(frases), {"conflitos": conflitos})


# --- regras adicionais (SPEC 4.2: "regras adicionais valem ponto") ---------
def regra_08_nome_divergente_mesmo_cpf(ctx: dict) -> dict:
    """R09 - Nomes de titular diferentes associados ao mesmo CPF."""
    por_cpf = {}
    for d in ctx["documentos"]:
        campos = _campos(d)
        cpf = _digitos(_campo(campos, "cpf_titular"))
        nome = _campo(campos, "proprietario")
        if cpf and nome:
            por_cpf.setdefault(cpf, []).append((_normalizar_nome(nome), nome, d))
    conflitos = []
    for cpf, itens in por_cpf.items():
        distintos = {n for n, _, _ in itens}
        if len(distintos) > 1:
            conflitos.append({
                "cpf": cpf,
                "nomes": sorted({bruto for _, bruto, _ in itens}),
                "documentos": [d.get("arquivo_origem") for _, _, d in itens]})
    if not conflitos:
        return _ok("R09 conforme: cada CPF aparece sempre com o mesmo nome de "
                   "titular nos documentos.", {})
    frases = ["o CPF %s aparece com os nomes %s nos documentos %s"
              % (c["cpf"], " e ".join(c["nomes"]), ", ".join(c["documentos"]))
              for c in conflitos]
    return _falha("R09 - mesmo CPF com titulares de nomes diferentes: %s. Ha "
                  "erro de digitacao ou tentativa de mascarar a titularidade."
                  % "; ".join(frases), {"conflitos": conflitos})


def regra_09_area_divergente_entre_documentos(ctx: dict) -> dict:
    """R12 - Area do mesmo talhao declarada com valores diferentes em
    documentos distintos.

    A ingestao grava um documento por talhao (campo `talhao_citado`), entao da
    para confrontar CAR, CCIR, SIGEF e matricula que falam do MESMO talhao.
    Se cada um declara uma area, os documentos nao descrevem o mesmo imovel.
    """
    talhao = ctx["talhao"]
    declaracoes = []
    for tipo in ("car_recibo", "car_demonstrativo", "ccir", "sigef",
                 "matricula_imovel", "itr"):
        for d in ctx["por_tipo"].get(tipo, []):
            if not _cita_talhao(d, talhao):
                continue
            area = _num(_campo(_campos(d), "area_ha"))
            if area:
                declaracoes.append((tipo, d, area))
    if len(declaracoes) < 2:
        return _ok("R12 nao avaliada: ha menos de dois documentos declarando a "
                   "area do imovel do talhao %s." % talhao["nome"],
                   {"declaracoes": len(declaracoes)})
    menor = min(a for _, _, a in declaracoes)
    maior = max(a for _, _, a in declaracoes)
    if maior <= menor * 1.05:      # tolerancia de 5% para arredondamento
        return _ok("R12 conforme: os %d documentos que declaram a area do "
                   "imovel do talhao %s convergem (%.2f a %.2f ha)."
                   % (len(declaracoes), talhao["nome"], menor, maior),
                   {"area_minima_ha": menor, "area_maxima_ha": maior})
    detalhe = [{"tipo": t, "documento": d.get("arquivo_origem"),
                "documento_id": d.get("id"), "area_ha": a}
               for t, d, a in declaracoes]
    frases = ["'%s' (%s) declara %.2f ha" % (x["documento"], x["tipo"],
                                             x["area_ha"]) for x in detalhe]
    return _falha(
        "R12 - area do imovel divergente entre documentos do talhao %s: %s. "
        "Uma diferenca de %.2f ha entre documentos do mesmo imovel indica que "
        "eles nao se referem a mesma area."
        % (talhao["nome"], "; ".join(frases), maior - menor),
        {"declaracoes": detalhe, "diferenca_ha": round(maior - menor, 2)})


def regra_10_emissao_depois_da_validade(ctx: dict) -> dict:
    """R32 - Data de emissao posterior a data de validade."""
    conflitos = []
    for d in ctx["documentos"]:
        emissao, validade = _data(d.get("data_emissao")), _data(
            d.get("data_validade"))
        if emissao and validade and emissao > validade:
            conflitos.append({"documento": d.get("arquivo_origem"),
                              "documento_id": d.get("id"),
                              "tipo": d.get("tipo"),
                              "data_emissao": d.get("data_emissao"),
                              "data_validade": d.get("data_validade")})
    if not conflitos:
        return _ok("R32 conforme: nenhum documento foi emitido depois da "
                   "propria data de validade.", {})
    frases = ["o documento '%s' (%s) consta emitido em %s, depois da propria "
              "validade em %s" % (c["documento"], c["tipo"],
                                  c["data_emissao"], c["data_validade"])
              for c in conflitos]
    return _falha("R32 - datas impossiveis: %s. O documento e internamente "
                  "inconsistente e nao serve como prova."
                  % "; ".join(frases), {"conflitos": conflitos})


def regra_11_nota_repetida(ctx: dict) -> dict:
    """R45 - Mesmo numero de nota fiscal repetido (tipo de multiplo esperado).

    Complementa a R46: para `nota_fiscal_produtor` o problema nunca e haver
    varias, e sim a mesma nota aparecer duas vezes, o que dobraria o volume.
    """
    notas = ctx["por_tipo"].get("nota_fiscal_produtor", [])
    if len(notas) < 2:
        return _ok("R45 nao avaliada: o produtor tem %d nota(s) fiscal(is), "
                   "insuficiente para checar repeticao." % len(notas), {})
    por_numero = {}
    for n in notas:
        campos = _campos(n)
        chave = "%s/%s" % (str(_campo(campos, "numero") or "").strip(),
                           str(_campo(campos, "serie") or "").strip())
        if chave.strip("/"):
            por_numero.setdefault(chave, []).append(n)
    repetidas = {k: v for k, v in por_numero.items() if len(v) > 1}
    if not repetidas:
        return _ok("R45 conforme: as %d notas fiscais do produtor tem numeros "
                   "distintos, como esperado de um tipo multiplo."
                   % len(notas), {"notas": len(notas)})
    frases = ["a nota numero %s aparece em %s"
              % (k, " e ".join("'%s'" % d.get("arquivo_origem") for d in v))
              for k, v in repetidas.items()]
    return _falha("R45 - nota fiscal repetida: %s. A mesma venda pode estar "
                  "sendo contada duas vezes no volume do lote."
                  % "; ".join(frases),
                  {"repetidas": {k: [d.get("id") for d in v]
                                 for k, v in repetidas.items()}})


def regra_12_documento_ilegivel_ou_divergente(ctx: dict) -> dict:
    """R47 - Documento do conjunto minimo marcado pela ingestao como ilegivel
    ou divergente.

    Nao inclui 'vencido' - isso e a R31, e repetir viraria ruido na fila de
    excecoes. Tambem ignora arquivo que nao e documento (foto, tipo
    desconhecido): esses aparecem no mapa de lacunas da ingestao, nao aqui.
    """
    minimo = ctx["params"].get("conjunto_minimo", {})
    relevantes = set(minimo.get("obrigatorios", []))
    for grupo in minimo.get("um_de", []):
        relevantes.update(grupo)
    problemas = [d for d in ctx["documentos"]
                 if d.get("status") in ("ilegivel", "divergente")
                 and d.get("tipo") in relevantes]
    if not problemas:
        return _ok("R47 conforme: nenhum documento do conjunto minimo deste "
                   "produtor ficou ilegivel ou divergente na ingestao.",
                   {"tipos_relevantes": sorted(relevantes)})
    por_status = {}
    for d in problemas:
        por_status.setdefault(d["status"], []).append(
            "%s (%s)" % (d.get("arquivo_origem"), d.get("tipo")))
    frases = ["%d documento(s) com status '%s': %s"
              % (len(v), k, ", ".join(v)) for k, v in por_status.items()]
    return _falha("R47 - documento essencial sem valor probatorio: %s. A prova "
                  "documental do produtor %s esta comprometida enquanto esses "
                  "arquivos nao forem substituidos."
                  % ("; ".join(frases), ctx["produtor"].get("nome") or "?"),
                  {"por_status": por_status,
                   "documento_ids": [d.get("id") for d in problemas]})


def regra_13_vigencia_nao_cobre_safra(ctx: dict) -> dict:
    """R33 - Contrato cuja vigencia nao cobre a data de embarque do lote."""
    contratos = ctx["por_tipo"].get("contrato_arrendamento", [])
    if not contratos or not ctx["lotes"]:
        return _ok("R33 nao avaliada: sem contrato de arrendamento ou sem "
                   "lote com data de embarque para confrontar.", {})
    conflitos = []
    for c in contratos:
        campos = _campos(c)
        inicio, fim = _data(_campo(campos, "vigencia_inicio")), _data(
            _campo(campos, "vigencia_fim"))
        for lote in ctx["lotes"]:
            embarque = _data(lote.get("data_embarque"))
            if not embarque:
                continue
            if (inicio and embarque < inicio) or (fim and embarque > fim):
                conflitos.append({
                    "documento": c.get("arquivo_origem"),
                    "documento_id": c.get("id"),
                    "vigencia": "%s a %s" % (_campo(campos, "vigencia_inicio"),
                                             _campo(campos, "vigencia_fim")),
                    "lote": lote.get("codigo"),
                    "data_embarque": lote.get("data_embarque")})
    if not conflitos:
        return _ok("R33 conforme: a vigencia dos contratos cobre as datas de "
                   "embarque dos lotes do talhao.", {})
    frases = ["o contrato '%s' vigora de %s, mas o lote %s embarca em %s"
              % (c["documento"], c["vigencia"], c["lote"], c["data_embarque"])
              for c in conflitos]
    return _falha("R33 - vigencia fora do periodo de producao: %s. No momento "
                  "do embarque o direito de uso da terra nao estaria vigente."
                  % "; ".join(frases), {"conflitos": conflitos})


def regra_14_car_situacao(ctx: dict) -> dict:
    """R29 - CAR com situacao diferente de ativo no demonstrativo."""
    demos = ctx["por_tipo"].get("car_demonstrativo", [])
    situacao_talhao = (ctx["talhao"].get("car_situacao") or "").strip().lower()
    conflitos = []
    if situacao_talhao and situacao_talhao != "ativo":
        conflitos.append({"origem": "cadastro do talhao",
                          "referencia": ctx["talhao"]["nome"],
                          "situacao": ctx["talhao"].get("car_situacao")})
    for d in demos:
        situacao = str(_campo(_campos(d), "situacao") or "").strip()
        if situacao and situacao.lower() != "ativo":
            conflitos.append({"origem": "demonstrativo do CAR",
                              "referencia": d.get("arquivo_origem"),
                              "documento_id": d.get("id"),
                              "situacao": situacao})
    if not conflitos:
        return _ok("R29 conforme: o CAR consta como ativo tanto no cadastro "
                   "do talhao quanto no demonstrativo.", {})
    frases = ["%s (%s) registra a situacao do CAR como '%s'"
              % (c["origem"], c["referencia"], c["situacao"])
              for c in conflitos]
    return _falha("R29 - CAR sem situacao ativa: %s. Um CAR suspenso ou "
                  "cancelado nao comprova regularidade ambiental."
                  % "; ".join(frases), {"conflitos": conflitos})


# ---------------------------------------------------------------------------
# Regras novas da spec v2: as que faltavam para fechar as NOVE obrigatorias
# ---------------------------------------------------------------------------
def _delegada(ctx: dict, codigo_checagem: str, codigo_regra: str,
              titulo: str) -> dict:
    """Registra o resultado de uma checagem geoespacial como resultado de uma
    regra da 05, SEM refazer o processamento.

    As regras R13, R16, R17, R18 e R19 sao geometricas e ja foram calculadas
    pelas checagens 03, 02, 01 e 04. Reprocessar aqui seria pagar duas vezes o
    mesmo sjoin e, pior, abrir espaco para os dois caminhos divergirem.
    """
    fonte = ctx["delegadas"].get(codigo_checagem)
    if not fonte:
        return _ok("%s nao avaliada: a checagem %s nao rodou nesta execucao, "
                   "entao nao ha resultado geoespacial a registrar."
                   % (codigo_regra, codigo_checagem),
                   {"delegada_a": codigo_checagem})
    resultado = fonte.get("resultado", "conforme")
    texto = ("%s (%s) - resultado registrado a partir da checagem %s, sem "
             "reprocessamento: %s. %s"
             % (codigo_regra, titulo, codigo_checagem, resultado.upper(),
                fonte.get("texto", "")))
    evidencia = {"delegada_a": codigo_checagem,
                 "resultado_da_checagem": resultado,
                 "evidencia_da_checagem": fonte.get("evidencia", {})}
    if resultado == "conforme":
        return _ok(texto, evidencia)
    return _falha(texto, evidencia, resultado="excecao")


def regra_r13_talhao_dentro_do_car(ctx: dict) -> dict:
    """R13 - Poligono do talhao nao contido no perimetro do CAR declarado.

    Delegada a checagem 03, que e quem confronta talhao, CAR e titular.
    """
    return _delegada(ctx, "03", "R13",
                     "talhao contido no perimetro do CAR declarado")


def regra_r16_embargo(ctx: dict) -> dict:
    """R16 - Poligono intersecta area embargada (Ibama ou LDI-PA).

    Quando a checagem 02 acha embargo pelo CPF do produtor SEM interseccao
    geometrica, o achado continua sendo registrado - mas com severidade F:
    a R16 e sobre o poligono, e o embargo em nome do produtor sobre outra
    area nao bloqueia a aptidao deste talhao, sinaliza revisao.
    """
    fonte = ctx["delegadas"].get("02") or {}
    evidencia = fonte.get("evidencia", {})
    saida = _delegada(ctx, "02", "R16", "interseccao com area embargada")
    if evidencia.get("motivo_excecao") == "match_por_cpf_sem_intersecao":
        saida["severidade"] = "F"
        saida["evidencia"]["rebaixada_para_f"] = (
            "embargo encontrado pelo CPF do produtor, em outra area, sem "
            "interseccao com o poligono do talhao")
    return saida


def regra_r17_desmate(ctx: dict) -> dict:
    """R17 - Poligono intersecta desmatamento validado pos-31/12/2020.

    A checagem 01 tambem detecta coordenada de ponto com menos de seis casas
    decimais (Art. 2(28)). Esse achado NAO e desmatamento: se a excecao da 01
    vier so por precisao, a R17 sai conforme e o defeito de precisao continua
    aparecendo na propria checagem 01, sem virar achado de desmate.
    """
    fonte = ctx["delegadas"].get("01") or {}
    evidencia = fonte.get("evidencia", {})
    if (fonte.get("resultado") == "excecao"
            and evidencia.get("motivo_excecao") == "precisao_coordenada"):
        return _ok(
            "R17 conforme: a checagem 01 nao encontrou alerta de supressao "
            "posterior a 31/12/2020 no talhao %s. A excecao registrada na 01 "
            "e de PRECISAO da coordenada (Art. 2(28)), nao de desmatamento."
            % ctx["talhao"]["nome"],
            {"delegada_a": "01", "resultado_da_checagem": "excecao",
             "motivo_da_excecao": "precisao_coordenada",
             "evidencia_da_checagem": evidencia})
    return _delegada(ctx, "01", "R17",
                     "interseccao com desmatamento pos-31/12/2020")


def _sobreposicao_por_tipo(ctx: dict, codigo_regra: str, tipo_area: str,
                           titulo: str, artigo: str) -> dict:
    """Base comum de R18 e R19: le a evidencia da checagem 04 e filtra por
    tipo de area, aplicando o rebaixamento proprio de cada regra.

    R18 e R19 eram um codigo composto 'R18/R19' e agora sao linhas de
    checagem distintas: a TI e a UC tem regras de rebaixamento diferentes
    (TI delimitada/declarada = F, homologada/regularizada = B; UC de uso
    sustentavel = F, de protecao integral = B) e um codigo unico nao
    conseguia carregar duas severidades.
    """
    fonte = ctx["delegadas"].get("04")
    if not fonte:
        return _ok("%s nao avaliada: a checagem 04 nao rodou nesta execucao, "
                   "entao nao ha resultado geoespacial a registrar."
                   % codigo_regra, {"delegada_a": "04"})
    areas = [a for a in fonte.get("evidencia", {}).get("areas", [])
             if a.get("tipo_area") == tipo_area]
    if not areas:
        return _ok("%s conforme: o poligono do talhao %s nao intersecta "
                   "nenhuma %s na camada consultada pela checagem 04."
                   % (codigo_regra, ctx["talhao"]["nome"], titulo),
                   {"delegada_a": "04", "tipo_area": tipo_area, "areas": []})
    severidade = "B" if any(a.get("severidade_regra") == "B" for a in areas) \
        else "F"
    descricao = "; ".join(
        "%s (categoria %s, severidade %s, %.4f ha de area comum)"
        % (a.get("nome_area"), a.get("categoria_area"),
           a.get("severidade_regra"), a.get("area_intersecao_ha") or 0.0)
        for a in areas)
    texto = ("%s - o poligono do talhao %s sobrepoe %d %s: %s. %s. "
             "Severidade %s pela categoria da area; resultado registrado a "
             "partir da checagem 04, sem reprocessamento geometrico."
             % (codigo_regra, ctx["talhao"]["nome"], len(areas), titulo,
                descricao, artigo, severidade))
    return {"resultado": "excecao", "texto": texto, "severidade": severidade,
            "evidencia": {"delegada_a": "04", "tipo_area": tipo_area,
                          "areas": areas, "severidade_calculada": severidade}}


def regra_r18_terra_indigena(ctx: dict) -> dict:
    """R18 - Interseccao com Terra Indigena.

    Homologada ou regularizada = B; delimitada ou declarada = F.
    """
    return _sobreposicao_por_tipo(
        ctx, "R18", "terra_indigena", "terra(s) indigena(s)",
        "TI homologada ou regularizada bloqueia a aptidao (B); apenas "
        "delimitada ou declarada rebaixa para flag (F)")


def regra_r19_unidade_conservacao(ctx: dict) -> dict:
    """R19 - Interseccao com Unidade de Conservacao.

    Protecao integral = B; uso sustentavel = F (conferir plano de manejo
    ou CDRU).
    """
    return _sobreposicao_por_tipo(
        ctx, "R19", "unidade_conservacao", "unidade(s) de conservacao",
        "UC de protecao integral bloqueia a aptidao (B); UC de uso "
        "sustentavel rebaixa para flag (F) e exige conferir o plano de "
        "manejo ou a CDRU")


def regra_r08_lista_suja(ctx: dict) -> dict:
    """R08 - CPF/CNPJ de qualquer elo do lote na Lista Suja vigente.

    Delegada a checagem 07, que faz o matching por CPF de todos os elos.
    """
    return _delegada(ctx, "07", "R08",
                     "CPF dos elos do lote contra a Lista Suja do MTE")


def regra_r14_poligono_como_ponto(ctx: dict) -> dict:
    """R14 - Talhao maior que 4 ha entregue como ponto (viola o Art. 2(28)).

    Regra fina, calculada aqui: o Art. 2(28) do Regulamento so aceita ponto
    com seis casas decimais para parcela de ate 4 ha. Acima disso a parcela
    tem que vir como poligono, e sem ele a camada 1 da aptidao nao fecha.
    """
    talhao = ctx["talhao"]
    area = _num(talhao.get("area_ha")) or 0.0
    tipo = (talhao.get("tipo_geom") or "").strip().lower()
    limite = 4.0
    evidencia = {"tipo_geom": tipo, "area_ha": round(area, 4),
                 "limite_ponto_ha": limite}
    if tipo != "ponto":
        return _ok("R14 conforme: o talhao %s foi entregue como %s, entao o "
                   "limite de 4 ha para geometria de ponto nao se aplica."
                   % (talhao["nome"], tipo or "geometria nao informada"),
                   evidencia)
    if area <= limite:
        return _ok("R14 conforme: o talhao %s tem %.2f ha, dentro do limite "
                   "de %.0f ha que o Art. 2(28) admite para parcela entregue "
                   "como ponto." % (talhao["nome"], area, limite), evidencia)
    return _falha(
        "R14 - falta o poligono do talhao %s: com %.2f ha ele ultrapassa o "
        "limite de %.0f ha que o Art. 2(28) admite para geolocalizacao por "
        "ponto, e o que existe no cadastro e uma coordenada. E lacuna de "
        "dado geografico, sanavel com uma caminhada de GPS no perimetro."
        % (talhao["nome"], area, limite), evidencia)


def regra_r39_volume_vs_produtividade_maxima(ctx: dict) -> dict:
    """R39 - DESLIGADA por decisao de spec (regra de ouro no 8 do contrato).

    Compararia a soma das notas do produtor contra area x produtividade
    maxima regional. O parametro nao foi levantado: `params/cacau.yml` traz
    `r39_produtividade_maxima.ativa: false` e o valor vazio. Nenhum numero e
    inventado aqui - a regra se declara desligada e sai como nao avaliada.
    """
    bloco = ctx["params"].get("r39_produtividade_maxima", {}) or {}
    if bloco.get("ativa"):
        # Se algum dia o parametro for levantado, esta e a porta de entrada.
        maxima = (bloco.get("produtividade_maxima_kg_ha") or {}).get(
            (ctx["produtor"].get("uf") or "PA").upper())
        if not maxima:
            return _ok("R39 nao avaliada: a regra esta marcada como ativa em "
                       "params/cacau.yml, mas a produtividade maxima da UF "
                       "continua vazia - nenhum numero e arbitrado aqui.",
                       {"ativa": True, "produtividade_maxima_kg_ha": None})
    return _ok("R39 nao avaliada: regra DESLIGADA em params/cacau.yml "
               "(`r39_produtividade_maxima.ativa: false`). A produtividade "
               "maxima regional nao foi levantada e a regra de ouro no 8 do "
               "contrato proibe arbitrar o numero.",
               {"ativa": bool(bloco.get("ativa")),
                "observacao": bloco.get("observacao")})


# ---------------------------------------------------------------------------
# MAPA DE RECODIFICACAO DAS REGRAS (spec v2, correcoes-spec_1.md secao 04)
# ---------------------------------------------------------------------------
# A numeracao propria da v1 (R1..R14) foi substituida pela numeracao oficial
# R01-R50. Onde havia equivalente oficial, a regra recebeu o codigo oficial;
# onde nao havia, recebeu codigo na faixa livre do grupo tematico a que
# pertence. Os grupos, conforme o contrato v2, sao:
#
#   R01-R10  identidade e titularidade
#   R11-R20  area e geometria
#   R21-R30  jurisdicao e localizacao
#   R31-R38  vigencia e tempo
#   R39-R44  volume e massa
#   R45-R50  documento fiscal
#
# | v1  | oficial | Sev | O que checa                        | equivalencia |
# |-----|---------|-----|------------------------------------|--------------|
# | R1  | R01     | B   | CPF do CAR != CPF da NF            | oficial      |
# | R2  | R11     | F   | area do talhao > area do CAR       | faixa livre  |
# | R3  | R31     | F   | documento vencido no embarque      | faixa livre  |
# | R4  | R21     | F   | municipio matricula != CAR         | faixa livre  |
# | R5  | R22     | F   | arrendatario != produtor           | faixa livre  |
# | R6  | R48     | F   | conjunto minimo ausente            | faixa livre  |
# | R7  | R46     | F   | duplicidade suspeita               | faixa livre  |
# | R8  | R09     | F   | mesmo CPF, nomes diferentes        | faixa livre  |
# | R9  | R12     | F   | area divergente entre documentos   | faixa livre  |
# | R10 | R32     | F   | emissao depois da validade         | faixa livre  |
# | R11 | R45     | F   | nota fiscal repetida               | faixa livre  |
# | R12 | R47     | F   | documento ilegivel ou divergente   | faixa livre  |
# | R13 | R33     | F   | vigencia nao cobre a safra         | faixa livre  |
# | R14 | R29     | B   | CAR nao Ativo (Cancelado = B)      | oficial      |
#
# Entraram novas, para fechar as NOVE regras B obrigatorias do contrato v2:
#   R13 (talhao dentro do CAR)      -> delegada a checagem 03
#   R16 (embargo)                   -> delegada a checagem 02
#   R17 (desmate pos-2020)          -> delegada a checagem 01
#   R18 (terra indigena)            -> delegada a checagem 04, filtrada por tipo
#   R19 (unidade de conservacao)    -> delegada a checagem 04, filtrada por tipo
#   R08 (Lista Suja do MTE)         -> delegada a checagem 07
#   R14 (poligono > 4 ha como ponto)-> regra fina, calculada aqui
#   R39 (volume vs produtividade)   -> DESLIGADA, nao roda e nao inventa numero
#
# ATENCAO ao homonimo: a "R13" da v1 (vigencia) virou R33; a R13 oficial e
# outra coisa (talhao dentro do CAR). O mesmo vale para R11, R12 e R14.
#
# Severidade B nao significa "lote bloqueado": significa "bloqueia a aptidao
# ate resolver" (contrato v2, secao 04). Quem derruba lote para 'bloqueado'
# sao as checagens 01, 02 e 04, que respondem por prova geometrica e por
# direito de terceiros. Invariante 5 do contrato: o sistema marca, ordena e
# informa - quem decide e sempre o humano.
#
# Registro ordenado das regras: (codigo oficial, severidade, funcao).
# Adicionar regra = acrescentar uma linha aqui.
REGRAS_05 = [
    # --- as nove B obrigatorias do contrato v2 ---
    ("R17", "B", regra_r17_desmate),
    ("R16", "B", regra_r16_embargo),
    ("R13", "B", regra_r13_talhao_dentro_do_car),
    ("R29", "B", regra_14_car_situacao),
    ("R08", "B", regra_r08_lista_suja),
    # R18 e R19 sao linhas SEPARADAS: cada uma tem rebaixamento proprio e a
    # severidade abaixo e so o padrao - a regra devolve a sua.
    ("R18", "B", regra_r18_terra_indigena),
    ("R19", "B", regra_r19_unidade_conservacao),
    ("R01", "B", regra_01_cpf_car_vs_nota),
    ("R14", "B", regra_r14_poligono_como_ponto),
    # --- as F, herdadas da numeracao v1 e recodificadas ---
    ("R09", "F", regra_08_nome_divergente_mesmo_cpf),
    ("R11", "F", regra_02_area_talhao_vs_car),
    ("R12", "F", regra_09_area_divergente_entre_documentos),
    ("R21", "F", regra_04_municipio_matricula_vs_car),
    ("R22", "F", regra_05_titular_arrendamento),
    ("R31", "F", regra_03_vencido_no_embarque),
    ("R32", "F", regra_10_emissao_depois_da_validade),
    ("R33", "F", regra_13_vigencia_nao_cobre_safra),
    ("R45", "F", regra_11_nota_repetida),
    ("R46", "F", regra_07_duplicidade_suspeita),
    ("R47", "F", regra_12_documento_ilegivel_ou_divergente),
    ("R48", "F", regra_06_conjunto_minimo),
    # --- desligada por falta de parametro (regra de ouro no 8) ---
    ("R39", "F", regra_r39_volume_vs_produtividade_maxima),
]

# Categoria EUDR de cada regra, para gravar em `checagem.categoria`.
CATEGORIA_REGRA = {
    "R01": "a", "R08": "e", "R09": "a", "R11": "a", "R12": "a",
    "R13": "a", "R14": "A", "R16": "b", "R17": "A", "R18": "d", "R19": "b",
    "R21": "a", "R22": "a", "R29": "b", "R31": "h", "R32": "h",
    "R33": "a", "R39": "h", "R45": "h", "R46": "h", "R47": "a",
    "R48": "a",
}


def checagem_05(talhao_id: str, delegadas: dict = None) -> dict:
    """Consistencia documental - roda as %d regras e agrega o pior resultado.

    Nao e "o documento existe": e o cruzamento entre documentos do mesmo
    produtor. Cada excecao diz qual documento conflita com qual.

    `delegadas` traz o resultado das checagens geoespaciais ja executadas
    neste talhao, para que R13, R16, R17, R18, R19 e R08 registrem o achado
    sem reprocessar geometria.

    O resultado agregado nunca e `bloqueio`: severidade B aqui significa
    "bloqueia a APTIDAO ate resolver" (contrato v2, secao 04), nao "barra o
    lote". Quem derruba lote para 'bloqueado' sao as checagens 01, 02 e 04.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["05"]
    ctx = _ctx_documental(talhao_id, delegadas)
    produtor = ctx["produtor"]
    total_docs = len(ctx["documentos"])
    base = ("documentos do produtor %s ja processados pela ingestao "
            "(%d documento(s) na tabela `documento`), cruzados entre si e "
            "com o conjunto minimo de params/cacau.yml"
            % (produtor.get("nome") or "?", total_docs))

    resultados = {}
    disparadas = []
    disparadas_b = []
    for nome, severidade, funcao in REGRAS_05:
        try:
            saida = funcao(ctx)
        except Exception as erro:      # uma regra ruim nao derruba a checagem
            saida = {"resultado": "excecao",
                     "texto": "%s nao pode ser avaliada: erro interno (%s)."
                              % (nome, erro), "evidencia": {"erro": str(erro)}}
        # A severidade da tupla e o PADRAO da regra; a regra pode devolver a
        # sua propria quando o rebaixamento depende do dado (R18 e R19).
        severidade_efetiva = saida.get("severidade") or severidade
        saida["severidade"] = severidade_efetiva
        saida["categoria"] = CATEGORIA_REGRA.get(nome, "a")
        resultados[nome] = saida
        if saida["resultado"] != "conforme":
            disparadas.append(nome)
            if severidade_efetiva == "B":
                disparadas_b.append(nome)

    if total_docs == 0:
        # Trilha A ainda nao populou `documento`. Isso e lacuna declarada,
        # nao conformidade: sai como excecao com a R48 explicando o que falta.
        resultado = "excecao"
        detalhe = ("nenhum documento do produtor foi processado ate agora, "
                   "entao todo o conjunto minimo esta ausente (R48) e as "
                   "demais regras ficaram sem par para cruzar")
        conclusao = ("nao ha prova documental nenhuma para este produtor - "
                     "EXCECAO por lacuna total de documentacao; a checagem "
                     "deve ser reexecutada assim que a ingestao rodar.")
    elif disparadas:
        resultado = "excecao"
        detalhe = ("%d de %d regras apontaram conflito (%d de severidade B, "
                   "que bloqueiam aptidao: %s) - %s"
                   % (len(disparadas), len(REGRAS_05), len(disparadas_b),
                      ", ".join(disparadas_b) or "nenhuma",
                      " | ".join(resultados[r]["texto"].rstrip(".")
                                 for r in disparadas)))
        conclusao = ("ha documento faltando ou em conflito no conjunto do "
                     "produtor: EXCECAO registrada para conferencia humana "
                     "antes do embarque.")
    else:
        resultado = "conforme"
        detalhe = ("as %d regras de cruzamento documental passaram sem "
                   "conflito" % len(REGRAS_05))
        conclusao = ("a documentacao do produtor e internamente consistente "
                     "na data da consulta.")

    return {
        "resultado": resultado, "perna": perna, "categoria": categoria,
        "severidade": "B" if disparadas_b else "F",
        "fonte": base,
        "texto": montar_laudo(
            comparado="os %d documentos do produtor %s entre si, o talhao %s "
                      "e os lotes que o contem, por %d regras numeradas de "
                      "consistencia documental (R01-R50)"
                      % (total_docs, produtor.get("nome") or "?",
                         ctx["talhao"]["nome"], len(REGRAS_05)),
            base=base, resultado=detalhe, conclusao=conclusao),
        "evidencia": {
            "regras_avaliadas": len(REGRAS_05),
            "regras_disparadas": disparadas,
            "regras_disparadas_severidade_b": disparadas_b,
            "documentos_do_produtor": total_docs,
            "detalhe_por_regra": {
                nome: {"resultado": r["resultado"], "texto": r["texto"],
                       "severidade": r["severidade"],
                       "categoria": r["categoria"],
                       "evidencia": r["evidencia"]}
                for nome, r in resultados.items()},
        },
    }


checagem_05.__doc__ = checagem_05.__doc__ % len(REGRAS_05)


# ===========================================================================
# Checagem 06 - Coerencia de volume (perna B, categoria 8)
# ===========================================================================
def checagem_06(talhao_id: str) -> dict:
    """Volume do produtor no lote contra area x produtividade de referencia.

    > 150% do esperado -> excecao; > 300% -> bloqueio.
    Evidencia guarda os tres numeros: area, produtividade e volume.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["06"]
    params = carregar_params()
    prod = params["produtividade_kg_ha"]
    talhao = db.buscar_talhao(talhao_id)
    produtor = db.buscar_produtor(talhao["produtor_id"]) or {}
    uf = (produtor.get("uf") or params.get("uf_recorte") or "PA").upper()
    produtividade = _num(prod.get(uf)) or _num(prod.get("PA"))
    limiar_ex = float(prod.get("limiar_excecao", 1.5))
    limiar_bl = float(prod.get("limiar_bloqueio", 3.0))
    base = ("produtividade de referencia de %s kg/ha para a UF %s, lida de "
            "params/cacau.yml (parametro declarado como 'a confirmar', "
            "pendencia P-01 do ADR.md)" % (produtividade, uf))

    alocacoes = db.consultar(
        "SELECT lt.quantidade_kg, l.codigo, l.id AS lote_id "
        "FROM lote_talhao lt JOIN lote l ON l.id = lt.lote_id "
        "WHERE lt.talhao_id = ?", (talhao_id,))
    volume = sum(_num(a.get("quantidade_kg")) or 0.0 for a in alocacoes)
    area = _num(talhao.get("area_ha")) or 0.0
    esperado = area * (produtividade or 0.0)

    numeros = {
        "area_ha": round(area, 4),
        "produtividade_kg_ha": produtividade,
        "volume_declarado_kg": round(volume, 2),
        "volume_esperado_kg": round(esperado, 2),
        "razao": round(volume / esperado, 3) if esperado else None,
        "uf_referencia": uf,
        "limiar_excecao": limiar_ex, "limiar_bloqueio": limiar_bl,
        "lotes": [{"codigo": a["codigo"], "quantidade_kg": a["quantidade_kg"]}
                  for a in alocacoes],
    }

    if not alocacoes:
        return {
            "resultado": "conforme", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="volume alocado ao talhao %s nos lotes de embarque"
                          % talhao["nome"],
                base=base,
                resultado="o talhao nao esta alocado a nenhum lote, entao nao "
                          "ha volume a confrontar com a capacidade produtiva "
                          "de %.2f ha x %s kg/ha" % (area, produtividade),
                conclusao="sem volume declarado nao ha incoerencia fiscal a "
                          "apontar."),
            "evidencia": numeros}

    if not esperado:
        return {
            "resultado": "excecao", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado="volume de %.0f kg alocado ao talhao %s contra area "
                          "x produtividade de referencia"
                          % (volume, talhao["nome"]),
                base=base,
                resultado="nao foi possivel calcular o volume esperado - area "
                          "do talhao %.2f ha e produtividade %s kg/ha"
                          % (area, produtividade),
                conclusao="cadastro incompleto impede a checagem de coerencia "
                          "de volume - EXCECAO para completar a area do "
                          "talhao ou o parametro da commodity."),
            "evidencia": numeros}

    razao = volume / esperado
    comparado = ("volume de %.0f kg declarado para o talhao %s em %d lote(s) "
                 "(%s) contra a capacidade estimada de %.0f kg "
                 "(%.2f ha x %s kg/ha)"
                 % (volume, talhao["nome"], len(alocacoes),
                    ", ".join(a["codigo"] for a in alocacoes), esperado,
                    area, produtividade))

    if razao > limiar_bl:
        return {
            "resultado": "bloqueio", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado=comparado, base=base,
                resultado="o volume declarado e %.0f%% do esperado, acima do "
                          "limiar de bloqueio de %.0f%%"
                          % (razao * 100, limiar_bl * 100),
                conclusao="o talhao nao tem como ter produzido esse volume: "
                          "ha forte indicio de mistura com cacau de origem "
                          "nao rastreada - lote BLOQUEADO ate reconciliacao "
                          "das notas fiscais."),
            "evidencia": numeros}

    if razao > limiar_ex:
        return {
            "resultado": "excecao", "perna": perna, "categoria": categoria,
            "fonte": base,
            "texto": montar_laudo(
                comparado=comparado, base=base,
                resultado="o volume declarado e %.0f%% do esperado, acima do "
                          "limiar de excecao de %.0f%% e abaixo do limiar de "
                          "bloqueio de %.0f%%"
                          % (razao * 100, limiar_ex * 100, limiar_bl * 100),
                conclusao="volume acima do que a area comporta em produtividade "
                          "media - EXCECAO para conferir se houve safra "
                          "excepcional ou entrada de terceiros."),
            "evidencia": numeros}

    return {
        "resultado": "conforme", "perna": perna, "categoria": categoria,
        "fonte": base,
        "texto": montar_laudo(
            comparado=comparado, base=base,
            resultado="o volume declarado e %.0f%% do esperado, dentro do "
                      "limiar de %.0f%%" % (razao * 100, limiar_ex * 100),
            conclusao="volume compativel com a area e a produtividade da "
                      "regiao - categoria 8 conforme."),
        "evidencia": numeros}


# ===========================================================================
# Checagem 07 - Lista Suja do MTE (perna B, categorias e, f) - NOVA na v2
# ===========================================================================
def checagem_07(talhao_id: str) -> dict:
    """CPF de todos os elos do lote contra a Lista Suja do MTE.

    Existe porque as categorias (e) trabalhista e (f) direitos humanos NAO
    tem documento positivo emitido para o produtor: nao ha certidao publica de
    conformidade trabalhista para pessoa fisica sem empregados. A prova e
    Lista Suja + CAF + autodeclaracao, e a parte automatizavel e a Lista Suja.

    Matching SEMPRE por CPF, nunca por nome: nomes colidem e divergem entre
    documentos, e o CPF e a chave de juncao de todas as checagens.

    A planilha semestral oficial do MTE nao foi baixada (recurso a descobrir),
    entao a lista aqui e SEMEADA - declarada como tal no laudo, ADR-012.
    """
    perna, categoria = "B", CATEGORIA_CHECAGEM["07"]
    base = ("lista `%s` com os CPF/CNPJ do Cadastro de Empregadores do MTE "
            "(Lista Suja) - %s"
            % (ARQUIVO_LISTA_SUJA_SEMEADO.name, FONTE_SEMEADA))

    talhao = db.buscar_talhao(talhao_id)
    lista = carregar_lista_suja()

    # Os elos do lote: o produtor do talhao e todos os demais produtores que
    # compoem os mesmos lotes. A checagem e do LOTE, nao so do talhao.
    elos = {}
    produtor = db.buscar_produtor(talhao["produtor_id"]) or {}
    if produtor:
        elos[produtor["id"]] = ("produtor do talhao", produtor)
    for lote in db.lotes_do_talhao(talhao_id):
        for outro in db.produtores_do_lote(lote["id"]):
            elos.setdefault(outro["id"], ("elo do lote %s" % lote["codigo"],
                                          outro))

    avaliados, achados = [], []
    for papel, pessoa in elos.values():
        cpf = _digitos(pessoa.get("cpf"))
        avaliados.append({"papel": papel, "produtor_id": pessoa.get("id"),
                          "cpf": cpf or None})
        if cpf and cpf in lista:
            registro = lista[cpf]
            achados.append({
                "papel": papel, "produtor_id": pessoa.get("id"), "cpf": cpf,
                "numero_inscricao": registro.get("numero_inscricao"),
                "ano_inclusao": registro.get("ano_inclusao"),
                "uf": registro.get("uf"), "fonte_camada": "SEMEADO"})

    sem_cpf = [a for a in avaliados if not a["cpf"]]
    comparado = ("os CPF de %d elo(s) do(s) lote(s) que contem o talhao %s "
                 "contra o Cadastro de Empregadores do MTE, por CPF e nunca "
                 "por nome" % (len(avaliados), talhao["nome"]))

    if achados:
        inscricoes = ", ".join(a["numero_inscricao"] or "sem numero"
                               for a in achados)
        return {
            "resultado": "bloqueio", "perna": perna, "categoria": categoria,
            "severidade": "B", "natureza": "lista_suja_mte",
            "tipo_excecao": "bloqueio", "fonte": base,
            "texto": montar_laudo(
                comparado=comparado, base=base,
                resultado="%d CPF de elo do lote consta na lista (inscricao "
                          "%s)" % (len(achados), inscricoes),
                conclusao="ha inscricao ativa no Cadastro de Empregadores "
                          "para um dos CPF da cadeia: R08 (severidade B) "
                          "aponta BLOQUEIO das categorias (e) e (f) ate a "
                          "baixa da inscricao - lembrando que a lista "
                          "consultada e semeada e precisa ser trocada pela "
                          "planilha oficial do MTE antes de valer como "
                          "prova."),
            "evidencia": {"elos_avaliados": avaliados, "achados": achados,
                          "registros_na_lista": len(lista),
                          "fonte_camada": "SEMEADO"}}

    return {
        "resultado": "conforme", "perna": perna, "categoria": categoria,
        "severidade": "B", "natureza": "lista_suja_mte", "fonte": base,
        "texto": montar_laudo(
            comparado=comparado, base=base,
            resultado="nenhum dos %d CPF avaliados consta entre os %d "
                      "registros da lista%s"
                      % (len(avaliados), len(lista),
                         "" if not sem_cpf else
                         " (%d elo(s) sem CPF no cadastro, que por isso nao "
                         "puderam ser cruzados)" % len(sem_cpf)),
            conclusao="checagem negativa fechada para as categorias (e) "
                      "trabalhista e (f) direitos humanos na data da "
                      "consulta - e evidencia que o sistema gera, nao que o "
                      "produtor entrega; a lista usada e semeada e nao "
                      "substitui a planilha do MTE."),
        "evidencia": {"elos_avaliados": avaliados, "achados": [],
                      "registros_na_lista": len(lista),
                      "fonte_camada": "SEMEADO"}}


CHECAGENS = [
    ("01", "Desmate pos-2020", checagem_01),
    ("02", "Embargo do Ibama", checagem_02),
    ("03", "CAR e posse", checagem_03),
    ("04", "Sobreposicao de direitos", checagem_04),
    ("05", "Consistencia documental", checagem_05),
    ("06", "Coerencia de volume", checagem_06),
    ("07", "Lista Suja do MTE", checagem_07),
]

# Codigos que contam para o status do lote. As linhas de `checagem` gravadas
# com codigo de regra (R01, R17...) sao detalhe da 05 e nao podem ser somadas
# de novo: contariam o mesmo achado duas vezes.
CODIGOS_AGREGADOS = tuple(c for c, _, _ in CHECAGENS)

# A natureza antiga do achado. NAO vai para `excecao.tipo` (que so aceita o
# vocabulario fixo de db.TIPOS_EXCECAO): vai para a evidencia e para o
# prefixo da descricao, que e o que mantem a idempotencia por origem.
NATUREZA_CHECAGEM = {
    "01": "desmate_pos_2020", "02": "embargo_ibama", "03": "car_e_posse",
    "04": "sobreposicao_direitos", "05": "consistencia_documental",
    "06": "coerencia_volume", "07": "lista_suja_mte",
}

# Classificacao padrao da excecao (correcoes-spec_1.md secao 03):
# resultado `bloqueio` -> `bloqueio`; resultado `excecao` -> `lacuna_sanavel`.
# As excecoes a esse padrao sao devolvidas pela propria checagem em
# `tipo_excecao` (CAR pendente -> `nao_sanavel_pelo_produtor`) ou criadas por
# `registrar_dispensas` (licenca, ASV e SIGEF -> `dispensa_documentada`).
TIPO_EXCECAO_PADRAO = {"bloqueio": "bloqueio", "excecao": "lacuna_sanavel"}

PIOR = {"conforme": 0, "excecao": 1, "bloqueio": 2}


# ===========================================================================
# Orquestracao
# ===========================================================================
# Ordem de execucao: a 05 vem por ultimo porque suas regras geometricas
# (R13, R16, R17, R18, R19) e a R08 delegam o resultado das demais.
ORDEM_EXECUCAO = ["01", "02", "03", "04", "06", "07", "05"]

# Documentos cuja AUSENCIA e a situacao regular da cacauicultura familiar.
# Nao sao lacuna: viram excecao `dispensa_documentada`, que o painel nao soma.
# (correcoes-spec_1.md secao 03 e invariante 3 do contrato v2.)
DISPENSAS = [
    ("licenca_ambiental", "licenca ambiental",
     "cacauicultura familiar em area consolidada e tipicamente dispensada de "
     "licenciamento"),
    ("asv", "ASV/AUTEF",
     "SAF de cacau em area consolidada nao suprime vegetacao, entao nao ha "
     "autorizacao a exigir - a presenca e que seria excepcional"),
    ("sigef", "certificacao SIGEF",
     "a obrigacao so comeca em 21/10/2029 (Dec. 12.689/2025) e em 2026 "
     "imoveis com menos de 25 ha nao estao obrigados"),
]


def _excecao_idempotente(talhao_id: str, tipo: str, natureza: str,
                         descricao: str, ids_lotes: str,
                         codigos_lotes: str, contexto: str) -> str:
    """Cria ou atualiza a excecao aberta daquela natureza naquele talhao.

    A idempotencia e por (talhao, natureza), nao por (talhao, tipo): o
    vocabulario de `excecao.tipo` tem so quatro valores e varias checagens
    diferentes caem no mesmo valor. Sem a natureza no prefixo, a segunda
    checagem sobrescreveria o laudo da primeira.
    """
    db.validar_tipo_excecao(tipo)
    marcado = "[%s] %s" % (natureza, descricao)
    ja_aberta = db.consultar(
        "SELECT id, tipo FROM excecao WHERE talhao_id = ? AND status = "
        "'aberta' AND descricao LIKE ? LIMIT 1",
        (talhao_id, "[%s]%%" % natureza))
    if ja_aberta:
        db.atualizar("excecao", ja_aberta[0]["id"],
                     {"descricao": marcado, "tipo": tipo,
                      "lotes_afetados": ids_lotes})
        return ja_aberta[0]["id"]
    excecao = db.inserir_excecao({
        "tipo": tipo, "talhao_id": talhao_id, "documento_id": None,
        "lotes_afetados": ids_lotes, "descricao": marcado, "status": "aberta"})
    db.registrar_evento(
        "sistema", "excecao_aberta", "excecao", excecao["id"],
        "%s: excecao do tipo '%s' (natureza %s); lotes afetados: %s"
        % (contexto, tipo, natureza, codigos_lotes))
    return excecao["id"]


def _fechar_excecoes(talhao_id: str, natureza: str, codigo: str,
                     nome_talhao: str) -> int:
    """Resolve as excecoes abertas daquela natureza quando a checagem volta a
    conforme. Nenhuma linha e apagada - a trilha de auditoria e o produto."""
    abertas = db.consultar(
        "SELECT id FROM excecao WHERE talhao_id = ? AND status = 'aberta' "
        "AND descricao LIKE ?", (talhao_id, "[%s]%%" % natureza))
    for linha in abertas:
        db.atualizar("excecao", linha["id"],
                     {"status": "resolvida", "resolvido_por": "sistema",
                      "resolvido_em": db.agora()})
        db.registrar_evento(
            "sistema", "excecao_resolvida", "excecao", linha["id"],
            "A checagem %s voltou a conforme no talhao %s: a excecao de "
            "natureza %s foi encerrada pelo proprio sistema."
            % (codigo, nome_talhao, natureza))
    return len(abertas)


def registrar_dispensas(talhao: dict, ids_lotes: str,
                        codigos_lotes: str) -> list:
    """Registra a ausencia de licenca, ASV e SIGEF como DISPENSA, nao lacuna.

    Invariante 3 do contrato v2: se o sistema tratar toda ausencia como
    pendencia, ele cria exatamente a barreira que o produto existe para
    remover. A frase fala do documento, nunca da pessoa.
    """
    documentos = db.listar_documentos(talhao["produtor_id"])
    presentes = {d.get("tipo") for d in documentos}
    ausentes = [(t, nome, motivo) for t, nome, motivo in DISPENSAS
                if t not in presentes]
    if not ausentes:
        return []
    produtor = db.buscar_produtor(talhao["produtor_id"]) or {}
    frases = ["nao consta %s nos arquivos de %s - %s"
              % (nome, produtor.get("nome") or "o produtor", motivo)
              for _, nome, motivo in ausentes]
    descricao = montar_laudo(
        comparado="os tipos documentais dispensados na cacauicultura familiar "
                  "(licenca ambiental, ASV/AUTEF e SIGEF) contra os "
                  "documentos entregues do talhao %s" % talhao["nome"],
        base="params/cacau.yml e correcoes-spec_1.md secao 03",
        resultado="; ".join(frases),
        conclusao="a ausencia desses documentos e a SITUACAO REGULAR: fica "
                  "registrada como dispensa documentada e nao entra na "
                  "contagem de lacunas do painel.")
    ident = _excecao_idempotente(
        talhao["id"], "dispensa_documentada", "dispensa_documentada",
        descricao, ids_lotes, codigos_lotes,
        "Dispensa documentada no talhao %s" % talhao["nome"])
    return [ident]


def verificar_talhao(talhao_id: str) -> dict:
    """Roda as SETE checagens de um talhao, grava tudo e devolve o resumo.

    Grava em `checagem` com data_execucao, categoria e severidade; grava
    tambem uma linha por regra da 05 com `codigo` = codigo oficial da regra
    (R01, R17...); cria `excecao` com o vocabulario fixo de quatro valores
    quando o resultado nao e conforme; e chama registrar_evento sempre.
    """
    talhao = db.buscar_talhao(talhao_id)
    if not talhao:
        raise ValueError("talhao inexistente: %s" % talhao_id)
    lotes = db.lotes_do_talhao(talhao_id)
    ids_lotes = ",".join(l["id"] for l in lotes)
    codigos_lotes = ", ".join(l["codigo"] for l in lotes) or "nenhum lote"

    resumo = {"talhao_id": talhao_id, "talhao_nome": talhao["nome"],
              "resultados": {}, "pior": "conforme", "excecoes_criadas": [],
              "regras_gravadas": 0}

    nomes = {c: n for c, n, _ in CHECAGENS}
    funcoes = {c: f for c, _, f in CHECAGENS}
    delegadas = {}

    for codigo in ORDEM_EXECUCAO:
        funcao, nome = funcoes[codigo], nomes[codigo]
        try:
            saida = (funcao(talhao_id, delegadas) if codigo == "05"
                     else funcao(talhao_id))
        except Exception as erro:
            # Falha de checagem nunca vira "conforme" silencioso.
            saida = {
                "resultado": "excecao", "perna": "B",
                "categoria": CATEGORIA_CHECAGEM[codigo],
                "severidade": SEVERIDADE_CHECAGEM[codigo],
                "fonte": "execucao interna",
                "texto": montar_laudo(
                    comparado="checagem %s do talhao %s"
                              % (codigo, talhao["nome"]),
                    base="execucao interna do verificacao.py",
                    resultado="a checagem falhou com erro tecnico: %s" % erro,
                    conclusao="resultado indefinido - EXCECAO ate que a "
                              "checagem seja reexecutada com sucesso."),
                "evidencia": {"erro": str(erro)}}
        delegadas[codigo] = saida

        categoria = CATEGORIA_CHECAGEM[codigo]
        severidade = saida.get("severidade") or SEVERIDADE_CHECAGEM[codigo]
        natureza = saida.get("natureza") or NATUREZA_CHECAGEM[codigo]

        registro = db.inserir_checagem({
            "talhao_id": talhao_id,
            "codigo": codigo,
            "perna": saida.get("perna"),
            "resultado": saida["resultado"],
            "texto": saida["texto"],
            "fonte": saida.get("fonte"),
            "data_execucao": db.agora(),
            "categoria": categoria,
            "severidade": severidade,
            "evidencia_json": json.dumps(
                {"categoria": categoria, "severidade": severidade,
                 "natureza": natureza,
                 "categoria_descricao": ", ".join(
                     NOME_CATEGORIA.get(x, x) for x in categoria.split(",")),
                 "evidencia": saida.get("evidencia", {})},
                ensure_ascii=False, default=str),
        })
        db.registrar_evento(
            "sistema", "checagem_executada", "checagem", registro["id"],
            "Checagem %s (%s, perna %s, categoria %s, severidade %s) no "
            "talhao %s: %s"
            % (codigo, nome, saida.get("perna"), categoria, severidade,
               talhao["nome"], saida["resultado"]))

        # Uma linha de `checagem` por regra da 05, com o codigo OFICIAL da
        # regra. Nao entram no calculo de status do lote (CODIGOS_AGREGADOS).
        if codigo == "05":
            resumo["regras_gravadas"] += _gravar_regras_05(
                talhao_id, saida, registro["id"])

        if saida["resultado"] != "conforme":
            tipo = saida.get("tipo_excecao") or TIPO_EXCECAO_PADRAO.get(
                saida["resultado"], "lacuna_sanavel")
            ident = _excecao_idempotente(
                talhao_id, tipo, natureza, saida["texto"], ids_lotes,
                codigos_lotes,
                "Checagem %s no talhao %s resultou em %s"
                % (codigo, talhao["nome"], saida["resultado"]))
            resumo["excecoes_criadas"].append(ident)
        else:
            # A checagem voltou a conforme (desembargo, documento novo, ou a
            # reversao da injecao da demo): a excecao daquela natureza fecha
            # sozinha, com o ator 'sistema' registrado na trilha.
            _fechar_excecoes(talhao_id, natureza, codigo, talhao["nome"])

        resumo["resultados"][codigo] = saida["resultado"]
        if PIOR[saida["resultado"]] > PIOR[resumo["pior"]]:
            resumo["pior"] = saida["resultado"]

    # Ausencia de licenca, ASV e SIGEF: dispensa documentada, nao lacuna.
    resumo["excecoes_criadas"].extend(
        registrar_dispensas(talhao, ids_lotes, codigos_lotes))

    db.registrar_evento(
        "sistema", "talhao_verificado", "talhao", talhao_id,
        "Sete checagens executadas no talhao %s; pior resultado: %s"
        % (talhao["nome"], resumo["pior"]))
    return resumo


def _gravar_regras_05(talhao_id: str, saida_05: dict,
                      checagem_05_id: str) -> int:
    """Grava uma linha de `checagem` por regra da 05, com o codigo oficial.

    E o que faz `checagem.codigo` carregar 'R17' como manda a spec v2, sem
    perder a linha agregada '05' de que a Trilha C depende. Estas linhas sao
    detalhe: `recalcular_status_lotes` so olha CODIGOS_AGREGADOS.
    """
    detalhe = saida_05.get("evidencia", {}).get("detalhe_por_regra", {})
    momento = db.agora()
    gravadas = 0
    for codigo_regra, dados in detalhe.items():
        db.inserir_checagem({
            "talhao_id": talhao_id,
            "codigo": codigo_regra,
            "perna": "B",
            "resultado": dados["resultado"],
            "texto": dados["texto"],
            "fonte": "regra %s da checagem 05 (verificacao.py)" % codigo_regra,
            "data_execucao": momento,
            "categoria": dados.get("categoria"),
            "severidade": dados.get("severidade"),
            "evidencia_json": json.dumps(
                {"regra": codigo_regra,
                 "severidade": dados.get("severidade"),
                 "categoria": dados.get("categoria"),
                 "checagem_agregada_id": checagem_05_id,
                 "evidencia": dados.get("evidencia", {})},
                ensure_ascii=False, default=str)})
        gravadas += 1
    return gravadas


# ===========================================================================
# Aptidao em cinco camadas (correcoes-spec_1.md secao 01) - escrita da Trilha B
# ===========================================================================
# APTIDAO E HIERARQUIA DE ALTERNATIVAS, NAO CHECKLIST. Cada camada aceita
# varios documentos, em ordem de forca probatoria, e a `forca` registra por
# qual degrau ela fechou. Um lote fechado so com camadas 2 fracas e conforme -
# e e exatamente o lote que a cooperativa quer ver antes de assinar.
#
# Reprovar quem nao tem matricula seria construir a barreira que o produto
# existe para remover: a FAQ da Comissao diz que, se a lei local nao exige
# titulo formal para produzir e comercializar, o Regulamento tambem nao exige.

NOME_CAMADA = {
    1: "parcela geolocalizada - Art. 9(1)(d) + 2(28)",
    2: "direito de uso da area - Art. 9(1)(h) + 2(40)(a)",
    3: "identidade e vinculo - Art. 9(1)(e)",
    4: "transacao, quantidade e data - Art. 9(1)(b), (d)",
    5: "checagens negativas na data do dossie - Art. 9(1)(g) + 10(2)",
}

# Camada 2, em ordem de forca probatoria decrescente. E a hierarquia inteira.
HIERARQUIA_CAMADA_2 = [
    ("matricula_imovel", "forte", "matricula em nome do produtor"),
    ("titulo_assentamento", "media", "titulo (TD, CDRU, CCU)"),
    ("declaracao_posse", "fraca",
     "contrato ou declaracao de posse, que so fecha corroborada por CCIR ou "
     "DITR/CIB em nome proprio"),
    ("contrato_arrendamento", "fraca",
     "contrato de arrendamento, parceria ou comodato"),
]


def _doc_id(documentos: list, *tipos) -> str:
    """Id do primeiro documento de um dos tipos pedidos, ou None."""
    for tipo in tipos:
        for d in documentos:
            if d.get("tipo") == tipo:
                return d.get("id")
    return None


def _camada_1(produtor: dict, talhoes: list, documentos: list) -> dict:
    """Poligono do talhao dentro de CAR nao-cancelado.

    Ativo e Pendente PASSAM (Pendente e o estado do sistema, nao falha do
    produtor). Cancelado e Suspenso reprovam. Ponto so vale para talhao de
    ate 4 ha - acima disso o Art. 2(28) exige poligono. Unica camada sem
    substituto possivel.
    """
    if not talhoes:
        return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
                "detalhe": "nao ha talhao cadastrado para este produtor"}
    reprovados, so_ponto, pendentes = [], [], []
    for t in talhoes:
        situacao = (t.get("car_situacao") or "").strip().lower()
        if not t.get("car_numero") or situacao in ("cancelado", "suspenso"):
            reprovados.append(t["nome"])
            continue
        if situacao == "pendente":
            pendentes.append(t["nome"])
        if (t.get("tipo_geom") or "").strip().lower() == "ponto":
            if (_num(t.get("area_ha")) or 0.0) > 4.0:
                reprovados.append(t["nome"])
            else:
                so_ponto.append(t["nome"])
    via = _doc_id(documentos, "car_recibo", "car_demonstrativo")
    if reprovados:
        return {"satisfeita": 0, "forca": "fraca", "via_documento_id": via,
                "detalhe": "falta poligono ou CAR nao-cancelado para: %s"
                           % ", ".join(sorted(set(reprovados)))}
    if pendentes:
        return {"satisfeita": 1, "forca": "media", "via_documento_id": via,
                "detalhe": "CAR em analise 'Pendente' em %d talhao(oes) - "
                           "passa, mas com forca media" % len(pendentes)}
    if so_ponto:
        return {"satisfeita": 1, "forca": "fraca", "via_documento_id": via,
                "detalhe": "%d talhao(oes) entregues como ponto dentro do "
                           "limite de 4 ha" % len(so_ponto)}
    return {"satisfeita": 1, "forca": "forte", "via_documento_id": via,
            "detalhe": "todos os talhoes com poligono e CAR nao-cancelado"}


def _camada_2(produtor: dict, talhoes: list, documentos: list) -> dict:
    """Hierarquia: matricula -> titulo -> posse corroborada por CCIR/DITR."""
    presentes = {d.get("tipo") for d in documentos}
    for tipo, forca, rotulo in HIERARQUIA_CAMADA_2:
        if tipo not in presentes:
            continue
        via = _doc_id(documentos, tipo)
        if forca == "fraca":
            # Posse so fecha se houver CCIR ou DITR em nome proprio.
            corroborante = _doc_id(documentos, "ccir", "itr")
            if not corroborante:
                return {"satisfeita": 0, "forca": "fraca",
                        "via_documento_id": via,
                        "detalhe": "ha %s, mas falta o CCIR ou o DITR/CIB em "
                                   "nome proprio que o corrobora" % rotulo}
            return {"satisfeita": 1, "forca": "fraca", "via_documento_id": via,
                    "detalhe": "%s, corroborada por CCIR ou DITR" % rotulo}
        return {"satisfeita": 1, "forca": forca, "via_documento_id": via,
                "detalhe": rotulo}
    return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
            "detalhe": "falta um documento de direito de uso da area: "
                       "matricula, titulo ou declaracao de posse com CCIR"}


def _camada_3(produtor: dict, talhoes: list, documentos: list) -> dict:
    """CPF valido + CAF ativo. Na falta: ficha de cooperado + inscricao
    estadual de produtor."""
    cpf = _digitos(produtor.get("cpf"))
    if len(cpf) != 11:
        return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
                "detalhe": "falta o CPF de 11 digitos no cadastro"}
    via_caf = _doc_id(documentos, "caf", "dap")
    if via_caf:
        return {"satisfeita": 1, "forca": "forte", "via_documento_id": via_caf,
                "detalhe": "CPF valido e CAF/DAP entre os documentos"}
    via_ie = _doc_id(documentos, "inscricao_estadual", "ficha_cooperado")
    if via_ie:
        return {"satisfeita": 1, "forca": "media", "via_documento_id": via_ie,
                "detalhe": "CPF valido e inscricao estadual de produtor ou "
                           "ficha de cooperado, na falta do CAF"}
    if produtor.get("cooperativa"):
        # O vinculo de cooperado esta no cadastro da cooperativa, nao em papel
        # entregue pelo produtor. Vale como degrau mais fraco, e fica dito.
        return {"satisfeita": 1, "forca": "fraca", "via_documento_id": None,
                "detalhe": "CPF valido e vinculo de cooperado registrado em "
                           "%s; falta o CAF ou a ficha de cooperado assinada "
                           "para subir de forca" % produtor["cooperativa"]}
    return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
            "detalhe": "falta o CAF ou a ficha de cooperado que prove o "
                       "vinculo"}


def _camada_4(produtor: dict, talhoes: list, documentos: list) -> dict:
    """NF-e do produtor ou contranota da cooperativa nomeando o produtor."""
    via_nf = _doc_id(documentos, "nota_fiscal_produtor")
    if via_nf:
        return {"satisfeita": 1, "forca": "forte", "via_documento_id": via_nf,
                "detalhe": "nota fiscal do proprio produtor"}
    via_contranota = _doc_id(documentos, "contranota", "nota_fiscal_entrada")
    if via_contranota:
        return {"satisfeita": 1, "forca": "media",
                "via_documento_id": via_contranota,
                "detalhe": "contranota da cooperativa nomeando o produtor "
                           "como remetente"}
    return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
            "detalhe": "falta a nota fiscal do produtor ou a contranota da "
                       "cooperativa que registre a transacao"}


def _camada_5(produtor: dict, talhoes: list, documentos: list) -> dict:
    """Checagens negativas na data: 01 (desmate), 02 (embargo),
    04 (sobreposicao) e 07 (Lista Suja). Evidencia que o sistema GERA."""
    negativas = ("01", "02", "04", "07")
    ultimas = _ultimas_checagens_por_talhao_detalhado()
    problemas, avaliadas = [], 0
    for t in talhoes:
        por_codigo = ultimas.get(t["id"], {})
        for codigo in negativas:
            linha = por_codigo.get(codigo)
            if not linha:
                continue
            avaliadas += 1
            if linha["resultado"] != "conforme":
                problemas.append("%s na checagem %s (%s)"
                                 % (t["nome"], codigo, linha["resultado"]))
    if not avaliadas:
        return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
                "detalhe": "as checagens negativas ainda nao rodaram para os "
                           "talhoes deste produtor"}
    if problemas:
        return {"satisfeita": 0, "forca": "fraca", "via_documento_id": None,
                "detalhe": "checagem negativa em aberto: %s"
                           % "; ".join(problemas[:4])}
    return {"satisfeita": 1, "forca": "forte", "via_documento_id": None,
            "detalhe": "%d checagens negativas conformes na data da consulta"
                       % avaliadas}


CAMADAS = {1: _camada_1, 2: _camada_2, 3: _camada_3, 4: _camada_4,
           5: _camada_5}


def _ultimas_checagens_por_talhao_detalhado() -> dict:
    """talhao_id -> {codigo agregado: linha da ultima checagem}."""
    if "ultimas_detalhado" in _cache:
        return _cache["ultimas_detalhado"]
    marcadores = ",".join("?" for _ in CODIGOS_AGREGADOS)
    linhas = db.consultar(
        "SELECT c.talhao_id, c.codigo, c.resultado, c.severidade FROM "
        "checagem c JOIN (SELECT talhao_id, codigo, MAX(rowid) AS r FROM "
        "checagem WHERE codigo IN (%s) GROUP BY talhao_id, codigo) u "
        "  ON u.talhao_id = c.talhao_id AND u.codigo = c.codigo "
        " AND u.r = c.rowid" % marcadores, tuple(CODIGOS_AGREGADOS))
    mapa = {}
    for linha in linhas:
        mapa.setdefault(linha["talhao_id"], {})[linha["codigo"]] = linha
    _cache["ultimas_detalhado"] = mapa
    return mapa


# ---------------------------------------------------------------------------
# SEVERIDADE B BLOQUEIA A APTIDAO ATE RESOLVER (correcoes-spec_1.md secao 04)
# ---------------------------------------------------------------------------
# Ate aqui as regras B documentais da checagem 05 nao tinham efeito nenhum na
# tabela `aptidao`: um produtor com R01 disparada podia sair com as cinco
# camadas satisfeitas. Este mapa e a ligacao que faltava - cada regra B derruba
# a camada cuja PROVA ela contradiz, e o detalhe da camada diz qual regra
# bloqueou.
#
# O principio do contrato continua intacto: B bloqueia a APTIDAO, nunca o
# LOTE. Quem derruba lote para 'bloqueado' sao e continuam sendo as checagens
# 01, 02 e 04 (ver `recalcular_status_lotes` e CODIGOS_AGREGADOS).
#
# | Regra | Camada | Por que essa camada                                     |
# |-------|--------|---------------------------------------------------------|
# | R13   |   1    | talhao fora do perimetro do CAR: a parcela geolocalizada |
# |       |        | nao esta provada                                         |
# | R14   |   1    | talhao > 4 ha entregue como ponto: falta o poligono do   |
# |       |        | Art. 2(28)                                               |
# | R29   |   1    | CAR Cancelado: a camada 1 exige CAR nao-cancelado        |
# | R01   |  4/2   | CPF do emitente da NF != CPF do titular do CAR. Se ha    |
# |       |        | nota, o documento em conflito e a NF -> camada 4; se nao |
# |       |        | ha nota nenhuma, o conflito e de titularidade -> camada 2|
# | R16   |   5    | embargo: checagem negativa na data do dossie             |
# | R17   |   5    | desmate pos-2020: checagem negativa                      |
# | R18   |   5    | terra indigena: checagem negativa                        |
# | R19   |   5    | unidade de conservacao: checagem negativa                |
# | R08   |   5    | Lista Suja do MTE: checagem negativa                     |
REGRA_B_CAMADA = {
    "R13": 1, "R14": 1, "R29": 1,
    "R01": 4,                      # ou 2, ver _camada_da_regra_b
    "R16": 5, "R17": 5, "R18": 5, "R19": 5, "R08": 5,
}

# Documentos que fazem a R01 recair sobre a camada 4 (transacao). Sem nenhum
# deles, a divergencia de CPF e de titularidade e recai sobre a camada 2.
DOCS_TRANSACAO = ("nota_fiscal_produtor", "contranota", "nota_fiscal_entrada")


def _camada_da_regra_b(codigo_regra: str, documentos: list) -> int:
    """Camada que a regra B derruba. So a R01 depende do documento."""
    if codigo_regra == "R01":
        presentes = {d.get("tipo") for d in documentos}
        return 4 if presentes & set(DOCS_TRANSACAO) else 2
    return REGRA_B_CAMADA.get(codigo_regra)


def _regras_b_abertas(talhoes: list, documentos: list) -> dict:
    """camada -> lista de regras B disparadas nos talhoes do produtor.

    Le a ULTIMA linha de `checagem` de cada par (talhao, regra) - as linhas
    que `_gravar_regras_05` grava com o codigo oficial da regra - e considera
    apenas as que ficaram com severidade B e resultado diferente de conforme.
    """
    ids = [t["id"] for t in talhoes]
    codigos = sorted(REGRA_B_CAMADA)
    if not ids:
        return {}
    m_ids = ",".join("?" for _ in ids)
    m_cod = ",".join("?" for _ in codigos)
    linhas = db.consultar(
        "SELECT c.talhao_id, c.codigo, c.resultado, c.severidade, c.texto "
        "FROM checagem c JOIN (SELECT talhao_id, codigo, MAX(rowid) AS r "
        "  FROM checagem WHERE codigo IN (%s) AND talhao_id IN (%s) "
        "  GROUP BY talhao_id, codigo) u "
        "  ON u.talhao_id = c.talhao_id AND u.codigo = c.codigo "
        " AND u.r = c.rowid" % (m_cod, m_ids), tuple(codigos) + tuple(ids))
    nomes = {t["id"]: t["nome"] for t in talhoes}
    bloqueios = {}
    for linha in linhas:
        if linha["resultado"] == "conforme" or linha["severidade"] != "B":
            continue
        camada = _camada_da_regra_b(linha["codigo"], documentos)
        if not camada:
            continue
        bloqueios.setdefault(camada, []).append(
            {"regra": linha["codigo"], "talhao": nomes.get(linha["talhao_id"]),
             "texto": linha["texto"]})
    return bloqueios


def avaliar_aptidao(produtor_id: str) -> list:
    """Grava uma linha de `aptidao` por camada (1..5) para o produtor.

    Devolve a lista das cinco linhas gravadas. `via_documento_id` aponta o
    documento que FECHOU a camada - e o que permite a Trilha C mostrar ao
    auditor por qual degrau da hierarquia a prova passou.
    """
    produtor = db.buscar_produtor(produtor_id)
    if not produtor:
        raise ValueError("produtor inexistente: %s" % produtor_id)
    talhoes = db.listar_talhoes(produtor_id)
    documentos = db.listar_documentos(produtor_id)
    momento = db.agora()

    # Regras B disparadas nos talhoes deste produtor: bloqueiam a camada
    # correspondente ate serem resolvidas (correcoes-spec_1.md secao 04).
    bloqueios = _regras_b_abertas(talhoes, documentos)

    gravadas = []
    for camada in sorted(CAMADAS):
        try:
            saida = CAMADAS[camada](produtor, talhoes, documentos)
        except Exception as erro:
            saida = {"satisfeita": 0, "forca": "fraca",
                     "via_documento_id": None,
                     "detalhe": "avaliacao falhou: %s" % erro}
        travas = bloqueios.get(camada, [])
        if travas and saida.get("satisfeita"):
            # A prova documental existe, mas uma regra de severidade B a
            # contradiz: a camada nao fecha ate que a regra seja resolvida.
            # A frase fala da REGRA e do DOCUMENTO, nunca da pessoa.
            saida["satisfeita"] = 0
            saida["forca"] = "fraca"
            saida["detalhe"] = (
                "%s | BLOQUEADA por regra de severidade B em aberto: %s - "
                "severidade B bloqueia a aptidao ate resolver (o lote nao e "
                "barrado por isto)"
                % (saida.get("detalhe") or "prova documental presente",
                   "; ".join("%s no talhao %s" % (t["regra"], t["talhao"])
                             for t in travas)))
        elif travas:
            saida["detalhe"] = (
                "%s | regra(s) B tambem em aberto: %s"
                % (saida.get("detalhe") or "camada aberta",
                   "; ".join("%s no talhao %s" % (t["regra"], t["talhao"])
                             for t in travas)))
        linha = db.inserir_aptidao({
            "produtor_id": produtor_id,
            "camada": camada,
            "satisfeita": int(saida["satisfeita"]),
            "via_documento_id": saida.get("via_documento_id"),
            "forca": saida.get("forca"),
            "avaliado_em": momento})
        linha["detalhe"] = saida.get("detalhe")
        gravadas.append(linha)

    fechadas = sum(1 for g in gravadas if g["satisfeita"])
    db.registrar_evento(
        "sistema", "aptidao_avaliada", "produtor", produtor_id,
        "Aptidao de %s avaliada nas cinco camadas: %d fechada(s) - %s"
        % (produtor.get("nome") or produtor_id, fechadas,
           "; ".join("camada %d %s (%s)"
                     % (g["camada"], "ok" if g["satisfeita"] else "aberta",
                        g["forca"]) for g in gravadas)))
    return gravadas


def avaliar_aptidao_de_todos(silencioso: bool = False) -> dict:
    """Roda `avaliar_aptidao` nos 60 produtores. Chamada por verificar_tudo."""
    _cache.pop("ultimas_detalhado", None)   # le as checagens recem-gravadas
    produtores = db.listar_produtores()
    por_camada = {c: {"satisfeitas": 0, "abertas": 0} for c in CAMADAS}
    por_forca = {"forte": 0, "media": 0, "fraca": 0}
    for produtor in produtores:
        for linha in avaliar_aptidao(produtor["id"]):
            chave = "satisfeitas" if linha["satisfeita"] else "abertas"
            por_camada[linha["camada"]][chave] += 1
            if linha["satisfeita"]:
                por_forca[linha["forca"]] = por_forca.get(linha["forca"], 0) + 1
    if not silencioso:
        print("")
        print("APTIDAO EM CINCO CAMADAS  |  %d produtores  |  hierarquia de "
              "alternativas, nao checklist" % len(produtores))
        for camada in sorted(por_camada):
            c = por_camada[camada]
            print("  camada %d  %-52s fechada %3d | aberta %3d"
                  % (camada, NOME_CAMADA[camada][:52], c["satisfeitas"],
                     c["abertas"]))
        print("  forca das camadas fechadas: forte %d | media %d | fraca %d"
              % (por_forca.get("forte", 0), por_forca.get("media", 0),
                 por_forca.get("fraca", 0)))
    return {"produtores": len(produtores), "por_camada": por_camada,
            "por_forca": por_forca}


def verificar_tudo(silencioso: bool = False) -> dict:
    """Roda as sete checagens em todos os talhoes e avalia a aptidao."""
    talhoes = db.listar("talhao", ordem="nome")
    total = len(talhoes)
    if not silencioso:
        print("")
        print("=" * 78)
        print("TRILHA B - VERIFICACAO  |  %d talhoes  |  consulta de %s"
              % (total, hoje()))
        print("=" * 78)
        print("Bases: embargos Ibama R-01 atualizada em %s | camadas das "
              "checagens 01, 04 e 07 SEMEADAS (declaradas no laudo, ADR-012)"
              % data_base_r01())
        print("-" * 78)

    contagem = {c: {"conforme": 0, "excecao": 0, "bloqueio": 0}
                for c, _, _ in CHECAGENS}
    piores = {"conforme": 0, "excecao": 0, "bloqueio": 0}
    destaques = []

    for i, talhao in enumerate(talhoes, start=1):
        resumo = verificar_talhao(talhao["id"])
        for codigo, resultado in resumo["resultados"].items():
            contagem[codigo][resultado] += 1
        piores[resumo["pior"]] += 1
        if resumo["pior"] != "conforme":
            destaques.append((talhao, resumo))
        if not silencioso:
            marca = {"conforme": "  ok  ", "excecao": " ATENC", "bloqueio": "BLOQUE"}
            linha = " ".join(
                "%s:%s" % (c, resumo["resultados"][c][:4].upper())
                for c, _, _ in CHECAGENS)
            print("[%3d/%3d] %-24s %s  ->  %s"
                  % (i, total, talhao["nome"][:24], linha,
                     marca[resumo["pior"]]))

    if not silencioso:
        print("-" * 78)
        print("RESULTADO POR CHECAGEM")
        for codigo, nome, _ in CHECAGENS:
            c = contagem[codigo]
            print("  %s %-26s conforme %3d | excecao %3d | bloqueio %3d"
                  % (codigo, nome, c["conforme"], c["excecao"], c["bloqueio"]))
        print("-" * 78)
        print("TALHOES  conforme %d | em excecao %d | bloqueados %d"
              % (piores["conforme"], piores["excecao"], piores["bloqueio"]))

        # As regras da 05 que efetivamente dispararam em algum talhao
        disparadas = regras_05_disparadas()
        print("REGRAS DA CHECAGEM 05 QUE DISPARARAM: %s"
              % (", ".join("%s (%d talhoes)" % (r, n)
                           for r, n in disparadas.items()) or "nenhuma"))
        print("-" * 78)
        print("BLOQUEIOS E EXCECOES POR TALHAO (as %d nao conformes)"
              % len(destaques))
        for talhao, resumo in destaques[:40]:
            nao_conformes = [c for c, r in resumo["resultados"].items()
                             if r != "conforme"]
            lotes = ", ".join(l["codigo"]
                              for l in db.lotes_do_talhao(talhao["id"]))
            print("  %-24s %-8s checagens %s  lotes: %s"
                  % (talhao["nome"][:24], resumo["pior"].upper(),
                     ",".join(nao_conformes), lotes or "-"))
        if len(destaques) > 40:
            print("  ... e mais %d talhao(oes)" % (len(destaques) - 40))
        print("=" * 78)

    # A aptidao le as checagens recem-gravadas: roda DEPOIS delas.
    aptidao = avaliar_aptidao_de_todos(silencioso)

    db.registrar_evento(
        "sistema", "verificacao_completa", "talhao", None,
        "Verificacao completa: %d talhoes, %d bloqueados, %d em excecao"
        % (total, piores["bloqueio"], piores["excecao"]))

    return {"talhoes": total, "por_checagem": contagem, "piores": piores,
            "aptidao": aptidao}


def regras_05_disparadas() -> dict:
    """Quais regras da 05 dispararam e em quantos talhoes - lido do banco."""
    contagem = {}
    for linha in db.consultar(
            "SELECT evidencia_json FROM checagem WHERE codigo = '05'"):
        try:
            dados = json.loads(linha["evidencia_json"] or "{}")
        except ValueError:
            continue
        for regra in dados.get("evidencia", {}).get("regras_disparadas", []):
            contagem[regra] = contagem.get(regra, 0) + 1
    # Ordena por codigo oficial. Nao ha mais codigo composto: R18 e R19 sao
    # linhas separadas desde o rebaixamento por categoria da area.
    def _chave(kv):
        digitos = re.findall(r"\d+", kv[0])
        return int(digitos[0]) if digitos else 999
    return dict(sorted(contagem.items(), key=_chave))


def _ultimas_checagens_por_talhao() -> dict:
    """Ultimo resultado de cada checagem de cada talhao (por data_execucao)."""
    # So os codigos agregados ('01'..'07'). As linhas gravadas com codigo de
    # regra (R01, R17...) sao detalhe da 05: soma-las de novo contaria o mesmo
    # achado duas vezes no status do lote.
    marcadores = ",".join("?" for _ in CODIGOS_AGREGADOS)
    linhas = db.consultar(
        "SELECT c.talhao_id, c.codigo, c.resultado FROM checagem c "
        "JOIN (SELECT talhao_id, codigo, MAX(data_execucao) AS m, MAX(rowid) "
        "      AS r FROM checagem WHERE codigo IN (%s) "
        "      GROUP BY talhao_id, codigo) u "
        "  ON u.talhao_id = c.talhao_id AND u.codigo = c.codigo "
        " AND u.r = c.rowid" % marcadores, tuple(CODIGOS_AGREGADOS))
    por_talhao = {}
    for linha in linhas:
        por_talhao.setdefault(linha["talhao_id"], []).append(linha["resultado"])
    return por_talhao


def recalcular_status_lotes(silencioso: bool = False) -> dict:
    """Define lote.status pelo PIOR resultado entre os talhoes do lote.

    qualquer bloqueio -> 'bloqueado'; qualquer excecao -> 'atencao';
    senao 'verde'. (SPEC 4.4)
    """
    por_talhao = _ultimas_checagens_por_talhao()
    mapa = {"conforme": "verde", "excecao": "atencao", "bloqueio": "bloqueado"}
    saida = {}
    if not silencioso:
        print("")
        print("STATUS DOS LOTES (pior resultado entre os talhoes)")
    for lote in db.listar_lotes():
        talhoes = db.talhoes_do_lote(lote["id"])
        pior = "conforme"
        contagem = {"conforme": 0, "excecao": 0, "bloqueio": 0}
        for t in talhoes:
            resultados = por_talhao.get(t["id"], [])
            pior_talhao = "conforme"
            for r in resultados:
                if PIOR.get(r, 0) > PIOR[pior_talhao]:
                    pior_talhao = r
            contagem[pior_talhao] += 1
            if PIOR[pior_talhao] > PIOR[pior]:
                pior = pior_talhao
        novo = mapa[pior]
        anterior = lote.get("status")
        if novo != anterior:
            db.atualizar("lote", lote["id"], {"status": novo})
            db.registrar_evento(
                "sistema", "lote_status_alterado", "lote", lote["id"],
                "Lote %s passou de '%s' para '%s' pelo pior resultado entre "
                "os %d talhoes que o compoem (%d bloqueado(s), %d em excecao)"
                % (lote["codigo"], anterior, novo, len(talhoes),
                   contagem["bloqueio"], contagem["excecao"]))
        saida[lote["codigo"]] = {
            "lote_id": lote["id"], "status": novo, "status_anterior": anterior,
            "talhoes": len(talhoes), "talhoes_bloqueados": contagem["bloqueio"],
            "talhoes_em_excecao": contagem["excecao"],
            "talhoes_conformes": contagem["conforme"]}
        if not silencioso:
            print("  %-14s %-10s %3d talhoes | %d bloqueado(s) | %d em "
                  "excecao%s"
                  % (lote["codigo"], novo.upper(), len(talhoes),
                     contagem["bloqueio"], contagem["excecao"],
                     "" if novo == anterior else "   (era %s)" % anterior))
    return saida


# ===========================================================================
# CLI
# ===========================================================================
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Trilha B - verificacao das sete checagens EUDR.")
    parser.add_argument("--tudo", action="store_true",
                        help="roda as sete checagens em todos os talhoes e avalia a aptidao")
    parser.add_argument("--talhao", metavar="ID",
                        help="roda as sete checagens em um talhao")
    parser.add_argument("--lotes", action="store_true",
                        help="apenas recalcula o status dos lotes")
    parser.add_argument("--aptidao", action="store_true",
                        help="apenas reavalia a aptidao dos 60 produtores")
    args = parser.parse_args(argv)

    db.criar_esquema()

    if args.talhao:
        resumo = verificar_talhao(args.talhao)
        talhao = db.buscar_talhao(args.talhao)
        print("")
        print("Talhao %s (%s) - pior resultado: %s"
              % (talhao["nome"], args.talhao, resumo["pior"].upper()))
        for linha in db.consultar(
                "SELECT codigo, perna, categoria, severidade, resultado, "
                "texto FROM checagem WHERE talhao_id = ? AND codigo IN "
                "('01','02','03','04','05','06','07') "
                "ORDER BY data_execucao DESC, codigo LIMIT 7",
                (args.talhao,)):
            print("")
            print("  [%s | perna %s | categoria %s | severidade %s] %s"
                  % (linha["codigo"], linha["perna"], linha["categoria"],
                     linha["severidade"], linha["resultado"].upper()))
            print("  %s" % linha["texto"])
        recalcular_status_lotes()
        return 0

    if args.lotes:
        recalcular_status_lotes()
        return 0

    if args.aptidao:
        avaliar_aptidao_de_todos()
        return 0

    if args.tudo or True:      # sem argumento, o padrao util e rodar tudo
        verificar_tudo()
        recalcular_status_lotes()
        contadores = db.contadores_autonomia()
        print("")
        print("AUTONOMIA  %d verificacoes executadas | %d documentos "
              "processados | %d excecoes para humano"
              % (contadores["verificacoes_executadas"],
                 contadores["documentos_processados"],
                 contadores["excecoes_para_humano"]))
        if contadores["documentos_processados"] == 0:
            print("AVISO: a tabela `documento` esta vazia - a Trilha A ainda "
                   "nao rodou. A checagem 05 sai como excecao por lacuna "
                   "total (R48) em todos os talhoes; reexecute "
                   "`python verificacao.py --tudo` depois da ingestao.")
        print("")
    return 0


if __name__ == "__main__":
    # erro de configuracao (params/cacau.yml) sai como mensagem, nao traceback
    try:
        sys.exit(main())
    except ValueError as _erro:
        print("ERRO DE CONFIGURACAO: %s" % _erro)
        sys.exit(2)
