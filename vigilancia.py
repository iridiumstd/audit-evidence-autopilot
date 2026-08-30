# -*- coding: utf-8 -*-
"""Trilha D - vigilancia continua das camadas geoespaciais.

O que este arquivo faz, em uma frase: fica olhando `dados/bases/` e, quando um
poligono de embargo ou de alerta de desmatamento aparece (ou desaparece), ele
reverifica sozinho os talhoes atingidos, recalcula o status dos lotes e refaz
os dossies dos lotes que mudaram - sem ninguem pedir.

O que ele NAO faz: bloquear, cancelar ou barrar carga nenhuma. Ele marca o
talhao, identifica os lotes que dependem dele e refaz os dossies. Quem decide
e sempre a gestora (docs/correcoes-spec_1.md secao 06).

Escrita no banco (contrato v2, tabela "quem escreve onde"):
  - `lote.status`, indiretamente, via verificacao.recalcular_status_lotes()
  - `evento`, via db.registrar_evento()
  - `dossie`, indiretamente, via dossie.gerar_dossie()
Nada mais. `checagem` e `excecao` sao da Trilha B, chamada por importacao.

Estado proprio (nunca uma tabela nova): dados/vigilancia_estado.json guarda a
impressao digital de cada poligono ja visto, para o ciclo seguinte saber o que
e novidade. Primeiro ciclo em banco limpo apenas fotografa a base - nao reage,
nao regera nada.

Uso:
    python vigilancia.py                  # laco continuo, 5 s
    python vigilancia.py --intervalo 10   # laco continuo, 10 s
    python vigilancia.py --uma-vez        # um unico ciclo, para teste
    python vigilancia.py --sem-cor        # sem ANSI, para log em arquivo
    python vigilancia.py --reset-estado   # esquece o que ja viu e refotografa
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import geopandas as gpd  # noqa: E402
from shapely import wkt as shapely_wkt  # noqa: E402

import db  # noqa: E402
import dossie  # noqa: E402
import geo  # noqa: E402
import verificacao  # noqa: E402

# ---------------------------------------------------------------------------
# Console: o terminal e metade da demonstracao. Precisa sair bonito no Windows.
# ---------------------------------------------------------------------------
ARQUIVO_ESTADO = RAIZ / "dados" / "vigilancia_estado.json"

# Distancia de vizinhanca, em metros. A checagem 02 ja trata 500 m como
# "adjacente ao embargo"; a vigilancia usa o mesmo raio para decidir quais
# talhoes vale a pena reverificar. Nao e norma, e o gatilho da reverificacao:
# quem decide o resultado e sempre a checagem, nao este arquivo.
RAIO_VIZINHANCA_M = 500.0

ORDEM_STATUS = {"verde": 0, "atencao": 1, "bloqueado": 2, None: -1}

USAR_COR = True


def _preparar_console() -> None:
    """UTF-8 na saida e sequencias ANSI ligadas no console do Windows."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            # 7 = ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL | ENABLE_VT
            k32.SetConsoleMode(k32.GetStdHandle(-11), 7)
        except Exception:
            pass


CORES = {
    "reset": "\033[0m", "negrito": "\033[1m", "fraco": "\033[2m",
    "vermelho": "\033[91m", "verde": "\033[92m", "amarelo": "\033[93m",
    "azul": "\033[94m", "magenta": "\033[95m", "ciano": "\033[96m",
    "cinza": "\033[90m", "fundo_vermelho": "\033[41m\033[97m",
    "fundo_amarelo": "\033[43m\033[30m",
}


def c(texto: str, *estilos) -> str:
    """Aplica cor ANSI, se o console aceitar."""
    if not USAR_COR or not estilos:
        return texto
    return "".join(CORES.get(e, "") for e in estilos) + texto + CORES["reset"]


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(texto: str, *estilos, simbolo: str = "·") -> None:
    """Uma linha de terminal com carimbo de hora. E entregavel: capriche."""
    print("%s %s %s" % (c(_ts(), "cinza"), c(simbolo, "azul"),
                        c(texto, *estilos)), flush=True)


def linha(caractere: str = "-", largura: int = 78, *estilos) -> None:
    print(c(caractere * largura, *estilos), flush=True)


def banner(titulo: str, subtitulo: str = "", estilo: str = "fundo_vermelho") -> None:
    """O momento do palco. Grande, impossivel de nao ver."""
    largura = 78
    print("", flush=True)
    print(c(" " * largura, estilo), flush=True)
    print(c((" " + titulo).ljust(largura), estilo, "negrito"), flush=True)
    if subtitulo:
        print(c((" " + subtitulo).ljust(largura), estilo), flush=True)
    print(c(" " * largura, estilo), flush=True)
    print("", flush=True)


def cor_do_status(status: str) -> str:
    return {"verde": "verde", "atencao": "amarelo",
            "bloqueado": "vermelho"}.get(status, "cinza")


# ---------------------------------------------------------------------------
# Estado proprio - arquivo JSON, nunca tabela nova (contrato v2)
# ---------------------------------------------------------------------------
def carregar_estado() -> dict:
    """Le dados/vigilancia_estado.json. Ausente ou corrompido = estado vazio."""
    if not ARQUIVO_ESTADO.exists():
        return {"poligonos": {}, "ciclos": 0, "criado_em": db.agora(),
                "atualizado_em": None}
    try:
        with ARQUIVO_ESTADO.open("r", encoding="utf-8") as f:
            estado = json.load(f)
    except (json.JSONDecodeError, OSError):
        log("estado anterior ilegivel - recomecando a fotografia da base",
            "amarelo", simbolo="!")
        return {"poligonos": {}, "ciclos": 0, "criado_em": db.agora(),
                "atualizado_em": None}
    estado.setdefault("poligonos", {})
    estado.setdefault("ciclos", 0)
    return estado


def gravar_estado(estado: dict) -> None:
    estado["atualizado_em"] = db.agora()
    ARQUIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ARQUIVO_ESTADO.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    tmp.replace(ARQUIVO_ESTADO)


# ---------------------------------------------------------------------------
# Leitura das camadas
# ---------------------------------------------------------------------------
def _impressao_digital(camada: str, identificador: str, wkt: str) -> str:
    """Chave estavel de um poligono: camada + identificador + geometria.

    Usa a geometria no hash de proposito - um termo de embargo que teve o
    poligono redesenhado e, para efeito de vigilancia, novidade.
    """
    bruto = "%s|%s|%s" % (camada, identificador, wkt)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:20]


def _rotulo_embargo(linha_gdf) -> str:
    num = str(linha_gdf.get("NUM_TAD") or linha_gdf.get("SEQ_TAD") or "s/n")
    nome = str(linha_gdf.get("NOME_EMBARGADO") or "").strip()
    return "termo %s%s" % (num, (" - %s" % nome) if nome and nome != "nan" else "")


def _rotulo_alerta(linha_gdf) -> str:
    for campo in ("id_alerta", "ID_ALERTA", "codigo", "id"):
        if campo in linha_gdf and str(linha_gdf[campo]) not in ("", "nan"):
            return "alerta %s" % linha_gdf[campo]
    return "alerta sem identificador"


def ler_camadas() -> dict:
    """Le embargos e alertas de dados/bases/ e devolve {chave: registro}.

    Cada registro traz camada, rotulo, fonte declarada e a geometria - para
    o laudo poder dizer de onde veio o poligono (ADR-012).
    """
    poligonos = {}

    # --- embargos (Ibama real + injetados pela demo) -----------------------
    try:
        gdf = geo.carregar_embargos()
    except FileNotFoundError as erro:
        log("camada de embargos indisponivel: %s" % erro, "amarelo", simbolo="!")
        gdf = None
    if gdf is not None:
        for _, linha_gdf in gdf.iterrows():
            if linha_gdf.geometry is None or linha_gdf.geometry.is_empty:
                continue
            wkt = linha_gdf.geometry.wkt
            chave = _impressao_digital("embargo", _rotulo_embargo(linha_gdf), wkt)
            poligonos[chave] = {
                "camada": "embargo",
                "rotulo": _rotulo_embargo(linha_gdf),
                "fonte": str(linha_gdf.get("fonte_camada") or "desconhecida"),
                "geometria": linha_gdf.geometry,
            }

    # --- alertas de desmatamento ------------------------------------------
    try:
        gdf_alertas = verificacao.carregar_alertas()
    except Exception as erro:  # camada opcional: nunca derruba o laco
        log("camada de alertas indisponivel: %s" % erro, "amarelo", simbolo="!")
        gdf_alertas = None
    if gdf_alertas is not None and len(gdf_alertas):
        for _, linha_gdf in gdf_alertas.iterrows():
            if linha_gdf.geometry is None or linha_gdf.geometry.is_empty:
                continue
            wkt = linha_gdf.geometry.wkt
            chave = _impressao_digital("alerta", _rotulo_alerta(linha_gdf), wkt)
            poligonos[chave] = {
                "camada": "alerta",
                "rotulo": _rotulo_alerta(linha_gdf),
                "fonte": str(linha_gdf.get("fonte_camada") or "alertas_desmatamento"),
                "geometria": linha_gdf.geometry,
            }
    return poligonos


def _talhoes_gdf():
    """Todos os talhoes com geometria, em GeoDataFrame EPSG:4326."""
    registros, geoms = [], []
    for t in db.listar_talhoes():
        if not t.get("geom_wkt"):
            continue
        try:
            geom = shapely_wkt.loads(t["geom_wkt"])
        except Exception:
            continue
        if geom is None or geom.is_empty:
            continue
        registros.append({"talhao_id": t["id"], "nome": t["nome"],
                          "produtor_id": t["produtor_id"]})
        geoms.append(geom)
    if not registros:
        return None
    return gpd.GeoDataFrame(registros, geometry=geoms, crs=geo.CRS_PADRAO)


def talhoes_atingidos(geometrias: list) -> list:
    """Talhoes que intersectam - ou ficam a menos de 500 m de - as geometrias.

    Devolve lista de dicts {talhao_id, nome, distancia_m}. Nao decide nada
    sobre o talhao: apenas escolhe quem vale reverificar.
    """
    if not geometrias:
        return []
    gdf_talhoes = _talhoes_gdf()
    if gdf_talhoes is None:
        return []
    alvo = gpd.GeoDataFrame(geometry=list(geometrias), crs=geo.CRS_PADRAO)
    talhoes_m = geo.em_metros(gdf_talhoes)
    alvo_m = geo.em_metros(alvo)
    unido = alvo_m.geometry.union_all() if hasattr(alvo_m.geometry, "union_all") \
        else alvo_m.geometry.unary_union

    achados = []
    for _, linha_gdf in talhoes_m.iterrows():
        distancia = float(linha_gdf.geometry.distance(unido))
        if distancia <= RAIO_VIZINHANCA_M:
            achados.append({"talhao_id": linha_gdf["talhao_id"],
                            "nome": linha_gdf["nome"],
                            "distancia_m": round(distancia, 1)})
    achados.sort(key=lambda a: a["distancia_m"])
    return achados


# ---------------------------------------------------------------------------
# Um ciclo
# ---------------------------------------------------------------------------
def ciclo(estado: dict, numero: int = 1, verboso_ocioso: bool = True) -> dict:
    """Um passe completo: le, compara, reverifica, recalcula, regera.

    Devolve um resumo em dict - nenhum objeto, como manda a regra de ouro 3.
    """
    resumo = {"ciclo": numero, "novos": [], "sumidos": [],
              "talhoes_reverificados": [], "lotes_piorados": [],
              "lotes_melhorados": [], "dossies": [], "houve_novidade": False}

    # O laco escreve poligono em disco entre um ciclo e outro: o cache
    # geoespacial da Trilha B tem que morrer antes de qualquer leitura.
    verificacao.limpar_cache_geo()

    atuais = ler_camadas()
    conhecidos = estado.get("poligonos", {})
    primeira_fotografia = not conhecidos and not estado.get("atualizado_em")

    chaves_novas = [k for k in atuais if k not in conhecidos]
    chaves_sumidas = [k for k in conhecidos if k not in atuais]

    # --- linha de base: banco recem-populado, nada disso e "novidade" ------
    if primeira_fotografia:
        estado["poligonos"] = {
            k: {"camada": v["camada"], "rotulo": v["rotulo"],
                "fonte": v["fonte"], "visto_em": db.agora(),
                "talhoes_afetados": []}
            for k, v in atuais.items()}
        estado["ciclos"] = estado.get("ciclos", 0) + 1
        gravar_estado(estado)
        log("linha de base gravada: %d poligonos conhecidos em dados/bases/ "
            "(nenhuma reverificacao disparada)" % len(atuais),
            "ciano", simbolo="=")
        db.registrar_evento(
            "sistema", "vigilancia_linha_de_base", "base", None,
            "Vigilancia fotografou a base geoespacial pela primeira vez: "
            "%d poligonos passam a ser o ponto de comparacao." % len(atuais))
        return resumo

    if not chaves_novas and not chaves_sumidas:
        if verboso_ocioso:
            log("base estavel - %d poligonos, nenhuma novidade" % len(atuais),
                "cinza")
        estado["ciclos"] = estado.get("ciclos", 0) + 1
        gravar_estado(estado)
        return resumo

    resumo["houve_novidade"] = True

    # --- 1. novidade detectada --------------------------------------------
    geometrias_para_reverificar = []
    talhoes_ids = {}

    if chaves_novas:
        rotulos = [atuais[k]["rotulo"] for k in chaves_novas]
        camadas = sorted({atuais[k]["camada"] for k in chaves_novas})
        banner("EMBARGO NOVO DETECTADO" if "embargo" in camadas
               else "ALERTA NOVO DETECTADO",
               "%d poligono(s) apareceram em dados/bases/ desde o ultimo ciclo"
               % len(chaves_novas))
        for k in chaves_novas:
            reg = atuais[k]
            log("poligono novo  %s  [camada %s · fonte declarada: %s]"
                % (reg["rotulo"], reg["camada"], reg["fonte"]),
                "vermelho", "negrito", simbolo="!")
            geometrias_para_reverificar.append(reg["geometria"])
            db.registrar_evento(
                "sistema", "vigilancia_poligono_novo", "base", None,
                "Vigilancia detectou poligono novo na camada %s: %s "
                "(fonte declarada: %s)."
                % (reg["camada"], reg["rotulo"], reg["fonte"]))
        resumo["novos"] = rotulos

    if chaves_sumidas:
        log("%d poligono(s) sairam da base - os talhoes que dependiam deles "
            "voltam para a fila de reverificacao" % len(chaves_sumidas),
            "ciano", simbolo="~")
        for k in chaves_sumidas:
            reg = conhecidos[k]
            log("poligono removido  %s  [camada %s]"
                % (reg.get("rotulo", "?"), reg.get("camada", "?")), "ciano")
            resumo["sumidos"].append(reg.get("rotulo", "?"))
            for tid in reg.get("talhoes_afetados", []):
                talhao = db.buscar_talhao(tid)
                if talhao:
                    talhoes_ids[tid] = talhao["nome"]
            db.registrar_evento(
                "sistema", "vigilancia_poligono_removido", "base", None,
                "Poligono %s saiu da camada %s; %d talhao(oes) marcados para "
                "reverificacao." % (reg.get("rotulo", "?"),
                                    reg.get("camada", "?"),
                                    len(reg.get("talhoes_afetados", []))))

    # --- 2. quais talhoes reverificar --------------------------------------
    afetados_por_chave = {}
    if geometrias_para_reverificar:
        achados = talhoes_atingidos(geometrias_para_reverificar)
        for a in achados:
            talhoes_ids[a["talhao_id"]] = a["nome"]
        for k in chaves_novas:
            individuais = talhoes_atingidos([atuais[k]["geometria"]])
            afetados_por_chave[k] = [i["talhao_id"] for i in individuais]
        if achados:
            log("interseccao geometrica: %d talhao(oes) dentro do raio de "
                "%.0f m" % (len(achados), RAIO_VIZINHANCA_M), "amarelo",
                simbolo=">")
            for a in achados[:10]:
                log("   talhao %s  (%s m do poligono)"
                    % (a["nome"], a["distancia_m"]), "amarelo")
        else:
            log("nenhum talhao no raio dos poligonos novos", "cinza", simbolo=">")

    # --- 3. status dos lotes antes de mexer --------------------------------
    antes = {l["id"]: l["status"] for l in db.listar_lotes()}
    codigos = {l["id"]: l["codigo"] for l in db.listar_lotes()}

    # --- 4. reverificacao (Trilha B, importada) ----------------------------
    for tid, nome in talhoes_ids.items():
        log("reverificando talhao %s - as sete checagens" % nome, "magenta",
            simbolo="*")
        try:
            saida = verificacao.verificar_talhao(tid)
        except Exception as erro:
            log("   falha ao reverificar %s: %s" % (nome, erro), "vermelho",
                simbolo="x")
            db.registrar_evento(
                "sistema", "vigilancia_falha", "talhao", tid,
                "Reverificacao do talhao %s falhou: %s" % (nome, erro))
            continue
        pior = saida.get("pior", "conforme")
        log("   resultado do talhao %s: %s  (%d excecao(oes) registrada(s))"
            % (nome, pior.upper(), len(saida.get("excecoes_criadas", []))),
            cor_do_status({"conforme": "verde", "excecao": "atencao",
                           "bloqueio": "bloqueado"}.get(pior, "")))
        resumo["talhoes_reverificados"].append({"talhao_id": tid, "nome": nome,
                                                "pior": pior})
        db.registrar_evento(
            "sistema", "vigilancia_talhao_reverificado", "talhao", tid,
            "Vigilancia reverificou o talhao %s apos mudanca na base "
            "geoespacial; pior resultado: %s." % (nome, pior))

    # --- 5. recalculo do status dos lotes ----------------------------------
    log("recalculando o status dos lotes pelo pior resultado entre os talhoes",
        "azul", simbolo="=")
    verificacao.limpar_cache_geo()
    depois_mapa = verificacao.recalcular_status_lotes(silencioso=True)
    depois = {v["lote_id"]: v["status"] for v in depois_mapa.values()}

    # --- 6. dossies dos lotes que mudaram ----------------------------------
    for lote_id, novo in depois.items():
        anterior = antes.get(lote_id)
        if novo == anterior:
            continue
        piorou = ORDEM_STATUS.get(novo, 0) > ORDEM_STATUS.get(anterior, 0)
        codigo = codigos.get(lote_id, lote_id)
        if piorou:
            log("lote %s  %s -> %s   PIOROU"
                % (codigo, str(anterior).upper(), novo.upper()),
                cor_do_status(novo), "negrito", simbolo="!")
            resumo["lotes_piorados"].append(codigo)
        else:
            log("lote %s  %s -> %s   melhorou"
                % (codigo, str(anterior).upper(), novo.upper()),
                cor_do_status(novo), simbolo="+")
            resumo["lotes_melhorados"].append(codigo)

        # Regerar em qualquer mudanca: um dossie que descreve um estado que
        # nao existe mais e pior do que nenhum dossie.
        try:
            gerado = dossie.gerar_dossie(lote_id)
        except Exception as erro:
            log("   falha ao regerar o dossie de %s: %s" % (codigo, erro),
                "vermelho", simbolo="x")
            db.registrar_evento(
                "sistema", "vigilancia_falha", "lote", lote_id,
                "Regeracao do dossie do lote %s falhou: %s" % (codigo, erro))
            continue
        log("   dossie do lote %s regerado na versao v%d  ->  %s"
            % (codigo, gerado["versao"], gerado["caminho_html"]),
            "verde", simbolo="+")
        resumo["dossies"].append({"lote": codigo, "versao": gerado["versao"],
                                  "html": gerado["caminho_html"],
                                  "pdf": gerado["caminho_pdf"]})
        db.registrar_evento(
            "sistema", "vigilancia_dossie_regerado", "lote", lote_id,
            "Vigilancia regerou o dossie do lote %s (v%d) porque o status "
            "passou de '%s' para '%s'."
            % (codigo, gerado["versao"], anterior, novo))

    # --- 7. estado atualizado ----------------------------------------------
    novos_conhecidos = {}
    for k, v in atuais.items():
        anterior_reg = conhecidos.get(k, {})
        novos_conhecidos[k] = {
            "camada": v["camada"], "rotulo": v["rotulo"], "fonte": v["fonte"],
            "visto_em": anterior_reg.get("visto_em") or db.agora(),
            "talhoes_afetados": afetados_por_chave.get(
                k, anterior_reg.get("talhoes_afetados", [])),
        }
    estado["poligonos"] = novos_conhecidos
    estado["ciclos"] = estado.get("ciclos", 0) + 1
    gravar_estado(estado)

    # --- 8. fecho do ciclo -------------------------------------------------
    cont = db.contadores()
    linha("-", 78, "cinza")
    log("ciclo %d encerrado · %d talhao(oes) reverificado(s) · %d dossie(s) "
        "regerado(s) · %d excecao(oes) esperando decisao humana"
        % (numero, len(resumo["talhoes_reverificados"]),
           len(resumo["dossies"]), cont["excecoes_para_humano"]),
        "ciano", "negrito", simbolo="=")
    linha("-", 78, "cinza")

    db.registrar_evento(
        "sistema", "vigilancia_ciclo", "base", None,
        "Ciclo de vigilancia %d: %d poligono(s) novo(s), %d removido(s), "
        "%d talhao(oes) reverificado(s), %d dossie(s) regerado(s)."
        % (numero, len(resumo["novos"]), len(resumo["sumidos"]),
           len(resumo["talhoes_reverificados"]), len(resumo["dossies"])))
    return resumo


# ---------------------------------------------------------------------------
# Abertura e laco
# ---------------------------------------------------------------------------
def abertura(intervalo: float, uma_vez: bool) -> None:
    cont = db.contadores()
    lotes = db.listar_lotes()
    linha("=", 78, "ciano")
    print(c(" EVIDENCE AUTOPILOT EUDR  ·  VIGILANCIA CONTINUA",
            "ciano", "negrito"), flush=True)
    linha("=", 78, "ciano")
    print(c("  O sistema nao bloqueia, nao cancela e nao barra carga. Ele "
            "marca o talhao,", "cinza"), flush=True)
    print(c("  identifica os lotes que dependem dele e refaz os dossies. "
            "Quem decide e a gestora.", "cinza"), flush=True)
    print("", flush=True)
    print("  base observada .... %s" % (RAIZ / "dados" / "bases"), flush=True)
    print("  intervalo ......... %s"
          % ("ciclo unico (--uma-vez)" if uma_vez else "%.0f s" % intervalo),
          flush=True)
    print("  estado ............ %s" % ARQUIVO_ESTADO.name, flush=True)
    print("  lotes acompanhados. %s"
          % ", ".join("%s [%s]" % (l["codigo"], c(str(l["status"]).upper(),
                                                  cor_do_status(l["status"])))
                      for l in lotes), flush=True)
    print("  autonomia ......... %d verificacoes · %d documentos · %d dossies "
          "· %d excecoes para humano"
          % (cont["verificacoes_executadas"], cont["documentos_processados"],
             cont["dossies_regerados"], cont["excecoes_para_humano"]),
          flush=True)
    linha("=", 78, "ciano")
    print("", flush=True)


def rodar(intervalo: float = 5.0, uma_vez: bool = False) -> dict:
    """Laco com sleep - nao cron, como manda a stack decidida no contrato."""
    estado = carregar_estado()
    abertura(intervalo, uma_vez)
    db.registrar_evento(
        "sistema", "vigilancia_iniciada", "base", None,
        "Vigilancia continua iniciada (%s)."
        % ("ciclo unico" if uma_vez else "intervalo de %.0f s" % intervalo))

    numero = estado.get("ciclos", 0) + 1
    ultimo = {}
    try:
        while True:
            ultimo = ciclo(estado, numero=numero,
                           verboso_ocioso=not uma_vez or True)
            if uma_vez:
                break
            numero += 1
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("", flush=True)
        log("vigilancia encerrada pela gestora (Ctrl+C)", "amarelo",
            simbolo="=")
        db.registrar_evento("humano", "vigilancia_encerrada", "base", None,
                            "Vigilancia continua encerrada pelo operador.")
    return ultimo


def main(argv=None) -> int:
    global USAR_COR
    parser = argparse.ArgumentParser(
        description="Trilha D - vigilancia continua das bases geoespaciais.")
    parser.add_argument("--intervalo", type=float, default=5.0,
                        metavar="N", help="segundos entre ciclos (padrao 5)")
    parser.add_argument("--uma-vez", action="store_true",
                        help="roda um unico ciclo e sai (teste)")
    parser.add_argument("--sem-cor", action="store_true",
                        help="desliga as cores ANSI")
    parser.add_argument("--reset-estado", action="store_true",
                        help="esquece os poligonos ja vistos e refotografa")
    args = parser.parse_args(argv)

    _preparar_console()
    USAR_COR = not args.sem_cor and sys.stdout.isatty()

    if args.reset_estado and ARQUIVO_ESTADO.exists():
        ARQUIVO_ESTADO.unlink()
        log("estado de vigilancia zerado", "amarelo", simbolo="!")

    rodar(intervalo=args.intervalo, uma_vez=args.uma_vez)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
