"""
Random Forest clasificador.

En la tesis de referencia, RF con 500 árboles alcanzó accuracy=82% y
AUC=0.87 sobre exclusión digital. Esta implementación replica esa
configuración como default y devuelve métricas + importancias + un
diagnóstico OOB (out-of-bag).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

from src.modelos._prep import DatosPreparados, preparar_datos


@dataclass
class ResultadoRandomForest:
    modelo: RandomForestClassifier
    importancias: pd.DataFrame
    metricas: dict
    matriz_confusion: pd.DataFrame
    roc: dict
    datos: DatosPreparados


def correr_random_forest(
    df: pd.DataFrame,
    target: str | pd.Series,
    features: list[str],
    n_estimators: int = 500,
    max_depth: int | None = None,
    min_samples_leaf: int = 5,
    test_size: float = 0.2,
    random_state: int = 42,
    n_jobs: int = -1,
    ponderador: str | None = "PONDERA",
) -> ResultadoRandomForest:
    """
    Entrena un Random Forest y devuelve métricas, importancias y ROC.
    """
    datos = preparar_datos(
        df, target, features,
        test_size=test_size,
        random_state=random_state,
        escalar=False,
        ponderador=ponderador,
    )

    modelo = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        oob_score=True,
        n_jobs=n_jobs,
        random_state=random_state,
        class_weight="balanced",
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

    cm = confusion_matrix(datos.y_test, y_pred)
    cm_df = pd.DataFrame(
        cm,
        index=["real_0", "real_1"],
        columns=["pred_0", "pred_1"],
    )

    try:
        auc = float(roc_auc_score(datos.y_test, y_proba))
        fpr, tpr, thr = roc_curve(datos.y_test, y_proba)
        roc_dict = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "thresholds": thr.tolist()}
    except ValueError:
        auc = float("nan")
        roc_dict = {"fpr": [], "tpr": [], "thresholds": []}

    metricas = {
        "n_train": datos.info["n_train"],
        "n_test": datos.info["n_test"],
        "n_features": datos.info["n_features_finales"],
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "balance_target": datos.info["balance_target"],
        "accuracy_test": round(float(accuracy_score(datos.y_test, y_pred)), 4),
        "auc_roc_test": round(auc, 4) if not np.isnan(auc) else None,
        "oob_score": round(float(modelo.oob_score_), 4),
        "classification_report": classification_report(
            datos.y_test, y_pred, output_dict=True, zero_division=0
        ),
    }

    return ResultadoRandomForest(
        modelo=modelo,
        importancias=importancias,
        metricas=metricas,
        matriz_confusion=cm_df,
        roc=roc_dict,
        datos=datos,
    )
