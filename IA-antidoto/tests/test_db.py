"""Persistência SQLite: triagens e conversas, sem dados pessoais."""
import unittest

from apoio import TesteComBanco
import assistente
import db


class BancoTest(TesteComBanco):
    def test_salva_e_lista_triagem(self):
        resultado = assistente.triar("CORAL", ["DOR_LOCAL"], llm=lambda p: None)
        db.salvar_triagem("sessao-1", resultado)
        salvas = db.listar_triagens()
        self.assertEqual(len(salvas), 1)
        self.assertEqual(salvas[0]["urgencia"], "ALTA")
        self.assertEqual(salvas[0]["resultado"]["soro"], "ELAPIDICO")

    def test_historico_da_sessao_em_ordem(self):
        for i in range(8):
            db.salvar_mensagem("s", "pessoa" if i % 2 == 0 else "antidoto", f"m{i}")
        db.salvar_mensagem("outra", "pessoa", "não aparece")
        historico = db.historico_sessao("s", limite=4)
        self.assertEqual([m["conteudo"] for m in historico], ["m4", "m5", "m6", "m7"])

    def test_papel_invalido_e_rejeitado(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            db.salvar_mensagem("s", "hacker", "x")


if __name__ == "__main__":
    unittest.main()
