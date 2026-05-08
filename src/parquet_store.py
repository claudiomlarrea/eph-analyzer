"""
Conversión y persistencia de bases EPH en formato Parquet.

Parquet es columnar, comprimido y ~10-20× más liviano que Excel,
con lectura ~50× más rápida. Es el formato recomendado para guardar
las bases procesadas y para alimentar la app de Streamlit.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"


def guardar_parquet(
    df: pd.DataFrame,
    nombre: str,
    directorio: Path | str = PROCESSED_DIR,
    compresion: str = "snappy",
) -> Path:
    """
    Guarda un DataFrame en Parquet.

    Parámetros
    ----------
    df : pd.DataFrame
    nombre : str
        Nombre del archivo (sin extensión). Ej: "hogar_2017_t1".
    directorio : Path | str
        Carpeta de destino (se crea si no existe).
    compresion : str
        Algoritmo: "snappy" (default, balance), "gzip" (más chico, más lento),
        "zstd" (mejor compresión moderna), "none".
    """
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    df_to_save = df.copy()
    for col in df_to_save.columns:
        dtype = df_to_save[col].dtype
        if dtype.name == "category":
            df_to_save[col] = df_to_save[col].astype("string")
        elif dtype == object:
            df_to_save[col] = df_to_save[col].astype("string")

    destino = directorio / f"{nombre}.parquet"
    df_to_save.to_parquet(
        destino,
        engine="pyarrow",
        compression=compresion,
        index=False,
    )

    tam_mb = destino.stat().st_size / 1024**2
    logger.info("Guardado %s · %.2f MB", destino, tam_mb)
    return destino


def cargar_parquet(
    nombre_o_ruta: str | Path,
    directorio: Path | str = PROCESSED_DIR,
) -> pd.DataFrame:
    """Lee un Parquet desde el directorio processed (o ruta absoluta)."""
    ruta = Path(nombre_o_ruta)
    if not ruta.is_absolute() and not ruta.exists():
        ruta = Path(directorio) / (
            ruta if str(ruta).endswith(".parquet") else f"{ruta}.parquet"
        )
    return pd.read_parquet(ruta, engine="pyarrow")


def listar_procesados(directorio: Path | str = PROCESSED_DIR) -> list[dict]:
    """Lista todos los Parquet ya guardados con tamaño y filas."""
    import pyarrow.parquet as pq

    directorio = Path(directorio)
    if not directorio.exists():
        return []
    out = []
    for f in sorted(directorio.glob("*.parquet")):
        meta = pq.read_metadata(f)
        out.append({
            "archivo": f.name,
            "ruta": str(f),
            "tamaño_mb": round(f.stat().st_size / 1024**2, 2),
            "filas": meta.num_rows,
            "columnas": meta.num_columns,
        })
    return out
