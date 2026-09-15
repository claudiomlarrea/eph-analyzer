"""Mapas interactivos GEMEPH (Plotly MapLibre)."""

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
    size_col = next((c for c in ("n_individuos", "n") if c in geo.columns), None)
    if size_col is None:
        size_col = "n_individuos"
        geo[size_col] = 1

    name_col = "territorio_nombre" if "territorio_nombre" in geo.columns else geo.columns[0]

    # Plotly 7 eliminó scatter_mapbox; usar scatter_map (MapLibre).
    # Mantener fallback para entornos con Plotly < 5.24.
    use_maplibre = hasattr(px, "scatter_map")
    scatter_fn = px.scatter_map if use_maplibre else px.scatter_mapbox

    kwargs = dict(
        data_frame=geo,
        lat="lat",
        lon="lon",
        color=metrica,
        size=size_col,
        size_max=28,
        color_continuous_scale=scale,
        zoom=3.6,
        center={"lat": -38.5, "lon": -64.0},
        hover_name=name_col,
        labels={metrica: label, size_col: "Individuos"},
        title=f"Mapa territorial — {label}",
    )
    if use_maplibre:
        kwargs["map_style"] = "open-street-map"
    else:
        kwargs["mapbox_style"] = "open-street-map"

    fig = scatter_fn(**kwargs)

    if highlight_codigo is not None and "aglomerado_codigo" in geo.columns:
        hi = geo.loc[geo["aglomerado_codigo"] == highlight_codigo]
        if not hi.empty:
            scatter_cls = go.Scattermap if hasattr(go, "Scattermap") else go.Scattermapbox
            fig.add_trace(
                scatter_cls(
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
