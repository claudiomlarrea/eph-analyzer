"""
Clústeres y segmentación de hogares / individuos.

Implementa:
    - **K-means** con elección automática del k óptimo (silueta).
    - **Aglomerativo jerárquico** (vínculo Ward) sobre una submuestra.
    - **Perfilamiento de clústeres**: media de cada variable por grupo.

Para clusterizar, todas las features deben estar codificadas y escaladas
(usamos la pipeline de _prep, sin target).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.modelos._prep import inferir_tipo_columnas


@dataclass
class ResultadoClusters:
    metodo: str
    k: int
    etiquetas: np.ndarray
    silhouette: float
    perfil: pd.DataFrame              # media de cada feature por clúster
    distribucion: pd.DataFrame        # n y % por clúster
    metricas_por_k: pd.DataFrame      # SSE y silueta para cada k probado
    feature_names: list[str]


def preparar_features_cluster(
    df: pd.DataFrame,
    features: Iterable[str],
    max_categorias: int = 20,
) -> tuple[pd.DataFrame, list[str]]:
    """Prepara la matriz X (numérica, imputada y escalada) para clustering."""
    features = [f for f in features if f in df.columns]
    if not features:
        raise ValueError("No hay features válidas en el DataFrame.")

    numericas, categoricas = inferir_tipo_columnas(df, features)

    cat_seguras = [
        c for c in categoricas
        if 1 < df[c].nunique(dropna=True) <= max_categorias
    ]

    X_num = df[numericas].apply(pd.to_numeric, errors="coerce")
    if numericas:
        X_num = pd.DataFrame(
            SimpleImputer(strategy="median").fit_transform(X_num),
            columns=numericas,
            index=df.index,
        )
    if cat_seguras:
        X_cat = pd.get_dummies(
            df[cat_seguras].astype("string"),
            drop_first=True,
            dummy_na=False,
            dtype=float,
        )
    else:
        X_cat = pd.DataFrame(index=df.index)

    X = pd.concat([X_num, X_cat], axis=1).fillna(0.0)
    X_scaled = pd.DataFrame(
        StandardScaler().fit_transform(X),
        columns=X.columns,
        index=X.index,
    )
    return X_scaled, list(X.columns)


def kmeans_cluster(
    df: pd.DataFrame,
    features: Iterable[str],
    k_min: int = 2,
    k_max: int = 8,
    k_objetivo: int | None = None,
    random_state: int = 42,
    muestra_silueta: int = 5000,
) -> ResultadoClusters:
    """
    K-means con elección automática del k óptimo.

    Si `k_objetivo` está dado, lo usa directamente. Si no, prueba k de
    `k_min` a `k_max` y elige el k con mejor silueta.
    """
    X, feature_names = preparar_features_cluster(df, features)

    rng = np.random.default_rng(random_state)
    if len(X) > muestra_silueta:
        idx_sil = rng.choice(len(X), size=muestra_silueta, replace=False)
    else:
        idx_sil = np.arange(len(X))

    metricas = []
    if k_objetivo is None:
        for k in range(k_min, k_max + 1):
            km = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit(X)
            sil = silhouette_score(
                X.iloc[idx_sil],
                km.labels_[idx_sil],
                random_state=random_state,
            )
            metricas.append({
                "k": k,
                "sse": round(float(km.inertia_), 2),
                "silhouette": round(float(sil), 4),
            })
        metricas_df = pd.DataFrame(metricas)
        k_optimo = int(metricas_df.loc[metricas_df["silhouette"].idxmax(), "k"])
    else:
        k_optimo = k_objetivo
        metricas_df = pd.DataFrame()

    modelo_final = KMeans(
        n_clusters=k_optimo, random_state=random_state, n_init=10
    ).fit(X)
    etiquetas = modelo_final.labels_
    sil_final = silhouette_score(
        X.iloc[idx_sil],
        etiquetas[idx_sil],
        random_state=random_state,
    )

    perfil = _perfil_clusters(df, etiquetas, features)
    distribucion = _distribucion_clusters(etiquetas)

    return ResultadoClusters(
        metodo="kmeans",
        k=int(k_optimo),
        etiquetas=etiquetas,
        silhouette=round(float(sil_final), 4),
        perfil=perfil,
        distribucion=distribucion,
        metricas_por_k=metricas_df,
        feature_names=feature_names,
    )


def jerarquico_cluster(
    df: pd.DataFrame,
    features: Iterable[str],
    k: int = 4,
    submuestra: int = 5000,
    random_state: int = 42,
    linkage: str = "ward",
) -> ResultadoClusters:
    """
    Clustering jerárquico (Ward) sobre una submuestra.

    Es O(n²) en memoria, así que se trabaja con submuestra cuando la base
    es grande.
    """
    X, feature_names = preparar_features_cluster(df, features)

    rng = np.random.default_rng(random_state)
    if len(X) > submuestra:
        idx = rng.choice(len(X), size=submuestra, replace=False)
        X_sub = X.iloc[idx]
        df_sub = df.iloc[idx]
    else:
        X_sub = X
        df_sub = df

    modelo = AgglomerativeClustering(n_clusters=k, linkage=linkage)
    etiquetas = modelo.fit_predict(X_sub)

    sil = silhouette_score(X_sub, etiquetas, random_state=random_state)

    perfil = _perfil_clusters(df_sub, etiquetas, features)
    distribucion = _distribucion_clusters(etiquetas)

    return ResultadoClusters(
        metodo="jerarquico",
        k=int(k),
        etiquetas=etiquetas,
        silhouette=round(float(sil), 4),
        perfil=perfil,
        distribucion=distribucion,
        metricas_por_k=pd.DataFrame(),
        feature_names=feature_names,
    )


def _perfil_clusters(
    df: pd.DataFrame,
    etiquetas: np.ndarray,
    features: Iterable[str],
) -> pd.DataFrame:
    """Genera tabla con la media de cada feature por clúster."""
    df = df.copy()
    df = df.iloc[: len(etiquetas)]
    df["_cluster"] = etiquetas

    cols_num = [
        c for c in features
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not cols_num:
        return pd.DataFrame()

    perfil = (
        df.groupby("_cluster")[cols_num]
        .mean()
        .round(3)
        .T
        .rename_axis("variable")
        .reset_index()
    )
    perfil.columns = ["variable"] + [f"C{c}" for c in perfil.columns[1:]]
    return perfil


def _distribucion_clusters(etiquetas: np.ndarray) -> pd.DataFrame:
    s = pd.Series(etiquetas, name="cluster")
    n = s.value_counts().sort_index()
    pct = (n / n.sum() * 100).round(2)
    return pd.DataFrame({
        "cluster": [f"C{c}" for c in n.index],
        "n": n.values,
        "%": pct.values,
    })
