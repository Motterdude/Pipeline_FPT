from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception:
    tk = None
    messagebox = None
    ttk = None


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = ROOT_DIR / "raw_FPT"
DEFAULT_OUT_DIR = ROOT_DIR / "out_FPT"
DEFAULT_CONFIG_PATH = ROOT_DIR / "config_pipeline_fpt.xlsx"
RPM_TICK_STEP = 250.0
LOCAL_STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "pipeline_fpt"
PAIR_SELECTION_PATH = LOCAL_STATE_DIR / "last_pair_selection.json"

FUEL_SPECS = {
    "D85B15": {
        "density_param": "FUEL_DENSITY_KG_M3_D85B15",
        "cost_param": "FUEL_COST_R_L_D85B15",
        "lhv_param": "LHV_KJ_KG_D85B15",
        "color": "#1f77b4",
    },
    "E94H6": {
        "density_param": "FUEL_DENSITY_KG_M3_E94H6",
        "cost_param": "FUEL_COST_R_L_E94H6",
        "lhv_param": "LHV_KJ_KG_E94H6",
        "color": "#d62728",
    },
}

MACHINE_SCENARIO_SPECS = [
    {
        "key": "Colheitadeira",
        "label": "Colheitadeira",
        "hours_param": "MACHINE_HOURS_PER_YEAR_COLHEITADEIRA",
        "diesel_l_h_param": "MACHINE_DIESEL_L_H_COLHEITADEIRA",
        "color": "#1f77b4",
    },
    {
        "key": "Trator_Transbordo",
        "label": "Trator transbordo",
        "hours_param": "MACHINE_HOURS_PER_YEAR_TRATOR_TRANSBORDO",
        "diesel_l_h_param": "MACHINE_DIESEL_L_H_TRATOR_TRANSBORDO",
        "color": "#ff7f0e",
    },
    {
        "key": "Caminhao",
        "label": "Caminhao",
        "hours_param": "MACHINE_HOURS_PER_YEAR_CAMINHAO",
        "diesel_l_h_param": "MACHINE_DIESEL_L_H_CAMINHAO",
        "color": "#2ca02c",
    },
]


@dataclass(frozen=True)
class FptComparePair:
    pair_id: str
    pair_label: str
    diesel_path: Path
    ethanol_path: Path


def norm_key(value: object) -> str:
    return str(value or "").strip().lower()


def slugify_token(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "item"


def make_pair_id(diesel_path: Path, ethanol_path: Path) -> str:
    diesel_token = slugify_token(diesel_path.stem)
    ethanol_token = slugify_token(ethanol_path.stem)
    return f"{diesel_token}__vs__{ethanol_token}"


def make_pair_label(diesel_path: Path, ethanol_path: Path) -> str:
    return f"{diesel_path.stem} vs {ethanol_path.stem}"


def _to_float(value: object, default: float = float("nan")) -> float:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip().replace(",", ".")
    if not text:
        return default
    try:
        return float(text)
    except Exception:
        return default


def load_last_pair_selection() -> List[Tuple[str, str]]:
    try:
        if not PAIR_SELECTION_PATH.exists():
            return []
        payload = json.loads(PAIR_SELECTION_PATH.read_text(encoding="utf-8"))
        raw_pairs = payload.get("pairs", [])
        out: List[Tuple[str, str]] = []
        for item in raw_pairs:
            diesel_raw = str(item.get("diesel_path", "")).strip()
            ethanol_raw = str(item.get("ethanol_path", "")).strip()
            if diesel_raw and ethanol_raw:
                out.append((diesel_raw, ethanol_raw))
        return out
    except Exception:
        return []


def save_last_pair_selection(pairs: List[FptComparePair]) -> None:
    LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "pairs": [
            {
                "pair_id": pair.pair_id,
                "pair_label": pair.pair_label,
                "diesel_path": str(pair.diesel_path),
                "ethanol_path": str(pair.ethanol_path),
            }
            for pair in pairs
        ]
    }
    PAIR_SELECTION_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def safe_to_excel(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_excel(path, index=False)
        return path
    except PermissionError:
        alt = path.with_name(f"{path.stem}_new{path.suffix}")
        df.to_excel(alt, index=False)
        return alt


def resolve_col(df: pd.DataFrame, requested: str) -> str:
    req = str(requested or "").strip()
    if not req:
        raise KeyError("Nome de coluna solicitado esta vazio.")
    if req in df.columns:
        return req

    low_map = {str(c).strip().lower(): c for c in df.columns}
    req_low = req.lower()
    if req_low in low_map:
        return low_map[req_low]

    canon_map = {
        re.sub(r"[^a-z0-9]+", "", str(c).strip().lower()): c
        for c in df.columns
    }
    req_canon = re.sub(r"[^a-z0-9]+", "", req_low)
    if req_canon in canon_map:
        return canon_map[req_canon]

    raise KeyError(f"Coluna '{requested}' nao encontrada.")


def load_defaults_config(path: Path) -> Dict[str, str]:
    df = pd.read_excel(path, sheet_name="Defaults")
    out: Dict[str, str] = {}
    if df.empty:
        return out

    col_param = resolve_col(df, "param")
    col_value = resolve_col(df, "value")
    for _, row in df.iterrows():
        param = str(row.get(col_param, "")).strip()
        if not param or param.lower() in {"global parameter name.", "nan"}:
            continue
        out[norm_key(param)] = "" if pd.isna(row.get(col_value, pd.NA)) else str(row[col_value]).strip()
    return out


def discover_input_files(raw_dir: Path, include_regex: str) -> List[Path]:
    files = sorted(p for p in raw_dir.rglob("*.xlsx") if p.is_file() and not p.name.startswith("~$"))
    if not include_regex:
        return files
    pattern = re.compile(include_regex)
    return [p for p in files if pattern.search(p.name)]


def build_selected_pairs_from_paths(raw_pairs: List[Tuple[Path, Path]]) -> List[FptComparePair]:
    out: List[FptComparePair] = []
    seen_ids: Dict[str, int] = {}
    for diesel_path, ethanol_path in raw_pairs:
        base_id = make_pair_id(diesel_path, ethanol_path)
        n = seen_ids.get(base_id, 0) + 1
        seen_ids[base_id] = n
        pair_id = base_id if n == 1 else f"{base_id}_{n:02d}"
        out.append(
            FptComparePair(
                pair_id=pair_id,
                pair_label=make_pair_label(diesel_path, ethanol_path),
                diesel_path=diesel_path,
                ethanol_path=ethanol_path,
            )
        )
    return out


def _default_pair_candidates(files: List[Path]) -> List[Tuple[Path, Path]]:
    diesel_files = [p for p in files if parse_fuel_label(p) == "D85B15"]
    ethanol_files = [p for p in files if parse_fuel_label(p) == "E94H6"]
    raw_pairs = load_last_pair_selection()
    if raw_pairs:
        path_map = {str(p.resolve()): p for p in files}
        restored_pairs: List[Tuple[Path, Path]] = []
        for diesel_raw, ethanol_raw in raw_pairs:
            diesel_path = path_map.get(str(Path(diesel_raw).resolve()))
            ethanol_path = path_map.get(str(Path(ethanol_raw).resolve()))
            if diesel_path is not None and ethanol_path is not None:
                restored_pairs.append((diesel_path, ethanol_path))
        if restored_pairs:
            return restored_pairs

    if len(diesel_files) == 1 and len(ethanol_files) == 1:
        return [(diesel_files[0], ethanol_files[0])]
    return []


def select_pairs_via_gui(raw_dir: Path, files: List[Path]) -> List[FptComparePair]:
    if tk is None or ttk is None or messagebox is None:
        raise RuntimeError("Tkinter nao esta disponivel neste Python.")

    diesel_files = [p for p in files if parse_fuel_label(p) == "D85B15"]
    ethanol_files = [p for p in files if parse_fuel_label(p) == "E94H6"]
    if not diesel_files or not ethanol_files:
        raise RuntimeError("Preciso de pelo menos um arquivo diesel e um arquivo etanol para montar pares.")

    selected_pairs: List[Tuple[Path, Path]] = list(_default_pair_candidates(files))
    result: Dict[str, List[FptComparePair] | bool] = {"pairs": [], "ok": False}

    def rel_name(path: Path) -> str:
        try:
            return str(path.relative_to(raw_dir))
        except Exception:
            return path.name

    root = tk.Tk()
    root.title("Selecao de pares FPT")
    root.geometry("1200x720")
    root.minsize(1080, 640)

    header = ttk.Label(
        root,
        text="Selecione os pares diesel vs etanol que devem entrar no comparativo desta rodada.",
        font=("Segoe UI", 11, "bold"),
    )
    header.pack(fill="x", padx=12, pady=(12, 6))

    info = ttk.Label(
        root,
        text=f"RAW: {raw_dir}",
        wraplength=1120,
        justify="left",
    )
    info.pack(fill="x", padx=12, pady=(0, 10))

    body = ttk.Frame(root)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=1)
    body.columnconfigure(2, weight=2)
    body.rowconfigure(1, weight=1)

    ttk.Label(body, text="Diesel").grid(row=0, column=0, sticky="w", padx=(0, 6))
    ttk.Label(body, text="Etanol").grid(row=0, column=1, sticky="w", padx=(6, 6))
    ttk.Label(body, text="Pares selecionados").grid(row=0, column=2, sticky="w", padx=(6, 0))

    diesel_list = tk.Listbox(body, exportselection=False)
    ethanol_list = tk.Listbox(body, exportselection=False)
    pair_list = ttk.Treeview(body, columns=("diesel", "ethanol"), show="headings", selectmode="browse")
    pair_list.heading("diesel", text="Diesel")
    pair_list.heading("ethanol", text="Etanol")
    pair_list.column("diesel", width=300, anchor="w")
    pair_list.column("ethanol", width=360, anchor="w")

    diesel_list.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
    ethanol_list.grid(row=1, column=1, sticky="nsew", padx=(6, 6))
    pair_list.grid(row=1, column=2, sticky="nsew", padx=(6, 0))

    for path in diesel_files:
        diesel_list.insert("end", rel_name(path))
    for path in ethanol_files:
        ethanol_list.insert("end", rel_name(path))

    path_lookup = {rel_name(path): path for path in files}

    def refresh_pairs() -> None:
        for item_id in pair_list.get_children():
            pair_list.delete(item_id)
        for idx, (diesel_path, ethanol_path) in enumerate(selected_pairs, start=1):
            pair_list.insert("", "end", iid=f"pair_{idx}", values=(rel_name(diesel_path), rel_name(ethanol_path)))

    def add_pair() -> None:
        diesel_idx = diesel_list.curselection()
        ethanol_idx = ethanol_list.curselection()
        if not diesel_idx or not ethanol_idx:
            messagebox.showwarning("Par incompleto", "Selecione um arquivo diesel e um arquivo etanol.")
            return
        diesel_path = diesel_files[int(diesel_idx[0])]
        ethanol_path = ethanol_files[int(ethanol_idx[0])]
        candidate = (diesel_path, ethanol_path)
        if candidate in selected_pairs:
            messagebox.showinfo("Par ja existe", "Esse par ja esta na lista.")
            return
        selected_pairs.append(candidate)
        refresh_pairs()

    def remove_pair() -> None:
        selected = pair_list.selection()
        if not selected:
            return
        item = pair_list.item(selected[0])
        diesel_raw, ethanol_raw = item.get("values", ["", ""])
        diesel_path = path_lookup.get(str(diesel_raw))
        ethanol_path = path_lookup.get(str(ethanol_raw))
        if diesel_path is None or ethanol_path is None:
            return
        selected_pairs[:] = [pair for pair in selected_pairs if pair != (diesel_path, ethanol_path)]
        refresh_pairs()

    def accept() -> None:
        if not selected_pairs:
            messagebox.showwarning("Sem pares", "Adicione pelo menos um par para continuar.")
            return
        pairs = build_selected_pairs_from_paths(selected_pairs)
        result["pairs"] = pairs
        result["ok"] = True
        save_last_pair_selection(pairs)
        root.destroy()

    def cancel() -> None:
        result["ok"] = False
        root.destroy()

    action_bar = ttk.Frame(root)
    action_bar.pack(fill="x", padx=12, pady=(0, 12))

    ttk.Button(action_bar, text="Adicionar par", command=add_pair).pack(side="left")
    ttk.Button(action_bar, text="Remover par", command=remove_pair).pack(side="left", padx=(8, 0))
    ttk.Button(action_bar, text="Cancelar", command=cancel).pack(side="right")
    ttk.Button(action_bar, text="Rodar com estes pares", command=accept).pack(side="right", padx=(0, 8))

    refresh_pairs()
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.state("zoomed")
    root.mainloop()

    if not bool(result["ok"]):
        raise SystemExit("Execucao cancelada pelo usuario na selecao de pares.")

    pairs = result.get("pairs", [])
    return list(pairs) if isinstance(pairs, list) else []


def resolve_selected_pairs(
    *,
    raw_dir: Path,
    files: List[Path],
    pair_selection_mode: str,
) -> List[FptComparePair]:
    mode = norm_key(pair_selection_mode) or "gui"
    if mode in {"gui", "pair_gui", "pairs_gui"}:
        if tk is not None and ttk is not None and messagebox is not None:
            return select_pairs_via_gui(raw_dir, files)
        print("[WARN] Tkinter nao esta disponivel; caindo para pareamento automatico.")
        mode = "auto"

    diesel_files = [p for p in files if parse_fuel_label(p) == "D85B15"]
    ethanol_files = [p for p in files if parse_fuel_label(p) == "E94H6"]
    auto_pairs = list(zip(diesel_files, ethanol_files))
    if not auto_pairs:
        raise SystemExit("Nao consegui montar pares automaticamente a partir dos arquivos encontrados.")
    return build_selected_pairs_from_paths(auto_pairs)


def parse_fuel_label(path: Path) -> Optional[str]:
    name = path.name.upper()
    if "D85B15" in name:
        return "D85B15"
    if ("E94H6" in name) or ("ETHANOL" in name) or ("ETANOL" in name):
        return "E94H6"
    return None


def read_fpt_xlsx(
    path: Path,
    *,
    pair_id: str,
    pair_label: str,
    sheet_name: str,
    fuel_mass_col: str,
    power_col: str,
    speed_col: str,
    rpm_round_digits: int,
) -> pd.DataFrame:
    fuel_label = parse_fuel_label(path)
    if not fuel_label:
        print(f"[INFO] Pulei {path.name}: combustivel nao reconhecido no nome.")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name=sheet_name, dtype=object)
    fb_col = resolve_col(df, fuel_mass_col)
    p_col = resolve_col(df, power_col)
    rpm_col = resolve_col(df, speed_col)

    out = pd.DataFrame(
        {
            "Pair_ID": pair_id,
            "Pair_Label": pair_label,
            "Source_File": path.name,
            "Fuel_Label": fuel_label,
            "Consumo_kg_h": pd.to_numeric(df[fb_col], errors="coerce"),
            "Power_kW": pd.to_numeric(df[p_col], errors="coerce"),
            "Speed_RPM_raw": pd.to_numeric(df[rpm_col], errors="coerce"),
        }
    )
    out = out.dropna(subset=["Consumo_kg_h", "Power_kW", "Speed_RPM_raw"]).copy()
    out["RPM"] = out["Speed_RPM_raw"].round(rpm_round_digits)
    out = out.dropna(subset=["RPM"]).copy()
    return out


def aggregate_curve_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    g = (
        df.groupby(["Pair_ID", "Pair_Label", "Fuel_Label", "RPM"], dropna=False, sort=True)
        .agg(
            Speed_RPM=("Speed_RPM_raw", "mean"),
            Power_kW=("Power_kW", "mean"),
            Consumo_kg_h=("Consumo_kg_h", "mean"),
            Power_kW_sd=("Power_kW", "std"),
            Consumo_kg_h_sd=("Consumo_kg_h", "std"),
            N_points=("Power_kW", "count"),
            Source_Files=("Source_File", lambda s: "; ".join(sorted(set(str(v) for v in s if str(v).strip())))),
        )
        .reset_index()
    )
    return g


def attach_fuel_properties(df: pd.DataFrame, defaults_cfg: Dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    out["Fuel_Density_kg_m3"] = pd.NA
    out["Fuel_Cost_R_L"] = pd.NA
    out["LHV_kJ_kg"] = pd.NA

    for label, spec in FUEL_SPECS.items():
        mask = out["Fuel_Label"].eq(label)
        if not bool(mask.any()):
            continue
        density = _to_float(defaults_cfg.get(norm_key(spec["density_param"]), ""), default=float("nan"))
        cost = _to_float(defaults_cfg.get(norm_key(spec["cost_param"]), ""), default=float("nan"))
        lhv = _to_float(defaults_cfg.get(norm_key(spec["lhv_param"]), ""), default=float("nan"))
        out.loc[mask, "Fuel_Density_kg_m3"] = density if np.isfinite(density) and density > 0 else pd.NA
        out.loc[mask, "Fuel_Cost_R_L"] = cost if np.isfinite(cost) and cost > 0 else pd.NA
        out.loc[mask, "LHV_kJ_kg"] = lhv if np.isfinite(lhv) and lhv > 0 else pd.NA

    return out


def compute_base_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    fuel_density = pd.to_numeric(out["Fuel_Density_kg_m3"], errors="coerce")
    fuel_cost = pd.to_numeric(out["Fuel_Cost_R_L"], errors="coerce")
    lhv = pd.to_numeric(out["LHV_kJ_kg"], errors="coerce")
    consumo_kg_h = pd.to_numeric(out["Consumo_kg_h"], errors="coerce")
    power_kw = pd.to_numeric(out["Power_kW"], errors="coerce")

    out["Consumo_L_h"] = (consumo_kg_h * 1000.0 / fuel_density).where(fuel_density.gt(0), pd.NA)
    out["Custo_R_h"] = (pd.to_numeric(out["Consumo_L_h"], errors="coerce") * fuel_cost).where(fuel_cost.gt(0), pd.NA)
    mdot = consumo_kg_h / 3600.0
    out["n_th"] = (power_kw / (mdot * lhv)).where((power_kw > 0) & (mdot > 0) & (lhv > 0), pd.NA)
    out["n_th_pct"] = pd.to_numeric(out["n_th"], errors="coerce") * 100.0
    return out


def attach_diesel_baseline(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    diesel = out[out["Fuel_Label"].eq("D85B15")].copy()
    if diesel.empty:
        print("[WARN] Nao encontrei pontos D85B15 para baseline.")
        return out

    baseline_cols = ["Pair_ID", "RPM", "Consumo_kg_h", "Consumo_L_h", "Custo_R_h", "n_th_pct", "Power_kW"]
    diesel = diesel[baseline_cols].rename(
        columns={
            "Consumo_kg_h": "Diesel_Baseline_Consumo_kg_h",
            "Consumo_L_h": "Diesel_Baseline_Consumo_L_h",
            "Custo_R_h": "Diesel_Baseline_Custo_R_h",
            "n_th_pct": "Diesel_Baseline_n_th_pct",
            "Power_kW": "Diesel_Baseline_Power_kW",
        }
    )

    out = out.merge(diesel, on=["Pair_ID", "RPM"], how="left")

    custo = pd.to_numeric(out["Custo_R_h"], errors="coerce")
    custo_bl = pd.to_numeric(out["Diesel_Baseline_Custo_R_h"], errors="coerce")
    cons_m = pd.to_numeric(out["Consumo_kg_h"], errors="coerce")
    cons_m_bl = pd.to_numeric(out["Diesel_Baseline_Consumo_kg_h"], errors="coerce")
    cons_v = pd.to_numeric(out["Consumo_L_h"], errors="coerce")
    cons_v_bl = pd.to_numeric(out["Diesel_Baseline_Consumo_L_h"], errors="coerce")
    nth = pd.to_numeric(out["n_th_pct"], errors="coerce")
    nth_bl = pd.to_numeric(out["Diesel_Baseline_n_th_pct"], errors="coerce")

    out["Economia_vs_Diesel_R_h"] = (custo - custo_bl).where(custo_bl.gt(0), pd.NA)
    out["Economia_vs_Diesel_pct"] = (100.0 * (custo / custo_bl - 1.0)).where(custo_bl.gt(0), pd.NA)
    out["Delta_Consumo_kg_h_vs_Diesel"] = cons_m - cons_m_bl
    out["Delta_Consumo_L_h_vs_Diesel"] = cons_v - cons_v_bl
    out["Delta_n_th_pct_vs_Diesel"] = nth - nth_bl

    diesel_mask = out["Fuel_Label"].eq("D85B15")
    zero_cols = [
        "Economia_vs_Diesel_R_h",
        "Economia_vs_Diesel_pct",
        "Delta_Consumo_kg_h_vs_Diesel",
        "Delta_Consumo_L_h_vs_Diesel",
        "Delta_n_th_pct_vs_Diesel",
    ]
    for col in zero_cols:
        out.loc[diesel_mask, col] = 0.0
    return out


def _scenario_machine_col(machine_key: str, suffix: str) -> str:
    return f"Scenario_{machine_key}_{suffix}"


def _resolve_machine_scenario_inputs(defaults_cfg: Dict[str, str], spec: Dict[str, str]) -> Tuple[float, float]:
    hours = _to_float(defaults_cfg.get(norm_key(spec["hours_param"]), ""), default=float("nan"))
    diesel_l_h = _to_float(defaults_cfg.get(norm_key(spec["diesel_l_h_param"]), ""), default=float("nan"))

    if np.isfinite(hours) and np.isfinite(diesel_l_h):
        likely_swapped = ((hours < 100.0 and diesel_l_h > 200.0) or (hours < 200.0 and diesel_l_h > 1000.0))
        if likely_swapped:
            hours, diesel_l_h = diesel_l_h, hours
            print(
                f"[WARN] Parametros de maquina parecem invertidos em {spec['label']}. "
                f"Vou usar hours/ano={hours:g} e diesel_L_h={diesel_l_h:g}."
            )
    return hours, diesel_l_h


def attach_machine_scenarios(df: pd.DataFrame, defaults_cfg: Dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    ethanol_mask = out["Fuel_Label"].eq("E94H6")
    economia_pct = pd.to_numeric(out.get("Economia_vs_Diesel_pct", pd.NA), errors="coerce")
    valid_eth = ethanol_mask & economia_pct.notna()

    for spec in MACHINE_SCENARIO_SPECS:
        hours, diesel_l_h = _resolve_machine_scenario_inputs(defaults_cfg, spec)
        if not (np.isfinite(hours) and hours > 0 and np.isfinite(diesel_l_h) and diesel_l_h > 0):
            print(f"[WARN] Cenario {spec['label']} incompleto no config; deixei colunas vazias.")
            continue

        diesel_cost_l = _to_float(defaults_cfg.get(norm_key("FUEL_COST_R_L_D85B15"), ""), default=float("nan"))
        ethanol_cost_l = _to_float(defaults_cfg.get(norm_key("FUEL_COST_R_L_E94H6"), ""), default=float("nan"))
        if not (np.isfinite(diesel_cost_l) and diesel_cost_l > 0 and np.isfinite(ethanol_cost_l) and ethanol_cost_l > 0):
            continue

        ratio = 1.0 + (economia_pct / 100.0)
        valid = valid_eth & ratio.gt(0)
        if not bool(valid.any()):
            continue

        diesel_cost_h = diesel_l_h * diesel_cost_l
        diesel_l_ano = diesel_l_h * hours
        diesel_cost_ano = diesel_cost_h * hours
        ethanol_cost_h = diesel_cost_h * ratio
        ethanol_l_h = ethanol_cost_h / ethanol_cost_l
        ethanol_l_ano = ethanol_l_h * hours
        ethanol_cost_ano = ethanol_cost_h * hours

        const_values = {
            "Hours_Ano": hours,
            "Diesel_L_h": diesel_l_h,
            "Diesel_L_ano": diesel_l_ano,
            "Diesel_Custo_R_h": diesel_cost_h,
            "Diesel_Custo_R_ano": diesel_cost_ano,
        }
        for suffix, value in const_values.items():
            out.loc[valid, _scenario_machine_col(spec["key"], suffix)] = value

        variable_values = {
            "E94H6_L_h": ethanol_l_h,
            "E94H6_L_ano": ethanol_l_ano,
            "E94H6_Custo_R_h": ethanol_cost_h,
            "E94H6_Custo_R_ano": ethanol_cost_ano,
            "Economia_R_h": ethanol_cost_h - diesel_cost_h,
            "Economia_R_ano": ethanol_cost_ano - diesel_cost_ano,
        }
        for suffix, series in variable_values.items():
            out.loc[valid, _scenario_machine_col(spec["key"], suffix)] = pd.to_numeric(series, errors="coerce").where(valid, pd.NA)

    return out


def build_compare_table(df: pd.DataFrame) -> pd.DataFrame:
    diesel = df[df["Fuel_Label"].eq("D85B15")].copy()
    ethanol = df[df["Fuel_Label"].eq("E94H6")].copy()
    if diesel.empty or ethanol.empty:
        return pd.DataFrame()

    diesel = diesel.rename(
        columns={
            "Speed_RPM": "Diesel_Speed_RPM",
            "Power_kW": "Diesel_Power_kW",
            "Consumo_kg_h": "Diesel_Consumo_kg_h",
            "Consumo_L_h": "Diesel_Consumo_L_h",
            "Custo_R_h": "Diesel_Custo_R_h",
            "n_th_pct": "Diesel_n_th_pct",
        }
    )
    ethanol = ethanol.rename(
        columns={
            "Speed_RPM": "E94H6_Speed_RPM",
            "Power_kW": "E94H6_Power_kW",
            "Consumo_kg_h": "E94H6_Consumo_kg_h",
            "Consumo_L_h": "E94H6_Consumo_L_h",
            "Custo_R_h": "E94H6_Custo_R_h",
            "n_th_pct": "E94H6_n_th_pct",
        }
    )

    cols_left = [
        "Pair_ID",
        "Pair_Label",
        "RPM",
        "Diesel_Speed_RPM",
        "Diesel_Power_kW",
        "Diesel_Consumo_kg_h",
        "Diesel_Consumo_L_h",
        "Diesel_Custo_R_h",
        "Diesel_n_th_pct",
    ]
    cols_right = [
        "Pair_ID",
        "RPM",
        "E94H6_Speed_RPM",
        "E94H6_Power_kW",
        "E94H6_Consumo_kg_h",
        "E94H6_Consumo_L_h",
        "E94H6_Custo_R_h",
        "E94H6_n_th_pct",
        "Economia_vs_Diesel_R_h",
        "Economia_vs_Diesel_pct",
    ]
    merged = diesel[cols_left].merge(ethanol[cols_right], on=["Pair_ID", "RPM"], how="inner")
    return merged.sort_values(["Pair_ID", "RPM"]).copy()


def _scaled_tick_formatter(divisor: float) -> FuncFormatter:
    return FuncFormatter(lambda value, _pos: f"{(value / divisor):g}")


def _reserve_upper_legend_headroom(ax, *, ratio: float = 0.25) -> None:
    ymin, ymax = ax.get_ylim()
    if not (np.isfinite(ymin) and np.isfinite(ymax)):
        return
    span = ymax - ymin
    if not np.isfinite(span) or span <= 0:
        span = max(abs(ymax), abs(ymin), 1.0)
    ax.set_ylim(ymin, ymax + span * ratio)


def _style_axes(
    fig,
    ax,
    *,
    x_values: pd.Series,
    title: str,
    y_label: str,
    y_tick_divisor: Optional[float] = None,
) -> None:
    x_num = pd.to_numeric(x_values, errors="coerce").dropna().tolist()
    if x_num:
        xmin = min(x_num)
        xmax = max(x_num)
        x_start = np.floor(xmin / RPM_TICK_STEP) * RPM_TICK_STEP
        x_end = np.ceil(xmax / RPM_TICK_STEP) * RPM_TICK_STEP
        xticks = np.arange(x_start, x_end + RPM_TICK_STEP * 0.5, RPM_TICK_STEP).tolist()
        ax.set_xlim(x_start, x_end)
        ax.set_xticks(xticks)
    ax.set_xlabel("Speed (RPM)")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    if y_tick_divisor is not None and np.isfinite(y_tick_divisor) and y_tick_divisor > 0 and y_tick_divisor != 1.0:
        ax.yaxis.set_major_formatter(_scaled_tick_formatter(float(y_tick_divisor)))

    if ax.get_legend_handles_labels()[0]:
        _reserve_upper_legend_headroom(ax)
        ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()


def plot_dual_fuel_metric(
    df: pd.DataFrame,
    *,
    y_col: str,
    title: str,
    filename: str,
    y_label: str,
    plot_dir: Path,
    y_tick_divisor: Optional[float] = None,
) -> None:
    fig, ax = plt.subplots()
    any_curve = False
    for fuel_label in ["D85B15", "E94H6"]:
        d = df[df["Fuel_Label"].eq(fuel_label)].copy()
        if d.empty or y_col not in d.columns:
            continue
        d["RPM"] = pd.to_numeric(d["RPM"], errors="coerce")
        d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
        d = d.dropna(subset=["RPM", y_col]).sort_values("RPM")
        if d.empty:
            continue
        any_curve = True
        ax.plot(
            d["RPM"],
            d[y_col],
            "o-",
            linewidth=1.8,
            markersize=4.8,
            color=FUEL_SPECS[fuel_label]["color"],
            label=fuel_label,
        )

    if not any_curve:
        plt.close(fig)
        print(f"[WARN] Sem dados para {filename}")
        return

    _style_axes(fig, ax, x_values=df["RPM"], title=title, y_label=y_label, y_tick_divisor=y_tick_divisor)
    outpath = plot_dir / filename
    fig.savefig(outpath, dpi=200)
    plt.close(fig)
    print(f"[OK] Salvei {outpath}")


def plot_ethanol_delta(
    df: pd.DataFrame,
    *,
    y_col: str,
    title: str,
    filename: str,
    y_label: str,
    plot_dir: Path,
    y_tick_divisor: Optional[float] = None,
) -> None:
    d = df[df["Fuel_Label"].eq("E94H6")].copy()
    if d.empty or y_col not in d.columns:
        print(f"[WARN] Sem dados E94H6 para {filename}")
        return

    d["RPM"] = pd.to_numeric(d["RPM"], errors="coerce")
    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    d = d.dropna(subset=["RPM", y_col]).sort_values("RPM")
    if d.empty:
        print(f"[WARN] Sem pontos validos E94H6 para {filename}")
        return

    fig, ax = plt.subplots()
    ax.plot(d["RPM"], d[y_col], "o-", linewidth=1.8, markersize=4.8, color=FUEL_SPECS["E94H6"]["color"], label="E94H6 vs diesel")
    _style_axes(fig, ax, x_values=d["RPM"], title=title, y_label=y_label, y_tick_divisor=y_tick_divisor)
    outpath = plot_dir / filename
    fig.savefig(outpath, dpi=200)
    plt.close(fig)
    print(f"[OK] Salvei {outpath}")


def plot_machine_scenario_dual_metric(
    df: pd.DataFrame,
    *,
    diesel_suffix: str,
    ethanol_suffix: str,
    title: str,
    filename: str,
    y_label: str,
    plot_dir: Path,
    y_tick_divisor: Optional[float] = None,
) -> None:
    d = df[df["Fuel_Label"].eq("E94H6")].copy()
    if d.empty:
        print(f"[WARN] Sem dados E94H6 para {filename}")
        return

    fig, ax = plt.subplots()
    any_curve = False
    for spec in MACHINE_SCENARIO_SPECS:
        diesel_col = _scenario_machine_col(spec["key"], diesel_suffix)
        ethanol_col = _scenario_machine_col(spec["key"], ethanol_suffix)
        if diesel_col in d.columns:
            dd = d[["RPM", diesel_col]].copy()
            dd["RPM"] = pd.to_numeric(dd["RPM"], errors="coerce")
            dd[diesel_col] = pd.to_numeric(dd[diesel_col], errors="coerce")
            dd = dd.dropna(subset=["RPM", diesel_col]).sort_values("RPM")
            if not dd.empty:
                any_curve = True
                ax.plot(dd["RPM"], dd[diesel_col], "o--", linewidth=1.8, markersize=4.5, color=spec["color"], label=f"{spec['label']} diesel")
        if ethanol_col in d.columns:
            de = d[["RPM", ethanol_col]].copy()
            de["RPM"] = pd.to_numeric(de["RPM"], errors="coerce")
            de[ethanol_col] = pd.to_numeric(de[ethanol_col], errors="coerce")
            de = de.dropna(subset=["RPM", ethanol_col]).sort_values("RPM")
            if not de.empty:
                any_curve = True
                ax.plot(de["RPM"], de[ethanol_col], "o-", linewidth=1.8, markersize=4.5, color=spec["color"], label=f"{spec['label']} E94H6")

    if not any_curve:
        plt.close(fig)
        print(f"[WARN] Sem curvas validas para {filename}")
        return

    _style_axes(fig, ax, x_values=d["RPM"], title=title, y_label=y_label, y_tick_divisor=y_tick_divisor)
    outpath = plot_dir / filename
    fig.savefig(outpath, dpi=200)
    plt.close(fig)
    print(f"[OK] Salvei {outpath}")


def plot_machine_scenario_single_metric(
    df: pd.DataFrame,
    *,
    value_suffix: str,
    title: str,
    filename: str,
    y_label: str,
    plot_dir: Path,
    y_tick_divisor: Optional[float] = None,
) -> None:
    d = df[df["Fuel_Label"].eq("E94H6")].copy()
    if d.empty:
        print(f"[WARN] Sem dados E94H6 para {filename}")
        return

    fig, ax = plt.subplots()
    any_curve = False
    for spec in MACHINE_SCENARIO_SPECS:
        value_col = _scenario_machine_col(spec["key"], value_suffix)
        if value_col not in d.columns:
            continue
        dd = d[["RPM", value_col]].copy()
        dd["RPM"] = pd.to_numeric(dd["RPM"], errors="coerce")
        dd[value_col] = pd.to_numeric(dd[value_col], errors="coerce")
        dd = dd.dropna(subset=["RPM", value_col]).sort_values("RPM")
        if dd.empty:
            continue
        any_curve = True
        ax.plot(dd["RPM"], dd[value_col], "o-", linewidth=1.8, markersize=4.5, color=spec["color"], label=spec["label"])

    if not any_curve:
        plt.close(fig)
        print(f"[WARN] Sem curvas validas para {filename}")
        return

    _style_axes(fig, ax, x_values=d["RPM"], title=title, y_label=y_label, y_tick_divisor=y_tick_divisor)
    outpath = plot_dir / filename
    fig.savefig(outpath, dpi=200)
    plt.close(fig)
    print(f"[OK] Salvei {outpath}")


def make_plots(df: pd.DataFrame, plot_dir: Path) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)

    plot_dual_fuel_metric(
        df,
        y_col="Power_kW",
        title="Power vs RPM",
        filename="power_kw_vs_rpm.png",
        y_label="Power (kW)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="Consumo_kg_h",
        title="Mass fuel flow vs RPM",
        filename="consumo_massico_vs_rpm.png",
        y_label="Fuel mass flow (kg/h)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="Consumo_L_h",
        title="Volumetric fuel flow vs RPM",
        filename="consumo_volumetrico_vs_rpm.png",
        y_label="Fuel volumetric flow (L/h)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="Custo_R_h",
        title="Fuel cost vs RPM",
        filename="custo_horario_vs_rpm.png",
        y_label="Fuel cost (R$/h)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="n_th_pct",
        title="n_th vs RPM",
        filename="nth_vs_rpm.png",
        y_label="Thermal efficiency (%)",
        plot_dir=plot_dir,
    )
    plot_ethanol_delta(
        df,
        y_col="Economia_vs_Diesel_R_h",
        title="Hourly economy vs diesel",
        filename="economia_r_h_vs_rpm.png",
        y_label="Delta cost vs diesel (R$/h)",
        plot_dir=plot_dir,
    )
    plot_ethanol_delta(
        df,
        y_col="Economia_vs_Diesel_pct",
        title="Relative economy vs diesel",
        filename="economia_pct_vs_rpm.png",
        y_label="Delta cost vs diesel (%)",
        plot_dir=plot_dir,
    )
    plot_machine_scenario_dual_metric(
        df,
        diesel_suffix="Diesel_Custo_R_h",
        ethanol_suffix="E94H6_Custo_R_h",
        title="Machine scenario: hourly cost diesel vs E94H6",
        filename="scenario_maquinas_custo_r_h_diesel_vs_e94h6_rpm.png",
        y_label="Cost (R$/h)",
        plot_dir=plot_dir,
    )
    plot_machine_scenario_single_metric(
        df,
        value_suffix="Economia_R_h",
        title="Machine scenario: hourly economy vs diesel",
        filename="scenario_maquinas_economia_r_h_vs_diesel_rpm.png",
        y_label="Delta cost vs diesel (R$/h)",
        plot_dir=plot_dir,
    )
    plot_machine_scenario_dual_metric(
        df,
        diesel_suffix="Diesel_L_h",
        ethanol_suffix="E94H6_L_h",
        title="Machine scenario: volumetric flow diesel vs E94H6",
        filename="scenario_maquinas_consumo_l_h_diesel_vs_e94h6_rpm.png",
        y_label="Volumetric flow (L/h)",
        plot_dir=plot_dir,
    )
    plot_machine_scenario_single_metric(
        df,
        value_suffix="E94H6_L_ano",
        title="Machine scenario: annual E94H6 consumption",
        filename="scenario_maquinas_consumo_anual_e94h6_l_rpm.png",
        y_label="Annual E94H6 consumption (x10^3 L/ano)",
        plot_dir=plot_dir,
        y_tick_divisor=1000.0,
    )
    plot_machine_scenario_dual_metric(
        df,
        diesel_suffix="Diesel_Custo_R_ano",
        ethanol_suffix="E94H6_Custo_R_ano",
        title="Machine scenario: annual cost diesel vs E94H6",
        filename="scenario_maquinas_custo_anual_diesel_vs_e94h6_rpm.png",
        y_label="Annual cost (x10^3 R$/ano)",
        plot_dir=plot_dir,
        y_tick_divisor=1000.0,
    )
    plot_machine_scenario_single_metric(
        df,
        value_suffix="Economia_R_ano",
        title="Machine scenario: annual economy vs diesel",
        filename="scenario_maquinas_economia_anual_vs_diesel_rpm.png",
        y_label="Annual delta cost vs diesel (x10^3 R$/ano)",
        plot_dir=plot_dir,
        y_tick_divisor=1000.0,
    )


def main() -> None:
    config_path = DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Nao encontrei config em {config_path}")

    defaults_cfg = load_defaults_config(config_path)
    raw_dir = Path(defaults_cfg.get(norm_key("RAW_INPUT_DIR"), str(DEFAULT_RAW_DIR)))
    out_dir = Path(defaults_cfg.get(norm_key("OUT_DIR"), str(DEFAULT_OUT_DIR)))
    plot_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    include_regex = defaults_cfg.get(norm_key("FILE_INCLUDE_REGEX"), "")
    sheet_name = defaults_cfg.get(norm_key("WORKSHEET_NAME"), "D") or "D"
    fuel_mass_col = defaults_cfg.get(norm_key("FUEL_MASS_COL"), "FB_VAL") or "FB_VAL"
    power_col = defaults_cfg.get(norm_key("POWER_COL"), "P_dyno") or "P_dyno"
    speed_col = defaults_cfg.get(norm_key("SPEED_COL"), "SPEED") or "SPEED"
    rpm_round_digits = int(_to_float(defaults_cfg.get(norm_key("RPM_ROUND_DIGITS"), "0"), default=0.0))
    pair_selection_mode = defaults_cfg.get(norm_key("PAIR_SELECTION_MODE"), "gui") or "gui"

    files = discover_input_files(raw_dir, include_regex)
    if not files:
        raise SystemExit(f"Nenhum .xlsx selecionado em {raw_dir} com regex '{include_regex}'.")

    selected_pairs = resolve_selected_pairs(raw_dir=raw_dir, files=files, pair_selection_mode=pair_selection_mode)
    selected_paths: List[Path] = []
    for pair in selected_pairs:
        selected_paths.extend([pair.diesel_path, pair.ethanol_path])

    unique_selected_files: List[Path] = []
    seen_paths: set[Path] = set()
    for path in selected_paths:
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        unique_selected_files.append(path)

    print(f"[INFO] Config: {config_path}")
    print(f"[INFO] RAW: {raw_dir}")
    print(f"[INFO] OUT: {out_dir}")
    print(f"[INFO] Modo de selecao de pares: {pair_selection_mode}")
    print(f"[INFO] Pares selecionados: {len(selected_pairs)}")
    for pair in selected_pairs:
        print(f"[INFO]   - {pair.pair_label}")
    print(f"[INFO] Arquivos usados: {len(unique_selected_files)}")
    for path in unique_selected_files:
        print(f"[INFO]   - {path.name}")

    all_rows: List[pd.DataFrame] = []
    for pair in selected_pairs:
        for path in [pair.diesel_path, pair.ethanol_path]:
            try:
                df_i = read_fpt_xlsx(
                    path,
                    pair_id=pair.pair_id,
                    pair_label=pair.pair_label,
                    sheet_name=sheet_name,
                    fuel_mass_col=fuel_mass_col,
                    power_col=power_col,
                    speed_col=speed_col,
                    rpm_round_digits=rpm_round_digits,
                )
                if not df_i.empty:
                    all_rows.append(df_i)
            except Exception as exc:
                print(f"[ERROR] Falha lendo {path.name}: {exc}")

    if not all_rows:
        raise SystemExit("Nenhum arquivo FPT valido foi lido.")

    raw_df = pd.concat(all_rows, ignore_index=True)
    agg_df = aggregate_curve_rows(raw_df)
    agg_df = attach_fuel_properties(agg_df, defaults_cfg)
    agg_df = compute_base_metrics(agg_df)
    agg_df = attach_diesel_baseline(agg_df)
    agg_df = attach_machine_scenarios(agg_df, defaults_cfg)

    kpi_path = safe_to_excel(agg_df.sort_values(["Pair_ID", "Fuel_Label", "RPM"]).copy(), out_dir / "lv_kpis_fpt.xlsx")
    print(f"[OK] KPI salvo: {kpi_path}")

    compare_df = build_compare_table(agg_df)
    if not compare_df.empty:
        cmp_path = safe_to_excel(compare_df, out_dir / "compare_rpm_diesel_vs_e94h6_fpt.xlsx")
        print(f"[OK] Comparativo salvo: {cmp_path}")

    pair_values = [pair.pair_id for pair in selected_pairs]
    if len(pair_values) == 1:
        make_plots(agg_df, plot_dir=plot_dir)
    else:
        for pair in selected_pairs:
            pair_df = agg_df[agg_df["Pair_ID"].eq(pair.pair_id)].copy()
            if pair_df.empty:
                continue
            pair_plot_dir = plot_dir / pair.pair_id
            pair_compare_df = build_compare_table(pair_df)
            if not pair_compare_df.empty:
                pair_cmp_path = safe_to_excel(pair_compare_df, out_dir / f"compare_{pair.pair_id}.xlsx")
                print(f"[OK] Comparativo do par salvo: {pair_cmp_path}")
            make_plots(pair_df, plot_dir=pair_plot_dir)


if __name__ == "__main__":
    main()
