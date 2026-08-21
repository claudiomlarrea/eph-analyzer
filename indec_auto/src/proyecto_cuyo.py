"""Pipeline one-click del proyecto UCCuyo: brecha digital y movilidad social en Cuyo."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from .aglomerados import nombre_aglomerado
from .analyze import ejecutar_analisis
from .config import (
    AGLOMERADO_MENDOZA,
    AGLOMERADO_SAN_JUAN,
    AGLOMERADO_SAN_LUIS,
    AGLOMERADOS_CUYO,
    PROYECTO_CUYO_TITULO,
    PROYECTO_CUYO_TRIMESTRE,
    PROYECTO_CUYO_YEAR_MAX,
    PROYECTO_CUYO_YEAR_MIN,
)
from .download import available_years, download_panel
from .prepare import build_analysis_frame, validate_microdata, weighted_mean

ANALISIS_PROYECTO = {"descriptivos", "frecuencias", "correlaciones", "logistica", "cluster", "shap"}

AMBITOS_PROYECTO: list[tuple[str, str, list[int] | None]] = [
    ("nacional", "Argentina (todos los aglomerados)", None),
    ("gran_cuyo", "Gran Cuyo (Mendoza + San Luis + San Juan)", list(AGLOMERADOS_CUYO)),
    ("gran_mendoza", "Gran Mendoza", [AGLOMERADO_MENDOZA]),
    ("san_luis", "San Luis - El Chorrillo", [AGLOMERADO_SAN_LUIS]),
    ("gran_san_juan", "Gran San Juan", [AGLOMERADO_SAN_JUAN]),
]


def anios_proyecto_disponibles(trimestre: int = PROYECTO_CUYO_TRIMESTRE) -> list[int]:
    """Años del proyecto (2024–actual) disponibles en fuente automática."""
    disponibles = available_years(trimestre, PROYECTO_CUYO_YEAR_MIN, PROYECTO_CUYO_YEAR_MAX)
    return [y for y in disponibles if PROYECTO_CUYO_YEAR_MIN <= y <= PROYECTO_CUYO_YEAR_MAX]


def _kpi_ambito(df: pd.DataFrame, ambito: str, label: str) -> dict:
    w = df["PONDERA"]
    row: dict = {
        "ambito": ambito,
        "label": label,
        "n": len(df),
        "anios": ", ".join(str(int(a)) for a in sorted(df["anio"].dropna().unique())),
    }
    for col, key in [
        ("idx_exclusion_digital", "idx_exclusion_digital"),
        ("score_movilidad_proxy", "score_movilidad_proxy"),
        ("vulnerabilidad_social", "vulnerabilidad_social"),
        ("exclusion_digital_alta", "pct_exclusion_digital_alta"),
        ("secundario_completo", "pct_secundario_completo"),
        ("ocupado", "pct_ocupado"),
        ("neet_15_24", "pct_neet_15_24"),
        ("jefa_hogar", "pct_jefa_hogar"),
        ("adulto_mayor_60", "pct_adulto_mayor_60"),
        ("excl_sin_internet_hogar", "pct_sin_internet_hogar"),
        ("excl_sin_uso_internet", "pct_sin_uso_internet"),
    ]:
        if col not in df.columns or not df[col].notna().any():
            row[key] = float("nan")
            continue
        val = weighted_mean(df[col], w)
        if key.startswith("pct_"):
            row[key] = val * 100
        else:
            row[key] = val
    if "idx_exclusion_digital" in df.columns and "score_movilidad_proxy" in df.columns and len(df) > 10:
        row["corr_exclusion_movilidad"] = float(
            df[["idx_exclusion_digital", "score_movilidad_proxy"]]
            .apply(pd.to_numeric, errors="coerce")
            .corr()
            .iloc[0, 1]
        )
    else:
        row["corr_exclusion_movilidad"] = float("nan")
    return row


def _perfiles_vulnerables(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores por perfiles prioritarios del proyecto."""
    perfiles = [
        ("Total", pd.Series(True, index=df.index)),
        ("Jóvenes NEET 15-24", df.get("neet_15_24", 0) == 1),
        ("Jefas de hogar", df.get("jefa_hogar", 0) == 1),
        ("Adultos mayores 60+", df.get("adulto_mayor_60", 0) == 1),
        ("Mujeres", df.get("sexo_mujer", 0) == 1),
        ("Quintil de ingreso bajo", df.get("quintil_bajo", 0) == 1),
    ]
    rows = []
    for nombre, mask in perfiles:
        sub = df.loc[mask]
        if sub.empty:
            continue
        w = sub["PONDERA"]
        row = {"perfil": nombre, "n": len(sub)}
        for col, key, as_pct in [
            ("idx_exclusion_digital", "idx_exclusion_digital", False),
            ("score_movilidad_proxy", "score_movilidad_proxy", False),
            ("vulnerabilidad_social", "vulnerabilidad_social", False),
            ("exclusion_digital_alta", "pct_exclusion_digital_alta", True),
            ("excl_sin_internet_hogar", "pct_sin_internet_hogar", True),
            ("excl_sin_uso_internet", "pct_sin_uso_internet", True),
            ("secundario_completo", "pct_secundario_completo", True),
            ("ocupado", "pct_ocupado", True),
        ]:
            if col not in sub.columns or not sub[col].notna().any():
                row[key] = float("nan")
            else:
                val = weighted_mean(sub[col], w)
                row[key] = val * 100 if as_pct else val
        rows.append(row)
    return pd.DataFrame(rows)


def _hallazgos_objetivos(comparativo: pd.DataFrame, perfiles: pd.DataFrame) -> list[dict[str, str]]:
    """Traduce tablas a hallazgos alineados a objetivos específicos del proyecto."""
    hallazgos: list[dict[str, str]] = []

    def _val(df: pd.DataFrame, filtro_col: str, filtro_val: str, col: str) -> float | None:
        if df is None or df.empty or col not in df.columns:
            return None
        sub = df.loc[df[filtro_col] == filtro_val]
        if sub.empty:
            return None
        v = pd.to_numeric(sub.iloc[0][col], errors="coerce")
        return None if pd.isna(v) else float(v)

    nacion_excl = _val(comparativo, "ambito", "nacional", "idx_exclusion_digital")
    cuyo_excl = _val(comparativo, "ambito", "gran_cuyo", "idx_exclusion_digital")
    nacion_mov = _val(comparativo, "ambito", "nacional", "score_movilidad_proxy")
    cuyo_mov = _val(comparativo, "ambito", "gran_cuyo", "score_movilidad_proxy")

    hallazgos.append(
        {
            "objetivo": "OE1 — Operacionalizar indicadores EPH/TIC en Cuyo",
            "hallazgo": (
                "Se construyeron índices de exclusión digital, movilidad social (proxy) y "
                "vulnerabilidad social con microdatos EPH hogar+individuo+TIC para Nación y Gran Cuyo."
            ),
        }
    )

    if nacion_excl is not None and cuyo_excl is not None:
        diff = cuyo_excl - nacion_excl
        sentido = "mayor" if diff > 0 else "menor"
        cuyo_mov_txt = f"{cuyo_mov:.3f}" if cuyo_mov is not None else "N/D"
        nacion_mov_txt = f"{nacion_mov:.3f}" if nacion_mov is not None else "N/D"
        hallazgos.append(
            {
                "objetivo": "OE2 — Comparar Cuyo vs. promedio nacional",
                "hallazgo": (
                    f"Exclusión digital en Gran Cuyo = {cuyo_excl:.3f} vs Nación = {nacion_excl:.3f} "
                    f"({sentido} en {abs(diff):.3f} puntos). "
                    f"Movilidad proxy: Cuyo={cuyo_mov_txt} · Nación={nacion_mov_txt}."
                ),
            }
        )

    for ambito, etiqueta in [
        ("gran_san_juan", "Gran San Juan"),
        ("gran_mendoza", "Gran Mendoza"),
        ("san_luis", "San Luis"),
    ]:
        excl = _val(comparativo, "ambito", ambito, "idx_exclusion_digital")
        if excl is not None:
            hallazgos.append(
                {
                    "objetivo": "OE2 — Desagregación provincial",
                    "hallazgo": f"{etiqueta}: índice de exclusión digital = {excl:.3f}.",
                }
            )

    if perfiles is not None and not perfiles.empty and "idx_exclusion_digital" in perfiles.columns:
        orden = perfiles.dropna(subset=["idx_exclusion_digital"]).sort_values(
            "idx_exclusion_digital", ascending=False
        )
        if not orden.empty:
            top = orden.iloc[0]
            hallazgos.append(
                {
                    "objetivo": "OE3 — Identificar perfiles de vulnerabilidad",
                    "hallazgo": (
                        f"El perfil con mayor exclusión digital es «{top['perfil']}» "
                        f"(índice={float(top['idx_exclusion_digital']):.3f}; n={int(top['n']):,})."
                    ),
                }
            )

    corr = _val(comparativo, "ambito", "gran_cuyo", "corr_exclusion_movilidad")
    if corr is None:
        corr = _val(comparativo, "ambito", "nacional", "corr_exclusion_movilidad")
    if corr is not None:
        hallazgos.append(
            {
                "objetivo": "OE4 — Asociación exclusión digital ↔ movilidad social",
                "hallazgo": (
                    f"Correlación Pearson exclusión digital vs. movilidad proxy = {corr:.3f} "
                    "(valores negativos indican que a mayor exclusión, menor movilidad)."
                ),
            }
        )

    hallazgos.append(
        {
            "objetivo": "OE5 — Productos de transferencia",
            "hallazgo": (
                "Se generan Excel y Word con KPIs comparativos, perfiles vulnerables, "
                "descriptivos, correlaciones, logística, clústeres y SHAP listos para "
                "informes trimestrales y fichas de prensa."
            ),
        }
    )
    return hallazgos


def ejecutar_proyecto_cuyo(
    *,
    years: list[int] | None = None,
    trimestre: int = PROYECTO_CUYO_TRIMESTRE,
    force_download: bool = False,
    titulo: str = PROYECTO_CUYO_TITULO,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Descarga microdatos INDEC del período y ejecuta el paquete completo del proyecto."""

    def _log(msg: str) -> None:
        if progress:
            progress(msg)

    if years is None:
        years = anios_proyecto_disponibles(trimestre)
    if not years:
        raise RuntimeError(
            f"No hay años disponibles en fuente automática para T{trimestre} "
            f"en el rango {PROYECTO_CUYO_YEAR_MIN}–{PROYECTO_CUYO_YEAR_MAX}."
        )

    _log(f"Descargando microdatos EPH T{trimestre} · años {min(years)}–{max(years)}…")
    hogar, individual = download_panel(years=list(years), trimester=trimestre, force=force_download)

    resultados_por_ambito: dict[str, dict] = {}
    kpis: list[dict] = []
    perfiles_por_ambito: list[pd.DataFrame] = []

    for ambito, label, aglos in AMBITOS_PROYECTO:
        _log(f"Analizando ámbito: {label}…")
        df = build_analysis_frame(
            hogar,
            individual,
            aglomerados=aglos,
            include_tic=True,
        )
        if df.empty:
            _log(f"Sin registros para {label}; se omite.")
            continue
        val = validate_microdata(df)
        res = ejecutar_analisis(df, tipos=ANALISIS_PROYECTO, label=ambito)
        res["meta"] = {
            "titulo": titulo,
            "ambito": label,
            "ambito_id": ambito,
            "periodo": f"{min(years)}–{max(years)} (T{trimestre})",
            "registros": len(df),
            "validacion": val,
            "modulo": "tic",
            "aglomerados": [nombre_aglomerado(a) for a in (aglos or [])] or ["Todos"],
            "fuente": "INDEC — EPH hogar + individuo + TIC/MAUTIC (automático)",
            "proyecto": "Brecha digital y movilidad social en Cuyo (UCCuyo)",
        }
        resultados_por_ambito[ambito] = res
        kpis.append(_kpi_ambito(df, ambito, label))
        perf = _perfiles_vulnerables(df)
        if not perf.empty:
            perf.insert(0, "ambito", ambito)
            perf.insert(1, "label", label)
            perfiles_por_ambito.append(perf)

    comparativo = pd.DataFrame(kpis)
    perfiles = pd.concat(perfiles_por_ambito, ignore_index=True) if perfiles_por_ambito else pd.DataFrame()
    hallazgos = _hallazgos_objetivos(comparativo, perfiles.loc[perfiles["ambito"] == "gran_cuyo"] if not perfiles.empty else perfiles)

    # Tabla principal del observatorio (Nación vs Cuyo vs provincias)
    tablas_proyecto = {
        "comparativo_ambitos": comparativo,
        "perfiles_vulnerables": perfiles,
        "hallazgos_objetivos": pd.DataFrame(hallazgos),
    }

    # Adjuntar tablas del ámbito Gran Cuyo (o Nación si faltara) como núcleo
    nucleo = resultados_por_ambito.get("gran_cuyo") or resultados_por_ambito.get("nacional")
    if nucleo:
        for k, v in nucleo.get("tablas", {}).items():
            tablas_proyecto[f"cuyo_{k}"] = v

    resultado = {
        "tablas": tablas_proyecto,
        "modelos": (nucleo or {}).get("modelos", {}),
        "correlacion_destacada": (nucleo or {}).get("correlacion_destacada"),
        "grafico_shap": (nucleo or {}).get("grafico_shap"),
        "grafico_evolucion": (nucleo or {}).get("grafico_evolucion"),
        "por_ambito": resultados_por_ambito,
        "meta": {
            "titulo": titulo,
            "ambito": "Proyecto Cuyo (multi-ámbito)",
            "periodo": f"{min(years)}–{max(years)} (T{trimestre})",
            "registros": int(comparativo["n"].sum()) if not comparativo.empty else 0,
            "anios": years,
            "trimestre": trimestre,
            "modulo": "tic",
            "fuente": "INDEC — EPH hogar + individuo + TIC/MAUTIC (automático)",
            "proyecto": "Brecha digital y movilidad social en Cuyo (UCCuyo)",
            "objetivos_cubiertos": [
                "OE1 indicadores",
                "OE2 comparación regional",
                "OE3 perfiles / cluster / SHAP",
                "OE4 asociación exclusión-movilidad",
                "OE5 Excel/Word transferencia",
            ],
        },
        "hallazgos": hallazgos,
    }
    _log("Proyecto Cuyo completado.")
    return resultado
