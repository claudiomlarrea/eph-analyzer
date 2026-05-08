"""
Pipeline completo: cargar → limpiar → mergear → guardar Parquet.

Es la función `procesar_eph` que se llama desde la app de Streamlit y
desde scripts batch para preparar las bases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data_cleaner import DataCleaner
from src.data_loader import cargar_eph
from src.file_detector import DetectionResult, FileDetector
from src.merger import ResultadoMerge, mergear
from src.parquet_store import guardar_parquet

logger = logging.getLogger(__name__)


@dataclass
class ResultadoPipeline:
    df: pd.DataFrame
    deteccion: DetectionResult
    merge: ResultadoMerge | None
    parquet_path: Path | None
    advertencias: list[str]


def procesar_eph(
    ruta_individuo: str | Path,
    ruta_hogar: str | Path | None = None,
    nombre_salida: str | None = None,
    guardar: bool = True,
    limpiar: bool = True,
) -> ResultadoPipeline:
    """
    Ejecuta el pipeline completo:
        1. Carga la base de individuos.
        2. Si se entrega base de hogar, hace el merge.
        3. Aplica limpieza y etiquetas.
        4. Guarda como Parquet en data/processed/.
    """
    detector = FileDetector()
    cleaner = DataCleaner()
    advertencias: list[str] = []

    df_individuo = cargar_eph(ruta_individuo)
    deteccion = detector.detectar(df_individuo.columns)
    logger.info(str(deteccion))

    df_hogar = None
    if ruta_hogar is not None:
        df_hogar = cargar_eph(ruta_hogar)
        det_hogar = detector.detectar(df_hogar.columns)
        if det_hogar.tipo not in ("hogar", "tic_hogar"):
            advertencias.append(
                f"El archivo entregado como hogar fue detectado como '{det_hogar.tipo}'. "
                "Se intentará el merge de todos modos."
            )

    resultado_merge = mergear(df_hogar, df_individuo)
    advertencias.extend(resultado_merge.advertencias)
    df_merged = resultado_merge.df

    if limpiar:
        df_final = cleaner.limpiar(df_merged)
    else:
        df_final = df_merged

    parquet_path = None
    if guardar:
        if nombre_salida is None:
            anio = (
                int(df_final["ANO4"].iloc[0])
                if "ANO4" in df_final.columns and len(df_final) > 0
                else "sin_anio"
            )
            trim = (
                int(df_final["TRIMESTRE"].iloc[0])
                if "TRIMESTRE" in df_final.columns and len(df_final) > 0
                else "sin_trim"
            )
            nombre_salida = f"eph_{deteccion.tipo}_{anio}_t{trim}"
        parquet_path = guardar_parquet(df_final, nombre_salida)

    return ResultadoPipeline(
        df=df_final,
        deteccion=deteccion,
        merge=resultado_merge,
        parquet_path=parquet_path,
        advertencias=advertencias,
    )
