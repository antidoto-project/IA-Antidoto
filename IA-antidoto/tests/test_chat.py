"""Terminal: leitura dos sintomas e sessão completa simulada (sem Ollama)."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from apoio import TesteComBanco
import chat
import db


class LerSintomasTest(unittest.TestCase):
    LISTA = ["DOR_LOCAL", "INCHACO", "FALTA_DE_AR"]

    def test_numeros_separados_por_virgula(self):
        self.assertEqual(chat.ler_sintomas("1, 3", self.LISTA), ["DOR_LOCAL", "FALTA_DE_AR"])
        self.assertEqual(chat.ler_sintomas("2;2", self.LISTA), ["INCHACO"])

    def test_vazio_e_invalido(self):
        self.assertEqual(chat.ler_sintomas("", self.LISTA), [])
        self.assertIsNone(chat.ler_sintomas("9", self.LISTA))
        self.assertIsNone(chat.ler_sintomas("um", self.LISTA))


class SessaoTest(TesteComBanco):
    def test_sos_e_duvida_pelo_menu(self):
        entradas = iter(["1", "5", "1", "", "2", "Posso fazer torniquete?", "receita de bolo", ":sair"])
        saida = io.StringIO()
        with patch("builtins.input", lambda _="": next(entradas)), \
                patch.object(chat, "chamar_llama", return_value=None), redirect_stdout(saida):
            chat.menu()
        texto = saida.getvalue()
        self.assertIn("Urgência: 🟡 MÉDIA", texto)
        self.assertIn("Soro antiescorpiônico", texto)
        self.assertIn("Do guia oficial:", texto)
        self.assertIn("Eu só respondo sobre acidentes com animais peçonhentos", texto)
        self.assertEqual(len(db.listar_triagens()), 1)


if __name__ == "__main__":
    unittest.main()
