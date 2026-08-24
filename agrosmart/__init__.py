"""AgroSmart - prototipo de visao computacional para triagem de folhas.

Pipeline: imagem -> atributos de cor/textura (OpenCV) -> classificador SVM
(scikit-learn) -> exportacao dos resultados em CSV/JSON.
"""

__version__ = "1.0.0"

# Rotulos das classes. A ordem define o indice usado pelo classificador e as
# colunas de confianca exportadas.
CLASSES = ["saudavel", "doente"]

# Rotulos "bonitos" para exibicao na interface e nos relatorios.
CLASS_LABELS = {
    "saudavel": "Saudavel",
    "doente": "Doente",
}
