"""Indicadores calculados somente sobre as análises selecionadas."""
from __future__ import annotations

import pandas as pd

DISPLAY_TIMEZONE = "America/Sao_Paulo"


def with_dates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["momento"] = pd.to_datetime(result["data_hora"], utc=True).dt.tz_convert(DISPLAY_TIMEZONE)
    result["dia"] = result["momento"].dt.date
    return result


def select_records(frame: pd.DataFrame, start, end, plots, categories) -> pd.DataFrame:
    dated = with_dates(frame)
    return dated.loc[(dated["dia"] >= start) & (dated["dia"] <= end)
                     & dated["talhao"].isin(plots) & dated["categoria"].isin(categories)].copy()


def summarize(frame: pd.DataFrame) -> dict:
    total = len(frame)
    sick = int((frame["categoria"] == "doente").sum())
    healthy = int((frame["categoria"] == "saudavel").sum())
    return {"total": total, "doentes": sick, "saudaveis": healthy,
            "pct_doentes": 100 * sick / total if total else None,
            "pct_saudaveis": 100 * healthy / total if total else None,
            "confianca_media": float(frame["confianca"].mean()) if total else None}


def by_plot(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.assign(doente=frame["categoria"].eq("doente").astype(int))
    result = data.groupby("talhao").agg(total=("categoria", "size"), doentes=("doente", "sum")).reset_index()
    result["percentual"] = result["doentes"] / result["total"] * 100
    return result.sort_values(["percentual", "total", "talhao"], ascending=[False, False, True])


def by_day(frame: pd.DataFrame) -> pd.DataFrame:
    data = with_dates(frame)
    data["doente"] = data["categoria"].eq("doente").astype(int)
    result = data.groupby("dia").agg(total=("categoria", "size"), doentes=("doente", "sum")).reset_index()
    result["percentual"] = result["doentes"] / result["total"] * 100
    return result
