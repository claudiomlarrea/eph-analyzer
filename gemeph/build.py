#!/usr/bin/env python3
"""CLI: construir panel y catálogo GEMEPH para todos los aglomerados."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemeph.catalog import persist_gemeph_run
from gemeph.panel import load_or_build_panel, periodo_texto


def main() -> None:
    p = argparse.ArgumentParser(description="Construir GEMEPH (nacional + 31 aglomerados)")
    p.add_argument("--years", default="2017-2024", help="Año único o rango, ej. 2022 o 2017-2024")
    p.add_argument("--trimestre", type=int, default=4)
    p.add_argument("--modulo", choices=["tic", "base"], default="tic")
    p.add_argument("--force", action="store_true", help="Forzar nueva descarga INDEC")
    args = p.parse_args()

    if "-" in args.years:
        y0, y1 = map(int, args.years.split("-", 1))
        years = list(range(y0, y1 + 1))
    else:
        years = [int(args.years)]

    panel, val, run_id = load_or_build_panel(
        years,
        args.trimestre,
        modulo=args.modulo,
        force_download=args.force,
    )
    periodo = periodo_texto(years, args.trimestre)
    meta = persist_gemeph_run(panel, run_id=run_id, periodo=periodo, modulo=args.modulo)
    print(f"GEMEPH listo: run_id={run_id}")
    print(f"Registros panel: {val.get('filas', len(panel)):,}")
    print(f"Territorios en catálogo: {meta['catalog']['n_territorios']}")


if __name__ == "__main__":
    main()
