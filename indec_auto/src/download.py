"""Descarga microdatos EPH (hogar e individuo) desde mirror público de bases INDEC."""

from __future__ import annotations

import io
import urllib.request
import ssl
from pathlib import Path

import pandas as pd
import rdata

from .config import DATA_DIR, MIRROR_BASE, TRIMESTER_TIC, YEARS_TIC


def _fetch_rds(url: str) -> pd.DataFrame:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
        raw = resp.read()
    parsed = rdata.parser.parse_file(io.BytesIO(raw))
    return rdata.conversion.convert(parsed)


def _url(kind: str, year: int, trimester: int) -> str:
    return f"{MIRROR_BASE}/{kind}/base_{kind}_{year}T{trimester}.RDS"


def download_trimester(
    year: int,
    trimester: int = TRIMESTER_TIC,
    *,
    force: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "hogar": DATA_DIR / f"hogar_{year}T{trimester}.parquet",
        "individual": DATA_DIR / f"individual_{year}T{trimester}.parquet",
    }
    if not force and all(p.exists() for p in paths.values()):
        return pd.read_parquet(paths["hogar"]), pd.read_parquet(paths["individual"])

    hogar = _fetch_rds(_url("hogar", year, trimester))
    individual = _fetch_rds(_url("individual", year, trimester))
    hogar.to_parquet(paths["hogar"], index=False)
    individual.to_parquet(paths["individual"], index=False)
    return hogar, individual


def download_panel_tic(
    years: list[int] | None = None,
    trimester: int = TRIMESTER_TIC,
    *,
    force: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = years or YEARS_TIC
    hogares, individuos = [], []
    for year in years:
        h, i = download_trimester(year, trimester, force=force)
        h = h.copy()
        i = i.copy()
        h["anio"] = year
        h["trimestre"] = trimester
        i["anio"] = year
        i["trimestre"] = trimester
        hogares.append(h)
        individuos.append(i)
    return pd.concat(hogares, ignore_index=True), pd.concat(individuos, ignore_index=True)
