# 🌿 AgroSmart-Fiap

Protótipo de **visão computacional** que classifica folhas em **saudável** ou **doente**
e exporta os resultados em **CSV** e **JSON**.

> FIAP — Fase 4 — *Visão Computacional aplicada ao ambiente rural*.
> Manual de uso passo a passo: **[MANUAL.md](MANUAL.md)**.

---

## O que o projeto entrega

| Requisito da atividade | Onde está |
|---|---|
| 1.1 Protótipo funcional de reconhecimento de imagens | `agrosmart/features.py` + `agrosmart/model.py` (OpenCV + scikit-learn) |
| Reconhecimento via upload / banco de imagens | `app.py` (Streamlit) e `agrosmart/cli.py` (lote) |
| 1.2 Exportação em `.csv` / `.json` com nome, categoria e acurácia | `agrosmart/export.py` |

## Como funciona

```
imagem  ->  pré-processamento  ->  segmentação  ->  atributos  ->  SVM  ->  categoria
 (BGR)      resize 256x256          da folha       cor+textura            + confiança
            blur gaussiano        (Otsu + maior     31 valores
                                 componente central)
```

1. **Pré-processamento (OpenCV)** — redimensiona para 256×256 e suaviza o ruído de captura.
2. **Segmentação da folha** — limiar de Otsu na saturação + limpeza morfológica; entre os
   componentes conexos vence o de maior área ponderada pela proximidade ao centro. Isso
   descarta o fundo (solo, bancada), que antes diluía as proporções de cor.
3. **Extração de atributos** — 31 valores: histogramas HSV grossos (8/4/4 bins), fração de
   pixels verdes, amarelados e marrons, razões entre elas, média/desvio de H, S e V e três
   medidas de textura (variância do Laplaciano, magnitude Sobel média, densidade de bordas Canny).
4. **Classificação (scikit-learn)** — `StandardScaler` + `SVC(kernel="rbf", C=10)` com
   `predict_proba`; a probabilidade da classe vencedora é a **acurácia por imagem** exportada.
5. **Exportação** — CSV e JSON com nome do arquivo, categoria, acurácia, confiança por classe
   e data/hora.

**Por que atributos e não uma CNN?** Com dezenas de imagens uma rede profunda faz overfitting;
os atributos de cor/textura são estáveis nesse volume e cada decisão é justificável
(ex.: *"22% da área da folha em tom marrom"*), o que ajuda na defesa do trabalho.

## Métricas do modelo publicado

Treinado com 60 imagens simuladas (30 por classe), `seed=42`:

| Métrica | Valor |
|---|---|
| Acurácia (holdout, 12 imagens) | **91,7%** |
| Validação cruzada (5 folds) | **98,3% ± 3,3%** |
| Matriz de confusão (teste) | `[[5, 1], [0, 6]]` (ordem: saudável, doente) |

Números completos em [`models/metrics.json`](models/metrics.json).
São imagens simuladas: a acurácia com fotos reais tende a ser menor — veja
[MANUAL.md](MANUAL.md) para retreinar com o seu próprio banco de fotos.

## Instalação

```bash
git clone https://github.com/<seu-usuario>/AgroSmart-Fiap.git
cd AgroSmart-Fiap

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

## Uso rápido

```bash
streamlit run app.py                                   # interface web (recomendado)

python -m agrosmart.cli gerar-dados                    # cria o dataset simulado
python -m agrosmart.cli treinar                        # treina e salva o modelo
python -m agrosmart.cli classificar --input data/samples --out outputs
```

O app tem três abas: **Classificar** (upload + download CSV/JSON),
**Treinamento** (enviar fotos ao banco e treinar pelo navegador) e **Sobre**.

## Formato da exportação

`resultados_AAAAMMDD_HHMMSS.csv`

```csv
imagem,categoria,acuracia,conf_saudavel,conf_doente,data_hora
amostra_doente_000.jpg,doente,0.9963,0.0037,0.9963,2026-08-23T20:58:40-03:00
amostra_saudavel_000.jpg,saudavel,0.9847,0.9847,0.0153,2026-08-23T20:58:40-03:00
```

`resultados_AAAAMMDD_HHMMSS.json`

```json
{
  "metadata": {
    "aplicacao": "AgroSmart-Fiap",
    "versao": "1.0.0",
    "gerado_em": "2026-08-23T20:58:40-03:00",
    "total_imagens": 6,
    "resumo_por_categoria": { "doente": 3, "saudavel": 3 },
    "modelo": "StandardScaler + SVC(rbf) sobre atributos HSV/textura",
    "acuracia_validacao": 0.9167
  },
  "resultados": [
    {
      "imagem": "amostra_doente_000.jpg",
      "categoria": "doente",
      "acuracia": 0.9963,
      "conf_saudavel": 0.0037,
      "conf_doente": 0.9963,
      "data_hora": "2026-08-23T20:58:40-03:00"
    }
  ]
}
```

## Estrutura

```
AgroSmart-Fiap/
├── app.py                  # interface Streamlit (classificar / treinar / sobre)
├── agrosmart/
│   ├── features.py         # pré-processamento, segmentação e atributos (OpenCV)
│   ├── dataset.py          # leitura de data/train/<classe>/
│   ├── model.py            # pipeline, treino, métricas e predição
│   ├── export.py           # geração do CSV e do JSON
│   ├── synthetic.py        # gerador de imagens simuladas
│   └── cli.py              # gerar-dados | treinar | classificar
├── data/train/{saudavel,doente}/   # banco de fotos usado no treino
├── data/samples/           # imagens avulsas para teste rápido
├── models/                 # modelo treinado + métricas
├── outputs/                # CSV/JSON gerados pela CLI
└── tests/test_pipeline.py  # 21 testes (atributos, treino, export, CLI e app)
```

## Testes

```bash
python -m pytest tests/ -q      # 21 passed
```

Cobrem extração de atributos, treino/validação, predição, formato do CSV/JSON,
fluxo completo da CLI e a abertura do app Streamlit em modo headless.

## Limitações

- O modelo publicado foi treinado em **imagens simuladas**; para uso real, retreine com fotos.
- Assume que a folha é o objeto **dominante e centralizado** da foto.
- Classificação **binária** (saudável × doente), sem identificar a praga específica.
- Iluminação muito colorida (estufa com luz roxa/amarela) desloca o matiz e prejudica a leitura.

## Licença

MIT — uso livre para fins acadêmicos.
