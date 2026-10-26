"""Testes da entrada incremental e do checkpoint da Sprint 3."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrosmart.history import ROOT, history_json, load_history, preview_import
from agrosmart.ingestion import Ingestor


class TestIngestaoSprint3(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temp.name)
        self.historico = self.raiz / "historico"
        self.historico.mkdir()
        self.csv = self.historico / "historico.csv"
        self.csv.write_bytes(
            (ROOT / "data/demo/historico_demo.csv").read_bytes()
        )
        self.lote = ROOT / "data/demo/lote_novo.csv"
        self.motor = Ingestor(self.historico)

    def tearDown(self):
        self.temp.cleanup()

    def linhas_novas(self):
        previa = preview_import(self.lote.read_bytes(), self.lote.name)
        return previa.rows.to_dict("records")

    def salvar_json(self, linhas):
        arquivo = self.raiz / "entrada.json"
        arquivo.write_text(json.dumps(linhas), encoding="utf-8")
        return arquivo

    def test_base_inicial_sem_acoes_retrospectivas(self):
        self.assertEqual(len(load_history(self.historico)), 360)
        self.assertEqual(self.motor.pendentes(), [])
        self.assertTrue(self.motor.banco.exists())

    def test_lote_adiciona_oito_e_guarda_contextos(self):
        resultado = self.motor.processar(self.lote)
        self.assertEqual(resultado["adicionados"], 8)
        self.assertEqual(resultado["total_historico"], 368)
        contextos = {
            r["talhao"]: r for r in self.motor.pendentes()[0]["contextos"]
        }
        self.assertEqual(contextos["Talhão B"]["doentes"], 28)
        self.assertEqual(contextos["Talhão C"]["doentes"], 53)
        self.assertEqual(contextos["Talhão C"]["total"], 92)

    def test_repeticao_nao_adiciona_registros_nem_pendencias(self):
        self.motor.processar(self.lote)
        resultado = self.motor.processar(self.lote)
        self.assertEqual(resultado["adicionados"], 0)
        self.assertEqual(resultado["duplicados"], 8)
        self.assertEqual(len(self.motor.pendentes()), 1)

    def test_mesmos_eventos_em_json_tambem_sao_repetidos(self):
        self.motor.processar(self.lote)
        previa = preview_import(self.lote.read_bytes(), self.lote.name)
        arquivo = self.raiz / "repeticao.json"
        arquivo.write_bytes(history_json(previa.rows))
        resultado = self.motor.processar(arquivo)
        self.assertEqual(resultado["adicionados"], 0)
        self.assertEqual(resultado["duplicados"], 8)
        self.assertEqual(len(self.motor.pendentes()), 1)

    def test_reinicio_preserva_historico_e_checkpoint(self):
        self.motor.processar(self.lote)
        reiniciado = Ingestor(self.historico)
        resultado = reiniciado.processar(self.lote)
        self.assertEqual(resultado["total_historico"], 368)
        self.assertEqual(resultado["adicionados"], 0)
        self.assertEqual(resultado["duplicados"], 8)
        self.assertEqual(len(reiniciado.pendentes()), 1)

    def test_lote_com_registro_invalido_e_rejeitado_por_inteiro(self):
        linhas = self.linhas_novas()[:2]
        linhas[1]["categoria"] = "invalida"
        with self.assertRaises(ValueError):
            self.motor.processar(self.salvar_json(linhas))
        self.assertEqual(len(load_history(self.historico)), 360)
        self.assertEqual(self.motor.pendentes(), [])

    def test_conflito_de_id_desfaz_todo_o_lote(self):
        linhas = self.linhas_novas()[:2]
        linhas[1]["id_analise"] = "demo-0001"
        with self.assertRaises(ValueError):
            self.motor.processar(self.salvar_json(linhas))
        self.assertEqual(len(load_history(self.historico)), 360)
        self.assertEqual(self.motor.pendentes(), [])

    def test_reinicio_recupera_csv_apos_falha_de_exportacao(self):
        with patch(
            "agrosmart.ingestion.atomic_write", side_effect=OSError("simulacao")
        ):
            with self.assertRaises(OSError):
                self.motor.processar(self.lote)
        self.assertEqual(len(load_history(self.historico)), 360)
        reiniciado = Ingestor(self.historico)
        self.assertEqual(len(load_history(self.historico)), 368)
        self.assertEqual(len(reiniciado.pendentes()), 1)

    def test_alteracao_externa_do_csv_nao_e_sobrescrita(self):
        alterado = self.csv.read_bytes() + b"\n"
        self.csv.write_bytes(alterado)
        with self.assertRaises(ValueError):
            self.motor.processar(self.lote)
        self.assertEqual(self.csv.read_bytes(), alterado)
        self.assertEqual(self.motor.pendentes(), [])