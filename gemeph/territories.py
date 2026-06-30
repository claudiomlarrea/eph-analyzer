"""Territorios GEMEPH: nacional + 31 aglomerados urbanos EPH."""

from __future__ import annotations

import pandas as pd

from indec_auto.src.aglomerados import AGLOMERADOS_EPH, nombre_aglomerado


def list_territories() -> list[dict]:
    """Lista nacional + los 31 aglomerados ordenados alfabéticamente."""
    items = [
        {
            "id": "nacional",
            "codigo": None,
            "nombre": "Argentina (31 aglomerados urbanos)",
            "tipo": "nacional",
        }
    ]
    for codigo in sorted(AGLOMERADOS_EPH):
        items.append(
            {
                "id": f"aglomerado_{codigo}",
                "codigo": codigo,
                "nombre": AGLOMERADOS_EPH[codigo],
                "tipo": "aglomerado",
            }
        )
    return items


def territory_label(territory_id: str) -> str:
    for t in list_territories():
        if t["id"] == territory_id:
            return t["nombre"]
    if territory_id.startswith("aglomerado_"):
        try:
            cod = int(territory_id.split("_", 1)[1])
            return nombre_aglomerado(cod)
        except ValueError:
            pass
    return territory_id


def territory_codigo(territory_id: str) -> int | None:
    for t in list_territories():
        if t["id"] == territory_id:
            return t["codigo"]
    return None


def filter_territory(df: pd.DataFrame, territory_id: str) -> pd.DataFrame:
    """Filtra el panel maestro al territorio solicitado."""
    if territory_id == "nacional" or not territory_id.startswith("aglomerado_"):
        return df.copy()
    cod = territory_codigo(territory_id)
    if cod is None or "AGLOMERADO" not in df.columns:
        return df.iloc[0:0].copy()
    aglo = pd.to_numeric(df["AGLOMERADO"], errors="coerce")
    return df.loc[aglo == cod].copy()
