"""Validação das bases estruturadas (soros.json e casos-triagem.json)."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import apoio  # noqa: F401  # ajusta o sys.path
import dados


class BasesReaisTest(unittest.TestCase):
    def test_bases_do_repositorio_sao_validas(self):
        soros = dados.carregar_soros()
        self.assertEqual(len(soros["grupos"]), 9)
        self.assertEqual(len(soros["soros"]), 8)
        self.assertEqual(dados.resumo()["bases"], "ok")

    def test_grupos_iguais_ao_catalogo_da_api_dotnet(self):
        self.assertEqual(dados.grupos_validos(), {
            "JARARACA", "CASCAVEL", "SURUCUCU", "CORAL", "ESCORPIAO",
            "ARMADEIRA", "ARANHA_MARROM", "LAGARTA", "DESCONHECIDO",
        })


class ValidarSorosTest(unittest.TestCase):
    def setUp(self):
        self.base = dados.carregar_soros()

    def alterar(self, funcao):
        base = copy.deepcopy(self.base)
        funcao(base)
        return dados.validar_soros(base)

    def test_soro_inexistente(self):
        erros = self.alterar(lambda b: b["grupos"][0].update(soro="ANTIDRAGAO"))
        self.assertTrue(any("soro inexistente" in e for e in erros))

    def test_id_repetido(self):
        erros = self.alterar(lambda b: b["grupos"].append(dict(b["grupos"][0])))
        self.assertTrue(any("id repetido" in e for e in erros))

    def test_campo_obrigatorio_ausente(self):
        erros = self.alterar(lambda b: b["grupos"][1].pop("nome"))
        self.assertTrue(any("campo obrigatório ausente (nome)" in e for e in erros))

    def test_tipo_invalido(self):
        erros = self.alterar(lambda b: b["grupos"][1].update(tipo="peixe"))
        self.assertTrue(any("tipo inválido" in e for e in erros))

    def test_so_desconhecido_fica_sem_soro(self):
        erros = self.alterar(lambda b: b["grupos"][0].update(soro=None))
        self.assertTrue(any("só o grupo desconhecido" in e for e in erros))

    def test_id_em_minusculas(self):
        erros = self.alterar(lambda b: b["grupos"][0].update(id="jararaca"))
        self.assertTrue(any("maiúsculas" in e for e in erros))

    def test_lista_vazia(self):
        self.assertEqual(dados.validar_soros({"soros": [], "grupos": []}), ["soros: lista ausente ou vazia"])


class ValidarCasosTest(unittest.TestCase):
    def setUp(self):
        self.soros = dados.carregar_soros()
        self.base = {"casos": dados.carregar_casos(self.soros)}

    def alterar(self, funcao):
        base = copy.deepcopy(self.base)
        funcao(base["casos"][0])
        return dados.validar_casos(base, self.soros)

    def test_grupo_invalido(self):
        erros = self.alterar(lambda c: c["entrada"].update(grupoAnimal="DRAGAO"))
        self.assertTrue(any("grupo inválido" in e for e in erros))

    def test_urgencia_invalida(self):
        erros = self.alterar(lambda c: c["esperado"].update(urgencia="URGENTE"))
        self.assertTrue(any("urgência inválida" in e for e in erros))

    def test_sintomas_precisa_ser_lista(self):
        erros = self.alterar(lambda c: c["entrada"].update(sintomas="DOR_LOCAL"))
        self.assertTrue(any("sintomas" in e for e in erros))

    def test_soro_esperado_inexistente(self):
        erros = self.alterar(lambda c: c["esperado"].update(soro="XYZ"))
        self.assertTrue(any("soro inexistente" in e for e in erros))

    def test_id_repetido(self):
        base = copy.deepcopy(self.base)
        base["casos"].append(copy.deepcopy(base["casos"][0]))
        self.assertTrue(any("id repetido" in e for e in dados.validar_casos(base, self.soros)))


class ArquivoTest(unittest.TestCase):
    def test_arquivo_ausente_ou_json_quebrado(self):
        with tempfile.TemporaryDirectory() as tmp:
            quebrado = Path(tmp) / "soros.json"
            quebrado.write_text("{ isto não é json", encoding="utf-8")
            with patch.object(dados, "SOROS_FILE", quebrado):
                with self.assertRaises(dados.DadosInvalidos):
                    dados.carregar_soros()
                self.assertEqual(dados.resumo()["bases"], "inválidas")
            with patch.object(dados, "SOROS_FILE", Path(tmp) / "nao-existe.json"):
                with self.assertRaises(dados.DadosInvalidos) as ctx:
                    dados.carregar_soros()
                self.assertIn("arquivo não encontrado", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
