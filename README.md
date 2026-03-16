# pipeline_FPT

Pipeline standalone para comparar um motor Diesel `D85B15` vs Etanol `E94H6` a partir de arquivos `.xlsx` do banco FPT.

## Escopo

- Le arquivos `.xlsx` da aba `D`
- Usa:
  - `FB_VAL` para vazao massica de combustivel
  - `P_dyno` para potencia em `kW`
  - `SPEED` para rotacao do motor
- Agrega resultados por `RPM`
- Compara:
  - consumo massico
  - consumo volumetrico
  - vazao de ar
  - vazao de ar por potencia
  - pressao no coletor em `mBar`
  - torque em `Nm`
  - `BMEP` em `bar`
  - curva de operacao do turbo-compressor
  - eficiencia volumetrica
  - eficiencia volumetrica corrigida pela pressao do coletor
  - potencia dissipada no intercooler
  - custo horario
  - custo especifico em `R$/kWh`
  - `n_th`
  - economias vs diesel
  - cenarios de colheitadeira, trator de transbordo e caminhao

## Estrutura

- `pipeline_FPT.py`: pipeline principal
- `config_pipeline_fpt.xlsx`: configuracao especifica
- `HANDOFF_FPT.md`: status atual e observacoes de manutencao
- `CHANGELOG.md`: historico incremental das mudancas do projeto
- `raw_FPT/`: dados brutos locais, fora do Git
- `out_FPT/`: saidas geradas e versionadas neste repositorio

## Como rodar

```powershell
python .\pipeline_FPT.py
```

Se estiver usando o mesmo ambiente do projeto anterior:

```powershell
C:\Users\SC61730\Downloads\Processamento_mestrado_28\Processamentos\.venv\Scripts\python.exe .\pipeline_FPT.py
```

Ao iniciar, o pipeline agora abre uma GUI para ler `raw_FPT/` e deixar voce montar explicitamente os pares Diesel vs Etanol que devem entrar no comparativo da rodada.

## Configuracao

Edite `config_pipeline_fpt.xlsx`, aba `Defaults`.

Parametros principais:

- `RAW_INPUT_DIR`
- `OUT_DIR`
- `FILE_INCLUDE_REGEX`
- `WORKSHEET_NAME`
- `FUEL_MASS_COL`
- `POWER_COL`
- `SPEED_COL`
- `PAIR_SELECTION_MODE`:
  - `gui` = abre a GUI de pares e deixa escolher manualmente
  - `auto` = tenta parear diesel e etanol automaticamente pela ordem dos arquivos filtrados
- `PLOT_POINT_FILTER_MODE`:
  - `gui` = abre a GUI de selecao de pontos antes dos comparativos e plots
  - `off` = pula esse filtro
- densidades, custos e `LHV`
- cenarios de maquinas (`horas/ano` e `diesel L/h`)

Observacoes da selecao de pares:

- a GUI sempre faz scan completo de `raw_FPT/` ao abrir e mostra todos os `.xlsx` disponiveis para escolha;
- `FILE_INCLUDE_REGEX` nao limita a tela da GUI; ele continua util apenas para modos automaticos/filtros operacionais;
- cada comparativo passa a ser feito por `Pair_ID`, sem misturar motores diferentes no mesmo baseline;
- a ultima selecao fica salva localmente em `%LOCALAPPDATA%\pipeline_fpt\last_pair_selection.json`;
- os nomes dos arquivos aparecem com quebra de linha nos seletores Diesel/Etanol, sem depender de slider horizontal;
- a coluna de pares selecionados tambem mostra Diesel/Etanol com quebra de linha;
- se mais de um par for escolhido, os plots saem em subpastas dentro de `out_FPT/plots/`.

Compatibilidade de leitura:

- o leitor agora aceita tanto o layout FPT antigo com aba `D` quanto o layout alternativo do arquivo `SWay_P8...`, que vem com `Planilha1`, uma linha numerica antes do cabecalho real e nomes como `qm Fuel`, `P dyno` e `n engine`;
- a vazao de ar e lida automaticamente como `Sensyflow` no layout antigo e como `qm Air` no layout SWay;
- a pressao de coletor `P_i_MF` tambem e lida automaticamente, incluindo o alias `p i MF` do SWay, e o pipeline normaliza tudo para `mBar`;
- a temperatura de coletor `T_i_MF` e a temperatura antes do intercooler `T_B_IC` tambem entram automaticamente, incluindo os aliases do SWay;
- quando o layout alternativo e detectado, o pipeline ajusta `sheet/header` automaticamente e informa isso no log.

Premissas termofluidicas:

- cilindrada do motor detectada pelo nome do arquivo:
  - `NEF67` ou `NEF6` -> `6,7 L`
  - `C13`, `Cursore 13` ou `Cursor 13` -> `12,9 L`
- eficiencia volumetrica:
  - referencia de pressao fixa em `1013 mBar`
  - temperatura de referencia do coletor `T_i_MF`
  - cilindrada total detectada automaticamente pelo nome do arquivo
  - `6` cilindros
- eficiencia volumetrica corrigida pela pressao do coletor:
  - usa `P_i_MF_abs = P_i_MF_rel + 1013 mBar`
  - usa `T_i_MF` como temperatura de referencia
  - remove o ganho aparente de enchimento causado pelo boost no coletor
  - sai como `%` no campo `Eta_v_corr_press_pct`
- potencia dissipada no intercooler:
  - usa `Air_kg_h`
  - usa `T_B_IC - T_i_MF`
  - usa `cp_ar = 1,005 kJ/kg.K`
- `BMEP`:
  - usa `Torque_Nm`
  - usa a cilindrada total detectada do motor
  - formula de 4 tempos: `BMEP = 4 * pi * T / Vd`
  - saida final em `bar`
- curva do compressor:
  - `PRatio_abs = P_B_IC_abs / P_B_Compr_abs`
  - `P_B_Compr` e `P_B_IC` sao lidas como pressao relativa e convertidas para absoluta somando `1013 mBar`
  - a vazao volumetrica usa `Air_kg_h`, `T_AIR/Air_tAFS`, pressao absoluta na entrada do compressor e umidade relativa
  - a umidade relativa vem de `CAIR_H1` no caso do ConsysAir e de `RH air` nas provas fora da PUC
  - se a umidade nao existir no arquivo, o pipeline assume `0% RH` e avisa no log

Filtro de pontos para plot:

- depois de salvar o `lv_kpis_fpt.xlsx` bruto, o pipeline pode abrir uma GUI em grade para marcar/desmarcar conjuntos por `Pair_ID/Fuel_Label` nas colunas e `RPM` nas linhas;
- a ultima selecao fica salva em `%LOCALAPPDATA%\pipeline_fpt\plot_point_filter_last.json`;
- o filtro vale para os comparativos e plots da rodada, mas nao apaga pontos do `lv_kpis_fpt.xlsx` bruto;
- isso permite excluir manualmente outliers de plot no estilo do filtro de cargas da pipeline NANUM, sem forcar deteccao automatica no codigo.

## Saidas

- `out_FPT/lv_kpis_fpt.xlsx`
- `out_FPT/compare_rpm_diesel_vs_e94h6_fpt.xlsx`
- `out_FPT/compare_<pair_id>.xlsx` quando houver mais de um par selecionado
- graficos em `out_FPT/plots`

Inclui tambem:

- `out_FPT/plots/power_kw_vs_rpm.png`
- `out_FPT/plots/custo_especifico_r_kwh_vs_rpm.png`
- `out_FPT/plots/vazao_ar_kg_h_vs_rpm.png`
- `out_FPT/plots/vazao_ar_kg_h_kw_vs_rpm.png`
- `out_FPT/plots/pressao_coletor_mbar_vs_rpm.png`
- `out_FPT/plots/torque_nm_vs_rpm.png`
- `out_FPT/plots/bmep_bar_vs_rpm.png`
- `out_FPT/plots/curva_compressor_pratio_vs_power_kw.png`
- `out_FPT/plots/curva_compressor_pratio_vs_vazao_massica_kg_h.png`
- `out_FPT/plots/curva_compressor_pratio_vs_vazao_volumetrica_m3_s.png`
- `out_FPT/plots/eficiencia_volumetrica_vs_rpm.png`
- `out_FPT/plots/eficiencia_volumetrica_corrigida_pressao_vs_rpm.png`
- `out_FPT/plots/potencia_intercooler_kw_vs_rpm.png`
- `out_FPT/plots/economia_r_kwh_vs_diesel_rpm.png`
- `out_FPT/plots/economia_pct_r_kwh_vs_diesel_rpm.png`

## Observacoes

- O eixo X dos graficos usa `RPM` com grade fixa de `250 rpm`.
- O reconhecimento de combustivel no nome do arquivo aceita `D85B15`, `E94H6`, `ETHANOL` e `ETANOL`.
- Se `horas/ano` e `diesel L/h` parecerem invertidos no config, o pipeline troca automaticamente e emite aviso.
- Os arquivos `.xlsx` e `.png` sao tratados como binarios via `.gitattributes`.
- `raw_FPT/` continua fora do Git; `out_FPT/` passa a ser versionado.
- Toda alteracao relevante deve entrar em `CHANGELOG.md`.
