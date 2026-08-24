"""Testes de ponta a ponta do prototipo AgroSmart.

Cobrem os tres requisitos da atividade: extracao/classificacao de imagens,
treino reprodutivel e exportacao dos resultados em CSV/JSON. O ultimo bloco
sobe o app Streamlit em modo headless para garantir que a interface abre.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agrosmart import CLASSES  # noqa: E402
from agrosmart.cli import main as cli_main  # noqa: E402
from agrosmart.dataset import listar_imagens, load_dataset  # noqa: E402
from agrosmart.export import COLUNAS, build_row, export_results, to_csv, to_json  # noqa: E402
from agrosmart.features import (  # noqa: E402
    FEATURE_NAMES,
    N_FEATURES,
    extract_features,
    imread_unicode,
)
from agrosmart.model import load_metrics, load_model, predict, train  # noqa: E402
from agrosmart.synthetic import gera_imagem, generate_dataset  # noqa: E402


@pytest.fixture(scope="module")
def rng() -> np.random.Generator:
    return np.random.default_rng(7)


@pytest.fixture(scope="module")
def dataset_treinado(tmp_path_factory):
    """Dataset simulado + modelo treinado, reaproveitados pelos testes."""
    base = tmp_path_factory.mktemp("agrosmart")
    dados = base / "data" / "train"
    generate_dataset(dados, n_per_class=15, seed=1)
    metricas = train(
        data_root=dados,
        model_path=base / "models" / "modelo.joblib",
        metrics_path=base / "models" / "metrics.json",
        seed=1,
    )
    modelo = load_model(base / "models" / "modelo.joblib")
    return {"base": base, "dados": dados, "metricas": metricas, "modelo": modelo}


# --------------------------------------------------------------------------
# 1. Extracao de atributos
# --------------------------------------------------------------------------

def test_features_tem_tamanho_fixo_e_e_deterministica(rng):
    img = gera_imagem("saudavel", rng)
    v1 = extract_features(img)
    v2 = extract_features(img.copy())
    assert v1.shape == (N_FEATURES,)
    assert np.allclose(v1, v2)
    assert np.isfinite(v1).all()


def test_features_aceita_cinza_e_png_com_alfa(rng):
    img = gera_imagem("doente", rng)
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    com_alfa = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    assert extract_features(cinza).shape == (N_FEATURES,)
    assert extract_features(com_alfa).shape == (N_FEATURES,)


def test_features_independem_do_tamanho_da_imagem(rng):
    img = gera_imagem("saudavel", rng)
    grande = cv2.resize(img, (700, 700), interpolation=cv2.INTER_LINEAR)
    # As proporcoes de cor devem ficar proximas mesmo mudando a resolucao.
    fatia = slice(FEATURE_NAMES.index("frac_verde"),
                  FEATURE_NAMES.index("frac_marrom") + 1)
    assert extract_features(img)[fatia] == pytest.approx(
        extract_features(grande)[fatia], abs=0.12
    )


def test_imagem_invalida_gera_erro_claro():
    with pytest.raises(ValueError):
        extract_features(np.zeros((0, 0, 3), np.uint8))


def test_folha_doente_tem_mais_area_nao_verde(rng):
    """Sanidade do gerador e dos atributos: doente = menos verde."""
    idx_verde = FEATURE_NAMES.index("frac_verde")
    saudaveis = [extract_features(gera_imagem("saudavel", rng))[idx_verde]
                 for _ in range(6)]
    doentes = [extract_features(gera_imagem("doente", rng))[idx_verde]
               for _ in range(6)]
    assert np.mean(saudaveis) > np.mean(doentes)


# --------------------------------------------------------------------------
# 2. Dataset e treino
# --------------------------------------------------------------------------

def test_gerador_cria_as_duas_classes(tmp_path):
    contagem = generate_dataset(tmp_path / "train", n_per_class=4, seed=3)
    assert contagem == {c: 4 for c in CLASSES}
    for classe in CLASSES:
        arquivos = listar_imagens(tmp_path / "train" / classe)
        assert len(arquivos) == 4
        assert imread_unicode(str(arquivos[0])).shape == (256, 256, 3)


def test_load_dataset_monta_matriz_coerente(dataset_treinado):
    X, y, caminhos = load_dataset(dataset_treinado["dados"])
    assert X.shape == (30, N_FEATURES)
    assert set(y) == set(CLASSES)
    assert len(caminhos) == 30


def test_load_dataset_sem_imagens_avisa(tmp_path):
    for classe in CLASSES:
        (tmp_path / classe).mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="Nenhuma imagem"):
        load_dataset(tmp_path)


def test_treino_atinge_acuracia_alta_e_salva_artefatos(dataset_treinado):
    metricas = dataset_treinado["metricas"]
    base = dataset_treinado["base"]
    # O holdout tem poucas imagens (um erro ja custa ~15 pontos), entao o
    # criterio forte fica na validacao cruzada, que usa o dataset inteiro.
    assert metricas["acuracia_holdout"] >= 0.80
    assert metricas["cross_val_media"] >= 0.90
    assert metricas["total_imagens"] == 30
    assert (base / "models" / "modelo.joblib").exists()
    salvas = load_metrics(base / "models" / "metrics.json")
    assert salvas["acuracia_holdout"] == metricas["acuracia_holdout"]


def test_treino_recusa_classe_com_uma_imagem(tmp_path):
    generate_dataset(tmp_path / "train", n_per_class=2, seed=5)
    sobrando = listar_imagens(tmp_path / "train" / "doente")[0]
    sobrando.unlink()
    with pytest.raises(ValueError, match="pelo menos 2 imagens"):
        train(data_root=tmp_path / "train",
              model_path=tmp_path / "m.joblib", metrics_path=None)


def test_modelo_ausente_da_mensagem_util(tmp_path):
    with pytest.raises(FileNotFoundError, match="Treine primeiro"):
        load_model(tmp_path / "nao_existe.joblib")


# --------------------------------------------------------------------------
# 3. Predicao
# --------------------------------------------------------------------------

def test_predict_retorna_estrutura_valida(dataset_treinado, rng):
    resultado = predict(dataset_treinado["modelo"], gera_imagem("saudavel", rng))
    assert resultado["categoria"] in CLASSES
    assert 0.0 <= resultado["confianca"] <= 1.0
    assert set(resultado["probabilidades"]) == set(CLASSES)
    assert sum(resultado["probabilidades"].values()) == pytest.approx(1.0, abs=1e-6)
    assert resultado["confianca"] == max(resultado["probabilidades"].values())


def test_predict_acerta_imagens_novas(dataset_treinado, rng):
    """Generalizacao: imagens que nao estavam no treino (outra seed)."""
    acertos = 0
    total = 0
    for classe in CLASSES:
        for _ in range(8):
            resultado = predict(dataset_treinado["modelo"], gera_imagem(classe, rng))
            acertos += int(resultado["categoria"] == classe)
            total += 1
    assert acertos / total >= 0.85


# --------------------------------------------------------------------------
# 4. Exportacao (item 1.2 da atividade)
# --------------------------------------------------------------------------

@pytest.fixture
def linhas_exemplo() -> list[dict]:
    return [
        build_row("folha_01.jpg", {"categoria": "saudavel", "confianca": 0.9312,
                                   "probabilidades": {"saudavel": 0.9312, "doente": 0.0688}}),
        build_row("folha_02.jpg", {"categoria": "doente", "confianca": 0.8745,
                                   "probabilidades": {"saudavel": 0.1255, "doente": 0.8745}}),
    ]


def test_csv_tem_as_colunas_exigidas(linhas_exemplo):
    linhas = list(csv.DictReader(io.StringIO(to_csv(linhas_exemplo))))
    assert list(linhas[0]) == COLUNAS
    assert {"imagem", "categoria", "acuracia"} <= set(COLUNAS)
    assert linhas[0]["imagem"] == "folha_01.jpg"
    assert linhas[0]["categoria"] == "saudavel"
    assert float(linhas[0]["acuracia"]) == pytest.approx(0.9312)


def test_json_traz_metadados_e_resultados(linhas_exemplo):
    doc = json.loads(to_json(linhas_exemplo, {"acuracia_holdout": 0.95}))
    assert doc["metadata"]["total_imagens"] == 2
    assert doc["metadata"]["resumo_por_categoria"] == {"saudavel": 1, "doente": 1}
    assert doc["metadata"]["acuracia_validacao"] == 0.95
    assert [r["imagem"] for r in doc["resultados"]] == ["folha_01.jpg", "folha_02.jpg"]


def test_export_results_grava_os_dois_arquivos(tmp_path, linhas_exemplo):
    destinos = export_results(linhas_exemplo, tmp_path, "lote_teste")
    assert destinos["csv"].exists() and destinos["json"].exists()
    # BOM garante acentos corretos ao abrir no Excel.
    assert destinos["csv"].read_bytes().startswith(b"\xef\xbb\xbf")
    assert json.loads(destinos["json"].read_text(encoding="utf-8"))["resultados"]


# --------------------------------------------------------------------------
# 5. CLI de ponta a ponta
# --------------------------------------------------------------------------

def test_cli_fluxo_completo(tmp_path, capsys):
    dados = tmp_path / "train"
    amostras = tmp_path / "samples"
    modelo = tmp_path / "modelo.joblib"
    saida = tmp_path / "outputs"

    assert cli_main(["gerar-dados", "--out", str(dados),
                     "--samples", str(amostras), "-n", "8"]) == 0
    # Caminhos temporarios: o teste nao pode sobrescrever o modelo do repo.
    assert cli_main(["treinar", "--data", str(dados), "--model", str(modelo),
                     "--metrics", str(tmp_path / "metrics.json")]) == 0
    assert cli_main(["classificar", "--input", str(amostras),
                     "--model", str(modelo),
                     "--metrics", str(tmp_path / "metrics.json"),
                     "--out", str(saida), "--basename", "lote"]) == 0

    texto = capsys.readouterr().out
    assert "Treino concluido" in texto
    csv_gerado = saida / "lote.csv"
    assert csv_gerado.exists() and (saida / "lote.json").exists()
    linhas = list(csv.DictReader(io.StringIO(
        csv_gerado.read_text(encoding="utf-8-sig"))))
    assert len(linhas) == len(listar_imagens(amostras))
    assert all(linha["categoria"] in CLASSES for linha in linhas)


def test_cli_entrada_vazia_retorna_erro(tmp_path):
    (tmp_path / "vazia").mkdir()
    assert cli_main(["classificar", "--input", str(tmp_path / "vazia")]) == 1


def test_cli_treinar_nao_toca_no_modelo_do_repositorio(tmp_path):
    """Regressao: o treino da CLI deve respeitar --model/--metrics."""
    from agrosmart.model import METRICS_PATH, MODEL_PATH

    antes = (MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else None,
             METRICS_PATH.stat().st_mtime if METRICS_PATH.exists() else None)
    dados = tmp_path / "train"
    generate_dataset(dados, n_per_class=4, seed=9)
    assert cli_main(["treinar", "--data", str(dados),
                     "--model", str(tmp_path / "m.joblib"),
                     "--metrics", str(tmp_path / "m.json")]) == 0
    assert (tmp_path / "m.joblib").exists()
    depois = (MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else None,
              METRICS_PATH.stat().st_mtime if METRICS_PATH.exists() else None)
    assert antes == depois


# --------------------------------------------------------------------------
# 6. Interface Streamlit (usabilidade)
# --------------------------------------------------------------------------

def test_app_streamlit_abre_sem_excecao():
    """Sobe o app headless e confere que as abas renderizam."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=90)
    app.run()
    assert not app.exception
    titulos = [t.value for t in app.title]
    assert any("AgroSmart" in titulo for titulo in titulos)
    assert len(app.tabs) == 3
    # O uploader da aba de classificacao precisa existir para o fluxo funcionar.
    assert len(app.get("file_uploader")) >= 1


def test_app_streamlit_tem_botao_de_treino():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=90)
    app.run()
    rotulos = [b.label for b in app.button]
    assert any("Treinar modelo" in rotulo for rotulo in rotulos)
