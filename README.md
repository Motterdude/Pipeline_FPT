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
  - custo horario
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
- densidades, custos e `LHV`
- cenarios de maquinas (`horas/ano` e `diesel L/h`)

## Saidas

- `out_FPT/lv_kpis_fpt.xlsx`
- `out_FPT/compare_rpm_diesel_vs_e94h6_fpt.xlsx`
- graficos em `out_FPT/plots`

Inclui tambem:

- `out_FPT/plots/power_kw_vs_rpm.png`

## Observacoes

- O eixo X dos graficos usa `RPM` com grade fixa de `250 rpm`.
- O reconhecimento de combustivel no nome do arquivo aceita `D85B15`, `E94H6`, `ETHANOL` e `ETANOL`.
- Se `horas/ano` e `diesel L/h` parecerem invertidos no config, o pipeline troca automaticamente e emite aviso.
- Os arquivos `.xlsx` e `.png` sao tratados como binarios via `.gitattributes`.
- `raw_FPT/` continua fora do Git; `out_FPT/` passa a ser versionado.
- Toda alteracao relevante deve entrar em `CHANGELOG.md`.
