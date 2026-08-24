"""Treinamento, persistencia e predicao do classificador."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import CLASSES, __version__
from .dataset import load_dataset
from .features import extract_features

RAIZ = Path(__file__).resolve().parent.parent
MODEL_PATH = RAIZ / "models" / "agrosmart_svm.joblib"
METRICS_PATH = RAIZ / "models" / "metrics.json"
DATA_TRAIN = RAIZ / "data" / "train"


def build_pipeline() -> Pipeline:
    """Padronizacao + SVM RBF.

    O StandardScaler e obrigatorio aqui: os atributos misturam frequencias
    (0 a 1) com variancias de textura (centenas), e a SVM e sensivel a escala.
    probability=True habilita o predict_proba usado como acuracia por imagem.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("svm", SVC(kernel="rbf", C=10.0, gamma="scale",
                    probability=True, class_weight="balanced", random_state=42)),
    ])


def train(data_root: str | Path = DATA_TRAIN,
          model_path: str | Path = MODEL_PATH,
          metrics_path: str | Path | None = METRICS_PATH,
          test_size: float = 0.2,
          seed: int = 42) -> dict:
    """Treina, valida e salva o modelo. Devolve o dicionario de metricas."""
    X, y, caminhos = load_dataset(data_root)

    menor_classe = int(min(np.sum(y == c) for c in CLASSES))
    if menor_classe < 2:
        raise ValueError(
            "Cada classe precisa de pelo menos 2 imagens para treinar "
            f"(menor classe tem {menor_classe})."
        )

    # Holdout estratificado: garante as duas classes no conjunto de teste.
    n_teste = max(len(CLASSES), int(round(len(y) * test_size)))
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=n_teste, stratify=y, random_state=seed
    )

    modelo = build_pipeline()
    modelo.fit(X_tr, y_tr)
    y_pred = modelo.predict(X_te)
    acuracia = float(accuracy_score(y_te, y_pred))

    # Validacao cruzada no dataset inteiro. O numero de folds e limitado pela
    # menor classe, para funcionar tambem com poucas imagens reais.
    n_folds = int(min(5, menor_classe))
    if n_folds >= 2:
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
        scores = cross_val_score(build_pipeline(), X, y, cv=cv, scoring="accuracy")
        cv_media, cv_desvio = float(scores.mean()), float(scores.std())
        cv_scores = [float(s) for s in scores]
    else:
        cv_media = cv_desvio = None
        cv_scores = []

    # Modelo final treinado com 100% dos dados (o holdout ja mediu a qualidade).
    modelo_final = build_pipeline()
    modelo_final.fit(X, y)

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": modelo_final, "classes": CLASSES,
                 "versao": __version__}, model_path)

    metricas = {
        "versao_app": __version__,
        "treinado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total_imagens": int(len(y)),
        "imagens_por_classe": {c: int(np.sum(y == c)) for c in CLASSES},
        "acuracia_holdout": round(acuracia, 4),
        "imagens_teste": int(len(y_te)),
        "cross_val_folds": n_folds,
        "cross_val_media": None if cv_media is None else round(cv_media, 4),
        "cross_val_desvio": None if cv_desvio is None else round(cv_desvio, 4),
        "cross_val_scores": [round(s, 4) for s in cv_scores],
        "matriz_confusao": {
            "classes": CLASSES,
            "valores": confusion_matrix(y_te, y_pred, labels=CLASSES).tolist(),
        },
        "relatorio": classification_report(
            y_te, y_pred, labels=CLASSES, zero_division=0, output_dict=True
        ),
        "dataset": str(Path(data_root)),
        "arquivo_modelo": str(model_path),
        "exemplos": len(caminhos),
    }

    if metrics_path is not None:
        metrics_path = Path(metrics_path)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return metricas


def load_model(model_path: str | Path = MODEL_PATH) -> Pipeline:
    """Carrega o pipeline treinado; erro claro se ainda nao existir."""
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo nao encontrado em {model_path}. "
            "Treine primeiro pela aba Treinamento do app ou com "
            "python -m agrosmart.cli treinar"
        )
    return joblib.load(model_path)["pipeline"]


def load_metrics(metrics_path: str | Path = METRICS_PATH) -> dict | None:
    """Le as metricas do ultimo treino, ou None se ainda nao houver treino."""
    metrics_path = Path(metrics_path)
    if not metrics_path.exists():
        return None
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def predict(modelo: Pipeline, img_bgr: np.ndarray) -> dict:
    """Classifica uma imagem BGR.

    Retorna a categoria, a confianca da classe vencedora e a probabilidade de
    cada classe: e isso que alimenta a coluna de acuracia da exportacao.
    """
    vetor = extract_features(img_bgr).reshape(1, -1)
    probabilidades = modelo.predict_proba(vetor)[0]
    classes = list(modelo.classes_)
    idx = int(np.argmax(probabilidades))
    return {
        "categoria": classes[idx],
        "confianca": float(probabilidades[idx]),
        "probabilidades": {c: float(p) for c, p in zip(classes, probabilidades)},
    }
