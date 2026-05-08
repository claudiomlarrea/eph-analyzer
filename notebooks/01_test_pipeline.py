"""
Test del pipeline completo con los archivos del 1°T 2017.

Verifica:
    - Carga de hogar e individuo.
    - Merge correcto (sin huérfanos).
    - Limpieza con etiquetas y variables derivadas.
    - Guardado a Parquet con conteo de tamaño y velocidad de lectura.

Ejecutar:
    .venv/bin/python notebooks/01_test_pipeline.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.parquet_store import cargar_parquet, listar_procesados
from src.pipeline import procesar_eph

ONEDRIVE = (
    "/Users/claudiolarrea/Library/CloudStorage/OneDrive-Personal/"
    "11 Investigacion/2025/0 Inclusión Digital/0 Bases de datos/"
    "2017/1º Trimestre"
)
RUTA_HOGAR = f"{ONEDRIVE}/usu_hogar_t117.xlsx"
RUTA_INDIVIDUO = f"{ONEDRIVE}/usu_individual_t117_ult.xlsx"


def main() -> None:
    print("=" * 78)
    print("PIPELINE EPH — 1° Trimestre 2017")
    print("=" * 78)

    t0 = time.time()
    resultado = procesar_eph(
        ruta_individuo=RUTA_INDIVIDUO,
        ruta_hogar=RUTA_HOGAR,
        nombre_salida="eph_2017_t1",
    )
    elapsed = time.time() - t0

    print(f"\n✓ Pipeline ejecutado en {elapsed:.1f}s")
    print(f"  → {resultado.deteccion}")
    print(f"  → {resultado.merge}")
    if resultado.parquet_path:
        tam = resultado.parquet_path.stat().st_size / 1024**2
        print(f"  → Guardado: {resultado.parquet_path.name} ({tam:.2f} MB)")

    df = resultado.df
    print(f"\nDataFrame final: {df.shape[0]:,} filas × {df.shape[1]:,} columnas")

    print("\n--- Variables derivadas creadas ---")
    derivadas = [
        c for c in [
            "GRUPO_ETARIO", "ES_JEFE_HOGAR", "OCUPADO", "DESOCUPADO", "INACTIVO",
            "EDUC_SUPERIOR_COMPLETA", "EDUC_SECUNDARIA_COMPLETA_O_MAS", "QUINTIL_IPCF",
        ]
        if c in df.columns
    ]
    for c in derivadas:
        print(f"  ✓ {c}")

    print("\n--- Columnas con etiquetas (LABEL) ---")
    label_cols = [c for c in df.columns if c.endswith("_LABEL")]
    print(f"  Total: {len(label_cols)}")
    for c in label_cols[:8]:
        print(f"  • {c}")
    if len(label_cols) > 8:
        print(f"  ... y {len(label_cols) - 8} más")

    print("\n--- Distribución de sexo (CH04) ---")
    if "CH04_LABEL" in df.columns:
        print(df["CH04_LABEL"].value_counts(dropna=False).to_string())

    print("\n--- Distribución de nivel educativo (NIVEL_ED) ---")
    if "NIVEL_ED_LABEL" in df.columns:
        print(df["NIVEL_ED_LABEL"].value_counts(dropna=False).to_string())

    print("\n--- Distribución de condición de actividad (ESTADO) ---")
    if "ESTADO_LABEL" in df.columns:
        print(df["ESTADO_LABEL"].value_counts(dropna=False).to_string())

    print("\n--- Distribución por grupo etario ---")
    if "GRUPO_ETARIO" in df.columns:
        print(df["GRUPO_ETARIO"].value_counts(dropna=False).sort_index().to_string())

    print("\n--- Quintiles de ingreso per cápita familiar ---")
    if "QUINTIL_IPCF" in df.columns:
        print(df["QUINTIL_IPCF"].value_counts(dropna=False).sort_index().to_string())

    if resultado.parquet_path:
        print("\n--- Test de lectura del Parquet ---")
        t0 = time.time()
        df_back = cargar_parquet(resultado.parquet_path)
        elapsed_read = time.time() - t0
        print(f"  Leído en {elapsed_read*1000:.0f} ms · {df_back.shape}")

    print("\n--- Archivos en data/processed/ ---")
    for info in listar_procesados():
        print(
            f"  • {info['archivo']:30s} "
            f"{info['tamaño_mb']:>6.2f} MB · "
            f"{info['filas']:>7,} filas × {info['columnas']:>3} cols"
        )

    if resultado.advertencias:
        print("\n⚠ Advertencias:")
        for a in resultado.advertencias:
            print(f"  • {a}")


if __name__ == "__main__":
    main()
