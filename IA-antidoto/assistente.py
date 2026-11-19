"""
Antídoto Assistente — lógica da IA usada pelo chat do terminal (chat.py) e pela
avaliação (avaliar.py).

SOS (triar):
1. As regras (regras.py) decidem urgência e soro. O LLM nunca altera essa decisão.
2. Sinal grave → resposta fixa "Ligue 192", sem LLM (protocolo).
3. O RAG (rag.py) busca no guia oficial os trechos de primeiros socorros do animal.
4. O Llama explica em linguagem simples usando só esses trechos e citando [n].
5. A resposta do Llama é validada; se falhar ou o Ollama estiver fora, a orientação
   sai com os trechos do guia sem reescrita (fallback). Ninguém fica sem resposta.

Dúvida (responder): mesmo fluxo, a partir de uma pergunta em texto livre.
"""
import re
import unicodedata

import dados
import rag
import regras

AVISO = "Orientação de primeiros socorros baseada no guia do Ministério da Saúde. Não substitui atendimento médico."

SINTOMAS = {
    "DOR_LOCAL": "dor no local", "INCHACO": "inchaço", "VERMELHIDAO": "vermelhidão",
    "FALTA_DE_AR": "falta de ar", "VISAO_DUPLA": "visão dupla ou turva",
    "PALPEBRA_CAIDA": "pálpebra caída", "URINA_ESCURA": "urina escura",
    "SANGRAMENTO": "sangramento", "DESMAIO": "desmaio", "VOMITOS": "vômitos",
}

MSG_SINAL_GRAVE = ("Isso é um sinal de gravidade. Ligue 192 (SAMU) agora e leve a pessoa à unidade de "
                   "saúde mais próxima. Não faça torniquete, não corte, não chupe o local e não passe "
                   "nada na picada.")
MSG_FORA_DO_TEMA = ("Eu só respondo sobre acidentes com animais peçonhentos (serpentes, escorpiões, "
                    "aranhas, lagartas, abelhas…). Em caso de acidente, ligue 192.")
MSG_SEM_FONTE = ("Não encontrei isso no guia oficial do Ministério da Saúde. Em caso de acidente com "
                 "animal peçonhento, procure atendimento médico imediatamente ou ligue 192 (SAMU).")

REGRAS_DE_ESCRITA = """Regras obrigatórias:
- Use SOMENTE as informações dos trechos abaixo. Não invente nada.
- TODA frase termina com o número do trecho de onde ela saiu, entre colchetes. Exemplo:
  "Lave o local com água e sabão [1]. Não amarre o braço [2]."
- Nunca diga que a pessoa pode esperar, ficar em casa ou que não precisa de atendimento.
- Nunca indique remédio, dose, chá, pomada ou receita caseira.
- Português do Brasil, frases curtas, linguagem simples, para alguém assustado.
- No máximo 5 frases. Sem títulos e sem listas."""

# Frases que contrariam "a IA nunca dispensa atendimento". Comparação sem acento.
# Ordens como "corte o local" ficam de fora: no guia elas aparecem negadas ("não corte").
FRASES_PROIBIDAS = (
    "nao precisa ir", "nao precisa procurar", "nao precisa de atendimento", "nao precisa de hospital",
    "nao e necessario procurar", "nao e necessario ir", "nao e perigoso", "nao e peconhento",
    "nao e venenoso", "pode esperar", "pode ficar em casa", "nao se preocupe", "nao ha risco", "sem risco",
)
TAMANHO_MAX_RESPOSTA = 1500

# O trecho de primeiros socorros do guia fala de todos os animais juntos. Na triagem, a
# resposta não pode trazer instrução que o guia dá só para outro tipo de animal.
# termo (sem acento) → tipo de animal ao qual ele pertence (ver "tipo" em soros.json)
TERMOS_DE_OUTRO_ANIMAL = {
    "tentacul": "cnidario", "agua-viva": "cnidario", "aguas-vivas": "cnidario", "caravela": "cnidario",
    "vinagre": "cnidario", "agua do mar": "cnidario",
    "ofidic": "serpente", "agua potavel": "serpente",
    "fria ou gelada": "lagarta", "agua gelada": "lagarta",
    "ferrao de abelha": "abelha", "ferrao das abelhas": "abelha",
}

DADOS_PESSOAIS = [
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),                    # CPF
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),                              # e-mail
    re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"),      # telefone
]


# ─────────────────────────────────────────────
# Apoio
# ─────────────────────────────────────────────
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def mascarar_dados_pessoais(texto: str) -> str:
    """CPF, telefone e e-mail viram [removido] antes de ir para o LLM ou para o banco."""
    for padrao in DADOS_PESSOAIS:
        texto = padrao.sub("[removido]", texto)
    return texto


def descrever_sintomas(sintomas) -> str:
    nomes = [SINTOMAS.get((s or "").upper(), (s or "").lower().replace("_", " ")) for s in (sintomas or []) if s]
    return ", ".join(nomes) if nomes else "nenhum sintoma informado"


def validar_resposta(texto: str | None, total_trechos: int, tipo_animal: str | None = None) -> tuple[bool, str]:
    """(válida, motivo). O texto do LLM só é usado se citar os trechos, não dispensar
    atendimento e, na triagem, não trazer instrução de outro tipo de animal."""
    if not texto or not texto.strip():
        return False, "vazia"
    if len(texto) > TAMANHO_MAX_RESPOSTA:
        return False, "longa demais"
    citacoes = {int(n) for n in re.findall(r"\[(\d+)\]", texto)}
    if not citacoes:
        return False, "sem citação"
    if any(n < 1 or n > total_trechos for n in citacoes):
        return False, "cita trecho inexistente"
    limpo = _sem_acento(texto)
    for frase in FRASES_PROIBIDAS:
        if frase in limpo:
            return False, f"frase proibida: {frase}"
    if tipo_animal and tipo_animal != "desconhecido":
        for termo, dono in TERMOS_DE_OUTRO_ANIMAL.items():
            if termo in limpo and dono != tipo_animal:
                return False, f"instrução de outro animal: {termo}"
    elif tipo_animal == "desconhecido":
        for termo in TERMOS_DE_OUTRO_ANIMAL:
            if termo in limpo:
                return False, f"instrução de animal específico: {termo}"
    return True, "ok"


def formatar_trechos(trechos: list[dict]) -> str:
    return "\n\n".join(f"[{t['n']}] ({t['titulo']}, p. {t['pagina']})\n{t['texto']}" for t in trechos)


def fontes(trechos: list[dict], texto: str | None = None) -> str:
    """Lista só os trechos citados no texto (ou todos, se o texto não citar nenhum)."""
    citados = {int(n) for n in re.findall(r"\[(\d+)\]", texto or "")}
    usados = [t for t in trechos if t["n"] in citados] or trechos
    return "Fontes: " + "; ".join(f"[{t['n']}] {t['titulo']}, p. {t['pagina']}" for t in usados)


def trechos_sem_reescrita(trechos: list[dict], quantos: int = 2, tamanho: int = 350) -> str:
    """Fallback sem LLM: os trechos do guia como estão, cortados e citados."""
    partes = []
    for t in trechos[:quantos]:
        texto = t["texto"] if len(t["texto"]) <= tamanho else t["texto"][:tamanho].rsplit(" ", 1)[0] + "…"
        partes.append(f"[{t['n']}] {texto}")
    return "Do guia oficial:\n" + "\n".join(partes)


def _gerar(llm, prompt: str, trechos: list[dict], tipo_animal: str | None = None):
    """Texto do LLM já validado, ou (None, motivo) para usar o fallback."""
    texto = llm(prompt) if llm else None
    if texto is None:
        return None, "ollama indisponível"
    valida, motivo = validar_resposta(texto, len(trechos), tipo_animal)
    return (texto.strip(), "ok") if valida else (None, motivo)


# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────
DESCRICAO_TIPO = {
    "serpente": "uma serpente; acidente ofídico = picada de cobra",
    "escorpiao": "um escorpião", "aranha": "uma aranha",
    "lagarta": "uma lagarta (taturana)", "desconhecido": "animal não identificado: use só instruções gerais",
}


def prompt_triagem(decisao: dict, grupo_nome: str, soro_nome: str | None, sintomas, trechos,
                   tipo: str = "desconhecido") -> str:
    descricao_tipo = DESCRICAO_TIPO.get(tipo, tipo)
    return f"""Você é o assistente de primeiros socorros do Antídoto, app de emergência para acidentes com animais peçonhentos.

Situação já decidida pelas regras do sistema (não mude nem questione):
- Animal: {grupo_nome}
- Sintomas: {descrever_sintomas(sintomas)}
- Urgência: {decisao["urgencia"]}
- Soro indicado: {soro_nome or "a equipe da unidade decide o soro depois de avaliar"}

Escreva o que a pessoa deve fazer AGORA, enquanto vai para a unidade de saúde, e o que NÃO deve fazer.

ATENÇÃO: os trechos falam de vários animais ao mesmo tempo. Use só as instruções que valem
para qualquer acidente ou especificamente para {grupo_nome} ({descricao_tipo}). Ignore
as instruções que o guia dá só para outros animais (águas-vivas, caravelas, abelhas,
lagartas ou acidentes ofídicos, conforme o caso).

{REGRAS_DE_ESCRITA}

Trechos do guia oficial:
{formatar_trechos(trechos)}

Resposta:"""


def prompt_duvida(pergunta: str, trechos: list[dict], historico: list[dict]) -> str:
    conversa = "\n".join(f"{'Pessoa' if m['papel'] == 'pessoa' else 'Antídoto'}: {m['conteudo']}"
                         for m in historico) or "(início da conversa)"
    return f"""Você é o assistente do Antídoto, que tira dúvidas sobre acidentes com animais peçonhentos com base no guia do Ministério da Saúde.

Se os trechos não respondem a pergunta, responda apenas: "Não encontrei isso no guia oficial; em caso de acidente, procure atendimento médico. [1]"

{REGRAS_DE_ESCRITA}

Conversa até aqui:
{conversa}

Trechos do guia oficial:
{formatar_trechos(trechos)}

Pergunta: {pergunta}

Resposta:"""


# ─────────────────────────────────────────────
# SOS
# ─────────────────────────────────────────────
def consulta_da_triagem(grupo_nome: str) -> str:
    """Pergunta usada no RAG durante o SOS: mira a seção de primeiros socorros do guia."""
    return (f"primeiros socorros em caso de acidente com {grupo_nome}: procure atendimento médico, "
            "lave o local com água e sabão, não amarrar torniquete, não cortar o local")

def triar(grupo: str, sintomas: list[str] | None, llm=None) -> dict:
    """Triagem completa. llm: função prompt → texto (ou None). Lança regras.GrupoInvalido."""
    soros = dados.carregar_soros()
    decisao = regras.avaliar(grupo, sintomas, soros)
    info = next(g for g in soros["grupos"] if g["id"] == decisao["grupo"])
    soro_nome = next((s["nome"] for s in soros["soros"] if s["id"] == decisao["soro"]), None)
    trechos, motivo = [], None

    if decisao["urgencia"] == "CRITICA":
        orientacao, fonte = decisao["orientacao"], "protocolo"
    else:
        busca = rag.buscar(consulta_da_triagem(info["nome"]))
        trechos = busca["trechos"]
        if not trechos:
            orientacao, fonte = decisao["orientacao"], "regras"
        else:
            prompt = prompt_triagem(decisao, info["nome"], soro_nome, sintomas, trechos, info["tipo"])
            texto, motivo = _gerar(llm, prompt, trechos, info["tipo"])
            if texto:
                orientacao, fonte = f"{decisao['orientacao']}\n\n{texto}", "llama"
                orientacao += f"\n\n{fontes(trechos, texto)}"
            else:
                # Só o 1º trecho (a seção de primeiros socorros): os outros podem ser de outro animal
                orientacao, fonte = f"{decisao['orientacao']}\n\n{trechos_sem_reescrita(trechos, quantos=1, tamanho=600)}", "regras+guia"
                orientacao += f"\n\n{fontes(trechos[:1])}"

    return {
        "grupo": decisao["grupo"], "grupo_nome": info["nome"],
        "urgencia": decisao["urgencia"], "soro": decisao["soro"], "soro_nome": soro_nome,
        "sinais_graves": decisao["sinais_graves"], "orientacao": orientacao, "fonte": fonte,
        "motivo_fallback": None if fonte in ("llama", "protocolo") else motivo,
        "trechos": [{"n": t["n"], "pagina": t["pagina"]} for t in trechos],
        "aviso": AVISO,
    }


# ─────────────────────────────────────────────
# Dúvidas
# ─────────────────────────────────────────────
def responder(mensagem: str, historico: list[dict] | None = None, llm=None) -> dict:
    """Resposta a uma dúvida em texto livre. Lança rag.PerguntaInvalida se vazia ou longa."""
    mensagem = mascarar_dados_pessoais((mensagem or "").strip())
    sinais = regras.sinal_grave_no_texto(mensagem)
    trechos, motivo = [], None
    if sinais:
        # Sinal grave no texto também tem resposta fixa, sem LLM
        resposta, fonte = MSG_SINAL_GRAVE, "protocolo"
    else:
        busca = rag.buscar(mensagem)
        trechos = busca["trechos"]
        if busca["status"] == "fora_do_tema":
            resposta, fonte = MSG_FORA_DO_TEMA, "fora_do_tema"
        elif not trechos:
            resposta, fonte = MSG_SEM_FONTE, "sem_fonte"
        else:
            texto, motivo = _gerar(llm, prompt_duvida(mensagem, trechos, historico or []), trechos)
            if texto:
                resposta, fonte = texto, "llama"
                resposta += f"\n\n{fontes(trechos, texto)}"
            else:
                resposta, fonte = trechos_sem_reescrita(trechos), "guia"
                resposta += f"\n\n{fontes(trechos[:2])}"
    return {
        "mensagem": mensagem, "resposta": resposta, "fonte": fonte, "sinais_graves": sinais,
        "motivo_fallback": None if fonte in ("llama", "protocolo", "fora_do_tema", "sem_fonte") else motivo,
        "trechos": [{"n": t["n"], "pagina": t["pagina"]} for t in trechos],
    }
