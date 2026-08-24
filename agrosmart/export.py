"""Exportacao dos resultados da classificacao em CSV e JSON (item 1.2)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from . import CLASSES, __version__

# Colunas exigidas pela atividade: nome da imagem, categoria e acuracia.
# As colunas de confianca por classe e a data_hora sao complemento de auditoria.
COLUNAS = (["imagem", "categoria", "acuracia"]
           + [f"conf_{c}" for c in CLASSES]
           + ["data_hora"])


def build_row(nome_imagem: str, resultado: dict,
              quando: datetime | None = None) -> dict:
    """Converte a saida de model.predict em uma linha do relatorio."""
    quando = quando or datetime.now().astimezone()
    linha = {
        "imagem": nome_imagem,
        "categoria": resultado["categoria"],
        "acuracia": round(float(resultado["confianca"]), 4),
        "data_hora": quando.isoformat(timespec="seconds"),
    }
    for classe in CLASSES:
        linha[f"conf_{classe}"] = round(
            float(resultado["probabilidades"].get(classe, 0.0)), 4
        )
    return {coluna: linha[coluna] for coluna in COLUNAS}


def to_csv(linhas: list[dict]) -> str:
    """Serializa as linhas em CSV (mesma fonte usada pelo download do app)."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUNAS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(linhas)
    return buffer.getvalue()


def to_json(linhas: list[dict], metricas: dict | None = None) -> str:
    """Serializa as linhas em JSON, com um bloco de metadados do lote."""
    resumo: dict[str, int] = {}
    for linha in linhas:
        resumo[linha["categoria"]] = resumo.get(linha["categoria"], 0) + 1
    documento = {
        "metadata": {
            "aplicacao": "AgroSmart-Fiap",
            "versao": __version__,
            "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
            "total_imagens": len(linhas),
            "resumo_por_categoria": resumo,
            "modelo": "StandardScaler + SVC(rbf) sobre atributos HSV/textura",
            "acuracia_validacao": (metricas or {}).get("acuracia_holdout"),
        },
        "resultados": linhas,
    }
    return json.dumps(documento, indent=2, ensure_ascii=False)


def export_results(linhas: list[dict], out_dir: str | Path,
                   basename: str | None = None,
                   metricas: dict | None = None) -> dict[str, Path]:
    """Grava CSV e JSON em disco e devolve os caminhos criados."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    basename = basename or f"resultados_{datetime.now():%Y%m%d_%H%M%S}"

    caminho_csv = out_dir / f"{basename}.csv"
    caminho_json = out_dir / f"{basename}.json"
    # utf-8-sig para o Excel abrir os acentos corretamente no Windows.
    caminho_csv.write_text(to_csv(linhas), encoding="utf-8-sig")
    caminho_json.write_text(to_json(linhas, metricas), encoding="utf-8")
    return {"csv": caminho_csv, "json": caminho_json}
