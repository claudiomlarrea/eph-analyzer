"""
Utilidades compartidas para el preprocesamiento previo al modelado.

Funciones:
    - `preparar_datos`: arma X / y, hace split train/test, codifica categóricas,
      imputa nulos, escala si se pide.
    - `construir_target_binario`: ayuda a construir un target binario a
      partir del índice de exclusión digital o cualquier columna numérica.
    - `inferir_tipo_columnas`: separa columnas numéricas vs categóricas.

Notas:
    - Pondera por defecto con `PONDERA` cuando está disponible (los modelos
      de scikit-learn aceptan `sample_weight`).
    - Si una variable es nominal, se hace one-hot. Si es ordinal numérica
      (ya codificada), se deja como está.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PONDERADOR_DEFAULT = "PONDERA"

CATEGORICAS_NOMINALES_HABITUALES = {
    "REGION", "AGLOMERADO", "CH04", "CH07", "CH08", "CH15",
    "CAT_OCUP", "CAT_INAC", "II7", "IV1", "GRUPO_ETARIO",
    "QUINTIL_IPCF",
}

ORDINALES_DEJAR_COMO_ESTAN = {
    "NIVEL_ED", "CH12", "CH13", "DECCFR", "DECIFR",
}


@dataclass
class DatosPreparados:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    sample_weight_train: np.ndarray | None
    sample_weight_test: np.ndarray | None
    nombres_features: list[str]
    columnas_originales: list[str]
    info: dict


def construir_target_binario(
    df: pd.DataFrame,
    columna: str,
    umbral: float | None = None,
    valores_positivos: Iterable | None = None,
) -> pd.Series:
    """
    Construye un target binario (0/1) desde una columna.

    Parámetros
    ----------
    columna : str
        Nombre de la columna a binarizar.
    umbral : float, opcional
        Si se da, se asigna 1 a valores >= umbral (numérico).
    valores_positivos : iterable, opcional
        Si se da, se asigna 1 a las filas cuyo valor está en este conjunto.

    Si la columna ya es 0/1 (o booleana), se devuelve tal cual.
    """
    if columna not in df.columns:
        raise KeyError(f"Columna '{columna}' no encontrada.")

    s = df[columna]

    if s.dtype == bool:
        return s.astype(int)

    valores_unicos = pd.unique(s.dropna())
    if set(map(_to_num, valores_unicos)).issubset({0, 1}):
        return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

    if valores_positivos is not None:
        return s.isin(list(valores_positivos)).astype(int)

    if umbral is not None:
        s_num = pd.to_numeric(s, errors="coerce")
        return (s_num >= umbral).astype(int)

    raise ValueError(
        f"No se pudo binarizar '{columna}'. Especificá `umbral` o `valores_positivos`."
    )


def _to_num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def inferir_tipo_columnas(
    df: pd.DataFrame,
    columnas: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Separa columnas en (numéricas, categóricas a one-hot encodear)."""
    numericas, categoricas = [], []
    for c in columnas:
        if c not in df.columns:
            continue
        if c.upper() in CATEGORICAS_NOMINALES_HABITUALES or c.endswith("_LABEL"):
            categoricas.append(c)
            continue
        if c.upper() in ORDINALES_DEJAR_COMO_ESTAN:
            numericas.append(c)
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            numericas.append(c)
        else:
            categoricas.append(c)
    return numericas, categoricas


def preparar_datos(
    df: pd.DataFrame,
    target: str | pd.Series,
    features: Iterable[str],
    test_size: float = 0.2,
    random_state: int = 42,
    escalar: bool = False,
    estratificar: bool = True,
    ponderador: str | None = PONDERADOR_DEFAULT,
    drop_na_target: bool = True,
    max_categorias_por_var: int = 30,
) -> DatosPreparados:
    """
    Prepara un dataset para modelado.

    Parámetros
    ----------
    df : DataFrame
    target : str o Series
        Nombre de columna o Serie ya construida con la variable dependiente.
    features : Iterable[str]
        Columnas a usar como predictoras. Las categóricas se one-hot encodean.
    test_size : float
        Proporción del test set.
    escalar : bool
        Si True, aplica StandardScaler a las numéricas (usar con logística).
    estratificar : bool
        Estratificar el split por la variable target (recomendado en clasificación).
    ponderador : str | None
        Nombre de la columna con los pesos muestrales.
    """
    if isinstance(target, str):
        if target not in df.columns:
            raise KeyError(f"Target '{target}' no encontrado.")
        y = df[target].copy()
        nombre_target = target
    else:
        y = pd.Series(target, index=df.index)
        nombre_target = getattr(target, "name", "target")

    features = [f for f in features if f in df.columns and f != nombre_target]
    if not features:
        raise ValueError("No hay features válidas en el DataFrame.")

    sample_weight = None
    if ponderador and ponderador in df.columns:
        sample_weight = pd.to_numeric(df[ponderador], errors="coerce").fillna(0).values

    if drop_na_target:
        mask = y.notna()
        df = df.loc[mask]
        y = y.loc[mask]
        if sample_weight is not None:
            sample_weight = sample_weight[mask.values]

    numericas, categoricas = inferir_tipo_columnas(df, features)

    cat_seguras = []
    for c in categoricas:
        n_cat = df[c].nunique(dropna=True)
        if 1 < n_cat <= max_categorias_por_var:
            cat_seguras.append(c)

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

    X = pd.concat([X_num, X_cat], axis=1)

    if escalar and numericas:
        scaler = StandardScaler()
        X[numericas] = scaler.fit_transform(X[numericas])

    estratificacion = y if estratificar and y.nunique() < 50 else None

    if sample_weight is not None:
        X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
            X, y, sample_weight,
            test_size=test_size,
            random_state=random_state,
            stratify=estratificacion,
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=estratificacion,
        )
        w_train = w_test = None

    info = {
        "n_total": int(len(X)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_numericas": len(numericas),
        "n_categoricas_original": len(cat_seguras),
        "n_features_finales": int(X.shape[1]),
        "target": nombre_target,
        "balance_target": y.value_counts(normalize=True).round(3).to_dict(),
    }

    return DatosPreparados(
        X_train=X_train, X_test=X_test,
        y_train=y_train, y_test=y_test,
        sample_weight_train=w_train, sample_weight_test=w_test,
        nombres_features=list(X.columns),
        columnas_originales=list(features),
        info=info,
    )
