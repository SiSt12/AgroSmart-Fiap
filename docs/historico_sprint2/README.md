# AgroSmart - Sprint 2

FIAP · turma 4ESOR · Integração de Dados e Visualização

Projeto AgroSmart — Fase 2 (Sprint 2). Painel de visualização e integração com os dados exportados na Fase 1.

## Executar no Windows

Extraia o ZIP e abra o terminal na pasta que contém `app.py`. Python 3.9 ou superior.

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Não é preciso ativar o ambiente virtual. Abra o endereço local informado no terminal, normalmente http://localhost:8501. Para encerrar, pressione Ctrl+C no terminal.

Linux/macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

A instalação precisa de internet; a demonstração usa arquivos locais. Nenhuma conta externa ou serviço em nuvem é necessário.

## O que foi acrescentado

- Dashboard com filtros de período, talhão e categoria.
- Indicadores de total, classificação saudável/doente e confiança média.
- Gráficos de distribuição, comparação entre talhões e evolução diária.
- Importação do CSV e JSON da Fase 1, validação e prévia dos registros.
- Histórico persistente em CSV, com escrita atômica e reconhecimento de reimportações.
- Exportação do recorte filtrado em CSV/JSON.
- Demonstração identificada: 360 registros e um lote adicional de 8.
- Testes de importação, cálculo, persistência e interface.

As abas de classificação e treinamento continuam disponíveis. A integração com o classificador funciona pela exportação/importação dos arquivos.

## Demonstração em poucos passos

1. Abra Dashboard. A base de demonstração tem 360 registros, de 24/08 a 22/09/2026, em quatro talhões.
2. Confira os totais: 254 classificados saudáveis e 106 doentes (29,4%).
3. Filtre Talhão C: 90 análises, sendo 51 classificadas doentes (56,7%).
4. Vá a Atualizar dados, abra “Começar com o exemplo da atividade” e clique em “Adicionar demonstração ao histórico”.
5. No Dashboard, selecione “Histórico importado”. Verifique 360 registros.
6. Em Atualizar dados, envie `data/demo/lote_novo.csv` e clique em “Gravar registros válidos”.
7. Volte ao Dashboard: com todos os filtros selecionados, o histórico deve conter 368 registros, sendo 109 doentes (29,6%).
8. Importe o mesmo lote novamente: 0 adicionados, 8 repetidos, total preservado em 368.
9. Feche e abra o aplicativo. O histórico importado permanece salvo.

A base fixa “Demonstração simulada” continua com 360 registros; novas importações aparecem na opção “Histórico importado”.

## Integração com a Fase 1

Os arquivos originais estão em `data/exemplos_fase1/`.

- O CSV usa `imagem,categoria,acuracia,conf_saudavel,conf_doente,data_hora`.
- O JSON possui `metadata` e a lista `resultados`.
- O importador converte a coluna legada `acuracia` em `confianca`.
- Preencha talhão e origem no formulário apenas quando o arquivo não os informa.
- Os exemplos da Fase 1 foram obtidos com imagens simuladas: selecione origem “Simulado”. Localização desconhecida pode continuar como “Não informado”.
- As 60 imagens de treino são diferentes dos registros de análises do histórico.

## Regras dos dados

Veja `docs/DICIONARIO_DADOS.md` para formatos e critérios completos.

Cada registro identifica a imagem, horário com fuso, categoria, confiança, talhão e origem. São aceitas somente as categorias saudável/doente. Datas sem fuso são rejeitadas, evitando interpretações silenciosas. A interface agrupa as datas no fuso America/Sao_Paulo.

Importações repetidas são reconhecidas pelo identificador e pelo conteúdo normalizado. Quando o arquivo não tem ID, um identificador estável é calculado a partir do conteúdo. O nome do arquivo de transporte não faz parte dessa identidade. Alterar a localização/origem usada no formulário altera o conteúdo; mantenha as mesmas informações ao reimportar um arquivo legado.

Um ID existente com conteúdo diferente impede a gravação do lote. Não há substituição silenciosa de eventos. Linhas inválidas aparecem na prévia e só as válidas são gravadas mediante clique explícito.

## Onde ficam os dados

- `data/demo/`: bases sintéticas fixas e reproduzíveis.
- `data/exemplos_fase1/`: exportações entregues na Fase 1.
- `data/history/historico.csv`: histórico local criado após a primeira importação.
- `data/history/raw/`: cópias dos arquivos de entrada que adicionaram registros.

As etapas são: extração dos arquivos, transformação/validação, carga do histórico e consumo pelo dashboard. O projeto usa processamento em lote, acionado pela interface.

O protótipo foi projetado para um servidor local. Um bloqueio protege gravações entre sessões do mesmo processo. Não execute vários servidores gravando simultaneamente na mesma pasta. Para aplicações multiusuário distribuídas, a persistência deve evoluir para um banco transacional.

Para isolar testes ou demonstrações, a variável opcional `AGROSMART_HISTORY_DIR` pode apontar para outra pasta. O padrão dispensa configuração.

## Interpretação correta

- “Confiança” é o valor associado à previsão; não é uma medida de acertos observados.
- Acurácia de validação do classificador da Fase 1 aparece separadamente na barra lateral e foi medida com imagens simuladas.
- A demonstração tabular não executa o SVM nem representa fotografias coletadas. Seus nomes de imagens são identificadores fictícios.
- Os percentuais usam apenas os registros selecionados. Se filtrar somente “doente”, o percentual de doentes será 100% naquele recorte.
- Para comparar talhões, observe também o total de análises de cada um.
- Dias sem coleta não são convertidos em zero. A interface não prevê o futuro nem diagnostica doenças específicas.
- Dados desconhecidos continuam identificados como desconhecidos; a opção “real” corresponde à declaração do responsável.

## Testar

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```

Suíte de testes: 46 aprovados (22 da Fase 1 e 24 da Sprint 2). Detalhes em `docs/VERIFICACAO.md`.

Para regenerar somente as bases de exemplo:

```powershell
.venv\Scripts\python.exe -m agrosmart.demo_history
```

Isso não altera o histórico importado. Não use o gerador para simular coletas reais.

## Entrega da atividade

Enunciado enviado: 04/10/2026 às 23h59. Vídeo de 2 a 4 minutos. Confira eventuais avisos mais recentes da FIAP.

Entrega: projeto, bases em `data/`, vídeo no YouTube e link em `LINK_DO_VIDEO_SPRINT2.txt`.

## Organização do grupo

Veja `docs/PLANO_GRUPO.md`. As cinco frentes são propostas de responsabilidade sobre revisão e finalização da base já implementada; não são declarações de autoria ou trabalho feito pelos colegas.

Integrantes: André Luiz Viana Ribeiro (RM553702), Gustavo Henrique de Jesus (RM553554), Silvaldo Stolarz de Lima (RM552727), Vinicius Eugênio da Silva (RM098064), Enzo Teles de Moura (RM553899).

## Referências de implementação

Materiais da FIAP enviados: Data Pipelines e Orquestração (ETL, camadas, cargas incrementais), RPA com Python (CSV/JSON e pandas), Introdução ao DevOps (versionamento, integração e testes). A ferramenta Streamlit já era usada na Fase 1.

Os manuais da fase anterior foram preservados em `docs/FASE1_README.md` e `docs/FASE1_MANUAL.md` como referência histórica.
