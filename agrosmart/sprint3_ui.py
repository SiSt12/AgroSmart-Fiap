"""Interface da entrada automatica e das acoes registradas na Sprint 3."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import streamlit as st

from .actions import MOTIVOS
from .history import ROOT, atomic_write, history_directory, preview_import


def enfileirar_arquivo(conteudo, nome, entrada):
    previa = preview_import(conteudo, nome)
    if previa.errors:
        raise ValueError("Corrija todos os registros inválidos antes de enviar.")
    extensao = Path(nome).suffix.lower()
    codigo = hashlib.sha256(conteudo).hexdigest()
    destino = Path(entrada) / f"upload_{codigo}{extensao}"
    atomic_write(destino, conteudo)
    return destino


def ler_estado(diretorio):
    banco = Path(diretorio) / "estado.sqlite3"
    if not banco.exists():
        return {"acoes": [], "lotes_pendentes": 0}
    with closing(sqlite3.connect(banco.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        con.execute("BEGIN")
        tabelas = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        pendentes = (
            con.execute("SELECT COUNT(*) FROM lotes WHERE concluido=0").fetchone()[0]
            if "lotes" in tabelas else 0
        )
        acoes = []
        if "acoes" in tabelas:
            for dados, exportado in con.execute(
                "SELECT dados, exportado FROM acoes ORDER BY id"
            ):
                acao = json.loads(dados)
                acao["exportado"] = bool(exportado)
                acoes.append(acao)
    return {"acoes": acoes, "lotes_pendentes": pendentes}


def render_upload(entrada=None):
    entrada = Path(entrada or history_directory().parent / "entrada")
    st.subheader("Enviar dados para processamento automático")
    st.write("Confira o arquivo e envie. O monitor incorporará apenas os registros novos.")
    st.caption("O monitor deve estar rodando no terminal para processar a entrada.")
    uploaded = st.file_uploader(
        "Resultados em CSV ou JSON",
        type=["csv", "json"],
        key="sprint3_upload",
        help="UTF-8; até 10 MB. Formatos das fases anteriores continuam aceitos.",
    )
    if uploaded is None:
        st.info("Selecione um arquivo para conferir a prévia.")
        return
    try:
        conteudo = uploaded.getvalue()
        previa = preview_import(conteudo, uploaded.name)
        st.write(
            f"{previa.received} recebidos | {len(previa.rows)} válidos | "
            f"{len(previa.errors)} inválidos"
        )
        if previa.errors:
            st.error("O lote inteiro será rejeitado. Corrija os registros indicados.")
            st.dataframe(
                pd.DataFrame(previa.errors), hide_index=True, use_container_width=True
            )
            return
        st.dataframe(
            previa.rows.head(20), hide_index=True, use_container_width=True
        )
        st.caption("Prévia de até 20 registros; repetições são verificadas pelo monitor.")
        if st.button("Enviar para entrada automática", key="s3_send", type="primary"):
            enfileirar_arquivo(conteudo, uploaded.name, entrada)
            st.success(
                "Arquivo enviado para a entrada. Aguarde o monitor e clique "
                "em Atualizar painel no Dashboard para conferir o resultado."
            )
    except (ValueError, OSError) as erro:
        st.error(str(erro))


def render_actions(diretorio=None, saida=None):
    diretorio = Path(diretorio or history_directory())
    saida = Path(saida or ROOT / "outputs" / "sprint3")
    st.subheader("Ações automáticas no campo")
    st.caption(
        "Ações simuladas por talhão, calculadas sobre o histórico acumulado. "
        "Os filtros dos gráficos não alteram as regras."
    )
    st.button("Atualizar painel", key="s3_refresh")
    try:
        estado = ler_estado(diretorio)
    except (sqlite3.Error, ValueError, OSError) as erro:
        st.error(f"Não foi possível consultar as ações: {erro}")
        return
    acoes = estado["acoes"]
    cards = st.columns(3)
    cards[0].metric("Alertas registrados", sum(a["tipo"] == "alerta" for a in acoes))
    cards[1].metric("Relatórios registrados", sum(a["tipo"] == "relatorio" for a in acoes))
    cards[2].metric("Ações aguardando gravação", sum(not a["exportado"] for a in acoes))
    if estado["lotes_pendentes"]:
        st.info(f"{estado['lotes_pendentes']} lote(s) aguardando avaliação das regras.")
    st.caption("Mantenha o monitor rodando durante a chegada de novos arquivos.")
    if not acoes:
        st.info("Nenhuma ação registrada. Envie novos dados com o monitor em execução.")
        return

    esquerda, direita = st.columns(2)
    tipo = esquerda.selectbox(
        "Tipo de ação", ["Todos", "Alerta", "Relatório"], key="s3_tipo"
    )
    talhao = direita.selectbox(
        "Talhão da ação",
        ["Todos"] + sorted({a["talhao"] for a in acoes}),
        key="s3_talhao",
    )
    filtradas = [
        a for a in acoes
        if (
            tipo == "Todos"
            or a["tipo"] == {"Alerta": "alerta", "Relatório": "relatorio"}.get(tipo)
        )
        and (talhao == "Todos" or a["talhao"] == talhao)
    ]
    if not filtradas:
        st.warning("Nenhuma ação corresponde aos filtros selecionados.")
        return
    st.dataframe(
        pd.DataFrame([
            {
                "Talhão": a["talhao"],
                "Tipo": "Alerta" if a["tipo"] == "alerta" else "Relatório",
                "Regra": a["regra"],
                "Doentes / total": f"{a['doentes']} / {a['total']}",
                "Doentes (%)": round(a["percentual_doentes"], 2),
                "Status": "Gravada" if a["exportado"] else "Aguardando gravação",
            }
            for a in filtradas
        ]),
        hide_index=True,
        use_container_width=True,
    )
    por_id = {a["id"]: a for a in filtradas}
    escolhido = st.selectbox(
        "Detalhar ação",
        list(por_id),
        format_func=lambda identidade: (
            f"Lote {por_id[identidade]['lote_id']} | "
            f"{por_id[identidade]['talhao']} | {por_id[identidade]['regra']}"
        ),
        key="s3_detalhe",
    )
    acao = por_id[escolhido]
    st.write("**Recomendação:**", acao["recomendacao"])
    for motivo in acao["motivos"]:
        st.write("- " + MOTIVOS.get(motivo, motivo))
    st.caption(f"Origem: {acao['arquivo_origem']} | Gerada em UTC: {acao['gerado_em']}")
    st.download_button(
        "Baixar JSON da ação",
        json.dumps(acao, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{acao['id']}.json",
        mime="application/json",
        key="s3_download_json",
    )
    if acao["tipo"] == "relatorio":
        arquivo = saida / "relatorios" / f"{acao['id']}.txt"
        if arquivo.exists():
            st.download_button(
                "Baixar relatório TXT", arquivo.read_bytes(),
                file_name=arquivo.name, mime="text/plain",
                key="s3_download_txt",
            )
        else:
            st.info("O TXT ainda não está disponível. Confira o monitor.")