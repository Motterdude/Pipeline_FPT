# Handoff FPT

## Objetivo

Repositório separado para o processamento FPT Diesel vs Etanol, sem dependência operacional do `pipeline28`.

## Estado atual

- Pipeline principal: `pipeline_FPT.py`
- Config principal: `config_pipeline_fpt.xlsx`
- Dados locais esperados em `raw_FPT/`
- Saídas geradas em `out_FPT/` e versionadas neste repositório

## Entradas assumidas

- Arquivos `.xlsx`
- Aba `D`
- Colunas:
  - `FB_VAL`
  - `P_dyno`
  - `SPEED`
- Combustível identificado no nome do arquivo

## KPIs gerados

- `Consumo_kg_h`
- `Consumo_L_h`
- `Custo_R_h`
- `n_th` e `n_th_pct`
- baseline diesel por `RPM`
- `Economia_vs_Diesel_R_h`
- `Economia_vs_Diesel_pct`
- cenários de máquinas:
  - colheitadeira
  - trator transbordo
  - caminhão

## Arquivos de saída principais

- `out_FPT/lv_kpis_fpt.xlsx`
- `out_FPT/compare_rpm_diesel_vs_e94h6_fpt.xlsx`

## Plots principais

- consumo mássico vs RPM
- potência em kW vs RPM
- consumo volumétrico vs RPM
- custo horário vs RPM
- `n_th` vs RPM
- economia `R$/h` vs RPM
- economia `%` vs RPM
- gráficos de cenários de máquinas por RPM

## Convenções

- eixo X em `RPM`
- passo fixo de `250 rpm`
- custo horário em `R$/h`
- custo anual em `x10^3 R$/ano`
- consumo anual de etanol em `x10^3 L/ano`
- economia negativa significa vantagem do etanol vs diesel

## Manutenção

- ajustar `FILE_INCLUDE_REGEX` no config para trocar o par Diesel/E94H6
- manter `raw_FPT/` fora do Git
- versionar `out_FPT/` quando os resultados precisarem acompanhar o código
- `xlsx` e `png` são marcados como binários em `.gitattributes`
- se o layout dos `.xlsx` mudar, revisar primeiro a função `read_fpt_xlsx`
