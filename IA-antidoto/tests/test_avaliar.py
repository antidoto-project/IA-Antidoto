"""Script de avaliação (sem Ollama)."""
import unittest

import apoio  # noqa: F401  # ajusta o sys.path
import avaliar
import rag


class AvaliarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rag.carregar()

    def test_triagem_100_por_cento(self):
        self.assertEqual(avaliar.avaliar_triagem()["acuracia"], 1.0)

    def test_rag_acima_da_meta(self):
        r = avaliar.avaliar_rag()
        self.assertGreaterEqual(r["recall_at_4"], 0.8)
        self.assertEqual(r["rejeicao_fora_do_tema"], 1.0)

    def test_todas_as_falhas_tratadas(self):
        falhas = avaliar.avaliar_falhas()
        self.assertTrue(all(f["ok"] for f in falhas), [f for f in falhas if not f["ok"]])

    def test_markdown(self):
        md = avaliar.para_markdown({"executado_em": "agora", "triagem": avaliar.avaliar_triagem(),
                                    "rag": avaliar.avaliar_rag(), "falhas": avaliar.avaliar_falhas(), "llm": None})
        self.assertIn("| Triagem (regras) |", md)
        self.assertIn("recall@4", md)


if __name__ == "__main__":
    unittest.main()
