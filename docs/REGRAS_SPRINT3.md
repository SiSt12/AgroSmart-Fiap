# Regras de decisão da Sprint 3

Cada avaliação corresponde a um talhão afetado por registros novos de um lote. O total N e a quantidade D de doentes consideram o histórico acumulado após a entrada do lote. C é a média aritmética da confiança somente dos registros novos desse talhão. A base inicial não gera ações retroativas.

## Expressões booleanas

```text
ELEGIVEL = (N >= 10) AND (quantidade_de_novos > 0)
R1 = ELEGIVEL AND (D * 100 > N * 30) AND NOT R1_JA_EMITIDA_NESTA_ENTRADA
R2 = ELEGIVEL AND ((D * 100 > N * 50) OR (C < 0.65))
     AND NOT R2_JA_EMITIDA_NESTA_ENTRADA
```

`rules.py` expõe sinalizadores de regra já emitida. No fluxo integrado, o controle persistente dos lotes e os IDs únicos das ações garantem a não repetição. A identidade da ação combina lote, hash do talhão e regra. As contagens usam comparações inteiras; a média usa Decimal para preservar a comparação de fronteira de 65%.

## Ações

SE R1, ENTÃO registrar alerta JSON para inspecionar o talhão. SE R2, ENTÃO registrar relatório JSON/TXT: por alta proporção, priorizar inspeção; por baixa confiança, revisar manualmente as classificações; pelos dois motivos, priorizar inspeção e revisão. As regras são independentes e podem produzir as duas ações no mesmo talhão e lote.

| Elegível | Proporção P de doentes | Média nova C | R1 | R2 |
|---|---|---|---|---|
| Não | Qualquer | Qualquer | Não | Não |
| Sim | P <= 30% | C >= 65% | Não | Não |
| Sim | 30% < P <= 50% | C >= 65% | Sim | Não |
| Sim | P > 50% | C >= 65% | Sim | Sim |
| Sim | P <= 30% | C < 65% | Não | Sim |
| Sim | P > 30% | C < 65% | Sim | Sim |

Sem registros novos não se emite ação, mesmo que o histórico já esteja acima do limite. Um novo lote genuíno pode gerar outra ação; a proteção se aplica a repetições, não à existência permanente de um alerta anterior no talhão. Filtros do painel não alteram a avaliação.

## Exemplos demonstrados

- B após o lote de 8: 28/92 = 30,43%, média nova 90% → R1.
- C após o lote de 8: 53/92 = 57,61%, média nova 90% → R1 e R2 por proporção.
- A após o lote de baixa confiança: 8/94 = 8,51%, média nova 57,5% → somente R2 por baixa confiança.
- Reimportação do mesmo lote: zero adições → nenhuma ação nova.

30%, 50% e 65% exatos não ativam suas respectivas comparações estritas. Os limiares são parâmetros acadêmicos, sem validação agronômica. As recomendações e os relatórios são simulados; não há envio real de e-mail, irrigação ou intervenção automática no campo.
