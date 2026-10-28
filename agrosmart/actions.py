"""Acoes simuladas da Sprint 3, persistidas antes da exportacao."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .history import ROOT, atomic_write
from .rules import avaliar_regras

MOTIVOS = {
    "mais_de_30_porcento_doentes": "Mais de 30% das analises classificadas doentes.",
    "mais_de_50_porcento_doentes": "Mais de 50% das analises classificadas doentes.",
    "baixa_confianca": "Confianca media das novas classificacoes abaixo de 65%.",
}


def recomendacao(tipo, motivos):
    if tipo == "alerta":
        return "Inspecionar o talhao e registrar as observacoes."
    if "baixa_confianca" in motivos:
        if "mais_de_50_porcento_doentes" in motivos:
            return "Priorizar a inspecao do talhao e revisar as classificacoes."
        return "Revisar manualmente as classificacoes antes de decidir uma intervencao."
    return "Priorizar a inspecao do talhao e registrar as observacoes."


def texto_relatorio(acao):
    motivos = "\n".join("- " + MOTIVOS[m] for m in acao["motivos"])
    return (
        "AGROSMART - RELATORIO SIMULADO - SPRINT 3\n\n"
        f"ID: {acao['id']}\n"
        f"Gerado em UTC: {acao['gerado_em']}\n"
        f"Arquivo de origem: {acao['arquivo_origem']}\n"
        f"Talhao: {acao['talhao']}\n"
        f"Analises acumuladas: {acao['total']}\n"
        f"Classificadas doentes: {acao['doentes']}\n"
        f"Percentual doente: {acao['percentual_doentes']:.2f}%\n"
        f"Confianca media das novas: {acao['confianca_media_novos']:.2%}\n\n"
        f"Motivos:\n{motivos}\n\n"
        f"Recomendacao: {acao['recomendacao']}\n\n"
        "Acao simulada para demonstracao academica.\n"
    )


def emitir_acoes(ingestor, destino=None):
    destino = Path(destino or ROOT / "outputs" / "sprint3")
    contagem = {"alertas_novos": 0, "relatorios_novos": 0, "acoes_publicadas": 0}

    with ingestor.conexao() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS acoes ("
            "id TEXT PRIMARY KEY, dados TEXT NOT NULL, "
            "exportado INTEGER NOT NULL DEFAULT 0)"
        )
        lotes = con.execute(
            "SELECT id, arquivo, contextos FROM lotes "
            "WHERE concluido=0 ORDER BY id"
        ).fetchall()
        for lote_id, arquivo, contextos in lotes:
            for contexto in json.loads(contextos):
                decisao = avaliar_regras(
                    contexto["total"],
                    contexto["doentes"],
                    contexto["confiancas_novas"],
                )
                for regra, tipo, ativa in [
                    ("R1", "alerta", decisao["alerta"]),
                    ("R2", "relatorio", decisao["relatorio"]),
                ]:
                    if not ativa:
                        continue
                    talhao = contexto["talhao"]
                    codigo = hashlib.sha256(talhao.encode("utf-8")).hexdigest()[:12]
                    identidade = f"lote_{lote_id:06d}_{codigo}_{regra}"
                    motivos = (
                        ["mais_de_30_porcento_doentes"]
                        if regra == "R1" else decisao["motivos"]
                    )
                    acao = {
                        "id": identidade,
                        "lote_id": lote_id,
                        "arquivo_origem": arquivo,
                        "regra": regra,
                        "tipo": tipo,
                        "talhao": talhao,
                        "total": contexto["total"],
                        "doentes": contexto["doentes"],
                        "percentual_doentes": decisao["percentual_doentes"],
                        "confianca_media_novos": decisao["confianca_media_novos"],
                        "motivos": motivos,
                        "recomendacao": recomendacao(tipo, motivos),
                        "gerado_em": datetime.now(timezone.utc).isoformat(
                            timespec="seconds"
                        ),
                        "acao_simulada": True,
                    }
                    insercao = con.execute(
                        "INSERT OR IGNORE INTO acoes(id, dados) VALUES (?, ?)",
                        (identidade, json.dumps(acao, ensure_ascii=False)),
                    )
                    if insercao.rowcount:
                        chave = "alertas_novos" if regra == "R1" else "relatorios_novos"
                        contagem[chave] += 1
            con.execute("UPDATE lotes SET concluido=1 WHERE id=?", (lote_id,))

        publicacoes = con.execute(
            "SELECT id, dados FROM acoes WHERE exportado=0 ORDER BY id"
        ).fetchall()

    for identidade, dados in publicacoes:
        acao = json.loads(dados)
        pasta = destino / ("alertas" if acao["tipo"] == "alerta" else "relatorios")
        atomic_write(pasta / f"{identidade}.json", dados.encode("utf-8"))
        if acao["tipo"] == "relatorio":
            atomic_write(
                pasta / f"{identidade}.txt",
                texto_relatorio(acao).encode("utf-8"),
            )
        with ingestor.conexao() as con:
            con.execute("UPDATE acoes SET exportado=1 WHERE id=?", (identidade,))
        contagem["acoes_publicadas"] += 1

    return contagem