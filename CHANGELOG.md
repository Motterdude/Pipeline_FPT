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
- Plots novos:
  - `custo_especifico_r_kwh_vs_rpm.png`
  - `economia_r_kwh_vs_diesel_rpm.png`
  - `economia_pct_r_kwh_vs_diesel_rpm.png`
  - `vazao_ar_kg_h_vs_rpm.png`
  - `vazao_ar_kg_h_kw_vs_rpm.png`
  - `pressao_coletor_mbar_vs_rpm.png`

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
