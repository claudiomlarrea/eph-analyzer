"""Catálogo comparativo de los 31 aglomerados + nacional."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .baseline import build_baselines_all, save_baseline
from .config import CATALOG_DIR
from .kpis import compute_kpis
from .territories import filter_territory, list_territories, territory_label


def build_catalog(
    panel: pd.DataFrame,
    *,
    periodo: str,
    modulo: str = "tic",
) -> dict[str, Any]:
    """Índice liviano: KPIs de todos los territorios sin clústeres."""
    include_tic = modulo == "tic"
    filas = []
    for t in list_territories():
        sub = filter_territory(panel, t["id"])
        kpis = compute_kpis(sub, include_tic=include_tic)
        filas.append(
            {
                "territorio_id": t["id"],
                "territorio_nombre": t["nombre"],
                "aglomerado_codigo": t["codigo"],
                "tipo": t["tipo"],
                **{k: v for k, v in kpis.items() if k != "brechas"},
                **(kpis.get("brechas") or {}),
            }
        )

    return {
        "periodo": periodo,
        "modulo": modulo,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "n_territorios": len(filas),
        "territorios": filas,
    }


def catalog_to_dataframe(catalog: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(catalog.get("territorios", []))


def save_catalog(catalog: dict[str, Any], run_id: str) -> Path:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    path = CATALOG_DIR / f"{run_id}.json"
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_catalog(run_id: str) -> dict[str, Any] | None:
    path = CATALOG_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def persist_gemeph_run(
    panel: pd.DataFrame,
    *,
    run_id: str,
    periodo: str,
    modulo: str = "tic",
    save_panel_parquet: bool = True,
) -> dict[str, Any]:
    """Guarda panel, catálogo y baselines completos de una corrida."""
    from .panel import save_panel

    if save_panel_parquet:
        save_panel(panel, run_id)

    catalog = build_catalog(panel, periodo=periodo, modulo=modulo)
    save_catalog(catalog, run_id)

    baselines = build_baselines_all(panel, periodo=periodo, modulo=modulo, include_clusters=False)
    for tid, bl in baselines.items():
        save_baseline(bl, run_id)

    # Perfil detallado con clústeres solo para nacional (evita tiempo excesivo)
    from .baseline import build_baseline

    bl_nacional = build_baseline(panel, "nacional", periodo=periodo, modulo=modulo, include_clusters=True)
    save_baseline(bl_nacional, run_id)

    return {"run_id": run_id, "catalog": catalog, "n_baselines": len(baselines)}
