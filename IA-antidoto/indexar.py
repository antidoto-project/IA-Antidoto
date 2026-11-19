"""
Preparação dos dados do RAG.

Lê os PDFs listados em data/documentos.json, limpa o texto (cabeçalhos, números de
página, hifenização, referências bibliográficas) e corta em trechos de 500 a 800
caracteres com sobreposição. Os trechos vão para runtime/indice.json, que o rag.py usa.

Uso:
  python indexar.py

O resumo da preparação vai para evidencias/indexacao.json. O rag.py roda a indexação
sozinho na primeira busca se o índice ainda não existir.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTOS_FILE = BASE_DIR / "data" / "documentos.json"
DOCS_DIR = BASE_DIR / "data" / "docs"
INDICE_FILE = BASE_DIR / "runtime" / "indice.json"
EVIDENCIA_FILE = BASE_DIR.parent / "evidencias" / "indexacao.json"

TAMANHO_MIN = 500
TAMANHO_MAX = 800
SOBREPOSICAO = 150
TRECHO_MINIMO = 120          # menos que isso é título solto, não entra no índice

MARCADOR_TOPICO = "\t\xa0"   # é assim que o pypdf devolve os marcadores de lista do guia
INICIO_DE_SECAO = re.compile(r"^\d+(?:\.\d+)+\s+[A-ZÀ-Ú]")   # "8.9 Primeiros-socorros"
FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÀ-Ú0-9“\"(•])")


class DocumentoInvalido(ValueError):
    """Entrada de data/documentos.json incompleta ou PDF ausente."""


# ─────────────────────────────────────────────
# Documentos
# ─────────────────────────────────────────────
def carregar_documentos() -> list[dict]:
    base = json.loads(DOCUMENTOS_FILE.read_text(encoding="utf-8"))
    documentos = base.get("documentos") or []
    erros = []
    ids = set()
    for i, doc in enumerate(documentos):
        rotulo = doc.get("id") or f"documentos[{i}]"
        for campo in ("id", "arquivo", "titulo", "link", "licenca", "paginas"):
            if not doc.get(campo):
                erros.append(f"{rotulo}: campo obrigatório ausente ({campo})")
        for intervalo in doc.get("paginas") or []:
            if (not isinstance(intervalo, list) or len(intervalo) != 2
                    or not all(isinstance(n, int) for n in intervalo) or intervalo[0] > intervalo[1]):
                erros.append(f"{rotulo}: intervalo de páginas inválido ({intervalo})")
        if doc.get("id") in ids:
            erros.append(f"{rotulo}: id repetido")
        ids.add(doc.get("id"))
    if not documentos:
        erros.append("documentos: lista vazia")
    if erros:
        raise DocumentoInvalido("; ".join(erros))
    return documentos


def paginas_incluidas(intervalos: list[list[int]]) -> list[int]:
    return [n for inicio, fim in intervalos for n in range(inicio, fim + 1)]


# ─────────────────────────────────────────────
# Limpeza e corte
# ─────────────────────────────────────────────
def limpar_pagina(texto: str, cabecalhos: list[str]) -> tuple[str, bool]:
    """Texto limpo da página e se ela entrou na seção de referências."""
    linhas, referencias = [], False
    for linha in (texto or "").splitlines():
        limpa = linha.strip()
        if limpa.upper().startswith("REFERÊNCIAS"):
            referencias = True
            break
        if not limpa or limpa.isdigit() or limpa in cabecalhos:
            continue
        if linha.startswith(MARCADOR_TOPICO):
            limpa = "• " + linha[len(MARCADOR_TOPICO):].strip()
        linhas.append(limpa)

    texto = "\n".join(linhas)
    # Hifenização: "cobra-\n-coral" é palavra composta (o guia repete o hífen na linha
    # seguinte); "acumula-\ndo" é só quebra de linha e vira "acumulado".
    texto = re.sub(r"(\w)\s?-\n-(\w)", r"\1-\2", texto)
    texto = re.sub(r"(\w)\s?-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"\n(?=• )", " \n", texto)            # tópico começa frase nova
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\.{3,}", " ", texto)                 # pontilhado de sumário
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto, referencias


def _frases(texto: str) -> list[str]:
    partes = []
    for bloco in re.split(r"\s(?=• )", texto):
        partes.extend(p.strip() for p in FIM_DE_FRASE.split(bloco) if p.strip())
    # frase maior que o tamanho máximo é cortada por palavras
    resultado = []
    for frase in partes:
        while len(frase) > TAMANHO_MAX:
            corte = frase.rfind(" ", 0, TAMANHO_MAX)
            corte = corte if corte > 0 else TAMANHO_MAX
            resultado.append(frase[:corte].strip())
            frase = frase[corte:].strip()
        if frase:
            resultado.append(frase)
    return resultado


def cortar_trechos(paginas: list[tuple[int, str]]) -> list[dict]:
    """Corta o texto contínuo das páginas em trechos de 500–800 caracteres com sobreposição.

    O trecho guarda a página onde começa. A sobreposição repete as últimas frases do
    trecho anterior (até SOBREPOSICAO caracteres) para não perder o contexto no corte.
    Cada seção numerada do guia ("8.9 Primeiros-socorros") começa um trecho novo, para o
    assunto da seção não ficar escondido no fim de um trecho sobre outro assunto.
    """
    frases = [(numero, frase) for numero, texto in paginas for frase in _frases(texto)]
    trechos, atual = [], []

    def tamanho(lista):
        return sum(len(f) + 1 for _, f in lista)

    def fechar():
        texto = " ".join(f for _, f in atual).strip()
        if len(texto) >= TRECHO_MINIMO:
            trechos.append({"pagina": atual[0][0], "texto": texto})

    for item in frases:
        if atual and INICIO_DE_SECAO.match(item[1]) and tamanho(atual) >= TRECHO_MINIMO:
            fechar()
            atual = []
        elif atual and tamanho(atual) + len(item[1]) > TAMANHO_MAX and tamanho(atual) >= TAMANHO_MIN:
            fechar()
            sobra = []
            for anterior in reversed(atual):
                if tamanho(sobra) + len(anterior[1]) > SOBREPOSICAO:
                    break
                sobra.insert(0, anterior)
            atual = sobra
        elif atual and tamanho(atual) + len(item[1]) > TAMANHO_MAX:
            fechar()
            atual = []
        atual.append(item)

    if atual:
        resto = " ".join(f for _, f in atual).strip()
        if trechos and len(resto) < TRECHO_MINIMO:
            trechos[-1]["texto"] += " " + resto
        else:
            fechar()

    for ordem, trecho in enumerate(trechos, start=1):
        trecho["ordem"] = ordem
    return trechos


def extrair_documento(doc: dict, docs_dir: Path = DOCS_DIR) -> dict:
    caminho = docs_dir / doc["arquivo"]
    if not caminho.exists():
        raise DocumentoInvalido(f"{doc['id']}: PDF não encontrado em data/docs/{doc['arquivo']}")
    leitor = PdfReader(str(caminho))
    paginas, vazias = [], []
    for numero in paginas_incluidas(doc["paginas"]):
        if numero > len(leitor.pages):
            raise DocumentoInvalido(f"{doc['id']}: página {numero} não existe (PDF tem {len(leitor.pages)})")
        texto, _ = limpar_pagina(leitor.pages[numero - 1].extract_text(), doc.get("cabecalhos", []))
        if texto:
            paginas.append((numero, texto))
        else:
            vazias.append(numero)
    trechos = cortar_trechos(paginas)
    return {
        "documento": doc,
        "trechos": trechos,
        "resumo": {
            "id": doc["id"],
            "titulo": doc["titulo"],
            "paginas_no_pdf": len(leitor.pages),
            "paginas_indexadas": len(paginas),
            "paginas_sem_texto": vazias,
            "caracteres": sum(len(t) for _, t in paginas),
            "trechos": len(trechos),
            "tamanho_trecho": {
                "min": min((len(t["texto"]) for t in trechos), default=0),
                "max": max((len(t["texto"]) for t in trechos), default=0),
                "media": round(sum(len(t["texto"]) for t in trechos) / len(trechos)) if trechos else 0,
            },
        },
    }


# ─────────────────────────────────────────────
# Execução
# ─────────────────────────────────────────────
def indexar(indice_file: Path = INDICE_FILE) -> dict:
    """Extrai e corta todos os documentos e grava o índice. Retorna o resumo."""
    trechos, resumos = [], []
    for doc in carregar_documentos():
        extraido = extrair_documento(doc)
        for t in extraido["trechos"]:
            trechos.append({"id": f"{doc['id']}#{t['ordem']}", "fonte": doc["id"], "titulo": doc["titulo"],
                            "pagina": t["pagina"], "ordem": t["ordem"], "texto": t["texto"]})
        resumo = extraido["resumo"]
        resumo["exemplos"] = [{"pagina": t["pagina"], "texto": t["texto"][:200] + "…"}
                              for t in extraido["trechos"][:: max(1, len(extraido["trechos"]) // 3)][:3]]
        resumos.append(resumo)
    gerado_em = datetime.now().astimezone().isoformat(timespec="seconds")
    indice_file.parent.mkdir(parents=True, exist_ok=True)
    indice_file.write_text(json.dumps({"gerado_em": gerado_em, "trechos": trechos}, ensure_ascii=False),
                           encoding="utf-8")
    return {"gerado_em": gerado_em,
            "parametros": {"tamanho_min": TAMANHO_MIN, "tamanho_max": TAMANHO_MAX, "sobreposicao": SOBREPOSICAO},
            "total_trechos": len(trechos), "documentos": resumos}


def main() -> int:
    try:
        resultado = indexar()
    except DocumentoInvalido as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    EVIDENCIA_FILE.parent.mkdir(exist_ok=True)
    EVIDENCIA_FILE.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for doc in resultado["documentos"]:
        print(f"✅ {doc['titulo']}: {doc['paginas_indexadas']} páginas → {doc['trechos']} trechos")
    print("   Índice em runtime/indice.json · resumo em evidencias/indexacao.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
