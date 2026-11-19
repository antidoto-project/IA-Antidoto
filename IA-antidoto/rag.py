"""
RAG básico do Antídoto: recuperação de trechos do guia oficial por BM25.

buscar(pergunta) devolve os k trechos do Guia de Animais Peçonhentos do Brasil
(Ministério da Saúde) mais relevantes para a pergunta, numerados [1]..[k] com a
página, para o Llama responder só com eles e citar a fonte.

Etapas:
  1. Filtro de tema: a pergunta precisa citar algo do assunto (picada, veneno, soro,
     cobra, escorpião, aranha…). Pergunta fora do tema volta sem trecho.
  2. BM25: pontua cada trecho pelas palavras da pergunta (sem acento, sem palavras
     vazias, singular = plural), dando mais peso às palavras raras no guia.
  3. Relevância mínima: o trecho precisa cobrir uma parte mínima do peso da pergunta.

Por que BM25 e não embeddings: testamos o nomic-embed-text (Ollama) e ele deu nota
maior para "jogo do Corinthians" (0,67) do que para "posso fazer torniquete?" (0,62),
sem trazer o trecho de primeiros socorros. Com 349 trechos em português técnico, o BM25
acerta os termos exatos do guia, roda sem modelo extra e é explicável. Ver README.

Uso no terminal:
  python rag.py "posso fazer torniquete?"
"""
import json
import math
import re
import sys
import unicodedata
from collections import Counter

import indexar

K_PADRAO = 4
BM25_K1 = 1.5
BM25_B = 0.75
COBERTURA_MINIMA = 0.15   # fração do peso (IDF) da pergunta que o trecho precisa ter
TAMANHO_MAX_PERGUNTA = 1000

STOPWORDS = set("""
a o as os um uma uns umas de da do das dos em na no nas nos por para pra com sem e ou que se
ao aos à às é foi ser ter tem como mais menos muito muita meu minha seu sua isso isto esse essa
este esta ele ela eles elas eu voce voces nao sim ja quando onde qual quais quem porque
pelo pela pelos pelas sobre entre ate depois antes tambem so mesmo fazer faz devo deve pode posso
for fui foram estou estava tava ainda agora aqui ali dar dei deu tive teve logo
""".split())

# Início de palavra (sem acento) que indica o assunto do Antídoto.
TERMOS_DO_TEMA = (
    "picad", "picou", "pique", "mordid", "mordeu", "mordedur", "ferroad", "ferrao", "veneno", "venenos",
    "peconh", "soro", "antiveneno", "antiofid", "ofidi", "acident", "socorr", "torniquet", "hospital",
    "atendimento", "sintoma", "inchac", "dor", "queimad", "bicho", "animal", "animai",
    "cobra", "serpent", "jararac", "cascavel", "chocalho", "coral", "corai", "surucucu",
    "escorpi", "aranha", "armadeir", "marrom", "viuva", "caranguejeir", "lagart", "taturan", "lonomi",
    "abelha", "vespa", "marimbond", "formiga", "lacraia", "centopeia", "agua", "caravel",
    "peixe", "arraia", "bagre", "mandi", "baiacu", "sapo", "toxin", "loreal", "fosset",
)

_cache = {"trechos": None, "idf": None, "media": None}


class PerguntaInvalida(ValueError):
    """Pergunta vazia ou longa demais."""


def _tokens(texto: str) -> list[str]:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower())
                         if unicodedata.category(c) != "Mn")
    return [p for p in re.findall(r"[a-z0-9]+", sem_acento) if len(p) > 2 and p not in STOPWORDS]


def palavras(texto: str) -> list[str]:
    return [_raiz(p) for p in _tokens(texto)]


def _raiz(palavra: str) -> str:
    """Radical simples: tira plural e vogal final, para "picada", "picado" e "picadas"
    contarem como a mesma palavra ("picad")."""
    if len(palavra) > 4 and palavra.endswith("s"):
        palavra = palavra[:-1]
    if len(palavra) > 4 and palavra[-1] in "aeo":
        palavra = palavra[:-1]
    return palavra


def fala_do_tema(pergunta: str) -> bool:
    return any(t.startswith(raiz) for t in _tokens(pergunta) for raiz in TERMOS_DO_TEMA)


def carregar(indice_file=None) -> int:
    """Lê o índice (gera se não existir) e prepara o BM25. Retorna quantos trechos carregou."""
    arquivo = indice_file or indexar.INDICE_FILE
    if not arquivo.exists():
        indexar.indexar(arquivo)
    trechos = json.loads(arquivo.read_text(encoding="utf-8"))["trechos"]
    for t in trechos:
        t["termos"] = Counter(palavras(t["texto"]))
        t["tamanho"] = sum(t["termos"].values())
    total = len(trechos) or 1
    com_termo = Counter(p for t in trechos for p in t["termos"])
    _cache["idf"] = {p: math.log(1 + (total - n + 0.5) / (n + 0.5)) for p, n in com_termo.items()}
    _cache["media"] = sum(t["tamanho"] for t in trechos) / total
    _cache["trechos"] = trechos
    return len(trechos)


def _trechos():
    if _cache["trechos"] is None:
        carregar()
    return _cache["trechos"]


def _bm25(termos: set, trecho: dict) -> float:
    idf, media, nota = _cache["idf"], _cache["media"] or 1, 0.0
    for p in termos:
        f = trecho["termos"].get(p, 0)
        if f:
            nota += idf[p] * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * trecho["tamanho"] / media))
    return nota


def _cobertura(termos: set, trecho: dict) -> float:
    idf = _cache["idf"]
    total = sum(idf.get(p, 0) for p in termos)
    return sum(idf.get(p, 0) for p in termos if p in trecho["termos"]) / total if total else 0.0


def buscar(pergunta: str, k: int = K_PADRAO) -> dict:
    """status: "ok" | "fora_do_tema" | "sem_trecho_relevante"."""
    pergunta = (pergunta or "").strip()
    if not pergunta:
        raise PerguntaInvalida("A pergunta está vazia.")
    if len(pergunta) > TAMANHO_MAX_PERGUNTA:
        raise PerguntaInvalida(f"A pergunta passa de {TAMANHO_MAX_PERGUNTA} caracteres.")
    if not fala_do_tema(pergunta):
        return {"status": "fora_do_tema", "trechos": []}

    trechos = _trechos()
    termos = set(palavras(pergunta))
    notas = [(_bm25(termos, t), _cobertura(termos, t), t) for t in trechos]
    notas.sort(key=lambda x: x[0], reverse=True)
    escolhidos = [(n, c, t) for n, c, t in notas[:k] if n > 0 and c >= COBERTURA_MINIMA]
    return {
        "status": "ok" if escolhidos else "sem_trecho_relevante",
        "trechos": [{"n": i, "id": t["id"], "titulo": t["titulo"], "pagina": t["pagina"],
                     "texto": t["texto"], "nota": round(n, 3), "cobertura": round(c, 3)}
                    for i, (n, c, t) in enumerate(escolhidos, start=1)],
    }


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print('Uso: python rag.py "sua pergunta"', file=sys.stderr)
        return 1
    try:
        resultado = buscar(" ".join(argv))
    except PerguntaInvalida as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    print(f"status = {resultado['status']}")
    for t in resultado["trechos"]:
        print(f"\n[{t['n']}] {t['titulo']}, p. {t['pagina']} · BM25 {t['nota']} · cobertura {t['cobertura']}")
        print(f"    {t['texto'][:300]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
