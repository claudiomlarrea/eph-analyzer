"""Motor de escenarios contrafactuales GEMEPH (what-if con sliders)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from indec_auto.src.analyze import _features_disponibles
from indec_auto.src.prepare import weighted_mean

from .kpis import compute_kpis

# Variables ajustables con sliders (orden de la UI)
LEVER_SPECS: list[dict[str, Any]] = [
    {
        "id": "internet_quintil_i",
        "label": "Hogares con internet en quintil I (ingresos bajos)",
        "help": "Porcentaje de personas del quintil I cuyo hogar tiene internet.",
        "kpi_key": "pct_internet_quintil_i",
        "requires_tic": True,
    },
    {
        "id": "pct_superior",
        "label": "Educación universitaria completa",
        "help": "Porcentaje de personas con estudios superiores completos.",
        "kpi_key": "pct_superior",
        "requires_tic": False,
    },
    {
        "id": "pct_empleo_formal",
        "label": "Empleo formal (entre ocupados)",
        "help": "Porcentaje de ocupados con empleo formal (con descuentos jubilatorios).",
        "kpi_key": "pct_empleo_formal",
        "requires_tic": False,
    },
]


def _pct_good(df: pd.DataFrame, col_excl: str, mask: pd.Series | None = None) -> float:
    sub = df.loc[mask] if mask is not None else df
    if col_excl not in sub.columns or sub.empty:
        return 0.0
    good = 1.0 - sub[col_excl].fillna(np.nan)
    w = sub["PONDERA"]
    v = weighted_mean(good, w)
    return 0.0 if np.isnan(v) else float(v) * 100.0


def _pct_col(df: pd.DataFrame, col: str, mask: pd.Series | None = None) -> float:
    sub = df.loc[mask] if mask is not None else df
    if col not in sub.columns or sub.empty:
        return 0.0
    w = sub["PONDERA"]
    v = weighted_mean(sub[col], w)
    return 0.0 if np.isnan(v) else float(v) * 100.0


def lever_baselines(df: pd.DataFrame, *, include_tic: bool = True) -> dict[str, float]:
    """Valores actuales (0–100) para inicializar sliders."""
    dec = pd.to_numeric(df.get("decil_ingreso"), errors="coerce")
    q1 = dec <= 2
    ocup = df.get("ocupado") == 1

    out: dict[str, float] = {
        "pct_superior": round(_pct_col(df, "superior"), 1),
        "pct_empleo_formal": round(100.0 - _pct_col(df, "informal_proxy", ocup), 1),
    }
    if include_tic and "excl_sin_internet_hogar" in df.columns:
        out["internet_quintil_i"] = round(_pct_good(df, "excl_sin_internet_hogar", q1), 1)
    return out


def _mask_quintil_i(df: pd.DataFrame) -> pd.Series:
    dec = pd.to_numeric(df["decil_ingreso"], errors="coerce")
    return dec <= 2


def _weighted_adjust_binary(
    df: pd.DataFrame,
    mask: pd.Series,
    col: str,
    *,
    target_good_pct: float,
    good_value: float = 0.0,
    bad_value: float = 1.0,
) -> pd.DataFrame:
    """Cambia filas en `mask` para acercar la tasa de `good_value` al objetivo (%)."""
    out = df.copy()
    sub_idx = out.index[mask & out[col].notna()]
    if len(sub_idx) == 0:
        return out

    w = out.loc[sub_idx, "PONDERA"].fillna(1.0)
    col_vals = out.loc[sub_idx, col].astype(float)
    good_now = (col_vals == good_value)
    current_pct = float(np.average(good_now.astype(float), weights=w)) * 100.0
    target = float(np.clip(target_good_pct, 0.0, 100.0))

    if target <= current_pct + 0.05:
        return out

    # Pasar filas de malo → bueno hasta alcanzar el peso objetivo
    need_good_w = (target / 100.0) * w.sum()
    have_good_w = w[good_now].sum()
    extra_w = max(0.0, need_good_w - have_good_w)

    bad_idx = sub_idx[~good_now]
    if len(bad_idx) == 0 or extra_w <= 0:
        return out

    bad_weights = out.loc[bad_idx, "PONDERA"].fillna(1.0)
    order = bad_weights.sort_values(ascending=False).index
    cum = 0.0
    for idx in order:
        if cum >= extra_w:
            break
        out.at[idx, col] = good_value
        cum += float(out.at[idx, "PONDERA"] if pd.notna(out.at[idx, "PONDERA"]) else 1.0)

    return out


def _weighted_adjust_rate(
    df: pd.DataFrame,
    mask: pd.Series,
    col: str,
    *,
    target_one_pct: float,
) -> pd.DataFrame:
    """Sube `col` a 1 en suficientes filas (valor 0) para alcanzar tasa objetivo."""
    out = df.copy()
    sub_idx = out.index[mask & out[col].notna()]
    if len(sub_idx) == 0:
        return out

    w = out.loc[sub_idx, "PONDERA"].fillna(1.0)
    vals = out.loc[sub_idx, col].astype(float)
    current_pct = float(np.average(vals, weights=w)) * 100.0
    target = float(np.clip(target_one_pct, 0.0, 100.0))

    if target <= current_pct + 0.05:
        return out

    need_one_w = (target / 100.0) * w.sum()
    have_one_w = w[vals == 1].sum()
    extra_w = max(0.0, need_one_w - have_one_w)

    zero_idx = sub_idx[vals == 0]
    if len(zero_idx) == 0 or extra_w <= 0:
        return out

    zw = out.loc[zero_idx, "PONDERA"].fillna(1.0)
    for idx in zw.sort_values(ascending=False).index:
        if extra_w <= 0:
            break
        out.at[idx, col] = 1.0
        extra_w -= float(out.at[idx, "PONDERA"] if pd.notna(out.at[idx, "PONDERA"]) else 1.0)

    return out


def _recalc_derived(df: pd.DataFrame, *, exclusion_threshold: float | None = None) -> pd.DataFrame:
    """Recalcula índices compuestos tras modificar variables base."""
    out = df.copy()

    acceso_cols = [c for c in ("excl_sin_pc", "excl_sin_internet_hogar") if c in out.columns]
    uso_cols = [c for c in ("excl_sin_uso_cel", "excl_sin_uso_pc", "excl_sin_uso_internet") if c in out.columns]
    all_excl = acceso_cols + uso_cols

    if all_excl:
        out["idx_acceso"] = out[acceso_cols].mean(axis=1, skipna=True) if acceso_cols else np.nan
        out["idx_uso"] = out[uso_cols].mean(axis=1, skipna=True) if uso_cols else np.nan
        out["idx_exclusion_digital"] = out[all_excl].mean(axis=1, skipna=True)
        thr = exclusion_threshold
        if thr is None:
            thr = float(out["idx_exclusion_digital"].median())
        out["exclusion_digital_alta"] = (out["idx_exclusion_digital"] >= thr).astype(int)

    out["score_movilidad_proxy"] = (
        out["secundario_completo"].fillna(0) * 0.3
        + out["superior"].fillna(0) * 0.2
        + out["ocupado"].fillna(0) * 0.2
        + (1 - out["informal_proxy"].fillna(1)) * 0.15
        + out["quintil_alto"].fillna(0) * 0.15
    )

    out["vulnerabilidad_social"] = (
        (1 - out["secundario_completo"].fillna(0)) * 0.35
        + out["desocupado"].fillna(0) * 0.25
        + out["quintil_bajo"].fillna(0) * 0.25
        + out["idx_exclusion_digital"].fillna(0) * 0.15
    )

    return out


def apply_scenario(
    df: pd.DataFrame,
    targets: dict[str, float],
    *,
    include_tic: bool = True,
) -> pd.DataFrame:
    """Aplica metas de sliders sobre una copia del panel territorial."""
    out = df.copy()
    baseline_thr = None
    if include_tic and "idx_exclusion_digital" in out.columns:
        baseline_thr = float(out["idx_exclusion_digital"].median())

    if include_tic and "internet_quintil_i" in targets and "excl_sin_internet_hogar" in out.columns:
        out = _weighted_adjust_binary(
            out,
            _mask_quintil_i(out),
            "excl_sin_internet_hogar",
            target_good_pct=targets["internet_quintil_i"],
            good_value=0.0,
            bad_value=1.0,
        )

    if "pct_superior" in targets:
        out = _weighted_adjust_rate(out, pd.Series(True, index=out.index), "superior", target_one_pct=targets["pct_superior"])

    if "pct_empleo_formal" in targets and "informal_proxy" in out.columns:
        out = _weighted_adjust_binary(
            out,
            out["ocupado"] == 1,
            "informal_proxy",
            target_good_pct=targets["pct_empleo_formal"],
            good_value=0.0,
            bad_value=1.0,
        )

    return _recalc_derived(out, exclusion_threshold=baseline_thr)


def _fit_exclusion_model(df: pd.DataFrame) -> tuple[Pipeline | None, list[str], str | None]:
    target = "exclusion_digital_alta"
    features = _features_disponibles(df)
    if not features or target not in df.columns:
        return None, [], "Sin variables para modelo predictivo."

    sub = df[features + [target, "PONDERA"]].dropna()
    if len(sub) < 300:
        return None, features, f"Muestra insuficiente para modelo ({len(sub)} registros)."

    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipe.fit(sub[features], sub[target].astype(int))
    return pipe, features, None


def _predicted_exclusion_pct(df: pd.DataFrame, pipe: Pipeline, features: list[str]) -> float | None:
    sub = df[features + ["PONDERA"]].dropna()
    if sub.empty:
        return None
    proba = pipe.predict_proba(sub[features])[:, 1]
    w = sub["PONDERA"]
    return round(float(np.average(proba, weights=w)) * 100.0, 2)


def run_scenario(
    df: pd.DataFrame,
    targets: dict[str, float],
    *,
    include_tic: bool = True,
) -> dict[str, Any]:
    """Ejecuta escenario y devuelve baseline, resultado y deltas."""
    baseline_kpis = compute_kpis(df, include_tic=include_tic)
    baselines = lever_baselines(df, include_tic=include_tic)

    df_scn = apply_scenario(df, targets, include_tic=include_tic)
    scenario_kpis = compute_kpis(df_scn, include_tic=include_tic)

    deltas: dict[str, float] = {}
    compare_keys = [
        "idx_exclusion_digital",
        "pct_exclusion_digital_alta",
        "vulnerabilidad_social",
        "score_movilidad_proxy",
        "pct_superior",
        "pct_ocupado",
    ]
    for key in compare_keys:
        b = baseline_kpis.get(key)
        s = scenario_kpis.get(key)
        if b is not None and s is not None:
            deltas[key] = round(float(s) - float(b), 4)

    model_note = None
    pred_base = pred_scn = None
    if include_tic:
        pipe, features, err = _fit_exclusion_model(df)
        if pipe is not None:
            pred_base = _predicted_exclusion_pct(df, pipe, features)
            pred_scn = _predicted_exclusion_pct(df_scn, pipe, features)
        else:
            model_note = err

    return {
        "baseline_kpis": baseline_kpis,
        "scenario_kpis": scenario_kpis,
        "deltas": deltas,
        "lever_baselines": baselines,
        "targets": targets,
        "modelo": {
            "pct_exclusion_predicho_base": pred_base,
            "pct_exclusion_predicho_escenario": pred_scn,
            "nota": model_note,
        },
    }


def compare_rows(result: dict[str, Any]) -> pd.DataFrame:
    """Tabla baseline vs escenario para la UI."""
    labels = {
        "idx_exclusion_digital": "Exclusión digital (índice 0–1)",
        "pct_exclusion_digital_alta": "Exclusión digital alta (%)",
        "vulnerabilidad_social": "Vulnerabilidad social (índice)",
        "score_movilidad_proxy": "Movilidad social proxy (índice)",
        "pct_superior": "Educación superior (%)",
        "pct_ocupado": "Tasa de ocupación (%)",
        "pct_informal_ocupados": "Informalidad ocupados (%)",
    }
    rows = []
    base = result["baseline_kpis"]
    scn = result["scenario_kpis"]
    deltas = result.get("deltas", {})
    for key, label in labels.items():
        if key not in base and key not in scn:
            continue
        b = base.get(key)
        s = scn.get(key)
        d = deltas.get(key)
        rows.append(
            {
                "Indicador": label,
                "Baseline": b,
                "Escenario": s,
                "Cambio": d,
            }
        )
    return pd.DataFrame(rows)
