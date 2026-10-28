# Verificação dos testes

Ambiente: Windows, Python 3.9+, dependências em `requirements.txt`.

- 22 testes da Fase 1 aprovados (classificação, exportação e interface).
- 24 testes da Sprint 2 aprovados (importação, histórico, dashboard e persistência).
- Formatos CSV/JSON legados, duplicatas, fuso horário e filtros do painel cobertos.

Para repetir localmente:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```
