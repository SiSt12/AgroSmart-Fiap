"""Gera registros tabulares sintéticos para demonstrar a Sprint 2.

Não executa o SVM, não cria fotos e não estima desempenho do classificador.
Execução: python -m agrosmart.demo_history
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

import pandas as pd

from .history import COLUMNS, ROOT, history_csv, history_json, normalize_row


def make_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = Random(42)
    start = datetime(2026, 8, 24, 9, tzinfo=timezone(timedelta(hours=-3)))
    rows = []
    for day in range(30):
        for plot in "ABCD":
            probability_sick = {"A": 0.12, "B": 0.28, "C": 0.30 + day / 60, "D": 0.18}[plot]
            for sample in range(3):
                confidence = round(rng.uniform(0.60, 0.99), 4)
                category = "doente" if rng.random() < probability_sick else "saudavel"
                number = len(rows) + 1
                rows.append(normalize_row({
                    "id_analise": f"demo-{number:04}", "imagem": f"simulada_{number:04}.jpg",
                    "data_hora": (start + timedelta(days=day, minutes=sample*15)).isoformat(),
                    "categoria": category, "confianca": confidence,
                    "conf_saudavel": confidence if category == "saudavel" else round(1-confidence, 4),
                    "conf_doente": confidence if category == "doente" else round(1-confidence, 4),
                    "talhao": f"Talhão {plot}", "origem_dado": "simulado"}))
    new_rows = []
    for number, plot in enumerate("AABBCCDD", 1):
        category = "doente" if plot == "C" or number == 3 else "saudavel"
        new_rows.append(normalize_row({
            "id_analise": f"demo-novo-{number:02}", "imagem": f"simulada_nova_{number:02}.jpg",
            "data_hora": (start + timedelta(days=30, minutes=number*10)).isoformat(),
            "categoria": category, "confianca": 0.9,
            "conf_saudavel": 0.9 if category == "saudavel" else 0.1,
            "conf_doente": 0.9 if category == "doente" else 0.1,
            "talhao": f"Talhão {plot}", "origem_dado": "simulado"}))
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(new_rows, columns=COLUMNS)


def generate(destination: Path | None = None) -> None:
    destination = destination or ROOT / "data" / "demo"
    destination.mkdir(parents=True, exist_ok=True)
    history, new = make_demo()
    (destination / "historico_demo.csv").write_bytes(history_csv(history))
    (destination / "lote_novo.csv").write_bytes(history_csv(new))
    (destination / "lote_novo.json").write_bytes(history_json(new))
    print(f"Gerados {len(history)} registros e lote adicional de {len(new)} em {destination}.")


if __name__ == "__main__":
    generate()
