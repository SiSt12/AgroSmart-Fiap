# AgroSmart Sprint 2 — plano de revisão e entrega

## Objetivo acordado

Dar continuidade à Fase 1 com um painel interativo, uma fonte de dados atualizável e um vídeo de 2 a 4 minutos. Priorizar a entrega solicitada. Spark, Databricks, orquestração em nuvem e melhorias para portfólio ficam para uma evolução posterior.

O grupo continua com cinco integrantes. A Fase 1 ainda está em avaliação, portanto não há correções do professor para incorporar até este momento. Todos podem assumir qualquer frente; dificuldade deve ser comunicada cedo para receber ajuda.

## O que a atividade pede

| Entrega do enunciado | Peso | Situação desta base |
|---|---:|---|
| Painel interativo e funcional | 40% | Implementado; falta revisão visual pelo grupo |
| Integração com base real ou simulada e atualização simples | 25% | CSV/JSON, validação e histórico implementados e testados |
| Vídeo explicando indicadores e utilidade para decisões | 25% | Roteiro preparado; falta gravar e disponibilizar |
| Organização e entrega no prazo | 10% | Documentação preparada; falta conferir participantes e envio |

O enunciado permite base simulada. As métricas mencionadas são exemplos: não é obrigatório inventar tipos de praga que o classificador binário da Fase 1 não reconhece. O uso de Spark/Databricks aparece como diferencial, sem peso separado na rubrica enviada.

Prazo mostrado nas capturas: **04/10/2026 às 23h59**. Formato: um ZIP ou RAR com projeto, base de dados e vídeo ou link. Nome indicado: `nomecompleto_rm_turma_fase2_atividade.zip`.

## Caminho adotado e relação com a matéria

Foi mantido o Python/Streamlit da Fase 1. Isso permite reaproveitar classificação e treinamento, acrescentando o painel e a integração.

O fluxo aplica conceitos de Data Pipelines: receber CSV/JSON, padronizar campos, validar linhas, evitar duplicação e gravar um histórico consumido pelo painel. O trabalho com arquivos e pandas se relaciona ao material de RPA com Python. Testes, dependências registradas e separação dos módulos se relacionam ao conteúdo de DevOps. Essa aplicação dos conceitos não exige acrescentar todas as tecnologias apresentadas nos ebooks.

As 60 imagens de treinamento da Fase 1 continuam distintas da demonstração da Sprint 2. Esta última contém 360 eventos tabulares fictícios, claramente identificados, e um lote de atualização com 8 eventos. Não são novas imagens fotografadas nem resultados efetivamente produzidos pelo SVM.

## Como dividir entre cinco

Recomendação: compartilhar agora a base funcional e dividir responsabilidades verificáveis de revisão e conclusão. Como a implementação central já está disponível, as frentes abaixo representam o trabalho restante. A quantidade de arquivos ou de tarefas não mede esforço igual; redistribuam conforme a dificuldade encontrada.

Cada frente deve ter um responsável entre os cinco. Os nomes ficam para escolha do grupo; esta proposta não atribui trabalho realizado a ninguém.

| Frente | Responsabilidade | Evidência para considerar concluída |
|---|---|---|
| 1 — Dados e importação | Ler o dicionário, conferir bases, importar exemplo legado, conferir campos, reimportação e mensagens de erro | Pequeno registro dos cenários executados e eventuais correções |
| 2 — Indicadores e interpretação | Conferir cálculos manualmente, filtros e denominadores; escrever duas observações úteis sobre os dados | Conferência dos números abaixo e explicação sem confundir confiança com acurácia |
| 3 — Interface e uso | Abrir em navegador, revisar legibilidade dos gráficos, filtros, estados vazios e instruções | Lista de ajustes ou confirmação com capturas das telas principais |
| 4 — Integração e pacote | Executar em outro computador, verificar persistência ao reiniciar, rodar testes e preparar o ZIP final | Execução reproduzida, testes conferidos e ZIP extraído/aberto com sucesso |
| 5 — Vídeo e documentação | Adaptar roteiro, gravar, revisar áudio/duração, preencher link e atualizar README se necessário | Vídeo de 2–4 minutos, acessível ao professor, e documentação consistente |

Todos devem abrir o projeto, entender o fluxo de dados e revisar o vídeo final. Se uma frente terminar antes, seu responsável ajuda a que estiver atrasada. Gravar o vídeo não significa precisar escrever o programa inteiro sozinho.

## Números de referência para revisão

| Recorte | Total de análises | Classificadas doentes | Percentual de doentes |
|---|---:|---:|---:|
| Demonstração completa | 360 | 106 | 29,4% |
| Talhão A | 90 | 8 | 8,9% |
| Talhão B | 90 | 27 | 30,0% |
| Talhão C | 90 | 51 | 56,7% |
| Talhão D | 90 | 20 | 22,2% |
| Histórico após adicionar demonstração e lote novo uma vez | 368 | 109 | 29,6% |

O total inicial de saudáveis é 254, ou 70,6%. Selecionar somente a categoria doente faz o percentual ser 100% no recorte. Limpar todos os talhões ou categorias deve resultar em ausência de registros, sem erro. O histórico importado e a demonstração fixa são fontes diferentes.

Uma interpretação possível: no exemplo, o Talhão C merece prioridade de inspeção por apresentar maior proporção de classificações doentes, com o mesmo número de análises dos demais. Isso não comprova incidência real na lavoura, não identifica uma praga e não indica aplicação automática de produto.

## Sequência sugerida

1. Compartilhar a base, escolher um responsável por frente e combinar a primeira devolutiva dentro de 24 horas. Isso é uma proposta de organização, não uma disponibilidade já confirmada dos colegas.
2. Executar as frentes de dados, indicadores e interface em paralelo. Registrar problemas com passos para reproduzir.
3. Consolidar correções numa única cópia. Evitar cinco ZIPs divergentes; usar o repositório existente se o grupo já tiver um fluxo estabelecido.
4. Validar em outro computador e ensaiar a demonstração. Gravar somente depois de confirmar os números.
5. Reservar 02/10 como alvo interno de fechamento, deixando margem antes de 04/10. Ajustar esse alvo à disponibilidade real sem alterar o prazo oficial.
6. Conferir acesso ao vídeo, participantes vinculados, nome do arquivo e conteúdo do ZIP. Guardar o comprovante após o envio pela plataforma.

Se os colegas não responderem, avancem no que já estiver disponível e registrem o que cada pessoa realmente fez. Não deixem gravação, conferência do pacote e cadastro dos integrantes para os últimos minutos.

## Checklist final

- [ ] Cada frente possui responsável e devolutiva.
- [ ] Projeto executado no computador do grupo e em uma segunda instalação.
- [ ] Gráficos e filtros revisados visualmente.
- [ ] Importação de 8 registros aumenta o histórico de 360 para 368.
- [ ] Reimportação do lote não aumenta o total.
- [ ] Histórico permanece após reiniciar o aplicativo.
- [ ] Vídeo de 2 a 4 minutos explica indicadores, atualização e uma decisão possível.
- [ ] Link preenchido em `LINK_DO_VIDEO_SPRINT2.txt` e testado com acesso equivalente ao do professor.
- [ ] Cinco integrantes vinculados à atividade; não presumir que o cadastro antigo foi reaproveitado.
- [ ] ZIP final sem `.venv`, caches, dados pessoais de teste ou links pendentes.
- [ ] Entrega conferida e enviada dentro do prazo.

## Limite da verificação já realizada

Passaram 46 testes automatizados. A revisão visual em navegador não foi concluída por falha na conexão da ferramenta; a execução em Windows também não foi feita nesta sessão. Esses pontos continuam no trabalho de revisão do grupo. O pacote disponibilizado é uma base funcional para finalizar a atividade, e ainda não é a entrega completa com vídeo.
