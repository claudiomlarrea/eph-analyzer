"""
Test del Bloque 1 — Análisis estadístico completo sobre 2017 1°T.

Verifica:
    - Estadística descriptiva (frecuencias y estadísticos)
    - Tabla cruzada
    - Quintiles y Gini sobre IPCF
    - Correlaciones entre variables socioeconómicas
    - Cronbach sobre los componentes del índice de exclusión
    - Cálculo del índice de exclusión digital

Ejecutar:
    .venv/bin/python notebooks/02_test_analisis.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

from src.analisis.correlaciones import (
    correlaciones_con_p,
    cronbach_alpha,
    matriz_correlacion,
)
from src.analisis.descriptivo import (
    estadisticos,
    frecuencias,
    tabla_cruzada,
)
from src.analisis.desigualdad import (
    comparar_por_grupo,
    gini,
    quintiles,
    razon_quintil,
    theil,
)
from src.indice_exclusion import calcular_indice_exclusion
from src.parquet_store import cargar_parquet


def encabezado(texto: str) -> None:
    print("\n" + "=" * 78)
    print(texto)
    print("=" * 78)


def main() -> None:
    print("Cargando Parquet...")
    df = cargar_parquet("eph_2017_t1")
    print(f"  → {df.shape[0]:,} filas × {df.shape[1]:,} columnas")

    encabezado("1) FRECUENCIAS — Sexo (CH04)")
    print(frecuencias(df, "CH04_LABEL").to_string(index=False))

    encabezado("1) FRECUENCIAS — Nivel educativo (NIVEL_ED)")
    print(frecuencias(df, "NIVEL_ED_LABEL", ordenar_por="frecuencia").to_string(index=False))

    encabezado("2) ESTADÍSTICOS — Edad (CH06)")
    print(estadisticos(df, "CH06").to_string())

    encabezado("2) ESTADÍSTICOS — Ingreso per cápita familiar (IPCF)")
    print(estadisticos(df, "IPCF", ponderador="PONDIH").to_string())

    encabezado("3) TABLA CRUZADA — Sexo × Condición de actividad (% por sexo)")
    if "CH04_LABEL" in df.columns and "ESTADO_LABEL" in df.columns:
        cross = tabla_cruzada(df, "CH04_LABEL", "ESTADO_LABEL", normalizar="fila")
        print(cross.to_string())

    encabezado("4) QUINTILES de IPCF (ponderados por PONDIH)")
    q = quintiles(df, "IPCF", ponderador="PONDIH", n_grupos=5)
    print(q.to_string(index=False))

    encabezado("5) DESIGUALDAD")
    g = gini(df, "IPCF", ponderador="PONDIH")
    t = theil(df, "IPCF", ponderador="PONDIH")
    razon = razon_quintil(df, "IPCF", ponderador="PONDIH")
    print(f"  Gini (IPCF): {g}")
    print(f"  Theil T:     {t['theil_T']}")
    print(f"  Theil L:     {t['theil_L']}")
    print(f"  Razón Q5/Q1: {razon}")

    encabezado("6) COMPARACIÓN REGIONAL (por código de región)")
    comp = comparar_por_grupo(df, "IPCF", "REGION", ponderador="PONDIH")
    print(comp.to_string(index=False))

    encabezado("7) CORRELACIONES (Pearson) — Edad, Educ, Ingresos")
    cols_corr = [c for c in ["CH06", "NIVEL_ED", "P21", "IPCF", "ITF"] if c in df.columns]
    if cols_corr:
        print(matriz_correlacion(df, cols_corr, metodo="pearson").to_string())

    encabezado("7) CORRELACIONES con p-valor (top 5)")
    if cols_corr:
        cp = correlaciones_con_p(df, cols_corr, metodo="pearson")
        print(cp.head(10).to_string(index=False))

    encabezado("8) CRONBACH α — Componentes potenciales del índice de exclusión")
    items_exclusion = [
        c for c in [
            "EDUC_SECUNDARIA_COMPLETA_O_MAS",
            "EDUC_SUPERIOR_COMPLETA",
            "OCUPADO",
        ]
        if c in df.columns
    ]
    if len(items_exclusion) >= 2:
        diag = cronbach_alpha(df, items_exclusion)
        if isinstance(diag, dict):
            print(f"  Alpha:           {diag['alpha']}")
            print(f"  Interpretación:  {diag['interpretacion']}")
            print(f"  k (ítems):       {diag['k']}")
            print(f"  n (filas):       {diag['n']:,}")
            print(f"  Items:           {diag['items']}")

    encabezado("9) ÍNDICE DE EXCLUSIÓN DIGITAL")
    res = calcular_indice_exclusion(df)
    print(f"  {res}")
    if res.advertencias:
        print("\n  Advertencias:")
        for a in res.advertencias:
            print(f"    ⚠ {a}")

    print(f"\n  Distribución de NIVEL_EXCLUSION:")
    if "NIVEL_EXCLUSION" in res.df.columns:
        print(
            res.df["NIVEL_EXCLUSION"]
            .value_counts(dropna=False)
            .sort_index()
            .to_string()
        )

    print(f"\n  Estadísticos del INDICE_EXCLUSION:")
    print(estadisticos(res.df, "INDICE_EXCLUSION").to_string())

    print(f"\n  Promedio del índice por nivel educativo:")
    if "NIVEL_ED_LABEL" in res.df.columns:
        prom = (
            res.df.groupby("NIVEL_ED_LABEL")["INDICE_EXCLUSION"]
            .agg(["mean", "count"])
            .round(3)
            .sort_values("mean", ascending=False)
        )
        print(prom.to_string())

    print(f"\n  Promedio del índice por quintil de IPCF:")
    if "QUINTIL_IPCF" in res.df.columns:
        prom_q = (
            res.df.groupby("QUINTIL_IPCF", observed=False)["INDICE_EXCLUSION"]
            .agg(["mean", "count"])
            .round(3)
        )
        print(prom_q.to_string())


if __name__ == "__main__":
    main()
