# -*- coding: utf-8 -*-
"""db.py - camada unica de acesso ao banco. Trilha 0 (Fundacao).

Regras de ouro do SPEC.md secao 2.4, respeitadas aqui:
  - toda escrita no banco passa por uma funcao deste arquivo;
  - toda funcao publica recebe e devolve dicts simples, nunca objetos;
  - datas sempre ISO 8601 em texto ('2026-08-30T14:22:00');
  - IDs sempre string, gerados com uuid4().hex[:12].

O esquema da secao 2.2 e congelado: nenhum campo foi renomeado, nenhum campo
extra foi acrescentado. Nenhuma trilha altera este arquivo sozinha.

Uso tipico em qualquer trilha:

    import db
    db.criar_esquema()
    pid = db.inserir_produtor({"nome": "...", "cpf": "...", ...})["id"]
    db.registrar_evento("sistema", "documento_processado", "documento", did,
                        "IMG_4471.jpg classificado como car_recibo")
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

RAIZ = Path(__file__).resolve().parent
CAMINHO_BANCO = RAIZ / "dados" / "app.db"

# ---------------------------------------------------------------------------
# Esquema - copia literal do SPEC.md secao 2.2. NAO RENOMEIE CAMPO NENHUM.
# ---------------------------------------------------------------------------
ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtor (
    id TEXT PRIMARY KEY,
    nome TEXT,
    cpf TEXT,
    municipio TEXT,
    uf TEXT,
    cooperativa TEXT,
    slug TEXT
);

CREATE TABLE IF NOT EXISTS talhao (
    id TEXT PRIMARY KEY,
    produtor_id TEXT,
    nome TEXT,
    area_ha REAL,
    geom_wkt TEXT,
    tipo_geom TEXT,          -- 'ponto' | 'poligono'
    car_numero TEXT,
    car_situacao TEXT
);

CREATE TABLE IF NOT EXISTS documento (
    id TEXT PRIMARY KEY,
    produtor_id TEXT,
    talhao_id TEXT,
    arquivo_origem TEXT,
    arquivo_padronizado TEXT,
    tipo TEXT,               -- ver params/cacau.yml
    campos_json TEXT,        -- campos extraidos
    data_emissao TEXT,
    data_validade TEXT,
    hash_sha256 TEXT,
    confianca REAL,          -- 0.0 a 1.0
    status TEXT,             -- 'ok'|'ilegivel'|'vencido'|'divergente'
    versao INTEGER           -- v01, v02... o anterior nunca e apagado
);

CREATE TABLE IF NOT EXISTS lote (
    id TEXT PRIMARY KEY,
    codigo TEXT,
    commodity TEXT,
    safra TEXT,
    quantidade_kg REAL,
    comprador TEXT,
    data_embarque TEXT,
    status TEXT              -- 'verde'|'atencao'|'bloqueado'
);

CREATE TABLE IF NOT EXISTS lote_talhao (
    lote_id TEXT,
    talhao_id TEXT,
    quantidade_kg REAL
);

CREATE TABLE IF NOT EXISTS checagem (
    id TEXT PRIMARY KEY,
    talhao_id TEXT,
    codigo TEXT,             -- codigo da regra: 'R17', 'R39' (antes '01'..'06')
    perna TEXT,              -- 'A' | 'B'
    resultado TEXT,          -- 'conforme'|'excecao'|'bloqueio'
    texto TEXT,
    fonte TEXT,
    data_execucao TEXT,
    evidencia_json TEXT,
    categoria TEXT,          -- 'A' (perna geometrica) ou 'a'..'h'
    severidade TEXT          -- 'B' bloqueia · 'F' flag
);

-- Aptidao: hierarquia de alternativas em 5 camadas, nao checklist.
-- Escrita pela Trilha B, lida pela Trilha C. Ver correcoes-spec_1.md secao 01.
CREATE TABLE IF NOT EXISTS aptidao (
    id TEXT PRIMARY KEY,
    produtor_id TEXT,
    camada INTEGER,          -- 1..5
    satisfeita INTEGER,      -- 0/1
    via_documento_id TEXT,   -- qual documento fechou a camada
    forca TEXT,              -- 'forte' | 'media' | 'fraca'
    avaliado_em TEXT
);

CREATE TABLE IF NOT EXISTS excecao (
    id TEXT PRIMARY KEY,
    tipo TEXT,               -- vocabulario fixo, ver TIPOS_EXCECAO
    talhao_id TEXT,
    documento_id TEXT,
    lotes_afetados TEXT,     -- ids separados por virgula
    descricao TEXT,
    status TEXT,             -- 'aberta'|'resolvida'
    resolvido_por TEXT,
    resolvido_em TEXT
);

CREATE TABLE IF NOT EXISTS dossie (
    id TEXT PRIMARY KEY,
    lote_id TEXT,
    versao INTEGER,
    gerado_em TEXT,
    status TEXT,             -- 'rascunho'|'aprovado'
    aprovado_por TEXT,
    hash_sha256 TEXT,
    caminho_pdf TEXT,
    caminho_html TEXT,
    diff TEXT
);

CREATE TABLE IF NOT EXISTS evento (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    ator TEXT,               -- 'sistema' | 'humano'
    acao TEXT,
    entidade TEXT,
    entidade_id TEXT,
    detalhe TEXT
);

CREATE INDEX IF NOT EXISTS ix_talhao_produtor ON talhao(produtor_id);
CREATE INDEX IF NOT EXISTS ix_documento_produtor ON documento(produtor_id);
CREATE INDEX IF NOT EXISTS ix_checagem_talhao ON checagem(talhao_id);
CREATE INDEX IF NOT EXISTS ix_lote_talhao_lote ON lote_talhao(lote_id);
CREATE INDEX IF NOT EXISTS ix_lote_talhao_talhao ON lote_talhao(talhao_id);
CREATE INDEX IF NOT EXISTS ix_evento_ts ON evento(timestamp);
CREATE INDEX IF NOT EXISTS ix_aptidao_produtor ON aptidao(produtor_id);
"""

# ---------------------------------------------------------------------------
# Migracao incremental - idempotente e NAO-DESTRUTIVA.
# Cada entrada e (tabela, coluna, tipo). ALTER TABLE ADD COLUMN so roda se a
# coluna ainda nao existir. Nenhum dado e apagado, nenhuma tabela e recriada.
# ---------------------------------------------------------------------------
COLUNAS_NOVAS = [
    ("checagem", "categoria", "TEXT"),     # 'A' ou 'a'..'h'
    ("checagem", "severidade", "TEXT"),    # 'B' | 'F'
    ("documento", "versao", "INTEGER"),    # v01, v02...
]

# Vocabulario fixo de excecao.tipo (correcoes-spec_1.md secao 03).
# Apenas `lacuna_sanavel` conta como lacuna no painel.
TIPOS_EXCECAO = (
    "bloqueio",
    "lacuna_sanavel",
    "dispensa_documentada",
    "nao_sanavel_pelo_produtor",
)

# Colunas de cada tabela, na ordem do esquema. Usadas para montar INSERT.
COLUNAS = {
    "produtor": ["id", "nome", "cpf", "municipio", "uf", "cooperativa", "slug"],
    "talhao": ["id", "produtor_id", "nome", "area_ha", "geom_wkt", "tipo_geom",
               "car_numero", "car_situacao"],
    "documento": ["id", "produtor_id", "talhao_id", "arquivo_origem",
                  "arquivo_padronizado", "tipo", "campos_json", "data_emissao",
                  "data_validade", "hash_sha256", "confianca", "status",
                  "versao"],
    "lote": ["id", "codigo", "commodity", "safra", "quantidade_kg",
             "comprador", "data_embarque", "status"],
    "lote_talhao": ["lote_id", "talhao_id", "quantidade_kg"],
    "checagem": ["id", "talhao_id", "codigo", "perna", "resultado", "texto",
                 "fonte", "data_execucao", "evidencia_json", "categoria",
                 "severidade"],
    "aptidao": ["id", "produtor_id", "camada", "satisfeita", "via_documento_id",
                "forca", "avaliado_em"],
    "excecao": ["id", "tipo", "talhao_id", "documento_id", "lotes_afetados",
                "descricao", "status", "resolvido_por", "resolvido_em"],
    "dossie": ["id", "lote_id", "versao", "gerado_em", "status",
               "aprovado_por", "hash_sha256", "caminho_pdf", "caminho_html",
               "diff"],
    "evento": ["id", "timestamp", "ator", "acao", "entidade", "entidade_id",
               "detalhe"],
}

# lote_talhao nao tem chave primaria propria (contrato congelado)
SEM_ID = {"lote_talhao"}


# ---------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------
def novo_id() -> str:
    """ID de 12 caracteres, conforme regra de ouro."""
    return uuid4().hex[:12]


def agora() -> str:
    """Timestamp ISO 8601 em texto, sem microssegundos."""
    return datetime.now().replace(microsecond=0).isoformat()


def conectar() -> sqlite3.Connection:
    """Abre a conexao. row_factory sqlite3.Row para converter em dict."""
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CAMINHO_BANCO, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # varias trilhas leem ao mesmo tempo
    con.execute("PRAGMA foreign_keys=ON")
    return con


def colunas_da_tabela(tabela: str) -> list:
    """Nomes das colunas que a tabela REALMENTE tem, via PRAGMA table_info."""
    with conectar() as con:
        try:
            return [l["name"] for l in
                    con.execute("PRAGMA table_info(%s)" % tabela).fetchall()]
        except sqlite3.Error:
            return []


def migrar_esquema() -> list:
    """Aplica as colunas novas em bancos que ja existem. Idempotente.

    Nao apaga nada e nao recria tabela nenhuma - `evento` e append-only e o
    banco tem dados reais das outras trilhas. Devolve a lista do que aplicou.
    """
    aplicadas = []
    for tabela, coluna, tipo in COLUNAS_NOVAS:
        existentes = colunas_da_tabela(tabela)
        if not existentes or coluna in existentes:
            continue
        with conectar() as con:
            con.execute("ALTER TABLE %s ADD COLUMN %s %s"
                        % (tabela, coluna, tipo))
        aplicadas.append("%s.%s" % (tabela, coluna))
    return aplicadas


def criar_esquema() -> None:
    """Cria as tabelas que faltam e migra as que ja existem. Idempotente."""
    with conectar() as con:
        con.executescript(ESQUEMA)
    migrar_esquema()


def validar_tipo_excecao(tipo) -> None:
    """Rejeita valor fora do vocabulario fixo de `excecao.tipo`.

    None passa: a Trilha B e quem classifica, e ate ela rodar a linha pode
    ficar sem tipo. Valor preenchido, porem, tem que estar no vocabulario.
    """
    if tipo is None:
        return
    if tipo not in TIPOS_EXCECAO:
        raise ValueError(
            "excecao.tipo invalido: %r. Valores aceitos: %s"
            % (tipo, ", ".join(TIPOS_EXCECAO)))


def apagar_banco() -> None:
    """Remove o arquivo do banco. So o seed.py chama, ao recomecar do zero."""
    for sufixo in ("", "-wal", "-shm"):
        alvo = Path(str(CAMINHO_BANCO) + sufixo)
        if alvo.exists():
            alvo.unlink()


def _dict(linha) -> dict:
    """sqlite3.Row -> dict simples."""
    return dict(linha) if linha is not None else None


# ---------------------------------------------------------------------------
# Escrita generica
# ---------------------------------------------------------------------------
def inserir(tabela: str, dados: dict) -> dict:
    """Insere uma linha em `tabela`. Gera `id` e devolve a linha como dict.

    Campos ausentes viram None. Campos que nao existem na tabela sao ignorados
    silenciosamente - isso evita que uma trilha quebre outra ao passar extra.
    """
    colunas = COLUNAS[tabela]
    linha = {c: dados.get(c) for c in colunas}
    if tabela == "excecao":
        validar_tipo_excecao(linha.get("tipo"))
    if tabela not in SEM_ID and not linha.get("id"):
        linha["id"] = novo_id()
    marcadores = ", ".join("?" for _ in colunas)
    sql = "INSERT INTO %s (%s) VALUES (%s)" % (
        tabela, ", ".join(colunas), marcadores)
    with conectar() as con:
        con.execute(sql, [linha[c] for c in colunas])
    return linha


def inserir_muitos(tabela: str, linhas: list) -> int:
    """Insere varias linhas de uma vez. Devolve quantas foram inseridas."""
    colunas = COLUNAS[tabela]
    prontas = []
    for dados in linhas:
        linha = {c: dados.get(c) for c in colunas}
        if tabela == "excecao":
            validar_tipo_excecao(linha.get("tipo"))
        if tabela not in SEM_ID and not linha.get("id"):
            linha["id"] = novo_id()
        prontas.append([linha[c] for c in colunas])
    sql = "INSERT INTO %s (%s) VALUES (%s)" % (
        tabela, ", ".join(colunas), ", ".join("?" for _ in colunas))
    with conectar() as con:
        con.executemany(sql, prontas)
    return len(prontas)


def atualizar(tabela: str, id_registro: str, campos: dict) -> dict:
    """Atualiza campos de uma linha pelo id. Devolve a linha atualizada."""
    validos = {c: v for c, v in campos.items()
               if c in COLUNAS[tabela] and c != "id"}
    if tabela == "excecao" and "tipo" in validos:
        validar_tipo_excecao(validos["tipo"])
    if not validos:
        return buscar(tabela, id_registro)
    sql = "UPDATE %s SET %s WHERE id = ?" % (
        tabela, ", ".join("%s = ?" % c for c in validos))
    with conectar() as con:
        con.execute(sql, list(validos.values()) + [id_registro])
    return buscar(tabela, id_registro)


# ---------------------------------------------------------------------------
# Leitura generica
# ---------------------------------------------------------------------------
def buscar(tabela: str, id_registro: str) -> dict:
    """Devolve uma linha pelo id, como dict, ou None."""
    with conectar() as con:
        cur = con.execute("SELECT * FROM %s WHERE id = ?" % tabela,
                          (id_registro,))
        return _dict(cur.fetchone())


def listar(tabela: str, ordem: str = None, **filtros) -> list:
    """Lista linhas de `tabela` filtrando por igualdade. Devolve list de dicts.

    Exemplo: listar('talhao', produtor_id='ab12cd34ef56')
    """
    sql = "SELECT * FROM %s" % tabela
    valores = []
    if filtros:
        sql += " WHERE " + " AND ".join("%s = ?" % c for c in filtros)
        valores = list(filtros.values())
    if ordem:
        sql += " ORDER BY " + ordem
    with conectar() as con:
        return [dict(l) for l in con.execute(sql, valores).fetchall()]


def consultar(sql: str, parametros: tuple = ()) -> list:
    """Consulta livre, somente leitura. Devolve list de dicts."""
    with conectar() as con:
        return [dict(l) for l in con.execute(sql, parametros).fetchall()]


def contar(tabela: str, **filtros) -> int:
    """Conta linhas de uma tabela, com filtro opcional por igualdade."""
    sql = "SELECT COUNT(*) AS n FROM %s" % tabela
    valores = []
    if filtros:
        sql += " WHERE " + " AND ".join("%s = ?" % c for c in filtros)
        valores = list(filtros.values())
    with conectar() as con:
        return con.execute(sql, valores).fetchone()["n"]


# ---------------------------------------------------------------------------
# Funcoes por tabela - acucar sobre as genericas, para o codigo das outras
# trilhas ficar legivel. Todas recebem e devolvem dicts.
# ---------------------------------------------------------------------------
def inserir_produtor(d: dict) -> dict:
    return inserir("produtor", d)


def inserir_talhao(d: dict) -> dict:
    return inserir("talhao", d)


def inserir_documento(d: dict) -> dict:
    return inserir("documento", d)


def inserir_lote(d: dict) -> dict:
    return inserir("lote", d)


def inserir_lote_talhao(d: dict) -> dict:
    return inserir("lote_talhao", d)


def inserir_checagem(d: dict) -> dict:
    return inserir("checagem", d)


def inserir_excecao(d: dict) -> dict:
    return inserir("excecao", d)


def inserir_dossie(d: dict) -> dict:
    return inserir("dossie", d)


def inserir_aptidao(d: dict) -> dict:
    """Uma linha de aptidao (produtor x camada 1..5). Escrita pela Trilha B."""
    return inserir("aptidao", d)


def buscar_aptidao(id_registro: str) -> dict:
    return buscar("aptidao", id_registro)


def listar_aptidoes(produtor_id: str = None) -> list:
    """Aptidoes de um produtor (ou todas), ordenadas por camada."""
    return listar("aptidao", ordem="camada", **(
        {"produtor_id": produtor_id} if produtor_id else {}))


def aptidao_do_produtor(produtor_id: str) -> dict:
    """Mapa camada -> linha de aptidao. Ultima avaliacao de cada camada vence."""
    mapa = {}
    for linha in consultar(
            "SELECT * FROM aptidao WHERE produtor_id = ? "
            "ORDER BY camada, avaliado_em", (produtor_id,)):
        mapa[linha["camada"]] = linha
    return mapa


def buscar_produtor(id_registro: str) -> dict:
    return buscar("produtor", id_registro)


def buscar_produtor_por_slug(slug: str) -> dict:
    linhas = listar("produtor", slug=slug)
    return linhas[0] if linhas else None


def buscar_talhao(id_registro: str) -> dict:
    return buscar("talhao", id_registro)


def buscar_lote(id_registro: str) -> dict:
    return buscar("lote", id_registro)


def buscar_lote_por_codigo(codigo: str) -> dict:
    linhas = listar("lote", codigo=codigo)
    return linhas[0] if linhas else None


def listar_produtores() -> list:
    return listar("produtor", ordem="nome")


def listar_talhoes(produtor_id: str = None) -> list:
    return listar("talhao", ordem="nome", **(
        {"produtor_id": produtor_id} if produtor_id else {}))


def listar_documentos(produtor_id: str = None) -> list:
    return listar("documento", **(
        {"produtor_id": produtor_id} if produtor_id else {}))


def listar_lotes() -> list:
    return listar("lote", ordem="codigo")


def listar_checagens(talhao_id: str = None) -> list:
    return listar("checagem", ordem="codigo", **(
        {"talhao_id": talhao_id} if talhao_id else {}))


def listar_excecoes(status: str = None) -> list:
    return listar("excecao", **({"status": status} if status else {}))


def listar_dossies(lote_id: str = None) -> list:
    return listar("dossie", ordem="versao", **(
        {"lote_id": lote_id} if lote_id else {}))


def listar_eventos(limite: int = 200) -> list:
    return consultar(
        "SELECT * FROM evento ORDER BY timestamp DESC LIMIT ?", (limite,))


# --- relacionamentos usados por todas as trilhas ---------------------------
def talhoes_do_lote(lote_id: str) -> list:
    """Talhoes que compoem um lote, com a quantidade alocada a cada um."""
    return consultar(
        "SELECT t.*, lt.quantidade_kg AS quantidade_kg_no_lote "
        "FROM lote_talhao lt JOIN talhao t ON t.id = lt.talhao_id "
        "WHERE lt.lote_id = ? ORDER BY t.nome", (lote_id,))


def lotes_do_talhao(talhao_id: str) -> list:
    """Lotes afetados por um talhao. E o que faz um embargo derrubar 3 lotes."""
    return consultar(
        "SELECT l.* FROM lote_talhao lt JOIN lote l ON l.id = lt.lote_id "
        "WHERE lt.talhao_id = ? ORDER BY l.codigo", (talhao_id,))


def produtores_do_lote(lote_id: str) -> list:
    """Produtores distintos que entram num lote."""
    return consultar(
        "SELECT DISTINCT p.* FROM lote_talhao lt "
        "JOIN talhao t ON t.id = lt.talhao_id "
        "JOIN produtor p ON p.id = t.produtor_id "
        "WHERE lt.lote_id = ? ORDER BY p.nome", (lote_id,))


def proxima_versao_dossie(lote_id: str) -> int:
    """Numero da proxima versao do dossie de um lote (comeca em 1)."""
    with conectar() as con:
        cur = con.execute(
            "SELECT COALESCE(MAX(versao), 0) AS v FROM dossie WHERE lote_id = ?",
            (lote_id,))
        return int(cur.fetchone()["v"]) + 1


# ---------------------------------------------------------------------------
# Trilha de auditoria - TODAS as trilhas chamam. Nunca apague linha de evento.
# ---------------------------------------------------------------------------
def registrar_evento(ator: str, acao: str, entidade: str,
                     entidade_id: str = None, detalhe: str = None) -> dict:
    """Grava uma linha na trilha de auditoria.

    ator     : 'sistema' ou 'humano'
    acao     : verbo curto e estavel, ex. 'checagem_executada'
    entidade : nome da tabela envolvida, ex. 'talhao'
    detalhe  : frase em portugues, legivel por auditor
    """
    if ator not in ("sistema", "humano"):
        raise ValueError("ator deve ser 'sistema' ou 'humano', veio %r" % ator)
    return inserir("evento", {
        "timestamp": agora(), "ator": ator, "acao": acao,
        "entidade": entidade, "entidade_id": entidade_id, "detalhe": detalhe,
    })


def contadores_autonomia() -> dict:
    """Os quatro numeros do topo da interface (SPEC.md secao 7).

    Lidos direto da tabela evento - e a prova visual de autonomia.
    """
    def n(acao):
        return consultar(
            "SELECT COUNT(*) AS n FROM evento WHERE acao = ?", (acao,))[0]["n"]
    return {
        "verificacoes_executadas": n("checagem_executada"),
        "documentos_processados": n("documento_processado"),
        "dossies_regerados": n("dossie_gerado"),
        "excecoes_para_humano": contar("excecao", status="aberta"),
    }


def contadores() -> dict:
    """Alias curto de contadores_autonomia(), como pede o contrato v2."""
    return contadores_autonomia()


def resumo() -> dict:
    """Contagem de todas as tabelas. Usado nos testes e no fim do seed."""
    return {t: contar(t) for t in COLUNAS}


if __name__ == "__main__":
    criar_esquema()
    print("esquema criado em %s" % CAMINHO_BANCO)
    for tabela, quantidade in resumo().items():
        print("  %-12s %d" % (tabela, quantidade))
