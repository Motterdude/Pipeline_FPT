# pipeline_FPT

Pipeline standalone para comparar um motor Diesel `D85B15` vs Etanol `E94H6` a partir de arquivos `.xlsx` do banco FPT.

## Escopo

- Lê arquivos `.xlsx` da aba `D`
- Usa:
  - `FB_VAL` para vazão mássica de combustível
  - `P_dyno` para potência em `kW`
  - `SPEED` para rotação do motor
- Agrega resultados por `RPM`
- Compara:
  - consumo mássico
  - consumo volumétrico
  - custo horário
  - `n_th`
  - economias vs diesel
  - cenários de colheitadeira, trator de transbordo e caminhão

## Estrutura

- `pipeline_FPT.py`: pipeline principal
- `config_pipeline_fpt.xlsx`: configuração específica
- `HANDOFF_FPT.md`: status atual e observações de manutenção
- `raw_FPT/`: dados brutos locais, fora do Git
- `out_FPT/`: saídas locais, fora do Git

## Como rodar

```powershell
python .\pipeline_FPT.py
```

Se estiver usando o mesmo ambiente do projeto anterior:

```powershell
C:\Users\SC61730\Downloads\Processamento_mestrado_28\Processamentos\.venv\Scripts\python.exe .\pipeline_FPT.py
```

## Configuração

Edite `config_pipeline_fpt.xlsx`, aba `Defaults`.

Parâmetros principais:

- `RAW_INPUT_DIR`
- `OUT_DIR`
- `FILE_INCLUDE_REGEX`
- `WORKSHEET_NAME`
- `FUEL_MASS_COL`
- `POWER_COL`
- `SPEED_COL`
- densidades, custos e `LHV`
- cenários de máquinas (`horas/ano` e `diesel L/h`)

## Saídas

- `out_FPT/lv_kpis_fpt.xlsx`
- `out_FPT/compare_rpm_diesel_vs_e94h6_fpt.xlsx`
- gráficos em `out_FPT/plots`

## Observações

- O eixo X dos gráficos usa `RPM` com grade fixa de `250 rpm`.
- O reconhecimento de combustível no nome do arquivo aceita `D85B15`, `E94H6`, `ETHANOL` e `ETANOL`.
- Se `horas/ano` e `diesel L/h` parecerem invertidos no config, o pipeline troca automaticamente e emite aviso.
