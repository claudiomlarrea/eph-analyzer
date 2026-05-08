"""
Merger de bases EPH.

En la EPH del INDEC, la base de individuos ya viene con las variables del
hogar incluidas (cada fila de un individuo trae los datos de su hogar). Por
eso este módulo:

    1. Si recibe **solo individuo** y ya trae las variables clave de hogar
       (`ITF`, `IPCF`, `IV1`, etc.), lo deja como está y avisa.
    2. Si recibe **hogar + individuo** por separado, hace un left join sobre
       (CODUSU, NRO_HOGAR), agregando solo las columnas de hogar que NO
       estén ya presentes en individuo.
    3. Validación: chequea que ningún individuo quede huérfano (sin hogar
       coincidente) y reporta cuántos no matchean.

Devuelve siempre un DataFrame con un índice limpio y un dict con las
estadísticas del merge.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

import pandas as pd
from pandas.errors import PerformanceWarning

logger = logging.getLogger(__name__)

CLAVES_HOGAR = ["CODUSU", "NRO_HOGAR"]
CLAVES_INDIVIDUO = ["CODUSU", "NRO_HOGAR", "COMPONENTE"]


@dataclass
class ResultadoMerge:
    """Salida del proceso de merge."""

    df: pd.DataFrame
    n_hogares: int
    n_individuos: int
    n_huerfanos: int
    columnas_agregadas: list[str]
    advertencias: list[str]

    def __str__(self) -> str:
        return (
            f"Merge OK · {self.n_individuos:,} individuos en {self.n_hogares:,} hogares · "
            f"+{len(self.columnas_agregadas)} columnas de hogar agregadas · "
            f"{self.n_huerfanos} huérfanos"
        )


def mergear(
    df_hogar: pd.DataFrame | None,
    df_individuo: pd.DataFrame,
    validar_claves: bool = True,
) -> ResultadoMerge:
    """
    Une la base de hogar con la de individuo.

    Parámetros
    ----------
    df_hogar : pd.DataFrame | None
        Base de hogares. Puede ser None si solo se quiere trabajar con
        individuos (en cuyo caso la base de individuos debe traer las
        variables de hogar embebidas, como es habitual en EPH).
    df_individuo : pd.DataFrame
        Base de individuos.
    validar_claves : bool
        Si True, chequea que las claves estén presentes y no haya
        duplicados problemáticos.

    Returns
    -------
    ResultadoMerge
    """
    advertencias: list[str] = []

    if validar_claves:
        for col in CLAVES_INDIVIDUO:
            if col not in df_individuo.columns:
                raise KeyError(
                    f"La base de individuos no tiene la clave obligatoria '{col}'."
                )

    if df_hogar is None:
        n_hog = df_individuo[CLAVES_HOGAR].drop_duplicates().shape[0]
        advertencias.append(
            "Solo se entregó base de individuos. Se asume que ya trae "
            "variables de hogar embebidas (estructura habitual EPH)."
        )
        return ResultadoMerge(
            df=df_individuo.copy(),
            n_hogares=n_hog,
            n_individuos=len(df_individuo),
            n_huerfanos=0,
            columnas_agregadas=[],
            advertencias=advertencias,
        )

    if validar_claves:
        for col in CLAVES_HOGAR:
            if col not in df_hogar.columns:
                raise KeyError(
                    f"La base de hogares no tiene la clave obligatoria '{col}'."
                )
        dups_hog = df_hogar.duplicated(subset=CLAVES_HOGAR).sum()
        if dups_hog > 0:
            advertencias.append(
                f"Hay {dups_hog} hogares duplicados en la base de hogares "
                "(esto rompe el merge; se conserva el primero)."
            )
            df_hogar = df_hogar.drop_duplicates(subset=CLAVES_HOGAR, keep="first")

    cols_indiv = set(df_individuo.columns)
    cols_a_agregar = [
        c for c in df_hogar.columns
        if c not in cols_indiv or c in CLAVES_HOGAR
    ]
    df_hogar_subset = df_hogar[cols_a_agregar].copy()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PerformanceWarning)
        df_merged = df_individuo.merge(
            df_hogar_subset,
            on=CLAVES_HOGAR,
            how="left",
            validate="many_to_one",
            indicator="_merge_status",
        ).copy()

    n_huerfanos = int((df_merged["_merge_status"] == "left_only").sum())
    if n_huerfanos > 0:
        advertencias.append(
            f"{n_huerfanos} individuos sin hogar coincidente "
            "(no encontraron pareja en la base de hogar)."
        )

    df_merged = df_merged.drop(columns="_merge_status")
    columnas_agregadas = [c for c in cols_a_agregar if c not in CLAVES_HOGAR]

    n_hog = df_merged[CLAVES_HOGAR].drop_duplicates().shape[0]
    return ResultadoMerge(
        df=df_merged,
        n_hogares=n_hog,
        n_individuos=len(df_merged),
        n_huerfanos=n_huerfanos,
        columnas_agregadas=columnas_agregadas,
        advertencias=advertencias,
    )
