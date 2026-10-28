# Dicionário de dados da Sprint 3

Uma linha representa um evento de análise. Os números usam ponto decimal; confiança é fração entre 0 e 1, exibida como percentual na interface.

| Campo | Tipo e unidade | Exemplo | Critério |
|---|---|---|---|
| id_analise | Texto, sem unidade | s3-baixa-confianca-01 | Até 128 caracteres; gerado quando ausente |
| imagem | Texto, identificador | simulada_baixa_01.jpg | Obrigatório, até 255 caracteres; não exige foto no lote tabular |
| data_hora | Data/hora ISO 8601 | 2026-09-23T14:00:00+00:00 | Obrigatório com fuso; normalizado para UTC |
| categoria | Texto enumerado | saudavel | saudavel ou doente; acentos e caixa normalizados |
| confianca | Número, fração 0 a 1 | 0.55 | Finito e obrigatório; acuracia legado aceito |
| conf_saudavel | Número opcional, fração 0 a 1 | 0.55 | Presente junto de conf_doente ou ambas vazias |
| conf_doente | Número opcional, fração 0 a 1 | 0.45 | Soma das duas próxima de 1, tolerância 0,0002 |
| talhao | Texto, sem unidade | Talhão A | Até 100 caracteres; ausente vira Não informado |
| origem_dado | Texto enumerado | simulado | simulado, nao_informada ou real_informado; ausente vira nao_informada |

A probabilidade da categoria escolhida precisa coincidir com confianca, tolerância 0,0002. Se confianca e acuracia vierem juntas, os valores devem concordar. As probabilidades por classe podem faltar nas exportações tabulares legadas.

CSV: UTF-8 com ou sem BOM; vírgula ou ponto e vírgula. JSON: lista ou objeto com resultados. Metadados de validação do modelo não são convertidos em confiança de um registro. Limites por arquivo: 10 MiB (mostrados como 10 MB na interface) e 50.000 registros. Um lote inválido é rejeitado por inteiro pelo fluxo da Sprint 3.

## Exemplo completo

```json
{
  "id_analise": "s3-baixa-confianca-01",
  "imagem": "simulada_baixa_01.jpg",
  "data_hora": "2026-09-23T14:00:00+00:00",
  "categoria": "saudavel",
  "confianca": 0.55,
  "conf_saudavel": 0.55,
  "conf_doente": 0.45,
  "talhao": "Talhão A",
  "origem_dado": "simulado"
}
```

## Identidade e agregações

A identidade por conteúdo usa todos os campos normalizados acima, exceto id_analise. Mesmo conteúdo com outro ID ou em outro formato não cria novo evento; ID existente com conteúdo diferente rejeita o lote. Horários diferentes representam eventos diferentes. Não se compara o conteúdo binário das fotografias.

Proporção de doentes = D / N * 100. A R2 usa a média de confiança somente das novas análises do talhão naquele lote; o cartão do Dashboard mostra a média dos registros selecionados. São denominadores distintos. As datas dos gráficos usam America/Sao_Paulo; as ações gravam gerado_em em UTC. Dias sem observação não recebem percentual zero.

## Saídas das ações

JSON: id, lote_id, arquivo_origem, regra, tipo, talhao, total, doentes, percentual_doentes (0 a 100), confianca_media_novos (0 a 1), motivos, recomendacao, gerado_em e acao_simulada. No download pela interface é acrescentado exportado, obtido do checkpoint; o JSON publicado em disco não contém obrigatoriamente esse campo. Relatórios R2 têm também TXT legível. O id da ação não é o id de análise.

## Bases incluídas

Base fixa: 360 eventos, 254 saudáveis e 106 doentes; 90 por talhão. Histórico atual: 370 eventos, 261 saudáveis e 109 doentes; A tem 94 e B/C/D têm 92 cada. O histórico legado da Sprint 2 em data/history tem 368 e não deve ser confundido com o da Sprint 3. Todas as bases tabulares de demonstração são simuladas.
