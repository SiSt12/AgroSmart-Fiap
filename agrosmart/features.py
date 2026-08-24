"""Extracao de atributos de cor e textura das imagens (OpenCV).

O classificador nao recebe os pixels crus: cada imagem vira um vetor numerico
fixo descrevendo *como a folha esta colorida* e *quao granulada e a superficie*.
Sao atributos explicaveis - da para justificar cada decisao do modelo, o que e
uma vantagem sobre uma rede neural caixa-preta no escopo deste prototipo.
"""

from __future__ import annotations

import cv2
import numpy as np

# Todas as imagens sao normalizadas para o mesmo tamanho antes da extracao,
# senao fotos maiores gerariam contagens de pixels incomparaveis.
IMAGE_SIZE = (256, 256)

# Histogramas propositalmente grossos: com algumas dezenas de imagens de
# treino, bins finos viram dimensoes de ruido e derrubam a validacao cruzada
# (medido: 64 bins -> 0.87, 16 bins -> 0.97 de acuracia com 15 imagens/classe).
H_BINS, S_BINS, V_BINS = 8, 4, 4

# Faixas de matiz em HSV do OpenCV (H vai de 0 a 179, nao de 0 a 359).
FAIXA_VERDE = ((35, 40, 30), (85, 255, 255))     # tecido saudavel
FAIXA_AMARELA = ((20, 60, 60), (34, 255, 255))   # clorose / amarelamento
FAIXA_MARROM = ((0, 40, 20), (19, 255, 200))     # necrose / mancha seca

_EPS = 1e-6


def _nomes_features() -> list[str]:
    nomes = [f"hist_h_{i}" for i in range(H_BINS)]
    nomes += [f"hist_s_{i}" for i in range(S_BINS)]
    nomes += [f"hist_v_{i}" for i in range(V_BINS)]
    nomes += ["frac_verde", "frac_amarelo", "frac_marrom"]
    nomes += ["razao_amarelo_verde", "razao_marrom_verde", "frac_lesao"]
    nomes += ["media_h", "media_s", "media_v", "desvio_h", "desvio_s", "desvio_v"]
    nomes += ["var_laplaciano", "media_sobel", "densidade_bordas"]
    return nomes


FEATURE_NAMES = _nomes_features()
N_FEATURES = len(FEATURE_NAMES)


def preprocess(img_bgr: np.ndarray) -> np.ndarray:
    """Redimensiona para o tamanho padrao e suaviza ruido de captura."""
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Imagem vazia ou nao pode ser lida.")
    if img_bgr.ndim == 2:  # tons de cinza -> BGR
        img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
    if img_bgr.shape[2] == 4:  # PNG com canal alfa
        img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)
    img = cv2.resize(img_bgr, IMAGE_SIZE, interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(img, (3, 3), 0)


def mascara_folha(hsv: np.ndarray) -> np.ndarray:
    """Segmenta a folha e descarta o fundo (solo, bancada, sombra).

    Sem isso o fundo dilui as proporcoes de cor e as duas classes ficam
    parecidas. A premissa - valida para fotos de triagem - e que a folha e o
    objeto dominante e centralizado do quadro:

    1. candidatos = pixels com saturacao/brilho suficientes (Otsu na saturacao,
       que se adapta a iluminacao em vez de usar um limiar fixo);
    2. limpeza morfologica para remover granulacao do solo;
    3. entre os componentes conexos, vence o de maior area ponderada pela
       proximidade ao centro - o fundo costuma ficar nas bordas.
    """
    s, v = hsv[:, :, 1], hsv[:, :, 2]

    limiar, _ = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    limiar = float(np.clip(limiar, 35, 140))
    mask = ((s >= limiar) & (v > 25)).astype(np.uint8) * 255

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    n, rotulos, stats, centroides = cv2.connectedComponentsWithStats(mask, 8)
    if n > 1:
        altura, largura = mask.shape
        centro = np.array([largura / 2.0, altura / 2.0])
        diagonal = float(np.hypot(largura, altura))
        melhor, melhor_nota = 0, 0.0
        for i in range(1, n):
            area = float(stats[i, cv2.CC_STAT_AREA])
            distancia = float(np.linalg.norm(centroides[i] - centro)) / diagonal
            nota = area * (1.0 - min(distancia, 0.5))  # centro pesa mais
            if nota > melhor_nota:
                melhor, melhor_nota = i, nota
        if melhor:
            mask = (rotulos == melhor).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                np.ones((11, 11), np.uint8))

    # Se a segmentacao falhar (folha ocupando todo o quadro, fundo branco),
    # usa a imagem inteira em vez de devolver uma mascara vazia.
    if cv2.countNonZero(mask) < 0.03 * mask.size:
        mask = np.full(mask.shape, 255, np.uint8)
    return mask


def _hist(canal: np.ndarray, bins: int, maximo: int, mask: np.ndarray) -> np.ndarray:
    h = cv2.calcHist([canal], [0], mask, [bins], [0, maximo]).flatten()
    return h / (h.sum() + _EPS)


def _fracao(hsv: np.ndarray, faixa, mask: np.ndarray, area: float) -> float:
    baixo, alto = faixa
    m = cv2.inRange(hsv, np.array(baixo, np.uint8), np.array(alto, np.uint8))
    m = cv2.bitwise_and(m, mask)
    return float(cv2.countNonZero(m)) / area


def extract_features(img_bgr: np.ndarray) -> np.ndarray:
    """Converte uma imagem BGR em um vetor de atributos de tamanho fixo."""
    img = preprocess(img_bgr)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = mascara_folha(hsv)
    area = float(cv2.countNonZero(mask)) + _EPS

    # 1) Distribuicao de cor: a assinatura mais forte de folha doente e o
    #    deslocamento do matiz verde para amarelo/marrom.
    feats = [
        _hist(hsv[:, :, 0], H_BINS, 180, mask),
        _hist(hsv[:, :, 1], S_BINS, 256, mask),
        _hist(hsv[:, :, 2], V_BINS, 256, mask),
    ]

    # 2) Proporcoes interpretaveis por faixa de cor.
    verde = _fracao(hsv, FAIXA_VERDE, mask, area)
    amarelo = _fracao(hsv, FAIXA_AMARELA, mask, area)
    marrom = _fracao(hsv, FAIXA_MARROM, mask, area)
    feats.append(np.array([
        verde, amarelo, marrom,
        amarelo / (verde + _EPS),
        marrom / (verde + _EPS),
        amarelo + marrom,
    ], dtype=np.float64))

    # 3) Estatisticas de cor apenas dentro da folha.
    media, desvio = cv2.meanStdDev(hsv, mask=mask)
    feats.append(np.concatenate([media.flatten(), desvio.flatten()]))

    # 4) Textura: manchas e bordas necrosadas aumentam a granulacao.
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(cinza, cv2.CV_64F)
    sobel_x = cv2.Sobel(cinza, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(cinza, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobel_x, sobel_y)
    bordas = cv2.Canny(cinza, 60, 160)
    feats.append(np.array([
        float(lap[mask > 0].var()),
        float(magnitude[mask > 0].mean()),
        float(cv2.countNonZero(cv2.bitwise_and(bordas, mask))) / area,
    ], dtype=np.float64))

    vetor = np.concatenate(feats).astype(np.float64)
    if vetor.shape[0] != N_FEATURES:  # guarda contra alteracoes acidentais
        raise RuntimeError(
            f"Vetor com {vetor.shape[0]} atributos, esperado {N_FEATURES}."
        )
    return np.nan_to_num(vetor, nan=0.0, posinf=0.0, neginf=0.0)


def imread_unicode(caminho: str) -> np.ndarray:
    """cv2.imread nao le caminhos com acento no Windows; isso resolve."""
    dados = np.fromfile(caminho, dtype=np.uint8)
    img = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Nao foi possivel decodificar a imagem: {caminho}")
    return img
