# 📖 Manual de utilização — AgroSmart

Guia prático do aplicativo. Para a parte técnica (como o modelo funciona, métricas,
estrutura do código), veja o [README.md](README.md).

---

## Sumário

1. [Instalação](#1-instalação)
2. [Abrindo o aplicativo](#2-abrindo-o-aplicativo)
3. [Aba Classificar — analisar fotos](#3-aba-classificar--analisar-fotos)
4. [Aba Treinamento — banco de fotos e treino](#4-aba-treinamento--banco-de-fotos-e-treino)
5. [Usando suas próprias fotos](#5-usando-suas-próprias-fotos)
6. [Entendendo os resultados](#6-entendendo-os-resultados)
7. [Arquivos exportados](#7-arquivos-exportados)
8. [Modo linha de comando](#8-modo-linha-de-comando)
9. [Solução de problemas](#9-solução-de-problemas)

---

## 1. Instalação

Requisito: **Python 3.10 ou superior**.

```bash
git clone https://github.com/<seu-usuario>/AgroSmart-Fiap.git
cd AgroSmart-Fiap

python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

Isso instala OpenCV, scikit-learn, Streamlit e pandas dentro da pasta `.venv`,
sem afetar o Python do sistema.

## 2. Abrindo o aplicativo

```bash
streamlit run app.py
```

O navegador abre em `http://localhost:8501`. Para encerrar, volte ao terminal e
pressione `Ctrl+C`.

A tela tem uma **barra lateral** (estado do modelo e do banco de fotos) e **três abas**:

| Aba | Para quê |
|---|---|
| 🔍 **Classificar** | Enviar fotos e obter o diagnóstico + baixar CSV/JSON |
| 🎓 **Treinamento** | Alimentar o banco de fotos e treinar o modelo |
| ℹ️ **Sobre** | Explicação do pipeline de visão computacional |

O repositório já vem com um modelo treinado, então dá para classificar
imediatamente, sem treinar nada.

## 3. Aba Classificar — analisar fotos

1. Clique em **Browse files** (ou arraste as fotos para a área pontilhada).
   Aceita `.jpg`, `.jpeg`, `.png`, `.bmp` e `.webp`, **várias de uma vez**.
2. Cada imagem aparece com:
   - o **rótulo** — verde para *Saudável*, vermelho para *Doente*;
   - a **barra de confiança** — quanto o modelo está seguro daquela decisão.
3. Abaixo das imagens, a tabela **Resultados** consolida tudo.
4. Use **⬇️ Baixar CSV** ou **⬇️ Baixar JSON** para salvar o relatório.

> Sem fotos à mão? Use as imagens de exemplo em `data/samples/`.

## 4. Aba Treinamento — banco de fotos e treino

O modelo aprende com as fotos guardadas em `data/train/`:

```
data/train/
├── saudavel/    ← fotos de folhas sadias
└── doente/      ← fotos com praga, mancha ou necrose
```

Você **não precisa mexer nessas pastas manualmente** — a aba faz isso.

### 4.1 Adicionar fotos

1. Escolha a classe no seletor: **Saudável** ou **Doente**.
2. Envie as fotos daquela classe.
3. Clique em **Salvar N imagem(ns)**. Os arquivos vão para a pasta correta com o
   prefixo `real_`, e os contadores no topo se atualizam.
4. Repita para a outra classe.

⚠️ Envie em **duas etapas separadas** — primeiro as saudáveis, depois as doentes.
Tudo que for enviado com a classe selecionada é gravado naquela classe.

### 4.2 Gerar ou limpar imagens simuladas

No expansor **"Gerar imagens simuladas / limpar banco"**:

- **Gerar imagens simuladas** — cria folhas artificiais (10 a 100 por classe) para
  testar o sistema sem fotos reais;
- **Remover imagens simuladas** — apaga só as geradas, preservando as suas fotos
  (as que têm prefixo `real_`).

### 4.3 Treinar

Clique em **🚀 Treinar modelo agora**. Em alguns segundos aparecem:

- **Acurácia (holdout)** — acertos em imagens separadas antes do treino;
- **Cross-val** — média de 5 rodadas de validação cruzada (indicador mais confiável);
- **Matriz de confusão** — onde o modelo errou (linhas = realidade, colunas = previsão).

O modelo novo passa a valer na aba **Classificar** imediatamente.

## 5. Usando suas próprias fotos

### Quantas fotos?

| Quantidade por classe | O que esperar |
|---|---|
| menos de 5 | não recomendado — a validação não significa nada |
| 10 por classe (**20 no total**) | ✅ suficiente para o protótipo; mantenha as simuladas como reforço |
| 25 a 50 por classe | resultado sólido, dá para remover as simuladas |

Com **20 fotos reais (10 + 10)** o sistema treina e funciona. O ponto de atenção é
que, com poucas imagens, uma única foto errada muda bastante a acurácia — por isso
olhe a **cross-val**, não só o holdout. Se puder, misture: suas 20 fotos + as 60
simuladas dão um modelo mais estável enquanto você amplia o banco.

### Como fotografar

- **Uma folha por foto**, centralizada e ocupando boa parte do quadro
  (o sistema segmenta o objeto central e descarta o fundo);
- fundo **contrastante e uniforme** — papel, bancada, solo liso;
- **luz natural difusa**; evite sombra dura, flash direto e luz colorida;
- foco nítido, sem borrão de movimento;
- **equilibre as classes**: aproximadamente o mesmo número de saudáveis e doentes;
- varie ângulo, distância e horário — variedade ensina mais que quantidade repetida.

### Fluxo recomendado

1. Aba **Treinamento** → envie as 10 saudáveis → envie as 10 doentes.
2. Clique em **Treinar modelo agora** e anote a cross-val.
3. Aba **Classificar** → teste com fotos que **não** entraram no treino.
4. Se errar muito, adicione mais fotos do caso que falhou e treine de novo.

## 6. Entendendo os resultados

- **Categoria** — `saudavel` ou `doente`.
- **Confiança / acurácia** — probabilidade da classe escolhida (0 a 1). Acima de
  **0,80** é uma decisão firme; entre **0,50 e 0,65** o modelo está em dúvida e vale
  conferir a foto manualmente.
- **conf_saudavel / conf_doente** — as duas probabilidades; sempre somam 1.

O que o modelo enxerga: proporção de área verde × amarelada × marrom, uniformidade
da cor e granulação da superfície. Manchas, necrose e bordas secas empurram para
*doente*; verde uniforme empurra para *saudável*.

## 7. Arquivos exportados

Os dois formatos trazem os mesmos registros.

**CSV** — abre direto no Excel (acentuação já tratada):

| coluna | conteúdo |
|---|---|
| `imagem` | nome do arquivo analisado |
| `categoria` | `saudavel` ou `doente` |
| `acuracia` | confiança da classe escolhida (0 a 1) |
| `conf_saudavel` | probabilidade de estar saudável |
| `conf_doente` | probabilidade de estar doente |
| `data_hora` | momento da análise (ISO 8601) |

**JSON** — mesmos registros em `resultados`, mais um bloco `metadata` com total de
imagens, resumo por categoria, versão do app e acurácia de validação do modelo.

Pelo app os arquivos vão para a pasta de downloads do navegador; pela linha de
comando, para `outputs/`.

## 8. Modo linha de comando

Útil para lotes grandes ou para gerar evidências da entrega.

```bash
# 1) cria o dataset simulado (30 por classe) e copia amostras para data/samples
python -m agrosmart.cli gerar-dados

# 2) treina e salva o modelo + métricas
python -m agrosmart.cli treinar

# 3) classifica uma pasta inteira e grava CSV + JSON em outputs/
python -m agrosmart.cli classificar --input data/samples --out outputs
```

Opções úteis:

| Comando | Opção | Efeito |
|---|---|---|
| `gerar-dados` | `-n 50` | imagens por classe |
| `treinar` | `--data <pasta>` | treina com outro banco de fotos |
| `treinar` | `--model <arquivo>` | salva o modelo em outro caminho |
| `classificar` | `--input foto.jpg` | classifica uma imagem só |
| `classificar` | `--basename lote_01` | nome dos arquivos exportados |

Ajuda completa: `python -m agrosmart.cli <comando> --help`.

## 9. Solução de problemas

| Situação | O que fazer |
|---|---|
| "Treine o modelo na aba Treinamento antes de classificar" | Não há modelo salvo: vá em **Treinamento** e clique em **Treinar modelo agora** |
| `streamlit` não é reconhecido | O ambiente virtual não está ativo — rode `.venv\Scripts\activate` |
| "Cada classe precisa de pelo menos 2 imagens" | Uma das pastas está quase vazia; adicione fotos ou gere as simuladas |
| Aviso de menos de 8 imagens por classe | Funciona, mas a validação fica instável; adicione mais fotos |
| Todas as fotos saem como a mesma categoria | O banco está desbalanceado ou as classes se parecem demais; equilibre a quantidade e revise se as fotos estão na pasta certa |
| Acurácia alta no treino e erros na prática | O modelo decorou o dataset — amplie e diversifique as fotos |
| Foto com muito fundo dá resultado estranho | Recorte deixando a folha centralizada e dominante |
| A porta 8501 já está em uso | `streamlit run app.py --server.port 8502` |

Verificação geral da instalação:

```bash
python -m pytest tests/ -q      # esperado: 21 passed
```
