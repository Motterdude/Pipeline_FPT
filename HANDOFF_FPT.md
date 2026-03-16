# Handoff FPT

## Objetivo

Repositorio separado para o processamento FPT Diesel vs Etanol, sem dependencia operacional do `pipeline28`.

## Estado atual

- Pipeline principal: `pipeline_FPT.py`
- Config principal: `config_pipeline_fpt.xlsx`
- Changelog principal: `CHANGELOG.md`
- Dados locais esperados em `raw_FPT/`
- Saidas geradas em `out_FPT/` e versionadas neste repositorio

## Entradas assumidas

- Arquivos `.xlsx`
- Aba `D`
- Colunas:
  - `FB_VAL`
  - `P_dyno`
  - `SPEED`
- Combustivel identificado no nome do arquivo

## KPIs gerados

- `Consumo_kg_h`
- `Consumo_L_h`
- `Custo_R_h`
- `n_th` e `n_th_pct`
- baseline diesel por `RPM`
- `Economia_vs_Diesel_R_h`
- `Economia_vs_Diesel_pct`
- cenarios de maquinas:
  - colheitadeira
  - trator transbordo
  - caminhao
- `Pair_ID`
- `Pair_Label`

## Arquivos de saida principais

- `out_FPT/lv_kpis_fpt.xlsx`
- `out_FPT/compare_rpm_diesel_vs_e94h6_fpt.xlsx`
- `out_FPT/compare_<pair_id>.xlsx` quando houver mais de um par

## Plots principais

- consumo massico vs RPM
- potencia em kW vs RPM
- consumo volumetrico vs RPM
- custo horario vs RPM
- `n_th` vs RPM
- economia `R$/h` vs RPM
- economia `%` vs RPM
- graficos de cenarios de maquinas por RPM

## Convencoes

- eixo X em `RPM`
- passo fixo de `250 rpm`
- custo horario em `R$/h`
- custo anual em `x10^3 R$/ano`
- consumo anual de etanol em `x10^3 L/ano`
- economia negativa significa vantagem do etanol vs diesel

## Manutencao

- o pipeline agora abre uma GUI para selecionar quais pares Diesel/E94H6 devem entrar na rodada;
- essa GUI faz scan completo de `raw_FPT/` sempre que abre e nao fica limitada por `FILE_INCLUDE_REGEX`;
- os nomes longos dos arquivos agora aparecem com quebra de linha no seletor, sem depender de scroll horizontal;
- se quiser bypass da GUI, usar `PAIR_SELECTION_MODE=auto` na aba `Defaults`;
- a ultima selecao de pares fica salva localmente em `%LOCALAPPDATA%\pipeline_fpt\last_pair_selection.json`;
- o baseline diesel e o merge de comparacao agora acontecem por `Pair_ID`, nao mais por combustivel puro no conjunto inteiro;
- ajustar `FILE_INCLUDE_REGEX` no config continua sendo util para reduzir a lista de arquivos mostrada na GUI;
- manter `raw_FPT/` fora do Git
- versionar `out_FPT/` quando os resultados precisarem acompanhar o codigo
- `xlsx` e `png` sao marcados como binarios em `.gitattributes`
- se o layout dos `.xlsx` mudar, revisar primeiro a funcao `read_fpt_xlsx`
- registrar cada passo relevante em `CHANGELOG.md`
