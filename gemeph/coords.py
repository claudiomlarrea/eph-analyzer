"""Coordenadas geográficas de aglomerados EPH para mapas."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_GEO_PATH = Path(__file__).resolve().parents[1] / "diccionario" / "aglomerados_geo.json"


def load_coords() -> dict[int, dict]:
    data = json.loads(_GEO_PATH.read_text(encoding="utf-8"))
    return {int(k): v for k, v in data.get("coordenadas", {}).items()}


def enrich_catalog_geo(cat_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega lat/lon al catálogo de aglomerados."""
    coords = load_coords()
    out = cat_df[cat_df["tipo"] == "aglomerado"].copy()
    out["lat"] = out["aglomerado_codigo"].map(lambda c: coords.get(int(c), {}).get("lat") if pd.notna(c) else None)
    out["lon"] = out["aglomerado_codigo"].map(lambda c: coords.get(int(c), {}).get("lon") if pd.notna(c) else None)
    return out.dropna(subset=["lat", "lon"])
