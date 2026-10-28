"""Interface analítica e importação de arquivos da Sprint 2."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .analytics import by_day, by_plot, select_records, summarize, with_dates
from .history import (ROOT, history_csv, history_directory, history_json, load_history,
                      preview_import, save_import)

DEMO_PATH = ROOT / "data" / "demo" / "historico_demo.csv"
COLORS = ["#17845D", "#CC634A"]
ORIGIN_LABELS = {"simulado": "Simulado", "nao_informada": "Origem não informada",
                 "real_informado": "Real, conforme informado no arquivo/importação"}


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def percent(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def demo_frame() -> pd.DataFrame:
    return preview_import(DEMO_PATH.read_bytes(), DEMO_PATH.name).rows


def import_panel() -> None:
    if (history_directory() / "estado.sqlite3").exists():
        from .sprint3_ui import render_upload
        render_upload()
        return
    st.subheader("Atualizar o histórico")
    st.write("Importe resultados em CSV ou JSON. Confira a prévia antes de gravar os registros válidos.")
    with st.expander("Começar com o exemplo da atividade"):
        st.write("Copie os 360 registros simulados para o seu histórico. Depois importe o lote adicional de 8 registros para demonstrar a atualização.")
        if st.button("Adicionar demonstração ao histórico", key="seed_history"):
            try:
                content = DEMO_PATH.read_bytes()
                result = save_import(preview_import(content, DEMO_PATH.name), content, DEMO_PATH.name)
                st.session_state["last_import_result"] = result
                st.rerun()
            except (ValueError, OSError) as error:
                st.error(str(error))
        new = ROOT / "data" / "demo" / "lote_novo.csv"
        st.download_button("Baixar lote adicional de exemplo", new.read_bytes(),
                           file_name="lote_novo.csv", mime="text/csv", key="download_demo_lot")

    uploaded = st.file_uploader("Resultados da classificação ou base simulada", type=["csv", "json"],
                                key="history_upload", help="UTF-8; até 10 MB. CSV da Fase 1 e JSON com metadata/resultados são aceitos.")
    left, right = st.columns(2)
    with left:
        plot = st.text_input("Talhão para registros sem localização", value="Não informado", key="default_plot")
    with right:
        origin = st.selectbox("Origem para registros sem essa informação", list(ORIGIN_LABELS),
                              index=1, format_func=lambda x: ORIGIN_LABELS[x], key="default_origin")
    st.caption("Os valores acima preenchem somente campos ausentes. A origem não é verificada automaticamente.")
    if uploaded is not None:
        try:
            content = uploaded.getvalue()
            preview = preview_import(content, uploaded.name, plot, origin)
            st.write(f"**{preview.received} recebidos · {len(preview.rows)} válidos · {len(preview.errors)} inválidos**")
            if preview.errors:
                st.warning("Os registros abaixo serão excluídos desta importação. Corrija o arquivo se precisar incluí-los.")
                st.dataframe(pd.DataFrame(preview.errors), hide_index=True, use_container_width=True)
            if not preview.rows.empty:
                st.dataframe(preview.rows.head(20), hide_index=True, use_container_width=True)
                st.caption("Prévia de até 20 registros. Repetições e conflitos de ID são verificados ao gravar.")
                if st.button("Gravar registros válidos", type="primary", key="save_history"):
                    result = save_import(preview, content, uploaded.name)
                    st.session_state["last_import_result"] = result
                    st.rerun()
        except (ValueError, OSError) as error:
            st.error(str(error))
    result = st.session_state.get("last_import_result")
    if result:
        st.success(f"Última importação: {result['adicionados']} adicionados, {result['duplicados']} repetidos e {result['invalidos']} inválidos. Histórico com {result['total_historico']} registros.")


def render_dashboard() -> None:
    st.subheader("Uma visão das análises do campo")
    st.write("Compare períodos e talhões para escolher onde concentrar a próxima inspeção.")
    try:
        history = load_history()
        demo = demo_frame()
    except (ValueError, OSError) as error:
        st.error(f"Não foi possível carregar a base: {error}")
        return
    source = st.radio(
        "Base de análise",
        ["Demonstração simulada", "Histórico importado"],
        horizontal=True,
        index=1 if (history_directory() / "estado.sqlite3").exists() else 0,
        key="analytics_source",
    )
    data = demo if source == "Demonstração simulada" else history
    if source == "Demonstração simulada":
        st.info("Demonstração: registros tabulares fictícios, com datas e talhões simulados. Não representam coletas reais nem resultados medidos do SVM.")
    else:
        st.caption("Histórico salvo neste computador. A classificação é uma triagem; a origem de cada registro acompanha os dados.")
        target = history_directory() / "historico.csv"
        if target.exists():
            updated = pd.Timestamp(target.stat().st_mtime, unit="s", tz="UTC").tz_convert("America/Sao_Paulo")
            st.caption(f"Última atualização da base: {updated:%d/%m/%Y %H:%M} (Brasília)")
    if data.empty:
        st.info("Seu histórico ainda está vazio. Abra Atualizar dados para importar os resultados ou adicionar a demonstração.")
        return
    dated = with_dates(data)
    source_key = "demo" if source == "Demonstração simulada" else "history"
    # Nova importação amplia a seleção padrão do período para incluir o novo lote.
    signature = f"{source_key}_{len(data)}_{dated['dia'].max()}"
    a, b, c = st.columns([1.4, 1.2, 1.2])
    with a:
        period = st.date_input("Período das análises", value=(dated["dia"].min(), dated["dia"].max()),
                               min_value=dated["dia"].min(), max_value=dated["dia"].max(), key=f"period_{signature}")
    with b:
        options = sorted(data["talhao"].unique())
        plots = st.multiselect("Talhões", options, default=options, key=f"plots_{signature}")
    with c:
        categories = st.multiselect("Categorias", ["saudavel", "doente"], default=["saudavel", "doente"],
                                    format_func=lambda x: "Saudável" if x == "saudavel" else "Doente",
                                    key=f"categories_{signature}")
    if len(period) != 2:
        st.info("Selecione também a data final do período.")
        return
    selected = select_records(data, period[0], period[1], plots, categories)
    if selected.empty:
        st.warning("Nenhum registro corresponde aos filtros. Amplie o período ou selecione talhões e categorias.")
        return
    kpi = summarize(selected)
    cards = st.columns(4)
    cards[0].metric("Análises selecionadas", number(kpi["total"]))
    cards[1].metric("Classificadas saudáveis", percent(kpi["pct_saudaveis"]), help=f"{kpi['saudaveis']} registros")
    cards[2].metric("Classificadas doentes", percent(kpi["pct_doentes"]), help=f"{kpi['doentes']} registros")
    cards[3].metric("Confiança média", percent(kpi["confianca_media"] * 100), help="Média da confiança declarada nas previsões; não é acurácia de validação.")
    st.caption("Todos os percentuais usam os registros selecionados como denominador. Para comparar a proporção de doentes, mantenha as duas categorias selecionadas.")
    st.caption("As medidas descrevem as análises disponíveis; não estimam, por si só, a condição de toda a plantação.")

    left, right = st.columns([1, 1.5])
    with left:
        st.markdown("#### Distribuição das classificações")
        counts = pd.DataFrame({"categoria": ["Saudável", "Doente"], "quantidade": [kpi["saudaveis"], kpi["doentes"]]})
        chart = alt.Chart(counts).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X("categoria:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("quantidade:Q", title="Análises", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("categoria:N", scale=alt.Scale(domain=["Saudável", "Doente"], range=COLORS), legend=None),
            tooltip=[alt.Tooltip("categoria:N", title="Categoria"), alt.Tooltip("quantidade:Q", title="Análises")]).properties(height=230)
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.markdown("#### Percentual classificado como doente por talhão")
        locations = by_plot(selected)
        chart = alt.Chart(locations).mark_bar(color=COLORS[1], cornerRadiusEnd=4).encode(
            y=alt.Y("talhao:N", title=None, sort="-x"),
            x=alt.X("percentual:Q", title="Percentual (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("talhao:N", title="Talhão"), alt.Tooltip("total:Q", title="Total analisado"),
                     alt.Tooltip("doentes:Q", title="Classificadas doentes"), alt.Tooltip("percentual:Q", title="Percentual", format=".1f")]).properties(height=230)
        st.altair_chart(chart, use_container_width=True)
    st.markdown("#### Evolução diária das classificações")
    daily = by_day(selected)
    daily["dia"] = pd.to_datetime(daily["dia"])
    # Datas ausentes interrompem a linha, em vez de representar ausência de coleta como zero.
    timeline = daily.set_index("dia").reindex(pd.date_range(daily["dia"].min(), daily["dia"].max(), freq="D")).rename_axis("dia").reset_index()
    chart = alt.Chart(timeline).mark_line(point=True, color="#17845D", invalid="break-paths-show-domains").encode(
        x=alt.X("dia:T", title="Data da análise (Brasília)", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("percentual:Q", title="Classificadas doentes (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("dia:T", title="Data", format="%d/%m/%Y"), alt.Tooltip("total:Q", title="Análises no dia"),
                 alt.Tooltip("doentes:Q", title="Doentes"), alt.Tooltip("percentual:Q", title="Percentual", format=".1f")]).properties(height=230)
    st.altair_chart(chart, use_container_width=True)
    st.caption("Dias sem análises não recebem percentual zero. A linha descreve o histórico selecionado, sem prever resultados futuros.")

    st.markdown("#### Leitura dos resultados")
    if set(categories) == {"saudavel", "doente"}:
        top = locations.iloc[0]
        if int(top["doentes"]) > 0:
            tied = locations.loc[locations["percentual"].eq(top["percentual"]), "talhao"].tolist()
            if len(tied) == 1:
                st.write(f"**{top['talhao']}** tem a maior proporção neste recorte: **{percent(top['percentual'])}** ({int(top['doentes'])} de {int(top['total'])} análises). Esse resultado pode orientar uma inspeção prioritária, considerando o tamanho da amostra.")
            else:
                st.write(f"Há empate na maior proporção ({percent(top['percentual'])}) entre: {', '.join(tied)}. Confira também o número de análises de cada talhão.")
        else:
            st.write("Não há classificações doentes neste recorte. Isso não comprova ausência de problemas em áreas não analisadas.")
    else:
        st.write("Selecione as duas categorias para comparar a proporção de classificações doentes entre talhões.")
    st.write("A confiança média ajuda a examinar as previsões. Ela não informa o percentual real de acertos sem rótulos de referência.")

    with st.expander("Registros e origem dos dados", expanded=False):
        origin_counts = selected["origem_dado"].value_counts()
        st.write(" · ".join(f"{ORIGIN_LABELS.get(o, o)}: {v}" for o, v in origin_counts.items()))
        table = selected.drop(columns=["momento", "dia"], errors="ignore").copy()
        table["data_hora"] = selected["momento"].dt.strftime("%d/%m/%Y %H:%M %z")
        st.dataframe(table, hide_index=True, use_container_width=True)
    left, right = st.columns(2)
    left.download_button("Baixar dados filtrados · CSV", history_csv(selected), file_name="agrosmart_filtrado.csv", mime="text/csv", key="export_history_csv", use_container_width=True)
    right.download_button("Baixar dados filtrados · JSON", history_json(selected), file_name="agrosmart_filtrado.json", mime="application/json", key="export_history_json", use_container_width=True)
