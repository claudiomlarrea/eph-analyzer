"""
Interpretabilidad con SHAP (SHapley Additive exPlanations).

Basado en la teoría de juegos de Shapley: descompone cada predicción
en la contribución aditiva de cada feature.

Funciones:
    - `explicar_modelo`: calcula SHAP values sobre una muestra y devuelve
      un objeto con summary, importancia global y por instancia.
    - `summary_plot_objeto`: genera la figura matplotlib del summary plot.
    - `dependence_plot_objeto`: figura matplotlib de dependence plot.
    - `waterfall_plot_objeto`: figura para una observación específica.

Selección de explainer:
    - TreeExplainer para Random Forest, gradient boosting, decision trees.
    - LinearExplainer para Logistic Regression / Linear SVM.
    - KernelExplainer como fallback genérico (más lento).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap


@dataclass
class ResultadoSHAP:
    shap_values: np.ndarray | shap.Explanation
    explainer: Any
    importancias_globales: pd.DataFrame
    X_muestra: pd.DataFrame
    n_muestra: int


def explicar_modelo(
    modelo,
    X: pd.DataFrame,
    n_muestra: int = 500,
    background: pd.DataFrame | None = None,
    background_size: int = 100,
    random_state: int = 42,
) -> ResultadoSHAP:
    """
    Calcula valores SHAP para una muestra de X.

    Parámetros
    ----------
    modelo : modelo entrenado (sklearn-compatible)
    X : DataFrame con las features (codificadas como en entrenamiento)
    n_muestra : int
        Cuántas filas explicar. SHAP es lento; 500-1000 alcanza para
        dependence plots y summary plots representativos.
    background : DataFrame, opcional
        Datos de fondo. Si None, se sub-muestrean de X. Solo aplica a
        explainers que lo necesitan (KernelExplainer, LinearExplainer).
    """
    rng = np.random.default_rng(random_state)
    if len(X) > n_muestra:
        idx = rng.choice(len(X), size=n_muestra, replace=False)
        X_muestra = X.iloc[idx].reset_index(drop=True)
    else:
        X_muestra = X.reset_index(drop=True)

    explainer = _seleccionar_explainer(
        modelo, background or X, background_size, random_state
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            shap_values = explainer(X_muestra, check_additivity=False)
        except TypeError:
            shap_values = explainer(X_muestra)

    if isinstance(shap_values, shap.Explanation):
        valores_array = shap_values.values
        if valores_array.ndim == 3:
            valores_array = valores_array[..., 1]
    else:
        valores_array = (
            shap_values[1] if isinstance(shap_values, list) else shap_values
        )

    importancias = (
        pd.DataFrame({
            "variable": X_muestra.columns,
            "shap_mean_abs": np.abs(valores_array).mean(axis=0).round(4),
        })
        .sort_values("shap_mean_abs", ascending=False)
        .reset_index(drop=True)
    )

    return ResultadoSHAP(
        shap_values=shap_values,
        explainer=explainer,
        importancias_globales=importancias,
        X_muestra=X_muestra,
        n_muestra=len(X_muestra),
    )


def _seleccionar_explainer(
    modelo,
    background: pd.DataFrame,
    background_size: int,
    random_state: int,
):
    """Elige el explainer más eficiente según el tipo de modelo."""
    nombre = type(modelo).__name__.lower()
    bg = (
        background.sample(min(background_size, len(background)), random_state=random_state)
        if isinstance(background, pd.DataFrame)
        else background
    )

    if any(k in nombre for k in ("forest", "tree", "boost", "gbm", "xgb", "lgbm", "catboost")):
        return shap.TreeExplainer(modelo, feature_perturbation="tree_path_dependent")
    if "logistic" in nombre or "linearclassifier" in nombre or nombre == "linearregression":
        try:
            return shap.LinearExplainer(modelo, bg)
        except Exception:
            pass
    return shap.Explainer(modelo.predict_proba, bg)


def summary_plot_objeto(resultado: ResultadoSHAP, max_features: int = 15) -> plt.Figure:
    """Genera summary plot (beeswarm) y devuelve la figura."""
    plt.close("all")
    fig = plt.figure(figsize=(10, 6))
    shap.summary_plot(
        resultado.shap_values,
        resultado.X_muestra,
        max_display=max_features,
        show=False,
    )
    fig.tight_layout()
    return fig


def importance_bar_objeto(resultado: ResultadoSHAP, max_features: int = 15) -> plt.Figure:
    """Bar plot de importancias globales SHAP (mean |SHAP|)."""
    top = resultado.importancias_globales.head(max_features).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, max(4, len(top) * 0.35)))
    ax.barh(top["variable"], top["shap_mean_abs"], color="#1f4e79")
    ax.set_xlabel("Importancia SHAP (mean |SHAP|)")
    ax.set_title("Importancia global de variables — SHAP")
    fig.tight_layout()
    return fig


def dependence_plot_objeto(
    resultado: ResultadoSHAP,
    variable: str,
    interaccion: str | None = "auto",
) -> plt.Figure:
    """Dependence plot para una variable."""
    plt.close("all")
    fig = plt.figure(figsize=(8, 5))
    shap.dependence_plot(
        variable,
        (
            resultado.shap_values.values
            if isinstance(resultado.shap_values, shap.Explanation)
            else resultado.shap_values
        ),
        resultado.X_muestra,
        interaction_index=interaccion,
        show=False,
    )
    fig.tight_layout()
    return fig


def waterfall_plot_objeto(resultado: ResultadoSHAP, indice_fila: int = 0) -> plt.Figure:
    """Waterfall plot para una observación particular."""
    plt.close("all")
    fig = plt.figure(figsize=(9, 6))
    if isinstance(resultado.shap_values, shap.Explanation):
        sv = resultado.shap_values[indice_fila]
        if sv.values.ndim == 2:
            sv = shap.Explanation(
                values=sv.values[:, 1],
                base_values=sv.base_values[1] if hasattr(sv.base_values, "__len__") else sv.base_values,
                data=sv.data,
                feature_names=sv.feature_names,
            )
        shap.plots.waterfall(sv, show=False)
    fig.tight_layout()
    return fig
