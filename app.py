# -*- coding: utf-8 -*-
"""Trilha D - interface da gestora (streamlit).

Tres telas, na ordem em que importam:

  1 · LOTES          semaforo por lote SEPARADO POR PERNA. As duas provas nao
                     se compensam, entao nao podem virar um farol so.
  2 · FILA DE EXCECOES  a tela principal do produto. Nao e painel de status
                     verde: e a lista do que precisa de decisao humana.
  3 · DOSSIE         seletor de lote e versao, diff entre versoes, aprovacao.

Em todas, no topo, o contador de autonomia lido direto da tabela `evento`.

Microcopia - inegociavel (docs/correcoes-spec_1.md secao 06):
  · o sistema marca, ordena e informa; nunca bloqueia, cancela ou barra.
    'bloqueado' aparece so como valor tecnico do semaforo.
  · a lacuna e do documento, nunca da pessoa: "falta o CCIR de Antonio".
  · quem decide e sempre a gestora - os botoes dizem isso.

Escrita no banco: `excecao` (status, resolvido_por, resolvido_em) pelas funcoes
genericas de db.py, porque quem escreve e o ATOR HUMANO pela interface; e
`evento` sempre. Dossie so via dossie.gerar_dossie / dossie.aprovar_dossie.

ARMADILHA DESTA MAQUINA: o Controle de Aplicativo do Windows bloqueia a DLL do
pyarrow (o mesmo motivo pelo qual geo.py existe). Instalar pyarrow quebra o
`import pandas` de TODAS as trilhas. Por isso ele foi desinstalado e este
arquivo NAO usa st.dataframe nem st.table - as tabelas sao montadas em HTML.
Nao reinstale pyarrow.

Uso:
    streamlit run app.py
"""
import inspect
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

import db  # noqa: E402
import dossie  # noqa: E402

# ---------------------------------------------------------------------------
# Vocabulario e rotulos
# ---------------------------------------------------------------------------
# Ordem de exibicao da fila: o que precisa de decisao primeiro fica em cima.
TIPOS_ORDEM = ["bloqueio", "lacuna_sanavel", "nao_sanavel_pelo_produtor",
               "dispensa_documentada"]

ROTULO_TIPO = {
    "bloqueio": "Bloqueio",
    "lacuna_sanavel": "Lacuna sanavel",
    "nao_sanavel_pelo_produtor": "Fora do alcance do produtor",
    "dispensa_documentada": "Dispensa documentada",
}

# Explicacao curta que aparece embaixo do titulo de cada grupo. E aqui que a
# microcopia paga a conta: o estado e do documento, nunca da pessoa.
EXPLICACAO_TIPO = {
    "bloqueio": "O achado desqualifica a parcela enquanto durar. O sistema "
                "marca e refaz os dossies; a decisao sobre o embarque e sua.",
    "lacuna_sanavel": "Falta um documento que o produtor consegue obter. "
                      "E a unica categoria que entra na contagem de lacunas.",
    "nao_sanavel_pelo_produtor": "A pendencia esta no orgao, nao com o "
                                 "produtor - CAR em analise, por exemplo. "
                                 "Registrada para o auditor, sem cobranca.",
    "dispensa_documentada": "A ausencia e a situacao regular na cacauicultura "
                            "familiar. Fica documentada como dispensa, nao "
                            "como falta.",
}

COR_TIPO = {"bloqueio": "#b3261e", "lacuna_sanavel": "#b26a00",
            "nao_sanavel_pelo_produtor": "#5b5bd6",
            "dispensa_documentada": "#2e7d32"}

# Semaforo. 'bloqueado' e valor tecnico do status, nao verbo do produto.
COR_STATUS = {"verde": "#2e7d32", "atencao": "#b26a00",
              "bloqueado": "#b3261e", None: "#6b6b6b"}
ROTULO_STATUS = {"verde": "VERDE", "atencao": "ATENCAO",
                 "bloqueado": "BLOQUEADO"}

# Codigos agregados das sete checagens. As linhas com codigo de regra (R17...)
# sao detalhe da checagem 05 - somar de novo contaria o mesmo achado duas vezes.
CODIGOS_AGREGADOS = ("01", "02", "03", "04", "05", "06", "07")
PIOR = {"conforme": 0, "excecao": 1, "bloqueio": 2}
STATUS_DO_RESULTADO = {"conforme": "verde", "excecao": "atencao",
                       "bloqueio": "bloqueado"}

NOME_PERNA = {"A": "Perna A · desmatamento",
              "B": "Perna B · legalidade"}

CSS = """
<style>
  .contador  { display:flex; gap:14px; flex-wrap:wrap; margin:2px 0 14px 0; }
  .cartao    { flex:1 1 190px; background:#12161c; border:1px solid #2b3138;
               border-radius:12px; padding:14px 18px; }
  .cartao .n { font-size:2.5rem; font-weight:800; line-height:1.05;
               color:#7fd1ae; letter-spacing:-1px; }
  .cartao .r { font-size:.78rem; text-transform:uppercase; color:#9aa4b0;
               letter-spacing:.08em; margin-top:4px; }
  .cartao.humano .n { color:#ffb547; }
  .selo      { display:inline-block; padding:3px 12px; border-radius:999px;
               color:#fff; font-weight:700; font-size:.78rem;
               letter-spacing:.06em; }
  .perna     { font-size:.72rem; color:#9aa4b0; text-transform:uppercase;
               letter-spacing:.08em; margin-bottom:3px; }
  .nota      { color:#9aa4b0; font-size:.84rem; }
  .laudo     { background:#12161c; border-left:3px solid #3b4652;
               padding:10px 14px; border-radius:6px; font-size:.86rem;
               white-space:pre-wrap; }
</style>
"""


def selo(texto: str, cor: str) -> str:
    return '<span class="selo" style="background:%s">%s</span>' % (cor, texto)


# ---------------------------------------------------------------------------
# Compatibilidade com a versao do streamlit instalada
# ---------------------------------------------------------------------------
# Regra desta secao: nunca chamar uma API do streamlit por suposicao. A
# assinatura realmente instalada e consultada por introspecao antes do uso,
# porque foi exatamente uma suposicao errada - st.iframe(srcdoc=...,
# scrolling=...) - que derrubou a visualizacao do dossie na tela 3. Nesta
# versao a assinatura e:
#     st.iframe(src, *, width, height, tab_index)
# ou seja: `srcdoc` e `scrolling` nao existem, e o HTML cru vai em `src`.
def _parametros(func) -> set:
    """Nomes dos parametros aceitos por `func`; vazio se nao introspectavel."""
    try:
        return set(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return set()


def _kwargs_largura_total(func) -> dict:
    """Como pedir "ocupe a largura toda" na versao instalada.

    O streamlit trocou `use_container_width=True` por `width="stretch"` e
    deixou o antigo como depreciado. Resolvido por introspecao, para nao
    depender de numero de versao nem colher aviso de depreciacao na tela.
    """
    p = _parametros(func)
    if "width" in p:
        return {"width": "stretch"}
    if "use_container_width" in p:
        return {"use_container_width": True}
    return {}


def _motor_de_embutir():
    """(funcao, kwargs_extra, nome) para embutir HTML cru dentro de um iframe.

    O `st.iframe` moderno aceita o proprio HTML em `src` e nao tem `scrolling`.
    Nas versoes em que `st.iframe` so aceita URL (tem `scrolling`) ou nem
    existe, o caminho certo e `components.html`, que funciona em qualquer
    versao e por isso fica como reserva. `components.html` ainda funciona
    aqui, mas esta depreciado: com client.showErrorDetails no padrao "full"
    ele imprime uma tarja amarela de depreciacao em cima do dossie.
    """
    p = _parametros(getattr(st, "iframe", None))
    if "src" in p and "scrolling" not in p:
        return st.iframe, {}, "st.iframe"
    return components.html, {"scrolling": True}, "components.html"


def ao_vivo(func, intervalo) -> None:
    """Roda `func` como fragmento que se refaz sozinho a cada `intervalo`.

    Fragmento, e nao `st.rerun()` global, de proposito: so o bloco que le o
    banco volta ao banco, entao o resto da pagina - inclusive o formulario de
    decisao que a gestora estiver preenchendo - nao e refeito junto. Com
    `intervalo` None a atualizacao automatica fica desligada e a funcao roda
    uma vez so, normalmente.
    """
    if intervalo:
        st.fragment(func, run_every=intervalo)()
    else:
        func()


def caminho_do_banco(relativo):
    """Caminho absoluto de um campo de caminho do banco, ou None se vazio.

    `RAIZ / ""` devolve a propria RAIZ - um diretorio que existe -, entao um
    caminho nulo no banco viraria "arquivo presente" e a leitura estouraria
    num erro de permissao. Por isso o vazio vira None e toda checagem daqui
    para a frente e `is_file()`, nunca `exists()`.
    """
    if not relativo:
        return None
    return RAIZ / relativo


def ler_bytes(caminho):
    """(bytes, erro): le o arquivo ou devolve o motivo por que nao deu.

    Quem chama mostra o motivo na tela. Engolir a falha deixava a gestora
    sem botao e sem explicacao.
    """
    try:
        return caminho.read_bytes(), None
    except OSError as erro:
        return None, str(erro)


def embutir_dossie(caminho_html, altura: int = 900) -> dict:
    """Le o HTML do dossie e o embute na pagina.

    Devolve {"modo", "motor", "bytes", "erro"} para que a tela decida a
    mensagem e para que o caminho feliz possa ser exercitado fora do
    streamlit. `modo` e "embutido", "ausente" ou "erro_leitura".
    """
    if caminho_html is None or not caminho_html.is_file():
        return {"modo": "ausente", "motor": None, "bytes": 0, "erro": None}
    try:
        bruto = caminho_html.read_text(encoding="utf-8", errors="replace")
    except OSError as erro:
        # Ultima linha de defesa: o arquivo esta em disco mas a leitura foi
        # negada (regeracao em curso, permissao, unidade de rede). Nao e o
        # caminho normal - por isso vira mensagem na tela, nunca silencio.
        return {"modo": "erro_leitura", "motor": None, "bytes": 0,
                "erro": str(erro)}
    embutir, extra, nome = _motor_de_embutir()
    embutir(bruto, height=altura, **extra)
    return {"modo": "embutido", "motor": nome, "bytes": len(bruto),
            "erro": None}


# ---------------------------------------------------------------------------
# Leitura do banco - so leitura aqui
# ---------------------------------------------------------------------------
def ultimas_checagens_por_talhao() -> dict:
    """talhao_id -> lista de {codigo, perna, resultado, texto} mais recentes."""
    marcadores = ",".join("?" for _ in CODIGOS_AGREGADOS)
    linhas = db.consultar(
        "SELECT c.talhao_id, c.codigo, c.perna, c.resultado, c.texto, "
        "       c.categoria, c.severidade, c.fonte, c.data_execucao "
        "FROM checagem c JOIN (SELECT talhao_id, codigo, MAX(rowid) AS r "
        "  FROM checagem WHERE codigo IN (%s) GROUP BY talhao_id, codigo) u "
        "  ON u.talhao_id = c.talhao_id AND u.codigo = c.codigo "
        " AND u.r = c.rowid" % marcadores, tuple(CODIGOS_AGREGADOS))
    mapa = {}
    for linha in linhas:
        mapa.setdefault(linha["talhao_id"], []).append(linha)
    return mapa


def semaforo_por_perna(lote_id: str, por_talhao: dict) -> dict:
    """Pior resultado do lote em cada perna, separadamente.

    As duas provas nao se compensam: um talhao impecavel na legalidade nao
    apaga uma falha geometrica, e o contrario tambem nao vale. Por isso saem
    duas colunas, nunca uma media.
    """
    piores = {"A": "conforme", "B": "conforme"}
    contagem = {"A": 0, "B": 0}
    for t in db.talhoes_do_lote(lote_id):
        for ch in por_talhao.get(t["id"], []):
            perna = ch.get("perna") or "B"
            if perna not in piores:
                continue
            if PIOR.get(ch["resultado"], 0) > PIOR[piores[perna]]:
                piores[perna] = ch["resultado"]
            if ch["resultado"] != "conforme":
                contagem[perna] += 1
    return {"A": piores["A"], "B": piores["B"], "achados": contagem}


def lotes_da_excecao(exc: dict) -> list:
    """Lotes afetados: campo `lotes_afetados` quando existe, senao pelo talhao."""
    ids = [i.strip() for i in (exc.get("lotes_afetados") or "").split(",")
           if i.strip()]
    lotes = [db.buscar_lote(i) for i in ids]
    lotes = [l for l in lotes if l]
    if not lotes and exc.get("talhao_id"):
        lotes = db.lotes_do_talhao(exc["talhao_id"])
    return lotes


def evidencia_da_excecao(exc: dict) -> list:
    """Laudos das checagens nao-conformes do talhao da excecao."""
    if not exc.get("talhao_id"):
        return []
    marcadores = ",".join("?" for _ in CODIGOS_AGREGADOS)
    return db.consultar(
        "SELECT c.codigo, c.resultado, c.texto, c.fonte, c.data_execucao "
        "FROM checagem c JOIN (SELECT talhao_id, codigo, MAX(rowid) AS r "
        "  FROM checagem WHERE codigo IN (%s) GROUP BY talhao_id, codigo) u "
        "  ON u.talhao_id = c.talhao_id AND u.codigo = c.codigo "
        " AND u.r = c.rowid WHERE c.talhao_id = ? AND c.resultado <> 'conforme'"
        % marcadores, tuple(CODIGOS_AGREGADOS) + (exc["talhao_id"],))


# ---------------------------------------------------------------------------
# Escrita - sempre com ator humano, sempre com evento
# ---------------------------------------------------------------------------
def resolver_excecao(exc: dict, nome: str, decisao: str,
                     excluir_talhao: bool) -> dict:
    """Fecha uma excecao por decisao da gestora e refaz os dossies afetados.

    Escreve em `excecao` pelas funcoes genericas de db.py: a linha e da
    Trilha B, mas quem esta escrevendo aqui e o ator humano pela interface, e
    isso vai registrado em `evento` com nome e horario.

    `excluir_talhao` NAO mexe em `lote_talhao` - esta trilha nao escreve nessa
    tabela. A decisao fica registrada na trilha de auditoria e aplicada na
    consolidacao do embarque, e os dossies sao refeitos na hora.
    """
    quando = db.agora()
    talhao = db.buscar_talhao(exc["talhao_id"]) if exc.get("talhao_id") else None
    nome_talhao = talhao["nome"] if talhao else "sem talhao vinculado"
    lotes = lotes_da_excecao(exc)
    codigos = ", ".join(l["codigo"] for l in lotes) or "nenhum lote"

    db.atualizar("excecao", exc["id"], {
        "status": "resolvida", "resolvido_por": nome, "resolvido_em": quando})

    if excluir_talhao:
        acao, verbo = ("talhao_retirado_do_lote_por_decisao_humana",
                       "determinou retirar o talhao %s dos lotes %s"
                       % (nome_talhao, codigos))
    else:
        acao, verbo = ("excecao_resolvida_por_decisao_humana",
                       "marcou a excecao como resolvida mantendo o talhao %s "
                       "nos lotes %s" % (nome_talhao, codigos))

    db.registrar_evento(
        "humano", acao, "excecao", exc["id"],
        "%s (gestora) %s em %s. Tipo da excecao: %s. Justificativa: %s"
        % (nome, verbo, quando, exc.get("tipo"), decisao or "nao informada"))

    regerados = []
    for lote in lotes:
        try:
            gerado = dossie.gerar_dossie(lote["id"])
            regerados.append("%s v%d" % (lote["codigo"], gerado["versao"]))
            db.registrar_evento(
                "humano", "dossie_regerado_apos_decisao", "lote", lote["id"],
                "Dossie do lote %s refeito na versao %d depois da decisao de "
                "%s sobre a excecao %s."
                % (lote["codigo"], gerado["versao"], nome, exc["id"]))
        except Exception as erro:
            db.registrar_evento(
                "humano", "dossie_regeracao_falhou", "lote", lote["id"],
                "Falha ao refazer o dossie do lote %s apos decisao humana: %s"
                % (lote["codigo"], erro))
            regerados.append("%s (falhou: %s)" % (lote["codigo"], erro))
    return {"regerados": regerados, "lotes": codigos}


# ---------------------------------------------------------------------------
# Contador de autonomia - o numero que o jurado anota
# ---------------------------------------------------------------------------
def contador_autonomia(intervalo=None) -> None:
    """Contador de autonomia, lido direto de `evento`.

    O intervalo vem da barra lateral em vez de ficar fixo no codigo,
    para que a gestora possa parar a atualizacao automatica da pagina
    inteira num clique so.
    """
    ao_vivo(_contador_ao_vivo, intervalo)


def _contador_ao_vivo() -> None:
    c = db.contadores()
    st.markdown(
        '<div class="contador">'
        '<div class="cartao"><div class="n">%s</div>'
        '<div class="r">verificacoes executadas</div></div>'
        '<div class="cartao"><div class="n">%s</div>'
        '<div class="r">documentos processados</div></div>'
        '<div class="cartao"><div class="n">%s</div>'
        '<div class="r">dossies regerados</div></div>'
        '<div class="cartao humano"><div class="n">%s</div>'
        '<div class="r">excecoes para humano</div></div>'
        '</div>'
        % ("{:,}".format(c["verificacoes_executadas"]).replace(",", "."),
           "{:,}".format(c["documentos_processados"]).replace(",", "."),
           "{:,}".format(c["dossies_regerados"]).replace(",", "."),
           "{:,}".format(c["excecoes_para_humano"]).replace(",", ".")),
        unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TELA 1 · LOTES
# ---------------------------------------------------------------------------
def tela_lotes(intervalo=None) -> None:
    st.subheader("1 · Lotes")
    st.markdown(
        '<p class="nota">Um semaforo por perna, lado a lado. As duas provas '
        'nao se compensam: evidencia de legalidade nao apaga falha geometrica, '
        'e nem o contrario. Por isso nunca ha um farol so.</p>',
        unsafe_allow_html=True)
    ao_vivo(_lotes_ao_vivo, intervalo)


def _lotes_ao_vivo() -> None:
    """Corpo da tela 1, relido do banco a cada ciclo do fragmento.

    Criterio de pronto da trilha: o semaforo de um lote muda sozinho na
    tela, sem F5. Como aqui nao ha nenhum campo de entrada, o fragmento
    pode se refazer inteiro sem risco de apagar o que alguem digitava.
    """
    por_talhao = ultimas_checagens_por_talhao()
    lotes = db.listar_lotes()
    if not lotes:
        st.info("Nenhum lote no banco. Rode `python seed.py`.")
        return

    for lote in lotes:
        sem = semaforo_por_perna(lote["id"], por_talhao)
        talhoes = db.talhoes_do_lote(lote["id"])
        dossies = sorted(db.listar_dossies(lote["id"]),
                         key=lambda d: d["versao"], reverse=True)

        cab = st.container(border=True)
        with cab:
            col0, colA, colB, col3 = st.columns([2.4, 1.8, 1.8, 1.6])
            col0.markdown(
                "**%s**  \n<span class='nota'>%s · safra %s · %s kg · %s</span>"
                % (lote["codigo"], lote.get("commodity") or "-",
                   lote.get("safra") or "-",
                   "{:,.0f}".format(lote.get("quantidade_kg") or 0)
                   .replace(",", "."), lote.get("comprador") or "-"),
                unsafe_allow_html=True)
            for coluna, perna in ((colA, "A"), (colB, "B")):
                estado = STATUS_DO_RESULTADO.get(sem[perna], "verde")
                coluna.markdown(
                    "<div class='perna'>%s</div>%s<br>"
                    "<span class='nota'>%d achado(s) nesta perna</span>"
                    % (NOME_PERNA[perna],
                       selo(ROTULO_STATUS.get(estado, estado.upper()),
                            COR_STATUS[estado]), sem["achados"][perna]),
                    unsafe_allow_html=True)
            col3.markdown(
                "<div class='perna'>Status consolidado do lote</div>%s<br>"
                "<span class='nota'>%d talhoes · %d versoes de dossie</span>"
                % (selo(ROTULO_STATUS.get(lote["status"],
                                          str(lote["status"]).upper()),
                        COR_STATUS.get(lote["status"], "#6b6b6b")),
                   len(talhoes), len(dossies)),
                unsafe_allow_html=True)

            with st.expander("Talhoes e dossies de %s" % lote["codigo"]):
                st.markdown("**Talhoes que compoem o lote**")
                for t in talhoes:
                    produtor = db.buscar_produtor(t["produtor_id"]) or {}
                    checagens = por_talhao.get(t["id"], [])
                    pior = "conforme"
                    for ch in checagens:
                        if PIOR.get(ch["resultado"], 0) > PIOR[pior]:
                            pior = ch["resultado"]
                    estado = STATUS_DO_RESULTADO.get(pior, "verde")
                    st.markdown(
                        "- %s **%s** — %s · %.2f ha · %s · CAR %s"
                        % (selo(ROTULO_STATUS[estado], COR_STATUS[estado]),
                           t["nome"], produtor.get("nome") or "-",
                           t.get("area_ha") or 0, t.get("tipo_geom") or "-",
                           t.get("car_numero") or "nao informado"),
                        unsafe_allow_html=True)

                st.markdown("**Historico de versoes do dossie**")
                if not dossies:
                    st.markdown(
                        "<span class='nota'>Ainda nao ha dossie deste lote. "
                        "Ele e gerado pela vigilancia quando o status muda, ou "
                        "na tela 3.</span>", unsafe_allow_html=True)
                for d in dossies:
                    html = caminho_do_banco(d.get("caminho_html"))
                    pdf = caminho_do_banco(d.get("caminho_pdf"))
                    st.markdown(
                        "- **v%d** · %s · gerado em %s · hash `%s`"
                        % (d["versao"], d.get("status") or "-",
                           d.get("gerado_em") or "-",
                           (d.get("hash_sha256") or "")[:16]))
                    st.markdown(
                        "&nbsp;&nbsp;&nbsp;HTML: `%s`%s"
                        % (d.get("caminho_html") or "nao gerado",
                           ("  ·  PDF: `%s`" % d["caminho_pdf"])
                           if d.get("caminho_pdf") else
                           "  ·  PDF nao gerado (o HTML e o entregavel)"))
                    # Nada de link file:/// aqui: a interface e servida
                    # por http e o navegador recusa navegar para
                    # file://. O caminho fica como referencia em texto
                    # (impresso logo acima) e o download de verdade e na
                    # tela 3, que trata de uma versao so - ler os
                    # megabytes de todas as versoes de todos os lotes a
                    # cada ciclo do fragmento seria caro a toa.
                    presentes = [r for r, c in (("HTML", html),
                                                ("PDF", pdf))
                                 if c and c.is_file()]
                    st.markdown(
                        "&nbsp;&nbsp;&nbsp;<span class='nota'>%s · baixe "
                        "o arquivo na tela 3 · Dossie.</span>"
                        % ("em disco: " + " e ".join(presentes)
                           if presentes else "nenhum arquivo em disco"),
                        unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TELA 2 · FILA DE EXCECOES  (a tela principal)
# ---------------------------------------------------------------------------
def cartao_excecao(exc: dict, indice: int) -> None:
    talhao = db.buscar_talhao(exc["talhao_id"]) if exc.get("talhao_id") else None
    produtor = db.buscar_produtor(talhao["produtor_id"]) if talhao else None
    lotes = lotes_da_excecao(exc)
    codigos = ", ".join(l["codigo"] for l in lotes) or "nenhum lote"
    titulo = "%s · %s · lotes: %s" % (
        ROTULO_TIPO.get(exc["tipo"], exc["tipo"]),
        (talhao["nome"] if talhao else "sem talhao"), codigos)

    with st.expander(titulo):
        st.markdown(
            "%s &nbsp; **Talhao** %s &nbsp;·&nbsp; **Produtor** %s "
            "&nbsp;·&nbsp; **Lotes afetados** %s"
            % (selo(ROTULO_TIPO.get(exc["tipo"], exc["tipo"]),
                    COR_TIPO.get(exc["tipo"], "#6b6b6b")),
               talhao["nome"] if talhao else "-",
               produtor["nome"] if produtor else "-", codigos),
            unsafe_allow_html=True)

        st.markdown("**O que foi encontrado**")
        st.markdown("<div class='nota'>%s</div>"
                    % (exc.get("descricao") or "sem descricao"),
                    unsafe_allow_html=True)

        evidencias = evidencia_da_excecao(exc)
        if evidencias:
            with st.expander("Evidencia · %d laudo(s) de checagem"
                             % len(evidencias)):
                for ev in evidencias:
                    st.markdown("**Checagem %s — %s** · fonte: %s · %s"
                                % (ev["codigo"], ev["resultado"],
                                   ev.get("fonte") or "-",
                                   ev.get("data_execucao") or "-"))
                    st.text(ev.get("texto") or "")

        st.divider()
        st.markdown(
            "<span class='nota'>Quem decide e voce. O sistema marcou o talhao, "
            "identificou os lotes que dependem dele e vai refazer os dossies "
            "com a sua decisao registrada.</span>", unsafe_allow_html=True)

        with st.form("form_exc_%s_%d" % (exc["id"], indice)):
            col1, col2 = st.columns([1, 2])
            nome = col1.text_input("Seu nome", key="nome_%s" % exc["id"],
                                   placeholder="quem esta decidindo")
            decisao = col2.text_input(
                "Justificativa (vai para a trilha de auditoria)",
                key="just_%s" % exc["id"],
                placeholder="por que voce esta decidindo assim")
            b1, b2 = st.columns(2)
            largura = _kwargs_largura_total(b1.form_submit_button)
            excluir = b1.form_submit_button(
                "Decidir retirar o talhao do lote", **largura)
            resolver = b2.form_submit_button(
                "Marcar como resolvida, mantendo o talhao", **largura)

        if excluir or resolver:
            if not nome.strip():
                st.error("Informe seu nome: a decisao vai assinada para a "
                         "trilha de auditoria.")
                return
            with st.spinner("Registrando a decisao e refazendo os dossies..."):
                saida = resolver_excecao(exc, nome.strip(), decisao.strip(),
                                         excluir_talhao=bool(excluir))
            if excluir:
                st.success(
                    "Decisao de %s registrada: retirar o talhao dos lotes %s. "
                    "A retirada e aplicada na consolidacao do embarque; aqui "
                    "ela fica assinada e datada."
                    % (nome.strip(), saida["lotes"]))
            else:
                st.success("Excecao marcada como resolvida por %s."
                           % nome.strip())
            st.info("Dossies refeitos: %s"
                    % (", ".join(saida["regerados"]) or "nenhum lote afetado"))
            st.rerun()


def tela_excecoes(intervalo=None) -> None:
    st.subheader("2 · Fila de excecoes")
    ao_vivo(_excecoes_ao_vivo, intervalo)


def _excecoes_ao_vivo() -> None:
    """Corpo da tela 2, relido do banco a cada ciclo do fragmento.

    Fica num fragmento - e nao num rerun global - justamente por causa
    dos formularios de decisao: so este bloco volta ao banco, o resto da
    pagina nao e refeito junto. Ainda assim a atualizacao automatica
    pode ser desligada na barra lateral por quem for escrever uma
    justificativa longa sem pressa.
    """
    abertas = db.listar_excecoes(status="aberta")
    por_tipo = {}
    for e in abertas:
        por_tipo.setdefault(e.get("tipo") or "sem_tipo", []).append(e)

    # A contagem de lacunas do painel soma SO lacuna_sanavel (correcoes secao 03).
    lacunas = len(por_tipo.get("lacuna_sanavel", []))
    st.markdown(
        "### %d lacunas esperando documento\n"
        "<span class='nota'>Contagem de lacunas = so as <b>sanaveis</b>: falta "
        "um papel que o produtor consegue obter. Dispensa documentada e "
        "pendencia de orgao aparecem na fila, mas nao contam como lacuna — "
        "ausencia nem sempre e falta.</span>" % lacunas,
        unsafe_allow_html=True)

    colunas = st.columns(len(TIPOS_ORDEM))
    for coluna, tipo in zip(colunas, TIPOS_ORDEM):
        coluna.markdown(
            "%s<br><span style='font-size:1.6rem;font-weight:700'>%d</span>"
            % (selo(ROTULO_TIPO[tipo], COR_TIPO[tipo]),
               len(por_tipo.get(tipo, []))), unsafe_allow_html=True)

    st.divider()
    col_f1, col_f2 = st.columns([3, 1])
    escolhidos = col_f1.multiselect(
        "Grupos exibidos", TIPOS_ORDEM, default=TIPOS_ORDEM,
        format_func=lambda t: ROTULO_TIPO[t])
    limite = col_f2.number_input("Itens por grupo", 5, 200, 15, step=5)

    if not abertas:
        st.success("Nenhuma excecao aberta. Tudo o que dependia de decisao "
                   "humana ja foi decidido.")
        return

    for tipo in TIPOS_ORDEM:
        if tipo not in escolhidos:
            continue
        itens = por_tipo.get(tipo, [])
        if not itens:
            continue
        st.markdown("#### %s &nbsp; %s"
                    % (ROTULO_TIPO[tipo],
                       selo(str(len(itens)), COR_TIPO[tipo])),
                    unsafe_allow_html=True)
        st.markdown("<span class='nota'>%s</span>" % EXPLICACAO_TIPO[tipo],
                    unsafe_allow_html=True)
        for i, exc in enumerate(itens[:int(limite)]):
            cartao_excecao(exc, i)
        if len(itens) > int(limite):
            st.markdown("<span class='nota'>… e mais %d neste grupo. Aumente "
                        "'itens por grupo' para ver o resto.</span>"
                        % (len(itens) - int(limite)), unsafe_allow_html=True)
        st.divider()


# ---------------------------------------------------------------------------
# TELA 3 · DOSSIE
# ---------------------------------------------------------------------------
def tela_dossie() -> None:
    st.subheader("3 · Dossie")
    lotes = db.listar_lotes()
    if not lotes:
        st.info("Nenhum lote no banco.")
        return

    col1, col2 = st.columns([1, 1])
    codigo = col1.selectbox("Lote", [l["codigo"] for l in lotes])
    lote = next(l for l in lotes if l["codigo"] == codigo)

    dossies = sorted(db.listar_dossies(lote["id"]),
                     key=lambda d: d["versao"], reverse=True)
    if not dossies:
        st.warning("O lote %s ainda nao tem dossie." % codigo)
        if st.button("Gerar a primeira versao agora"):
            gerado = dossie.gerar_dossie(lote["id"])
            st.success("Dossie v%d gerado." % gerado["versao"])
            st.rerun()
        return

    rotulos = ["v%d · %s · %s" % (d["versao"], d.get("status") or "-",
                                  d.get("gerado_em") or "-") for d in dossies]
    escolha = col2.selectbox("Versao", rotulos)
    atual = dossies[rotulos.index(escolha)]

    st.markdown(
        "**Status** %s &nbsp;·&nbsp; **Gerado em** %s &nbsp;·&nbsp; "
        "**Hash** `%s`%s"
        % (atual.get("status") or "-", atual.get("gerado_em") or "-",
           (atual.get("hash_sha256") or "")[:32],
           ("&nbsp;·&nbsp; **Aprovado por** %s" % atual["aprovado_por"])
           if atual.get("aprovado_por") else ""))

    st.markdown("#### O que mudou em relacao a versao anterior")
    st.text(atual.get("diff") or "sem diff registrado")

    caminho_html = caminho_do_banco(atual.get("caminho_html"))
    caminho_pdf = caminho_do_banco(atual.get("caminho_pdf"))
    st.markdown("**Arquivos** — HTML `%s`%s"
                % (atual.get("caminho_html") or "nao gerado",
                   ("  ·  PDF `%s`" % atual["caminho_pdf"])
                   if atual.get("caminho_pdf") else
                   "  ·  PDF nao gerado (o HTML e o entregavel primario)"))
    # Sem link file:///: a interface e servida por http e o navegador
    # bloqueia a navegacao para file://. O caminho continua impresso
    # acima como referencia e o arquivo sai por download de verdade.
    if caminho_html and caminho_html.is_file():
        dados_html, erro_html = ler_bytes(caminho_html)
        if dados_html is None:
            st.warning("O HTML esta em disco mas nao pode ser lido agora "
                       "(%s)." % erro_html)
        else:
            st.download_button("Baixar o HTML", dados_html,
                               file_name=caminho_html.name,
                               mime="text/html",
                               key="baixar_html_%s" % atual["id"])
    if caminho_pdf and caminho_pdf.is_file():
        # O caminho normal e ler e oferecer o botao. Se a leitura
        # falhar, a gestora precisa saber por que - engolir o erro
        # deixava a tela sem botao e sem explicacao nenhuma.
        dados_pdf, erro_pdf = ler_bytes(caminho_pdf)
        if dados_pdf is None:
            st.warning("O PDF esta em disco mas nao pode ser lido agora "
                       "(%s). O HTML e o entregavel primario."
                       % erro_pdf)
        else:
            st.download_button("Baixar o PDF", dados_pdf,
                               file_name=caminho_pdf.name,
                               mime="application/pdf",
                               key="baixar_pdf_%s" % atual["id"])

    st.divider()
    st.markdown("#### Aprovacao")
    st.markdown(
        "<span class='nota'>Aprovar gera uma versao nova, sem marca d'agua, "
        "assinada com seu nome e cargo. A versao anterior continua no "
        "historico: trilha de auditoria nao apaga rascunho.</span>",
        unsafe_allow_html=True)
    with st.form("form_aprovar_%s" % atual["id"]):
        a1, a2 = st.columns(2)
        nome = a1.text_input("Nome de quem aprova")
        cargo = a2.text_input("Cargo")
        aprovar = st.form_submit_button("Aprovar este dossie")
    if aprovar:
        if not nome.strip() or not cargo.strip():
            st.error("Nome e cargo sao obrigatorios: a aprovacao vai assinada.")
        else:
            with st.spinner("Gerando a versao aprovada..."):
                novo = dossie.aprovar_dossie(atual["id"], nome.strip(),
                                             cargo.strip())
            st.success("Dossie do lote %s aprovado na versao v%d."
                       % (codigo, novo["versao"]))
            st.rerun()

    st.divider()
    st.markdown("#### Visualizacao do dossie")
    embutido = embutir_dossie(caminho_html)
    if embutido["modo"] == "embutido":
        st.markdown("<span class='nota'>Dossie embutido acima por "
                    "<code>%s</code> · %s caracteres de HTML.</span>"
                    % (embutido["motor"],
                       "{:,}".format(embutido["bytes"])
                       .replace(",", ".")),
                    unsafe_allow_html=True)
    elif embutido["modo"] == "ausente":
        st.warning("O arquivo HTML do dossie nao esta em disco (%s). "
                   "Gere outra versao para recriar o arquivo."
                   % (atual.get("caminho_html")
                      or "caminho nao registrado"))
    else:
        st.warning("O HTML do dossie existe mas nao pode ser lido agora "
                   "(%s). Use o botao de download acima."
                   % embutido["erro"])


# ---------------------------------------------------------------------------
# Aplicacao
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Evidence Autopilot EUDR",
                       page_icon="🌱", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown("## Evidence Autopilot EUDR")
    st.markdown(
        "<span class='nota'>O sistema marca, ordena e informa. Ele nao "
        "bloqueia, nao cancela e nao barra carga — quem decide e sempre "
        "voce.</span>", unsafe_allow_html=True)
    tela = st.sidebar.radio(
        "Telas", ["2 · Fila de excecoes", "1 · Lotes", "3 · Dossie"],
        index=0)
    st.sidebar.markdown("---")

    # Criterio de pronto desta trilha: um lote muda de status na tela
    # sem ninguem apertar F5. Cada tela le o banco dentro de um
    # fragmento com `run_every`, entao so o bloco de leitura se refaz -
    # o formulario de decisao que estiver preenchido continua no lugar.
    ligado = st.sidebar.toggle(
        "Atualizacao automatica", value=True,
        help="As telas voltam ao banco sozinhas, sem recarregar a pagina.")
    intervalo = st.sidebar.selectbox(
        "A cada", ["5s", "10s", "30s"], index=0) if ligado else None
    st.sidebar.markdown(
        "<span class='nota'>So o bloco que le o banco e refeito, entao o "
        "que voce estiver digitando num formulario de decisao continua no "
        "lugar. Desligue se preferir escrever sem nenhuma interrupcao.</span>",
        unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<span class='nota'>A fila de excecoes e a tela principal: e a lista "
        "do que espera decisao humana, nao um painel de status verde.</span>",
        unsafe_allow_html=True)
    if st.sidebar.button("Atualizar agora"):
        st.rerun()

    contador_autonomia(intervalo)

    if tela.startswith("1"):
        tela_lotes(intervalo)
    elif tela.startswith("3"):
        tela_dossie()
    else:
        tela_excecoes(intervalo)


main()
