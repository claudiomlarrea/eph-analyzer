"""
Cargador genérico de bases EPH del INDEC.

Soporta los siguientes formatos de entrada:
    - .xlsx / .xls          : Excel (vía openpyxl / xlrd)
    - .csv                   : CSV con detección automática de separador y encoding
    - .txt                   : texto delimitado (típicamente ';' en INDEC)
    - .dbf                   : dBase (formato histórico INDEC, vía dbfread)
    - .parquet               : Parquet (vía pyarrow)
    - .zip                   : descomprime y carga el primer archivo de datos válido

Devuelve siempre un pandas.DataFrame con columnas en mayúsculas y tipos
inferidos.

Uso:
    from src.data_loader import cargar_eph
    df = cargar_eph("/ruta/al/archivo.xlsx")
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

EXTENSIONES_DATOS = {".xlsx", ".xls", ".csv", ".txt", ".dbf", ".parquet"}


class FormatoNoSoportadoError(ValueError):
    """Se levanta cuando el archivo no tiene un formato manejable."""


def cargar_eph(
    ruta: str | Path,
    sheet: Optional[str | int] = 0,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Carga una base EPH desde cualquier formato soportado.

    Parámetros
    ----------
    ruta : str | Path
        Ruta al archivo a cargar.
    sheet : str | int, opcional
        Hoja a leer si es Excel (por defecto la primera).
    nrows : int, opcional
        Limita la cantidad de filas (útil para previsualizar archivos grandes).

    Returns
    -------
    pandas.DataFrame
        DataFrame con columnas normalizadas a mayúsculas.
    """
    ruta = Path(ruta).expanduser().resolve()

    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    ext = ruta.suffix.lower()

    if ext == ".zip":
        df = _cargar_zip(ruta, sheet=sheet, nrows=nrows)
    elif ext in {".xlsx", ".xls"}:
        df = _cargar_excel(ruta, sheet=sheet, nrows=nrows)
    elif ext in {".csv", ".txt"}:
        df = _cargar_texto(ruta, nrows=nrows)
    elif ext == ".dbf":
        df = _cargar_dbf(ruta, nrows=nrows)
    elif ext == ".parquet":
        df = pd.read_parquet(ruta)
        if nrows is not None:
            df = df.head(nrows)
    else:
        raise FormatoNoSoportadoError(
            f"Formato '{ext}' no soportado. Aceptados: {sorted(EXTENSIONES_DATOS)} y .zip"
        )

    df.columns = [str(c).strip().upper() for c in df.columns]

    logger.info(
        "Cargado %s · %d filas × %d columnas",
        ruta.name,
        df.shape[0],
        df.shape[1],
    )
    return df


def _cargar_excel(ruta: Path, sheet: Optional[str | int], nrows: Optional[int]) -> pd.DataFrame:
    engine = "openpyxl" if ruta.suffix.lower() == ".xlsx" else None
    return pd.read_excel(ruta, sheet_name=sheet, nrows=nrows, engine=engine)


def _cargar_texto(ruta: Path, nrows: Optional[int]) -> pd.DataFrame:
    """Lee CSV o TXT detectando separador y encoding."""
    encoding = _detectar_encoding(ruta)

    for sep in [";", ",", "\t", "|"]:
        try:
            df = pd.read_csv(
                ruta,
                sep=sep,
                encoding=encoding,
                nrows=nrows,
                low_memory=False,
                on_bad_lines="warn",
            )
            if df.shape[1] >= 3:
                return df
        except (pd.errors.ParserError, UnicodeDecodeError):
            continue

    return pd.read_csv(ruta, sep=None, engine="python", encoding=encoding, nrows=nrows)


def _cargar_dbf(ruta: Path, nrows: Optional[int]) -> pd.DataFrame:
    from dbfread import DBF

    table = DBF(str(ruta), encoding="latin-1", load=True)
    registros = list(table)
    if nrows is not None:
        registros = registros[:nrows]
    return pd.DataFrame(registros)


def _cargar_zip(ruta: Path, sheet: Optional[str | int], nrows: Optional[int]) -> pd.DataFrame:
    """Descomprime el .zip y carga el primer archivo de datos compatible."""
    with zipfile.ZipFile(ruta, "r") as zf:
        candidatos = [
            n for n in zf.namelist()
            if Path(n).suffix.lower() in EXTENSIONES_DATOS
            and not n.startswith("__MACOSX")
        ]
        if not candidatos:
            raise FormatoNoSoportadoError(
                f"El zip {ruta.name} no contiene archivos de datos compatibles."
            )
        candidatos.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
        objetivo = candidatos[0]

        destino = ruta.parent / Path(objetivo).name
        with zf.open(objetivo) as src, open(destino, "wb") as dst:
            dst.write(src.read())

    try:
        return cargar_eph(destino, sheet=sheet, nrows=nrows)
    finally:
        if destino.exists():
            destino.unlink()


def _detectar_encoding(ruta: Path, n_bytes: int = 32_768) -> str:
    """Detecta el encoding leyendo los primeros bytes del archivo."""
    try:
        import chardet

        with open(ruta, "rb") as f:
            sample = f.read(n_bytes)
        resultado = chardet.detect(sample)
        return resultado.get("encoding") or "utf-8"
    except Exception:
        return "utf-8"


def resumen_dataframe(df: pd.DataFrame) -> dict:
    """Devuelve un resumen estructurado de un DataFrame."""
    return {
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "memoria_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2),
        "columnas_lista": list(df.columns),
        "nulos_por_columna": df.isna().sum().to_dict(),
        "tipos": {c: str(t) for c, t in df.dtypes.items()},
    }
