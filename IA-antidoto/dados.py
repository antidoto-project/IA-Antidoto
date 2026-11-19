"""
Camada de dados do Antídoto IA.

Carrega e valida as bases estruturadas que as regras usam:
  data/soros.json           grupos de animal e soro indicado para cada um
  data/casos-triagem.json   casos de urgência compartilhados com a API .NET

Uma base inválida é rejeitada inteira, com a lista de problemas encontrados.
Nenhum dado é inventado: grupo sem soro (DESCONHECIDO) fica sem soro.
"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOROS_FILE = Path(os.getenv("ANTIDOTO_SOROS_FILE", str(BASE_DIR / "data" / "soros.json")))
CASOS_FILE = Path(os.getenv("ANTIDOTO_CASOS_FILE", str(BASE_DIR / "data" / "casos-triagem.json")))

URGENCIAS_VALIDAS = {"BAIXA", "MEDIA", "ALTA", "CRITICA"}
TIPOS_VALIDOS = {"serpente", "escorpiao", "aranha", "lagarta", "desconhecido"}


class DadosInvalidos(ValueError):
    """Erro de validação de uma base, com a lista de problemas encontrados."""

    def __init__(self, erros):
        super().__init__("; ".join(erros))
        self.erros = erros


def _ler_json(caminho: Path):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DadosInvalidos([f"arquivo não encontrado: {caminho.name}"])
    except json.JSONDecodeError as e:
        raise DadosInvalidos([f"{caminho.name}: JSON inválido na linha {e.lineno}"])


def _ids_repetidos(itens: list, nome: str, erros: list) -> None:
    vistos = set()
    for item in itens:
        id_ = item.get("id") if isinstance(item, dict) else None
        if id_ in vistos:
            erros.append(f"{nome}: id repetido ({id_})")
        vistos.add(id_)


# ─────────────────────────────────────────────
# soros.json
# ─────────────────────────────────────────────
def validar_soros(base: dict) -> list[str]:
    """Retorna a lista de erros da base de soros (vazia quando está válida)."""
    erros = []
    soros = base.get("soros") if isinstance(base, dict) else None
    grupos = base.get("grupos") if isinstance(base, dict) else None
    if not isinstance(soros, list) or not soros:
        return ["soros: lista ausente ou vazia"]
    if not isinstance(grupos, list) or not grupos:
        return ["grupos: lista ausente ou vazia"]

    for i, soro in enumerate(soros):
        for campo in ("id", "nome"):
            if not isinstance(soro, dict) or not soro.get(campo):
                erros.append(f"soros[{i}]: campo obrigatório ausente ({campo})")
    _ids_repetidos(soros, "soros", erros)
    ids_soros = {s.get("id") for s in soros if isinstance(s, dict)}

    for i, grupo in enumerate(grupos):
        if not isinstance(grupo, dict):
            erros.append(f"grupos[{i}]: registro inválido")
            continue
        rotulo = grupo.get("id") or f"grupos[{i}]"
        for campo in ("id", "nome", "tipo"):
            if not grupo.get(campo):
                erros.append(f"{rotulo}: campo obrigatório ausente ({campo})")
        if "soro" not in grupo:
            erros.append(f"{rotulo}: campo obrigatório ausente (soro)")
        if grupo.get("id") and grupo["id"] != grupo["id"].upper():
            erros.append(f"{rotulo}: id deve estar em maiúsculas")
        if grupo.get("tipo") and grupo["tipo"] not in TIPOS_VALIDOS:
            erros.append(f"{rotulo}: tipo inválido ({grupo['tipo']})")
        soro = grupo.get("soro")
        if soro is not None and soro not in ids_soros:
            erros.append(f"{rotulo}: soro inexistente ({soro})")
        if soro is None and grupo.get("tipo") != "desconhecido":
            erros.append(f"{rotulo}: só o grupo desconhecido pode ficar sem soro")
    _ids_repetidos(grupos, "grupos", erros)
    return erros


def carregar_soros() -> dict:
    base = _ler_json(SOROS_FILE)
    erros = validar_soros(base)
    if erros:
        raise DadosInvalidos(erros)
    return base


def grupos_validos(soros: dict | None = None) -> set[str]:
    soros = soros or carregar_soros()
    return {g["id"] for g in soros["grupos"]}


# ─────────────────────────────────────────────
# casos-triagem.json
# ─────────────────────────────────────────────
def validar_casos(base: dict, soros: dict) -> list[str]:
    """Retorna a lista de erros dos casos de triagem (vazia quando estão válidos)."""
    casos = base.get("casos") if isinstance(base, dict) else None
    if not isinstance(casos, list) or not casos:
        return ["casos: lista ausente ou vazia"]

    erros = []
    grupos = {g["id"] for g in soros["grupos"]}
    ids_soros = {s["id"] for s in soros["soros"]}
    for i, caso in enumerate(casos):
        if not isinstance(caso, dict):
            erros.append(f"casos[{i}]: registro inválido")
            continue
        rotulo = caso.get("id") or f"casos[{i}]"
        entrada, esperado = caso.get("entrada"), caso.get("esperado")
        if not caso.get("id"):
            erros.append(f"{rotulo}: campo obrigatório ausente (id)")
        if not isinstance(entrada, dict) or not isinstance(esperado, dict):
            erros.append(f"{rotulo}: entrada e esperado são obrigatórios")
            continue
        if str(entrada.get("grupoAnimal", "")).upper() not in grupos:
            erros.append(f"{rotulo}: grupo inválido ({entrada.get('grupoAnimal')})")
        sintomas = entrada.get("sintomas")
        if not isinstance(sintomas, list) or not all(isinstance(s, str) for s in sintomas):
            erros.append(f"{rotulo}: sintomas deve ser uma lista de textos")
        if esperado.get("urgencia") not in URGENCIAS_VALIDAS:
            erros.append(f"{rotulo}: urgência inválida ({esperado.get('urgencia')})")
        if "soro" not in esperado:
            erros.append(f"{rotulo}: soro esperado ausente (use null para sem soro)")
        elif esperado["soro"] is not None and esperado["soro"] not in ids_soros:
            erros.append(f"{rotulo}: soro inexistente ({esperado['soro']})")
    _ids_repetidos(casos, "casos", erros)
    return erros


def carregar_casos(soros: dict | None = None) -> list[dict]:
    soros = soros or carregar_soros()
    base = _ler_json(CASOS_FILE)
    erros = validar_casos(base, soros)
    if erros:
        raise DadosInvalidos(erros)
    return base["casos"]


def resumo() -> dict:
    """Status das bases para o /health. Nunca lança exceção."""
    try:
        soros = carregar_soros()
        casos = carregar_casos(soros)
        return {"bases": "ok", "grupos": len(soros["grupos"]), "soros": len(soros["soros"]),
                "casos_triagem": len(casos)}
    except DadosInvalidos as e:
        return {"bases": "inválidas", "erros": e.erros}
