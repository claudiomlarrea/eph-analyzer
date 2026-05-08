"""
Limpieza y enriquecimiento de DataFrames de la EPH.

Funcionalidades:
    - normalizar tipos de datos (int / float / categóricas).
    - convertir códigos especiales (9 = NS/NR en muchas variables) a NaN
      cuando corresponda.
    - aplicar etiquetas humanas a columnas categóricas usando el diccionario
      EPH (genera columnas adicionales con sufijo `_LABEL`).
    - calcular variables derivadas usuales (grupo etario, jefe de hogar,
      quintil de ingresos, etc.).

El objetivo es que después de pasar por aquí, los DataFrames estén listos
para análisis estadístico y modelado, sin perder los códigos originales.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DICCIONARIO_PATH = Path(__file__).parent.parent / "diccionario" / "eph_variables.json"

CODIGOS_NSNR = {9, 99, 999, -9, -99}

VARIABLES_NUMERICAS = {
    "CH06", "CH14", "ANO4", "TRIMESTRE", "AGLOMERADO", "REGION",
    "IX_TOT", "IX_MEN10", "IX_MAYEQ10", "IV2", "II1",
    "P21", "P47T", "TOT_P12", "ITF", "IPCF",
    "PONDERA", "PONDIH", "PONDII", "PONDIIO",
}

VARIABLES_CATEGORICAS_CON_NSNR_COMO_NULO = {
    "CH07", "CH08", "CH11", "CH13", "CAT_OCUP", "II7", "IV1",
}


class DataCleaner:
    """Aplica limpieza y enriquecimiento sobre un DataFrame EPH."""

    def __init__(self, diccionario_path: Path | str = DICCIONARIO_PATH):
        with open(diccionario_path, "r", encoding="utf-8") as f:
            self.diccionario = json.load(f)
        self._etiquetas = self._construir_mapa_etiquetas()

    def _construir_mapa_etiquetas(self) -> dict[str, dict]:
        mapa: dict[str, dict] = {}
        for seccion, contenido in self.diccionario.items():
            if seccion.startswith("_") or seccion in {"claves_unicas", "fingerprints"}:
                continue
            if not isinstance(contenido, dict):
                continue
            for variable, meta in contenido.items():
                if isinstance(meta, dict) and "etiquetas" in meta:
                    mapa[variable.upper()] = meta["etiquetas"]
        return mapa

    def limpiar(
        self,
        df: pd.DataFrame,
        aplicar_etiquetas: bool = True,
        nsnr_a_nulo: bool = True,
        agregar_derivadas: bool = True,
    ) -> pd.DataFrame:
        """
        Pipeline de limpieza completa.

        Parámetros
        ----------
        df : pd.DataFrame
            DataFrame con columnas en mayúsculas (output de `cargar_eph`).
        aplicar_etiquetas : bool
            Si True, agrega columnas `<VAR>_LABEL` con las etiquetas humanas.
        nsnr_a_nulo : bool
            Si True, convierte códigos 9/99/-9 a NaN en variables aplicables.
        agregar_derivadas : bool
            Si True, agrega columnas derivadas (grupo etario, jefe de hogar,
            etc.) cuando las variables fuente están disponibles.
        """
        df = df.copy()
        df = self._normalizar_objetos(df)
        df = self._normalizar_tipos(df)

        if nsnr_a_nulo:
            df = self._marcar_nsnr_como_nulo(df)

        if aplicar_etiquetas:
            df = self._aplicar_etiquetas(df)

        if agregar_derivadas:
            df = self._agregar_variables_derivadas(df)

        return df.copy()

    def _normalizar_objetos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza columnas tipo object: strings con solo espacios → NaN,
        y trata de inferir tipo numérico si la columna en realidad es
        numérica con algunos huecos. Esto evita el error típico de Arrow
        cuando una columna mezcla int y str-vacío.
        """
        for col in df.columns:
            if df[col].dtype != object:
                continue
            s = df[col]
            if s.map(type).eq(str).any():
                s = s.where(~s.astype(str).str.strip().eq(""), np.nan)
            numeric = pd.to_numeric(s, errors="coerce")
            if numeric.notna().sum() >= s.notna().sum() * 0.95:
                df[col] = numeric
            else:
                df[col] = s.astype("string")
        return df

    def _normalizar_tipos(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if col in VARIABLES_NUMERICAS:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _marcar_nsnr_como_nulo(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in VARIABLES_CATEGORICAS_CON_NSNR_COMO_NULO:
            if col in df.columns:
                df[col] = df[col].where(~df[col].isin(CODIGOS_NSNR), np.nan)
        return df

    def _aplicar_etiquetas(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, etiquetas in self._etiquetas.items():
            if col not in df.columns:
                continue
            mapa = {self._coerce_key(k): v for k, v in etiquetas.items()}
            label_col = f"{col}_LABEL"
            df[label_col] = df[col].map(self._normalizar_para_lookup).map(mapa)
        return df

    @staticmethod
    def _coerce_key(k: str) -> str:
        try:
            return str(int(k))
        except (TypeError, ValueError):
            return str(k).strip()

    @staticmethod
    def _normalizar_para_lookup(v):
        if pd.isna(v):
            return v
        try:
            return str(int(v))
        except (TypeError, ValueError):
            return str(v).strip()

    def _agregar_variables_derivadas(self, df: pd.DataFrame) -> pd.DataFrame:
        if "CH06" in df.columns:
            df["GRUPO_ETARIO"] = pd.cut(
                df["CH06"],
                bins=[-1, 4, 14, 29, 44, 64, 200],
                labels=[
                    "0-4 años",
                    "5-14 años",
                    "15-29 años",
                    "30-44 años",
                    "45-64 años",
                    "65+ años",
                ],
            )

        if "CH03" in df.columns:
            df["ES_JEFE_HOGAR"] = (df["CH03"] == 1).astype("Int8")

        if "ESTADO" in df.columns:
            df["OCUPADO"] = (df["ESTADO"] == 1).astype("Int8")
            df["DESOCUPADO"] = (df["ESTADO"] == 2).astype("Int8")
            df["INACTIVO"] = (df["ESTADO"] == 3).astype("Int8")

        if "NIVEL_ED" in df.columns:
            df["EDUC_SUPERIOR_COMPLETA"] = df["NIVEL_ED"].isin([6]).astype("Int8")
            df["EDUC_SECUNDARIA_COMPLETA_O_MAS"] = df["NIVEL_ED"].isin([4, 5, 6]).astype("Int8")

        if "IPCF" in df.columns:
            ipcf_validos = df["IPCF"][df["IPCF"] > 0]
            if len(ipcf_validos) > 0:
                df["QUINTIL_IPCF"] = pd.qcut(
                    df["IPCF"].where(df["IPCF"] > 0),
                    q=5,
                    labels=["Q1 (más bajo)", "Q2", "Q3", "Q4", "Q5 (más alto)"],
                    duplicates="drop",
                )

        return df
