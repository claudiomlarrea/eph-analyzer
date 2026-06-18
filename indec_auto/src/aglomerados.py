"""Diccionario de aglomerados urbanos EPH (INDEC / paquete eph)."""

from __future__ import annotations

import pandas as pd

# Fuente: ropensci/eph::diccionario_aglomerados
AGLOMERADOS_EPH: dict[int, str] = {
    2: "Gran La Plata",
    3: "Bahía Blanca - Cerri",
    4: "Gran Rosario",
    5: "Gran Santa Fé",
    6: "Gran Paraná",
    7: "Posadas",
    8: "Gran Resistencia",
    9: "Cdro. Rivadavia - R. Tilly",
    10: "Gran Mendoza",
    12: "Corrientes",
    13: "Gran Córdoba",
    14: "Concordia",
    15: "Formosa",
    17: "Neuquén - Plottier",
    18: "S. del Estero - La Banda",
    19: "Jujuy - Palpalá",
    20: "Río Gallegos",
    22: "Gran Catamarca",
    23: "Salta",
    25: "La Rioja",
    26: "San Luis - El Chorrillo",
    27: "Gran San Juan",
    29: "Gran Tucumán - T. Viejo",
    30: "Santa Rosa - Toay",
    31: "Ushuaia - Río Grande",
    32: "Ciudad de Bs. As.",
    33: "Partidos GBA",
    34: "Mar del Plata - Batán",
    36: "Río Cuarto",
    38: "San Nicolás - Villa Const.",
    91: "Rawson - Trelew",
    93: "Viedma - Carmen de Patagones",
}


def nombre_aglomerado(codigo: int | float | str | None) -> str:
    if codigo is None or (isinstance(codigo, float) and pd.isna(codigo)):
        return "Sin dato"
    try:
        c = int(float(codigo))
    except (TypeError, ValueError):
        return str(codigo)
    return AGLOMERADOS_EPH.get(c, f"Aglomerado {c}")


def opciones_aglomerado_ui() -> list[tuple[int, str]]:
    return sorted(
        ((cod, f"{nom} ({cod})") for cod, nom in AGLOMERADOS_EPH.items()),
        key=lambda x: x[1],
    )
