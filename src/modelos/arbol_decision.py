"""
Árbol de decisión clasificador.

Devuelve el modelo entrenado, métricas, importancia de variables y
una representación textual del árbol (útil para mostrar en Streamlit
sin depender de graphviz).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier, export_text

from src.modelos._prep import DatosPreparados, preparar_datos


@dataclass
class ResultadoArbol:
    modelo: DecisionTreeClassifier
    importancias: pd.DataFrame
    metricas: dict
    arbol_texto: str
    datos: DatosPreparados


def correr_arbol(
    df: pd.DataFrame,
    target: str | pd.Series,
    features: list[str],
    max_depth: int = 5,
    min_samples_leaf: int = 50,
    test_size: float = 0.2,
    random_state: int = 42,
    ponderador: str | None = "PONDERA",
) -> ResultadoArbol:
    """Entrena un árbol de decisión y devuelve métricas + estructura."""
    datos = preparar_datos(
        df, target, features,
        test_size=test_size,
        random_state=random_state,
        escalar=False,
        ponderador=ponderador,
    )

    modelo = DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        criterion="gini",
        random_state=random_state,
    )
    modelo.fit(
        datos.X_train,
        datos.y_train,
        sample_weight=datos.sample_weight_train,
    )

    y_pred = modelo.predict(datos.X_test)
    y_proba = modelo.predict_proba(datos.X_test)[:, 1]

    importancias = (
        pd.DataFrame({
            "variable": datos.nombres_features,
            "importancia": modelo.feature_importances_.round(4),
        })
        .sort_values("importancia", ascending=False)
        .reset_index(drop=True)
    )

    try:
        auc = float(roc_auc_score(datos.y_test, y_proba))
    except ValueError:
        auc = float("nan")

    arbol_str = export_text(
        modelo,
        feature_names=list(datos.X_train.columns),
        max_depth=max_depth,
    )

    metricas = {
        "n_train": datos.info["n_train"],
        "n_test": datos.info["n_test"],
        "max_depth": max_depth,
        "min_samples_leaf": min_samples_leaf,
        "accuracy_test": round(float(accuracy_score(datos.y_test, y_pred)), 4),
        "auc_roc_test": round(auc, 4) if not np.isnan(auc) else None,
        "n_hojas": int(modelo.get_n_leaves()),
        "profundidad_real": int(modelo.get_depth()),
    }

    return ResultadoArbol(
        modelo=modelo,
        importancias=importancias,
        metricas=metricas,
        arbol_texto=arbol_str,
        datos=datos,
    )
