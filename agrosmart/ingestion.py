"""Entrada incremental da Sprint 3, com checkpoint persistente em SQLite."""

import hashlib
import json
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path

import pandas as pd

from .history import (
    COLUMNS, ROOT, atomic_write, fingerprint, history_csv,
    load_history, preview_import,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS registros (
    id TEXT PRIMARY KEY, conteudo TEXT UNIQUE NOT NULL, dados TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY,
    arquivo TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    contextos TEXT NOT NULL,
    concluido INTEGER NOT NULL,
    UNIQUE(arquivo, sha256)
);
"""


def hash_bytes(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


class Ingestor:
    def __init__(self, diretorio=None):
        self.diretorio = Path(
            diretorio or ROOT / "data" / "sprint3" / "historico"
        )
        self.diretorio.mkdir(parents=True, exist_ok=True)
        self.csv = self.diretorio / "historico.csv"
        self.banco = self.diretorio / "estado.sqlite3"
        with closing(sqlite3.connect(self.banco)) as con:
            con.executescript(SCHEMA)

        with self.conexao() as con:
            pronto = con.execute(
                "SELECT valor FROM meta WHERE chave='inicializado'"
            ).fetchone()
            if not pronto:
                base = load_history(self.diretorio)
                if base.empty:
                    raise ValueError("Prepare o historico inicial antes do monitor.")
                self.inserir(con, base.to_dict("records"))
                con.executemany(
                    "INSERT INTO meta(chave, valor) VALUES (?, ?)",
                    [
                        ("inicializado", "1"),
                        ("ultimo_csv", hash_bytes(self.csv.read_bytes())),
                    ],
                )
        self.exportar_historico()

    @contextmanager
    def conexao(self):
        with closing(sqlite3.connect(self.banco, timeout=10)) as con:
            with con:
                con.execute("BEGIN IMMEDIATE")
                yield con

    @staticmethod
    def registros(con):
        return [
            json.loads(linha[0])
            for linha in con.execute("SELECT dados FROM registros ORDER BY rowid")
        ]

    @staticmethod
    def inserir(con, linhas):
        novos, repetidos = [], 0
        for original in linhas:
            linha = {
                chave: None if pd.isna(valor) else valor
                for chave, valor in original.items()
            }
            identidade = linha["id_analise"]
            conteudo = fingerprint(linha)
            existente = con.execute(
                "SELECT conteudo FROM registros WHERE id=?", (identidade,)
            ).fetchone()
            if existente and existente[0] != conteudo:
                raise ValueError(f"ID {identidade} possui conteudo conflitante.")
            duplicado = con.execute(
                "SELECT 1 FROM registros WHERE conteudo=?", (conteudo,)
            ).fetchone()
            if existente or duplicado:
                repetidos += 1
                continue
            con.execute(
                "INSERT INTO registros(id, conteudo, dados) VALUES (?, ?, ?)",
                (
                    identidade,
                    conteudo,
                    json.dumps(linha, ensure_ascii=False, allow_nan=False),
                ),
            )
            novos.append(linha)
        return novos, repetidos

    def exportar_historico(self):
        with self.conexao() as con:
            linhas = self.registros(con)
            conteudo = history_csv(pd.DataFrame(linhas, columns=COLUMNS))
            esperado = hash_bytes(conteudo)
            anterior = con.execute(
                "SELECT valor FROM meta WHERE chave='ultimo_csv'"
            ).fetchone()[0]
            atual = hash_bytes(self.csv.read_bytes()) if self.csv.exists() else ""
            if atual and atual not in {anterior, esperado}:
                raise ValueError(
                    "Historico alterado fora do monitor. Preserve o arquivo "
                    "e revise a alteracao antes de continuar."
                )
            if atual != esperado:
                atomic_write(self.csv, conteudo)
            con.execute(
                "UPDATE meta SET valor=? WHERE chave='ultimo_csv'", (esperado,)
            )

    def processar(self, arquivo):
        arquivo = Path(arquivo)
        conteudo = arquivo.read_bytes()
        previa = preview_import(conteudo, arquivo.name)
        if previa.errors:
            raise ValueError(
                f"Lote rejeitado: {len(previa.errors)} registro(s) invalido(s). "
                f"Primeiro motivo: {previa.errors[0]['motivo']}"
            )
        self.exportar_historico()
        digest = hash_bytes(conteudo)
        with self.conexao() as con:
            recebido = con.execute(
                "SELECT id FROM lotes WHERE arquivo=? AND sha256=?",
                (arquivo.name, digest),
            ).fetchone()
            if recebido:
                novos, repetidos = [], previa.received
            else:
                novos, repetidos = self.inserir(
                    con, previa.rows.to_dict("records")
                )
                historico = self.registros(con)
                contextos = []
                for talhao in sorted({r["talhao"] for r in novos}):
                    acumulados = [r for r in historico if r["talhao"] == talhao]
                    contextos.append({
                        "talhao": talhao,
                        "total": len(acumulados),
                        "doentes": sum(
                            r["categoria"] == "doente" for r in acumulados
                        ),
                        "confiancas_novas": [
                            r["confianca"] for r in novos if r["talhao"] == talhao
                        ],
                    })
                con.execute(
                    "INSERT INTO lotes(arquivo, sha256, contextos, concluido) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        arquivo.name, digest,
                        json.dumps(contextos, ensure_ascii=False),
                        int(not novos),
                    ),
                )
            total = con.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
        self.exportar_historico()
        return {
            "arquivo": arquivo.name,
            "recebidos": previa.received,
            "adicionados": len(novos),
            "duplicados": repetidos,
            "total_historico": total,
        }

    def pendentes(self):
        with self.conexao() as con:
            return [
                {"id": r[0], "arquivo": r[1], "contextos": json.loads(r[2])}
                for r in con.execute(
                    "SELECT id, arquivo, contextos FROM lotes "
                    "WHERE concluido=0 ORDER BY id"
                )
            ]


def main():
    from .actions import emitir_acoes

    entrada = ROOT / "data" / "sprint3" / "entrada"
    entrada.mkdir(parents=True, exist_ok=True)
    ingestor = Ingestor()
    anteriores, tratados = {}, {}
    print(f"Monitorando: {entrada}", flush=True)
    print("Intervalo: 2 segundos. Para encerrar: Ctrl+C.", flush=True)
    try:
        while True:
            for arquivo in sorted(entrada.iterdir()):
                if not arquivo.is_file() or arquivo.suffix.lower() not in {
                    ".csv", ".json"
                }:
                    continue
                try:
                    stat = arquivo.stat()
                except FileNotFoundError:
                    continue
                assinatura = (stat.st_size, stat.st_mtime_ns)
                if anteriores.get(arquivo) != assinatura:
                    anteriores[arquivo] = assinatura
                    continue
                if tratados.get(arquivo) == assinatura:
                    continue
                try:
                    resultado = ingestor.processar(arquivo)
                    print(json.dumps(resultado, ensure_ascii=True), flush=True)
                except (ValueError, OSError, sqlite3.Error) as erro:
                    print(f"ERRO {arquivo.name}: {erro}", flush=True)
                tratados[arquivo] = assinatura

            try:
                acoes = emitir_acoes(ingestor)
                if acoes["acoes_publicadas"]:
                    print(json.dumps({"acoes": acoes}), flush=True)
            except (ValueError, OSError, sqlite3.Error) as erro:
                print(f"ERRO ao publicar acoes: {erro}", flush=True)

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitor encerrado.", flush=True)


if __name__ == "__main__":
    main()