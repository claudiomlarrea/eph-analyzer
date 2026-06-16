"""Análisis estadístico: descriptivos, logística, clústeres y SHAP."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shap
import statsmodels.api as sm
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import OUTPUT_DIR
from .prepare import weighted_mean


FEATURES_MODEL = [
    "edad",
    "sexo_mujer",
    "secundario_completo",
    "superior",
    "ocupado",
    "desocupado",
    "informal_proxy",
    "quintil_bajo",
    "decil_ingreso",
    "excl_sin_pc",
    "excl_sin_internet_hogar",
    "excl_sin_uso_internet",
]

CLUSTER_FEATURES = [
    "idx_exclusion_digital",
    "score_movilidad_proxy",
    "vulnerabilidad_social",
    "secundario_completo",
    "informal_proxy",
    "quintil_bajo",
]


def _ensure_out() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def descriptivos_por_anio(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for anio, g in df.groupby("anio"):
        w = g["PONDERA"]
        rows.append(
            {
                "anio": anio,
                "n": len(g),
                "pct_exclusion_digital_alta": weighted_mean(g["exclusion_digital_alta"], w) * 100,
                "idx_exclusion_digital": weighted_mean(g["idx_exclusion_digital"], w),
                "pct_secundario_completo": weighted_mean(g["secundario_completo"], w) * 100,
                "pct_superior": weighted_mean(g["superior"], w) * 100,
                "pct_ocupado": weighted_mean(g["ocupado"], w) * 100,
                "pct_informal": weighted_mean(
                    g.loc[g["ocupado"] == 1, "informal_proxy"],
                    g.loc[g["ocupado"] == 1, "PONDERA"],
                )
                * 100
                if (g["ocupado"] == 1).any()
                else float("nan"),
                "score_movilidad_proxy": weighted_mean(g["score_movilidad_proxy"], w),
                "itf_mediano_ponderado": weighted_mean(g["ITF"], w),
            }
        )
    return pd.DataFrame(rows)


def frecuencias_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for col in ["region_nombre", "ESTADO", "NIVEL_ED"]:
        if col not in df.columns:
            continue
        vc = df.groupby(col)["PONDERA"].sum()
        vc = (vc / vc.sum() * 100).reset_index()
        vc.columns = ["categoria", "pct_ponderado"]
        vc["variable"] = col
        out.append(vc)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def correlaciones(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "idx_exclusion_digital",
        "score_movilidad_proxy",
        "vulnerabilidad_social",
        "CH12",
        "ITF",
        "decil_ingreso",
    ]
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    pearson = sub.corr(method="pearson")
    kendall = sub.corr(method="kendall")
    out = pearson.stack().reset_index()
    out.columns = ["var1", "var2", "pearson"]
    k = kendall.stack().reset_index()
    k.columns = ["var1", "var2", "kendall"]
    return out.merge(k, on=["var1", "var2"])


def regresion_logistica(df: pd.DataFrame, target: str = "exclusion_digital_alta") -> dict:
    sub = df[FEATURES_MODEL + [target, "PONDERA"]].copy()
    sub = sub.dropna()
    if len(sub) < 500:
        return {"error": "muestra insuficiente", "n": len(sub)}

    y = sub[target].astype(int)
    X = sub[FEATURES_MODEL]
    w = sub["PONDERA"]

    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipe.fit(X, y)
    coefs = dict(zip(FEATURES_MODEL, pipe.named_steps["clf"].coef_[0]))
    pred = pipe.predict(X)
    report = classification_report(y, pred, output_dict=True, zero_division=0)

    # statsmodels con ponderación (muestra)
    Xs = sm.add_constant(pipe.named_steps["imputer"].fit_transform(X))
    try:
        logit = sm.GLM(y, Xs, family=sm.families.Binomial(), freq_weights=w)
        res = logit.fit()
        sm_pvalues = dict(zip(["const"] + FEATURES_MODEL, res.pvalues))
        sm_or = {k: float(np.exp(v)) for k, v in zip(["const"] + FEATURES_MODEL, res.params)}
    except Exception as exc:
        sm_pvalues, sm_or = {}, {}
        report["statsmodels_error"] = str(exc)

    return {
        "n": len(sub),
        "accuracy": report.get("accuracy"),
        "f1_exclusion": report.get("1", {}).get("f1-score"),
        "coeficientes_estandarizados": coefs,
        "odds_ratios_aprox": {k: float(np.exp(v)) for k, v in coefs.items()},
        "p_values": {k: float(v) for k, v in sm_pvalues.items()} if sm_pvalues else {},
        "odds_ratios_glm": sm_or,
    }


def clustering_kmeans(df: pd.DataFrame, k: int = 4) -> dict:
    sub = df[CLUSTER_FEATURES + ["PONDERA"]].dropna()
    if len(sub) < k * 50:
        return {"error": "muestra insuficiente", "n": len(sub)}

    X = sub[CLUSTER_FEATURES].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(Xs)
    sil = float(silhouette_score(Xs, labels))

    prof = sub.copy()
    prof["cluster"] = labels
    centroids = prof.groupby("cluster")[CLUSTER_FEATURES].mean().round(4)

    sizes = prof["cluster"].value_counts(normalize=True).sort_index() * 100
    return {
        "n": len(sub),
        "k": k,
        "silhouette": sil,
        "tamano_cluster_pct": sizes.round(2).to_dict(),
        "perfiles_medios": centroids.to_dict(),
    }


def shap_importance(
    df: pd.DataFrame,
    target: str = "exclusion_digital_alta",
    sample: int = 8000,
    *,
    out_dir: Path | None = None,
    prefix: str = "nacional",
) -> dict:
    sub = df[FEATURES_MODEL + [target]].dropna()
    if len(sub) > sample:
        sub = sub.sample(sample, random_state=42)
    X = sub[FEATURES_MODEL]
    y = sub[target].astype(int)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    Xp = scaler.fit_transform(imputer.fit_transform(X))
    model.fit(Xp, y)

    explainer = shap.LinearExplainer(model, Xp, feature_perturbation="interventional")
    shap_values = explainer.shap_values(Xp)
    if isinstance(shap_values, list):
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

    mean_abs = np.abs(shap_values).mean(axis=0)
    imp = dict(sorted(zip(FEATURES_MODEL, mean_abs), key=lambda x: -x[1]))
    imp_pct = {k: round(v / mean_abs.sum() * 100, 2) for k, v in imp.items()}

    out = out_dir or _ensure_out()
    graf_path = out / f"shap_summary_{prefix}.png"
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, pd.DataFrame(Xp, columns=FEATURES_MODEL), show=False)
    plt.tight_layout()
    plt.savefig(graf_path, dpi=120, bbox_inches="tight")
    plt.close()

    return {
        "importancia_media_absoluta": imp,
        "peso_relativo_pct": imp_pct,
        "n_muestra": len(sub),
        "grafico": str(graf_path),
    }


def logistica_a_tablas(logit: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    coef = _dict_a_df_local(logit.get("coeficientes_estandarizados", {}), "variable", "coeficiente")
    or_df = _dict_a_df_local(logit.get("odds_ratios_glm") or logit.get("odds_ratios_aprox", {}), "variable", "odds_ratio")
    if "p_values" in logit and logit["p_values"]:
        p = _dict_a_df_local(logit["p_values"], "variable", "p_value")
        coef = coef.merge(p, on="variable", how="left")
    return coef, or_df


def _dict_a_df_local(data: dict, col1: str, col2: str) -> pd.DataFrame:
    if not data:
        return pd.DataFrame(columns=[col1, col2])
    return pd.DataFrame(list(data.items()), columns=[col1, col2])


def shap_a_tabla(shap_res: dict) -> pd.DataFrame:
    pct = shap_res.get("peso_relativo_pct", {})
    if not pct:
        return pd.DataFrame()
    return pd.DataFrame(
        [{"variable": k, "peso_relativo_pct": v} for k, v in pct.items()]
    ).sort_values("peso_relativo_pct", ascending=False)


def ejecutar_analisis(
    df: pd.DataFrame,
    tipos: set[str],
    *,
    label: str = "nacional",
    out_dir: Path | None = None,
) -> dict:
    """Ejecuta solo los análisis solicitados y devuelve tablas + modelos."""
    out = out_dir or _ensure_out()
    tablas: dict[str, pd.DataFrame] = {}
    modelos: dict[str, object] = {}
    grafico_shap = None

    if "descriptivos" in tipos:
        tablas["descriptivos_anuales"] = descriptivos_por_anio(df)

    if "frecuencias" in tipos:
        tablas["frecuencias"] = frecuencias_categoricas(df)

    if "correlaciones" in tipos:
        tablas["correlaciones"] = correlaciones(df)

    if "logistica" in tipos:
        logit = regresion_logistica(df)
        modelos["logistica"] = logit
        coef, or_df = logistica_a_tablas(logit)
        tablas["logistica_coeficientes"] = coef
        tablas["logistica_odds_ratios"] = or_df

    if "cluster" in tipos:
        clust = clustering_kmeans(df)
        modelos["cluster"] = clust
        if "tamano_cluster_pct" in clust:
            tablas["cluster_tamanos"] = _dict_a_df_local(
                clust["tamano_cluster_pct"], "cluster", "pct"
            )
        if "perfiles_medios" in clust:
            tablas["cluster_perfiles"] = pd.DataFrame(clust["perfiles_medios"]).T.reset_index().rename(
                columns={"index": "cluster"}
            )

    if "shap" in tipos:
        shap_res = shap_importance(df, out_dir=out, prefix=label)
        modelos["shap"] = shap_res
        tablas["shap_importancia"] = shap_a_tabla(shap_res)
        grafico_shap = shap_res.get("grafico")

    if "descriptivos" in tipos and not tablas.get("descriptivos_anuales", pd.DataFrame()).empty:
        plt.figure(figsize=(9, 5))
        sns.lineplot(data=tablas["descriptivos_anuales"], x="anio", y="idx_exclusion_digital", marker="o")
        plt.title(f"Índice de exclusión digital — {label}")
        plt.ylabel("Índice (0=inclusión, 1=exclusión)")
        plt.tight_layout()
        evo_path = out / f"evolucion_exclusion_{label}.png"
        plt.savefig(evo_path, dpi=120)
        plt.close()
        grafico_shap = grafico_shap or str(evo_path)

    correlacion = None
    if len(df) > 10:
        correlacion = float(
            df[["idx_exclusion_digital", "score_movilidad_proxy"]]
            .apply(pd.to_numeric, errors="coerce")
            .corr()
            .iloc[0, 1]
        )

    return {
        "tablas": tablas,
        "modelos": modelos,
        "correlacion_destacada": correlacion,
        "grafico_shap": grafico_shap,
    }


def run_full_analysis(df: pd.DataFrame, label: str = "nacional") -> dict:
    """Compatibilidad: ejecuta todos los análisis y guarda CSV/JSON en outputs/."""
    out = _ensure_out()
    res = ejecutar_analisis(
        df,
        tipos={"descriptivos", "frecuencias", "correlaciones", "logistica", "cluster", "shap"},
        label=label,
        out_dir=out,
    )
    prefix = label.replace(" ", "_").lower()
    for name, frame in res["tablas"].items():
        frame.to_csv(out / f"{name}_{prefix}.csv", index=False)

    summary = {
        "ambito": label,
        "filas_analisis": len(df),
        "anios": sorted(df["anio"].unique().tolist()),
        "descriptivos_anuales": res["tablas"].get("descriptivos_anuales", pd.DataFrame()).to_dict(orient="records"),
        "regresion_logistica_exclusion_digital": res["modelos"].get("logistica", {}),
        "clustering": res["modelos"].get("cluster", {}),
        "shap": res["modelos"].get("shap", {}),
        "correlacion_destacada": {"exclusion_vs_movilidad_pearson": res.get("correlacion_destacada")},
    }
    with open(out / f"resumen_{prefix}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
