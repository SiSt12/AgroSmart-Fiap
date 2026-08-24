"""AgroSmart - interface web (Streamlit).

Duas abas principais:
  * Classificar - upload de imagens, resultado por imagem e download CSV/JSON;
  * Treinamento - gerencia o banco de fotos e treina o modelo pelo navegador.

Execucao:  streamlit run app.py
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from agrosmart import CLASSES, CLASS_LABELS, __version__
from agrosmart.dataset import listar_imagens
from agrosmart.export import build_row, to_csv, to_json
from agrosmart.model import (
    DATA_TRAIN,
    METRICS_PATH,
    MODEL_PATH,
    load_metrics,
    load_model,
    predict,
    train,
)
from agrosmart.synthetic import generate_dataset

RAIZ = Path(__file__).resolve().parent
CORES = {"saudavel": "#1e8e3e", "doente": "#c5221f"}
# Nome dos arquivos criados pelo gerador simulado, ex.: doente_007.jpg
PADRAO_SIMULADA = re.compile(r"^(saudavel|doente)_\d{3}\.jpg$")

st.set_page_config(page_title="AgroSmart - FIAP", page_icon="🌿", layout="wide")


@st.cache_resource(show_spinner=False)
def carregar_modelo(assinatura: float):
    """Carrega o modelo treinado.

    `assinatura` e o mtime do arquivo: quando o modelo e retreinado o valor
    muda e o cache do Streamlit e invalidado automaticamente.
    """
    del assinatura
    return load_model()


def modelo_atual():
    if not MODEL_PATH.exists():
        return None
    return carregar_modelo(MODEL_PATH.stat().st_mtime)


def contar_dataset() -> dict[str, int]:
    return {classe: len(listar_imagens(DATA_TRAIN / classe)) for classe in CLASSES}


def decodifica_upload(arquivo) -> np.ndarray:
    dados = np.frombuffer(arquivo.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Arquivo invalido ou corrompido: {arquivo.name}")
    return img


def barra_lateral(metricas: dict | None) -> None:
    with st.sidebar:
        st.header("🌿 AgroSmart")
        st.caption(f"FIAP - Fase 4 - Visao Computacional · v{__version__}")
        st.divider()

        st.subheader("Modelo")
        if metricas is None:
            st.warning("Nenhum modelo treinado ainda. Use a aba **Treinamento**.")
        else:
            st.metric("Acuracia (holdout)", f"{metricas['acuracia_holdout']:.1%}")
            if metricas.get("cross_val_media") is not None:
                st.metric(
                    f"Cross-val ({metricas['cross_val_folds']} folds)",
                    f"{metricas['cross_val_media']:.1%}",
                    delta=f"± {metricas['cross_val_desvio']:.1%}",
                    delta_color="off",
                )
            st.caption(f"{metricas['total_imagens']} imagens de treino · "
                       f"treinado em {metricas['treinado_em'][:16].replace('T', ' ')}")

        st.divider()
        st.subheader("Banco de fotos")
        for classe, total in contar_dataset().items():
            st.write(f"**{CLASS_LABELS[classe]}**: {total} imagens")


def aba_classificar(modelo, metricas: dict | None) -> None:
    st.subheader("Classificacao de imagens")
    st.write("Envie fotos de folhas para identificar sinais de praga ou doenca.")

    if modelo is None:
        st.error("Treine o modelo na aba **Treinamento** antes de classificar.")
        return

    arquivos = st.file_uploader(
        "Imagens (pode selecionar varias)",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        accept_multiple_files=True,
    )
    if not arquivos:
        st.info("Dica: use as imagens de `data/samples/` para um teste rapido.")
        return

    linhas: list[dict] = []
    colunas = st.columns(3)
    for i, arquivo in enumerate(arquivos):
        try:
            img = decodifica_upload(arquivo)
            resultado = predict(modelo, img)
        except ValueError as erro:
            st.warning(str(erro))
            continue

        linhas.append(build_row(arquivo.name, resultado))
        categoria = resultado["categoria"]
        with colunas[i % 3]:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                     caption=arquivo.name, use_container_width=True)
            st.markdown(
                f"<h4 style='color:{CORES[categoria]};margin:0'>"
                f"{CLASS_LABELS[categoria]}</h4>",
                unsafe_allow_html=True,
            )
            st.progress(min(1.0, resultado["confianca"]),
                        text=f"confianca {resultado['confianca']:.1%}")

    if not linhas:
        return

    st.divider()
    st.subheader("Resultados")
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    esquerda, direita = st.columns(2)
    esquerda.download_button(
        "⬇️ Baixar CSV", data=to_csv(linhas).encode("utf-8-sig"),
        file_name=f"resultados_{carimbo}.csv", mime="text/csv",
        use_container_width=True,
    )
    direita.download_button(
        "⬇️ Baixar JSON", data=to_json(linhas, metricas).encode("utf-8"),
        file_name=f"resultados_{carimbo}.json", mime="application/json",
        use_container_width=True,
    )


def aba_treinamento() -> None:
    st.subheader("Treinamento do modelo")
    st.write(
        "O banco de fotos fica em `data/train/<classe>/`. Voce pode enviar fotos "
        "reais por aqui, gerar imagens simuladas e treinar sem sair do navegador."
    )

    contagem = contar_dataset()
    colunas = st.columns(len(CLASSES))
    for coluna, classe in zip(colunas, CLASSES):
        coluna.metric(f"Imagens - {CLASS_LABELS[classe]}", contagem[classe])

    st.markdown("#### 1. Adicionar fotos ao banco")
    classe_alvo = st.radio(
        "Classe das fotos que voce vai enviar", CLASSES,
        format_func=lambda c: CLASS_LABELS[c], horizontal=True,
    )
    novas = st.file_uploader(
        f"Fotos de folha **{CLASS_LABELS[classe_alvo].lower()}**",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        accept_multiple_files=True, key="upload_treino",
    )
    if novas and st.button(f"Salvar {len(novas)} imagem(ns) em {classe_alvo}"):
        destino = DATA_TRAIN / classe_alvo
        destino.mkdir(parents=True, exist_ok=True)
        salvas = 0
        for arquivo in novas:
            try:  # revalida antes de gravar, para nao poluir o dataset
                decodifica_upload(arquivo)
            except ValueError as erro:
                st.warning(str(erro))
                continue
            nome = Path(arquivo.name).name
            (destino / f"real_{nome}").write_bytes(arquivo.getvalue())
            salvas += 1
        st.success(f"{salvas} imagem(ns) salva(s) em `data/train/{classe_alvo}/`.")
        st.rerun()

    with st.expander("Gerar imagens simuladas / limpar banco"):
        quantidade = st.slider("Imagens simuladas por classe", 10, 100, 30, step=10)
        if st.button("Gerar imagens simuladas"):
            generate_dataset(DATA_TRAIN, n_per_class=quantidade)
            st.success(f"{quantidade} imagens por classe geradas.")
            st.rerun()
        if st.button("Remover imagens simuladas (manter apenas fotos reais)"):
            removidas = 0
            for classe in CLASSES:
                for caminho in listar_imagens(DATA_TRAIN / classe):
                    if PADRAO_SIMULADA.match(caminho.name):
                        caminho.unlink()
                        removidas += 1
            st.success(f"{removidas} imagens simuladas removidas.")
            st.rerun()

    st.markdown("#### 2. Treinar")
    if min(contagem.values()) < 2:
        st.error("Cada classe precisa de pelo menos 2 imagens para treinar.")
        return
    if min(contagem.values()) < 8:
        st.warning(
            "Com menos de 8 imagens por classe a validacao fica instavel. "
            "O ideal e ter ao menos 10 por classe, ou combinar com as simuladas."
        )

    if st.button("🚀 Treinar modelo agora", type="primary"):
        with st.spinner("Extraindo atributos e treinando a SVM..."):
            metricas = train()
        st.cache_resource.clear()
        st.success(f"Modelo treinado com {metricas['total_imagens']} imagens.")
        st.rerun()

    metricas = load_metrics()
    if metricas:
        st.markdown("#### Ultimo treino")
        col1, col2, col3 = st.columns(3)
        col1.metric("Acuracia (holdout)", f"{metricas['acuracia_holdout']:.1%}")
        if metricas.get("cross_val_media") is not None:
            col2.metric("Cross-val", f"{metricas['cross_val_media']:.1%}")
        col3.metric("Imagens", metricas["total_imagens"])

        matriz = pd.DataFrame(
            metricas["matriz_confusao"]["valores"],
            index=[f"real: {CLASS_LABELS[c]}" for c in metricas["matriz_confusao"]["classes"]],
            columns=[f"previsto: {CLASS_LABELS[c]}" for c in metricas["matriz_confusao"]["classes"]],
        )
        st.write("Matriz de confusao (conjunto de teste):")
        st.dataframe(matriz, use_container_width=True)
        st.caption(f"Metricas completas em `{METRICS_PATH.relative_to(RAIZ)}`.")


def aba_sobre() -> None:
    st.subheader("Como funciona")
    st.markdown(
        """
**Pipeline**

1. **Pre-processamento (OpenCV)** - redimensiona para 256x256, suaviza ruido e
   segmenta a folha do fundo por saturacao/brilho.
2. **Extracao de atributos** - histogramas HSV, proporcao de pixels verdes,
   amarelados e marrons, estatisticas de cor e medidas de textura
   (variancia do Laplaciano, Sobel, densidade de bordas).
3. **Classificacao (scikit-learn)** - `StandardScaler` + `SVC(kernel="rbf")`
   com `predict_proba`, que fornece a confianca exportada como acuracia.
4. **Exportacao** - CSV e JSON com nome da imagem, categoria, acuracia,
   confianca por classe e data/hora.

**Por que atributos e nao uma CNN?** Com dezenas de imagens, uma rede profunda
sofre overfitting; os atributos de cor/textura sao estaveis nesse volume e cada
decisao do modelo pode ser justificada (ex.: 32% da area em tom marrom).
        """
    )
    st.caption("Linha de comando equivalente: `python -m agrosmart.cli treinar` · "
               "`python -m agrosmart.cli classificar --input data/samples`")


def main() -> None:
    metricas = load_metrics()
    barra_lateral(metricas)

    st.title("AgroSmart - Triagem de folhas por visao computacional")
    st.caption("Classifica folhas em **saudavel** ou **doente** e exporta os "
               "resultados em CSV/JSON.")

    aba1, aba2, aba3 = st.tabs(["🔍 Classificar", "🎓 Treinamento", "ℹ️ Sobre"])
    with aba1:
        aba_classificar(modelo_atual(), metricas)
    with aba2:
        aba_treinamento()
    with aba3:
        aba_sobre()


if __name__ == "__main__":
    main()
