# -*- coding: utf-8 -*-
"""seed.py - base semeada da Trilha 0 (Fundacao).

Semente fixa (SEMENTE = 20260830): rodar duas vezes produz exatamente a mesma
base. Popula produtor, talhao, lote e lote_talhao, e gera os grupos de arquivos
crus em dados/entrada/<produtor_slug>/.

O que e REAL aqui: os poligonos de embargo do Ibama, lidos de dados/bases/.
O que e SEMEADO: produtores, talhoes, lotes e documentos - tudo ficticio.
CPF ficticio de formato valido (digitos verificadores corretos), nome de
pessoa inventado. Nenhum dado pessoal real entra nesta base.

Conflitos plantados de proposito (SPEC.md secao 8):
  - 4 talhoes SOBREPOSTOS a poligonos de embargo reais -> checagem 02 bloqueio
  - 3 talhoes a menos de 500 m da borda de um embargo -> checagem 02 excecao
  - 3 lotes com sobreposicao, um produtor nos tres ao mesmo tempo
  - 5 armadilhas documentais, em produtores diferentes

Nao implementa ingestao, verificacao, dossie nem interface.
"""
import json
import math
import random
import shutil
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from shapely.geometry import Point, Polygon, mapping  # noqa: F401
from shapely.ops import unary_union

import db
import geo

SEMENTE = 20260830
RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "dados" / "entrada"
PADRONIZADO = RAIZ / "dados" / "padronizado"

MUNICIPIOS = ["Medicilandia", "Altamira", "Uruara", "Brasil Novo"]

# Envelope generoso dos quatro municipios do recorte (WGS84). A base bruta do
# Ibama traz linhas com MUNICIPIO certo mas geometria em outro canto do pais
# (erro de cadastro na origem); tudo que cai fora deste retangulo e descartado
# como ancora, senao o talhao semeado nasce a mil quilometros do produtor.
ENVELOPE_LON = (-55.9, -51.7)
ENVELOPE_LAT = (-9.9, -2.7)
COOPERATIVA = "Cooperativa Agroindustrial da Transamazonica - CACAUTRANS"
UF = "PA"

# Codigo do lote citado no roteiro da demo (SPEC.md secao 10)
CODIGO_LOTE_DEMO = "CAC-2026-114"

PRENOMES = [
    "Jose", "Maria", "Antonio", "Francisca", "Joao", "Ana", "Raimundo",
    "Rosa", "Manoel", "Terezinha", "Sebastiao", "Luzia", "Pedro", "Marlene",
    "Francisco", "Cleuza", "Domingos", "Ivanilde", "Adriano", "Sueli",
    "Valdir", "Neide", "Genivaldo", "Elizete",
    "Osmar", "Marinalva", "Edvaldo", "Zilda", "Nilson", "Creuza",
]
SOBRENOMES = [
    "da Silva", "dos Santos", "Ferreira", "Oliveira", "Souza", "Lima",
    "Pereira", "Alves", "Rodrigues", "Nascimento", "Barbosa", "Cardoso",
    "Moraes", "Batista", "Ribeiro", "Gomes", "Carvalho", "Araujo",
    "Monteiro", "Vieira", "Rocha", "Machado", "Teixeira", "Freitas",
]

COMPRADORES = [
    "Barry Callebaut Belgium NV",
    "Chocolats Halba / Coop Suisse",
    "Cemoi Chocolatier SAS",
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def sem_acento(texto: str) -> str:
    """Remove acentos. Usado no slug do produtor."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def criar_slug(nome: str) -> str:
    """'Jose da Silva' -> 'jose-da-silva'. Sem acento, so a-z, 0-9 e hifen."""
    base = sem_acento(nome).lower()
    limpo = "".join(c if c.isalnum() else "-" for c in base)
    while "--" in limpo:
        limpo = limpo.replace("--", "-")
    return limpo.strip("-")


def cpf_ficticio(rnd: random.Random) -> str:
    """CPF ficticio com digitos verificadores corretos (formato valido).

    Nao corresponde a pessoa nenhuma - os nove primeiros digitos sao sorteados.
    Precisa ser de formato valido para a Trilha A exercitar a validacao.
    """
    n = [rnd.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        peso = len(n) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(n))
        resto = (soma * 10) % 11
        n.append(0 if resto == 10 else resto)
    d = "".join(str(x) for x in n)
    return "%s.%s.%s-%s" % (d[:3], d[3:6], d[6:9], d[9:])


def ponto_dentro(poligono, rnd: random.Random, tentativas: int = 400):
    """Sorteia um ponto dentro de um poligono, por rejeicao."""
    minx, miny, maxx, maxy = poligono.bounds
    for _ in range(tentativas):
        p = Point(rnd.uniform(minx, maxx), rnd.uniform(miny, maxy))
        if poligono.contains(p):
            return p
    return poligono.representative_point()


def quadrado_ha(centro: Point, area_ha: float) -> Polygon:
    """Quadrado aproximado com a area pedida, centrado no ponto (EPSG:4326).

    1 grau de latitude ~ 111.320 m. Perto do equador a longitude vale quase o
    mesmo, e o erro e irrelevante para talhao de poucos hectares.
    """
    lado_m = (area_ha * 10_000.0) ** 0.5
    meio = (lado_m / 2.0) / 111_320.0
    x, y = centro.x, centro.y
    return Polygon([(x - meio, y - meio), (x + meio, y - meio),
                    (x + meio, y + meio), (x - meio, y + meio)])


def graus(metros: float) -> float:
    """Metros -> graus de arco, aproximacao boa para a latitude do recorte."""
    return metros / 111_320.0


def no_envelope(x: float, y: float) -> bool:
    """Ponto dentro do retangulo dos quatro municipios do recorte."""
    return (ENVELOPE_LON[0] < x < ENVELOPE_LON[1]
            and ENVELOPE_LAT[0] < y < ENVELOPE_LAT[1])


def ancoras_por_municipio(embargos) -> dict:
    """Embargos REAIS utilizaveis como ancora, agrupados por municipio.

    Duas filtragens, nesta ordem:
      1. o centroide tem que cair no envelope do recorte - a base do Ibama tem
         linhas com MUNICIPIO da Transamazonica e geometria em outro canto do
         pais (erro de cadastro na origem), e era isso que jogava talhao
         semeado para fora da regiao;
      2. o municipio, sem acento, tem que ser um dos quatro do recorte.

    Cada lista sai ordenada por area decrescente (deterministico), para que os
    conflitos deliberados possam pegar os maiores poligonos e caber dentro.
    """
    grupos = {m: [] for m in MUNICIPIOS}
    for posicao, linha in enumerate(embargos.itertuples(index=False)):
        municipio = sem_acento(str(getattr(linha, "MUNICIPIO", "") or "")).strip()
        if municipio not in grupos:
            continue
        geom = linha.geometry
        if geom is None or geom.is_empty:
            continue
        centro = geom.centroid
        if not no_envelope(centro.x, centro.y):
            continue
        grupos[municipio].append({
            "chave": posicao,
            "geom": geom,
            "area": geom.area,
            "tad": str(getattr(linha, "NUM_TAD", "") or "").strip() or "-",
        })
    for municipio, itens in grupos.items():
        itens.sort(key=lambda a: (-a["area"], a["chave"]))
        if not itens:
            raise ValueError(
                "nenhum embargo real utilizavel em %s - sem ancora para "
                "semear talhao no municipio" % municipio)
    return grupos


# ---------------------------------------------------------------------------
# Geracao de produtores
# ---------------------------------------------------------------------------
def gerar_produtores(rnd: random.Random, quantidade: int = 60) -> list:
    """60 produtores com nome plausivel, CPF ficticio valido e slug sem acento."""
    vistos, produtores = set(), []
    while len(produtores) < quantidade:
        nome = "%s %s" % (rnd.choice(PRENOMES), rnd.choice(SOBRENOMES))
        if rnd.random() < 0.35:  # alguns com nome composto
            nome = "%s %s %s" % (nome.split()[0], rnd.choice(SOBRENOMES),
                                 nome.split(maxsplit=1)[1])
        slug = criar_slug(nome)
        if slug in vistos:
            continue
        vistos.add(slug)
        produtores.append({
            "id": db.novo_id(),
            "nome": nome,
            "cpf": cpf_ficticio(rnd),
            "municipio": rnd.choice(MUNICIPIOS),
            "uf": UF,
            "cooperativa": COOPERATIVA,
            "slug": slug,
        })
    return produtores


# ---------------------------------------------------------------------------
# Geracao de talhoes
# ---------------------------------------------------------------------------
def gerar_talhoes(rnd: random.Random, produtores: list, embargos) -> tuple:
    """1 a 3 talhoes por produtor, 2 a 10 ha, ponto ou poligono.

    Devolve (talhoes, plantados) onde `plantados` documenta os conflitos
    deliberados para o relatorio final.
    """
    # Ancoras: embargos reais, por municipio, ja filtrados pelo envelope do
    # recorte. Todo talhao - normal ou conflituoso - nasce a poucos km de uma
    # ancora do MESMO municipio do produtor. Antes o sorteio era uniforme no
    # total_bounds da camada bruta (que vai de -59 a -47 de longitude e de
    # -15,8 a +4,4 de latitude, por causa das linhas com geometria errada na
    # origem), e por isso a maioria dos talhoes caia fora da Transamazonica.
    ancoras = ancoras_por_municipio(embargos)

    # Uniao de TODOS os embargos do recorte, nao so dos alvos: e contra ela
    # que se garante que talhao normal fica longe e que talhao limitrofe fica
    # perto sem tocar.
    uniao = unary_union(list(embargos.geometry))

    talhoes = []
    plantados = {"sobrepostos": [], "limitrofes": []}

    # produtores que recebem os conflitos: distintos entre si, e nenhum e o
    # produtor-pivo dos tres lotes (ele leva o embargo injetado ao vivo)
    escolhidos = [p for p in produtores[1:]]
    rnd.shuffle(escolhidos)
    donos_sobre = escolhidos[:4]
    donos_limite = escolhidos[4:7]
    # cada conflito recebe uma ancora do proprio municipio do produtor, tirada
    # da faixa dos maiores poligonos - para caber um talhao de ate 4 ha dentro
    usadas, mapa_sobre, mapa_limite = set(), {}, {}
    for destino, donos, faixa in ((mapa_sobre, donos_sobre, 40),
                                  (mapa_limite, donos_limite, 60)):
        for dono in donos:
            pool = [a for a in ancoras[dono["municipio"]][:faixa]
                    if a["chave"] not in usadas]
            escolhida = pool[rnd.randrange(len(pool))]
            usadas.add(escolhida["chave"])
            destino[dono["id"]] = escolhida

    for produtor in produtores:
        quantos = rnd.randint(1, 3)
        for n in range(1, quantos + 1):
            area_ha = round(rnd.uniform(2.0, 10.0), 2)
            nome = "Talhao %s-%02d" % (produtor["slug"][:8].upper(), n)
            conflito = None

            if n == 1 and produtor["id"] in mapa_sobre:
                # --- CONFLITO A: talhao dentro de um embargo real ---
                ancora = mapa_sobre[produtor["id"]]
                alvo, termo = ancora["geom"], ancora["tad"]
                centro = ponto_dentro(alvo, rnd)
                # area menor, para caber dentro do embargo com folga
                area_ha = round(min(area_ha, 4.0), 2)
                conflito = ("sobrepostos", termo)
            elif n == 1 and produtor["id"] in mapa_limite:
                # --- CONFLITO B: a menos de 500 m da borda, sem tocar ---
                ancora = mapa_limite[produtor["id"]]
                alvo, termo = ancora["geom"], ancora["tad"]
                area_ha = round(min(area_ha, 3.0), 2)
                fronteira = alvo.boundary
                cx, cy = alvo.centroid.x, alvo.centroid.y
                # Empurra o talhao para fora ate ele parar de tocar QUALQUER
                # embargo, mas ainda ficar a menos de 500 m do mais proximo.
                # A busca e explicita porque poligono concavo faz a direcao
                # "centroide -> borda" reentrar no proprio poligono.
                centro = None
                for tentativa in range(60):
                    borda = fronteira.interpolate(
                        rnd.random(), normalized=True)
                    dx, dy = borda.x - cx, borda.y - cy
                    comp = max((dx * dx + dy * dy) ** 0.5, 1e-9)
                    for metros in (260, 300, 340, 380, 420):
                        afast = graus(metros)
                        cand = Point(borda.x + dx / comp * afast,
                                     borda.y + dy / comp * afast)
                        quadrado = quadrado_ha(cand, area_ha)
                        if uniao.intersects(quadrado):
                            continue
                        dist_graus = uniao.distance(quadrado)
                        if 0 < dist_graus < graus(480):
                            centro = cand
                            break
                    if centro is not None:
                        break
                if centro is None:      # nao deve acontecer com esta semente
                    centro = Point(cx, cy)
                conflito = ("limitrofes", termo)
            else:
                # --- talhao normal: perto de uma ancora do municipio do
                # produtor, mas fora de qualquer embargo ---
                pool = ancoras[produtor["municipio"]]
                centro = None
                # 1a passada exige folga de 600 m para qualquer embargo; a 2a
                # so exige nao encostar, para nunca ficar sem ponto valido
                for folga_m in (600.0, 0.0):
                    for _ in range(300):
                        base = pool[rnd.randrange(len(pool))]["geom"].centroid
                        raio = graus(rnd.uniform(900.0, 7000.0))
                        angulo = rnd.uniform(0.0, 2.0 * math.pi)
                        x = base.x + raio * math.cos(angulo)
                        y = base.y + raio * math.sin(angulo)
                        if not no_envelope(x, y):
                            continue
                        tentativa = Point(x, y)
                        if folga_m:
                            alcance = tentativa.buffer(graus(folga_m))
                        else:
                            alcance = tentativa
                        if uniao.intersects(alcance):
                            continue
                        centro = tentativa
                        break
                    if centro is not None:
                        break

            # mistura ponto e poligono; conflitos sempre poligono, para a
            # checagem 02 poder medir area de intersecao
            usa_poligono = conflito is not None or rnd.random() < 0.6
            if usa_poligono:
                geom = quadrado_ha(centro, area_ha)
                tipo_geom = "poligono"
            else:
                geom = centro
                tipo_geom = "ponto"

            talhao = {
                "id": db.novo_id(),
                "produtor_id": produtor["id"],
                "nome": nome,
                "area_ha": area_ha,
                "geom_wkt": geom.wkt,
                "tipo_geom": tipo_geom,
                "car_numero": "PA-15%05d-%s" % (
                    rnd.randint(0, 99999),
                    "".join(rnd.choice("ABCDEF0123456789") for _ in range(8))),
                "car_situacao": rnd.choices(
                    ["ativo", "pendente", "cancelado"],
                    weights=[88, 9, 3])[0],
            }
            talhoes.append(talhao)

            if conflito:
                plantados[conflito[0]].append({
                    "talhao_id": talhao["id"], "talhao": nome,
                    "produtor": produtor["nome"], "slug": produtor["slug"],
                    "num_tad_embargo": conflito[1], "area_ha": area_ha,
                })
    return talhoes, plantados


# ---------------------------------------------------------------------------
# Geracao de lotes
# ---------------------------------------------------------------------------
def gerar_lotes(rnd: random.Random, produtores: list, talhoes: list,
                plantados: dict = None) -> tuple:
    """3 lotes de embarque com sobreposicao deliberada.

    O produtor de indice 0 (o pivo) entra nos TRES lotes. E dele o talhao que
    demo/injetar_embargo.py cobre ao vivo - um embargo derruba tres dossies.

    IMPORTANTE (correcao da demo): os 4 talhoes plantados SOBRE embargo real e
    os 3 limitrofes NAO entram em lote nenhum. Eles continuam existindo no
    banco - viram material da tela de excecoes - mas se ficassem dentro dos
    lotes, os tres ja sairiam 'bloqueado' antes de demo/injetar_embargo.py e a
    virada de cor no palco nunca aconteceria. Antes da injecao os lotes tem
    que estar 'verde' ou 'atencao'; a injecao e que os derruba.
    """
    excluidos = set()
    for chave in ("sobrepostos", "limitrofes"):
        for p in (plantados or {}).get(chave, []):
            excluidos.add(p["talhao_id"])

    por_produtor = {}
    for t in talhoes:
        if t["id"] in excluidos:
            continue                    # fica fora dos lotes, de proposito
        por_produtor.setdefault(t["produtor_id"], []).append(t)

    pivo = produtores[0]
    outros = produtores[1:]

    hoje = date(2026, 8, 30)
    lotes, vinculos = [], []
    tamanhos = [24, 18, 31]      # entre 10 e 40 produtores por lote
    codigos = [CODIGO_LOTE_DEMO, "CAC-2026-115", "CAC-2026-117"]

    for i, (codigo, tamanho) in enumerate(zip(codigos, tamanhos)):
        # o pivo sempre entra; o resto e sorteado, com sobreposicao natural
        selecionados = [pivo] + rnd.sample(outros, tamanho - 1)
        lote_id = db.novo_id()
        total_kg = 0.0
        for produtor in selecionados:
            for talhao in por_produtor.get(produtor["id"], []):
                # volume coerente: area x produtividade PA, com ruido
                esperado = talhao["area_ha"] * 900.0
                kg = round(esperado * rnd.uniform(0.55, 0.95), 1)
                vinculos.append({"lote_id": lote_id,
                                 "talhao_id": talhao["id"],
                                 "quantidade_kg": kg})
                total_kg += kg
        lotes.append({
            "id": lote_id,
            "codigo": codigo,
            "commodity": "cacau",
            "safra": "2026",
            "quantidade_kg": round(total_kg, 1),
            "comprador": COMPRADORES[i],
            "data_embarque": (hoje + timedelta(days=21 + i * 14)).isoformat(),
            "status": "verde",   # a Trilha B recalcula
        })
    return lotes, vinculos, pivo


# ---------------------------------------------------------------------------
# NF-e: chave de acesso de 44 digitos
# ---------------------------------------------------------------------------
# Layout (o mesmo que ingestao.decompor_chave_acesso quebra):
#   cUF(2) AAMM(4) CNPJ/CPF(14) mod(2) serie(3) nNF(9) tpEmis(1) cNF(8) cDV(1)
# Na NF-e de produtor rural pessoa fisica o CPF entra no campo de 14 posicoes
# do CNPJ com ZEROS A ESQUERDA, e a serie fica na faixa 920-969.
CUF_PARA = "15"                      # codigo IBGE da UF do Para
SERIE_PF_MIN, SERIE_PF_MAX = 920, 969


def digito_chave_nfe(base43: str) -> str:
    """Digito verificador da chave (modulo 11, pesos 2..9 da direita)."""
    peso, soma = 2, 0
    for digito in reversed(base43):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    return "0" if resto in (0, 1) else str(11 - resto)


def montar_chave_nfe(cpf: str, emissao, modelo: str, serie: int,
                     numero: int, rnd: random.Random) -> str:
    """Chave de acesso de 44 digitos, com DV correto, para um emitente PF."""
    so_digitos = "".join(c for c in cpf if c.isdigit())
    campo_documento = so_digitos.zfill(14)        # 000 + 11 digitos do CPF
    base = "%s%s%s%s%03d%09d%d%08d" % (
        CUF_PARA, emissao.strftime("%y%m"), campo_documento, modelo,
        serie, numero, 1, rnd.randint(0, 99999999))
    assert len(base) == 43, len(base)
    return base + digito_chave_nfe(base)


# ---------------------------------------------------------------------------
# Geracao dos arquivos crus
# ---------------------------------------------------------------------------
def texto_documento(tipo: str, produtor: dict, talhao: dict, rnd: random.Random,
                    emissao: date, validade: date = None,
                    cpf_sobrescrito: str = None,
                    variante_nfe: str = None) -> str:
    """Corpo de texto plausivel para o documento, com as palavras-chave do
    params/cacau.yml presentes, para a Trilha A ter o que casar."""
    cpf = cpf_sobrescrito or produtor["cpf"]
    linhas = []
    cab = {
        "car_recibo": ("CADASTRO AMBIENTAL RURAL - RECIBO DE INSCRICAO",
                       "Sistema Nacional de Cadastro Ambiental Rural - SICAR"),
        "car_demonstrativo": ("DEMONSTRATIVO DA SITUACAO DO CADASTRO",
                              "SICAR - Cadastro Ambiental Rural"),
        "ccir": ("CCIR - CERTIFICADO DE CADASTRO DE IMOVEL RURAL",
                 "INCRA - Instituto Nacional de Colonizacao e Reforma Agraria"),
        "matricula_imovel": ("CERTIDAO DE MATRICULA DE IMOVEL",
                             "Cartorio de Registro de Imoveis da Comarca"),
        "nota_fiscal_produtor": ("NOTA FISCAL DE PRODUTOR RURAL - NFP-e",
                                 "Natureza da operacao: venda de producao propria"),
        "cnd_estadual": ("CERTIDAO NEGATIVA DE DEBITOS ESTADUAIS",
                         "SEFAZ - Secretaria de Estado da Fazenda do Para"),
        "cnd_federal": ("CERTIDAO NEGATIVA DE DEBITOS FEDERAIS",
                        "Receita Federal do Brasil"),
        "cndt": ("CERTIDAO NEGATIVA DE DEBITOS TRABALHISTAS",
                 "Tribunal Superior do Trabalho - TST"),
        "itr": ("RECIBO DE ENTREGA DA DITR - IMPOSTO TERRITORIAL RURAL",
                "Receita Federal do Brasil - NIRF"),
        "contrato_arrendamento": ("CONTRATO DE ARRENDAMENTO RURAL",
                                  "Parceria agricola entre arrendador e arrendatario"),
        "declaracao_posse": ("DECLARACAO DE POSSE",
                             "Ocupacao mansa e pacifica - posseiro"),
        "licenca_ambiental": ("LICENCA DE OPERACAO",
                              "SEMAS/PA - Secretaria de Meio Ambiente"),
        "decl_trabalho_infantil": (
            "DECLARACAO DE AUSENCIA DE TRABALHO INFANTIL",
            "Declaracao do empregador rural - menor de idade"),
    }.get(tipo, (tipo.replace("_", " ").upper(), "Documento do produtor"))

    linhas.append(cab[0])
    linhas.append(cab[1])
    linhas.append("")
    linhas.append("Titular: %s" % produtor["nome"])
    linhas.append("CPF: %s" % cpf)
    linhas.append("Municipio: %s / %s" % (produtor["municipio"], UF))
    linhas.append("Cooperativa: %s" % COOPERATIVA)
    linhas.append("Data de emissao: %s" % emissao.strftime("%d/%m/%Y"))
    if validade:
        linhas.append("Valido ate: %s" % validade.strftime("%d/%m/%Y"))
    linhas.append("")

    if tipo in ("car_recibo", "car_demonstrativo"):
        linhas.append("Numero do CAR: %s" % talhao["car_numero"])
        linhas.append("Situacao do cadastro: %s" % talhao["car_situacao"])
        linhas.append("Area do imovel: %.2f ha" % (talhao["area_ha"] * 1.4))
        linhas.append("Area de reserva legal: %.2f ha" % (talhao["area_ha"] * 0.5))
        linhas.append("Area de APP: %.2f ha" % (talhao["area_ha"] * 0.12))
    elif tipo == "ccir":
        linhas.append("Codigo do imovel rural: %03d.%03d.%06d-%d" % (
            rnd.randint(1, 999), rnd.randint(1, 999),
            rnd.randint(1, 999999), rnd.randint(0, 9)))
        linhas.append("Area total: %.2f ha" % (talhao["area_ha"] * 1.4))
    elif tipo == "matricula_imovel":
        linhas.append("Matricula n %d, Livro n 2-%s" % (
            rnd.randint(1000, 9999), rnd.choice("ABCDE")))
        linhas.append("Cartorio de Registro de Imoveis de %s"
                      % produtor["municipio"])
        linhas.append("Proprietario: %s" % produtor["nome"])
        linhas.append("Area: %.2f ha" % (talhao["area_ha"] * 1.4))
    elif tipo == "nota_fiscal_produtor":
        # Variantes que existem para o parser de NF-e da Trilha A ter o que
        # exercitar: chave de 44 digitos com serie de PF, nota modelo 4 de
        # papel (sem chave, e isso NAO e erro) e CFOP de revenda.
        numero = rnd.randint(1, 999999)
        if variante_nfe == "chave_pf":
            serie = rnd.randint(SERIE_PF_MIN, SERIE_PF_MAX)
            chave = montar_chave_nfe(cpf, emissao, "55", serie, numero, rnd)
            linhas.append("Modelo: 55   Serie: %03d   Numero: %06d"
                          % (serie, numero))
            linhas.append("Chave de acesso: %s" % chave)
            linhas.append("Natureza da operacao: venda de producao propria")
            linhas.append("CFOP: 5101")
        elif variante_nfe == "modelo_4":
            # nota de papel, modelo 4: legado, nao tem chave de acesso
            linhas.append("Modelo: 04   Serie: 001   Numero: %06d" % numero)
            linhas.append("Nota fiscal de produtor em talao (modelo 4) - "
                          "documento sem chave de acesso eletronica")
            linhas.append("CFOP: 5101")
        elif variante_nfe == "cfop_revenda":
            chave = montar_chave_nfe(cpf, emissao, "55", 1, numero, rnd)
            linhas.append("Modelo: 55   Serie: 001   Numero: %06d" % numero)
            linhas.append("Chave de acesso: %s" % chave)
            linhas.append("Natureza da operacao: revenda de mercadoria "
                          "adquirida de terceiros")
            linhas.append("CFOP: 6102")
        else:
            linhas.append("Numero: %06d   Serie: 1" % numero)
        linhas.append("CPF do emitente: %s" % cpf)
        linhas.append("Produto: amendoa de cacau seca")
        linhas.append("Quantidade: %.1f kg" % (talhao["area_ha"] * 900 *
                                               rnd.uniform(0.5, 0.9)))
        linhas.append("Valor total: R$ %.2f" % (rnd.uniform(8000, 45000)))
    elif tipo == "contrato_arrendamento":
        linhas.append("Arrendador: %s %s" % (rnd.choice(PRENOMES),
                                             rnd.choice(SOBRENOMES)))
        linhas.append("Arrendatario: %s" % produtor["nome"])
        linhas.append("Area arrendada: %.2f ha" % talhao["area_ha"])
        linhas.append("Vigencia: %s a %s" % (
            emissao.strftime("%d/%m/%Y"),
            (emissao + timedelta(days=730)).strftime("%d/%m/%Y")))
    else:
        linhas.append("Numero: %s" % "".join(
            rnd.choice("0123456789") for _ in range(12)))
        linhas.append("Resultado: NEGATIVA - nada consta")

    linhas.append("")
    linhas.append("Talhao de referencia: %s (%.2f ha)"
                  % (talhao["nome"], talhao["area_ha"]))
    linhas.append("Documento gerado para ambiente de demonstracao.")
    return "\n".join(linhas)


def escrever_pdf(caminho: Path, texto: str) -> None:
    """PDF de texto simples, legivel por pdfplumber."""
    from fpdf import FPDF
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for linha in texto.split("\n"):
        # latin-1 e o que a fonte core do fpdf aceita; o texto ja vem sem acento
        pdf.cell(0, 5, linha.encode("latin-1", "replace").decode("latin-1"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(caminho))


def escrever_pdf_ilegivel(caminho: Path, rnd: random.Random) -> None:
    """PDF SEM camada de texto: so uma imagem ruidosa, como scan torto.

    E a armadilha do status 'ilegivel': pdfplumber extrai string vazia.
    """
    from PIL import Image
    from fpdf import FPDF
    img = Image.new("L", (620, 877))
    img.putdata([rnd.randint(150, 230) for _ in range(620 * 877)])
    temp = caminho.with_suffix(".ruido.png")
    img.save(temp)
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.image(str(temp), x=5, y=5, w=200)
    pdf.output(str(caminho))
    temp.unlink()


def escrever_foto_cacau(caminho: Path, rnd: random.Random) -> None:
    """Imagem sem texto util - a foto do cacau secando no terreiro.

    Armadilha do tipo 'nao_documento'.
    """
    from PIL import Image
    largura, altura = 800, 600
    img = Image.new("RGB", (largura, altura))
    pix = []
    for y in range(altura):
        for x in range(largura):
            # terreiro de cimento em cima, amendoas marrons embaixo
            if y < altura * 0.32:
                base = 170 + rnd.randint(-12, 12)
                pix.append((base, base - 4, base - 12))
            else:
                pix.append((95 + rnd.randint(-30, 40),
                            55 + rnd.randint(-20, 30),
                            28 + rnd.randint(-14, 20)))
    img.putdata(pix)
    img.save(caminho, quality=82)


def escrever_planilha(caminho: Path, produtor: dict, talhoes: list,
                      rnd: random.Random) -> None:
    """Planilha de entregas da safra - o 'planilha final v2.xlsx'."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "entregas"
    ws.append(["produtor", "cpf", "talhao", "area_ha", "data_entrega",
               "quantidade_kg", "umidade_pct"])
    for t in talhoes:
        for _ in range(rnd.randint(2, 4)):
            ws.append([
                produtor["nome"], produtor["cpf"], t["nome"], t["area_ha"],
                (date(2026, 5, 1) + timedelta(
                    days=rnd.randint(0, 110))).isoformat(),
                round(t["area_ha"] * 900 * rnd.uniform(0.1, 0.3), 1),
                round(rnd.uniform(6.5, 8.2), 1),
            ])
    wb.save(caminho)


NOMES_RUINS = [
    "IMG_%04d.jpg", "doc scan (%d).pdf", "planilha final v%d.xlsx",
    "documento sem titulo.pdf", "Digitalizar0%d.pdf", "novo doc (%d).pdf",
    "WhatsApp Image 2026-07-1%d at 09.13.22.jpeg", "SKM_C224e260%d.pdf",
    "Copia de doc%d.pdf", "arquivo%d.pdf", "PDF-%d.pdf", "foto %d.jpg",
    "Sem titulo %d.pdf", "20260%d_112233.pdf", "digitalizado (%d).pdf",
]


def gerar_arquivos(rnd: random.Random, produtores: list, talhoes: list) -> dict:
    """5 a 10 arquivos por produtor em dados/entrada/<slug>/.

    Planta as cinco armadilhas do SPEC.md secao 8, em produtores DIFERENTES.
    """
    por_produtor = {}
    for t in talhoes:
        por_produtor.setdefault(t["produtor_id"], []).append(t)

    if ENTRADA.exists():
        shutil.rmtree(ENTRADA)
    ENTRADA.mkdir(parents=True)
    PADRONIZADO.mkdir(parents=True, exist_ok=True)

    # produtores que recebem cada armadilha - distintos entre si e nenhum e o
    # pivo dos tres lotes (indice 0), para nao misturar dois efeitos
    sorteio = list(range(1, len(produtores)))
    rnd.shuffle(sorteio)
    a_ilegivel, a_vencido, a_cpf, a_dup, a_foto = sorteio[:5]
    armadilhas = {}

    # Produtores que recebem cada variante de NF-e - todos distintos entre si
    # e das armadilhas documentais. Sem isso o parser de NF-e da Trilha A
    # nunca sai do caminho trivial (nota sem chave e serie 001).
    variantes_nfe = {sorteio[5]: "chave_pf", sorteio[6]: "chave_pf",
                     sorteio[7]: "modelo_4", sorteio[8]: "cfop_revenda"}
    notas_nfe = []

    tipos_comuns = ["car_recibo", "car_demonstrativo", "ccir",
                    "matricula_imovel", "nota_fiscal_produtor", "itr",
                    "cnd_estadual", "cnd_federal", "cndt",
                    "declaracao_posse", "licenca_ambiental",
                    "contrato_arrendamento", "decl_trabalho_infantil"]

    total = 0
    for idx, produtor in enumerate(produtores):
        pasta = ENTRADA / produtor["slug"]
        pasta.mkdir(parents=True, exist_ok=True)
        meus = por_produtor.get(produtor["id"], [])
        if not meus:
            continue
        # ALVO de arquivos do produtor: entre 5 e 10, contando TUDO o que sai
        # na pasta (documentos, copia duplicada, scan ilegivel, foto e
        # planilha). Antes o randint(5, 10) contava so os documentos e os
        # extras estouravam o teto - havia produtor com 12 arquivos.
        alvo_arquivos = rnd.randint(5, 10)
        tem_planilha = rnd.random() < 0.45
        extras = (1 if idx == a_dup else 0) \
            + (1 if idx == a_ilegivel else 0) \
            + (1 if idx == a_foto else 0) \
            + (1 if tem_planilha else 0)

        # o conjunto minimo aparece na maioria dos produtores, mas nao em todos:
        # o mapa de lacunas da Trilha A precisa ter o que reportar
        escolha = ["car_recibo", "car_demonstrativo", "ccir",
                   "nota_fiscal_produtor"]
        if rnd.random() < 0.25:
            escolha.remove(rnd.choice(escolha))      # lacuna deliberada
        escolha.append(rnd.choice(
            ["matricula_imovel", "declaracao_posse", "titulo_assentamento"]))

        # tipos que nao podem sumir na hora de cortar para caber no teto:
        # sem eles a armadilha (ou a variante de NF-e) nao dispara
        obrigatorios = set()
        if idx == a_vencido:
            obrigatorios.add("cnd_estadual")
        if idx in (a_cpf, a_dup):
            obrigatorios.add("car_recibo")
        if idx in variantes_nfe:
            obrigatorios.add("nota_fiscal_produtor")
        for tipo_obrigatorio in sorted(obrigatorios):
            if tipo_obrigatorio not in escolha:
                escolha.append(tipo_obrigatorio)

        quantos_docs = max(len(obrigatorios), 1, alvo_arquivos - extras)
        while len(escolha) < quantos_docs:
            escolha.append(rnd.choice(tipos_comuns))
        while len(escolha) > quantos_docs:
            # corta sempre um nao-obrigatorio, do fim para o inicio
            for posicao in range(len(escolha) - 1, -1, -1):
                if escolha[posicao] not in obrigatorios:
                    escolha.pop(posicao)
                    break
            else:
                break                    # so sobraram obrigatorios: para aqui
        rnd.shuffle(escolha)

        usados = set()
        conteudos = {}       # nome de arquivo -> texto, para o duplicado
        for tipo in escolha:
            talhao = rnd.choice(meus)
            emissao = date(2026, 1, 1) + timedelta(days=rnd.randint(0, 220))
            validade = emissao + timedelta(days=rnd.choice([90, 180, 365]))
            cpf_alt = None

            # --- ARMADILHA 2: documento vencido ---
            if idx == a_vencido and tipo == "cnd_estadual" and \
                    "vencido" not in armadilhas:
                emissao = date(2025, 9, 10)
                validade = date(2025, 12, 9)      # vencido antes de hoje
                armadilhas["vencido"] = {
                    "produtor": produtor["nome"], "slug": produtor["slug"],
                    "tipo": tipo}
            # --- ARMADILHA 3: CPF divergente do produtor do grupo ---
            if idx == a_cpf and tipo == "car_recibo" and \
                    "cpf_divergente" not in armadilhas:
                outro = produtores[(idx + 7) % len(produtores)]
                cpf_alt = outro["cpf"]
                # A validade precisa ser FUTURA. decidir_status() (ingestao.py)
                # segue a ordem do SPEC - ilegivel, vencido, divergente, ok -
                # entao um documento que tambem estivesse vencido sairia como
                # "vencido" e a armadilha de CPF divergente nunca apareceria.
                emissao = date(2026, 7, 1)
                validade = emissao + timedelta(days=365)
                armadilhas["cpf_divergente"] = {
                    "produtor": produtor["nome"], "slug": produtor["slug"],
                    "tipo": tipo, "cpf_do_documento": cpf_alt,
                    "cpf_do_produtor": produtor["cpf"],
                    "cpf_pertence_a": outro["nome"]}

            modelo = rnd.choice(NOMES_RUINS)
            nome_arquivo = modelo % rnd.randint(1, 9999) if "%" in modelo \
                else modelo
            if nome_arquivo.lower().endswith((".jpg", ".jpeg")):
                nome_arquivo = nome_arquivo.rsplit(".", 1)[0] + ".pdf"
            while nome_arquivo in usados:
                nome_arquivo = "%s (%d).%s" % (
                    nome_arquivo.rsplit(".", 1)[0], rnd.randint(2, 9),
                    nome_arquivo.rsplit(".", 1)[1])
            usados.add(nome_arquivo)

            # --- variante de NF-e (uma por produtor sorteado) ---
            variante = None
            if tipo == "nota_fiscal_produtor" and idx in variantes_nfe and \
                    not any(n["slug"] == produtor["slug"] for n in notas_nfe):
                variante = variantes_nfe[idx]

            texto = texto_documento(tipo, produtor, talhao, rnd, emissao,
                                    validade, cpf_alt, variante)
            if variante:
                notas_nfe.append({
                    "variante": variante, "produtor": produtor["nome"],
                    "slug": produtor["slug"], "arquivo": nome_arquivo,
                    "cpf_do_produtor": produtor["cpf"]})
            escrever_pdf(pasta / nome_arquivo, texto)
            conteudos[nome_arquivo] = (tipo, texto)
            total += 1

            # --- ARMADILHA 4: duplicado com outro nome ---
            if idx == a_dup and tipo == "car_recibo" and \
                    "duplicado" not in armadilhas:
                copia = "Copia de doc%d.pdf" % rnd.randint(10, 99)
                escrever_pdf(pasta / copia, texto)
                total += 1
                armadilhas["duplicado"] = {
                    "produtor": produtor["nome"], "slug": produtor["slug"],
                    "tipo": tipo, "arquivos": [nome_arquivo, copia]}

        # --- ARMADILHA 1: arquivo ilegivel (PDF sem camada de texto) ---
        if idx == a_ilegivel:
            nome = "doc scan (3).pdf"
            escrever_pdf_ilegivel(pasta / nome, rnd)
            total += 1
            armadilhas["ilegivel"] = {
                "produtor": produtor["nome"], "slug": produtor["slug"],
                "arquivo": nome}

        # --- ARMADILHA 5: nao e documento nenhum (foto do cacau secando) ---
        if idx == a_foto:
            nome = "IMG_4471.jpg"
            escrever_foto_cacau(pasta / nome, rnd)
            total += 1
            armadilhas["nao_documento"] = {
                "produtor": produtor["nome"], "slug": produtor["slug"],
                "arquivo": nome}

        # planilha de entregas em parte dos produtores (ja sorteada acima,
        # porque conta no teto de arquivos)
        if tem_planilha:
            nome = "planilha final v%d.xlsx" % rnd.randint(1, 3)
            escrever_planilha(pasta / nome, produtor, meus, rnd)
            total += 1

    return {"total_arquivos": total, "armadilhas": armadilhas,
            "notas_nfe": notas_nfe}


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------
def main() -> int:
    rnd = random.Random(SEMENTE)
    print("=" * 72)
    print(" SEED - Evidence Autopilot EUDR - Trilha 0 (Fundacao)")
    print(" semente fixa: %d" % SEMENTE)
    print("=" * 72)

    print("\n[1/6] recriando o banco em dados/app.db")
    db.apagar_banco()
    db.criar_esquema()
    db.registrar_evento("sistema", "seed_iniciado", "banco", None,
                        "Base semeada recriada com semente fixa %d" % SEMENTE)

    print("[2/6] carregando embargos reais do Ibama de dados/bases/")
    embargos = geo.carregar_embargos(incluir_injetados=False)
    fonte = embargos["fonte_camada"].iloc[0] if len(embargos) else "?"
    print("      %d poligonos de embargo, fonte=%s" % (len(embargos), fonte))
    if fonte == "SEMEADO":
        print("      ATENCAO: camada SEMEADA em uso - o download real falhou.")

    print("[3/6] gerando 60 produtores")
    produtores = gerar_produtores(rnd, 60)
    db.inserir_muitos("produtor", produtores)

    print("[4/6] gerando talhoes (1 a 3 por produtor, 2 a 10 ha)")
    talhoes, plantados = gerar_talhoes(rnd, produtores, embargos)
    db.inserir_muitos("talhao", talhoes)

    print("[5/6] gerando 3 lotes de embarque com sobreposicao")
    lotes, vinculos, pivo = gerar_lotes(rnd, produtores, talhoes, plantados)
    db.inserir_muitos("lote", lotes)
    db.inserir_muitos("lote_talhao", vinculos)

    print("[6/6] gerando arquivos crus em dados/entrada/")
    arquivos = gerar_arquivos(rnd, produtores, talhoes)

    db.registrar_evento(
        "sistema", "seed_concluido", "banco", None,
        "%d produtores, %d talhoes, %d lotes, %d vinculos, %d arquivos"
        % (len(produtores), len(talhoes), len(lotes), len(vinculos),
           arquivos["total_arquivos"]))

    # --- ficha do que foi plantado, para as outras trilhas e para o relatorio
    talhoes_pivo = [t for t in talhoes if t["produtor_id"] == pivo["id"]]
    ficha = {
        "semente": SEMENTE,
        "gerado_em": datetime.now().replace(microsecond=0).isoformat(),
        "contagens": {
            "produtores": len(produtores), "talhoes": len(talhoes),
            "lotes": len(lotes), "lote_talhao": len(vinculos),
            "arquivos_entrada": arquivos["total_arquivos"],
            "embargos_ibama_recorte": int(len(embargos)),
        },
        "produtor_nos_tres_lotes": {
            "id": pivo["id"], "nome": pivo["nome"], "slug": pivo["slug"],
            "cpf": pivo["cpf"], "municipio": pivo["municipio"],
            "talhoes": [{"id": t["id"], "nome": t["nome"],
                         "area_ha": t["area_ha"], "tipo_geom": t["tipo_geom"],
                         "geom_wkt": t["geom_wkt"]} for t in talhoes_pivo],
        },
        "lotes": [{"codigo": l["codigo"], "id": l["id"],
                   "quantidade_kg": l["quantidade_kg"],
                   "comprador": l["comprador"],
                   "produtores": len(db.produtores_do_lote(l["id"])),
                   "talhoes": len(db.talhoes_do_lote(l["id"]))}
                  for l in lotes],
        "talhoes_sobre_embargo": plantados["sobrepostos"],
        "talhoes_limitrofes_500m": plantados["limitrofes"],
        "talhoes_conflito_fora_dos_lotes": True,   # ver docstring de gerar_lotes
        "armadilhas_documentais": arquivos["armadilhas"],
        "notas_fiscais_variantes": arquivos["notas_nfe"],
    }
    caminho_ficha = RAIZ / "dados" / "semente.json"
    caminho_ficha.write_text(json.dumps(ficha, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    # --- relatorio de terminal ---
    print("\n" + "=" * 72)
    print(" RESUMO DA BASE SEMEADA")
    print("=" * 72)
    for tabela, quantidade in db.resumo().items():
        print("  %-14s %6d" % (tabela, quantidade))
    print("  %-14s %6d" % ("arquivos", arquivos["total_arquivos"]))

    print("\n  LOTES")
    for l in ficha["lotes"]:
        print("    %-14s %3d produtores  %3d talhoes  %10.1f kg  %s"
              % (l["codigo"], l["produtores"], l["talhoes"],
                 l["quantidade_kg"], l["comprador"]))

    print("\n  PRODUTOR NOS TRES LOTES (pivo da demo)")
    print("    %s  [%s]  %s" % (pivo["nome"], pivo["slug"], pivo["municipio"]))
    for t in talhoes_pivo:
        print("      %s  %.2f ha  %s  id=%s"
              % (t["nome"], t["area_ha"], t["tipo_geom"], t["id"]))

    print("\n  TALHOES SOBRE EMBARGO REAL (checagem 02 deve dar bloqueio)")
    for p in plantados["sobrepostos"]:
        print("    %-22s %-28s TAD %s" % (p["talhao"], p["produtor"],
                                          p["num_tad_embargo"]))
    print("\n  TALHOES A MENOS DE 500 M DA BORDA (checagem 02 deve dar excecao)")
    for p in plantados["limitrofes"]:
        print("    %-22s %-28s TAD %s" % (p["talhao"], p["produtor"],
                                          p["num_tad_embargo"]))

    print("\n  NOTAS FISCAIS COM VARIANTE (exercitam o parser de NF-e)")
    for n in arquivos["notas_nfe"]:
        print("    %-14s %-28s %s" % (n["variante"], n["produtor"],
                                      n["arquivo"]))

    print("\n  ARMADILHAS DOCUMENTAIS")
    for chave, valor in arquivos["armadilhas"].items():
        print("    %-16s %s" % (chave, json.dumps(valor, ensure_ascii=False)))

    print("\n  ficha completa em dados/semente.json")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
