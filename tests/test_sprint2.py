"""Regras de importação, cálculo e atualização do dashboard."""
from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agrosmart.analytics import by_day, by_plot, select_records, summarize
from agrosmart.demo_history import make_demo
from agrosmart.export import to_csv, to_json
from agrosmart.history import (history_csv, history_json, load_history, normalize_row,
                               preview_import, save_import)


def legacy_row(**changes):
    row = {"imagem": "folha.jpg", "categoria": "doente", "acuracia": 0.9,
           "conf_saudavel": 0.1, "conf_doente": 0.9,
           "data_hora": "2026-09-01T09:00:00-03:00"}
    row.update(changes)
    return row


def preview(rows, **kwargs):
    return preview_import(json.dumps(rows).encode(), "lote.json", **kwargs)


def test_real_legacy_export_formats_have_equal_normalized_events():
    rows = [legacy_row()]
    csv_bytes = to_csv(rows).encode("utf-8-sig")
    json_bytes = to_json(rows, {"acuracia_holdout": 0.9167}).encode()
    a = preview_import(csv_bytes, "fase1.csv", "Talhão A", "simulado")
    b = preview_import(json_bytes, "fase1.json", "Talhão A", "simulado")
    pd.testing.assert_frame_equal(a.rows, b.rows)
    assert a.rows.iloc[0]["confianca"] == 0.9
    assert "acuracia" not in a.rows.columns


def test_reimport_csv_and_json_is_idempotent_and_persists(tmp_path):
    rows = [legacy_row()]
    first = to_csv(rows).encode()
    second = to_json(rows).encode()
    assert save_import(preview_import(first, "one.csv"), first, "one.csv", tmp_path)["adicionados"] == 1
    outcome = save_import(preview_import(second, "two.json"), second, "two.json", tmp_path)
    assert outcome["adicionados"] == 0 and outcome["duplicados"] == 1
    assert len(load_history(tmp_path)) == 1
    assert len(list((tmp_path / "raw").glob('*'))) == 1


def test_conflicting_id_aborts_whole_batch_preserving_history(tmp_path):
    old = legacy_row(id_analise="evento-1")
    save_import(preview([old]), json.dumps([old]).encode(), "first.json", tmp_path)
    before = (tmp_path / "historico.csv").read_bytes()
    conflict = legacy_row(id_analise="evento-1", imagem="outra.jpg")
    fresh = legacy_row(id_analise="evento-2", imagem="nova.jpg")
    with pytest.raises(ValueError, match="conteúdo diferente"):
        save_import(preview([fresh, conflict]), b"unused", "second.json", tmp_path)
    assert (tmp_path / "historico.csv").read_bytes() == before


@pytest.mark.parametrize("change", [
    {"data_hora": "2026-09-01"}, {"data_hora": "amanhã"},
    {"categoria": "ferrugem"}, {"acuracia": float("nan")},
    {"acuracia": 90}, {"acuracia": True},
    {"conf_saudavel": 0.8}, {"origem_dado": "adivinhada"},
    {"imagem": ""}, {"confianca": 0.6},
])
def test_invalid_rows_are_reported_without_losing_valid_rows(change):
    result = preview([legacy_row(), legacy_row(**change)])
    assert result.received == 2
    assert len(result.rows) == 1
    assert len(result.errors) == 1 and result.errors[0]["registro"] == 2


def test_zero_probability_is_valid_and_timezones_normalize():
    a = normalize_row(legacy_row(acuracia=1, conf_saudavel=0, conf_doente=1))
    b = normalize_row(legacy_row(acuracia=1, conf_saudavel=0, conf_doente=1,
                                data_hora="2026-09-01T12:00:00Z"))
    assert a == b


def test_explicit_origin_preserved_and_missing_origin_not_assumed():
    a = normalize_row(legacy_row())
    b = normalize_row(legacy_row(origem_dado="simulado"), default_origin="real_informado")
    assert a["origem_dado"] == "nao_informada" and a["talhao"] == "Não informado"
    assert b["origem_dado"] == "simulado"


def test_canonical_export_roundtrip_preserves_ids_and_optional_probabilities():
    row = legacy_row()
    del row["conf_saudavel"], row["conf_doente"]
    frame = preview([row]).rows
    for content, name in [(history_csv(frame), "x.csv"), (history_json(frame), "x.json")]:
        back = preview_import(content, name)
        assert not back.errors
        assert back.rows.iloc[0]["id_analise"] == frame.iloc[0]["id_analise"]


def test_csv_bom_semicolon_and_bad_structure():
    good = "imagem;categoria;acuracia;data_hora\nf.jpg;saudável;0.8;2026-09-01T09:00:00-03:00\n"
    result = preview_import(good.encode("utf-8-sig"), "f.csv")
    assert not result.errors and result.rows.iloc[0]["categoria"] == "saudavel"
    with pytest.raises(ValueError, match="colunas repetidas"):
        preview_import(b"imagem,imagem\nx,y", "bad.csv")
    with pytest.raises(ValueError, match="JSON"):
        preview_import(b'{"metadata": {}}', "bad.json")


def test_save_failure_does_not_replace_existing_history(tmp_path, monkeypatch):
    old = legacy_row()
    save_import(preview([old]), json.dumps([old]).encode(), "old.json", tmp_path)
    before = (tmp_path / "historico.csv").read_bytes()
    import agrosmart.history as module
    original = module.os.replace
    def fail_on_history(src, dst):
        if Path(dst).name == "historico.csv":
            raise OSError("Falha simulada de disco")
        original(src, dst)
    monkeypatch.setattr(module.os, "replace", fail_on_history)
    with pytest.raises(OSError):
        save_import(preview([legacy_row(imagem="new.jpg")]), b"new", "new.json", tmp_path)
    assert (tmp_path / "historico.csv").read_bytes() == before


def test_global_rate_uses_records_not_average_of_plot_percentages():
    rows = [legacy_row(imagem="1", talhao="A"),
            legacy_row(imagem="2", talhao="A", categoria="saudavel", conf_saudavel=0.9, conf_doente=0.1),
            legacy_row(imagem="3", talhao="A", categoria="saudavel", conf_saudavel=0.9, conf_doente=0.1),
            legacy_row(imagem="4", talhao="B")]
    frame = preview(rows).rows
    metrics = summarize(frame)
    assert metrics["total"] == 4 and metrics["pct_doentes"] == 50
    plots = by_plot(frame).set_index("talhao")
    assert plots.loc["A", "percentual"] == pytest.approx(100/3)
    assert plots.loc["B", "percentual"] == 100


def test_filter_uses_local_calendar_and_no_records_is_not_zero_percent():
    frame = preview([legacy_row(data_hora="2026-09-01T01:00:00Z", talhao="A")]).rows
    result = select_records(frame, date(2026, 8, 31), date(2026, 8, 31), ["A"], ["doente"])
    assert len(result) == 1 and by_day(result).iloc[0]["dia"] == date(2026, 8, 31)
    empty = select_records(frame, date(2026, 9, 1), date(2026, 9, 1), ["A"], ["doente"])
    assert summarize(empty)["pct_doentes"] is None


def test_demo_has_360_events_and_additional_lot_is_disjoint():
    base, new = make_demo()
    assert len(base) == 360 and len(new) == 8
    assert len(set(base["id_analise"]) & set(new["id_analise"])) == 0
    assert set(base["origem_dado"]) == {"simulado"}
    again, _ = make_demo()
    pd.testing.assert_frame_equal(base, again)


def test_dashboard_filters_and_empty_state(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("AGROSMART_HISTORY_DIR", str(tmp_path))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert any(m.label == "Análises selecionadas" and m.value == "360" for m in app.metric)
    plot_widget = next(w for w in app.multiselect if w.label == "Talhões")
    plot_widget.set_value(["Talhão C"]).run()
    assert not app.exception
    assert any(m.label == "Análises selecionadas" and m.value == "90" for m in app.metric)
    next(w for w in app.multiselect if w.label == "Talhões").set_value([]).run()
    assert not app.exception
    assert any("Nenhum registro" in w.value for w in app.warning)


def test_dashboard_seed_import_refresh_and_duplicate_ui(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("AGROSMART_HISTORY_DIR", str(tmp_path))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.button(key="seed_history").click().run()
    app.radio(key="analytics_source").set_value("Histórico importado").run()
    assert len(load_history(tmp_path)) == 360
    assert not app.exception
    app.button(key="seed_history").click().run()
    assert len(load_history(tmp_path)) == 360
    assert any("0 adicionados, 360 repetidos" in x.value for x in app.success)
    extra = ROOT / "data" / "demo" / "lote_novo.csv"
    content = extra.read_bytes()
    save_import(preview_import(content, extra.name), content, extra.name, tmp_path)
    app.run()
    assert not app.exception
    assert any(m.label == "Análises selecionadas" and m.value == "368" for m in app.metric)


def test_upload_button_calls_import_flow(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    monkeypatch.setenv("AGROSMART_HISTORY_DIR", str(tmp_path))
    content = to_json([legacy_row()]).encode()
    uploaded = io.BytesIO(content)
    uploaded.name = "fase1.json"
    original = st.file_uploader
    def fake_uploader(*args, **kwargs):
        return uploaded if kwargs.get("key") == "history_upload" else original(*args, **kwargs)
    monkeypatch.setattr(st, "file_uploader", fake_uploader)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    app.button(key="save_history").click().run()
    assert not app.exception and len(load_history(tmp_path)) == 1
    app.button(key="save_history").click().run()
    assert len(load_history(tmp_path)) == 1
