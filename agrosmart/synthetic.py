"""Gerador de imagens simuladas de folhas (saudaveis e doentes).

A atividade permite usar imagens reais OU simuladas. Este modulo garante que o
repositorio treine e rode logo apos o clone, sem depender de download de
dataset. Para usar fotos reais, basta colocar os arquivos em
`data/train/saudavel/` e `data/train/doente/` e treinar de novo.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from . import CLASSES

TAMANHO = 256


def _fundo(rng: np.random.Generator) -> np.ndarray:
    """Fundo de terra//solo levemente texturizado, em BGR."""
    base = rng.integers(90, 130, size=3)
    img = np.full((TAMANHO, TAMANHO, 3), base, dtype=np.uint8)
    ruido = rng.normal(0, 12, (TAMANHO, TAMANHO, 3))
    return np.clip(img + ruido, 0, 255).astype(np.uint8)


def _desenha_folha(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Elipse verde com nervuras, servindo de folha saudavel base."""
    centro = (TAMANHO // 2 + int(rng.integers(-12, 12)),
              TAMANHO // 2 + int(rng.integers(-12, 12)))
    eixos = (int(rng.integers(58, 74)), int(rng.integers(88, 108)))
    angulo = int(rng.integers(0, 180))

    # Verde saudavel em HSV -> BGR, com variacao natural de tom.
    hsv = np.uint8([[[rng.integers(38, 60), rng.integers(150, 225),
                      rng.integers(110, 175)]]])
    cor = tuple(int(c) for c in cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0])

    mask = np.zeros((TAMANHO, TAMANHO), np.uint8)
    cv2.ellipse(mask, centro, eixos, angulo, 0, 360, 255, -1)
    img[mask > 0] = cor

    # Nervura central e secundarias, em verde mais escuro.
    escuro = tuple(int(c * 0.72) for c in cor)
    rad = np.deg2rad(angulo + 90)
    dx, dy = np.cos(rad), np.sin(rad)
    p1 = (int(centro[0] - dx * eixos[1]), int(centro[1] - dy * eixos[1]))
    p2 = (int(centro[0] + dx * eixos[1]), int(centro[1] + dy * eixos[1]))
    nerv = np.zeros_like(img)
    cv2.line(nerv, p1, p2, escuro, 2)
    for t in np.linspace(-0.7, 0.7, 8):
        meio = (int(centro[0] + dx * eixos[1] * t), int(centro[1] + dy * eixos[1] * t))
        lado = (int(meio[0] - dy * eixos[0] * 0.8), int(meio[1] + dx * eixos[0] * 0.8))
        cv2.line(nerv, meio, lado, escuro, 1)
        lado2 = (int(meio[0] + dy * eixos[0] * 0.8), int(meio[1] - dx * eixos[0] * 0.8))
        cv2.line(nerv, meio, lado2, escuro, 1)
    img[(nerv.sum(axis=2) > 0) & (mask > 0)] = escuro
    return mask


def _aplica_doenca(img: np.ndarray, mask: np.ndarray, rng: np.random.Generator) -> None:
    """Adiciona clorose amarela, manchas necroticas e borda seca."""
    lesao = np.zeros((TAMANHO, TAMANHO), np.uint8)

    # Manchas arredondadas de necrose (marrom) com halo amarelo.
    for _ in range(int(rng.integers(4, 10))):
        ys, xs = np.nonzero(mask)
        i = int(rng.integers(len(xs)))
        ponto = (int(xs[i]), int(ys[i]))
        raio = int(rng.integers(6, 18))
        cv2.circle(lesao, ponto, raio + int(rng.integers(2, 7)), 120, -1)  # halo
        cv2.circle(lesao, ponto, raio, 255, -1)                            # nucleo

    # Ressecamento partindo da borda da folha.
    if rng.random() < 0.7:
        borda = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((13, 13), np.uint8))
        lesao = np.maximum(lesao, (borda > 0).astype(np.uint8) * 120)

    lesao = cv2.GaussianBlur(lesao, (9, 9), 0)
    lesao = cv2.bitwise_and(lesao, mask)

    marrom = np.uint8([[[rng.integers(8, 18), rng.integers(170, 235),
                        rng.integers(70, 120)]]])
    amarelo = np.uint8([[[rng.integers(22, 32), rng.integers(180, 245),
                         rng.integers(160, 215)]]])
    cor_marrom = cv2.cvtColor(marrom, cv2.COLOR_HSV2BGR)[0][0].astype(np.float64)
    cor_amarela = cv2.cvtColor(amarelo, cv2.COLOR_HSV2BGR)[0][0].astype(np.float64)

    peso = (lesao.astype(np.float64) / 255.0)[:, :, None]
    alvo = np.where(peso > 0.55, cor_marrom, cor_amarela)
    img[:] = np.clip(img * (1 - peso) + alvo * peso, 0, 255).astype(np.uint8)


def gera_imagem(classe: str, rng: np.random.Generator) -> np.ndarray:
    """Cria uma imagem sintetica 256x256 da classe informada."""
    if classe not in CLASSES:
        raise ValueError(f"Classe desconhecida: {classe}")
    img = _fundo(rng)
    mask = _desenha_folha(img, rng)
    if classe == "doente":
        _aplica_doenca(img, mask, rng)
    # Ruido de sensor + variacao de iluminacao, para nao ficar sintetico demais.
    img = np.clip(img.astype(np.float64) * rng.uniform(0.85, 1.15)
                  + rng.normal(0, 6, img.shape), 0, 255).astype(np.uint8)
    return img


def generate_dataset(out_dir: str | Path, n_per_class: int = 30,
                     seed: int = 42) -> dict[str, int]:
    """Gera o dataset em `out_dir/<classe>/*.jpg` e devolve a contagem."""
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    contagem: dict[str, int] = {}
    for classe in CLASSES:
        pasta = out_dir / classe
        pasta.mkdir(parents=True, exist_ok=True)
        for i in range(n_per_class):
            img = gera_imagem(classe, rng)
            destino = pasta / f"{classe}_{i:03d}.jpg"
            ok, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if not ok:
                raise RuntimeError(f"Falha ao codificar {destino}")
            buffer.tofile(str(destino))
        contagem[classe] = n_per_class
    return contagem
