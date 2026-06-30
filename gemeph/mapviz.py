"""Mapas interactivos GEMEPH (Plotly)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .coords import enrich_catalog_geo

# Indicadores donde valores más bajos son mejores
_INVERT_COLOR = frozenset(
    {
        "idx_exclusion_digital",
        "pct_exclusion_digital_alta",
        "vulnerabilidad_social",
        "pct_informal_ocupados",
    }
)

MAP_METRICS = {
    "idx_exclusion_digital": "Exclusión digital (índice)",
    "pct_exclusion_digital_alta": "Exclusión digital alta (%)",
    "pct_ocupado": "Tasa de ocupación (%)",
    "pct_superior": "Educación superior (%)",
    "vulnerabilidad_social": "Vulnerabilidad social",
    "score_movilidad_proxy": "Movilidad social (proxy)",
}


def metric_choices(include_tic: bool) -> dict[str, str]:
    opts = dict(MAP_METRICS)
    if not include_tic:
        opts.pop("idx_exclusion_digital", None)
        opts.pop("pct_exclusion_digital_alta", None)
    return opts


def build_map_figure(
    cat_df: pd.DataFrame,
    metrica: str,
    *,
    highlight_codigo: int | None = None,
    metric_label: str | None = None,
) -> go.Figure:
    geo = enrich_catalog_geo(cat_df)
    if geo.empty or metrica not in geo.columns:
        fig = go.Figure()
        fig.update_layout(title="Sin datos geográficos para el indicador seleccionado")
        return fig

    geo = geo.dropna(subset=[metrica]).copy()
    label = metric_label or MAP_METRICS.get(metrica, metrica)
    scale = "RdYlGn_r" if metrica in _INVERT_COLOR else "RdYlGn"

    geo["hover"] = geo.apply(
        lambda r: (
            f"<b>{r['territorio_nombre']}</b><br>"
            f"{label}: {r[metrica]:.4g}<br>"
            f"Muestra: {int(r.get('n_individuos', 0)):,} individuos"
        ),
        axis=1,
    )

    fig = px.scatter_mapbox(
        geo,
        lat="lat",
        lon="lon",
        color=metrica,
        size="n_individuos",
        size_max=28,
        color_continuous_scale=scale,
        mapbox_style="open-street-map",
        zoom=3.6,
        center={"lat": -38.5, "lon": -64.0},
        hover_name="territorio_nombre",
        labels={metrica: label, "n_individuos": "Individuos"},
        title=f"Mapa territorial — {label}",
    )

    if highlight_codigo is not None:
        hi = geo.loc[geo["aglomerado_codigo"] == highlight_codigo]
        if not hi.empty:
            fig.add_trace(
                go.Scattermapbox(
                    lat=hi["lat"],
                    lon=hi["lon"],
                    mode="markers+text",
                    marker={"size": 22, "color": "#c62828", "opacity": 0.95},
                    text=["★"],
                    textfont={"size": 18, "color": "#c62828"},
                    hoverinfo="skip",
                    name="Seleccionado",
                )
            )

    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        height=560,
        coloraxis_colorbar={"title": label},
    )
    return fig
