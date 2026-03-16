# Changelog

Todas as mudancas relevantes deste repositorio devem ser registradas aqui.

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
  - `Diesel_Baseline_Eta_v_pct`
  - `Delta_Eta_v_pct_vs_Diesel`
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
- A eficiencia volumetrica agora usa `1013 mBar` de referencia, `T_i_MF` como temperatura de referencia e cilindrada detectada pelo nome do arquivo (`NEF67/NEF6 -> 6,7 L`; `C13/Cursore 13/Cursor 13 -> 12,9 L`) com `6` cilindros.
- A potencia dissipada no intercooler agora usa `Air_kg_h * cp_ar * (T_B_IC - T_i_MF)`, com `cp_ar = 1,005 kJ/kg.K`.
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
