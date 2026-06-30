"""Estado territorial del gemelo (baseline JSON)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from indec_auto.src.analyze import clustering_kmeans

from .config import BASELINE_DIR
from .kpis import compute_evolution, compute_kpis
from .territories import filter_territory, list_territories, territory_label


def build_baseline(
    panel: pd.DataFrame,
    territory_id: str,
    *,
    periodo: str,
    modulo: str = "tic",
    include_clusters: bool = True,
) -> dict[str, Any]:
    """Construye baseline de un territorio a partir del panel maestro."""
    include_tic = modulo == "tic"
    sub = filter_territory(panel, territory_id)
    codigo = next((t["codigo"] for t in list_territories() if t["id"] == territory_id), None)

    baseline: dict[str, Any] = {
        "territorio_id": territory_id,
        "territorio_nombre": territory_label(territory_id),
        "aglomerado_codigo": codigo,
        "periodo": periodo,
        "modulo": modulo,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "fuente": "INDEC — EPH (hogar + individuo)",
        "kpis": compute_kpis(sub, include_tic=include_tic),
        "evolucion": compute_evolution(sub, include_tic=include_tic),
    }

    if include_clusters and include_tic and len(sub) >= 200:
        cl = clustering_kmeans(sub, k=4)
        if "error" not in cl:
            nombres = cl.get("nombres_clusters", {})
            tam = cl.get("tamano_cluster_pct", {})
            baseline["perfiles"] = [
                {
                    "cluster": int(cid),
                    "nombre": nombres.get(cid, nombres.get(str(cid), f"Perfil {cid}")),
                    "pct": tam.get(cid, tam.get(str(cid))),
                }
                for cid in sorted(tam.keys(), key=lambda x: int(x))
            ]

    return baseline


def save_baseline(baseline: dict[str, Any], run_id: str) -> Path:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    tid = baseline["territorio_id"]
    path = BASELINE_DIR / run_id / f"{tid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_baseline(run_id: str, territory_id: str) -> dict[str, Any] | None:
    path = BASELINE_DIR / run_id / f"{territory_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_baselines_all(
    panel: pd.DataFrame,
    *,
    periodo: str,
    modulo: str = "tic",
    include_clusters: bool = False,
) -> dict[str, dict[str, Any]]:
    """Genera baseline para nacional + 31 aglomerados."""
    out: dict[str, dict[str, Any]] = {}
    for t in list_territories():
        out[t["id"]] = build_baseline(
            panel,
            t["id"],
            periodo=periodo,
            modulo=modulo,
            include_clusters=include_clusters,
        )
    return out
