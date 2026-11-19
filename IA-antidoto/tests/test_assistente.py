"""Assistente: triagem (SOS), dúvidas, validação do LLM, fallback e dados pessoais."""
import unittest

import apoio  # noqa: F401  # ajusta o sys.path
import assistente
import dados
import rag
import regras


def llm_bom(prompt):
    return "Lave o local com água e sabão e procure atendimento agora [1]. Não faça torniquete [2]."


class TriagemTest(unittest.TestCase):
    def test_todos_os_casos_de_triagem(self):
        for caso in dados.carregar_casos():
            with self.subTest(caso=caso["id"]):
                r = assistente.triar(caso["entrada"]["grupoAnimal"], caso["entrada"]["sintomas"])
                self.assertEqual(r["urgencia"], caso["esperado"]["urgencia"])
                self.assertEqual(r["soro"], caso["esperado"]["soro"])

    def test_llama_explica_com_fontes_do_guia(self):
        r = assistente.triar("ESCORPIAO", ["DOR_LOCAL"], llm=llm_bom)
        self.assertEqual(r["fonte"], "llama")
        self.assertTrue(r["orientacao"].startswith(regras.ORIENTACAO_BASE))
        self.assertIn("Fontes: [1] Guia de Animais Peçonhentos", r["orientacao"])
        self.assertEqual(r["trechos"][0]["pagina"], 164)  # seção 8.9 Primeiros-socorros

    def test_prompt_leva_a_decisao_das_regras(self):
        prompts = []
        assistente.triar("CASCAVEL", ["INCHACO"], llm=lambda p: prompts.append(p) or None)
        self.assertIn("Urgência: ALTA", prompts[0])
        self.assertIn("Soro anticrotálico", prompts[0])
        self.assertIn("inchaço", prompts[0])
        self.assertIn("[1] (Guia de Animais Peçonhentos", prompts[0])

    def test_llm_nao_muda_urgencia_nem_soro(self):
        r = assistente.triar("JARARACA", [], llm=lambda p: "Urgência BAIXA, use soro antiofídico [1].")
        self.assertEqual((r["urgencia"], r["soro"]), ("ALTA", "BOTROPICO"))

    def test_sinal_grave_nao_chama_o_llm(self):
        chamado = []
        r = assistente.triar("ESCORPIAO", ["FALTA_DE_AR"], llm=lambda p: chamado.append(p))
        self.assertEqual((r["urgencia"], r["fonte"]), ("CRITICA", "protocolo"))
        self.assertTrue(r["orientacao"].startswith("Ligue 192"))
        self.assertEqual(chamado, [])

    def test_ollama_fora_do_ar(self):
        r = assistente.triar("ARMADEIRA", [], llm=lambda p: None)
        self.assertEqual(r["fonte"], "regras+guia")
        self.assertEqual(r["motivo_fallback"], "ollama indisponível")
        self.assertIn("Do guia oficial:\n[1] 8.9 Primeiros-socorros", r["orientacao"])

    def test_llm_que_dispensa_atendimento_e_descartado(self):
        r = assistente.triar("LAGARTA", [], llm=lambda p: "Não é perigoso, pode ficar em casa [1].")
        self.assertEqual(r["fonte"], "regras+guia")
        self.assertNotIn("pode ficar em casa", r["orientacao"])

    def test_instrucao_de_outro_animal_e_descartada(self):
        # Caso real da avaliação: o Llama misturou água-viva e cobra na triagem da lagarta
        r = assistente.triar("LAGARTA", ["DOR_LOCAL"], llm=lambda p: (
            "Lave com água fria ou gelada [1]. Não remova os tentáculos aderidos à pele [2]."))
        self.assertEqual(r["fonte"], "regras+guia")
        self.assertIn("instrução de outro animal", r["motivo_fallback"])

    def test_instrucao_do_proprio_animal_e_aceita(self):
        r = assistente.triar("LAGARTA", [], llm=lambda p: "Lave o local com água fria ou gelada [1].")
        self.assertEqual(r["fonte"], "llama")
        r = assistente.triar("JARARACA", [], llm=lambda p: "Em acidente ofídico, dê água potável [1].")
        self.assertEqual(r["fonte"], "llama")
        r = assistente.triar("ESCORPIAO", [], llm=lambda p: "Em acidente ofídico, dê água potável [1].")
        self.assertEqual(r["fonte"], "regras+guia")

    def test_prompt_avisa_para_ignorar_outros_animais(self):
        prompts = []
        assistente.triar("JARARACA", [], llm=lambda p: prompts.append(p) or None)
        self.assertIn("acidente ofídico = picada de cobra", prompts[0])
        self.assertIn("Ignore", prompts[0])

    def test_fontes_so_dos_trechos_citados(self):
        r = assistente.triar("ESCORPIAO", [], llm=lambda p: "Procure atendimento agora [1].")
        self.assertIn("Fontes: [1]", r["orientacao"])
        self.assertNotIn("[2] Guia", r["orientacao"])

    def test_fallback_da_triagem_mostra_so_a_secao_de_primeiros_socorros(self):
        r = assistente.triar("ESCORPIAO", [], llm=lambda p: None)
        self.assertNotIn("\n[2] ", r["orientacao"])
        self.assertIn("[1] 8.9 Primeiros-socorros", r["orientacao"])

    def test_animal_invalido(self):
        with self.assertRaises(regras.GrupoInvalido):
            assistente.triar("DRAGAO", [])


class DuvidaTest(unittest.TestCase):
    def test_responde_com_llama_e_fontes(self):
        r = assistente.responder("Posso fazer torniquete?", [], llm=llm_bom)
        self.assertEqual(r["fonte"], "llama")
        self.assertIn("Fontes: [1]", r["resposta"])

    def test_historico_vai_no_prompt(self):
        prompts = []
        assistente.responder("e se inchar a picada?", [{"papel": "pessoa", "conteudo": "fui picado por aranha"}],
                             llm=lambda p: prompts.append(p) or None)
        self.assertIn("Pessoa: fui picado por aranha", prompts[0])

    def test_sinal_grave_no_texto(self):
        r = assistente.responder("meu filho está com falta de ar", llm=llm_bom)
        self.assertEqual(r["fonte"], "protocolo")
        self.assertIn("192", r["resposta"])

    def test_fora_do_tema_nao_chama_o_llm(self):
        chamado = []
        r = assistente.responder("quem ganhou o jogo ontem?", llm=lambda p: chamado.append(p))
        self.assertEqual(r["fonte"], "fora_do_tema")
        self.assertEqual(chamado, [])

    def test_ollama_fora_do_ar_devolve_o_guia(self):
        r = assistente.responder("como evitar escorpião em casa?", llm=lambda p: None)
        self.assertEqual(r["fonte"], "guia")
        self.assertIn("Do guia oficial:", r["resposta"])

    def test_dados_pessoais_nao_chegam_ao_llm(self):
        prompts = []
        r = assistente.responder("sou João, CPF 123.456.789-09, tel (11) 98765-4321, fui picado por aranha",
                                 llm=lambda p: prompts.append(p) or None)
        for dado in ("123.456.789-09", "98765-4321"):
            self.assertNotIn(dado, prompts[0])
            self.assertNotIn(dado, r["mensagem"])

    def test_pergunta_vazia(self):
        with self.assertRaises(rag.PerguntaInvalida):
            assistente.responder("   ")


class ValidacaoTest(unittest.TestCase):
    def test_regras_de_validacao(self):
        self.assertEqual(assistente.validar_resposta("Vá à unidade [1].", 2), (True, "ok"))
        self.assertEqual(assistente.validar_resposta("Vá à unidade.", 2)[1], "sem citação")
        self.assertEqual(assistente.validar_resposta("Vá à unidade [3].", 2)[1], "cita trecho inexistente")
        self.assertEqual(assistente.validar_resposta("", 2)[1], "vazia")
        self.assertEqual(assistente.validar_resposta("x [1] " * 400, 2)[1], "longa demais")
        self.assertFalse(assistente.validar_resposta("Não é necessário procurar o hospital [1].", 2)[0])

    def test_orientacao_negada_do_guia_e_permitida(self):
        self.assertTrue(assistente.validar_resposta("Não faça torniquete e não corte o local [1].", 1)[0])

    def test_mascara_dados_pessoais(self):
        texto = assistente.mascarar_dados_pessoais("cpf 12345678909, joao@mail.com, 11 91234-5678")
        self.assertEqual(texto.count("[removido]"), 3)


if __name__ == "__main__":
    unittest.main()
