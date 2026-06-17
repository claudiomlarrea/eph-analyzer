"""Descarga microdatos EPH (hogar e individuo) desde mirror público de bases INDEC."""

from __future__ import annotations

import io
import urllib.request
import ssl
import urllib.error
from pathlib import Path
import zipfile

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


def _indec_zip_url(year: int, trimester: int) -> str:
    return f"https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_{trimester}_Trim_{year}_txt.zip"


def _url_exists(url: str) -> bool:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx):
            return True
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405):
            # Algunos hosts no aceptan HEAD; fallback a GET.
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                    timeout=20,
                    context=ctx,
                ):
                    return True
            except Exception:
                return False
        return False
    except Exception:
        return False


def _download_bytes(url: str, timeout: int = 180) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def _read_table_from_zip_bytes(zip_bytes: bytes, member_name: str) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        with zf.open(member_name) as fh:
            raw = fh.read()
    for enc in ("utf-8", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(raw), sep=";", decimal=",", encoding=enc, low_memory=False)
        except Exception:
            continue
    raise RuntimeError(f"No pude leer {member_name} desde ZIP INDEC")


def _fetch_from_indec_zip(year: int, trimester: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    zip_bytes = _download_bytes(_indec_zip_url(year, trimester), timeout=180)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    hog_candidates = [n for n in names if "hog" in n.lower()]
    ind_candidates = [n for n in names if "ind" in n.lower()]
    if not hog_candidates or not ind_candidates:
        raise RuntimeError(f"ZIP INDEC sin archivos hogar/individual para {year}T{trimester}")
    hogar = _read_table_from_zip_bytes(zip_bytes, hog_candidates[0])
    individual = _read_table_from_zip_bytes(zip_bytes, ind_candidates[0])
    return hogar, individual


def available_years(trimester: int, year_min: int, year_max: int) -> list[int]:
    """Años disponibles en el mirror para hogar+individual del trimestre indicado."""
    out: list[int] = []
    for year in range(year_min, year_max + 1):
        ok_github = _url_exists(_url("hogar", year, trimester)) and _url_exists(_url("individual", year, trimester))
        ok_indec = _url_exists(_indec_zip_url(year, trimester))
        if ok_github or ok_indec:
            out.append(year)
    return out


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

    try:
        hogar = _fetch_rds(_url("hogar", year, trimester))
        individual = _fetch_rds(_url("individual", year, trimester))
    except urllib.error.HTTPError:
        try:
            hogar, individual = _fetch_from_indec_zip(year, trimester)
        except Exception as exc:
            raise RuntimeError(
                f"No se encontró microdato para {year}T{trimester} en fuente automática (GitHub/INDEC)."
            ) from exc
    hogar.to_parquet(paths["hogar"], index=False)
    individual.to_parquet(paths["individual"], index=False)
    return hogar, individual


def download_panel(
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


def download_panel_tic(
    years: list[int] | None = None,
    trimester: int = TRIMESTER_TIC,
    *,
    force: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compatibilidad retroactiva."""
    return download_panel(years=years, trimester=trimester, force=force)
