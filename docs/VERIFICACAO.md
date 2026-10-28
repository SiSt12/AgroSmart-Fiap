# Verificação da Sprint 3

## Testes executados

Em 26/10/2026, a cópia extraída do ZIP atualizado foi executada em ambiente isolado Linux com Python 3.12.14 e as nove dependências diretas fixadas em requirements.txt. Resultado: **84 passed, 51 warnings**. No Windows do grupo, Python 3.12.10, a captura 10 registra o mesmo total após os ajustes de texto e identificação.

Distribuição: 22 testes da Fase 1, 24 da Sprint 2, 12 de regras, 9 de ingestão, 9 de ações e 8 de interface Sprint 3. Os 51 avisos da revisão são UserWarning de Altair/Narwhals: 6 em test_pipeline, 42 em test_sprint2 e 3 em test_sprint3_ui. Não foram ocultados. Dependências transitivas podem variar entre instalações.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Os testes de Streamlit usam AppTest. A inspeção visual em navegador foi realizada pelo grupo e registrada nas capturas recebidas; essa evidência não deve ser confundida com uma sessão remota de navegador no computador do grupo.

## Integridade do estado entregue

- SQLite PRAGMA integrity_check: ok.
- Banco: 370 registros, 4 lotes concluídos e 4 ações exportadas.
- Histórico CSV: 370 IDs únicos; 261 saudáveis e 109 doentes.
- Hash do CSV corresponde ao checkpoint ultimo_csv.
- Payloads dos quatro JSONs publicados correspondem aos registrados no SQLite.
- CSV/JSON completos exportados pela interface: nenhuma divergência de campos.
- Cabeçalho JSON atualizado para AgroSmart Sprint 3.

## Evidências da demonstração

360 → lote de 8 → 368 (2 alertas e 1 relatório). Repetição: zero adições, oito duplicados e nenhum novo efeito. Reinício: estado preservado. Envio do lote de baixa confiança: duas adições → 370 e mais um relatório. Os JSON/TXT dos talhões C e A foram conferidos com os valores exibidos no painel.

## Reinício adicional na cópia revisada

O monitor foi iniciado em uma cópia temporária renomeada com espaços. Reconheceu os quatro arquivos de entrada como repetidos (8, 8, 2 e 8 registros), preservando 370 eventos e quatro ações. Não publicou novas ações. Os hashes do histórico CSV e dos seis arquivos de saída permaneceram idênticos. Log em evidencias_sprint3/reinicio_monitor_revisao.txt.

## Limites conhecidos

- Regras e dados são acadêmicos e simulados; os limiares não foram validados no campo.
- Não há sensor, e-mail real, diagnóstico de praga específica ou acionamento físico.
- O sistema é local; não foi validado para múltiplos monitores simultâneos, rede distribuída ou grandes volumes.
- A série histórica não é previsão; confiança individual não mede acurácia observada.
- A exportação CSV do histórico inteiro está sujeita ao limite operacional do leitor de 50.000 registros; o estado atual tem 370.
- O monitor deve ficar ativo para novos arquivos; a interface precisa de atualização para mostrar alterações.
- Não há reset automático; preserve banco, CSV, entrada e saídas em conjunto.

## Antes da entrega

Conferir a instalação na cópia baixada no computador de destino e o endereço local informado pelo terminal. A pasta renomeada deve funcionar porque os caminhos operacionais são relativos; caminhos antigos em models/metrics.json são metadados do treinamento, não o diretório de execução. Verificar também os participantes na plataforma e o vídeo/link da Sprint 3, ainda pendente.
