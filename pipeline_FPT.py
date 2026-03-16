from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
PLOT_POINT_FILTER_PATH = LOCAL_STATE_DIR / "plot_point_filter_last.json"

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

FPT_COLUMN_ALIASES = {
    "fuel_mass": ["FB_VAL", "qm Fuel", "qm_fuel", "Fuel mass", "Fuel_Mass"],
    "power": ["P_dyno", "P dyno", "P dyno Corr", "P_dyno_Corr", "Power"],
    "speed": ["SPEED", "n engine", "n_engine", "Engine Speed", "Epm_nEng"],
    "air_mass": ["Sensyflow", "qm Air", "qmair", "qm_air", "Air mass", "Air_Mass"],
    "intake_pressure": ["P_i_MF", "p i MF", "p_i_mf"],
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


def _canon_text(value: object) -> str:
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


def _pressure_series_to_mbar(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    finite = values[np.isfinite(values)]
    if finite.empty:
        return values

    median = float(finite.median())
    if median <= 20.0:
        return values * 1000.0
    if median <= 400.0:
        return values * 10.0
    return values


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


def _normalize_plot_point_key(pair_id: object, fuel_label: object, rpm_value: object) -> Optional[Tuple[str, str, float]]:
    pair = str(pair_id or "").strip()
    fuel = str(fuel_label or "").strip()
    rpm = _to_float(rpm_value, default=float("nan"))
    if not pair or not fuel or not np.isfinite(rpm):
        return None
    return pair, fuel, round(float(rpm), 6)


def _plot_point_keys_to_jsonable(points: Set[Tuple[str, str, float]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for pair_id, fuel_label, rpm_value in sorted(points, key=lambda item: (_canon_text(item[0]), _canon_text(item[1]), item[2])):
        out.append({"pair_id": pair_id, "fuel_label": fuel_label, "rpm": round(float(rpm_value), 6)})
    return out


def load_last_plot_point_selection_state() -> Optional[Dict[str, object]]:
    try:
        if not PLOT_POINT_FILTER_PATH.exists():
            return None
        payload = json.loads(PLOT_POINT_FILTER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    selected_points: Set[Tuple[str, str, float]] = set()
    for row in payload.get("selected_points", []) or []:
        if not isinstance(row, dict):
            continue
        key = _normalize_plot_point_key(row.get("pair_id", ""), row.get("fuel_label", ""), row.get("rpm", None))
        if key is not None:
            selected_points.add(key)

    available_points: Set[Tuple[str, str, float]] = set()
    for row in payload.get("available_points", []) or []:
        if not isinstance(row, dict):
            continue
        key = _normalize_plot_point_key(row.get("pair_id", ""), row.get("fuel_label", ""), row.get("rpm", None))
        if key is not None:
            available_points.add(key)

    return {
        "selected_points": selected_points,
        "available_points": available_points,
    }


def save_last_plot_point_selection_state(
    selected_points: Set[Tuple[str, str, float]],
    available_points: Set[Tuple[str, str, float]],
) -> None:
    try:
        LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "selected_points": _plot_point_keys_to_jsonable(selected_points),
            "available_points": _plot_point_keys_to_jsonable(available_points),
        }
        PLOT_POINT_FILTER_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception as exc:
        print(f"[WARN] Nao consegui salvar a ultima selecao de pontos do plot FPT: {exc}")


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


def resolve_col_with_aliases(df: pd.DataFrame, requested: str, aliases: List[str]) -> str:
    candidates = [str(requested or "").strip()] + [str(alias or "").strip() for alias in aliases]
    tried: List[str] = []
    for candidate in candidates:
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        try:
            return resolve_col(df, candidate)
        except KeyError:
            continue
    raise KeyError(f"Nenhuma coluna encontrada para '{requested}' com aliases {aliases}.")


def load_fpt_measure_dataframe(
    path: Path,
    *,
    sheet_name: str,
    fuel_mass_col: str,
    power_col: str,
    speed_col: str,
) -> Tuple[pd.DataFrame, str, str, str, Optional[str], Optional[str]]:
    workbook = pd.ExcelFile(path)
    sheet_candidates: List[str] = []
    requested_sheet = str(sheet_name or "").strip()
    if requested_sheet and requested_sheet in workbook.sheet_names:
        sheet_candidates.append(requested_sheet)
    for candidate in workbook.sheet_names:
        if candidate not in sheet_candidates:
            sheet_candidates.append(candidate)

    errors: List[str] = []
    for candidate_sheet in sheet_candidates:
        for header_row in [0, 1, 2]:
            try:
                df = pd.read_excel(path, sheet_name=candidate_sheet, header=header_row, dtype=object)
            except Exception as exc:
                errors.append(f"{candidate_sheet}/header={header_row}: {exc}")
                continue
            try:
                fb_col = resolve_col_with_aliases(df, fuel_mass_col, FPT_COLUMN_ALIASES["fuel_mass"])
                p_col = resolve_col_with_aliases(df, power_col, FPT_COLUMN_ALIASES["power"])
                rpm_col = resolve_col_with_aliases(df, speed_col, FPT_COLUMN_ALIASES["speed"])
                air_col = None
                try:
                    air_col = resolve_col_with_aliases(df, "air_mass", FPT_COLUMN_ALIASES["air_mass"])
                except KeyError:
                    air_col = None
                intake_pressure_col = None
                try:
                    intake_pressure_col = resolve_col_with_aliases(df, "intake_pressure", FPT_COLUMN_ALIASES["intake_pressure"])
                except KeyError:
                    intake_pressure_col = None
                if candidate_sheet != requested_sheet or header_row != 0:
                    print(
                        f"[INFO] {path.name}: usei sheet='{candidate_sheet}' header={header_row} "
                        f"para compatibilizar o layout do arquivo."
                    )
                return df, fb_col, p_col, rpm_col, air_col, intake_pressure_col
            except KeyError as exc:
                errors.append(f"{candidate_sheet}/header={header_row}: {exc}")
                continue

    joined = "; ".join(errors[:6])
    raise ValueError(
        f"Nao consegui interpretar {path.name}. Sheets disponiveis: {workbook.sheet_names}. "
        f"Tentativas: {joined}"
    )


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


def _build_wrapped_radio_panel(
    parent,
    *,
    title: str,
    paths: List[Path],
    rel_name,
    width_wrap: int = 360,
):
    container = ttk.Frame(parent)
    container.columnconfigure(0, weight=1)
    container.rowconfigure(1, weight=1)
    ttk.Label(container, text=title).grid(row=0, column=0, sticky="w")

    viewport = ttk.Frame(container)
    viewport.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    viewport.columnconfigure(0, weight=1)
    viewport.rowconfigure(0, weight=1)

    canvas = tk.Canvas(viewport, highlightthickness=0)
    scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    viewport.columnconfigure(0, weight=1)
    viewport.rowconfigure(0, weight=1)

    inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_inner_configure(_event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event) -> None:
        canvas.itemconfigure(inner_window, width=event.width)

    inner.bind("<Configure>", on_inner_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    value_var = tk.StringVar(value="")
    for row_idx, path in enumerate(paths):
        tk.Radiobutton(
            inner,
            text=rel_name(path),
            variable=value_var,
            value=str(path.resolve()),
            anchor="w",
            justify="left",
            wraplength=width_wrap,
            padx=6,
            pady=4,
        ).grid(row=row_idx, column=0, sticky="ew")

    return container, value_var


def _build_wrapped_selected_pairs_panel(
    parent,
    *,
    title: str,
    rel_name,
    width_wrap: int = 520,
):
    container = ttk.Frame(parent)
    container.columnconfigure(0, weight=1)
    container.rowconfigure(1, weight=1)
    ttk.Label(container, text=title).grid(row=0, column=0, sticky="w")

    viewport = ttk.Frame(container)
    viewport.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    viewport.columnconfigure(0, weight=1)
    viewport.rowconfigure(0, weight=1)

    canvas = tk.Canvas(viewport, highlightthickness=0)
    scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_inner_configure(_event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event) -> None:
        canvas.itemconfigure(inner_window, width=event.width)

    inner.bind("<Configure>", on_inner_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    value_var = tk.StringVar(value="")
    pair_lookup: Dict[str, Tuple[Path, Path]] = {}

    def refresh(selected_pairs: List[Tuple[Path, Path]]) -> None:
        pair_lookup.clear()
        for child in inner.winfo_children():
            child.destroy()
        for idx, (diesel_path, ethanol_path) in enumerate(selected_pairs):
            key = str(idx)
            pair_lookup[key] = (diesel_path, ethanol_path)
            label = (
                f"DIESEL:\n{rel_name(diesel_path)}\n\n"
                f"ETANOL:\n{rel_name(ethanol_path)}"
            )
            tk.Radiobutton(
                inner,
                text=label,
                variable=value_var,
                value=key,
                anchor="w",
                justify="left",
                wraplength=width_wrap,
                padx=6,
                pady=6,
            ).grid(row=idx, column=0, sticky="ew")
        if value_var.get() not in pair_lookup:
            value_var.set("")

    return container, value_var, pair_lookup, refresh


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
        text=(
            f"RAW: {raw_dir}\n"
            "A GUI sempre faz scan completo da pasta e mostra todos os .xlsx disponiveis. "
            "O FILE_INCLUDE_REGEX nao limita esta tela."
        ),
        wraplength=1120,
        justify="left",
    )
    info.pack(fill="x", padx=12, pady=(0, 10))

    body = ttk.Frame(root)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=1)
    body.columnconfigure(2, weight=2)
    body.rowconfigure(0, weight=1)

    diesel_panel, diesel_value = _build_wrapped_radio_panel(body, title="Diesel", paths=diesel_files, rel_name=rel_name)
    ethanol_panel, ethanol_value = _build_wrapped_radio_panel(body, title="Etanol", paths=ethanol_files, rel_name=rel_name)
    selected_panel, selected_value, selected_lookup, refresh_selected_panel = _build_wrapped_selected_pairs_panel(
        body,
        title="Pares selecionados",
        rel_name=rel_name,
    )
    diesel_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    ethanol_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 6))
    selected_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    abs_lookup = {str(path.resolve()): path for path in files}

    def refresh_pairs() -> None:
        refresh_selected_panel(selected_pairs)

    def add_pair() -> None:
        diesel_path = abs_lookup.get(diesel_value.get())
        ethanol_path = abs_lookup.get(ethanol_value.get())
        if diesel_path is None or ethanol_path is None:
            messagebox.showwarning("Par incompleto", "Selecione um arquivo diesel e um arquivo etanol.")
            return
        candidate = (diesel_path, ethanol_path)
        if candidate in selected_pairs:
            messagebox.showinfo("Par ja existe", "Esse par ja esta na lista.")
            return
        selected_pairs.append(candidate)
        refresh_pairs()

    def remove_pair() -> None:
        selected = selected_lookup.get(selected_value.get())
        if selected is None:
            return
        diesel_path, ethanol_path = selected
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

    df, fb_col, p_col, rpm_col, air_col, intake_pressure_col = load_fpt_measure_dataframe(
        path,
        sheet_name=sheet_name,
        fuel_mass_col=fuel_mass_col,
        power_col=power_col,
        speed_col=speed_col,
    )

    pressure_series = _pressure_series_to_mbar(df[intake_pressure_col]) if intake_pressure_col else pd.Series(pd.NA, index=df.index)
    out = pd.DataFrame(
        {
            "Pair_ID": pair_id,
            "Pair_Label": pair_label,
            "Source_File": path.name,
            "Fuel_Label": fuel_label,
            "Consumo_kg_h": pd.to_numeric(df[fb_col], errors="coerce"),
            "Power_kW": pd.to_numeric(df[p_col], errors="coerce"),
            "Speed_RPM_raw": pd.to_numeric(df[rpm_col], errors="coerce"),
            "Air_kg_h": pd.to_numeric(df[air_col], errors="coerce") if air_col else pd.NA,
            "P_i_MF_mbar": pressure_series,
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
            Air_kg_h=("Air_kg_h", "mean"),
            P_i_MF_mbar=("P_i_MF_mbar", "mean"),
            Power_kW_sd=("Power_kW", "std"),
            Consumo_kg_h_sd=("Consumo_kg_h", "std"),
            Air_kg_h_sd=("Air_kg_h", "std"),
            P_i_MF_mbar_sd=("P_i_MF_mbar", "std"),
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
    air_kg_h = pd.to_numeric(out.get("Air_kg_h", pd.NA), errors="coerce")
    power_kw = pd.to_numeric(out["Power_kW"], errors="coerce")

    out["Consumo_L_h"] = (consumo_kg_h * 1000.0 / fuel_density).where(fuel_density.gt(0), pd.NA)
    out["Custo_R_h"] = (pd.to_numeric(out["Consumo_L_h"], errors="coerce") * fuel_cost).where(fuel_cost.gt(0), pd.NA)
    custo_r_h = pd.to_numeric(out["Custo_R_h"], errors="coerce")
    out["Custo_R_kWh"] = (custo_r_h / power_kw).where(power_kw.gt(0), pd.NA)
    out["Air_kg_h_kW"] = (air_kg_h / power_kw).where(power_kw.gt(0), pd.NA)
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

    baseline_cols = [
        "Pair_ID",
        "RPM",
        "Consumo_kg_h",
        "Consumo_L_h",
        "Custo_R_h",
        "Custo_R_kWh",
        "Air_kg_h",
        "Air_kg_h_kW",
        "n_th_pct",
        "Power_kW",
    ]
    diesel = diesel[baseline_cols].rename(
        columns={
            "Consumo_kg_h": "Diesel_Baseline_Consumo_kg_h",
            "Consumo_L_h": "Diesel_Baseline_Consumo_L_h",
            "Custo_R_h": "Diesel_Baseline_Custo_R_h",
            "Custo_R_kWh": "Diesel_Baseline_Custo_R_kWh",
            "Air_kg_h": "Diesel_Baseline_Air_kg_h",
            "Air_kg_h_kW": "Diesel_Baseline_Air_kg_h_kW",
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
    custo_kwh = pd.to_numeric(out["Custo_R_kWh"], errors="coerce")
    custo_kwh_bl = pd.to_numeric(out["Diesel_Baseline_Custo_R_kWh"], errors="coerce")
    air_m = pd.to_numeric(out.get("Air_kg_h", pd.NA), errors="coerce")
    air_m_bl = pd.to_numeric(out.get("Diesel_Baseline_Air_kg_h", pd.NA), errors="coerce")
    air_sp = pd.to_numeric(out.get("Air_kg_h_kW", pd.NA), errors="coerce")
    air_sp_bl = pd.to_numeric(out.get("Diesel_Baseline_Air_kg_h_kW", pd.NA), errors="coerce")
    nth = pd.to_numeric(out["n_th_pct"], errors="coerce")
    nth_bl = pd.to_numeric(out["Diesel_Baseline_n_th_pct"], errors="coerce")

    out["Economia_vs_Diesel_R_h"] = (custo - custo_bl).where(custo_bl.gt(0), pd.NA)
    out["Economia_vs_Diesel_pct"] = (100.0 * (custo / custo_bl - 1.0)).where(custo_bl.gt(0), pd.NA)
    out["Economia_vs_Diesel_R_kWh"] = (custo_kwh - custo_kwh_bl).where(custo_kwh_bl.gt(0), pd.NA)
    out["Economia_vs_Diesel_R_kWh_pct"] = (100.0 * (custo_kwh / custo_kwh_bl - 1.0)).where(custo_kwh_bl.gt(0), pd.NA)
    out["Delta_Consumo_kg_h_vs_Diesel"] = cons_m - cons_m_bl
    out["Delta_Consumo_L_h_vs_Diesel"] = cons_v - cons_v_bl
    out["Delta_Air_kg_h_vs_Diesel"] = air_m - air_m_bl
    out["Delta_Air_kg_h_kW_vs_Diesel"] = air_sp - air_sp_bl
    out["Delta_n_th_pct_vs_Diesel"] = nth - nth_bl

    diesel_mask = out["Fuel_Label"].eq("D85B15")
    zero_cols = [
        "Economia_vs_Diesel_R_h",
        "Economia_vs_Diesel_pct",
        "Economia_vs_Diesel_R_kWh",
        "Economia_vs_Diesel_R_kWh_pct",
        "Delta_Consumo_kg_h_vs_Diesel",
        "Delta_Consumo_L_h_vs_Diesel",
        "Delta_Air_kg_h_vs_Diesel",
        "Delta_Air_kg_h_kW_vs_Diesel",
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
            "Custo_R_kWh": "Diesel_Custo_R_kWh",
            "Air_kg_h": "Diesel_Air_kg_h",
            "Air_kg_h_kW": "Diesel_Air_kg_h_kW",
            "P_i_MF_mbar": "Diesel_P_i_MF_mbar",
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
            "Custo_R_kWh": "E94H6_Custo_R_kWh",
            "Air_kg_h": "E94H6_Air_kg_h",
            "Air_kg_h_kW": "E94H6_Air_kg_h_kW",
            "P_i_MF_mbar": "E94H6_P_i_MF_mbar",
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
        "Diesel_Custo_R_kWh",
        "Diesel_Air_kg_h",
        "Diesel_Air_kg_h_kW",
        "Diesel_P_i_MF_mbar",
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
        "E94H6_Custo_R_kWh",
        "E94H6_Air_kg_h",
        "E94H6_Air_kg_h_kW",
        "E94H6_P_i_MF_mbar",
        "E94H6_n_th_pct",
        "Economia_vs_Diesel_R_h",
        "Economia_vs_Diesel_pct",
        "Economia_vs_Diesel_R_kWh",
        "Economia_vs_Diesel_R_kWh_pct",
    ]
    merged = diesel[cols_left].merge(ethanol[cols_right], on=["Pair_ID", "RPM"], how="inner")
    return merged.sort_values(["Pair_ID", "RPM"]).copy()


def _build_plot_point_rows(df: pd.DataFrame) -> List[Dict[str, object]]:
    if df is None or df.empty:
        return []

    cols = [
        "Pair_ID",
        "Pair_Label",
        "Fuel_Label",
        "RPM",
        "Power_kW",
        "Consumo_kg_h",
        "Custo_R_h",
        "Custo_R_kWh",
        "N_points",
        "Source_Files",
    ]
    tmp = df.copy()
    for col in cols:
        if col not in tmp.columns:
            tmp[col] = pd.NA

    point_df = tmp[cols].copy()
    point_df["RPM"] = pd.to_numeric(point_df["RPM"], errors="coerce")
    point_df["Power_kW"] = pd.to_numeric(point_df["Power_kW"], errors="coerce")
    point_df["Consumo_kg_h"] = pd.to_numeric(point_df["Consumo_kg_h"], errors="coerce")
    point_df["Custo_R_h"] = pd.to_numeric(point_df["Custo_R_h"], errors="coerce")
    point_df["Custo_R_kWh"] = pd.to_numeric(point_df["Custo_R_kWh"], errors="coerce")
    point_df["N_points"] = pd.to_numeric(point_df["N_points"], errors="coerce")
    point_df = point_df.dropna(subset=["Pair_ID", "Fuel_Label", "RPM"])
    point_df = point_df.sort_values(["Pair_Label", "Fuel_Label", "RPM"], kind="stable")

    rows: List[Dict[str, object]] = []
    for _, row in point_df.iterrows():
        key = _normalize_plot_point_key(row.get("Pair_ID", ""), row.get("Fuel_Label", ""), row.get("RPM", pd.NA))
        if key is None:
            continue
        rows.append(
            {
                "key": key,
                "pair_id": key[0],
                "pair_label": str(row.get("Pair_Label", "")).strip() or key[0],
                "fuel_label": key[1],
                "rpm": key[2],
                "power_kw": _to_float(row.get("Power_kW", pd.NA), default=float("nan")),
                "consumo_kg_h": _to_float(row.get("Consumo_kg_h", pd.NA), default=float("nan")),
                "custo_r_h": _to_float(row.get("Custo_R_h", pd.NA), default=float("nan")),
                "custo_r_kwh": _to_float(row.get("Custo_R_kWh", pd.NA), default=float("nan")),
                "n_points": int(_to_float(row.get("N_points", 1), default=1.0)) if np.isfinite(_to_float(row.get("N_points", 1), default=1.0)) else 1,
                "source_files": str(row.get("Source_Files", "")).strip(),
            }
        )
    return rows


def _preferred_fpt_fuel_order(labels: List[str]) -> List[str]:
    preferred = ["D85B15", "E94H6"]
    uniq = [str(v).strip() for v in labels if str(v).strip()]
    ordered = [label for label in preferred if label in uniq]
    extras = sorted([label for label in uniq if label not in ordered], key=_canon_text)
    return ordered + extras


def _build_fpt_plot_point_catalog(
    df: pd.DataFrame,
) -> Tuple[List[Tuple[str, str]], List[float], Dict[Tuple[str, str, float], int], Dict[Tuple[str, str], str], List[str]]:
    rows = _build_plot_point_rows(df)
    if not rows:
        return [], [], {}, {}, []

    pair_labels: Dict[str, str] = {}
    for row in rows:
        pair_id = str(row["pair_id"]).strip()
        pair_label = str(row["pair_label"]).strip() or pair_id
        if pair_id not in pair_labels:
            pair_labels[pair_id] = pair_label

    ordered_pair_ids = sorted(pair_labels.keys(), key=lambda key: (_canon_text(pair_labels.get(key, "")), _canon_text(key)))
    pair_aliases = {pair_id: f"P{idx + 1}" for idx, pair_id in enumerate(ordered_pair_ids)}

    series_keys_set = {(str(row["pair_id"]).strip(), str(row["fuel_label"]).strip()) for row in rows}
    fuel_order = {fuel: idx for idx, fuel in enumerate(_preferred_fpt_fuel_order([fuel for _, fuel in series_keys_set]))}
    series_keys = sorted(
        series_keys_set,
        key=lambda item: (
            ordered_pair_ids.index(item[0]) if item[0] in ordered_pair_ids else 999,
            fuel_order.get(item[1], 999),
            _canon_text(item[1]),
        ),
    )

    series_labels = {
        series_key: f"{pair_aliases.get(series_key[0], series_key[0])}\n{series_key[1]}"
        for series_key in series_keys
    }
    legend_lines = [f"{pair_aliases[pair_id]} = {pair_labels[pair_id]}" for pair_id in ordered_pair_ids]

    rpm_values = sorted({float(row["rpm"]) for row in rows})
    counts: Dict[Tuple[str, str, float], int] = {}
    for row in rows:
        key = row["key"]
        counts[key] = int(row.get("n_points", 1) or 1)

    return series_keys, rpm_values, counts, series_labels, legend_lines


def _resolve_plot_point_initial_selection(
    available_points: Set[Tuple[str, str, float]],
) -> Tuple[Dict[Tuple[str, str, float], bool], str]:
    defaults = {key: True for key in available_points}
    state = load_last_plot_point_selection_state()
    if state is None:
        return defaults, "Sem ultima selecao salva. Todos os pontos vieram marcados."

    saved_available = set(state.get("available_points", set()) or set())
    saved_selected = set(state.get("selected_points", set()) or set())
    matched = 0
    for key in sorted(available_points):
        if key in saved_available:
            defaults[key] = key in saved_selected
            matched += 1
    if matched == 0:
        return defaults, "Ultima selecao salva nao combinou com este conjunto. Todos os pontos vieram marcados."

    new_points = available_points - saved_available
    selected_count = sum(1 for value in defaults.values() if value)
    message = f"Ultima selecao carregada automaticamente: {selected_count} / {len(available_points)} ponto(s) marcados."
    if new_points:
        message += f" {len(new_points)} ponto(s) novo(s) vieram selecionados por padrao."
    return defaults, message


def prompt_plot_point_filter(df: pd.DataFrame) -> Optional[Set[Tuple[str, str, float]]]:
    series_keys, rpm_values, counts, series_labels, legend_lines = _build_fpt_plot_point_catalog(df)
    if not series_keys or not rpm_values or not counts:
        print("[WARN] Nao encontrei pontos para abrir o filtro de plot FPT. Vou usar todos.")
        return None
    if tk is None or ttk is None or messagebox is None:
        print("[WARN] Tkinter nao esta disponivel. Vou usar todos os pontos do FPT.")
        return None

    available_points = {key for key, count in counts.items() if count > 0}
    initial_selection, initial_message = _resolve_plot_point_initial_selection(available_points)
    result: Dict[str, object] = {"selected": None}

    root = tk.Tk()
    root.title("Pipeline FPT - filtro de pontos para plots")
    root.geometry("1240x760")
    root.minsize(1080, 640)

    ttk.Label(
        root,
        text="Selecione os conjuntos de pontos que entram nos comparativos e plots do FPT. O lv_kpis_fpt.xlsx bruto continua completo.",
        wraplength=1180,
        justify="left",
    ).pack(fill="x", padx=12, pady=(12, 4))
    info_var = tk.StringVar(value=initial_message)
    ttk.Label(root, textvariable=info_var, wraplength=1180, justify="left").pack(fill="x", padx=12, pady=(0, 8))
    if legend_lines:
        ttk.Label(
            root,
            text=" | ".join(legend_lines),
            wraplength=1180,
            justify="left",
        ).pack(fill="x", padx=12, pady=(0, 8))

    toolbar = ttk.Frame(root)
    toolbar.pack(fill="x", padx=12, pady=(0, 8))
    status_var = tk.StringVar(value="")

    body = ttk.Frame(root)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    body.columnconfigure(0, weight=1)
    body.rowconfigure(0, weight=1)

    canvas = tk.Canvas(body, highlightthickness=0)
    hscroll = ttk.Scrollbar(body, orient="horizontal", command=canvas.xview)
    scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=hscroll.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    hscroll.grid(row=1, column=0, sticky="ew")

    inner = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def sync_canvas(_event: object = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(canvas_window, width=max(canvas.winfo_width(), inner.winfo_reqwidth()))

    inner.bind("<Configure>", sync_canvas)
    canvas.bind("<Configure>", sync_canvas)

    header_bg = "#f4f6f8"
    cell_border = "#d7dce1"

    def make_cell(row: int, column: int, *, bg: str = "white") -> tk.Frame:
        cell = tk.Frame(
            inner,
            bg=bg,
            highlightbackground=cell_border,
            highlightthickness=1,
            bd=0,
            padx=3,
            pady=0,
        )
        cell.grid(row=row, column=column, sticky="nsew")
        return cell

    header_cell = make_cell(0, 0, bg=header_bg)
    ttk.Label(header_cell, text="RPM", anchor="center", justify="center").pack(fill="both", expand=True)

    for col_idx, series_key in enumerate(series_keys, start=1):
        header_cell = make_cell(0, col_idx, bg=header_bg)
        ttk.Label(
            header_cell,
            text=series_labels.get(series_key, "\n".join(series_key)),
            anchor="center",
            justify="center",
        ).pack(fill="both", expand=True)
        inner.columnconfigure(col_idx, weight=1)

    cell_vars: Dict[Tuple[str, str, float], tk.BooleanVar] = {}

    for row_idx, rpm_value in enumerate(rpm_values, start=1):
        rpm_cell = make_cell(row_idx, 0, bg=header_bg)
        ttk.Label(rpm_cell, text=f"{rpm_value:.0f}", anchor="center", justify="center").pack(fill="both", expand=True)
        for col_idx, series_key in enumerate(series_keys, start=1):
            key = (series_key[0], series_key[1], float(rpm_value))
            count = counts.get(key, 0)
            if count <= 0:
                empty_cell = make_cell(row_idx, col_idx)
                ttk.Label(empty_cell, text="-", anchor="center").pack(fill="both", expand=True)
                continue

            var = tk.BooleanVar(value=bool(initial_selection.get(key, True)))
            cell_vars[key] = var
            point_cell = make_cell(row_idx, col_idx)
            inner_frame = ttk.Frame(point_cell)
            inner_frame.pack(fill="both", expand=True)
            ttk.Checkbutton(inner_frame, variable=var).pack(anchor="center", pady=0)
            ttk.Label(inner_frame, text="" if count == 1 else f"{count}x", anchor="center", justify="center").pack(anchor="center")

    def selected_points_now() -> Set[Tuple[str, str, float]]:
        return {key for key, var in cell_vars.items() if bool(var.get())}

    def refresh_status() -> None:
        selected = sum(1 for var in cell_vars.values() if bool(var.get()))
        status_var.set(f"Pontos selecionados: {selected} / {len(cell_vars)}")

    for var in cell_vars.values():
        var.trace_add("write", lambda *_args: refresh_status())

    def set_all(value: bool) -> None:
        for var in cell_vars.values():
            var.set(value)

    def load_last_selection() -> None:
        defaults, message = _resolve_plot_point_initial_selection(available_points)
        for key, var in cell_vars.items():
            var.set(bool(defaults.get(key, True)))
        info_var.set(message)

    def save_current_selection() -> None:
        selected = selected_points_now()
        save_last_plot_point_selection_state(selected, available_points)
        info_var.set(f"Selecao atual salva como ultima: {len(selected)} / {len(available_points)} ponto(s) marcados.")

    def confirm() -> None:
        selected = selected_points_now()
        if not selected:
            messagebox.showerror("Pipeline FPT", "Selecione pelo menos um ponto para gerar os plots.", parent=root)
            return
        save_last_plot_point_selection_state(selected, available_points)
        result["selected"] = selected
        root.destroy()

    def cancel() -> None:
        root.destroy()

    ttk.Button(toolbar, text="Selecionar tudo", command=lambda: set_all(True)).pack(side="left")
    ttk.Button(toolbar, text="Limpar tudo", command=lambda: set_all(False)).pack(side="left", padx=(8, 0))
    ttk.Button(toolbar, text="Carregar ultima", command=load_last_selection).pack(side="left", padx=(8, 0))
    ttk.Button(toolbar, text="Salvar atual", command=save_current_selection).pack(side="left", padx=(8, 0))
    ttk.Label(toolbar, text="Colunas = par/combustivel | Linhas = RPM").pack(side="left", padx=(12, 0))
    ttk.Label(toolbar, textvariable=status_var).pack(side="right")
    refresh_status()

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", padx=12, pady=(0, 12))
    ttk.Button(buttons, text="Cancelar", command=cancel).pack(side="right")
    ttk.Button(buttons, text="Gerar comparativos e plots", command=confirm).pack(side="right", padx=(0, 8))

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.state("zoomed")
    root.mainloop()

    selected = result.get("selected")
    if selected is None:
        print("[WARN] Filtro de pontos cancelado. Vou usar todos os pontos do FPT.")
        return None
    return set(selected)


def apply_plot_point_filter(
    df: pd.DataFrame,
    selected_points: Optional[Set[Tuple[str, str, float]]],
) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    if df.empty or selected_points is None:
        return df.copy()

    pair_ids = df.get("Pair_ID", pd.Series(pd.NA, index=df.index)).astype(str).str.strip()
    fuel_labels = df.get("Fuel_Label", pd.Series(pd.NA, index=df.index)).astype(str).str.strip()
    rpms = pd.to_numeric(df.get("RPM", pd.Series(pd.NA, index=df.index)), errors="coerce").round(6)
    mask = pd.Series(False, index=df.index, dtype="bool")
    for pair_id, fuel_label, rpm_value in selected_points:
        mask = mask | (pair_ids.eq(pair_id) & fuel_labels.eq(fuel_label) & rpms.eq(round(float(rpm_value), 6)))
    kept = int(mask.sum())
    print(f"[INFO] Filtro de pontos FPT: {kept} linha(s) mantida(s) para comparativos e plots.")
    return df.loc[mask].copy()


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
        y_col="Custo_R_kWh",
        title="Specific fuel cost vs RPM",
        filename="custo_especifico_r_kwh_vs_rpm.png",
        y_label="Specific fuel cost (R$/kWh)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="Air_kg_h",
        title="Air mass flow vs RPM",
        filename="vazao_ar_kg_h_vs_rpm.png",
        y_label="Air mass flow (kg/h)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="Air_kg_h_kW",
        title="Air mass flow per power vs RPM",
        filename="vazao_ar_kg_h_kw_vs_rpm.png",
        y_label="Air mass flow per power (kg/h/kW)",
        plot_dir=plot_dir,
    )
    plot_dual_fuel_metric(
        df,
        y_col="P_i_MF_mbar",
        title="Intake manifold pressure vs RPM",
        filename="pressao_coletor_mbar_vs_rpm.png",
        y_label="Intake manifold pressure (mBar)",
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
    plot_ethanol_delta(
        df,
        y_col="Economia_vs_Diesel_R_kWh",
        title="Specific cost delta vs diesel",
        filename="economia_r_kwh_vs_diesel_rpm.png",
        y_label="Delta specific cost vs diesel (R$/kWh)",
        plot_dir=plot_dir,
    )
    plot_ethanol_delta(
        df,
        y_col="Economia_vs_Diesel_R_kWh_pct",
        title="Relative specific cost vs diesel",
        filename="economia_pct_r_kwh_vs_diesel_rpm.png",
        y_label="Delta specific cost vs diesel (%)",
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
    plot_point_filter_mode = defaults_cfg.get(norm_key("PLOT_POINT_FILTER_MODE"), "gui") or "gui"

    all_files = discover_input_files(raw_dir, "")
    filtered_files = discover_input_files(raw_dir, include_regex)
    if not all_files:
        raise SystemExit(f"Nenhum .xlsx encontrado em {raw_dir}.")

    selector_files = all_files if norm_key(pair_selection_mode) in {"gui", "pair_gui", "pairs_gui"} else filtered_files
    if not selector_files:
        raise SystemExit(f"Nenhum .xlsx disponivel para o modo '{pair_selection_mode}' com regex '{include_regex}'.")

    selected_pairs = resolve_selected_pairs(raw_dir=raw_dir, files=selector_files, pair_selection_mode=pair_selection_mode)
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
    print(f"[INFO] Arquivos detectados na pasta: {len(all_files)}")
    if include_regex:
        print(f"[INFO] Arquivos filtrados pela regex do config: {len(filtered_files)}")
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

    plot_df = agg_df.copy()
    if norm_key(plot_point_filter_mode) not in {"off", "skip", "none", "0", "false"}:
        selected_plot_points = prompt_plot_point_filter(agg_df)
        plot_df = apply_plot_point_filter(agg_df, selected_plot_points)
    else:
        print("[INFO] Filtro de pontos de plot FPT desativado por configuracao.")

    compare_df = build_compare_table(plot_df)
    if not compare_df.empty:
        cmp_path = safe_to_excel(compare_df, out_dir / "compare_rpm_diesel_vs_e94h6_fpt.xlsx")
        print(f"[OK] Comparativo salvo: {cmp_path}")

    pair_values = [pair.pair_id for pair in selected_pairs]
    if len(pair_values) == 1:
        make_plots(plot_df, plot_dir=plot_dir)
    else:
        for pair in selected_pairs:
            pair_df = plot_df[plot_df["Pair_ID"].eq(pair.pair_id)].copy()
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
