"""
Regresión logística (binaria) con dos engines:

    1. **statsmodels** — para inferencia: odds ratios, p-valores, IC95,
       pseudo-R² de McFadden, deviance, log-verosimilitud.
    2. **scikit-learn** — para predicción y métricas: accuracy, AUC-ROC,
       matriz de confusión.

Devuelve un dataclass con todo el reporte estructurado.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

from src.modelos._prep import DatosPreparados, preparar_datos


@dataclass
class ResultadoLogistica:
    coeficientes: pd.DataFrame      # variable, coef, OR, IC95_inf, IC95_sup, p_valor
    metricas: dict                  # accuracy, auc, n_train, n_test, balance, etc.
    matriz_confusion: pd.DataFrame
    roc: dict                       # fpr, tpr, thresholds (para graficar)
    modelo_sklearn: LogisticRegression
    modelo_statsmodels: object | None
    datos: DatosPreparados


def correr_logistica(
    df: pd.DataFrame,
    target: str | pd.Series,
    features: list[str],
    test_size: float = 0.2,
    random_state: int = 42,
    max_iter: int = 1000,
    ponderador: str | None = "PONDERA",
    escalar: bool = False,
) -> ResultadoLogistica:
    """
    Ajusta una regresión logística y devuelve métricas + inferencia.

    Nota
    ----
    Por default `escalar=False` para que los odds ratios sean interpretables
    en unidades originales (un año más de edad, un peso más de ingreso, etc.),
    igual que en literatura aplicada y tesis de ciencias sociales.
    Activar `escalar=True` solo si hay problemas de convergencia.
    """
    datos = preparar_datos(
        df, target, features,
        test_size=test_size,
        random_state=random_state,
        escalar=escalar,
        ponderador=ponderador,
    )

    modelo_sk = LogisticRegression(
        max_iter=max_iter,
        solver="lbfgs",
        random_state=random_state,
    )
    modelo_sk.fit(
        datos.X_train,
        datos.y_train,
        sample_weight=datos.sample_weight_train,
    )

    y_pred = modelo_sk.predict(datos.X_test)
    y_proba = modelo_sk.predict_proba(datos.X_test)[:, 1]

    cm = confusion_matrix(datos.y_test, y_pred)
    cm_df = pd.DataFrame(
        cm,
        index=["real_0", "real_1"],
        columns=["pred_0", "pred_1"],
    )

    try:
        auc = roc_auc_score(datos.y_test, y_proba)
        fpr, tpr, thr = roc_curve(datos.y_test, y_proba)
        roc_dict = {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thr.tolist(),
        }
    except ValueError:
        auc = float("nan")
        roc_dict = {"fpr": [], "tpr": [], "thresholds": []}

    coef_df, modelo_sm = _ajustar_statsmodels(datos)

    metricas = {
        "n_train": datos.info["n_train"],
        "n_test": datos.info["n_test"],
        "n_features": datos.info["n_features_finales"],
        "balance_target": datos.info["balance_target"],
        "accuracy_test": round(float(accuracy_score(datos.y_test, y_pred)), 4),
        "auc_roc_test": round(float(auc), 4) if not np.isnan(auc) else None,
        "classification_report": classification_report(
            datos.y_test, y_pred, output_dict=True, zero_division=0
        ),
    }
    if modelo_sm is not None:
        metricas["pseudo_r2_mcfadden"] = round(float(modelo_sm.prsquared), 4)
        metricas["log_likelihood"] = round(float(modelo_sm.llf), 2)
        metricas["aic"] = round(float(modelo_sm.aic), 2)
        metricas["bic"] = round(float(modelo_sm.bic), 2)

    return ResultadoLogistica(
        coeficientes=coef_df,
        metricas=metricas,
        matriz_confusion=cm_df,
        roc=roc_dict,
        modelo_sklearn=modelo_sk,
        modelo_statsmodels=modelo_sm,
        datos=datos,
    )


def _ajustar_statsmodels(datos: DatosPreparados) -> tuple[pd.DataFrame, object | None]:
    """Ajusta con statsmodels para extraer OR, IC95, p-valores."""
    X = sm.add_constant(datos.X_train.astype(float), has_constant="add")
    y = datos.y_train.astype(float)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            modelo = sm.Logit(y, X).fit(disp=False, maxiter=200)
    except Exception as e:
        return pd.DataFrame(
            columns=["variable", "coef", "OR", "IC95_inf", "IC95_sup", "p_valor"]
        ), None

    params = modelo.params
    conf = modelo.conf_int(alpha=0.05)
    conf.columns = ["IC95_inf", "IC95_sup"]
    pvals = modelo.pvalues

    coef_df = pd.DataFrame({
        "variable": params.index,
        "coef": params.values.round(4),
        "OR": np.exp(params.values).round(4),
        "IC95_inf_OR": np.exp(conf["IC95_inf"]).round(4).values,
        "IC95_sup_OR": np.exp(conf["IC95_sup"]).round(4).values,
        "p_valor": pvals.values.round(4),
    })
    coef_df["significativa_05"] = coef_df["p_valor"] < 0.05
    coef_df = coef_df.sort_values("p_valor").reset_index(drop=True)

    return coef_df, modelo
