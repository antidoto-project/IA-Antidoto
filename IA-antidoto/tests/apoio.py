"""Configuração comum dos testes: banco SQLite temporário e Ollama nunca chamado de verdade."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TesteComBanco(unittest.TestCase):
    """Cada teste usa um SQLite novo em pasta temporária."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._antigo = os.environ.get("ANTIDOTO_DB")
        os.environ["ANTIDOTO_DB"] = str(Path(self._tmp.name) / "teste.db")

    def tearDown(self):
        if self._antigo is None:
            os.environ.pop("ANTIDOTO_DB", None)
        else:
            os.environ["ANTIDOTO_DB"] = self._antigo
        self._tmp.cleanup()
