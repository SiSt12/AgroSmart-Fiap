"""Regressao da interface e do envio pela entrada automatica."""

import io
import json

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from agrosmart.actions import emitir_acoes
from agrosmart.history import ROOT, load_history, preview_import
from agrosmart.ingestion import Ingestor
from agrosmart.sprint3_ui import enfileirar_arquivo, ler_estado


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    historico = tmp_path / "historico com espaco"
    historico.mkdir()
    (historico / "historico.csv").write_bytes(
        (ROOT / "data/demo/historico_demo.csv").read_bytes()
    )
    motor = Ingestor(historico)
    monkeypatch.setenv("AGROSMART_HISTORY_DIR", str(historico))
    return historico, motor, tmp_path / "entrada", tmp_path / "saidas"


def test_envio_valido_enfileira_sem_importar_diretamente(ambiente):
    historico, motor, entrada, saidas = ambiente
    lote = ROOT / "data/demo/lote_novo.csv"
    destino = enfileirar_arquivo(lote.read_bytes(), lote.name, entrada)
    assert destino.exists()
    assert len(preview_import(destino.read_bytes(), destino.name).rows) == 8
    assert len(load_history(historico)) == 360
    assert motor.pendentes() == []


def test_envio_aceita_json_com_resultados(ambiente):
    historico, motor, entrada, saidas = ambiente
    lote = ROOT / "data/demo/lote_novo.csv"
    linhas = preview_import(lote.read_bytes(), lote.name).rows.to_dict("records")
    conteudo = json.dumps({"metadata": {}, "resultados": linhas}).encode()
    destino = enfileirar_arquivo(conteudo, "resultados.json", entrada)
    assert destino.suffix == ".json"
    assert len(preview_import(destino.read_bytes(), destino.name).rows) == 8


def test_envio_invalido_nao_cria_arquivo(ambiente):
    historico, motor, entrada, saidas = ambiente
    with pytest.raises(ValueError):
        enfileirar_arquivo(b'[{"imagem":"invalida.jpg"}]', "invalido.json", entrada)
    assert not entrada.exists()
    assert len(load_history(historico)) == 360


def test_consulta_sem_banco_nao_cria_arquivos(tmp_path):
    caminho = tmp_path / "nao_existe"
    assert ler_estado(caminho) == {"acoes": [], "lotes_pendentes": 0}
    assert not caminho.exists()


def test_consulta_das_acoes_nao_modifica_banco_nem_csv(ambiente):
    historico, motor, entrada, saidas = ambiente
    motor.processar(ROOT / "data/demo/lote_novo.csv")
    emitir_acoes(motor, saidas)
    antes = (motor.banco.read_bytes(), motor.csv.read_bytes())
    estado = ler_estado(historico)
    assert len(estado["acoes"]) == 3
    assert all(a["exportado"] for a in estado["acoes"])
    assert estado["lotes_pendentes"] == 0
    assert antes == (motor.banco.read_bytes(), motor.csv.read_bytes())


def test_interface_filtra_acoes_e_mostra_estado_vazio(ambiente):
    historico, motor, entrada, saidas = ambiente
    motor.processar(ROOT / "data/demo/lote_novo.csv")
    emitir_acoes(motor, saidas)
    fonte = (
        "from pathlib import Path\n"
        "from agrosmart.sprint3_ui import render_actions\n"
        f"render_actions(Path({str(historico)!r}), Path({str(saidas)!r}))"
    )
    app = AppTest.from_string(fonte).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 3
    app.selectbox(key="s3_tipo").set_value("Relatório").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1
    app.selectbox(key="s3_talhao").set_value("Talhão B").run()
    assert not app.exception
    assert any("Nenhuma ação" in w.value for w in app.warning)


def test_botao_de_envio_usa_a_fila(ambiente, monkeypatch):
    historico, motor, entrada, saidas = ambiente
    lote = ROOT / "data/demo/lote_novo.csv"
    uploaded = io.BytesIO(lote.read_bytes())
    uploaded.name = lote.name
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)
    fonte = (
        "from pathlib import Path\n"
        "from agrosmart.sprint3_ui import render_upload\n"
        f"render_upload(Path({str(entrada)!r}))"
    )
    app = AppTest.from_string(fonte).run()
    app.button(key="s3_send").click().run()
    assert not app.exception
    assert list(entrada.glob("*.csv"))
    assert len(load_history(historico)) == 360
    assert app.success


def test_app_com_sqlite_abre_no_historico_e_encaminha_upload(ambiente):
    historico, motor, entrada, saidas = ambiente
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not app.exception
    assert len(app.tabs) == 5
    assert app.radio(key="analytics_source").value == "Histórico importado"
    assert not any(b.key == "seed_history" for b in app.button)
    assert any(
        u.proto.label == "Resultados em CSV ou JSON"
        for u in app.get("file_uploader")
    )