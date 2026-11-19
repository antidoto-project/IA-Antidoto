"""RAG: preparação do guia (indexar.py) e busca BM25 (rag.py)."""
import json
import tempfile
import unittest
from pathlib import Path

import apoio  # noqa: F401  # ajusta o sys.path
import indexar
import rag

CABECALHOS = ["Guia de animais peçonhentos do Brasil"]

TRECHOS = [
    {"id": "g#1", "fonte": "g", "titulo": "Guia", "pagina": 164, "ordem": 1,
     "texto": "8.9 Primeiros-socorros. Em caso de acidente, procure atendimento médico imediatamente. "
              "Lave o local da picada com água e sabão."},
    {"id": "g#2", "fonte": "g", "titulo": "Guia", "pagina": 165, "ordem": 2,
     "texto": "Não amarrar (torniquete) o membro e não cortar o local da picada."},
    {"id": "g#3", "fonte": "g", "titulo": "Guia", "pagina": 98, "ordem": 3,
     "texto": "O escorpião-amarelo se reproduz por partenogênese em áreas urbanas."},
    {"id": "g#4", "fonte": "g", "titulo": "Guia", "pagina": 89, "ordem": 4,
     "texto": "A aranha-marrom tem uma mancha escura semelhante a um violino."},
]


class LimpezaTest(unittest.TestCase):
    def test_remove_cabecalho_numero_e_referencias(self):
        texto, ref = indexar.limpar_pagina("163\nGuia de animais peçonhentos do Brasil\nTexto útil.\n"
                                           "REFERÊNCIAS\nSILVA, A. 2020.", CABECALHOS)
        self.assertEqual(texto, "Texto útil.")
        self.assertTrue(ref)

    def test_hifenizacao_e_topicos(self):
        texto, _ = indexar.limpar_pagina("acumula-\ndo e cobra-\n-coral\n\t\xa0 Não cortar.", CABECALHOS)
        self.assertEqual(texto, "acumulado e cobra-coral • Não cortar.")


class CorteTest(unittest.TestCase):
    def setUp(self):
        frase = "Esta é uma frase de exemplo sobre acidentes com escorpião. "
        self.paginas = [(10, frase * 20), (11, frase * 20)]

    def test_tamanho_ordem_e_sobreposicao(self):
        trechos = indexar.cortar_trechos(self.paginas)
        for t in trechos[:-1]:
            self.assertTrue(indexar.TAMANHO_MIN <= len(t["texto"]) <= indexar.TAMANHO_MAX)
        self.assertEqual([t["ordem"] for t in trechos], list(range(1, len(trechos) + 1)))
        fim_do_primeiro = trechos[0]["texto"].split(". ")[-1].rstrip(".")
        self.assertTrue(trechos[1]["texto"].startswith(fim_do_primeiro))

    def test_secao_numerada_comeca_trecho_novo(self):
        texto = "Texto sobre prevenção de acidentes em casa e no campo. " * 4 + \
                "8.9 Primeiros-socorros. Em caso de acidente, procure atendimento médico imediatamente. " * 2
        trechos = indexar.cortar_trechos([(164, texto)])
        self.assertTrue(trechos[-1]["texto"].startswith("8.9 Primeiros-socorros"))

    def test_titulo_solto_nao_vira_trecho(self):
        self.assertEqual(indexar.cortar_trechos([(7, "APRESENTAÇÃO")]), [])


class GuiaRealTest(unittest.TestCase):
    @unittest.skipUnless((indexar.DOCS_DIR / "guia_animais_peconhentos_brasil.pdf").exists(), "PDF ausente")
    def test_pdf_vira_indice(self):
        with tempfile.TemporaryDirectory() as tmp:
            resumo = indexar.indexar(Path(tmp) / "indice.json")
            trechos = json.loads((Path(tmp) / "indice.json").read_text(encoding="utf-8"))["trechos"]
        self.assertGreater(resumo["total_trechos"], 300)
        self.assertEqual(resumo["documentos"][0]["paginas_sem_texto"], [])
        self.assertTrue(any(t["texto"].startswith("8.9 Primeiros-socorros") for t in trechos))


class BuscaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        arquivo = Path(self.tmp.name) / "indice.json"
        arquivo.write_text(json.dumps({"trechos": TRECHOS}), encoding="utf-8")
        rag.carregar(arquivo)

    def tearDown(self):
        rag._cache.update(trechos=None, idf=None, media=None)
        self.tmp.cleanup()

    def test_termo_exato_vem_primeiro_e_numerado(self):
        r = rag.buscar("Posso fazer torniquete?")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["trechos"][0]["pagina"], 165)
        self.assertEqual(r["trechos"][0]["n"], 1)

    def test_picado_e_picada_sao_a_mesma_palavra(self):
        self.assertEqual(rag.buscar("fui picado, procuro atendimento?")["trechos"][0]["pagina"], 164)

    def test_sem_acento_e_maiusculas(self):
        self.assertEqual(rag.buscar("ESCORPIÃO AMARELO")["trechos"][0]["pagina"], 98)

    def test_respeita_k(self):
        self.assertLessEqual(len(rag.buscar("acidente picada escorpião aranha", k=2)["trechos"]), 2)

    def test_fora_do_tema(self):
        self.assertEqual(rag.buscar("qual o horário do jogo do Corinthians?")["status"], "fora_do_tema")
        self.assertEqual(rag.buscar("receita de bolo de cenoura")["status"], "fora_do_tema")

    def test_do_tema_mas_sem_trecho(self):
        self.assertEqual(rag.buscar("cobra de estimação come rato?")["status"], "sem_trecho_relevante")

    def test_pergunta_invalida(self):
        with self.assertRaises(rag.PerguntaInvalida):
            rag.buscar("   ")
        with self.assertRaises(rag.PerguntaInvalida):
            rag.buscar("picada " * 200)

    def test_filtro_de_tema(self):
        self.assertTrue(rag.fala_do_tema("a taturana queimou meu braço"))
        self.assertTrue(rag.fala_do_tema("como tirar o ferrão da abelha"))
        self.assertFalse(rag.fala_do_tema("como trocar o pneu do carro"))


if __name__ == "__main__":
    unittest.main()
