"""Testes das acoes automaticas e da recuperacao apos falhas."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrosmart.actions import emitir_acoes
from agrosmart.history import ROOT, atomic_write, history_json, preview_import
from agrosmart.ingestion import Ingestor


class TestAcoesSprint3(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temp.name)
        self.historico = self.raiz / "historico"
        self.historico.mkdir()
        (self.historico / "historico.csv").write_bytes(
            (ROOT / "data/demo/historico_demo.csv").read_bytes()
        )
        self.destino = self.raiz / "saidas"
        self.lote = ROOT / "data/demo/lote_novo.csv"
        self.motor = Ingestor(self.historico)

    def tearDown(self):
        self.temp.cleanup()

    def emitir(self):
        return emitir_acoes(self.motor, self.destino)

    def acoes(self):
        return [
            json.loads(p.read_text(encoding="utf-8"))
            for p in self.destino.rglob("*.json")
        ]

    def novo_lote(self, talhao, confiancas, categoria="saudavel", nome="extra.json"):
        linhas = [
            {
                "id_analise": f"{nome}-{i}",
                "imagem": f"{nome}_{i}.jpg",
                "data_hora": f"2026-09-24T12:{i:02d}:00+00:00",
                "categoria": categoria,
                "confianca": valor,
                "talhao": talhao,
                "origem_dado": "simulado",
            }
            for i, valor in enumerate(confiancas)
        ]
        arquivo = self.raiz / nome
        arquivo.write_text(json.dumps(linhas), encoding="utf-8")
        return arquivo

    def test_base_inicial_nao_dispara_acoes(self):
        resultado = self.emitir()
        self.assertEqual(resultado["acoes_publicadas"], 0)
        self.assertEqual(self.acoes(), [])

    def test_lote_gera_dois_alertas_e_um_relatorio(self):
        self.motor.processar(self.lote)
        resultado = self.emitir()
        self.assertEqual(resultado["alertas_novos"], 2)
        self.assertEqual(resultado["relatorios_novos"], 1)
        self.assertEqual(resultado["acoes_publicadas"], 3)
        self.assertEqual(
            {(a["regra"], a["talhao"]) for a in self.acoes()},
            {("R1", "Talhão B"), ("R1", "Talhão C"), ("R2", "Talhão C")},
        )
        self.assertEqual(len(list(self.destino.rglob("*.txt"))), 1)
        self.assertEqual(self.motor.pendentes(), [])

    def test_emitir_novamente_nao_duplica_acoes(self):
        self.motor.processar(self.lote)
        self.emitir()
        antes = {p: p.read_bytes() for p in self.destino.rglob("*") if p.is_file()}
        resultado = self.emitir()
        self.assertEqual(resultado["acoes_publicadas"], 0)
        depois = {p: p.read_bytes() for p in self.destino.rglob("*") if p.is_file()}
        self.assertEqual(antes, depois)

    def test_reimportacao_em_json_nao_gera_nova_acao(self):
        self.motor.processar(self.lote)
        self.emitir()
        previa = preview_import(self.lote.read_bytes(), self.lote.name)
        repetido = self.raiz / "repetido.json"
        repetido.write_bytes(history_json(previa.rows))
        self.motor.processar(repetido)
        self.assertEqual(self.emitir()["acoes_publicadas"], 0)
        self.assertEqual(len(self.acoes()), 3)

    def test_reinicio_nao_repete_as_acoes(self):
        self.motor.processar(self.lote)
        self.emitir()
        self.motor = Ingestor(self.historico)
        self.motor.processar(self.lote)
        self.assertEqual(self.emitir()["acoes_publicadas"], 0)
        self.assertEqual(len(self.acoes()), 3)

    def test_falha_no_txt_e_recuperada_sem_duplicacao(self):
        self.motor.processar(self.lote)

        def falhar_no_txt(caminho, conteudo):
            if caminho.suffix == ".txt":
                raise OSError("falha simulada")
            atomic_write(caminho, conteudo)

        with patch("agrosmart.actions.atomic_write", side_effect=falhar_no_txt):
            with self.assertRaises(OSError):
                self.emitir()
        self.motor = Ingestor(self.historico)
        resultado = self.emitir()
        self.assertEqual(resultado["alertas_novos"], 0)
        self.assertEqual(resultado["relatorios_novos"], 0)
        self.assertGreater(resultado["acoes_publicadas"], 0)
        self.assertEqual(len(self.acoes()), 3)
        self.assertEqual(len(list(self.destino.rglob("*.txt"))), 1)

    def test_baixa_confianca_gera_apenas_relatorio(self):
        self.motor.processar(self.novo_lote("Talhão A", [0.55, 0.60]))
        resultado = self.emitir()
        self.assertEqual(resultado["alertas_novos"], 0)
        self.assertEqual(resultado["relatorios_novos"], 1)
        self.assertEqual(self.acoes()[0]["motivos"], ["baixa_confianca"])

    def test_dois_motivos_geram_um_unico_relatorio(self):
        self.motor.processar(
            self.novo_lote("Talhão C", [0.55, 0.60], categoria="doente")
        )
        self.emitir()
        relatorios = [a for a in self.acoes() if a["regra"] == "R2"]
        self.assertEqual(len(relatorios), 1)
        self.assertEqual(len(relatorios[0]["motivos"]), 2)

    def test_lote_posterior_nao_altera_decisao_do_anterior(self):
        self.motor.processar(self.lote)
        self.motor.processar(self.novo_lote("Talhão B", [0.9, 0.9]))
        self.emitir()
        alertas_b = [
            a for a in self.acoes()
            if a["regra"] == "R1" and a["talhao"] == "Talhão B"
        ]
        self.assertEqual(len(alertas_b), 1)
        self.assertEqual(alertas_b[0]["total"], 92)
        self.assertGreater(alertas_b[0]["percentual_doentes"], 30)