"""
Persistência local da IA do Antídoto (SQLite).

Guarda as triagens do SOS e as conversas do chat. O arquivo fica em
runtime/antidoto.db (ou no caminho definido em ANTIDOTO_DB) e é criado
automaticamente na primeira execução.

Nenhuma tabela guarda nome, CPF, telefone ou localização: o chat mascara esses
dados antes de gravar (ver assistente.mascarar_dados_pessoais).
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ESQUEMA = """
CREATE TABLE IF NOT EXISTS triagens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id  TEXT NOT NULL,
    grupo      TEXT NOT NULL,
    urgencia   TEXT NOT NULL,
    soro       TEXT,
    fonte      TEXT NOT NULL,
    resultado  TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mensagens (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id TEXT NOT NULL,
    papel     TEXT NOT NULL CHECK (papel IN ('pessoa', 'antidoto')),
    conteudo  TEXT NOT NULL,
    fonte     TEXT,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_triagens_sess  ON triagens (sessao_id, id);
CREATE INDEX IF NOT EXISTS idx_mensagens_sess ON mensagens (sessao_id, id);
"""


def caminho_db() -> Path:
    return Path(os.getenv("ANTIDOTO_DB", str(BASE_DIR / "runtime" / "antidoto.db")))


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@contextmanager
def conexao():
    caminho = caminho_db()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(ESQUEMA)
        yield con
        con.commit()
    finally:
        con.close()


# ── Triagens ────────────────────────────────────────────────────────────────
def salvar_triagem(sessao_id: str, resultado: dict) -> int:
    with conexao() as con:
        cur = con.execute(
            "INSERT INTO triagens (sessao_id, grupo, urgencia, soro, fonte, resultado, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sessao_id, resultado["grupo"], resultado["urgencia"], resultado["soro"],
             resultado["fonte"], json.dumps(resultado, ensure_ascii=False), agora()),
        )
        return cur.lastrowid


def listar_triagens(limite: int = 20) -> list[dict]:
    with conexao() as con:
        linhas = con.execute("SELECT * FROM triagens ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [{**dict(l), "resultado": json.loads(l["resultado"])} for l in linhas]


# ── Conversas ───────────────────────────────────────────────────────────────
def salvar_mensagem(sessao_id: str, papel: str, conteudo: str, fonte: str | None = None) -> None:
    with conexao() as con:
        con.execute(
            "INSERT INTO mensagens (sessao_id, papel, conteudo, fonte, criado_em) VALUES (?, ?, ?, ?, ?)",
            (sessao_id, papel, conteudo, fonte, agora()),
        )


def historico_sessao(sessao_id: str, limite: int = 6) -> list[dict]:
    """Últimas mensagens da sessão, da mais antiga para a mais nova."""
    with conexao() as con:
        linhas = con.execute(
            "SELECT papel, conteudo FROM mensagens WHERE sessao_id = ? ORDER BY id DESC LIMIT ?",
            (sessao_id, limite),
        ).fetchall()
    return [dict(l) for l in reversed(linhas)]
