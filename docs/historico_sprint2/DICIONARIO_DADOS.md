# Dicionário e regras de importação

Uma linha corresponde a um evento de análise, não necessariamente a uma fotografia única ao longo de toda a história.

| Campo | Regra |
|---|---|
| id_analise | Texto até 128 caracteres; calculado automaticamente quando ausente |
| imagem | Identificador/nome não vazio, até 255 caracteres |
| data_hora | ISO 8601 com fuso; exemplo 2026-09-01T09:00:00-03:00; persistido em UTC |
| categoria | saudavel ou doente; acentos/caixa são normalizados |
| confianca | Número finito entre 0 e 1; a coluna legada acuracia é aceita como equivalente |
| conf_saudavel, conf_doente | Ambas presentes ou ambas vazias; quando presentes, entre 0 e 1, soma próxima de 1 e confiança compatível com a classe |
| talhao | Texto até 100 caracteres; se ausente, usa o formulário ou Não informado |
| origem_dado | simulado, nao_informada ou real_informado |

CSV: UTF-8, com ou sem BOM, separado por vírgula ou ponto e vírgula. Números usam ponto decimal. JSON: lista de objetos ou objeto com resultados. Metadados de acurácia da Fase 1 não viram confiança dos eventos.

Limites operacionais: 10 MB e 50.000 registros por importação. O protótipo é voltado a pequenos volumes locais.

A identificação por conteúdo considera imagem, horário, categoria, confiança, probabilidades, talhão e origem. Mesmo conteúdo em outro arquivo CSV/JSON não cria novo evento. Horários diferentes são eventos distintos. IDs em conflito abortam o lote; não há atualização destrutiva automática. Não é feita deduplicação pelo conteúdo binário de fotografias.

Na gravação, os dados completos são escritos em arquivo temporário, sincronizados e substituídos por operação atômica. O histórico é gravado somente após a validação e a verificação de conflitos.

Indicadores: total = número de eventos selecionados; % doentes = eventos classificados doentes / total selecionado * 100. A proporção global é calculada sobre eventos, sem usar a média simples dos percentuais dos talhões. Confiança média = média das confianças dos eventos selecionados. Recorte vazio não recebe 0% como se houvesse observações.

Datas são agrupadas em America/Sao_Paulo. Dias sem observações interrompem a série; não são contados como dias com zero doentes.

Os 360 registros do exemplo são inteiramente simulados em tabela (seed 42), assim como o lote de 8. Existem 90 por talhão. Resultados: A 8/90 doentes; B 27/90; C 51/90; D 20/90. Nenhuma foto real foi coletada para produzir essa base.
