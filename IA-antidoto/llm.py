"""Cliente do Ollama (LLM local). Sem custo de API, sem chave e sem dados saindo da máquina."""
import os

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Respostas curtas e estáveis: temperatura baixa e limite de tokens (mais rápido na CPU).
OPCOES = {"temperature": 0.2, "num_predict": 350}


def chamar_llama(prompt: str, timeout: int = 120) -> str | None:
    """Retorna o texto gerado ou None se o Ollama estiver indisponível."""
    try:
        resposta = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False, "options": OPCOES},
            timeout=timeout,
        )
        resposta.raise_for_status()
        texto = resposta.json().get("response", "").strip()
        return texto or None
    except (requests.RequestException, ValueError):
        return None


def status_ollama() -> dict:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        modelos = [m["name"] for m in r.json().get("models", [])]
        return {"ollama": "conectado", "modelo": MODEL, "modelo_baixado": MODEL in modelos,
                "modelos_disponiveis": modelos}
    except (requests.RequestException, ValueError, KeyError):
        return {"ollama": "desconectado", "modelo": MODEL, "modelo_baixado": False, "modelos_disponiveis": []}
