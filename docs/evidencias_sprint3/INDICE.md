# Evidências da Sprint 3

Capturas fornecidas por Gustavo em 26/10/2026. As imagens originais foram copiadas sem alteração de conteúdo. Os nomes foram organizados para a documentação.

- `01_acoes_gerais.png`: Dashboard com duas R1, duas R2 e nenhuma ação aguardando gravação.
- `02_historico_370.png`: Histórico completo com 370 análises e gráficos por talhão e período.
- `03_alerta_r1_talhao_b.png`: R1 do Talhão B: 28 de 92 doentes, 30,43%.
- `04_relatorio_r2_talhao_c.png`: R2 do Talhão C: 53 de 92 doentes, 57,61%.
- `05_relatorio_r2_talhao_a.png`: R2 do Talhão A: baixa confiança nas novas análises, com 8 de 94 doentes.
- `06_entrada_repeticao_reinicio.png`: Execução anterior: 360 para 368, duplicatas e reinício sem novas ações. A suíte de 76 testes mostrada era a etapa anterior à interface.
- `07_comparacao_arquivos.png`: Compare-Object sem diferenças entre hashes antes e depois da repetição, na demonstração com 368 registros.
- `08_repeticao_pela_interface.png`: Reenvio pela interface: zero adições e oito duplicados; total de 368. Falhas antigas no topo antecedem o resultado aprovado abaixo.
- `09_lote_baixa_confianca.png`: Novo lote: duas adições, total 370 e um relatório publicado.
- `10_testes_84_aprovados.png`: Após ajustes de identificação e texto: 84 testes aprovados e 51 avisos no Windows.
- `11_classificacao_exemplo.png`: Uma imagem simulada classificada como doente com confiança de 97,02%; não é a acurácia global.
- `12_sobre_atualizado.png`: Descrição atualizada das regras e da compatibilidade com o campo legado acuracia.

As evidências 06 a 09 descrevem momentos diferentes da execução, não o mesmo estado simultâneo. A sequência completa é 360 → 368 → 370.

- `reinicio_monitor_revisao.txt`: log adicional da revisão em cópia isolada renomeada, preservando 370 registros e quatro ações.
- `verificacao_integridade.json`: resumo da integridade do estado conferido.
- `exportacoes_conferidas/`: CSV/JSON do histórico completo e JSON/TXT dos dois relatórios R2, baixados da interface.
