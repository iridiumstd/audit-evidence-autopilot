# -*- coding: utf-8 -*-
"""ingestao.py - Trilha A (Ingestao). SPEC.md secao 3.

Le os arquivos crus de dados/entrada/<produtor_slug>/, identifica o tipo pelo
params/cacau.yml, extrai campos, atribui confianca e status, copia com nome
canonico para dados/padronizado/<produtor_slug>/ e grava uma linha em
`documento` por arquivo - sempre via db.py, sempre com registrar_evento.

Uso:
    python ingestao.py --todos
    python ingestao.py --produtor joao-souza-oliveira

Regras respeitadas:
  - esta trilha escreve SO na tabela `documento` (mais `evento`);
  - toda escrita passa por db.py;
  - tipo nao reconhecido grava 'desconhecido'. Nao se chuta.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path

import yaml

import db

RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "dados" / "entrada"
PADRONIZADO = RAIZ / "dados" / "padronizado"
PARAMS = RAIZ / "params" / "cacau.yml"

EXT_PDF = {".pdf"}
EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
EXT_PLANILHA = {".xlsx", ".xls", ".csv"}

# ---------------------------------------------------------------------------
# Vocabulario controlado do nome de arquivo (contrato.md v2 / correcoes-spec_1
# secao 05). ATENCAO: o codigo curto abaixo vale SO para o NOME DO ARQUIVO.
# O valor gravado em `documento.tipo` continua sendo o tipo canonico do
# params/cacau.yml - nada aqui muda o que a Trilha B le.
#
# Mapeamento adotado (tipo canonico -> codigo do contrato):
#   matricula_imovel          -> MATR
#   ccir                      -> CCIR
#   itr                       -> DITR       (recibo da DITR / NIRF)
#   sigef                     -> SIGEF
#   contrato_arrendamento     -> POSSE      (arranjo de uso sem titulo formal)
#   declaracao_posse          -> POSSE
#   titulo_assentamento       -> TIT        (TD, CDRU, CCU)
#   car_recibo                -> CAR-REC
#   car_demonstrativo         -> CAR-DEM
#   licenca_ambiental         -> LIC
#   outorga_agua              -> LIC        (ato de licenciamento/outorga)
#   adesao_pra                -> LIC        (ato de regularizacao ambiental)
#   pmfs                      -> LIC        (autorizacao florestal)
#   manejo_cabruca            -> LIC        (autorizacao de manejo)
#   radar_siscomex            -> LIC        (habilitacao = ato autorizativo)
#   asv                       -> ASV
#   auto_infracao             -> EMB        (auto de infracao / termo de embargo)
#   dof                       -> CFIT       (documento que acompanha o transito da carga)
#   certidao_acoes_reais      -> CERT-RA
#   protocolo_consulta        -> DECL
#   ata_consulta_previa       -> DECL
#   acordo_reparticao         -> DECL
#   politica_direitos_humanos -> DECL
#   cndt                      -> TRAB
#   crf_fgts                  -> TRAB
#   registro_empregados       -> TRAB
#   contrato_trabalho         -> TRAB
#   nr31                      -> TRAB
#   decl_trabalho_infantil    -> TRAB
#   funrural_senar            -> TRAB       (contribuicao rural/SENAR)
#   consulta_acp              -> LAUDO      (resultado de consulta gerada)
#   consulta_ceis_cnep        -> LAUDO
#   nota_fiscal_produtor      -> NFP        (NFA/NF4/NF-ENT sao refinamentos da
#                                            NFP e saem do parsing da NF-e, ver
#                                            _refinar_codigo_nf)
#   due_embarque              -> NF-EXP
#   inscricao_estadual        -> IE-PR
#   cnd_federal               -> CND-ITR    (a CND federal e a que cobre o ITR)
#   cnd_estadual              -> CND-ITR    (familia CND; a esfera fica
#   cnd_municipal             -> CND-ITR     preservada em `documento.tipo`)
#   desconhecido / nao_documento -> NAOCLASS (nunca se chuta)
#
# Codigos ainda sem tipo canonico correspondente no params/cacau.yml, deixados
# reservados: CAF, DAP, ROM, FCOOP, CERT-ORG, CERT-FT, NFA, NF4, NF-ENT.
# ---------------------------------------------------------------------------
CODIGO_TIPO = {
    "matricula_imovel": "MATR",
    "ccir": "CCIR",
    "itr": "DITR",
    "sigef": "SIGEF",
    "contrato_arrendamento": "POSSE",
    "declaracao_posse": "POSSE",
    "titulo_assentamento": "TIT",
    "car_recibo": "CAR-REC",
    "car_demonstrativo": "CAR-DEM",
    "licenca_ambiental": "LIC",
    "outorga_agua": "LIC",
    "adesao_pra": "LIC",
    "pmfs": "LIC",
    "manejo_cabruca": "LIC",
    "radar_siscomex": "LIC",
    "asv": "ASV",
    "auto_infracao": "EMB",
    "dof": "CFIT",
    "certidao_acoes_reais": "CERT-RA",
    "protocolo_consulta": "DECL",
    "ata_consulta_previa": "DECL",
    "acordo_reparticao": "DECL",
    "politica_direitos_humanos": "DECL",
    "cndt": "TRAB",
    "crf_fgts": "TRAB",
    "registro_empregados": "TRAB",
    "contrato_trabalho": "TRAB",
    "nr31": "TRAB",
    "decl_trabalho_infantil": "TRAB",
    "funrural_senar": "TRAB",
    "consulta_acp": "LAUDO",
    "consulta_ceis_cnep": "LAUDO",
    "nota_fiscal_produtor": "NFP",
    "due_embarque": "NF-EXP",
    "inscricao_estadual": "IE-PR",
    "cnd_federal": "CND-ITR",
    "cnd_estadual": "CND-ITR",
    "cnd_municipal": "CND-ITR",
    "desconhecido": "NAOCLASS",
    "nao_documento": "NAOCLASS",
}

# vocabulario fechado - qualquer codigo fora daqui e erro de programacao
VOCABULARIO_TIPO = {
    "CAR-REC", "CAR-DEM", "CCIR", "DITR", "CND-ITR", "MATR", "TIT", "POSSE",
    "SIGEF", "NFP", "NFA", "NF4", "NF-ENT", "IE-PR", "CAF", "DAP", "ROM",
    "FCOOP", "LIC", "ASV", "EMB", "CERT-RA", "CERT-ORG", "CERT-FT", "DECL",
    "TRAB", "NF-EXP", "CFIT", "LAUDO", "NAOCLASS",
}

# titular sem CPF/CNPJ legivel e sem CPF de produtor no grupo (nao deve
# acontecer na base semeada, mas o nome precisa continuar valido)
TITULAR_INDEFINIDO = "SEMTITULAR"

# regex oficial do nome padronizado - o mesmo usado para validar a pasta
RE_NOME_PADRONIZADO = re.compile(
    r"^(?:%s)_(?:\d{11}|\d{14}|LOTE-[A-Za-z0-9\-]+|%s)_\d{8}u?_v\d{2}\.[a-z0-9]+$"
    % ("|".join(sorted((re.escape(c) for c in VOCABULARIO_TIPO), key=len,
                       reverse=True)), TITULAR_INDEFINIDO))

# ---------------------------------------------------------------------------
# Cores ANSI - a saida vai ao vivo na apresentacao
# ---------------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    NEG = "\033[1m"
    CINZA = "\033[90m"
    VERDE = "\033[32m"
    AMAR = "\033[33m"
    VERM = "\033[31m"
    AZUL = "\033[36m"


COR_STATUS = {
    "ok": C.VERDE,
    "vencido": C.AMAR,
    "divergente": C.VERM,
    "ilegivel": C.CINZA,
}


def _preparar_terminal() -> None:
    """Habilita ANSI no console do Windows e forca UTF-8 na saida."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Parametros da commodity
# ---------------------------------------------------------------------------
_PARAMS_CACHE = None


def carregar_params() -> dict:
    """Le params/cacau.yml uma unica vez por processo."""
    global _PARAMS_CACHE
    if _PARAMS_CACHE is None:
        with open(PARAMS, "r", encoding="utf-8") as f:
            _PARAMS_CACHE = yaml.safe_load(f)
    return _PARAMS_CACHE


def limiar_ilegivel() -> float:
    return float(carregar_params().get("confianca", {})
                 .get("limiar_ilegivel", 0.4))


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Minusculas, sem acento - para casar palavra-chave sem sofrimento."""
    if not texto:
        return ""
    sem = unicodedata.normalize("NFKD", texto)
    sem = "".join(c for c in sem if not unicodedata.combining(c))
    return sem.lower()


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def hash_arquivo(caminho: Path) -> str:
    """SHA-256 do arquivo, lido em blocos (nao carrega o arquivo inteiro)."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Extracao de texto - pdfplumber / pytesseract / pandas
# ---------------------------------------------------------------------------
def extrair_texto(caminho: Path) -> tuple:
    """Devolve (texto, metodo). Texto vazio significa arquivo ilegivel.

    Nunca levanta excecao: falha de leitura vira texto vazio e o status
    'ilegivel' cuida do resto.
    """
    ext = caminho.suffix.lower()
    try:
        if ext in EXT_PDF:
            return _texto_pdf(caminho), "pdfplumber"
        if ext in EXT_IMAGEM:
            return _texto_imagem(caminho), "pytesseract"
        if ext in EXT_PLANILHA:
            return _texto_planilha(caminho), "pandas"
    except Exception as erro:                     # pragma: no cover - defensivo
        return "", "falha:%s" % type(erro).__name__
    return "", "extensao_nao_suportada"


def _texto_pdf(caminho: Path) -> str:
    """pdfplumber. PDF que e so imagem devolve string vazia - e a armadilha."""
    import pdfplumber
    partes = []
    with pdfplumber.open(str(caminho)) as pdf:
        for pagina in pdf.pages:
            partes.append(pagina.extract_text() or "")
    return "\n".join(partes).strip()


_TESSERACT_OK = None


def _texto_imagem(caminho: Path) -> str:
    """pytesseract, se o binario existir. Se nao existir, devolve vazio -
    o arquivo cai em 'ilegivel' e a ingestao segue (SPEC secao 3, tabela)."""
    global _TESSERACT_OK
    if _TESSERACT_OK is False:
        return ""
    try:
        import pytesseract
        from PIL import Image
        texto = pytesseract.image_to_string(Image.open(caminho), lang="por")
        _TESSERACT_OK = True
        return (texto or "").strip()
    except Exception:
        _TESSERACT_OK = False
        return ""


def _texto_planilha(caminho: Path) -> str:
    """pandas: todas as abas viradas em texto, cabecalho incluido."""
    import pandas as pd
    if caminho.suffix.lower() == ".csv":
        quadros = {"csv": pd.read_csv(caminho, encoding="utf-8",
                                      on_bad_lines="skip")}
    else:
        quadros = pd.read_excel(caminho, sheet_name=None)
    partes = []
    for aba, quadro in quadros.items():
        partes.append(str(aba))
        partes.append(" ".join(str(c) for c in quadro.columns))
        partes.append(quadro.head(40).to_string(index=False))
    return "\n".join(partes).strip()


# ---------------------------------------------------------------------------
# Identificacao do tipo pelas palavras-chave do params/cacau.yml
# ---------------------------------------------------------------------------
def _casa_palavra(texto_norm: str, palavra: str) -> bool:
    """Palavra curta (sigla) casa so com limite de palavra; frase casa como
    substring. Evita 'CAR' casar dentro de 'cartorio'."""
    alvo = normalizar(palavra).strip()
    if not alvo:
        return False
    if len(alvo) <= 5 and " " not in alvo:
        return re.search(r"(?<![0-9a-z])%s(?![0-9a-z])" % re.escape(alvo),
                         texto_norm) is not None
    return alvo in texto_norm


def identificar_tipo(texto: str, nome_arquivo: str = "") -> dict:
    """Escolhe o tipo canonico com maior pontuacao.

    Pontuacao = soma do tamanho das palavras-chave casadas, com bonus para as
    que aparecem no cabecalho (primeiras linhas). Empate resolve pelo maior
    numero de palavras casadas. Sem nenhuma casada -> 'desconhecido'.
    """
    tipos = carregar_params()["tipos"]
    texto_norm = normalizar(texto)
    cabecalho = normalizar("\n".join(texto.splitlines()[:3]))
    melhor = {"tipo": "desconhecido", "pontos": 0.0, "casadas": []}
    for nome_tipo, cfg in tipos.items():
        chaves = cfg.get("palavras_chave") or []
        if not chaves:
            continue                     # 'desconhecido' e 'nao_documento'
        pontos, casadas = 0.0, []
        for palavra in chaves:
            if _casa_palavra(texto_norm, palavra):
                casadas.append(palavra)
                pontos += len(normalizar(palavra))
                if _casa_palavra(cabecalho, palavra):
                    pontos += 6.0        # cabecalho vale mais que rodape
        if not casadas:
            continue
        atual = (pontos, len(casadas))
        anterior = (melhor["pontos"], len(melhor["casadas"]))
        if atual > anterior:
            melhor = {"tipo": nome_tipo, "pontos": pontos, "casadas": casadas}
    return melhor


# ---------------------------------------------------------------------------
# Extracao de campos
# ---------------------------------------------------------------------------
RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
RE_DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
RE_DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _iso(dia: str, mes: str, ano: str) -> str:
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


def _campo_apos(texto: str, rotulos: list) -> str:
    """Pega o valor depois de 'Rotulo:' na mesma linha, sem depender de acento."""
    for linha in texto.splitlines():
        norm = normalizar(linha)
        for rotulo in rotulos:
            marca = normalizar(rotulo)
            if norm.startswith(marca) or (":" in linha and marca in norm.split(":")[0]):
                valor = linha.split(":", 1)[1].strip() if ":" in linha else ""
                if valor:
                    return valor
    return None


def _data_rotulada(texto: str, rotulos: list) -> str:
    """Data ISO da primeira linha que contenha um dos rotulos."""
    for linha in texto.splitlines():
        norm = normalizar(linha)
        if any(normalizar(r) in norm for r in rotulos):
            achou = RE_DATA_BR.search(linha)
            if achou:
                return _iso(*achou.groups())
            achou = RE_DATA_ISO.search(linha)
            if achou:
                a, m, d = achou.groups()
                return _iso(d, m, a)
    return None


# ---------------------------------------------------------------------------
# Parsing de NF-e - a armadilha da secao 05 do correcoes-spec_1.md
#
# Tres coisas que quebram parser ingenuo:
#   1. na NF-e de pessoa fisica as series ficam na faixa 920-969 e o CPF entra
#      com ZEROS A ESQUERDA nas 14 posicoes do campo CNPJ da chave de acesso -
#      quem espera CNPJ erra o produtor em toda nota de produtor;
#   2. nota modelo 4 (papel, legado) NAO tem chave de acesso - ausencia de
#      chave nao e erro nem motivo de status ruim;
#   3. CFOP 5102/6102 e revenda (atravessador): o elo vira 'intermediario',
#      nunca e descartado.
#
# Layout da chave de acesso (44 digitos):
#   cUF(2) AAMM(4) CNPJ/CPF(14) mod(2) serie(3) nNF(9) tpEmis(1) cNF(8) cDV(1)
# ---------------------------------------------------------------------------
RE_CHAVE_NFE = re.compile(r"(?<!\d)(\d{44})(?!\d)")
RE_CHAVE_ESPACADA = re.compile(r"(?<!\d)((?:\d{4}[ .\-]){10}\d{4})(?!\d)")
RE_CFOP = re.compile(r"\b([1-7]\d{3})\b")
CFOP_REVENDA = {"5102", "6102"}
SERIE_PF_MIN, SERIE_PF_MAX = 920, 969


def _formatar_cpf(digitos: str) -> str:
    """11 digitos -> 000.000.000-00 (mesmo formato que o RE_CPF produz)."""
    return "%s.%s.%s-%s" % (digitos[:3], digitos[3:6], digitos[6:9],
                            digitos[9:11])


def achar_chave_acesso(texto: str) -> str:
    """Devolve os 44 digitos da chave, aceitando a impressao em grupos de 4.
    Ausencia de chave devolve None e NAO e erro (nota modelo 4)."""
    achou = RE_CHAVE_NFE.search(texto or "")
    if achou:
        return achou.group(1)
    achou = RE_CHAVE_ESPACADA.search(texto or "")
    if achou:
        return so_digitos(achou.group(1))
    return None


def decompor_chave_acesso(chave: str) -> dict:
    """Quebra a chave de 44 digitos. Trata o campo CNPJ com CPF zero-a-esquerda."""
    if not chave or len(chave) != 44 or not chave.isdigit():
        return {}
    dados = {
        "chave_acesso": chave,
        "uf_ibge": chave[0:2],
        "aamm": chave[2:6],
        "modelo": chave[20:22],
        "serie": chave[22:25],
        "numero_nf": chave[25:34].lstrip("0") or "0",
    }
    documento_emitente = chave[6:20]          # 14 posicoes do campo "CNPJ"
    if documento_emitente.startswith("000"):
        # CPF de 11 digitos preenchido com zeros a esquerda - produtor PF
        dados["cpf_emitente"] = _formatar_cpf(documento_emitente[3:])
        dados["emitente_pessoa_fisica"] = True
    else:
        dados["cnpj_emitente"] = documento_emitente
        dados["emitente_pessoa_fisica"] = False
    try:
        serie = int(dados["serie"])
        if SERIE_PF_MIN <= serie <= SERIE_PF_MAX:
            # faixa reservada a produtor rural pessoa fisica
            dados["serie_produtor_pf"] = True
            dados["emitente_pessoa_fisica"] = True
    except ValueError:
        pass
    return dados


def parse_nfe(texto: str) -> dict:
    """Campos de NF-e extraidos defensivamente. Nada aqui e obrigatorio:
    nota sem chave, sem serie ou sem CFOP devolve o que der."""
    achados = {}
    if not texto:
        return achados
    chave = achar_chave_acesso(texto)
    if chave:
        achados.update(decompor_chave_acesso(chave))
    else:
        achados["chave_acesso_ausente"] = True   # modelo 4 nao tem chave

    # serie impressa no corpo, quando nao veio pela chave
    achou = re.search(r"[Ss][eé]rie[^0-9]{0,10}(\d{1,3})", texto)
    if achou:
        achados.setdefault("serie", achou.group(1).zfill(3))
        try:
            if SERIE_PF_MIN <= int(achou.group(1)) <= SERIE_PF_MAX:
                achados["serie_produtor_pf"] = True
                achados["emitente_pessoa_fisica"] = True
        except ValueError:
            pass

    achou = re.search(r"[Mm]odelo[^0-9]{0,10}(\d{1,2})", texto)
    if achou:
        achados.setdefault("modelo", achou.group(1).zfill(2))
    if achados.get("modelo") == "04":
        achados["nota_modelo_4"] = True          # papel/legado: sem chave, ok

    # CFOP: 5102/6102 e revenda -> o elo e intermediario, nunca descartado
    achou = re.search(r"CFOP[^0-9]{0,10}([1-7]\d{3})", texto)
    if not achou:
        for linha in texto.splitlines():
            if "cfop" in normalizar(linha):
                achou = RE_CFOP.search(linha)
                if achou:
                    break
    if achou:
        cfop = achou.group(1)
        achados["cfop"] = cfop
        if cfop in CFOP_REVENDA:
            achados["elo"] = "intermediario"
            achados["cfop_revenda"] = True
        else:
            achados["elo"] = "produtor"
    return achados


def extrair_campos(texto: str, tipo: str) -> dict:
    """Campos comuns a qualquer documento + os especificos do tipo.

    Devolve dict simples, pronto para virar campos_json.
    """
    campos = {}
    if not texto:
        return campos

    cpfs = RE_CPF.findall(texto)
    if cpfs:
        campos["cpf"] = cpfs[0]
        if len(set(cpfs)) > 1:
            campos["cpfs_encontrados"] = sorted(set(cpfs))
    cnpjs = RE_CNPJ.findall(texto)
    if cnpjs:
        campos["cnpj"] = cnpjs[0]

    nome = _campo_apos(texto, ["Titular", "Proprietario", "Declarante",
                               "Arrendatario", "Beneficiario", "produtor"])
    if nome:
        campos["nome"] = nome

    municipio = _campo_apos(texto, ["Municipio"])
    if municipio:
        campos["municipio"] = municipio.split("/")[0].strip()

    emissao = _data_rotulada(texto, ["Data de emissao", "Emissao", "Emitido em"])
    if emissao:
        campos["data_emissao"] = emissao
    validade = _data_rotulada(texto, ["Valido ate", "Validade", "Valida ate",
                                      "Data de validade"])
    if validade:
        campos["data_validade"] = validade

    # vigencia de contrato: "Vigencia: dd/mm/aaaa a dd/mm/aaaa"
    for linha in texto.splitlines():
        if "vigencia" in normalizar(linha):
            datas = RE_DATA_BR.findall(linha)
            if len(datas) >= 2:
                campos["vigencia_inicio"] = _iso(*datas[0])
                campos["vigencia_fim"] = _iso(*datas[1])
                campos.setdefault("data_validade", _iso(*datas[1]))

    # numero do documento - o primeiro rotulo que aparecer
    numero = _campo_apos(texto, ["Numero do CAR", "Numero do termo",
                                 "Codigo do imovel rural", "Numero", "Matricula n",
                                 "NIRF", "Codigo"])
    if numero:
        campos["numero"] = numero.split()[0] if numero.split() else numero
    achou_mat = re.search(r"[Mm]atricula n[\.\s]*(\d+)", texto)
    if achou_mat:
        campos["numero_matricula"] = achou_mat.group(1)

    # areas em hectare
    areas = {}
    for linha in texto.splitlines():
        norm = normalizar(linha)
        achou = re.search(r"([\d.]+,\d+|\d+\.\d+|\d+)\s*ha\b", norm)
        if not achou:
            continue
        try:
            valor = float(achou.group(1).replace(".", "").replace(",", ".")) \
                if "," in achou.group(1) else float(achou.group(1))
        except ValueError:
            continue
        rotulo = norm.split(":")[0].strip() if ":" in norm else "area"
        areas[rotulo] = valor
    if areas:
        for rotulo, valor in areas.items():
            if rotulo.startswith("area") and "area_ha" not in campos and \
                    "reserva" not in rotulo and "app" not in rotulo:
                campos["area_ha"] = valor
        campos["areas_ha"] = areas
        campos.setdefault("area_ha", list(areas.values())[0])

    if tipo == "nota_fiscal_produtor":
        achou = re.search(r"[Qq]uantidade[^\d]*([\d.,]+)\s*kg", texto)
        if achou:
            try:
                campos["quantidade_kg"] = float(
                    achou.group(1).replace(".", "").replace(",", "."))
            except ValueError:
                pass
    # NF-e: parsing defensivo, so acrescenta chaves (nunca renomeia as antigas)
    if tipo in ("nota_fiscal_produtor", "due_embarque") or "nota fiscal" in \
            normalizar(texto)[:4000]:
        for chave, valor in parse_nfe(texto).items():
            campos.setdefault(chave, valor)
        # o CPF do emitente lido da chave de acesso serve de CPF do documento
        # quando o corpo nao trouxe CPF formatado - e a armadilha da secao 05
        if not campos.get("cpf") and campos.get("cpf_emitente"):
            campos["cpf"] = campos["cpf_emitente"]
    if tipo in ("car_recibo", "car_demonstrativo"):
        situacao = _campo_apos(texto, ["Situacao do cadastro", "Situacao"])
        if situacao:
            campos["situacao"] = situacao
    if tipo == "matricula_imovel":
        cartorio = _campo_apos(texto, ["Cartorio"])
        if cartorio:
            campos["cartorio"] = cartorio
    if tipo == "contrato_arrendamento":
        for rotulo in ("Arrendador", "Arrendatario"):
            valor = _campo_apos(texto, [rotulo])
            if valor:
                campos[normalizar(rotulo)] = valor

    # talhao citado no corpo - usado para amarrar documento -> talhao
    achou = re.search(r"[Tt]alhao de referencia:\s*([^\(\n]+)", texto)
    if achou:
        campos["talhao_citado"] = achou.group(1).strip()
    return campos


# ---------------------------------------------------------------------------
# Confianca
# ---------------------------------------------------------------------------
def calcular_confianca(texto: str, tipo: str, deteccao: dict,
                       campos: dict) -> float:
    """0.0 a 1.0. Combina quantidade de texto, forca do casamento de tipo e
    quantidade de campos esperados que foram realmente extraidos."""
    if not texto.strip():
        return 0.0
    if tipo in ("desconhecido", "nao_documento"):
        # ha texto, mas nenhuma palavra-chave casou: confianca baixa de proposito
        return round(min(0.35, 0.10 + len(texto) / 8000.0), 2)

    esperados = carregar_params()["tipos"][tipo].get("campos") or []
    obtidos = sum(1 for c in esperados
                  if c in campos or c.split("_")[0] in campos)
    conf = 0.30
    conf += min(0.30, 0.10 * len(deteccao.get("casadas", [])))
    conf += min(0.25, 0.06 * len(campos))
    if esperados:
        conf += 0.15 * (obtidos / float(len(esperados)))
    if len(texto) < 120:
        conf -= 0.25                       # texto curto demais para confiar
    return round(max(0.0, min(1.0, conf)), 2)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
def _nomes_parecidos(a: str, b: str) -> bool:
    """Compara nomes ignorando acento, caixa e pontuacao. Considera parecido
    quando pelo menos 2 tokens (ou todos, se houver menos) coincidem."""
    ta = set(normalizar(a).replace(".", " ").split())
    tb = set(normalizar(b).replace(".", " ").split())
    if not ta or not tb:
        return True
    comuns = ta & tb
    return len(comuns) >= min(2, len(ta), len(tb))


def decidir_status(texto: str, confianca: float, campos: dict,
                   produtor: dict, hoje: date = None) -> tuple:
    """Devolve (status, motivo). Ordem do SPEC secao 3: ilegivel, vencido,
    divergente, ok."""
    hoje = hoje or date.today()
    if not texto.strip():
        return "ilegivel", "nenhum texto extraido do arquivo"
    if confianca < limiar_ilegivel():
        return "ilegivel", "confianca %.2f abaixo do limiar %.2f" % (
            confianca, limiar_ilegivel())

    validade = campos.get("data_validade")
    if validade:
        try:
            if date.fromisoformat(validade) < hoje:
                return "vencido", "validade %s anterior a %s" % (
                    validade, hoje.isoformat())
        except ValueError:
            pass

    cpf_doc = so_digitos(campos.get("cpf") or "")
    cpf_prod = so_digitos(produtor.get("cpf") or "")
    if cpf_doc and cpf_prod and cpf_doc != cpf_prod:
        return "divergente", "CPF %s no documento difere do CPF %s do produtor" \
            % (campos.get("cpf"), produtor.get("cpf"))

    nome_doc = campos.get("nome")
    if nome_doc and produtor.get("nome") and \
            not _nomes_parecidos(nome_doc, produtor["nome"]):
        return "divergente", "titular '%s' difere do produtor '%s'" % (
            nome_doc, produtor["nome"])
    return "ok", "sem inconsistencia detectada"


# ---------------------------------------------------------------------------
# Nome canonico e copia padronizada
# ---------------------------------------------------------------------------
def codigo_tipo(tipo: str, campos: dict = None) -> str:
    """Tipo canonico do params/cacau.yml -> codigo curto do contrato v2.
    Tipo fora do mapa nunca vira palpite: cai em NAOCLASS."""
    codigo = CODIGO_TIPO.get(tipo, "NAOCLASS")
    if codigo == "NFP" and campos:
        # refinamento pelo parsing da NF-e: modelo 4 (papel) tem codigo proprio
        if campos.get("nota_modelo_4") or campos.get("modelo") == "04":
            codigo = "NF4"
        elif campos.get("elo") == "intermediario":
            codigo = "NF-ENT"   # entrada/atravessador: revenda, nao producao
    return codigo if codigo in VOCABULARIO_TIPO else "NAOCLASS"


def titular_arquivo(campos: dict, produtor: dict, codigo: str,
                    lote_id: str = None) -> str:
    """TITULAR do nome: CPF de 11 digitos do documento; sem CPF legivel, o CPF
    do produtor do grupo; documento de lote, LOTE-{id}; cooperativa, CNPJ."""
    if lote_id:
        return "LOTE-%s" % re.sub(r"[^A-Za-z0-9\-]", "", str(lote_id))
    cpf_doc = so_digitos(campos.get("cpf") or campos.get("cpf_emitente") or "")
    if len(cpf_doc) == 11:
        return cpf_doc
    cnpj_doc = so_digitos(campos.get("cnpj") or campos.get("cnpj_emitente") or "")
    # documento da cooperativa / exportacao anda no CNPJ
    if codigo in ("FCOOP", "NF-EXP") and len(cnpj_doc) == 14:
        return cnpj_doc
    cpf_prod = so_digitos((produtor or {}).get("cpf") or "")
    if len(cpf_prod) == 11:
        return cpf_prod
    if len(cnpj_doc) == 14:
        return cnpj_doc
    return TITULAR_INDEFINIDO


def data_arquivo(campos: dict, origem: Path) -> str:
    """AAAAMMDD da emissao. Emissao ilegivel usa a data do upload (mtime do
    arquivo cru na pasta de entrada) com o sufixo 'u'."""
    emissao = campos.get("data_emissao")
    if emissao:
        try:
            return date.fromisoformat(str(emissao)[:10]).strftime("%Y%m%d")
        except ValueError:
            pass
    upload = date.fromtimestamp(origem.stat().st_mtime)
    return upload.strftime("%Y%m%d") + "u"


# assinaturas de conteudo - a extensao tem de ser verdadeira ao conteudo:
# foto de DANFE e .jpg, nunca PDF requalificado
_ASSINATURAS = (
    (b"%PDF", ".pdf"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"II*\x00", ".tif"),
    (b"MM\x00*", ".tif"),
    (b"BM", ".bmp"),
    (b"PK\x03\x04", ".xlsx"),
    (b"\xd0\xcf\x11\xe0", ".xls"),
)


def extensao_verdadeira(origem: Path) -> str:
    """Le os primeiros bytes e devolve a extensao coerente com o conteudo.
    Sem assinatura conhecida (texto puro, XML, CSV), mantem a de origem."""
    try:
        with open(origem, "rb") as f:
            cabecalho = f.read(16)
    except OSError:
        return origem.suffix.lower()
    for marca, ext in _ASSINATURAS:
        if cabecalho.startswith(marca):
            if ext == ".xlsx" and origem.suffix.lower() in (".docx", ".zip"):
                return origem.suffix.lower()
            return ext
    inicio = cabecalho.lstrip()[:5].lower()
    if inicio.startswith(b"<?xml"):
        return ".xml"
    return origem.suffix.lower() or ".bin"


def nome_padronizado(codigo: str, titular: str, data_ref: str, versao: int,
                     extensao: str) -> str:
    """{TIPO}_{TITULAR}_{AAAAMMDD}_{VERSAO}.{ext} - contrato.md v2."""
    return "%s_%s_%s_v%02d%s" % (codigo, titular, data_ref, versao,
                                 extensao.lower())


def copiar_padronizado(origem: Path, slug: str, codigo: str, titular: str,
                       data_ref: str, contador: dict) -> tuple:
    """Copia para dados/padronizado/<slug>/ com o nome novo e devolve
    (caminho, versao). A versao incrementa por tipo+titular e o arquivo
    anterior NUNCA e apagado - a trilha de auditoria e parte do produto."""
    destino_pasta = PADRONIZADO / slug
    destino_pasta.mkdir(parents=True, exist_ok=True)
    chave = (codigo, titular)
    versao = contador.get(chave, 0) + 1
    contador[chave] = versao
    extensao = extensao_verdadeira(origem)
    destino = destino_pasta / nome_padronizado(codigo, titular, data_ref,
                                               versao, extensao)
    shutil.copy2(origem, destino)
    return destino, versao


def validar_pasta_padronizado(raiz: Path = None) -> dict:
    """Confere a pasta inteira contra a RE_NOME_PADRONIZADO do contrato v2.
    Devolve total, validos e a lista dos que nao seguem o padrao."""
    raiz = raiz or PADRONIZADO
    invalidos, total = [], 0
    if raiz.exists():
        for arquivo in sorted(raiz.rglob("*")):
            if not arquivo.is_file():
                continue
            total += 1
            if not RE_NOME_PADRONIZADO.match(arquivo.name):
                invalidos.append(str(arquivo.relative_to(RAIZ)))
    return {"total": total, "validos": total - len(invalidos),
            "invalidos": invalidos}


# ---------------------------------------------------------------------------
# Mapa de lacunas
# ---------------------------------------------------------------------------
def mapa_lacunas(tipos_presentes: set, textos_norm: str = "") -> dict:
    """Confronta os tipos encontrados com o conjunto minimo do cacau.yml,
    incluindo as regras `um_de` e as `condicionais`."""
    minimo = carregar_params().get("conjunto_minimo", {}) or {}
    obrigatorios = minimo.get("obrigatorios") or []
    faltando = [t for t in obrigatorios if t not in tipos_presentes]

    grupos = []
    for grupo in (minimo.get("um_de") or []):
        atendido = [t for t in grupo if t in tipos_presentes]
        grupos.append({
            "opcoes": list(grupo),
            "atendido": bool(atendido),
            "encontrados": atendido,
        })

    condicionais = []
    for tipo, condicao in (minimo.get("condicionais") or {}).items():
        # a condicao so vale se algum documento do produtor sugerir o cenario
        gatilho = any(p in textos_norm for p in
                      ("arrendamento", "arrendatario", "arrendador",
                       "parceria agricola", "comodato"))
        condicionais.append({
            "tipo": tipo,
            "condicao": condicao,
            "aplicavel": bool(gatilho),
            "presente": tipo in tipos_presentes,
            "falta": bool(gatilho) and tipo not in tipos_presentes,
        })

    faltando_total = list(faltando)
    for g in grupos:
        if not g["atendido"]:
            faltando_total.append("um_de(%s)" % "|".join(g["opcoes"]))
    for c in condicionais:
        if c["falta"]:
            faltando_total.append("%s (condicional)" % c["tipo"])

    return {
        "obrigatorios": obrigatorios,
        "presentes": sorted(tipos_presentes),
        "faltando_obrigatorios": faltando,
        "grupos_um_de": grupos,
        "condicionais": condicionais,
        "faltando": faltando_total,
        "apto": not faltando_total,
    }


# ---------------------------------------------------------------------------
# Processamento de um produtor
# ---------------------------------------------------------------------------
def processar_produtor(produtor_slug: str, verboso: bool = True) -> dict:
    """SPEC secao 3. Processa todos os arquivos crus de um produtor.

    Devolve dict com contagem de arquivos, contagem por status, contagem por
    tipo, lista de documentos e o mapa de lacunas.
    """
    produtor = db.buscar_produtor_por_slug(produtor_slug)
    if not produtor:
        raise ValueError("produtor com slug %r nao existe no banco"
                         % produtor_slug)

    pasta = ENTRADA / produtor_slug
    arquivos = sorted([a for a in pasta.iterdir() if a.is_file()]) \
        if pasta.exists() else []

    talhoes = db.listar_talhoes(produtor["id"])
    por_nome_talhao = {normalizar(t["nome"]): t["id"] for t in talhoes}

    if verboso:
        print("%s%s%s  %s%s%s  (%d arquivo%s)" % (
            C.NEG, produtor["nome"], C.RESET, C.CINZA, produtor_slug, C.RESET,
            len(arquivos), "" if len(arquivos) == 1 else "s"))

    documentos = []
    contador_versao = {}          # (codigo, titular) -> ultima versao usada
    por_status, por_tipo = {}, {}
    tipos_presentes, textos_norm = set(), []
    hashes_vistos = {}

    # idempotencia por arquivo_origem: arquivo ja ingerido ATUALIZA a linha
    # existente (nome padronizado e versao), nunca duplica e nunca apaga evento
    ja_ingeridos = {d["arquivo_origem"]: d
                    for d in db.listar_documentos(produtor["id"])}

    for arquivo in arquivos:
        relativo = str(arquivo.relative_to(RAIZ))
        anterior = ja_ingeridos.get(relativo)
        sha = hash_arquivo(arquivo)
        texto, metodo = extrair_texto(arquivo)
        textos_norm.append(normalizar(texto))

        deteccao = identificar_tipo(texto, arquivo.name)
        tipo = deteccao["tipo"]
        # imagem/arquivo sem texto util nao e documento - nao se chuta o tipo
        if not texto.strip():
            tipo = "nao_documento" if arquivo.suffix.lower() in EXT_IMAGEM \
                else "desconhecido"

        campos = extrair_campos(texto, tipo)
        # validade derivada de validade_dias quando o documento nao a declara
        cfg = carregar_params()["tipos"].get(tipo, {})
        if not campos.get("data_validade") and campos.get("data_emissao") \
                and cfg.get("validade_dias"):
            from datetime import timedelta
            campos["data_validade"] = (
                date.fromisoformat(campos["data_emissao"])
                + timedelta(days=int(cfg["validade_dias"]))).isoformat()
            campos["validade_derivada"] = True

        confianca = calcular_confianca(texto, tipo, deteccao, campos)
        status, motivo = decidir_status(texto, confianca, campos, produtor)

        campos["metodo_extracao"] = metodo
        campos["palavras_chave_casadas"] = deteccao.get("casadas", [])
        campos["motivo_status"] = motivo
        if sha in hashes_vistos:
            # mesmo conteudo com outro nome: duplicado. Vira v02 do mesmo
            # tipo+titular e o v01 continua na pasta.
            campos["duplicata_de"] = hashes_vistos[sha]
            campos["duplicado"] = True
        else:
            hashes_vistos[sha] = arquivo.name

        # --- nomenclatura nova: {TIPO}_{TITULAR}_{AAAAMMDD}_{VERSAO}.{ext} ---
        codigo = codigo_tipo(tipo, campos)
        titular = titular_arquivo(campos, produtor, codigo)
        data_ref = data_arquivo(campos, arquivo)
        campos["codigo_tipo_arquivo"] = codigo
        campos["titular_arquivo"] = titular
        campos["data_arquivo"] = data_ref
        if data_ref.endswith("u"):
            campos["data_emissao_ilegivel"] = True
        destino, versao = copiar_padronizado(arquivo, produtor_slug, codigo,
                                             titular, data_ref,
                                             contador_versao)
        campos["versao"] = versao

        talhao_id = None
        citado = normalizar(campos.get("talhao_citado") or "")
        if citado in por_nome_talhao:
            talhao_id = por_nome_talhao[citado]

        dados = {
            "produtor_id": produtor["id"],
            "talhao_id": talhao_id,
            "arquivo_origem": relativo,
            "arquivo_padronizado": str(destino.relative_to(RAIZ)),
            "tipo": tipo,
            "campos_json": json.dumps(campos, ensure_ascii=False),
            "data_emissao": campos.get("data_emissao"),
            "data_validade": campos.get("data_validade"),
            "hash_sha256": sha,
            "confianca": confianca,
            "status": status,
            "versao": versao,
        }
        if anterior:
            linha = db.atualizar("documento", anterior["id"], dados)
            db.registrar_evento(
                "sistema", "documento_reprocessado", "documento", linha["id"],
                "%s renomeado para %s (v%02d, tipo %s, status %s)"
                % (arquivo.name, destino.name, versao, tipo, status))
        else:
            linha = db.inserir_documento(dados)
            db.registrar_evento(
                "sistema", "documento_processado", "documento", linha["id"],
                "%s classificado como %s (confianca %.2f, status %s): %s"
                % (arquivo.name, tipo, confianca, status, motivo))

        if tipo not in ("desconhecido", "nao_documento"):
            tipos_presentes.add(tipo)
        por_status[status] = por_status.get(status, 0) + 1
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        documentos.append({
            "id": linha["id"], "arquivo": arquivo.name, "tipo": tipo,
            "status": status, "confianca": confianca, "hash_sha256": sha,
            "arquivo_padronizado": destino.name, "motivo": motivo,
        })

        if verboso:
            cor = COR_STATUS.get(status, "")
            print("   %s%-8s%s %-34.34s -> %-22s conf %.2f  %s%s"
                  % (cor, status.upper(), C.RESET, arquivo.name, tipo,
                     confianca, C.CINZA + destino.name + C.RESET, ""))

    lacunas = mapa_lacunas(tipos_presentes, " ".join(textos_norm))
    if verboso:
        if lacunas["faltando"]:
            print("   %slacunas:%s %s" % (C.AMAR, C.RESET,
                                          ", ".join(lacunas["faltando"])))
        else:
            print("   %sconjunto minimo completo%s" % (C.VERDE, C.RESET))
        print("")

    resultado = {
        "produtor_id": produtor["id"],
        "produtor_nome": produtor["nome"],
        "slug": produtor_slug,
        "arquivos": len(arquivos),
        "por_status": por_status,
        "por_tipo": por_tipo,
        "documentos": documentos,
        "mapa_lacunas": lacunas,
    }
    db.registrar_evento(
        "sistema", "produtor_ingerido", "produtor", produtor["id"],
        "%d arquivo(s) processado(s); lacunas: %s"
        % (len(arquivos), ", ".join(lacunas["faltando"]) or "nenhuma"))
    return resultado


# ---------------------------------------------------------------------------
# Processamento de todos
# ---------------------------------------------------------------------------
def _barra(titulo: str) -> None:
    print("%s%s%s" % (C.AZUL, "=" * 78, C.RESET))
    print("%s%s%s" % (C.NEG, titulo, C.RESET))
    print("%s%s%s" % (C.AZUL, "=" * 78, C.RESET))


def processar_todos(verboso: bool = True) -> dict:
    """Roda os 60 produtores e imprime o resumo. SPEC secao 3."""
    _preparar_terminal()
    inicio = time.time()
    db.criar_esquema()
    produtores = db.listar_produtores()

    _barra("TRILHA A - INGESTAO  |  %d produtores  |  %s"
           % (len(produtores), datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    print("")

    total_status, total_tipo = {}, {}
    total_arquivos = 0
    lacunas_agregadas = {}
    sem_lacuna = 0
    resultados = []

    for i, produtor in enumerate(produtores, 1):
        if verboso:
            print("%s[%02d/%02d]%s " % (C.AZUL, i, len(produtores), C.RESET),
                  end="")
        res = processar_produtor(produtor["slug"], verboso=verboso)
        resultados.append(res)
        total_arquivos += res["arquivos"]
        for s, n in res["por_status"].items():
            total_status[s] = total_status.get(s, 0) + n
        for t, n in res["por_tipo"].items():
            total_tipo[t] = total_tipo.get(t, 0) + n
        if res["mapa_lacunas"]["faltando"]:
            for item in res["mapa_lacunas"]["faltando"]:
                lacunas_agregadas[item] = lacunas_agregadas.get(item, 0) + 1
        else:
            sem_lacuna += 1

    duracao = time.time() - inicio

    _barra("RESUMO DA INGESTAO")
    print("  produtores processados : %d" % len(produtores))
    print("  arquivos processados   : %d" % total_arquivos)
    print("  documentos no banco    : %d" % db.contar("documento"))
    print("")
    print("  %sStatus%s" % (C.NEG, C.RESET))
    for s in ("ok", "vencido", "divergente", "ilegivel"):
        n = total_status.get(s, 0)
        pct = (100.0 * n / total_arquivos) if total_arquivos else 0
        cor = COR_STATUS.get(s, "")
        print("    %s%-11s%s %4d  %5.1f%%  %s" % (
            cor, s, C.RESET, n, pct, "#" * int(pct / 2)))
    print("")
    print("  %sTipos identificados (top 12)%s" % (C.NEG, C.RESET))
    for tipo, n in sorted(total_tipo.items(), key=lambda x: -x[1])[:12]:
        print("    %-26s %4d" % (tipo, n))
    print("")
    print("  %sMapa de lacunas agregado%s" % (C.NEG, C.RESET))
    print("    produtores com conjunto minimo completo: %s%d de %d%s"
          % (C.VERDE, sem_lacuna, len(produtores), C.RESET))
    if lacunas_agregadas:
        for item, n in sorted(lacunas_agregadas.items(), key=lambda x: -x[1]):
            print("    %s%-46s%s falta em %2d produtor(es)"
                  % (C.AMAR, item, C.RESET, n))
    else:
        print("    nenhuma lacuna")
    print("")
    print("  %sNomenclatura (contrato v2)%s" % (C.NEG, C.RESET))
    conferencia = validar_pasta_padronizado()
    cor = C.VERDE if not conferencia["invalidos"] else C.VERM
    print("    arquivos padronizados: %d  |  %sno padrao: %d%s  |  fora: %d"
          % (conferencia["total"], cor, conferencia["validos"], C.RESET,
             len(conferencia["invalidos"])))
    for item in conferencia["invalidos"][:5]:
        print("      %sfora do padrao:%s %s" % (C.VERM, C.RESET, item))
    print("")
    print("  tempo total: %s%.1f s%s  (%.0f arquivos/s)"
          % (C.NEG, duracao, C.RESET,
             total_arquivos / duracao if duracao else 0))
    print("%s%s%s" % (C.AZUL, "=" * 78, C.RESET))

    db.registrar_evento(
        "sistema", "ingestao_concluida", "documento", None,
        "%d arquivos de %d produtores; %s" % (
            total_arquivos, len(produtores),
            "; ".join("%s=%d" % (s, n) for s, n in sorted(total_status.items()))))

    return {
        "produtores": len(produtores),
        "arquivos": total_arquivos,
        "por_status": total_status,
        "por_tipo": total_tipo,
        "lacunas_agregadas": lacunas_agregadas,
        "produtores_completos": sem_lacuna,
        "duracao_s": round(duracao, 2),
        "resultados": resultados,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    _preparar_terminal()
    p = argparse.ArgumentParser(description="Trilha A - ingestao documental")
    p.add_argument("--todos", action="store_true",
                   help="processa os 60 produtores")
    p.add_argument("--produtor", metavar="SLUG",
                   help="processa apenas um produtor")
    p.add_argument("--silencioso", action="store_true",
                   help="so o resumo, sem linha por arquivo")
    p.add_argument("--validar-nomes", action="store_true",
                   help="confere dados/padronizado/ contra a regex do contrato")
    args = p.parse_args()

    if args.validar_nomes:
        res = validar_pasta_padronizado()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if not res["invalidos"] else 1
    if args.produtor:
        res = processar_produtor(args.produtor, verboso=not args.silencioso)
        print(json.dumps({k: v for k, v in res.items() if k != "documentos"},
                         ensure_ascii=False, indent=2))
        return 0
    if args.todos:
        processar_todos(verboso=not args.silencioso)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
