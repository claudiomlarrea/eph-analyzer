#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mejora presentacion GEMEPH Jornadas IA 2026: redaccion y graficos."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from pptx import Presentation
from pptx.util import Inches

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "JORNADAS IA 2026"
CHARTS_DIR = OUT_DIR / "graficos"
SOURCE_PPT = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/Presentacion_GEMEPH_Jornadas_IA_2026_bd00.pptx"
)

BASELINE = {
    "exclusion_digital": 0.6205,
    "exclusion_alta_pct": 53.96,
    "vulnerabilidad": 0.2667,
    "movilidad_proxy": 0.4774,
    "ocupacion_pct": 58.62,
    "pred_exclusion_alta_pct": 6.08,
}

TOP_EXCLUSION = [
    ("Ushuaia-R.G.", 0.6298),
    ("Rio Gallegos", 0.6277),
    ("Partidos GBA", 0.6270),
    ("Gran Resistencia", 0.6267),
    ("Jujuy-Palpala", 0.6246),
]
REF_LOW = ("Gran Cordoba", 0.5979)

ESCENARIOS = {
    "Baseline": {"movilidad": 0.4774, "pred_exc": 6.08},
    "E1 Conectividad": {"movilidad": 0.4774, "pred_exc": 5.73},
    "E2 Educacion 40%": {"movilidad": 0.5183, "pred_exc": 6.08},
    "E3 Integrado": {"movilidad": 0.5125, "pred_exc": 5.84},
}

PALETTE = {
    "primary": "#1B3A6B",
    "secondary": "#2E6DB4",
    "accent": "#E8A838",
    "muted": "#6B7B8C",
    "e1": "#5B9BD5",
    "e2": "#70AD47",
    "e3": "#ED7D31",
}

SLIDES = {
    1: (
        "GEMEPH\n"
        "Gemelo digital sociodemogr\u00e1fico de la EPH-INDEC\n\n"
        "Exclusi\u00f3n digital, vulnerabilidad y brechas territoriales en Argentina\n\n"
        "C. Larrea Arnau\u00b9 \u00b7 J. La Malfa \u00b7 J. Coria \u00b7 S. Young \u00b7 B. Arias \u00b7 L. Pizarro\n"
        "Observatorio de Inteligencia Artificial \u2014 Universidad Cat\u00f3lica de Cuyo\n"
        "observatorioia@uccuyo.edu.ar"
    ),
    2: (
        "\u00bfPor qu\u00e9 un gemelo digital sobre la EPH?\n"
        "\u2022 La Encuesta Permanente de Hogares (INDEC) es la fuente oficial para estudiar "
        "vida, empleo, educaci\u00f3n y TIC en el aglomerado urbano argentino.\n"
        "\u2022 Sin embargo, la EPH describe el presente: no permite explorar de forma "
        "sistem\u00e1tica qu\u00e9 ocurrir\u00eda si mejoran conectividad, educaci\u00f3n o formalidad laboral.\n"
        "\u2022 GEMEPH representa el dato oficial y lo expone a escenarios contrafactuales "
        "(what-if) con trazabilidad y reproducibilidad.\n"
        "\u2022 Objetivo: apoyar investigaci\u00f3n, docencia y decisi\u00f3n en el Observatorio de IA "
        "\u00b7 UCCuyo, con evidencia comparable en 31 aglomerados."
    ),
    3: (
        "\u00bfC\u00f3mo funciona GEMEPH?\n"
        "\u2022 Integraci\u00f3n de microdatos EPH 2022\u20132024 (4.\u00ba trimestre, m\u00f3dulo TIC): "
        "114.280 registros individuales, ponderados con PONDERA.\n"
        "\u2022 C\u00e1lculo de indicadores: exclusi\u00f3n digital, vulnerabilidad social, movilidad "
        "proxy, ocupaci\u00f3n, educaci\u00f3n e informalidad.\n"
        "\u2022 Modelado en Python (pandas, scikit-learn): perfiles k-means y predicci\u00f3n de "
        "exclusi\u00f3n digital alta.\n"
        "\u2022 Simulaci\u00f3n mediante tres palancas: internet en quintil I, educaci\u00f3n superior "
        "completa y empleo formal.\n"
        "\u2022 Tres escenarios ficticios \u2014 E1 conectividad \u00b7 E2 educaci\u00f3n al 40% \u00b7 "
        "E3 paquete integrado \u2014 sobre un mismo baseline oficial.\n"
        "\u2022 Plataforma p\u00fablica: eph-analyzer.streamlit.app/GEMEPH"
    ),
    4: (
        "Resultados del baseline oficial\n"
        "\u2022 Exclusi\u00f3n digital: 0,62 \u2014 54% en exclusi\u00f3n alta.\n"
        "\u2022 Vulnerabilidad: 0,27 \u00b7 Movilidad proxy: 0,48.\n"
        "\u2022 Fuerte heterogeneidad entre los 31 aglomerados urbanos.\n"
        "\u2022 Ushuaia\u2013R\u00edo Grande lidera el ranking; Gran C\u00f3rdoba, el valor m\u00e1s bajo.\n"
        "\u2022 El gemelo actualiza estas brechas con cada onda del INDEC."
    ),
    5: (
        "Tres escenarios, tres lecciones\n"
        "\u2022 E1 Conectividad: efecto marginal (quintil bajo ya al 94% de internet).\n"
        "\u2022 E2 Educaci\u00f3n al 40%: mayor impacto en movilidad proxy (+0,04).\n"
        "\u2022 E3 Paquete integrado: efecto m\u00e1s equilibrado; exclusi\u00f3n predicha 5,84%.\n"
        "\u2022 Una sola palanca digital no basta: conviene combinar pol\u00edticas.\n"
        "\u2022 El gemelo anticipa magnitudes de cambio sin reemplazar al INDEC."
    ),
    6: (
        "Gracias\n\n"
        "Preguntas y comentarios\n"
        "observatorioia@uccuyo.edu.ar\n\n"
        "GEMEPH \u00b7 eph-analyzer.streamlit.app/GEMEPH\n"
        "Observatorio de Inteligencia Artificial \u00b7 UCCuyo"
    ),
}


def _style_axes(ax, title: str) -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", color=PALETTE["primary"], pad=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.set_facecolor("#FAFBFC")


def build_charts() -> dict[str, Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    fig, ax = plt.subplots(figsize=(6.5, 2.4), dpi=150)
    labels = ["Exclusion\ndigital", "Vulnerabilidad\nsocial", "Movilidad\nproxy"]
    values = [BASELINE["exclusion_digital"], BASELINE["vulnerabilidad"], BASELINE["movilidad_proxy"]]
    colors = [PALETTE["secondary"], PALETTE["accent"], PALETTE["e2"]]
    bars = ax.bar(labels, values, color=colors, width=0.55, edgecolor="white", linewidth=0.8)
    ax.set_ylim(0, 0.75)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.015,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color=PALETTE["primary"],
        )
    _style_axes(ax, "Argentina urbana - Baseline EPH 2022-2024 (T4, TIC)")
    fig.text(
        0.5,
        0.02,
        f"Exclusion digital alta: {BASELINE['exclusion_alta_pct']:.1f}%  |  "
        f"Ocupacion: {BASELINE['ocupacion_pct']:.1f}%",
        ha="center",
        fontsize=8,
        color=PALETTE["muted"],
    )
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    p1 = CHARTS_DIR / "01_baseline_indicadores.png"
    fig.savefig(p1, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths["baseline"] = p1

    fig, ax = plt.subplots(figsize=(6.5, 2.5), dpi=150)
    nombres = [n for n, _ in TOP_EXCLUSION] + [REF_LOW[0]]
    vals = [v for _, v in TOP_EXCLUSION] + [REF_LOW[1]]
    cols = [PALETTE["e3"]] * 5 + [PALETTE["e2"]]
    y = np.arange(len(nombres))
    bars = ax.barh(y, vals, color=cols, height=0.6, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(nombres, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0.59, 0.64)
    for bar, val in zip(bars, vals):
        ax.text(
            val + 0.0003,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}",
            va="center",
            fontsize=7.5,
            color=PALETTE["primary"],
        )
    _style_axes(ax, "Exclusion digital - Top 5 aglomerados vs referencia minima")
    fig.tight_layout()
    p2 = CHARTS_DIR / "02_brecha_territorial.png"
    fig.savefig(p2, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths["territorial"] = p2

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=150)
    esc_names = list(ESCENARIOS.keys())
    x = np.arange(len(esc_names))
    mov = [ESCENARIOS[e]["movilidad"] for e in esc_names]
    pred = [ESCENARIOS[e]["pred_exc"] for e in esc_names]
    esc_colors = [PALETTE["muted"], PALETTE["e1"], PALETTE["e2"], PALETTE["e3"]]

    ax = axes[0]
    bars = ax.bar(x, mov, color=esc_colors, width=0.6, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(["Base", "E1", "E2", "E3"], fontsize=8)
    ax.set_ylabel("Indice", fontsize=8)
    baseline_mov = mov[0]
    for bar, val in zip(bars, mov):
        delta = val - baseline_mov
        label = f"{val:.3f}" if abs(delta) < 0.0001 else f"{val:.3f}\n(+{delta:.3f})"
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.003, label, ha="center", va="bottom", fontsize=7, fontweight="bold")
    _style_axes(ax, "Movilidad social proxy")

    ax = axes[1]
    bars = ax.bar(x, pred, color=esc_colors, width=0.6, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(["Base", "E1", "E2", "E3"], fontsize=8)
    ax.set_ylabel("%", fontsize=8)
    baseline_pred = pred[0]
    for bar, val in zip(bars, pred):
        delta = val - baseline_pred
        sign = "+" if delta >= 0 else ""
        label = f"{val:.2f}%" if abs(delta) < 0.01 else f"{val:.2f}%\n({sign}{delta:.2f} pp)"
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.08, label, ha="center", va="bottom", fontsize=7, fontweight="bold")
    _style_axes(ax, "Prediccion exclusion digital alta")

    legend_patches = [
        mpatches.Patch(color=PALETTE["e1"], label="E1 Conectividad"),
        mpatches.Patch(color=PALETTE["e2"], label="E2 Educacion 40%"),
        mpatches.Patch(color=PALETTE["e3"], label="E3 Paquete integrado"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Escenarios contrafactuales sobre el mismo baseline oficial", fontsize=10, fontweight="bold", color=PALETTE["primary"], y=1.02)
    fig.tight_layout()
    p3 = CHARTS_DIR / "03_comparacion_escenarios.png"
    fig.savefig(p3, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths["escenarios"] = p3

    return paths


def _set_shape_text(shape, text: str) -> None:
    tf = shape.text_frame
    lines = text.split("\n")
    if not tf.paragraphs:
        tf.add_paragraph()
    for i, line in enumerate(lines):
        if i < len(tf.paragraphs):
            tf.paragraphs[i].text = line
        else:
            tf.add_paragraph().text = line
    while len(tf.paragraphs) > len(lines):
        p = tf.paragraphs[-1]._element
        p.getparent().remove(p)


def _add_chart(slide, path: Path, left: float, top: float, width: float) -> None:
    slide.shapes.add_picture(str(path), Inches(left), Inches(top), width=Inches(width))


def build_presentation(chart_paths: dict[str, Path], out_path: Path) -> None:
    shutil.copy2(SOURCE_PPT, out_path)
    prs = Presentation(out_path)

    for idx, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.name == "Rounded Rectangle 9" and idx in SLIDES:
                _set_shape_text(shape, SLIDES[idx])
                if idx in (4, 5):
                    shape.width = Inches(6.1)

        if idx == 4:
            _add_chart(slide, chart_paths["baseline"], left=6.55, top=2.20, width=6.2)
            _add_chart(slide, chart_paths["territorial"], left=6.55, top=4.35, width=6.2)
        elif idx == 5:
            _add_chart(slide, chart_paths["escenarios"], left=6.55, top=2.30, width=6.2)

    prs.save(out_path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    charts = build_charts()

    ppt_out = OUT_DIR / "Presentacion_GEMEPH_Jornadas_IA_2026.pptx"
    ppt_named = OUT_DIR / "Investigacion_UCCuyo_Larrea_GEMEPH.pptx"
    ppt_tpl = OUT_DIR / "plantilla-presentacion-jornadas-ia-2026.pptx"

    build_presentation(charts, ppt_out)
    shutil.copy2(ppt_out, ppt_named)
    shutil.copy2(ppt_out, ppt_tpl)

    word_src = Path(
        "/home/ubuntu/.cursor/projects/workspace/uploads/"
        "Investigacion_UCCuyo_Larrea_GEMEPH_GemeloDigitalEPH_128f.docx"
    )
    if word_src.exists():
        shutil.copy2(word_src, OUT_DIR / "Investigacion_UCCuyo_Larrea_GEMEPH_GemeloDigitalEPH.docx")

    print(f"Presentacion mejorada: {ppt_out}")
    print(f"Graficos: {', '.join(p.name for p in charts.values())}")


if __name__ == "__main__":
    main()
