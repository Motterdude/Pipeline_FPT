# Changelog

Todas as mudancas relevantes deste repositorio devem ser registradas aqui.

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
