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
- `Air_kg_h`
- `Air_kg_h_kW`
- `P_i_MF_mbar`
- `T_i_MF_C`
- `T_B_IC_C`
- `Eta_v` e `Eta_v_pct`
- `Q_intercooler_kW`
- `Custo_R_h`
- `Custo_R_kWh`
- `n_th` e `n_th_pct`
- baseline diesel por `RPM`
- `Diesel_Baseline_Air_kg_h`
- `Diesel_Baseline_Air_kg_h_kW`
- `Diesel_Baseline_Eta_v_pct`
- `Diesel_Baseline_Q_intercooler_kW`
- `Economia_vs_Diesel_R_h`
- `Economia_vs_Diesel_pct`
- `Economia_vs_Diesel_R_kWh`
- `Economia_vs_Diesel_R_kWh_pct`
- `Delta_Air_kg_h_vs_Diesel`
- `Delta_Air_kg_h_kW_vs_Diesel`
- `Delta_Eta_v_pct_vs_Diesel`
- `Delta_Q_intercooler_kW_vs_Diesel`
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
- custo especifico `R$/kWh` vs RPM
- vazao de ar `kg/h` vs RPM
- vazao de ar especifica `kg/h/kW` vs RPM
- pressao de coletor `mBar` vs RPM
- eficiencia volumetrica `%` vs RPM
- potencia dissipada no intercooler `kW` vs RPM
- `n_th` vs RPM
- economia `R$/h` vs RPM
- economia `%` vs RPM
- delta de custo especifico `R$/kWh` vs diesel
- delta percentual de custo especifico vs diesel
- graficos de cenarios de maquinas por RPM

## Convencoes

- eixo X em `RPM`
- passo fixo de `250 rpm`
- custo horario em `R$/h`
- custo especifico em `R$/kWh`
- custo anual em `x10^3 R$/ano`
- consumo anual de etanol em `x10^3 L/ano`
- economia negativa significa vantagem do etanol vs diesel

## Manutencao

- o pipeline agora abre uma GUI para selecionar quais pares Diesel/E94H6 devem entrar na rodada;
- essa GUI faz scan completo de `raw_FPT/` sempre que abre e nao fica limitada por `FILE_INCLUDE_REGEX`;
- os nomes longos dos arquivos agora aparecem com quebra de linha no seletor, sem depender de scroll horizontal;
- a lista de pares selecionados tambem saiu do layout tabular horizontal e passou a usar bloco com quebra de linha;
- se quiser bypass da GUI, usar `PAIR_SELECTION_MODE=auto` na aba `Defaults`;
- o filtro de pontos para comparativos/plots usa `PLOT_POINT_FILTER_MODE=gui` por default e aceita `off` para bypass;
- a GUI desse filtro agora segue o estilo do catalogo do pipeline NANUM: colunas por par/combustivel e linhas por RPM;
- a ultima selecao de pontos fica salva em `%LOCALAPPDATA%\pipeline_fpt\plot_point_filter_last.json`;
- esse filtro atua nos comparativos e plots, mas o `lv_kpis_fpt.xlsx` continua sendo salvo bruto antes dele;
- a ultima selecao de pares fica salva localmente em `%LOCALAPPDATA%\pipeline_fpt\last_pair_selection.json`;
- o baseline diesel e o merge de comparacao agora acontecem por `Pair_ID`, nao mais por combustivel puro no conjunto inteiro;
- ajustar `FILE_INCLUDE_REGEX` no config continua sendo util para reduzir a lista de arquivos mostrada na GUI;
- o leitor agora reconhece o layout alternativo do arquivo `SWay_P8...D85B15.xlsx`, que nao usa a aba `D` e nao traz os mesmos nomes de coluna do conjunto FPT anterior;
- a vazao de ar entra automaticamente quando a planilha trouxer `Sensyflow` ou `qm Air`;
- a pressao de coletor entra automaticamente quando a planilha trouxer `P_i_MF` ou `p i MF`, e o pipeline normaliza a unidade final para `mBar`;
- `T_i_MF` e `T_B_IC` entram automaticamente tanto no layout antigo quanto no SWay;
- a eficiencia volumetrica usa `1013 mBar` de referencia, `T_i_MF`, `6` cilindros e cilindrada detectada pelo nome do arquivo:
  - `NEF67` e `NEF6` -> `6,7 L`
  - `C13`, `Cursore 13` e `Cursor 13` -> `12,9 L`
- a potencia dissipada no intercooler usa `Air_kg_h`, `T_B_IC`, `T_i_MF` e `cp_ar = 1,005 kJ/kg.K`;
- manter `raw_FPT/` fora do Git
- versionar `out_FPT/` quando os resultados precisarem acompanhar o codigo
- `xlsx` e `png` sao marcados como binarios em `.gitattributes`
- se o layout dos `.xlsx` mudar, revisar primeiro a funcao `read_fpt_xlsx`
- registrar cada passo relevante em `CHANGELOG.md`
