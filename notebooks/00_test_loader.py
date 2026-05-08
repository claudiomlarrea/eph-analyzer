"""
Smoke test del cargador y detector con los archivos del 1°T 2017 que
están guardados en OneDrive.

Ejecutar con:
    .venv/bin/python notebooks/00_test_loader.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import cargar_eph, resumen_dataframe
from src.file_detector import FileDetector

ARCHIVOS = [
    "/Users/claudiolarrea/Library/CloudStorage/OneDrive-Personal/"
    "11 Investigacion/2025/0 Inclusión Digital/0 Bases de datos/2017/"
    "1º Trimestre/usu_hogar_t117.xlsx",
    "/Users/claudiolarrea/Library/CloudStorage/OneDrive-Personal/"
    "11 Investigacion/2025/0 Inclusión Digital/0 Bases de datos/2017/"
    "1º Trimestre/usu_individual_t117_ult.xlsx",
]


def main() -> None:
    detector = FileDetector()

    for ruta_str in ARCHIVOS:
        ruta = Path(ruta_str)
        print("\n" + "=" * 78)
        print(f"ARCHIVO: {ruta.name}")
        print("=" * 78)

        if not ruta.exists():
            print(f"  ✗ No encontrado: {ruta}")
            continue

        try:
            df = cargar_eph(ruta)
        except Exception as exc:
            print(f"  ✗ Error al cargar: {exc}")
            continue

        resumen = resumen_dataframe(df)
        print(f"  ✓ Cargado correctamente")
        print(f"    Filas:    {resumen['filas']:,}")
        print(f"    Columnas: {resumen['columnas']:,}")
        print(f"    Memoria:  {resumen['memoria_mb']} MB")

        deteccion = detector.detectar(df.columns)
        print(f"\n  → {deteccion}")

        if deteccion.columnas_clave_encontradas:
            print(f"    Claves: {deteccion.columnas_clave_encontradas}")
        if deteccion.columnas_tipicas_encontradas:
            print(
                "    Variables típicas detectadas: "
                f"{deteccion.columnas_tipicas_encontradas}"
            )
        for adv in deteccion.advertencias:
            print(f"    ⚠ {adv}")

        muestra_cols = list(df.columns[:15])
        print(f"\n  Primeras 15 columnas: {muestra_cols}")

        nulos = df.isna().sum()
        nulos_top = nulos[nulos > 0].sort_values(ascending=False).head(5)
        if len(nulos_top) > 0:
            print(f"\n  Top 5 columnas con nulos:")
            for col, n in nulos_top.items():
                pct = 100 * n / len(df)
                print(f"    {col:20s} {n:>7,} ({pct:.1f}%)")

        print(f"\n  Primeras 3 filas:")
        with_cols = df[muestra_cols[:8]].head(3).to_string(index=False, max_colwidth=15)
        for line in with_cols.split("\n"):
            print(f"    {line}")


if __name__ == "__main__":
    main()
