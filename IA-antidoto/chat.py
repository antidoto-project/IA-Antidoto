"""
Antídoto IA — versão de terminal.

  [1] SOS: escolha o animal e os sintomas → urgência, soro e o que fazer agora
  [2] Dúvidas: pergunte em texto livre, respostas só com base no guia oficial

Usa o motor de regras, o RAG sobre o Guia de Animais Peçonhentos do Brasil
(Ministério da Saúde) e o Llama 3.1 local via Ollama. Triagens e conversas
ficam no SQLite (runtime/antidoto.db).
"""
import uuid

import assistente
import dados
import db
import rag
import regras
from llm import MODEL, chamar_llama, status_ollama

ICONE_URGENCIA = {"CRITICA": "🔴 CRÍTICA", "ALTA": "🟠 ALTA", "MEDIA": "🟡 MÉDIA", "BAIXA": "🟢 BAIXA"}
ORIGEM = {
    "llama": "",
    "protocolo": "  (protocolo de emergência — sem IA)",
    "regras": "  (orientação das regras — nenhum trecho do guia encontrado)",
    "regras+guia": "  (trechos do guia sem reescrita — Llama indisponível ou resposta descartada)",
    "guia": "  (trechos do guia sem reescrita — Llama indisponível ou resposta descartada)",
    "fora_do_tema": "",
    "sem_fonte": "",
}


def llm(prompt: str):
    return chamar_llama(prompt, timeout=120)


def perguntar(texto: str) -> str:
    try:
        return input(texto).strip()
    except (KeyboardInterrupt, EOFError):
        return ":sair"


def escolher_numero(opcoes: int, texto: str = "Sua escolha: ") -> int | None:
    while True:
        escolha = perguntar(texto)
        if escolha.lower() in (":sair", ":menu", "0"):
            return None
        if escolha.isdigit() and 1 <= int(escolha) <= opcoes:
            return int(escolha)
        print("Opção inválida. Tente novamente.")


def ler_sintomas(texto: str, lista: list[str]) -> list[str] | None:
    """'1, 3' → códigos. Vazio = nenhum sintoma. None = entrada inválida."""
    if not texto:
        return []
    escolhidos = []
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte.isdigit() or not 1 <= int(parte) <= len(lista):
            return None
        escolhidos.append(lista[int(parte) - 1])
    return list(dict.fromkeys(escolhidos))


def exibir_triagem(r: dict):
    print(f"\n┌─ Resultado da triagem {'─' * 30}")
    print(f"│  Animal:   {r['grupo_nome']}")
    print(f"│  Urgência: {ICONE_URGENCIA[r['urgencia']]}")
    print(f"│  Soro:     {r['soro_nome'] or 'a unidade de saúde decide após avaliar'}")
    if r["sinais_graves"]:
        print(f"│  Sinais graves: {assistente.descrever_sintomas(r['sinais_graves'])}")
    print(f"└{'─' * 53}")
    print(f"\n🩺 O que fazer agora:{ORIGEM[r['fonte']]}\n")
    print(r["orientacao"])
    print(f"\nℹ️  {r['aviso']}\n")


def sos(sessao: str):
    soros = dados.carregar_soros()
    grupos = soros["grupos"]
    print("\n🚨 SOS — Qual animal causou o acidente?\n")
    for i, g in enumerate(grupos, start=1):
        print(f"  [{i}] {g['nome']}")
    escolha = escolher_numero(len(grupos), "\nNúmero do animal (0 para voltar): ")
    if escolha is None:
        return
    grupo = grupos[escolha - 1]

    lista = list(assistente.SINTOMAS)
    print("\nQuais sintomas a pessoa tem? (números separados por vírgula, Enter se nenhum)\n")
    for i, codigo in enumerate(lista, start=1):
        grave = "  ⚠️" if codigo in regras.SINAIS_GRAVES else ""
        print(f"  [{i}] {assistente.SINTOMAS[codigo]}{grave}")
    while True:
        sintomas = ler_sintomas(perguntar("\nSintomas: "), lista)
        if sintomas is not None:
            break
        print("Use os números da lista, separados por vírgula (ex.: 1, 2).")

    print("\n🤔 Analisando...", end="\r")
    resultado = assistente.triar(grupo["id"], sintomas, llm=llm)
    db.salvar_triagem(sessao, resultado)
    exibir_triagem(resultado)
    perguntar("Enter para voltar ao menu...")


def duvidas(sessao: str):
    print("\n💬 Dúvidas sobre animais peçonhentos (respostas com base no guia do Ministério da Saúde)")
    print("   Comandos:  :menu volta ao menu · :limpar nova conversa · :sair encerra\n")
    while True:
        mensagem = perguntar("👤 Você: ")
        comando = mensagem.lower()
        if not mensagem:
            continue
        if comando in (":menu", ":sair"):
            return comando
        if comando == ":limpar":
            sessao = str(uuid.uuid4())
            print("── Nova conversa iniciada ──\n")
            continue
        print("🤔 Pensando...", end="\r")
        try:
            resultado = assistente.responder(mensagem, db.historico_sessao(sessao), llm=llm)
        except rag.PerguntaInvalida as e:
            print(f"⚠️  {e}\n")
            continue
        db.salvar_mensagem(sessao, "pessoa", resultado["mensagem"])
        db.salvar_mensagem(sessao, "antidoto", resultado["resposta"], resultado["fonte"])
        print(f"\n🩺 Antídoto:{ORIGEM[resultado['fonte']]}\n{resultado['resposta']}\n")


def menu():
    sessao = str(uuid.uuid4())
    while True:
        print("\n" + "─" * 50)
        print("  [1] 🚨 SOS — alguém foi picado ou mordido")
        print("  [2] 💬 Tirar dúvidas sobre animais peçonhentos")
        print("  [0] Sair")
        escolha = perguntar("\nSua escolha: ")
        if escolha == "1":
            sos(sessao)
        elif escolha == "2":
            if duvidas(sessao) == ":sair":
                break
        elif escolha in ("0", ":sair"):
            break
        else:
            print("Opção inválida.")
    print("\nCuide-se. Em caso de acidente, ligue 192. 🩺\n")


if __name__ == "__main__":
    print("\n" + "═" * 50)
    print("  🩺 Antídoto IA — acidentes com animais peçonhentos")
    print("═" * 50)
    print("  Em emergência, ligue 192 (SAMU).")

    status = status_ollama()
    if status["ollama"] == "conectado" and status["modelo_baixado"]:
        print(f"\n✅ Ollama conectado · modelo {MODEL}")
    elif status["ollama"] == "conectado":
        print(f"\n⚠️  Ollama conectado, mas o modelo {MODEL} não foi baixado: ollama pull {MODEL}")
    else:
        print("\n⚠️  Ollama não está rodando — as respostas virão das regras e dos trechos do guia.")
        print(f"   Para usar o Llama: abra o Ollama e rode  ollama pull {MODEL}")

    try:
        dados.carregar_soros()
        total = rag.carregar()
        print(f"📚 Guia oficial indexado: {total} trechos")
    except dados.DadosInvalidos as e:
        print("\n❌ Base de soros inválida:")
        for problema in e.erros:
            print(f"   • {problema}")
        raise SystemExit(1)
    menu()
