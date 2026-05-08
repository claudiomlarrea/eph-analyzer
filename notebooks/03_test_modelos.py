"""
Test del Bloque B — Modelos inferenciales y predictivos.

Como la base 1°T 2017 no tiene módulo TIC (no podemos modelar exclusión
digital "real"), corremos todos los modelos contra un outcome alternativo
sólido: estar OCUPADO en la población de 18-65 años. Eso ejercita
exactamente el mismo flujo que después se usará para exclusión digital.

Outcome:    OCUPADO (binario 0/1)
Features:   CH06 (edad), CH04 (sexo), NIVEL_ED, REGION, IPCF, ITF, IX_TOT

Ejecutar:
    .venv/bin/python notebooks/03_test_modelos.py
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from src.modelos.arbol_decision import correr_arbol
from src.modelos.clusters import jerarquico_cluster, kmeans_cluster
from src.modelos.logistica import correr_logistica
from src.modelos.random_forest import correr_random_forest
from src.modelos.shap_xai import explicar_modelo
from src.parquet_store import cargar_parquet


def encabezado(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    print("Cargando Parquet...")
    df = cargar_parquet("eph_2017_t1")
    print(f"  → {df.shape[0]:,} filas × {df.shape[1]:,} columnas")

    df = df[(df["CH06"] >= 18) & (df["CH06"] <= 65)].copy()
    df = df[df["ESTADO"].isin([1, 2])].copy()
    print(
        f"  → Filtrado a 18-65 años, ocupados/desocupados: "
        f"{df.shape[0]:,} filas"
    )
    print(f"  → Distribución del target OCUPADO:")
    print(df["OCUPADO"].value_counts(normalize=True).round(3).to_string())

    FEATURES = ["CH06", "CH04", "NIVEL_ED", "REGION", "IPCF", "IX_TOT"]
    TARGET = "OCUPADO"

    encabezado("1) REGRESIÓN LOGÍSTICA")
    t0 = time.time()
    res_log = correr_logistica(df, TARGET, FEATURES)
    print(f"  ✓ Entrenada en {time.time() - t0:.1f}s")
    print(f"\n  Métricas:")
    for k, v in res_log.metricas.items():
        if k != "classification_report" and k != "balance_target":
            print(f"    {k:25s} = {v}")

    print(f"\n  Top 8 coeficientes (por p-valor):")
    cols_show = ["variable", "coef", "OR", "IC95_inf_OR", "IC95_sup_OR", "p_valor", "significativa_05"]
    print(res_log.coeficientes[cols_show].head(8).to_string(index=False))

    print(f"\n  Matriz de confusión (test):")
    print(res_log.matriz_confusion.to_string())

    encabezado("2) ÁRBOL DE DECISIÓN")
    t0 = time.time()
    res_arb = correr_arbol(df, TARGET, FEATURES, max_depth=4, min_samples_leaf=200)
    print(f"  ✓ Entrenado en {time.time() - t0:.1f}s")
    for k, v in res_arb.metricas.items():
        print(f"    {k:25s} = {v}")
    print(f"\n  Importancias:")
    print(res_arb.importancias.head(8).to_string(index=False))
    print(f"\n  Reglas del árbol (primeros niveles):")
    print("\n".join(res_arb.arbol_texto.split("\n")[:25]))

    encabezado("3) RANDOM FOREST (500 árboles)")
    t0 = time.time()
    res_rf = correr_random_forest(df, TARGET, FEATURES, n_estimators=500)
    print(f"  ✓ Entrenado en {time.time() - t0:.1f}s")
    for k, v in res_rf.metricas.items():
        if k != "classification_report" and k != "balance_target":
            print(f"    {k:25s} = {v}")
    print(f"\n  Importancias:")
    print(res_rf.importancias.head(8).to_string(index=False))

    encabezado("4) SHAP — Interpretabilidad del Random Forest")
    t0 = time.time()
    print("  (calculando sobre 500 filas...)")
    res_shap = explicar_modelo(
        modelo=res_rf.modelo,
        X=res_rf.datos.X_test,
        n_muestra=500,
    )
    print(f"  ✓ SHAP values calculados en {time.time() - t0:.1f}s "
          f"(n={res_shap.n_muestra})")
    print(f"\n  Top 10 importancias SHAP (mean |SHAP|):")
    print(res_shap.importancias_globales.head(10).to_string(index=False))

    encabezado("5) CLUSTERING — K-means")
    cluster_features = ["CH06", "NIVEL_ED", "IPCF", "IX_TOT", "OCUPADO"]
    t0 = time.time()
    res_km = kmeans_cluster(
        df.sample(20_000, random_state=42),
        cluster_features,
        k_min=2, k_max=6,
    )
    print(f"  ✓ K-means en {time.time() - t0:.1f}s · k óptimo = {res_km.k} · "
          f"silueta = {res_km.silhouette}")
    print(f"\n  Métricas por k:")
    print(res_km.metricas_por_k.to_string(index=False))
    print(f"\n  Distribución por clúster:")
    print(res_km.distribucion.to_string(index=False))
    print(f"\n  Perfil (medias) por clúster:")
    print(res_km.perfil.to_string(index=False))

    encabezado("6) CLUSTERING — Jerárquico (Ward, k=4, submuestra 5k)")
    t0 = time.time()
    res_h = jerarquico_cluster(df, cluster_features, k=4, submuestra=5000)
    print(f"  ✓ Jerárquico en {time.time() - t0:.1f}s · silueta = {res_h.silhouette}")
    print(f"\n  Distribución por clúster:")
    print(res_h.distribucion.to_string(index=False))
    print(f"\n  Perfil:")
    print(res_h.perfil.to_string(index=False))


if __name__ == "__main__":
    main()
