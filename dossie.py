# -*- coding: utf-8 -*-
"""dossie.py - Trilha C. Gera o dossie de conformidade EUDR de um lote.

Regra que governa este arquivo (SPEC.md secao 5): o dossie **fotografa** o
estado corrente e nunca recalcula nada. Ele le `checagem`, `excecao`,
`documento`, `talhao`, `produtor`, `lote` e `evento` e congela tudo numa
versao nova. Quem decide se um talhao esta bloqueado e a Trilha B; aqui so se
carimba o que ela apurou, com a data em que a consulta foi feita.

Esta trilha escreve em UMA tabela apenas: `dossie` (mais `evento`, como todas).

Uso:
    python dossie.py --lote CAC-2026-114
    python dossie.py --lote CAC-2026-114 --aprovar --nome "..." --cargo "..."
    python dossie.py --todos

    import dossie
    dossie.gerar_dossie(lote_id)
    dossie.aprovar_dossie(dossie_id, "Helena Vaz", "Diretora de Conformidade")
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import db

RAIZ = Path(__file__).resolve().parent
TEMPLATES = RAIZ / "templates"
SAIDA_DOSSIES = RAIZ / "saida" / "dossies"

# ---------------------------------------------------------------------------
# Metadados das seis checagens (SPEC.md secao 4). Sao rotulos de apresentacao:
# o resultado vem do banco, nada aqui e recalculado.
# ---------------------------------------------------------------------------
CATALOGO_CHECAGENS = [
    {"codigo": "01", "nome": "Desmate pos-2020", "perna": "A",
     "categoria": "A - geometria da parcela",
     "fonte_padrao": "Alertas de desmatamento (PRODES/DETER)"},
    {"codigo": "02", "nome": "Embargo do Ibama e LDI-PA", "perna": "B",
     "categoria": "b, d",
     "fonte_padrao": "Lista de areas embargadas do Ibama e da LDI-PA"},
    {"codigo": "03", "nome": "CAR e posse", "perna": "B",
     "categoria": "a, b",
     "fonte_padrao": "Cadastro Ambiental Rural (SICAR)"},
    {"codigo": "04", "nome": "Sobreposicao de direitos de terceiros", "perna": "B",
     "categoria": "d, f, g",
     "fonte_padrao": "Terras indigenas (Funai), quilombos (Incra), UCs (MMA)"},
    {"codigo": "05", "nome": "Consistencia documental (R01-R50)", "perna": "B",
     "categoria": "transversal",
     "fonte_padrao": "Documentos do proprio produtor"},
    {"codigo": "06", "nome": "Coerencia de volume e fiscal", "perna": "B",
     "categoria": "h",
     "fonte_padrao": "Produtividade de referencia (params/cacau.yml)"},
    {"codigo": "07", "nome": "Lista Suja do MTE", "perna": "B",
     "categoria": "e, f",
     "fonte_padrao": "Cadastro de Empregadores do MTE (Lista Suja vigente)"},
]
POR_CODIGO = {c["codigo"]: c for c in CATALOGO_CHECAGENS}

CODIGOS_PERNA = {
    "A": ["01"],
    "B": ["02", "03", "04", "05", "06", "07"],
}
NOME_PERNA = {"A": "Desmatamento", "B": "Legalidade"}

# Pior resultado manda. Ordem de severidade crescente.
SEVERIDADE = {"conforme": 0, "excecao": 1, "bloqueio": 2}
SEMAFORO_POR_SEVERIDADE = {0: "verde", 1: "atencao", 2: "bloqueado"}

CLASSE_STATUS_DOC = {
    "ok": "r-conforme", "vencido": "r-excecao",
    "divergente": "r-excecao", "ilegivel": "r-excecao",
}

MAX_EVENTOS_IMPRESSOS = 120

# ---------------------------------------------------------------------------
# Severidade das regras (correcoes-spec_1.md secao 04). 'B' impede o embarque,
# 'F' pede leitura humana antes da assinatura. Vem preenchida do banco pela
# Trilha B; aqui so se rotula. Vazio vira 'nao informada' - nunca um chute.
# ---------------------------------------------------------------------------
ROTULO_SEVERIDADE = {
    "B": "B - impede",
    "F": "F - revisar",
}
EXPLICACAO_SEVERIDADE = {
    "B": "Ocorrencia de severidade B: enquanto nao for resolvida, o talhao "
         "fica impedido de compor embarque.",
    "F": "Ocorrencia de severidade F: nao impede por si so; e leitura "
         "obrigatoria antes da assinatura.",
}
CLASSE_SEVERIDADE = {"B": "sev-b", "F": "sev-f"}

# ---------------------------------------------------------------------------
# As OITO categorias de legalidade (a-h) do Art. 2(40) do Reg. (UE) 2023/1115.
#
# O bloco de conformidade de legalidade itera sobre ESTA lista, nunca sobre a
# lista de documentos entregues. Cada categoria fecha por DOCUMENTO ENTREGUE
# ou por CHECAGEM GERADA - e (f), (g) e parte de (d) so fecham por checagem,
# porque nao existe certidao a pedir nem orgao a procurar.
#
#   `tipos`     - tipos documentais canonicos que podem fechar a categoria
#   `codigos`   - checagens do catalogo que provam a categoria
#   `so_checagem` - True quando nao existe documento positivo possivel
# ---------------------------------------------------------------------------
CATEGORIAS_LEGALIDADE = [
    {"letra": "a", "numero": 1, "nome": "Direitos de uso da terra",
     "artigo": "Art. 2(40)(a)",
     "tipos": ["matricula_imovel", "titulo_assentamento", "declaracao_posse",
               "contrato_arrendamento", "ccir", "itr", "sigef"],
     "codigos": ["03"], "so_checagem": False,
     "nota": "Fecha pela hierarquia da camada 2 de aptidao: matricula, depois "
             "titulo, depois posse corroborada por CCIR ou DITR em nome "
             "proprio. A lei local nao exige titulo formal para produzir."},
    {"letra": "b", "numero": 2, "nome": "Protecao ambiental",
     "artigo": "Art. 2(40)(b)",
     "tipos": ["car_recibo", "car_demonstrativo", "licenca_ambiental",
               "outorga_agua", "asv", "adesao_pra"],
     "codigos": ["02", "03"], "so_checagem": False,
     "nota": "O CAR e o documento entregue; o embargo e a checagem gerada. A "
             "ausencia de licenca ambiental em cacauicultura familiar e "
             "tipicamente dispensa documentada, nao lacuna."},
    {"letra": "c", "numero": 3, "nome": "Regulacao florestal",
     "artigo": "Art. 2(40)(c)",
     "tipos": ["dof", "pmfs", "manejo_cabruca", "asv"],
     "codigos": [], "so_checagem": False, "ausencia_esperada": True,
     "nota": "SAF de cacau em area consolidada nao exige ASV nem AUTEF, e "
             "cabruca nao suprime: a ausencia e o cenario normal e a presenca "
             "e que e rara."},
    {"letra": "d", "numero": 4, "nome": "Direitos de terceiros",
     "artigo": "Art. 2(40)(d)",
     "tipos": ["certidao_acoes_reais"],
     "codigos": ["02", "04"], "so_checagem": False,
     "nota": "Parte desta categoria nao tem documento possivel: a sobreposicao "
             "com terra indigena, quilombo ou unidade de conservacao so se "
             "prova por checagem negativa georreferenciada."},
    {"letra": "e", "numero": 5, "nome": "Direitos trabalhistas",
     "artigo": "Art. 2(40)(e)",
     "tipos": ["cndt", "crf_fgts", "registro_empregados", "contrato_trabalho",
               "nr31", "decl_trabalho_infantil"],
     "codigos": ["07"], "so_checagem": False,
     "nota": "Nao existe certidao publica de conformidade trabalhista para "
             "pessoa fisica sem empregados: o substituto e o trio Lista Suja "
             "do MTE, CAF e autodeclaracao."},
    {"letra": "f", "numero": 6, "nome": "Direitos humanos",
     "artigo": "Art. 2(40)(f)",
     "tipos": ["politica_direitos_humanos", "consulta_acp"],
     "codigos": ["04", "07"], "so_checagem": True,
     "nota": "Categoria sem documento positivo emitido para o produtor. Fecha "
             "exclusivamente por checagem negativa: sobreposicao de direitos "
             "e Lista Suja do MTE."},
    {"letra": "g", "numero": 7,
     "nome": "Consentimento livre, previo e informado",
     "artigo": "Art. 2(40)(g)",
     "tipos": ["protocolo_consulta", "ata_consulta_previa",
               "acordo_reparticao"],
     "codigos": ["04"], "so_checagem": True,
     "nota": "Categoria sem documento positivo emitido para o produtor. Fecha "
             "por checagem de sobreposicao: nao havendo territorio de "
             "comunidade tradicional na parcela, nao ha consulta a obter."},
    {"letra": "h", "numero": 8,
     "nome": "Tributario, anticorrupcao, comercial e aduaneiro",
     "artigo": "Art. 2(40)(h)",
     "tipos": ["nota_fiscal_produtor", "inscricao_estadual", "cnd_federal",
               "cnd_estadual", "cnd_municipal", "cndt", "funrural_senar",
               "radar_siscomex", "due_embarque", "consulta_ceis_cnep"],
     "codigos": ["06"], "so_checagem": False,
     "nota": "Debito de ITR e flag, nunca impedimento: nao torna a producao "
             "ilegal."},
]

# Fallback de categoria por codigo de checagem, usado enquanto `checagem.
# categoria` chegar vazio da Trilha B. A 05 e transversal (R01-R50) e por isso
# nao amarra em categoria nenhuma sem o campo preenchido.
CATEGORIAS_POR_CODIGO = {
    "01": ["A"], "02": ["b", "d"], "03": ["a", "b"], "04": ["d", "f", "g"],
    "05": [], "06": ["h"], "07": ["e", "f"],
}

FRASE_DUAS_NATUREZAS = ("E evidencia que o sistema gera, nao que o produtor "
                        "entrega.")

# ---------------------------------------------------------------------------
# As cinco camadas de aptidao (correcoes-spec_1.md secao 01). Hierarquia de
# alternativas, nunca checklist: `forca` registra o degrau que fechou.
# ---------------------------------------------------------------------------
CAMADAS_APTIDAO = [
    {"numero": 1, "nome": "Parcela geolocalizada",
     "artigo": "Art. 9(1)(d) + 2(28)",
     "como_fecha": "Poligono do talhao dentro do perimetro de um CAR nao "
                   "cancelado. Ativo e Pendente passam; Cancelado e Suspenso "
                   "reprovam. Unica exigencia sem substituto possivel."},
    {"numero": 2, "nome": "Direito de uso da area",
     "artigo": "Art. 9(1)(h) + 2(40)(a)",
     "como_fecha": "Um entre, nesta ordem de forca: matricula em nome do "
                   "produtor, titulo (TD, CDRU, CCU), ou contrato/declaracao "
                   "de posse corroborado por CCIR ou DITR em nome proprio."},
    {"numero": 3, "nome": "Identidade e vinculo",
     "artigo": "Art. 9(1)(e)",
     "como_fecha": "CPF valido mais CAF ativo. Na falta: ficha de cooperado "
                   "mais inscricao estadual de produtor."},
    {"numero": 4, "nome": "Transacao, quantidade e data",
     "artigo": "Art. 9(1)(b), (d)",
     "como_fecha": "NF-e do produtor ou contranota da cooperativa nomeando o "
                   "produtor como remetente, com romaneio quando existir."},
    {"numero": 5, "nome": "Checagens negativas na data do dossie",
     "artigo": "Art. 9(1)(g) + 10(2)",
     "como_fecha": "Geradas pelo sistema. " + FRASE_DUAS_NATUREZAS},
]
ROTULO_FORCA = {"forte": "forte", "media": "media", "fraca": "fraca"}

# ---------------------------------------------------------------------------
# Vocabulario fixo de `excecao.tipo` (correcoes-spec_1.md secao 03).
# A contagem de lacunas soma SOMENTE `lacuna_sanavel`.
# ---------------------------------------------------------------------------
GRUPOS_EXCECAO = [
    {"tipo": "bloqueio", "titulo": "Bloqueios",
     "classe": "r-bloqueio",
     "explicacao": "Impedem a composicao do embarque enquanto nao forem "
                   "resolvidos. Sao decisao da responsavel, nao do sistema."},
    {"tipo": "lacuna_sanavel", "titulo": "Lacunas sanaveis",
     "classe": "r-excecao",
     "explicacao": "Falta um documento que pode ser obtido. E o unico grupo "
                   "que a contagem de lacunas soma."},
    {"tipo": "dispensa_documentada", "titulo": "Dispensas documentadas",
     "classe": "r-conforme",
     "explicacao": "A ausencia do documento e a situacao regular - licenca "
                   "ambiental, ASV e SIGEF em cacauicultura familiar. Nao e "
                   "lacuna e nao entra na contagem."},
    {"tipo": "nao_sanavel_pelo_produtor",
     "titulo": "Nao sanaveis pelo produtor",
     "classe": "r-excecao",
     "explicacao": "Condicao do sistema publico, e nao falha de quem produz - "
                   "CAR pendente de analise e casos analogos. Registra-se a "
                   "condicao e a data; nao entra na contagem de lacunas."},
    {"tipo": None, "titulo": "Ainda sem classificacao",
     "classe": "r-excecao",
     "explicacao": "Ocorrencias registradas antes de a verificacao atribuir o "
                   "tipo. Aparecem aqui para nao sumirem do documento."},
]


# ---------------------------------------------------------------------------
# Utilitarios de formatacao - o documento e lido por auditor, nao por maquina
# ---------------------------------------------------------------------------
def _br(iso: str) -> str:
    """ISO 8601 -> '30/08/2026 14:22'. Devolve travessao se vazio."""
    if not iso:
        return "—"
    texto = str(iso).strip()
    for tamanho, formato, saida in ((19, "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M"),
                                    (16, "%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M"),
                                    (10, "%Y-%m-%d", "%d/%m/%Y")):
        try:
            return datetime.strptime(texto[:tamanho], formato).strftime(saida)
        except ValueError:
            continue
    return texto


def _num(valor, casas: int = 2) -> str:
    """Numero com separador de milhar em padrao brasileiro."""
    if valor is None:
        return "—"
    try:
        bruto = ("%%.%df" % casas) % float(valor)
    except (TypeError, ValueError):
        return str(valor)
    inteiro, _, decimal = bruto.partition(".")
    negativo = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    texto = ".".join(grupos)
    if decimal:
        texto += "," + decimal
    return ("-" if negativo else "") + texto


def _sha256_arquivo(caminho: Path) -> str:
    """SHA-256 de um arquivo em disco - e o que transforma PDF em prova."""
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for pedaco in iter(lambda: fh.read(65536), b""):
            h.update(pedaco)
    return h.hexdigest()


def _resumir_texto(texto: str, limite: int = 320) -> str:
    """Corta um laudo longo em fronteira de frase ou de palavra, nunca no meio.

    O laudo integral continua no bloco 5; aqui e so o motivo resumido.
    """
    texto = (texto or "").strip()
    if len(texto) <= limite:
        return texto
    pedaco = texto[:limite]
    ponto = pedaco.rfind(". ")
    corte = ponto + 1 if ponto > limite * 0.5 else pedaco.rfind(" ")
    return pedaco[:corte].rstrip(" ,;") + " […]"


def _centroide_wkt(wkt: str):
    """Centroide aproximado de um WKT, sem depender de shapely.

    O dossie nao faz geoprocessamento: so precisa mostrar uma coordenada
    legivel por talhao. Media aritmetica dos vertices basta para isso.
    """
    if not wkt:
        return None, None, 0
    pares = re.findall(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", wkt)
    if not pares:
        return None, None, 0
    xs = [float(x) for x, _ in pares]
    ys = [float(y) for _, y in pares]
    return sum(ys) / len(ys), sum(xs) / len(xs), len(pares)


# ---------------------------------------------------------------------------
# Fotografia do estado - leitura pura, sem nenhum recalculo
# ---------------------------------------------------------------------------
def _checagens_correntes(talhao_id: str) -> dict:
    """Ultima checagem de cada codigo para um talhao.

    Se a Trilha B rodou o mesmo talhao varias vezes, vale a mais recente:
    o dossie fotografa o estado corrente, nao o historico.
    """
    correntes = {}
    for c in db.listar_checagens(talhao_id):
        anterior = correntes.get(c["codigo"])
        if anterior is None or (c.get("data_execucao") or "") >= (
                anterior.get("data_execucao") or ""):
            correntes[c["codigo"]] = c
    return correntes


def coletar_estado(lote_id: str) -> dict:
    """Le do banco tudo o que o dossie precisa. Nao escreve nada."""
    lote = db.buscar_lote(lote_id)
    if not lote:
        raise ValueError("lote %r nao existe no banco" % lote_id)

    talhoes = db.talhoes_do_lote(lote_id)
    produtores = {p["id"]: p for p in db.produtores_do_lote(lote_id)}

    checagens = {t["id"]: _checagens_correntes(t["id"]) for t in talhoes}

    documentos = []
    for pid in produtores:
        documentos.extend(db.listar_documentos(pid))

    ids_talhoes = {t["id"] for t in talhoes}
    ids_documentos = {d["id"] for d in documentos}
    excecoes = [e for e in db.listar_excecoes()
                if e.get("talhao_id") in ids_talhoes
                or e.get("documento_id") in ids_documentos
                or (e.get("lotes_afetados") or "").find(lote_id) >= 0]

    return {"lote": lote, "talhoes": talhoes, "produtores": produtores,
            "checagens": checagens, "documentos": documentos,
            "excecoes": excecoes}


def _eventos_do_lote(estado: dict, dossie_id: str) -> list:
    """Eventos da trilha de auditoria que tocam este lote.

    Inclui o proprio lote, seus talhoes, seus produtores, seus documentos e os
    dossies ja emitidos - e o que permite a um auditor reconstruir a historia.
    """
    alvos = {estado["lote"]["id"], dossie_id}
    alvos |= {t["id"] for t in estado["talhoes"]}
    alvos |= set(estado["produtores"])
    alvos |= {d["id"] for d in estado["documentos"]}
    alvos |= {e["id"] for e in estado["excecoes"]}
    alvos |= {d["id"] for d in db.listar_dossies(estado["lote"]["id"])}
    todos = db.consultar("SELECT * FROM evento ORDER BY timestamp DESC")
    return [e for e in todos if e.get("entidade_id") in alvos]


# ---------------------------------------------------------------------------
# Montagem dos oito blocos
# ---------------------------------------------------------------------------
def _perna_da_checagem(c: dict) -> str:
    """'A' ou 'B'. Prefere o campo gravado; cai no catalogo; assume 'B'."""
    perna = (c.get("perna") or "").strip().upper()
    if perna in ("A", "B"):
        return perna
    return POR_CODIGO.get(c.get("codigo"), {}).get("perna", "B")


def _bloco2_pernas(estado: dict) -> tuple:
    """Semaforo separado por perna, com contagem de talhoes. Bloco 2."""
    pernas = []
    criticos = []
    for letra in ("A", "B"):
        codigos = CODIGOS_PERNA[letra]
        contagem = {"conforme": 0, "excecao": 0, "bloqueio": 0}
        sem_dado = 0
        pior_global = 0
        for talhao in estado["talhoes"]:
            correntes = estado["checagens"].get(talhao["id"], {})
            # Vale o campo `perna` gravado pela Trilha B; o catalogo por codigo
            # e so o fallback para checagens antigas sem esse campo.
            desta_perna = [c for c in correntes.values()
                           if _perna_da_checagem(c) == letra]
            if not desta_perna:
                sem_dado += 1
                continue
            pior = max(SEVERIDADE.get(c["resultado"], 0) for c in desta_perna)
            pior_global = max(pior_global, pior)
            rotulo = [k for k, v in SEVERIDADE.items() if v == pior][0]
            contagem[rotulo] += 1
            if pior > 0:
                produtor = estado["produtores"].get(talhao["produtor_id"], {})
                for c in desta_perna:
                    if SEVERIDADE.get(c["resultado"], 0) == pior:
                        criticos.append({
                            "talhao_nome": talhao["nome"],
                            "produtor_nome": produtor.get("nome", "—"),
                            "perna": letra,
                            "codigo": c["codigo"],
                            "checagem_nome": POR_CODIGO.get(
                                c["codigo"], {}).get("nome", ""),
                            "resultado": c["resultado"],
                            "severidade": _severidade_da_checagem(c),
                            "severidade_rotulo": ROTULO_SEVERIDADE.get(
                                _severidade_da_checagem(c), "nao informada"),
                            "severidade_classe": CLASSE_SEVERIDADE.get(
                                _severidade_da_checagem(c), "r-neutro"),
                            "motivo": _resumir_texto(c.get("texto")),
                        })
                        break
        nomes = ", ".join(
            "%s %s" % (c, POR_CODIGO[c]["nome"]) for c in codigos)
        pernas.append({
            "letra": letra, "nome": NOME_PERNA[letra],
            "semaforo": SEMAFORO_POR_SEVERIDADE[pior_global]
                        if (contagem["conforme"] + contagem["excecao"]
                            + contagem["bloqueio"]) else "atencao",
            "conformes": contagem["conforme"],
            "excecoes": contagem["excecao"],
            "bloqueios": contagem["bloqueio"],
            "sem_dado": sem_dado,
            "total": len(estado["talhoes"]),
            "checagens_texto": "Checagens desta perna: %s." % nomes,
        })
    criticos.sort(key=lambda c: (-SEVERIDADE.get(c["resultado"], 0),
                                 c["talhao_nome"]))
    return pernas, criticos


def _categorias_da_checagem(c: dict) -> list:
    """Letras de categoria de uma checagem.

    Prefere o campo `checagem.categoria`, que a Trilha B preenche. Enquanto ele
    chegar vazio, cai no mapa por codigo do catalogo - degradacao silenciosa,
    nunca excecao.
    """
    bruto = (c.get("categoria") or "").strip()
    if bruto:
        # aceita 'd', 'd,f,g', 'd, f, g', 'A'
        letras = [p.strip() for p in re.split(r"[,;/ ]+", bruto) if p.strip()]
        if letras:
            return letras
    return CATEGORIAS_POR_CODIGO.get(c.get("codigo"), [])


def _severidade_da_checagem(c: dict) -> str:
    """'B', 'F' ou '' quando a Trilha B ainda nao classificou."""
    sev = (c.get("severidade") or "").strip().upper()
    return sev if sev in ROTULO_SEVERIDADE else ""


def _todas_checagens_correntes(estado: dict) -> list:
    """Pares (talhao, checagem) de todas as checagens correntes do lote."""
    pares = []
    for talhao in estado["talhoes"]:
        for c in estado["checagens"].get(talhao["id"], {}).values():
            pares.append((talhao, c))
    return pares


def _bloco_categorias(estado: dict) -> dict:
    """Conformidade de legalidade montada pelas OITO categorias (a)-(h).

    Esta e a mudanca central da correcao v2: a iteracao e sobre as categorias,
    NUNCA sobre a lista de documentos entregues. Cada ficha fecha por documento
    entregue ou por checagem gerada, e diz qual foi a origem da prova.

    As categorias (f), (g) e parte da (d) nao tem documento positivo emitido
    para o produtor: tratar a ausencia como lacuna documental seria erro de
    modelo, e por isso a ficha carrega `so_checagem`.
    """
    pares = _todas_checagens_correntes(estado)
    docs_por_tipo = {}
    for d in estado["documentos"]:
        docs_por_tipo.setdefault(d.get("tipo") or "desconhecido", []).append(d)

    fichas = []
    for meta in CATEGORIAS_LEGALIDADE:
        letra = meta["letra"]

        # --- origem 1: documentos entregues pelo produtor -------------------
        documentos = []
        for tipo in meta["tipos"]:
            documentos.extend(docs_por_tipo.get(tipo, []))
        docs_ok = [d for d in documentos if (d.get("status") or "") == "ok"]
        docs_problema = [d for d in documentos
                         if (d.get("status") or "") not in ("ok", "")]

        # --- origem 2: checagens geradas pelo sistema ------------------------
        checagens = [(t, c) for t, c in pares
                     if letra in _categorias_da_checagem(c)
                     or c.get("codigo") in meta["codigos"]]
        piores = {}
        for t, c in checagens:
            atual = piores.get(c["codigo"])
            if atual is None or SEVERIDADE.get(c["resultado"], 0) > SEVERIDADE.get(
                    atual[1]["resultado"], 0):
                piores[c["codigo"]] = (t, c)

        pior_chk = max([SEVERIDADE.get(c["resultado"], 0)
                        for _, c in checagens], default=None)
        datas = sorted((c.get("data_execucao") or "") for _, c in checagens)
        tem_b = any(_severidade_da_checagem(c) == "B"
                    and c["resultado"] != "conforme" for _, c in checagens)
        tem_f = any(_severidade_da_checagem(c) == "F"
                    and c["resultado"] != "conforme" for _, c in checagens)

        # --- situacao da categoria ------------------------------------------
        if pior_chk == 2:
            situacao, rotulo = "impedida", "impedimento registrado"
        elif pior_chk == 1 or docs_problema:
            situacao, rotulo = "atencao", "revisar antes de assinar"
        elif pior_chk == 0 or docs_ok:
            situacao, rotulo = "fechada", "prova reunida"
        else:
            situacao, rotulo = "nao_avaliada", "nao avaliado"

        # --- a ficha diz DE ONDE veio a prova -------------------------------
        origem = []
        for tipo in sorted({d.get("tipo") for d in docs_ok if d.get("tipo")}):
            exemplares = [d for d in docs_ok if d.get("tipo") == tipo]
            um = exemplares[0]
            origem.append({
                "natureza": "documento",
                "titulo": "Documento entregue: %s" % tipo,
                "detalhe": "%s (%d exemplar(es) com status ok); emissao %s"
                           % (um.get("arquivo_origem")
                              or um.get("arquivo_padronizado") or "sem nome",
                              len(exemplares), _br(um.get("data_emissao"))),
                "data_br": _br(um.get("data_emissao")),
                "hash_sha256": um.get("hash_sha256") or "",
                "resultado": "conforme",
                "severidade": "",
            })
        for codigo in sorted(piores):
            t, c = piores[codigo]
            nome_chk = POR_CODIGO.get(codigo, {}).get(
                "nome", "checagem %s" % codigo)
            origem.append({
                "natureza": "checagem",
                "titulo": "Checagem gerada: %s %s" % (codigo, nome_chk),
                "detalhe": "consulta a %s executada em %s; resultado %s "
                           "(pior caso, talhao %s)"
                           % (c.get("fonte")
                              or POR_CODIGO.get(codigo, {}).get(
                                  "fonte_padrao", "base externa"),
                              _br(c.get("data_execucao")), c["resultado"],
                              t["nome"]),
                "data_br": _br(c.get("data_execucao")),
                "hash_sha256": "",
                "resultado": c["resultado"],
                "severidade": _severidade_da_checagem(c),
            })

        # --- prosa da ficha --------------------------------------------------
        if situacao == "nao_avaliada":
            if meta.get("ausencia_esperada"):
                # Ausencia de documento nem sempre e lacuna (secao 03): aqui a
                # ausencia e o cenario normal, e dizer "falta" seria erro.
                rotulo = "ausencia esperada"
                texto = ("Nao ha documento desta categoria entre os anexos, e "
                         "essa e a situacao esperada: %s Registra-se a "
                         "condicao, e nao uma lacuna a sanar." % meta["nota"])
            elif meta["so_checagem"]:
                texto = ("Categoria sem documento positivo possivel: nao ha "
                         "certidao a pedir nem orgao a procurar. A prova e a "
                         "checagem negativa georreferenciada, que ainda nao "
                         "foi executada para os talhoes deste lote. Nao se "
                         "trata de documento faltando - trata-se de consulta "
                         "por fazer. %s" % FRASE_DUAS_NATUREZAS)
            else:
                texto = ("Nao ha, na data de geracao deste dossie, documento "
                         "entregue nem checagem executada que sustente esta "
                         "categoria. O estado e nao avaliado, e nao conforme "
                         "nem nao conforme.")
        elif meta["so_checagem"]:
            texto = ("Prova reunida por checagem gerada pelo sistema, unica "
                     "natureza de evidencia possivel nesta categoria. %s %s"
                     % (FRASE_DUAS_NATUREZAS, meta["nota"]))
        elif docs_ok and piores:
            texto = ("Prova reunida por duas naturezas: %d documento(s) "
                     "entregue(s) e %d checagem(ns) gerada(s) pelo sistema. %s"
                     % (len(docs_ok), len(piores), meta["nota"]))
        elif docs_ok:
            texto = ("Prova reunida por documento entregue pelo produtor "
                     "(%d exemplar(es) com status ok). %s"
                     % (len(docs_ok), meta["nota"]))
        else:
            texto = ("Prova reunida por checagem gerada pelo sistema. %s %s"
                     % (FRASE_DUAS_NATUREZAS, meta["nota"]))

        if docs_problema:
            tipos_prob = sorted({"%s (%s)" % (d.get("tipo") or "sem tipo",
                                              d.get("status"))
                                 for d in docs_problema})
            texto += (" Ha documento nesta categoria com status a resolver: "
                      "%s." % ", ".join(tipos_prob))

        fichas.append({
            "letra": letra, "numero": meta["numero"], "nome": meta["nome"],
            "artigo": meta["artigo"], "nota": meta["nota"],
            "so_checagem": meta["so_checagem"],
            "natureza": ("checagem gerada" if meta["so_checagem"]
                         else "documento entregue ou checagem gerada"),
            "situacao": situacao, "rotulo": rotulo,
            "classe": {"fechada": "r-conforme", "atencao": "r-excecao",
                       "impedida": "r-bloqueio",
                       "nao_avaliada": "r-neutro"}[situacao],
            "origem": origem,
            "documentos_ok": len(docs_ok),
            "documentos_problema": len(docs_problema),
            "checagens": len(piores),
            "data_ultima_checagem_br": _br(datas[-1]) if datas else "—",
            "tem_b": tem_b, "tem_f": tem_f,
            "texto": texto,
        })

    resumo = {
        "fechadas": sum(1 for f in fichas if f["situacao"] == "fechada"),
        "atencao": sum(1 for f in fichas if f["situacao"] == "atencao"),
        "impedidas": sum(1 for f in fichas if f["situacao"] == "impedida"),
        "nao_avaliadas": sum(1 for f in fichas
                             if f["situacao"] == "nao_avaliada"),
        "so_por_checagem": [f["letra"] for f in fichas if f["so_checagem"]],
    }
    return {"fichas": fichas, "resumo": resumo,
            "frase": FRASE_DUAS_NATUREZAS}


def _bloco_aptidao(estado: dict) -> dict:
    """Aptidao por produtor, nas cinco camadas, com a forca de cada uma.

    Le a tabela `aptidao`, escrita pela Trilha B. Camada fechada com forca
    'fraca' recebe destaque: e conforme, e e exatamente o que a gestora quer
    ver antes de assinar. Tabela vazia degrada para 'nao avaliado'.
    """
    produtores = []
    fracas_total = 0
    sem_avaliacao = 0
    for pid, produtor in sorted(estado["produtores"].items(),
                                key=lambda kv: kv[1].get("nome") or ""):
        try:
            mapa = db.aptidao_do_produtor(pid)
        except Exception:                                    # noqa: BLE001
            mapa = {}                        # tabela ausente: degrada limpo
        camadas = []
        for meta in CAMADAS_APTIDAO:
            linha = mapa.get(meta["numero"]) or mapa.get(str(meta["numero"]))
            if not linha:
                camadas.append({
                    "numero": meta["numero"], "nome": meta["nome"],
                    "artigo": meta["artigo"], "como_fecha": meta["como_fecha"],
                    "estado": "nao avaliado", "classe": "r-neutro",
                    "forca": "—", "fraca": False, "via": "—",
                    "avaliado_em_br": "—",
                })
                continue
            satisfeita = bool(linha.get("satisfeita"))
            forca = (linha.get("forca") or "").strip().lower()
            fraca = satisfeita and forca == "fraca"
            if fraca:
                fracas_total += 1
            doc = (db.buscar("documento", linha["via_documento_id"])
                   if linha.get("via_documento_id") else None)
            camadas.append({
                "numero": meta["numero"], "nome": meta["nome"],
                "artigo": meta["artigo"], "como_fecha": meta["como_fecha"],
                "estado": "satisfeita" if satisfeita else "nao satisfeita",
                "classe": "r-conforme" if satisfeita else "r-excecao",
                "forca": ROTULO_FORCA.get(forca, forca or "nao informada"),
                "fraca": fraca,
                "via": ("%s · %s" % (doc.get("tipo") or "documento",
                                     doc.get("arquivo_origem")
                                     or doc.get("arquivo_padronizado") or "—")
                        if doc else
                        ("documento %s" % linha["via_documento_id"]
                         if linha.get("via_documento_id")
                         else "checagem do sistema")),
                "avaliado_em_br": _br(linha.get("avaliado_em")),
            })
        avaliado = any(c["estado"] != "nao avaliado" for c in camadas)
        if not avaliado:
            sem_avaliacao += 1
        produtores.append({
            "nome": produtor.get("nome") or "—",
            "cpf": produtor.get("cpf") or "—",
            "municipio": "%s/%s" % (produtor.get("municipio") or "—",
                                    produtor.get("uf") or ""),
            "camadas": camadas,
            "avaliado": avaliado,
            "satisfeitas": sum(1 for c in camadas
                               if c["estado"] == "satisfeita"),
            "fracas": sum(1 for c in camadas if c["fraca"]),
        })
    return {
        "produtores": produtores,
        "total_produtores": len(produtores),
        "sem_avaliacao": sem_avaliacao,
        "camadas_fracas": fracas_total,
        "avaliado": sem_avaliacao < len(produtores) if produtores else False,
    }


def _bloco_excecoes(estado: dict, nomes_talhao: dict) -> dict:
    """Excecoes agrupadas pelos quatro valores do vocabulario fixo.

    A contagem de lacunas soma SOMENTE `lacuna_sanavel` - as demais nao sao
    lacuna: dispensa documentada e situacao regular, e CAR pendente nao e algo
    que o produtor tenha como resolver.
    """
    abertas = [e for e in estado["excecoes"] if e.get("status") == "aberta"]
    grupos = []
    for meta in GRUPOS_EXCECAO:
        do_grupo = [e for e in abertas
                    if (e.get("tipo") or None) == meta["tipo"]]
        if not do_grupo:
            continue
        grupos.append({
            "tipo": meta["tipo"] or "sem tipo",
            "titulo": meta["titulo"],
            "classe": meta["classe"],
            "explicacao": meta["explicacao"],
            "conta_como_lacuna": meta["tipo"] == "lacuna_sanavel",
            "itens": [{
                "talhao_nome": nomes_talhao.get(e.get("talhao_id"), "—"),
                "descricao": e.get("descricao") or "—",
                "status": e.get("status") or "—",
            } for e in do_grupo],
            "total": len(do_grupo),
        })
    lacunas = sum(g["total"] for g in grupos
                  if g["tipo"] == "lacuna_sanavel")
    return {
        "grupos": grupos,
        "total_abertas": len(abertas),
        "lacunas": lacunas,
        "sem_tipo": sum(1 for e in abertas if not e.get("tipo")),
        "nota_contagem": ("Lacunas contadas: %d. A contagem soma somente "
                          "excecoes do tipo lacuna_sanavel; dispensas "
                          "documentadas e condicoes nao sanaveis pelo produtor "
                          "aparecem no dossie mas nao sao lacuna." % lacunas),
    }


def _bloco3_cadeia(estado: dict) -> list:
    """Cadeia de custodia: produtor -> talhao -> nota fiscal -> lote -> contentor."""
    lote = estado["lote"]
    docs_por_produtor = {}
    for d in estado["documentos"]:
        docs_por_produtor.setdefault(d["produtor_id"], []).append(d)

    linhas = []
    for talhao in estado["talhoes"]:
        produtor = estado["produtores"].get(talhao["produtor_id"], {})
        docs = docs_por_produtor.get(talhao["produtor_id"], [])
        # elo 1: produtor -> talhao, sustentado pelo CAR / titulo de posse
        posse = next((d for d in docs if (d.get("tipo") or "").startswith(
            ("car_", "matricula", "titulo", "contrato_arrendamento",
             "declaracao_posse", "ccir"))), None)
        linhas.append({
            "elo": "produtor > talhao",
            "origem": "%s (CPF %s)" % (produtor.get("nome", "—"),
                                       produtor.get("cpf", "—")),
            "destino": "%s · %s ha" % (talhao["nome"],
                                            _num(talhao.get("area_ha"))),
            "volume": "—",
            "documento": _rotulo_documento(posse, "posse ou CAR nao anexado"),
            "documento_hash": (posse or {}).get("hash_sha256"),
        })
        # elo 2: talhao -> lote, sustentado pela nota fiscal do produtor
        nota = next((d for d in docs
                     if (d.get("tipo") or "") == "nota_fiscal_produtor"), None)
        linhas.append({
            "elo": "talhao > lote",
            "origem": talhao["nome"],
            "destino": lote["codigo"],
            "volume": _num(talhao.get("quantidade_kg_no_lote"), 1),
            "documento": _rotulo_documento(nota, "nota fiscal de produtor "
                                                 "rural nao anexada"),
            "documento_hash": (nota or {}).get("hash_sha256"),
        })

    embarque = next((d for d in estado["documentos"]
                     if (d.get("tipo") or "") == "due_embarque"), None)
    linhas.append({
        "elo": "lote > contentor",
        "origem": lote["codigo"],
        "destino": "Embarque para %s em %s" % (
            lote.get("comprador") or "—", _br(lote.get("data_embarque"))),
        "volume": _num(lote.get("quantidade_kg"), 1),
        "documento": _rotulo_documento(
            embarque, "DU-E e documentos de embarque ainda nao emitidos "
                      "(lote nao embarcado)"),
        "documento_hash": (embarque or {}).get("hash_sha256"),
    })
    return linhas


def _rotulo_documento(doc, ausente: str) -> str:
    if not doc:
        return "⚠ %s" % ausente
    return "%s · %s (status %s)" % (
        doc.get("tipo") or "desconhecido",
        doc.get("arquivo_origem") or doc.get("arquivo_padronizado") or "—",
        doc.get("status") or "—")


def _bloco4_geo(estado: dict) -> list:
    """Coordenadas por talhao. Nao faz geoprocessamento: apenas apresenta."""
    linhas = []
    for talhao in estado["talhoes"]:
        produtor = estado["produtores"].get(talhao["produtor_id"], {})
        lat, lon, vertices = _centroide_wkt(talhao.get("geom_wkt"))
        linhas.append({
            "nome": talhao["nome"],
            "produtor": produtor.get("nome", "—"),
            "municipio": "%s/%s" % (produtor.get("municipio", "—"),
                                    produtor.get("uf", "")),
            "tipo_geom": talhao.get("tipo_geom") or "—",
            "area_ha": _num(talhao.get("area_ha")),
            "lat": ("%.6f" % lat) if lat is not None else "—",
            "lon": ("%.6f" % lon) if lon is not None else "—",
            "vertices": vertices if talhao.get("tipo_geom") == "poligono" else 1,
            "car_numero": talhao.get("car_numero") or "—",
            "car_situacao": talhao.get("car_situacao") or "—",
        })
    return linhas


def _bloco5_laudos(estado: dict) -> list:
    """Um laudo por checagem: o que, contra que base, em que data, resultado."""
    # O catalogo fixo cobre as sete checagens do SPEC. A Trilha B tambem grava
    # regras com codigo proprio (R01-R50): estas entram depois, com rotulo
    # derivado do codigo, para nenhuma checagem sumir do dossie.
    catalogo = list(CATALOGO_CHECAGENS)
    conhecidos = {m["codigo"] for m in catalogo}
    extras = sorted({c["codigo"] for _, c in _todas_checagens_correntes(estado)
                     if c.get("codigo") and c["codigo"] not in conhecidos})
    for codigo_extra in extras:
        exemplo = next(c for _, c in _todas_checagens_correntes(estado)
                       if c.get("codigo") == codigo_extra)
        catalogo.append({
            "codigo": codigo_extra,
            "nome": "Regra %s da consistencia documental" % codigo_extra,
            "perna": exemplo.get("perna") or "B",
            "categoria": exemplo.get("categoria") or "transversal",
            "fonte_padrao": "Documentos do proprio produtor",
        })

    laudos = []
    for meta in catalogo:
        codigo = meta["codigo"]
        registros = []
        for talhao in estado["talhoes"]:
            c = estado["checagens"].get(talhao["id"], {}).get(codigo)
            if c:
                registros.append((talhao, c))

        contagem = {"conforme": 0, "excecao": 0, "bloqueio": 0}
        for _, c in registros:
            if c["resultado"] in contagem:
                contagem[c["resultado"]] += 1
        pior = max([SEVERIDADE.get(c["resultado"], 0) for _, c in registros],
                   default=0)
        resultado = ([k for k, v in SEVERIDADE.items() if v == pior][0]
                     if registros else "conforme")

        datas = sorted(c.get("data_execucao") or "" for _, c in registros)
        fontes = sorted({(c.get("fonte") or "").strip()
                         for _, c in registros if c.get("fonte")})

        if not registros:
            conclusao = (
                "Nao ha registro desta checagem para nenhum dos %d talhoes do "
                "lote na data de geracao deste dossie. A ausencia de verificacao "
                "e ela propria uma lacuna de diligencia devida: o lote nao pode "
                "ser considerado conforme quanto a este item."
                % len(estado["talhoes"]))
        else:
            conclusao = (
                "Foram comparados %d talhao(oes) do lote %s contra %s. A consulta "
                "mais recente foi executada em %s. Resultado consolidado: %s "
                "(%d conforme, %d em excecao, %d em bloqueio). %s"
                % (len(registros), estado["lote"]["codigo"],
                   ", ".join(fontes) or meta["fonte_padrao"],
                   _br(datas[-1]) if datas else "—",
                   resultado.upper(), contagem["conforme"], contagem["excecao"],
                   contagem["bloqueio"],
                   {"conforme": "Nenhuma restricao identificada neste item.",
                    "excecao": "Ha ocorrencias que exigem leitura humana antes "
                               "da assinatura.",
                    "bloqueio": "Ha ocorrencia impeditiva: neste item o lote "
                                "fica impedido de compor embarque ate a "
                                "resolucao. Quem decide e a responsavel; o "
                                "sistema marca, ordena e informa."}[resultado]))

        # No laudo detalhado entram as ocorrencias nao conformes; se tudo esta
        # conforme, mostra-se uma amostra para provar que a checagem rodou.
        nao_conformes = [(t, c) for t, c in registros
                         if c["resultado"] != "conforme"]
        mostrar = nao_conformes or registros[:3]

        laudos.append({
            "codigo": codigo, "nome": meta["nome"], "perna": meta["perna"],
            "categoria": meta["categoria"],
            "fonte": ", ".join(fontes) or meta["fonte_padrao"],
            "data_execucao_br": _br(datas[-1]) if datas else "sem execucao",
            "resultado": resultado,
            "total": len(registros),
            "conformes": contagem["conforme"],
            "excecoes": contagem["excecao"],
            "bloqueios": contagem["bloqueio"],
            "conclusao": conclusao,
            "bloqueiam": sum(1 for _, c in registros
                             if _severidade_da_checagem(c) == "B"
                             and c["resultado"] != "conforme"),
            "flags": sum(1 for _, c in registros
                         if _severidade_da_checagem(c) == "F"
                         and c["resultado"] != "conforme"),
            "ocorrencias": [{
                "talhao_nome": t["nome"],
                "resultado": c["resultado"],
                "codigo_regra": c.get("codigo") or "—",
                "severidade": _severidade_da_checagem(c),
                "severidade_rotulo": ROTULO_SEVERIDADE.get(
                    _severidade_da_checagem(c), "nao informada"),
                "severidade_classe": CLASSE_SEVERIDADE.get(
                    _severidade_da_checagem(c), "r-neutro"),
                "data_br": _br(c.get("data_execucao")),
                "texto": c.get("texto") or "—",
                "evidencia": _resumir_evidencia(c.get("evidencia_json")),
            } for t, c in mostrar],
        })
    return laudos


def _resumir_evidencia(bruto: str) -> str:
    """evidencia_json -> uma linha legivel. Nunca quebra por JSON invalido."""
    if not bruto:
        return ""
    try:
        dados = json.loads(bruto)
    except (ValueError, TypeError):
        return str(bruto)[:300]
    if isinstance(dados, dict):
        return "; ".join("%s = %s" % (k, v) for k, v in dados.items())[:600]
    return str(dados)[:600]


def _bloco6_anexos(estado: dict) -> list:
    """Anexos indexados com tipo, origem, datas, validade e hash SHA-256."""
    anexos = []
    for d in sorted(estado["documentos"],
                    key=lambda x: ((x.get("tipo") or "zzz"),
                                   x.get("arquivo_origem") or "")):
        produtor = estado["produtores"].get(d["produtor_id"], {})
        anexos.append({
            "tipo": d.get("tipo") or "desconhecido",
            "produtor": produtor.get("nome", "—"),
            "arquivo_origem": d.get("arquivo_origem") or "—",
            "data_emissao": _br(d.get("data_emissao")),
            "data_validade": _br(d.get("data_validade")),
            "status": d.get("status") or "—",
            "classe": CLASSE_STATUS_DOC.get(d.get("status"), "r-excecao"),
            "confianca": ("%.2f" % d["confianca"]
                          if d.get("confianca") is not None else "—"),
            "hash_sha256": d.get("hash_sha256") or "sem hash registrado",
        })
    return anexos


# ---------------------------------------------------------------------------
# Versionamento e diff em portugues
# ---------------------------------------------------------------------------
def _instantaneo(estado: dict) -> dict:
    """Estado reduzido, guardado em disco para comparar com a versao seguinte.

    Guardado como `vN.estado.json` ao lado do HTML. Nao vai para o banco
    porque o esquema da secao 2.2 do SPEC e congelado.
    """
    # Codigos acompanhados: os do catalogo mais os que a Trilha B tiver gravado
    # (R01-R50). Assim o diff enxerga regra nova aparecendo entre duas versoes.
    codigos = set(POR_CODIGO) | {c["codigo"] for _, c
                                 in _todas_checagens_correntes(estado)
                                 if c.get("codigo")}
    return {
        "lote_status": estado["lote"].get("status"),
        "talhoes": {t["nome"]: {
            c: estado["checagens"].get(t["id"], {}).get(c, {}).get("resultado")
            for c in sorted(codigos)} for t in estado["talhoes"]},
        "documentos": {d.get("hash_sha256") or d["id"]: {
            "tipo": d.get("tipo"), "status": d.get("status"),
            "arquivo": d.get("arquivo_origem")} for d in estado["documentos"]},
        "excecoes_abertas": sorted(
            e["id"] for e in estado["excecoes"] if e.get("status") == "aberta"),
    }


def _caminho_instantaneo(codigo: str, versao: int) -> Path:
    return SAIDA_DOSSIES / codigo / ("v%d.estado.json" % versao)


def _calcular_diff(codigo: str, versao_anterior, atual: dict) -> list:
    """Diff em portugues claro entre a versao anterior e a atual."""
    if not versao_anterior:
        return []
    caminho = _caminho_instantaneo(codigo, versao_anterior)
    if not caminho.exists():
        return ["Nao foi possivel comparar com a versao %d: o instantaneo "
                "daquela versao nao esta disponivel em disco." % versao_anterior]
    try:
        antes = json.loads(caminho.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ["O instantaneo da versao %d esta ilegivel; a comparacao nao "
                "pode ser feita." % versao_anterior]

    itens = []
    if antes.get("lote_status") != atual.get("lote_status"):
        itens.append("o status do lote passou de %s para %s."
                     % (antes.get("lote_status"), atual.get("lote_status")))

    talhoes_antes = antes.get("talhoes", {})
    talhoes_agora = atual.get("talhoes", {})
    for nome in sorted(set(talhoes_antes) | set(talhoes_agora)):
        if nome not in talhoes_antes:
            itens.append("talhao %s foi incluido no lote." % nome)
            continue
        if nome not in talhoes_agora:
            itens.append("talhao %s foi retirado do lote." % nome)
            continue
        for codigo_chk in sorted(set(talhoes_antes[nome])
                                 | set(talhoes_agora[nome])):
            a = talhoes_antes[nome].get(codigo_chk)
            b = talhoes_agora[nome].get(codigo_chk)
            if a == b:
                continue
            nome_chk = POR_CODIGO.get(codigo_chk, {}).get(
                "nome", "regra %s" % codigo_chk)
            if a is None:
                itens.append("talhao %s passou a ter resultado %s na checagem "
                             "%s (%s), antes nao verificada."
                             % (nome, b, codigo_chk, nome_chk))
            elif b is None:
                itens.append("talhao %s perdeu o registro da checagem %s (%s), "
                             "que antes estava como %s."
                             % (nome, codigo_chk, nome_chk, a))
            else:
                itens.append("talhao %s passou de %s para %s na checagem %s (%s)."
                             % (nome, a, b, codigo_chk, nome_chk))

    docs_antes = antes.get("documentos", {})
    docs_agora = atual.get("documentos", {})
    for chave in sorted(set(docs_agora) - set(docs_antes)):
        d = docs_agora[chave]
        itens.append("documento %s (%s) foi anexado ao dossie."
                     % (d.get("arquivo"), d.get("tipo")))
    for chave in sorted(set(docs_antes) - set(docs_agora)):
        d = docs_antes[chave]
        itens.append("documento %s (%s) deixou de constar no dossie."
                     % (d.get("arquivo"), d.get("tipo")))
    for chave in sorted(set(docs_antes) & set(docs_agora)):
        if docs_antes[chave].get("status") != docs_agora[chave].get("status"):
            itens.append("documento %s passou do status %s para %s."
                         % (docs_agora[chave].get("arquivo"),
                            docs_antes[chave].get("status"),
                            docs_agora[chave].get("status")))

    novas = set(atual.get("excecoes_abertas", [])) - set(
        antes.get("excecoes_abertas", []))
    fechadas = set(antes.get("excecoes_abertas", [])) - set(
        atual.get("excecoes_abertas", []))
    if novas:
        itens.append("%d excecao(oes) nova(s) foram abertas desde a versao %d."
                     % (len(novas), versao_anterior))
    if fechadas:
        itens.append("%d excecao(oes) foram resolvidas desde a versao %d."
                     % (len(fechadas), versao_anterior))
    return itens


# ---------------------------------------------------------------------------
# Contexto completo entregue ao template
# ---------------------------------------------------------------------------
def montar_contexto(estado: dict, versao: int, dossie_id: str,
                    aprovacao: dict = None, gerado_em: str = None) -> dict:
    """Os oito blocos, na ordem do SPEC.md secao 5, prontos para o template."""
    lote = dict(estado["lote"])
    lote["quantidade_kg_fmt"] = _num(lote.get("quantidade_kg"), 1)
    lote["data_embarque_br"] = _br(lote.get("data_embarque"))

    pernas, criticos = _bloco2_pernas(estado)
    eventos = _eventos_do_lote(estado, dossie_id)
    nomes_talhao = {t["id"]: t["nome"] for t in estado["talhoes"]}

    area_total = sum(float(t.get("area_ha") or 0) for t in estado["talhoes"])
    gerado_em = gerado_em or db.agora()

    # --- severidade B/F: a decisao que a tela da manha apresenta ------------
    pares = _todas_checagens_correntes(estado)
    nao_conformes = [(t, c) for t, c in pares if c["resultado"] != "conforme"]
    sev_b = sum(1 for _, c in nao_conformes
                if _severidade_da_checagem(c) == "B")
    sev_f = sum(1 for _, c in nao_conformes
                if _severidade_da_checagem(c) == "F")
    sev_sem = len(nao_conformes) - sev_b - sev_f

    # --- as duas provas nao se compensam (secao 06) -------------------------
    perna_a = next((p for p in pernas if p["letra"] == "A"), None)
    desmatamento_impede = bool(perna_a and perna_a["bloqueios"])

    categorias = _bloco_categorias(estado)
    aptidao = _bloco_aptidao(estado)
    excecoes = _bloco_excecoes(estado, nomes_talhao)

    contexto = {
        "dossie_id": dossie_id,
        "versao": versao,
        "status": "aprovado" if aprovacao else "rascunho",
        "aprovacao": aprovacao,
        "gerado_em": gerado_em,
        "gerado_em_br": _br(gerado_em),
        "paginacao_texto": "documento continuo — ver paginacao no rodape do PDF",
        # bloco 1
        "lote": lote,
        "total_produtores": len(estado["produtores"]),
        "total_talhoes": len(estado["talhoes"]),
        "area_total_fmt": _num(area_total),
        # bloco 2
        "pernas": pernas,
        "talhoes_criticos": criticos,
        # severidade B/F
        "sev_b": sev_b,
        "sev_f": sev_f,
        "sev_sem_classificacao": sev_sem,
        "sev_legenda": ("B = nao embarca ate resolver. F = atencao: leitura "
                        "obrigatoria antes de assinar, mas nao impede por si."),
        # as duas provas nao se compensam
        "desmatamento_impede": desmatamento_impede,
        "nota_nao_compensacao": (
            "Desmatamento posterior a 31/12/2020 desqualifica a parcela "
            "inteira, ainda que a supressao tenha sido autorizada: a condicao "
            "do Art. 3(a) independe da legalidade. Nenhuma evidencia da perna "
            "de legalidade compensa falha da perna de geometria, e a "
            "desqualificacao alcanca toda a producao da parcela, sem "
            "proporcionalidade."),
        # 2b - as oito categorias de legalidade
        "categorias": categorias["fichas"],
        "categorias_resumo": categorias["resumo"],
        "frase_duas_naturezas": categorias["frase"],
        # 2c - aptidao em cinco camadas
        "aptidao": aptidao,
        # excecoes agrupadas pelo vocabulario fixo
        "excecoes": excecoes,
        # blocos 3 a 6
        "cadeia": _bloco3_cadeia(estado),
        "geolocalizacao": _bloco4_geo(estado),
        "laudos": _bloco5_laudos(estado),
        "anexos": _bloco6_anexos(estado),
        # bloco 7
        "eventos": [{
            "timestamp_br": _br(e.get("timestamp")),
            "ator": e.get("ator") or "sistema",
            "acao": e.get("acao") or "—",
            "entidade": e.get("entidade") or "—",
            "detalhe": e.get("detalhe") or "—",
        } for e in eventos[:MAX_EVENTOS_IMPRESSOS]],
        "eventos_total": len(eventos),
        "eventos_sistema": sum(1 for e in eventos if e.get("ator") == "sistema"),
        "eventos_humano": sum(1 for e in eventos if e.get("ator") == "humano"),
    }
    return contexto


def renderizar_html(contexto: dict) -> str:
    """Aplica o template jinja2. O template nao calcula: so apresenta."""
    ambiente = Environment(
        loader=FileSystemLoader(str(TEMPLATES), encoding="utf-8"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True, lstrip_blocks=True)
    css = (TEMPLATES / "estilo.css").read_text(encoding="utf-8")
    modelo = ambiente.get_template("dossie.html.j2")
    return modelo.render(d=contexto, css=css)


# ---------------------------------------------------------------------------
# PDF - melhor esforco. O HTML e o entregavel primario.
# ---------------------------------------------------------------------------
def gerar_pdf(caminho_html: Path, caminho_pdf: Path, contexto: dict) -> dict:
    """Converte o HTML em PDF com playwright/chromium.

    Se o chromium nao carregar nesta maquina (ha politica de Controle de
    Aplicativo do Windows que bloqueia DLLs), devolve sucesso=False com o erro
    exato. O HTML ja esta salvo e continua valendo como entregavel.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        return {"sucesso": False, "erro": "playwright nao instalado: %s" % erro}

    cabecalho = (
        '<div style="font-family:Consolas,monospace;font-size:7pt;color:#5a5f55;'
        'width:100%;padding:0 18mm;letter-spacing:.4px;">'
        'DOSSIE DE CONFORMIDADE EUDR &middot; LOTE {codigo}'
        '<span style="float:right">VERSAO {versao} &middot; {status}</span></div>'
    ).format(codigo=contexto["lote"]["codigo"], versao=contexto["versao"],
             status=contexto["status"].upper())
    rodape = (
        '<div style="font-family:Consolas,monospace;font-size:7pt;color:#5a5f55;'
        'width:100%;padding:0 18mm;letter-spacing:.4px;">'
        '{codigo} &middot; V{versao} &middot; GERADO EM {data}'
        '<span style="float:right">PAGINA <span class="pageNumber"></span>'
        ' DE <span class="totalPages"></span></span></div>'
    ).format(codigo=contexto["lote"]["codigo"], versao=contexto["versao"],
             data=contexto["gerado_em_br"])

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page()
            pagina.goto(caminho_html.resolve().as_uri(),
                        wait_until="networkidle")
            pagina.pdf(path=str(caminho_pdf), format="A4",
                       print_background=True,
                       display_header_footer=True,
                       header_template=cabecalho, footer_template=rodape,
                       margin={"top": "26mm", "bottom": "22mm",
                               "left": "18mm", "right": "18mm"})
            navegador.close()
        return {"sucesso": True, "erro": None}
    except Exception as erro:                                # noqa: BLE001
        return {"sucesso": False,
                "erro": "%s: %s" % (type(erro).__name__, erro)}


# ---------------------------------------------------------------------------
# API publica da Trilha C
# ---------------------------------------------------------------------------
def gerar_dossie(lote_id: str, aprovacao: dict = None) -> dict:
    """Fotografa o estado corrente do lote numa versao nova do dossie.

    Devolve dict com id, versao, status, caminhos, hash e diff.
    `aprovacao` so e preenchida por aprovar_dossie(); geracao normal sai
    como rascunho, com marca de agua.
    """
    # Aceita tambem o codigo do lote, por comodidade de quem chama.
    lote = db.buscar_lote(lote_id) or db.buscar_lote_por_codigo(lote_id)
    if not lote:
        raise ValueError("lote %r nao encontrado (nem por id, nem por codigo)"
                         % lote_id)
    lote_id = lote["id"]

    estado = coletar_estado(lote_id)
    codigo = estado["lote"]["codigo"]
    versao = db.proxima_versao_dossie(lote_id)
    anteriores = db.listar_dossies(lote_id)
    versao_anterior = max((d["versao"] for d in anteriores), default=None)
    dossie_anterior = next((d for d in anteriores
                            if d["versao"] == versao_anterior), None)

    dossie_id = db.novo_id()
    contexto = montar_contexto(estado, versao, dossie_id, aprovacao)

    # --- diff em portugues em relacao a versao anterior --------------------
    instantaneo = _instantaneo(estado)
    itens_diff = _calcular_diff(codigo, versao_anterior, instantaneo)
    if versao_anterior is None:
        diff_texto = ("Primeira versao do dossie deste lote. Nao ha versao "
                      "anterior para comparar.")
    elif itens_diff:
        diff_texto = "Em relacao a versao %d: %s" % (
            versao_anterior, " ".join(
                i[0].upper() + i[1:] for i in itens_diff))
    else:
        diff_texto = ("Nenhuma alteracao de conteudo em relacao a versao %d. "
                      "Esta versao foi emitida %s."
                      % (versao_anterior,
                         "para registrar a aprovacao" if aprovacao
                         else "por nova solicitacao de geracao"))
    contexto["diff"] = diff_texto
    contexto["diff_itens"] = itens_diff
    contexto["versao_anterior"] = versao_anterior
    contexto["gerado_em_anterior_br"] = _br(
        (dossie_anterior or {}).get("gerado_em"))

    # --- gravacao dos arquivos --------------------------------------------
    pasta = SAIDA_DOSSIES / codigo
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_html = pasta / ("v%d.html" % versao)
    caminho_pdf = pasta / ("v%d.pdf" % versao)

    caminho_html.write_text(renderizar_html(contexto), encoding="utf-8")
    _caminho_instantaneo(codigo, versao).write_text(
        json.dumps(instantaneo, ensure_ascii=False, indent=1), encoding="utf-8")

    resultado_pdf = gerar_pdf(caminho_html, caminho_pdf, contexto)
    if resultado_pdf["sucesso"] and caminho_pdf.exists():
        hash_doc = _sha256_arquivo(caminho_pdf)
        origem_hash = "pdf"
        pdf_gravado = str(caminho_pdf.relative_to(RAIZ))
    else:
        # PDF indisponivel: o HTML e o entregavel e e dele que sai o hash.
        hash_doc = _sha256_arquivo(caminho_html)
        origem_hash = "html"
        pdf_gravado = None

    # --- linha em `dossie` (unica tabela que esta trilha escreve) ----------
    linha = db.inserir_dossie({
        "id": dossie_id,
        "lote_id": lote_id,
        "versao": versao,
        "gerado_em": contexto["gerado_em"],
        "status": contexto["status"],
        "aprovado_por": ("%s - %s" % (aprovacao["nome"], aprovacao["cargo"])
                         if aprovacao else None),
        "hash_sha256": hash_doc,
        "caminho_pdf": pdf_gravado,
        "caminho_html": str(caminho_html.relative_to(RAIZ)),
        "diff": diff_texto,
    })

    db.registrar_evento(
        "humano" if aprovacao else "sistema",
        "dossie_aprovado" if aprovacao else "dossie_gerado",
        "dossie", dossie_id,
        "Dossie do lote %s emitido na versao %d com status %s; %d talhoes, "
        "%d anexos, hash do %s %s."
        % (codigo, versao, contexto["status"], contexto["total_talhoes"],
           len(contexto["anexos"]), origem_hash, hash_doc[:16]))

    linha["origem_hash"] = origem_hash
    linha["erro_pdf"] = resultado_pdf["erro"]
    linha["diff_itens"] = itens_diff
    linha["codigo_lote"] = codigo
    return linha


def aprovar_dossie(dossie_id: str, nome: str, cargo: str) -> dict:
    """Aprova um dossie: gera versao nova, status 'aprovado', sem marca de agua.

    A versao anterior nao e alterada - o rascunho fica no historico, como
    manda uma trilha de auditoria honesta.
    """
    base = db.buscar("dossie", dossie_id)
    if not base:
        raise ValueError("dossie %r nao existe" % dossie_id)
    aprovacao = {"nome": nome, "cargo": cargo, "em": db.agora()}
    db.registrar_evento(
        "humano", "dossie_aprovacao_solicitada", "dossie", dossie_id,
        "%s (%s) solicitou a aprovacao do dossie versao %d."
        % (nome, cargo, base["versao"]))
    novo = gerar_dossie(base["lote_id"], aprovacao=aprovacao)
    novo["aprovado_a_partir_de"] = dossie_id
    return novo


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _imprimir(resultado: dict) -> None:
    print("")
    print("  lote .............. %s" % resultado["codigo_lote"])
    print("  versao ............ v%d  (%s)" % (resultado["versao"],
                                               resultado["status"]))
    print("  html .............. %s" % resultado["caminho_html"])
    if resultado["caminho_pdf"]:
        print("  pdf ............... %s" % resultado["caminho_pdf"])
    else:
        print("  pdf ............... NAO GERADO -> %s" % resultado["erro_pdf"])
        print("                      (o HTML e o entregavel primario)")
    print("  hash (%s) ....... %s" % (resultado["origem_hash"].ljust(4),
                                      resultado["hash_sha256"]))
    print("  diff .............. %s" % resultado["diff"][:300])
    print("")


def main(argv=None) -> int:
    # O console do Windows costuma abrir em cp1252 e engasgar com travessao e
    # aspas curvas. Forcar UTF-8 evita quebrar a demo por causa de um caractere.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(
        description="Gera o dossie de conformidade EUDR de um lote.")
    parser.add_argument("--lote", help="codigo (CAC-2026-114) ou id do lote")
    parser.add_argument("--todos", action="store_true",
                        help="gera o dossie de todos os lotes")
    parser.add_argument("--aprovar", action="store_true",
                        help="aprova a ultima versao do dossie do lote")
    parser.add_argument("--nome", help="nome do responsavel pela aprovacao")
    parser.add_argument("--cargo", help="cargo do responsavel pela aprovacao")
    parser.add_argument("--listar", action="store_true",
                        help="lista as versoes ja emitidas do lote")
    args = parser.parse_args(argv)

    db.criar_esquema()

    if args.todos:
        for lote in db.listar_lotes():
            print("== %s" % lote["codigo"])
            _imprimir(gerar_dossie(lote["id"]))
        return 0

    if not args.lote:
        parser.error("informe --lote CODIGO ou --todos")

    lote = db.buscar_lote_por_codigo(args.lote) or db.buscar_lote(args.lote)
    if not lote:
        print("lote %r nao encontrado." % args.lote)
        return 1

    if args.listar:
        for d in db.listar_dossies(lote["id"]):
            print("v%-3d %-9s %s  %s" % (d["versao"], d["status"],
                                         d["gerado_em"], d["hash_sha256"][:16]))
        return 0

    if args.aprovar:
        if not (args.nome and args.cargo):
            parser.error("--aprovar exige --nome e --cargo")
        versoes = db.listar_dossies(lote["id"])
        if not versoes:
            print("nao ha dossie para aprovar; gere um primeiro.")
            return 1
        ultima = max(versoes, key=lambda d: d["versao"])
        print("aprovando o dossie do lote %s (versao base v%d)..."
              % (lote["codigo"], ultima["versao"]))
        _imprimir(aprovar_dossie(ultima["id"], args.nome, args.cargo))
        return 0

    print("gerando dossie do lote %s..." % lote["codigo"])
    _imprimir(gerar_dossie(lote["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
