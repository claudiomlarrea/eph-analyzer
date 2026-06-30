"""Panel maestro GEMEPH: descarga, merge y persistencia."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from indec_auto.src.download import download_panel
from indec_auto.src.prepare import build_analysis_frame, validate_microdata

from .config import PANEL_DIR


def run_id_for(years: list[int], trimestre: int, modulo: str) -> str:
    y0, y1 = min(years), max(years)
    period = str(y0) if y0 == y1 else f"{y0}_{y1}"
    return f"{period}_T{trimestre}_{modulo}"


def periodo_texto(years: list[int], trimestre: int) -> str:
    if len(years) == 1:
        return f"{years[0]} (T{trimestre})"
    return f"{min(years)}–{max(years)} (T{trimestre})"


def build_panel(
    years: list[int],
    trimestre: int,
    *,
    modulo: str = "tic",
    force_download: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Descarga microdatos y arma panel maestro sin filtro territorial."""
    hogar, individual = download_panel(
        years=list(years),
        trimester=trimestre,
        force=force_download,
    )
    df = build_analysis_frame(
        hogar,
        individual,
        aglomerado=None,
        include_tic=(modulo == "tic"),
    )
    val = validate_microdata(df)
    return df, val


def panel_path(run_id: str) -> Path:
    return PANEL_DIR / f"{run_id}.parquet"


def save_panel(df: pd.DataFrame, run_id: str) -> Path:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    path = panel_path(run_id)
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
    return path


def load_panel(run_id: str) -> pd.DataFrame | None:
    path = panel_path(run_id)
    if not path.exists():
        return None
    return pd.read_parquet(path, engine="pyarrow")


def load_or_build_panel(
    years: list[int],
    trimestre: int,
    *,
    modulo: str = "tic",
    force_download: bool = False,
) -> tuple[pd.DataFrame, dict, str]:
    """Lee parquet cacheado o construye panel desde INDEC."""
    run_id = run_id_for(years, trimestre, modulo)
    cached = load_panel(run_id)
    if cached is not None and not force_download:
        return cached, {"filas": len(cached), "cache": True}, run_id

    df, val = build_panel(years, trimestre, modulo=modulo, force_download=force_download)
    save_panel(df, run_id)
    val["cache"] = False
    return df, val, run_id
