#!/usr/bin/env python3
"""Sistema de pedidos de análisis EPH (INDEC) → Excel + Word.

Ejemplos:
  python run.py --pedido pedidos/nacional.json
  python run.py --san-juan --years 2017-2022 --analisis descriptivos,logistica,shap
  python run.py --ambito nacional --solo-excel
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from indec_auto.src.engine import procesar_solicitud  # noqa: E402
from indec_auto.src.request import SolicitudAnalisis  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pedir análisis sobre microdatos EPH (hogar, individuo, TIC INDEC)"
    )
    parser.add_argument(
        "--pedido",
        type=Path,
        help="Archivo JSON con la solicitud (ver pedidos/ejemplo.json)",
    )
    parser.add_argument("--titulo", type=str, default=None)
    parser.add_argument("--ambito", choices=["nacional", "san_juan", "aglomerado"], default="nacional")
    parser.add_argument("--aglomerado", type=int, default=None, help="Código aglomerado EPH (si ambito=aglomerado)")
    parser.add_argument("--years", type=str, default="2026", help="Año o rango, ej. 2026 o 2017-2026")
    parser.add_argument("--trimestre", type=int, default=4, help="Trimestre EPH (1..4)")
    parser.add_argument("--modulo", choices=["tic", "base"], default="tic", help="Tipo de módulo a analizar")
    parser.add_argument(
        "--analisis",
        type=str,
        default="todos",
        help="Lista separada por comas: descriptivos,frecuencias,correlaciones,logistica,cluster,shap,todos",
    )
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--san-juan", action="store_true", help="Atajo: ámbito Gran San Juan (agl. 27)")
    parser.add_argument("--solo-excel", action="store_true")
    parser.add_argument("--solo-word", action="store_true")
    args = parser.parse_args()

    if args.pedido:
        solicitud = SolicitudAnalisis.desde_json(args.pedido)
    else:
        if "-" in args.years:
            y0, y1 = map(int, args.years.split("-"))
            years = list(range(y0, y1 + 1))
        else:
            years = [int(args.years)]
        ambito = "san_juan" if args.san_juan else args.ambito
        excel = not args.solo_word
        word = not args.solo_excel
        solicitud = SolicitudAnalisis(
            titulo=args.titulo or "Analizador automático EPH",
            years=years,
            trimestre=args.trimestre,
            modulo=args.modulo,
            ambito=ambito,
            aglomerado=args.aglomerado,
            analisis=[a.strip() for a in args.analisis.split(",")],
            excel=excel,
            word=word,
            force_download=args.force_download,
        )

    print(f"Procesando: {solicitud.titulo}")
    print(f"  Ámbito: {solicitud.label} | Período: {solicitud.periodo_texto()}")
    print(f"  Análisis: {', '.join(sorted(solicitud.analisis_resueltos))}")
    print(f"  Módulo: {solicitud.modulo}")
    print("  Descargando microdatos INDEC (hogar + individuo)...")

    resultado = procesar_solicitud(solicitud)

    print(f"\nListo. Salida en: {resultado['directorio']}")
    for fmt, path in resultado.get("archivos", {}).items():
        print(f"  {fmt.upper()}: {path}")

    if resultado.get("correlacion_destacada") is not None:
        print(f"\nCorrelación exclusión digital ↔ movilidad proxy: {resultado['correlacion_destacada']:.3f}")

    shap = resultado.get("modelos", {}).get("shap", {})
    if shap.get("peso_relativo_pct"):
        print("\nTop variables SHAP:")
        for k, v in list(shap["peso_relativo_pct"].items())[:5]:
            print(f"  {k}: {v}%")


if __name__ == "__main__":
    main()
