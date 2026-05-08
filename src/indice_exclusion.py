"""
Índice compuesto de Exclusión Digital (Larrea, 2025).

El índice se construye con tres dimensiones, cada una con valor en [0, 1]:

    1) ACCESO MATERIAL
       - Conexión a internet en el hogar
       - Disponibilidad de computadora
       - Disponibilidad de teléfono celular
       - Cantidad de dispositivos por persona

    2) COMPETENCIAS DIGITALES (proxy)
       - Edad (jóvenes ≈ más competencias)
       - Nivel educativo del individuo / jefe de hogar
       - Asistencia educativa actual

    3) USO SIGNIFICATIVO
       - Uso de internet
       - Uso de computadora
       - Uso para fines educativos / laborales (cuando está disponible)

El índice global es el **promedio simple de las tres dimensiones**.
Resultado en [0, 1]: 0 = inclusión total, 1 = exclusión total.

Si la base no tiene módulo TIC, las dimensiones que dependen de TIC se
marcan como NA y el índice se calcula con las disponibles, dejando un
indicador de cobertura para que el usuario sepa la calidad.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VARS_ACCESO_TIC_HOGAR = {
    "internet": ["IH_II_04"],
    "computadora": ["IH_II_03", "IV12_3"],
    "celular": ["IH_II_02", "IH_II_01"],
}

VARS_USO_TIC_INDIVIDUAL = {
    "usa_internet": ["IP_III_04"],
    "usa_computadora": ["IP_III_05"],
    "usa_celular": ["IP_III_06"],
}


@dataclass
class ResultadoIndice:
    df: pd.DataFrame
    cobertura: dict
    advertencias: list[str]

    def __str__(self) -> str:
        c = self.cobertura
        return (
            f"Índice exclusión digital · "
            f"acceso={c.get('acceso_pct', 0):.0f}% / "
            f"competencias={c.get('competencias_pct', 0):.0f}% / "
            f"uso={c.get('uso_pct', 0):.0f}% disponible"
        )


def calcular_indice_exclusion(df: pd.DataFrame) -> ResultadoIndice:
    """
    Devuelve el DataFrame original con columnas adicionales:
        - DIM_ACCESO          ∈ [0,1] — exclusión por falta de acceso
        - DIM_COMPETENCIAS    ∈ [0,1] — exclusión por falta de competencias
        - DIM_USO             ∈ [0,1] — exclusión por bajo uso (NaN si no hay TIC)
        - INDICE_EXCLUSION    ∈ [0,1] — promedio de las dimensiones disponibles
        - NIVEL_EXCLUSION     ∈ {Inclusión, Exclusión leve, moderada, severa}
    """
    df = df.copy()
    advertencias: list[str] = []

    dim_acceso, cob_acceso = _dimension_acceso(df)
    df["DIM_ACCESO"] = dim_acceso

    dim_comp, cob_comp = _dimension_competencias(df)
    df["DIM_COMPETENCIAS"] = dim_comp

    dim_uso, cob_uso = _dimension_uso(df)
    df["DIM_USO"] = dim_uso

    if cob_acceso == 0:
        advertencias.append("Dimensión ACCESO sin variables TIC: usando proxies débiles.")
    if cob_uso == 0:
        advertencias.append("Dimensión USO no disponible: la base no tiene módulo TIC individual.")

    dimensiones = pd.concat(
        [df["DIM_ACCESO"], df["DIM_COMPETENCIAS"], df["DIM_USO"]],
        axis=1,
    )
    df["INDICE_EXCLUSION"] = dimensiones.mean(axis=1, skipna=True).round(4)

    df["NIVEL_EXCLUSION"] = pd.cut(
        df["INDICE_EXCLUSION"],
        bins=[-0.001, 0.25, 0.50, 0.75, 1.001],
        labels=[
            "Inclusión",
            "Exclusión leve",
            "Exclusión moderada",
            "Exclusión severa",
        ],
    )

    cobertura = {
        "acceso_pct": cob_acceso * 100,
        "competencias_pct": cob_comp * 100,
        "uso_pct": cob_uso * 100,
    }
    return ResultadoIndice(df=df, cobertura=cobertura, advertencias=advertencias)


def _dimension_acceso(df: pd.DataFrame) -> tuple[pd.Series, float]:
    """Dimensión 1: acceso material a TIC."""
    componentes: list[pd.Series] = []
    cobertura_count = 0
    cobertura_total = len(VARS_ACCESO_TIC_HOGAR)

    for nombre, candidatos in VARS_ACCESO_TIC_HOGAR.items():
        col = next((c for c in candidatos if c in df.columns), None)
        if col is None:
            continue
        cobertura_count += 1
        s = pd.to_numeric(df[col], errors="coerce")
        carencia = (s == 2).astype(float)
        carencia = carencia.where(s.isin([1, 2]), np.nan)
        componentes.append(carencia.rename(f"_falta_{nombre}"))

    if not componentes:
        if "EDUC_SECUNDARIA_COMPLETA_O_MAS" in df.columns and "QUINTIL_IPCF" in df.columns:
            edu_low = (df["EDUC_SECUNDARIA_COMPLETA_O_MAS"] == 0).astype(float)
            q_low = df["QUINTIL_IPCF"].isin(["Q1 (más bajo)", "Q2"]).astype(float)
            proxy = (edu_low + q_low) / 2
            return proxy.fillna(np.nan), 0.0
        return pd.Series(np.nan, index=df.index), 0.0

    matriz = pd.concat(componentes, axis=1)
    return matriz.mean(axis=1, skipna=True), cobertura_count / cobertura_total


def _dimension_competencias(df: pd.DataFrame) -> tuple[pd.Series, float]:
    """Dimensión 2: competencias digitales (proxy: edad + educación)."""
    factores: list[pd.Series] = []
    cobertura = 0

    if "CH06" in df.columns:
        edad = pd.to_numeric(df["CH06"], errors="coerce")
        comp_edad = pd.Series(np.nan, index=df.index)
        comp_edad[edad < 30] = 0.0
        comp_edad[(edad >= 30) & (edad < 45)] = 0.2
        comp_edad[(edad >= 45) & (edad < 60)] = 0.4
        comp_edad[(edad >= 60) & (edad < 75)] = 0.7
        comp_edad[edad >= 75] = 0.9
        factores.append(comp_edad.rename("_comp_edad"))
        cobertura += 1

    if "NIVEL_ED" in df.columns:
        ne = pd.to_numeric(df["NIVEL_ED"], errors="coerce")
        comp_ed = pd.Series(np.nan, index=df.index)
        comp_ed[ne == 7] = 1.0  # sin instrucción
        comp_ed[ne == 1] = 0.9  # primaria incompleta
        comp_ed[ne == 2] = 0.7  # primaria completa
        comp_ed[ne == 3] = 0.5  # secundaria incompleta
        comp_ed[ne == 4] = 0.3  # secundaria completa
        comp_ed[ne == 5] = 0.15  # superior incompleta
        comp_ed[ne == 6] = 0.0  # superior completa
        factores.append(comp_ed.rename("_comp_edu"))
        cobertura += 1

    if not factores:
        return pd.Series(np.nan, index=df.index), 0.0

    matriz = pd.concat(factores, axis=1)
    return matriz.mean(axis=1, skipna=True).round(4), cobertura / 2


def _dimension_uso(df: pd.DataFrame) -> tuple[pd.Series, float]:
    """Dimensión 3: uso significativo de TIC (requiere módulo TIC individual)."""
    componentes: list[pd.Series] = []
    cobertura_count = 0
    cobertura_total = len(VARS_USO_TIC_INDIVIDUAL)

    for nombre, candidatos in VARS_USO_TIC_INDIVIDUAL.items():
        col = next((c for c in candidatos if c in df.columns), None)
        if col is None:
            continue
        cobertura_count += 1
        s = pd.to_numeric(df[col], errors="coerce")
        no_uso = (s == 2).astype(float)
        no_uso = no_uso.where(s.isin([1, 2]), np.nan)
        componentes.append(no_uso.rename(f"_no_{nombre}"))

    if not componentes:
        return pd.Series(np.nan, index=df.index), 0.0

    matriz = pd.concat(componentes, axis=1)
    return matriz.mean(axis=1, skipna=True), cobertura_count / cobertura_total
