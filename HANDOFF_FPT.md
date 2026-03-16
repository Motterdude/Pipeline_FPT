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
- `Custo_R_kWh`
- `n_th` e `n_th_pct`
- baseline diesel por `RPM`
- `Economia_vs_Diesel_R_h`
- `Economia_vs_Diesel_pct`
- `Economia_vs_Diesel_R_kWh`
- `Economia_vs_Diesel_R_kWh_pct`
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
- manter `raw_FPT/` fora do Git
- versionar `out_FPT/` quando os resultados precisarem acompanhar o codigo
- `xlsx` e `png` sao marcados como binarios em `.gitattributes`
- se o layout dos `.xlsx` mudar, revisar primeiro a funcao `read_fpt_xlsx`
- registrar cada passo relevante em `CHANGELOG.md`
