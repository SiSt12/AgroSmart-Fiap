# Fluxo de dados e escolha do microbatch

Origem: CSV/JSON simulados ou exportações das fases anteriores. Ingestão: pasta monitorada, alimentada por cópia de arquivo ou pela interface. Processamento: validação integral, normalização, deduplicação, incorporação e agregação por talhão. Decisão: R1/R2. Ação: alerta JSON ou relatório JSON/TXT. Consulta: Dashboard e downloads. A figura fluxo_sprint3.png representa esse percurso.

## Justificativa do modelo escolhido

Escolhemos microbatch com arquivos locais porque os eventos de classificação chegam em pequenos lotes e as regras representam apoio à inspeção, sem controle de equipamento nem exigência de resposta crítica em tempo real. O monitor verifica a entrada a cada 2 segundos e exige estabilidade de tamanho e modificação entre verificações. Em condições normais há um atraso de poucos segundos, mais o tempo de leitura e processamento; o intervalo não é uma garantia de latência máxima. Essa resposta é adequada aos alertas de proporção acumulada e aos relatórios de revisão de confiança do protótipo.

O modelo reaproveita CSV/JSON das fases anteriores, dispensa infraestrutura de streaming e mantém um checkpoint local em SQLite para registros, lotes e publicações. Ele permite reiniciar sem repetir efeitos de entradas já processadas. Streaming com Kafka seria justificável se surgisse uma necessidade de eventos contínuos de alta frequência ou acionamento de baixa latência, ausente no escopo atual. A chegada do arquivo pode ser manualmente simulada; depois que ele entra na pasta, incorporação, regras e publicação não dependem de clique. O botão Atualizar painel apenas consulta o resultado.

## Controles de execução

- registros: ID e hash do conteúdo normalizado, com unicidade.
- lotes: nome e hash do arquivo, contextos por talhão e indicador concluido.
- acoes: identidade por lote/talhão/regra, payload e indicador exportado.
- meta: inicialização e hash do último CSV materializado.

Transações BEGIN IMMEDIATE protegem as alterações do SQLite. A base inicial apenas alimenta registros. Cada lote com novidades guarda seus próprios totais acumulados e confianças novas, para que lotes posteriores não mudem a avaliação anterior. Ações são persistidas antes da escrita dos arquivos, por um mecanismo local de fila de publicação. Uma falha de exportação deixa exportado=0 para uma nova tentativa no próximo ciclo. Arquivos são escritos de forma atômica por substituição. O protótipo não oferece uma transação única distribuída entre banco e todos os arquivos: a recuperação usa identidades estáveis e publicação repetível.

Se houver falha de leitura ou validação de um arquivo, o monitor registra ERRO e volta ao laço. A mesma assinatura de tamanho/data não é tentada a cada ciclo: corrija e reenvie o arquivo, ou reinicie o monitor depois de resolver a causa. Se um arquivo de ação já publicado for apagado manualmente, exportado=1 não faz sua recriação automática; preserve as saídas no backup.
