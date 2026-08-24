"""Leitura do dataset em disco: data/train/<classe>/*.jpg."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import CLASSES
from .features import extract_features, imread_unicode

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def listar_imagens(pasta: str | Path) -> list[Path]:
    """Todos os arquivos de imagem de uma pasta, em ordem estavel."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir()
                  if p.is_file() and p.suffix.lower() in EXTENSOES)


def load_dataset(root: str | Path) -> tuple[np.ndarray, np.ndarray, list[Path]]:
    """Le `root/<classe>/` e devolve (X, y, caminhos).

    y guarda o nome da classe (string), nao o indice - o scikit-learn lida bem
    com rotulos textuais e isso mantem os relatorios legiveis.
    """
    root = Path(root)
    X: list[np.ndarray] = []
    y: list[str] = []
    caminhos: list[Path] = []

    for classe in CLASSES:
        arquivos = listar_imagens(root / classe)
        if not arquivos:
            raise FileNotFoundError(
                f"Nenhuma imagem em {root / classe}. "
                "Rode `python -m agrosmart.cli gerar-dados` ou adicione fotos reais."
            )
        for arquivo in arquivos:
            X.append(extract_features(imread_unicode(str(arquivo))))
            y.append(classe)
            caminhos.append(arquivo)

    return np.vstack(X), np.array(y), caminhos
