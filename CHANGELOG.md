# Changelog

Todas as mudancas relevantes deste repositorio devem ser registradas aqui.

## 2026-03-17

### Added

- Fluxo novo de comparacao de combustao `NEF67` vs `Cursor 13` dentro de `pipeline_FPT.py`.
- Persistencia local da ultima selecao de pares de combustao em `%LOCALAPPDATA%\\pipeline_fpt\\last_combustion_selection.json`.
- Persistencia local do ultimo filtro de pontos da analise de combustao em `%LOCALAPPDATA%\\pipeline_fpt\\combustion_plot_point_filter_last.json`.
- Resolucao automatica de canais de combustao por aliases `EE_MEA...` para:
  - `PCYL1`
  - `APMAX1`
  - `PMAX1`
  - `IMEP1`
  - `IMEPH1`
  - `IMPEL1`
  - `AI05_1`
  - `AI10_1`
  - `AI50_1`
  - `AI90_1`
  - `RMAX1`
- Novas saidas de combustao:
  - `out_FPT/lv_combustion_fpt.xlsx`
  - `out_FPT/compare_rpm_combustion_nef67_vs_cursor13_fpt.xlsx`
  - `out_FPT/compare_combustion_<pair_id>.xlsx`
- Nova pasta `out_FPT/plots_combustion/` com os graficos por canal de combustao vs `RPM`.

### Changed

- O pipeline agora mantem estados separados para selecao/filtro do fluxo de KPI e do fluxo de combustao.
- A descoberta de pares de combustao passou a sugerir automaticamente correspondencias `NEF67` vs `Cursor 13` quando os nomes dos arquivos compartilham descritores de ensaio.
- Os outputs principais do repo foram rerodados para refletir as novas tabelas e plots de combustao.

## 2026-03-16

### Added

- GUI em `Tkinter` no `pipeline_FPT.py` para ler `raw_FPT/` e montar explicitamente os pares Diesel vs Etanol da rodada.
- Persistencia local da ultima selecao de pares em `%LOCALAPPDATA%\pipeline_fpt\last_pair_selection.json`.
- GUI em `Tkinter` para filtro manual de pontos de plot em grade, com memoria da ultima selecao em `%LOCALAPPDATA%\pipeline_fpt\plot_point_filter_last.json`.
- `Pair_ID` e `Pair_Label` nos dataframes agregados e no comparativo final.
- Saidas adicionais `compare_<pair_id>.xlsx` quando houver mais de um par selecionado.
- Metricas novas de custo especifico:
  - `Custo_R_kWh`
  - `Economia_vs_Diesel_R_kWh`
  - `Economia_vs_Diesel_R_kWh_pct`
- Metricas novas de vazao de ar:
  - `Air_kg_h`
  - `Air_kg_h_kW`
  - `Diesel_Baseline_Air_kg_h`
  - `Diesel_Baseline_Air_kg_h_kW`
  - `Delta_Air_kg_h_vs_Diesel`
  - `Delta_Air_kg_h_kW_vs_Diesel`
- Metrica nova de pressao de coletor:
  - `P_i_MF_mbar`
- Metricas novas de enchimento e troca termica:
  - `Eta_v`
  - `Eta_v_pct`
  - `Eta_v_corr_press`
  - `Eta_v_corr_press_pct`
  - `Diesel_Baseline_Eta_v_pct`
  - `Diesel_Baseline_Eta_v_corr_press_pct`
  - `Delta_Eta_v_pct_vs_Diesel`
  - `Delta_Eta_v_corr_press_pct_vs_Diesel`
  - `Q_intercooler_kW`
  - `Diesel_Baseline_Q_intercooler_kW`
  - `Delta_Q_intercooler_kW_vs_Diesel`
- Metricas novas de torque e pressao media efetiva:
  - `Torque_Nm`
  - `BMEP_bar`
  - `Diesel_Baseline_Torque_Nm`
  - `Diesel_Baseline_BMEP_bar`
  - `Delta_Torque_Nm_vs_Diesel`
  - `Delta_BMEP_bar_vs_Diesel`
- Metricas novas para curva do compressor:
  - `P_B_Compr_rel_mbar`
  - `P_B_IC_rel_mbar`
  - `P_B_Compr_abs_mbar`
  - `P_B_IC_abs_mbar`
  - `T_AIR_C`
  - `RH_Air_pct`
  - `Compressor_PRatio_abs`
  - `Compressor_VolFlow_m3_s`
- Plots novos:
  - `custo_especifico_r_kwh_vs_rpm.png`
  - `economia_r_kwh_vs_diesel_rpm.png`
  - `economia_pct_r_kwh_vs_diesel_rpm.png`
  - `vazao_ar_kg_h_vs_rpm.png`
  - `vazao_ar_kg_h_kw_vs_rpm.png`
  - `pressao_coletor_mbar_vs_rpm.png`
  - `torque_nm_vs_rpm.png`
  - `bmep_bar_vs_rpm.png`
  - `curva_compressor_pratio_vs_power_kw.png`
  - `curva_compressor_pratio_vs_vazao_massica_kg_h.png`
  - `curva_compressor_pratio_vs_vazao_volumetrica_m3_s.png`
  - `eficiencia_volumetrica_vs_rpm.png`
  - `eficiencia_volumetrica_corrigida_pressao_vs_rpm.png`
  - `potencia_intercooler_kw_vs_rpm.png`

### Changed

- O baseline diesel e o comparativo `D85B15` vs `E94H6` agora sao calculados por par selecionado, evitando misturar arquivos de motores diferentes.
- A descoberta de arquivos `.xlsx` em `raw_FPT/` passou a ser recursiva.
- O modo padrao do pipeline passa a ser selecao por GUI; `PAIR_SELECTION_MODE=auto` fica disponivel como fallback operacional.
- A GUI de pares passou a ignorar `FILE_INCLUDE_REGEX` e sempre listar tudo que estiver disponivel em `raw_FPT/`.
- Os seletores Diesel/Etanol passaram a mostrar nomes longos com quebra de linha, sem slider horizontal.
- A lista de pares selecionados passou a mostrar Diesel/Etanol com quebra de linha, sem tabela horizontal.
- O leitor passou a detectar automaticamente o layout alternativo do arquivo `SWay_P8...D85B15.xlsx`, com `Planilha1`, cabecalho na segunda linha e aliases de coluna (`qm Fuel`, `P dyno`, `n engine`).
- O leitor agora tambem detecta vazao de ar tanto como `Sensyflow` quanto como `qm Air`, sem depender de ajuste manual por arquivo.
- A pressao de coletor `P_i_MF` agora e normalizada para `mBar`, convertendo automaticamente series em `bar`, `kPa` ou `mBar` conforme a magnitude dos dados.
- O torque agora usa `M_dyno` ou `M dyno` como fonte principal, com fallback para `9550 * Power_kW / RPM` se o canal nao estiver disponivel.
- A `BMEP` agora e calculada em `bar` pela relacao de 4 tempos com torque e cilindrada detectada do motor.
- A curva do compressor agora usa `P_B_Compr` e `P_B_IC` como pressoes relativas, converte ambas para absolutas com base em `1013 mBar` e plota `PRatio_abs` contra potencia, vazao massica e vazao volumetrica.
- A vazao volumetrica do compressor agora considera umidade relativa via `CAIR_H1` ou `RH air`; quando a umidade nao existe no arquivo, o pipeline assume `0% RH` e informa isso no log.
- Corrigida a heuristica de conversao de pressao para preservar leituras negativas pequenas em `mBar` no `p b compr` do SWay; antes disso, o diesel do `C13` ficava com `PRatio_abs` invalido e sumia da curva do compressor.
- A eficiencia volumetrica agora usa `1013 mBar` de referencia, `T_i_MF` como temperatura de referencia e cilindrada detectada pelo nome do arquivo (`NEF67/NEF6 -> 6,7 L`; `C13/Cursore 13/Cursor 13 -> 12,9 L`) com `6` cilindros.
- Adicionada a eficiencia volumetrica corrigida pela pressao do coletor, usando `P_i_MF_abs = P_i_MF_rel + 1013 mBar` e `T_i_MF`, para separar o enchimento real de aspiracao do ganho aparente por boost.
- A potencia dissipada no intercooler agora usa `Air_kg_h * cp_ar * (T_B_IC - T_i_MF)`, com `cp_ar = 1,005 kJ/kg.K`.
- Os plots de custo especifico passaram a explicitar `R$/kWh` de forma mais visivel no titulo e no eixo Y.
- Os titulos dos plots por par agora incluem automaticamente a familia do motor, unificando `NEF6/NEF67` como `NEF67` e `C13/Cursor/Cursore 13` como `Cursor 13`.
- O fluxo do FPT agora salva o `lv_kpis_fpt.xlsx` bruto e so depois aplica o filtro manual de pontos para comparativos e plots.

## 2026-03-12

### Added

- Criado o pipeline standalone `pipeline_FPT.py` para comparacao Diesel `D85B15` vs Etanol `E94H6` com arquivos `.xlsx` FPT.
- Criado o config dedicado `config_pipeline_fpt.xlsx`.
- Criados `README.md`, `HANDOFF_FPT.md`, `.gitignore`, `.gitattributes` e `requirements.txt`.
- Gerados e versionados os outputs iniciais em `out_FPT/`.
- Adicionado o plot `out_FPT/plots/power_kw_vs_rpm.png`.

### Changed

- Eixo X dos graficos ajustado para `RPM` com passo fixo de `250 rpm`.
- `out_FPT/` passou a ser versionado no Git; `raw_FPT/` permanece fora do repositorio.
- Documentacao atualizada para refletir a estrutura final do projeto FPT.

### Git

- `ee53080` Initial FPT diesel-ethanol RPM comparison pipeline
- `cd04ec7` Track FPT outputs and add power-vs-RPM plot
