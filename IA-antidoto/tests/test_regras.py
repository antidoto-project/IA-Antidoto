"""Motor de regras: todos os casos de casos-triagem.json e o guarda de sinais graves."""
import unittest

import apoio  # noqa: F401  # ajusta o sys.path
import dados
import regras


class CasosTriagemTest(unittest.TestCase):
    """Cada caso compartilhado com a API .NET precisa passar (meta: 100%)."""

    def test_todos_os_casos_de_triagem(self):
        casos = dados.carregar_casos()
        self.assertGreaterEqual(len(casos), 20)
        for caso in casos:
            with self.subTest(caso=caso["id"], descricao=caso["descricao"]):
                entrada = caso["entrada"]
                resultado = regras.avaliar(entrada["grupoAnimal"], entrada["sintomas"])
                self.assertEqual(resultado["urgencia"], caso["esperado"]["urgencia"])
                self.assertEqual(resultado["soro"], caso["esperado"]["soro"])

    def test_casos_cobrem_todos_os_grupos_e_sinais_graves(self):
        casos = dados.carregar_casos()
        grupos = {c["entrada"]["grupoAnimal"].upper() for c in casos}
        sintomas = {s.upper() for c in casos for s in c["entrada"]["sintomas"]}
        self.assertEqual(grupos, dados.grupos_validos())
        self.assertTrue(set(regras.SINAIS_GRAVES) <= sintomas)


class RegrasTest(unittest.TestCase):
    def test_critico_manda_ligar_192(self):
        resultado = regras.avaliar("ESCORPIAO", ["FALTA_DE_AR"])
        self.assertEqual(resultado["urgencia"], "CRITICA")
        self.assertIn("192", resultado["orientacao"])
        self.assertEqual(resultado["sinais_graves"], ["FALTA_DE_AR"])

    def test_orientacao_igual_a_da_api_dotnet(self):
        # Texto do OrientacaoBase do RegrasTriagem.cs
        self.assertEqual(regras.avaliar("JARARACA", [])["orientacao"], regras.ORIENTACAO_BASE)
        self.assertIn("Não faça torniquete", regras.ORIENTACAO_BASE)

    def test_nenhuma_decisao_dispensa_atendimento(self):
        # Regra 2: nenhum grupo cai em BAIXA e toda orientação manda ir à unidade
        for grupo in dados.grupos_validos():
            with self.subTest(grupo=grupo):
                resultado = regras.avaliar(grupo, [])
                self.assertIn(resultado["urgencia"], {"MEDIA", "ALTA", "CRITICA"})
                self.assertIn("Vá agora para a unidade", resultado["orientacao"])

    def test_desconhecido_nao_tem_soro_e_fica_alta(self):
        resultado = regras.avaliar("DESCONHECIDO", ["DOR_LOCAL"])
        self.assertIsNone(resultado["soro"])
        self.assertEqual(resultado["urgencia"], "ALTA")

    def test_grupo_invalido_e_rejeitado(self):
        with self.assertRaises(regras.GrupoInvalido):
            regras.avaliar("DRAGAO", [])
        with self.assertRaises(regras.GrupoInvalido):
            regras.avaliar("", [])

    def test_sintoma_vazio_ou_nulo_nao_quebra(self):
        self.assertEqual(regras.avaliar("ESCORPIAO", None)["urgencia"], "MEDIA")
        self.assertEqual(regras.avaliar("ESCORPIAO", ["", None])["urgencia"], "MEDIA")


class SinalGraveNoTextoTest(unittest.TestCase):
    def test_reconhece_sinais_com_e_sem_acento(self):
        self.assertEqual(regras.sinal_grave_no_texto("Ele está com FALTA DE AR"), ["FALTA_DE_AR"])
        self.assertEqual(regras.sinal_grave_no_texto("a pálpebra está caída"), ["PALPEBRA_CAIDA"])
        self.assertEqual(regras.sinal_grave_no_texto("ela vomitou duas vezes"), ["VOMITOS"])
        self.assertIn("VISAO_DUPLA", regras.sinal_grave_no_texto("visão turva e desmaiou"))
        self.assertIn("DESMAIO", regras.sinal_grave_no_texto("visão turva e desmaiou"))

    def test_texto_sem_sinal_grave(self):
        self.assertEqual(regras.sinal_grave_no_texto("o local está vermelho e doendo"), [])
        self.assertEqual(regras.sinal_grave_no_texto(None), [])
        # "ar" só conta como palavra inteira, não dentro de "lugar" ou "arde"
        self.assertEqual(regras.sinal_grave_no_texto("o lugar da picada arde muito"), [])


if __name__ == "__main__":
    unittest.main()
