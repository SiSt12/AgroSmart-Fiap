"""Importação e persistência do histórico analítico da Sprint 2.

CSV e JSON legados continuam aceitos. A coluna legada 'acuracia' é tratada
como confiança; nunca como uma avaliação de acertos do modelo.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import tempfile
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ["id_analise", "imagem", "data_hora", "categoria", "confianca",
           "conf_saudavel", "conf_doente", "talhao", "origem_dado"]
ORIGINS = {"simulado", "nao_informada", "real_informado"}
LOCK = threading.RLock()


@dataclass
class ImportPreview:
    rows: pd.DataFrame
    errors: list[dict]
    received: int


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def history_directory() -> Path:
    configurado = os.environ.get("AGROSMART_HISTORY_DIR")
    if configurado:
        return Path(configurado)
    sprint3 = ROOT / "data" / "sprint3" / "historico"
    if (sprint3 / "estado.sqlite3").exists():
        return sprint3
    return ROOT / "data" / "history"


def plain(value) -> str:
    return "" if value is None else str(value).strip()


def normalize_word(value) -> str:
    text = unicodedata.normalize("NFKD", plain(value).lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def probability(value, label: str) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError
        n = float(value)
        if not math.isfinite(n) or not 0 <= n <= 1:
            raise ValueError
        return round(n, 6)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: informe um número entre 0 e 1.") from None


def normalize_row(row: dict, default_plot="Não informado", default_origin="nao_informada") -> dict:
    if not isinstance(row, dict):
        raise ValueError("O registro precisa ser um objeto com colunas nomeadas.")
    image = plain(row.get("imagem"))
    if not image or len(image) > 255:
        raise ValueError("imagem: nome ausente ou maior que 255 caracteres.")
    category = normalize_word(row.get("categoria"))
    if category not in {"saudavel", "doente"}:
        raise ValueError("categoria: use saudavel ou doente.")
    confidence = probability(row.get("confianca", row.get("acuracia")), "confianca")
    if "confianca" in row and "acuracia" in row:
        legacy = probability(row["acuracia"], "acuracia legada")
        if not math.isclose(confidence, legacy, abs_tol=0.0002):
            raise ValueError("confianca e acuracia legada têm valores diferentes.")
    try:
        stamp = datetime.fromisoformat(plain(row.get("data_hora")).replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        stamp = stamp.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, OverflowError):
        raise ValueError("data_hora: use ISO 8601 com fuso, ex.: 2026-09-01T09:00:00-03:00.") from None
    plot = plain(row.get("talhao")) or plain(default_plot) or "Não informado"
    origin = normalize_word(row.get("origem_dado")) or default_origin
    if len(plot) > 100:
        raise ValueError("talhao: máximo de 100 caracteres.")
    if origin not in ORIGINS:
        raise ValueError("origem_dado: use simulado, nao_informada ou real_informado.")
    healthy = row.get("conf_saudavel")
    sick = row.get("conf_doente")
    has_h = healthy is not None and plain(healthy) != ""
    has_s = sick is not None and plain(sick) != ""
    if has_h != has_s:
        raise ValueError("Informe as duas probabilidades por classe ou deixe ambas vazias.")
    if has_h:
        healthy = probability(healthy, "conf_saudavel")
        sick = probability(sick, "conf_doente")
        chosen = healthy if category == "saudavel" else sick
        if not math.isclose(healthy + sick, 1.0, abs_tol=0.0002):
            raise ValueError("As probabilidades das duas classes devem somar 1.")
        if not math.isclose(chosen, confidence, abs_tol=0.0002):
            raise ValueError("A confiança deve corresponder à probabilidade da categoria.")
    else:
        healthy = sick = None
    result = dict(imagem=image, data_hora=stamp, categoria=category,
                  confianca=confidence, conf_saudavel=healthy, conf_doente=sick,
                  talhao=plot, origem_dado=origin)
    provided_id = plain(row.get("id_analise"))
    if len(provided_id) > 128:
        raise ValueError("id_analise: máximo de 128 caracteres.")
    result["id_analise"] = provided_id or "auto_" + fingerprint(result)[:24]
    return {key: result[key] for key in COLUMNS}


def fingerprint(row: dict) -> str:
    """Mesmo evento/conteúdo, independente do arquivo CSV/JSON de transporte."""
    payload = {key: row.get(key) for key in COLUMNS if key != "id_analise"}
    for key in ("confianca", "conf_saudavel", "conf_doente"):
        value = payload[key]
        payload[key] = None if pd.isna(value) else round(float(value), 6)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def preview_import(content: bytes, filename: str, default_plot="Não informado",
                   default_origin="nao_informada") -> ImportPreview:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Use um arquivo de até 10 MB por importação.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("O arquivo precisa estar em UTF-8 (com ou sem BOM).") from None
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".json":
            document = json.loads(text)
            records = document.get("resultados") if isinstance(document, dict) else document
            if not isinstance(records, list):
                raise ValueError("JSON: use uma lista de registros ou um objeto com resultados.")
        elif suffix == ".csv":
            first_line = text.splitlines()[0] if text.splitlines() else ""
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("CSV sem cabeçalho válido ou com colunas repetidas.")
            records = list(reader)
        else:
            raise ValueError("Formato aceito: CSV ou JSON.")
    except (json.JSONDecodeError, csv.Error) as error:
        raise ValueError(f"Não foi possível ler o arquivo: {error}") from None
    if not records:
        raise ValueError("O arquivo não possui registros.")
    if len(records) > 50000:
        raise ValueError("Use até 50.000 registros por arquivo.")
    valid, errors = [], []
    for i, record in enumerate(records, 1):
        try:
            if isinstance(record, dict) and None in record:
                raise ValueError("Linha com mais campos que o cabeçalho CSV.")
            valid.append(normalize_row(record, default_plot, default_origin))
        except (ValueError, TypeError) as error:
            errors.append({"registro": i, "motivo": str(error)})
    return ImportPreview(pd.DataFrame(valid, columns=COLUMNS), errors, len(records))


def load_history(directory: Path | None = None) -> pd.DataFrame:
    path = (directory or history_directory()) / "historico.csv"
    if not path.exists():
        return empty_history()
    preview = preview_import(path.read_bytes(), path.name)
    if preview.errors:
        raise ValueError("O histórico contém registros inválidos; preserve o arquivo e revise os dados.")
    return preview.rows


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".agrosmart-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def history_csv(frame: pd.DataFrame) -> bytes:
    return frame[COLUMNS].to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def history_json(frame: pd.DataFrame) -> bytes:
    rows = json.loads(frame[COLUMNS].to_json(orient="records", force_ascii=False))
    return json.dumps({"metadata": {"aplicacao": "AgroSmart Sprint 3",
                       "total_registros": len(frame),
                       "nota": "confianca não é acurácia de validação; origem_dado acompanha cada registro"},
                       "resultados": rows}, ensure_ascii=False, indent=2).encode("utf-8")


def save_import(preview: ImportPreview, content: bytes, filename: str,
                directory: Path | None = None) -> dict:
    """Carga incremental idempotente em um servidor local; não altera eventos antigos.

    Linhas inválidas são excluídas na prévia. IDs conflitantes abortam a carga,
    evitando alteração silenciosa de um evento existente.
    """
    directory = directory or history_directory()
    with LOCK:
        current = load_history(directory)
        by_id = {r["id_analise"]: fingerprint(r) for r in current.to_dict("records")}
        contents = set(by_id.values())
        additions, duplicates = [], 0
        for row in preview.rows.to_dict("records"):
            digest = fingerprint(row)
            record_id = row["id_analise"]
            if record_id in by_id and by_id[record_id] != digest:
                raise ValueError(f"ID {record_id} já existe com conteúdo diferente; lote não gravado.")
            if record_id in by_id or digest in contents:
                duplicates += 1
                continue
            by_id[record_id] = digest
            contents.add(digest)
            additions.append(row)
        if additions:
            added_frame = pd.DataFrame(additions, columns=COLUMNS)
            consolidated = added_frame if current.empty else pd.concat([current, added_frame], ignore_index=True)
            raw_name = hashlib.sha256(content).hexdigest() + Path(filename).suffix.lower()
            atomic_write(directory / "raw" / raw_name, content)
            atomic_write(directory / "historico.csv", history_csv(consolidated))
        return {"recebidos": preview.received, "adicionados": len(additions),
                "duplicados": duplicates, "invalidos": len(preview.errors),
                "total_historico": len(current) + len(additions)}
