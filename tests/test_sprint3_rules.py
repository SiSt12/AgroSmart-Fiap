"""Verifica as regras aprovadas para a Sprint 3."""

import unittest

from agrosmart.rules import avaliar_regras


class TestRegrasSprint3(unittest.TestCase):
    def test_talhao_b_gera_apenas_alerta(self):
        resultado = avaliar_regras(92, 28, [0.9, 0.9])
        self.assertTrue(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_talhao_c_gera_alerta_e_relatorio(self):
        resultado = avaliar_regras(92, 53, [0.9, 0.9])
        self.assertTrue(resultado["alerta"])
        self.assertTrue(resultado["relatorio"])
        self.assertEqual(resultado["motivos"], ["mais_de_50_porcento_doentes"])

    def test_baixa_confianca_gera_relatorio_sem_alerta(self):
        resultado = avaliar_regras(92, 8, [0.55, 0.60])
        self.assertFalse(resultado["alerta"])
        self.assertEqual(resultado["motivos"], ["baixa_confianca"])
        self.assertAlmostEqual(resultado["confianca_media_novos"], 0.575)

    def test_trinta_porcento_exatos_nao_geram_alerta(self):
        resultado = avaliar_regras(90, 27, [0.9])
        self.assertFalse(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_cinquenta_porcento_exatos_nao_geram_relatorio(self):
        resultado = avaliar_regras(100, 50, [0.9])
        self.assertTrue(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_media_sessenta_e_cinco_exata_nao_e_baixa(self):
        resultado = avaliar_regras(100, 0, [0.60, 0.70])
        self.assertFalse(resultado["relatorio"])
        self.assertEqual(resultado["confianca_media_novos"], 0.65)

    def test_sem_registros_novos_nao_gera_acoes(self):
        resultado = avaliar_regras(92, 53, [])
        self.assertFalse(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_menos_de_dez_analises_nao_gera_acoes(self):
        resultado = avaliar_regras(9, 9, [0.5])
        self.assertFalse(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_historico_vazio_nao_inventa_percentual(self):
        resultado = avaliar_regras(0, 0, [])
        self.assertIsNone(resultado["percentual_doentes"])
        self.assertFalse(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_acoes_da_mesma_entrada_nao_se_repetem(self):
        resultado = avaliar_regras(
            92, 53, [0.9], r1_ja_emitida=True, r2_ja_emitida=True
        )
        self.assertFalse(resultado["alerta"])
        self.assertFalse(resultado["relatorio"])

    def test_rejeita_contagens_invalidas(self):
        for total, doentes in [(-1, 0), (10, 11), (10, -1), (1.5, 1)]:
            with self.subTest(total=total, doentes=doentes):
                with self.assertRaises(ValueError):
                    avaliar_regras(total, doentes, [])

    def test_rejeita_confiancas_invalidas(self):
        for valor in [-0.1, 1.1, float("nan"), float("inf"), "invalido"]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    avaliar_regras(10, 0, [valor])