# AgroSmart Sprint 3

FIAP · Engenharia de Software · turma 4ESOR · Inteligência no campo

O AgroSmart recebe arquivos CSV/JSON, incorpora apenas análises novas ao histórico e aplica regras por talhão. O monitor grava o checkpoint em SQLite, publica alertas e relatórios simulados e o Streamlit apresenta os resultados. O classificador e o painel das fases anteriores continuam disponíveis.

## Estado incluído neste pacote

O projeto já contém uma demonstração executada: **370 análises (261 saudáveis e 109 doentes), 2 alertas e 2 relatórios**, todos publicados. Há quatro ações em JSON e dois relatórios adicionais em TXT. O banco e o CSV correspondem ao mesmo estado.

Os exemplos de entrada já foram processados. Reenviá-los mantém 370 registros e não gera novas ações. A base fixa “Demonstração simulada” tem 360 registros; para ver o estado atual, use **Histórico importado**. A avaliação das regras usa o acumulado por talhão e não depende dos filtros do painel.

## Instalar no Windows

Use Python **3.12**, versão principal validada nesta revisão. Abra o PowerShell na pasta que contém `app.py`. A pasta pode ser renomeada; os caminhos operacionais são relativos à raiz do projeto.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A instalação precisa de internet. Depois, a demonstração usa somente arquivos locais. O ambiente virtual foi excluído do ZIP para ser recriado no computador de destino. SQLite já acompanha o Python.

## Iniciar os dois programas

No primeiro terminal, inicie o monitor e deixe-o executando:

```powershell
.\.venv\Scripts\python.exe -m agrosmart.ingestion
```

No segundo terminal, na mesma pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra o endereço **Local URL** informado pelo Streamlit. Normalmente é `http://localhost:8501`; se estiver ocupado, pode ser `8502` ou outra porta. Para encerrar, pressione Ctrl+C em cada terminal. O monitor precisa estar ativo durante a chegada de arquivos; o painel sozinho não processa a fila da Sprint 3.

Linux/macOS: crie o ambiente com `python3.12 -m venv .venv`, instale com `.venv/bin/python -m pip install -r requirements.txt` e use `.venv/bin/python` nos dois comandos acima.

## Enviar dados

1. Abra **Atualizar dados**, selecione um CSV/JSON e confira a prévia.
2. Clique em **Enviar para entrada automática**. A interface valida e grava uma cópia `upload_<hash>.csv` ou `.json` na entrada; esse nome interno preserva a rastreabilidade por conteúdo do arquivo.
3. O monitor procura arquivos a cada 2 segundos, espera tamanho e data de modificação estáveis entre verificações e processa o lote automaticamente.
4. No Dashboard, clique em **Atualizar painel**. Esse botão atualiza a visualização; não executa as regras.

Também é possível copiar arquivos para `data/sprint3/entrada/`. Para evitar leitura durante uma cópia incompleta, copie primeiro com extensão `.tmp` e renomeie para `.csv` ou `.json` ao terminar. Os arquivos `.tmp` são ignorados pelo monitor.

Um arquivo com qualquer registro inválido é rejeitado inteiro na Sprint 3. Um ID já existente com conteúdo conflitante também rejeita a transação do lote. Corrija e envie novamente; não edite diretamente o CSV do histórico.

## Regras

As regras são avaliadas somente para talhões com novos registros válidos, após a incorporação do lote. Ambas exigem pelo menos 10 análises acumuladas.

- **R1:** proporção acumulada de doentes **maior que 30%** → alerta de inspeção em JSON.
- **R2:** proporção acumulada de doentes **maior que 50% OU** confiança média das análises novas **menor que 65%** → relatório de revisão prioritária em JSON e TXT.
- **Repetições:** o mesmo evento não é incorporado novamente, mesmo vindo em outro arquivo; sem registros novos, não há nova ação.

30%, 50% e 65% exatos não ultrapassam os respectivos limites. Um talhão pode gerar R1 e R2 no mesmo lote. Outros dados genuinamente novos podem gerar novas ações no mesmo talhão; a proteção não bloqueia alertas para sempre.

Os limites são escolhas acadêmicas do protótipo, sem validação agronômica. “Doente” é a classe binária de triagem; não identifica espécie de praga ou doença específica. Confiança individual não é a acurácia de validação do modelo.

## Arquivos e persistência

| Caminho | Função |
|---|---|
| `agrosmart/rules.py` | Regras puras, sem leitura ou escrita |
| `agrosmart/ingestion.py` | Monitor, validação incremental e checkpoint |
| `agrosmart/actions.py` | Avaliação dos lotes e publicação de ações |
| `agrosmart/sprint3_ui.py` | Fila de entrada, consulta e download das ações |
| `data/sprint3/entrada/` | Arquivos recebidos pelo monitor |
| `data/sprint3/historico/estado.sqlite3` | Registros, lotes, ações e controle persistente |
| `data/sprint3/historico/historico.csv` | Materialização do histórico para o painel |
| `outputs/sprint3/alertas/` | Alertas R1 em JSON |
| `outputs/sprint3/relatorios/` | Relatórios R2 em JSON e TXT |
| `data/demo/` | Base fixa de 360 e lotes de exemplo |
| `data/exemplos_fase1/` | CSV/JSON legados da primeira fase |
| `data/history/` | Histórico legado da Sprint 2, separado do estado atual |

O banco SQLite é a referência persistente da Sprint 3. O monitor mantém o CSV sincronizado e detecta edições externas conflitantes. Não substitua somente o CSV pela base de 360 mantendo o banco com 370. Para backup, encerre os dois programas e copie em conjunto `data/sprint3/` e `outputs/sprint3/`.

Para um ensaio limpo no futuro, use uma segunda cópia isolada do projeto e um estado coerente de banco, CSV, entrada e saídas. Este pacote conserva a demonstração executada; não inclui comando de reset destrutivo. Os testes já exercitam cenários limpos em pastas temporárias.

A variável `AGROSMART_HISTORY_DIR` afeta a seleção do histórico na interface e em funções legadas. Ela **não redireciona o monitor padrão**. No uso normal deixe-a ausente e abra os dois programas na mesma cópia do projeto. Ao detectar o SQLite padrão, a interface seleciona o histórico da Sprint 3.

## Compatibilidade com a Fase 1

O leitor aceita a coluna legada `acuracia` como confiança individual e JSON com `metadata` e `resultados`. Na Sprint 3, talhão ausente recebe “Não informado” e origem ausente recebe `nao_informada`; a prévia não solicita esses campos em formulário. Para demonstrar uma localidade e a origem simulada, inclua `talhao` e `origem_dado` no arquivo antes do primeiro envio. Não modifique a origem de um evento já recebido mantendo o mesmo ID.

As abas Classificar e Treinamento foram preservadas. A classificação exporta resultados que podem ser enviados pela aba Atualizar dados; essa ponte ainda depende da seleção e do envio do arquivo. A automação exigida começa quando o arquivo chega à entrada. As métricas do modelo foram obtidas com imagens simuladas.

## Documentação e evidências

- `docs/AgroSmart_Sprint3_Documentacao.pdf`: documento principal para leitura e avaliação.
- `docs/AgroSmart_Sprint3_Documentacao.docx`: versão editável equivalente.
- `docs/DICIONARIO_DADOS.md`: campos, unidades e critérios de validação.
- `docs/REGRAS_SPRINT3.md`: regras, condições e tabela de decisão.
- `docs/FLUXO_SPRINT3.md` e `docs/fluxo_sprint3.png`: fluxo e justificativa do microbatch.
- `docs/evidencias_sprint3/INDICE.md`: índice das capturas originais.
- `docs/VERIFICACAO.md`: testes, verificações e limitações.
- `docs/ALTERACOES_SPRINT3.md`: mudanças desta revisão.
- `docs/historico_sprint2/`: documentos antigos, sem uso como instrução atual.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Revisão de 26/10/2026: **84 aprovados e 51 avisos** no Windows informado pelo grupo e na cópia revisada em Linux com Python 3.12.14. Os avisos vêm da interoperabilidade Altair/Narwhals. São conhecidos, não foram ocultados e não impediram os testes. Dependências diretas fixadas em `requirements.txt`; dependências transitivas podem variar.

## Integrantes

| Nome | RM |
|---|---|
| André Luiz Viana Ribeiro | 553702 |
| Gustavo Henrique de Jesus | 553554 |
| Silvaldo Stolarz de Lima | 552727 |
| Vinicius Eugênio da Silva | 098064 |
| Enzo Teles de Moura | 553899 |

