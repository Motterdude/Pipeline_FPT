# Handoff

## Estado salvo em 2026-03-17

Este repositorio ficou salvo com duas frentes operacionais:

- comparativos Diesel vs Etanol por KPI em `pipeline_FPT.py`
- comparativos de combustao `NEF67` vs `Cursor 13` no mesmo pipeline

## O que entrou hoje

- Selecao dedicada de pares de combustao, com memoria local da ultima escolha.
- Filtro dedicado de pontos da analise de combustao, separado do filtro usado para KPI/plots gerais.
- Leitura automatica dos canais de combustao via aliases `EE_MEA...`.
- Geracao de tabela longa de combustao em `out_FPT/lv_combustion_fpt.xlsx`.
- Geracao de comparativos em:
  - `out_FPT/compare_rpm_combustion_nef67_vs_cursor13_fpt.xlsx`
  - `out_FPT/compare_combustion_<pair_id>.xlsx`
- Geracao de plots de combustao em `out_FPT/plots_combustion/`.

## Como rodar

```bash
python pipeline_FPT.py
```

## Estado local persistido

- `%LOCALAPPDATA%\\pipeline_fpt\\last_pair_selection.json`
- `%LOCALAPPDATA%\\pipeline_fpt\\plot_point_filter_last.json`
- `%LOCALAPPDATA%\\pipeline_fpt\\last_combustion_selection.json`
- `%LOCALAPPDATA%\\pipeline_fpt\\combustion_plot_point_filter_last.json`

## Observacoes

- `HANDOFF_FPT.md` continua como referencia historica mais extensa.
- Este `HANDOFF.md` resume o estado operacional mais recente do repositorio.
- Os artefatos em `out_FPT/` foram salvos junto com o codigo para manter rastreabilidade da rodada atual.
