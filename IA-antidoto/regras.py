"""
Motor de regras do Antídoto IA: decide urgência e soro.

É o mesmo critério do RegrasTriagem.cs da API .NET, testado pelos mesmos casos
de data/casos-triagem.json. O LLM nunca altera o que sai daqui: ele só explica.
"""
import re
import unicodedata

import dados

URGENCIAS = ("BAIXA", "MEDIA", "ALTA", "CRITICA")

# Mesma separação do switch do RegrasTriagem.cs
GRUPOS_URGENCIA_ALTA = {"JARARACA", "CASCAVEL", "SURUCUCU", "CORAL", "DESCONHECIDO"}
GRUPOS_URGENCIA_MEDIA = {"ARMADEIRA", "ARANHA_MARROM", "LAGARTA", "ESCORPIAO"}

# Mesma lista do Catalogo.SinaisGraves da API .NET: sempre tornam o caso crítico
SINAIS_GRAVES = (
    "FALTA_DE_AR", "VISAO_DUPLA", "PALPEBRA_CAIDA", "URINA_ESCURA",
    "SANGRAMENTO", "DESMAIO", "VOMITOS",
)

# Como cada sinal grave aparece em texto livre (chat). Comparação sem acento e por palavras:
# a expressão casa quando todas as palavras dela aparecem na frase ("a pálpebra está caída").
EXPRESSOES_SINAIS_GRAVES = {
    "FALTA_DE_AR": ("falta de ar", "dificuldade para respirar", "dificuldade de respirar",
                    "nao consegue respirar", "nao consigo respirar", "sem ar"),
    "VISAO_DUPLA": ("visao dupla", "visao turva", "vista embacada", "enxergando dobrado"),
    "PALPEBRA_CAIDA": ("palpebra caida", "olho caido", "palpebras caidas"),
    "URINA_ESCURA": ("urina escura", "xixi escuro", "urina vermelha", "urina com sangue"),
    "SANGRAMENTO": ("sangramento", "sangrando", "sangue na gengiva", "sangrou"),
    "DESMAIO": ("desmaio", "desmaiou", "desmaiando", "desacordado", "inconsciente"),
    "VOMITOS": ("vomito", "vomitos", "vomitando", "vomitou"),
}

ORIENTACAO_BASE = (
    "Lave o local com água e sabão, mantenha a pessoa calma e deitada. "
    "Não faça torniquete, não corte, não chupe o local e não passe nada na picada. "
    "Vá agora para a unidade indicada."
)
ORIENTACAO_CRITICA = "Ligue 192 (SAMU) agora. " + ORIENTACAO_BASE


class GrupoInvalido(ValueError):
    """Grupo de animal fora da lista de data/soros.json."""


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )


def normalizar_grupo(grupo: str, soros: dict | None = None) -> str:
    soros = soros or dados.carregar_soros()
    codigo = (grupo or "").strip().upper()
    if codigo not in dados.grupos_validos(soros):
        validos = ", ".join(sorted(dados.grupos_validos(soros)))
        raise GrupoInvalido(f"Grupo de animal inválido: {grupo!r}. Aceitos: {validos}")
    return codigo


def soro_do_grupo(grupo: str, soros: dict | None = None) -> str | None:
    """Soro indicado para o grupo. DESCONHECIDO não tem soro: a unidade decide."""
    soros = soros or dados.carregar_soros()
    codigo = normalizar_grupo(grupo, soros)
    return next(g["soro"] for g in soros["grupos"] if g["id"] == codigo)


def sinais_graves(sintomas: list[str] | None) -> list[str]:
    """Códigos de sinal grave presentes na lista de sintomas (sem diferenciar maiúsculas)."""
    informados = {(s or "").strip().upper() for s in (sintomas or [])}
    return [sinal for sinal in SINAIS_GRAVES if sinal in informados]


def sinal_grave_no_texto(texto: str | None) -> list[str]:
    """Sinais graves citados em texto livre (usado no chat para pular o LLM)."""
    palavras = set(re.findall(r"[a-z]+", _sem_acento(texto or "")))
    return [
        sinal for sinal, expressoes in EXPRESSOES_SINAIS_GRAVES.items()
        if any(set(expressao.split()) <= palavras for expressao in expressoes)
    ]


def classificar_urgencia(grupo: str, sintomas: list[str] | None, soros: dict | None = None) -> str:
    codigo = normalizar_grupo(grupo, soros)
    if sinais_graves(sintomas):
        return "CRITICA"
    if codigo in GRUPOS_URGENCIA_MEDIA:
        return "MEDIA"
    return "ALTA"  # GRUPOS_URGENCIA_ALTA e qualquer caso não previsto ficam do lado seguro


def avaliar(grupo: str, sintomas: list[str] | None = None, soros: dict | None = None) -> dict:
    """Decisão completa das regras, no formato do ResultadoTriagem da API .NET + detalhes."""
    soros = soros or dados.carregar_soros()
    urgencia = classificar_urgencia(grupo, sintomas, soros)
    return {
        "urgencia": urgencia,
        "soro": soro_do_grupo(grupo, soros),
        "orientacao": ORIENTACAO_CRITICA if urgencia == "CRITICA" else ORIENTACAO_BASE,
        "grupo": normalizar_grupo(grupo, soros),
        "sinais_graves": sinais_graves(sintomas),
    }
