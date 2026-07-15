#!/usr/bin/env python3
"""Genera el instructivo PDF de Análisis EPH (INDEC) — misma estética Observatorio/EvaluAR."""

from __future__ import annotations

import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "instructivo"
LOGO = ROOT / "assets" / "logo_observatorio_ia.png"
OUTPUT = ROOT / "assets" / "instructivo_analisis_eph.pdf"
DOCS_OUTPUT = Path.home() / "Documents" / "AnalisisEPH" / "instructivo-analisis-eph-uccuyo.pdf"
OBS_OUTPUT = (
    Path.home()
    / "Projects"
    / "observatorio-ia"
    / "docs"
    / "instructivos"
    / "instructivo-analisis-eph.pdf"
)

URL_UCCUYO = "https://uccuyo.edu.ar/"
URL_OBS = "https://claudiomlarrea.github.io/observatorio-ia/"
URL_HERR = "https://claudiomlarrea.github.io/observatorio-ia/#herramientas"
URL_APP = "https://eph-analyzer.streamlit.app/"
URL_INDEC = "https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos"
URL_TIC = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-26-89"
URL_MAIL = "observatorioia@uccuyo.edu.ar"

GREEN = colors.HexColor("#044A30")
GREEN_BANNER = colors.HexColor("#064a38")
MAROON = colors.HexColor("#7a1532")
MAROON_DARK = colors.HexColor("#4a0c1f")
GRAY = colors.HexColor("#64748b")
TEXT = colors.HexColor("#1e293b")
WHITE = colors.white


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=WHITE,
            spaceAfter=12,
            alignment=TA_CENTER,
            leading=32,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontSize=13,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=10,
            leading=18,
        ),
        "cover_muted": ParagraphStyle(
            "cover_muted",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.Color(1, 1, 1, alpha=0.9),
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=16,
        ),
        "cover_body": ParagraphStyle(
            "cover_body",
            parent=base["Normal"],
            fontSize=10.5,
            textColor=colors.Color(1, 1, 1, alpha=0.92),
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=15,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=GREEN,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=MAROON_DARK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=TEXT,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=14,
            spaceAfter=4,
        ),
        "url": ParagraphStyle(
            "url",
            parent=base["Normal"],
            fontSize=9,
            textColor=GREEN,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontSize=8.5,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "step": ParagraphStyle(
            "step",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=MAROON_DARK,
            spaceBefore=8,
            spaceAfter=4,
        ),
    }


def _p(text: str, style: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles[style])


def _bullets(items: list[str], styles: dict[str, ParagraphStyle]) -> list:
    return [_p(f"• {item}", "bullet", styles) for item in items]


def _image(path: Path, width: float = 165 * mm, max_height: float = 95 * mm) -> Image | Spacer:
    if not path.is_file():
        return Spacer(1, 6)
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    if iw <= 0 or ih <= 0:
        return Spacer(1, 6)
    height = width * (ih / iw)
    if height > max_height:
        height = max_height
        width = height * (iw / ih)
    img = Image(str(path), width=width, height=height)
    img.hAlign = "CENTER"
    return img


def _url_block(label: str, url: str, styles: dict[str, ParagraphStyle]) -> list:
    return [
        _p(f"<b>{label}</b>", "body", styles),
        _p(f'<link href="{url}"><u>{url}</u></link>', "url", styles),
        Spacer(1, 4),
    ]


def _section(title: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return _p(title, "h1", styles)


def build_story(styles: dict[str, ParagraphStyle]) -> list:
    story: list = []

    story.append(Spacer(1, 48 * mm))
    if LOGO.is_file():
        logo = Image(str(LOGO), width=36 * mm, height=36 * mm)
        logo.hAlign = "CENTER"
        story += [logo, Spacer(1, 10 * mm)]
    story += [
        _p("UNIVERSIDAD CATÓLICA DE CUYO", "cover_muted", styles),
        _p("Observatorio de Inteligencia Artificial", "cover_subtitle", styles),
        Spacer(1, 8 * mm),
        _p("Instructivo Análisis EPH (INDEC)", "cover_title", styles),
        _p("Microdatos · Descriptivos · Exclusión digital · Modelos y SHAP", "cover_subtitle", styles),
        Spacer(1, 14 * mm),
        _p(
            "Guía paso a paso para docentes e investigadores:<br/>"
            "acceso, carga de bases EPH, modos guiado y experto,<br/>"
            "análisis, interpretabilidad y exportación de resultados.",
            "cover_body",
            styles,
        ),
        Spacer(1, 28 * mm),
        _p(URL_MAIL, "cover_muted", styles),
        PageBreak(),
    ]

    story.append(_section("Índice", styles))
    toc = [
        "1. ¿Qué es Análisis EPH (INDEC)?",
        "2. Cómo acceder desde la web de la UCCuyo",
        "3. Navegación de la app (tres módulos)",
        "4. Obtener microdatos del INDEC",
        "5. Carga manual de bases",
        "6. Modo guiado y modo experto",
        "7. Secciones de análisis",
        "8. Microdatos INDEC automático",
        "9. GEMEPH (gemelo territorial)",
        "10. Descargas y exportaciones",
        "11. Consejos útiles",
        "12. URLs de referencia",
    ]
    story += [_p(line, "bullet", styles) for line in toc]
    story.append(PageBreak())

    story.append(_section("1. ¿Qué es Análisis EPH (INDEC)?", styles))
    story += _bullets(
        [
            "Herramienta del Observatorio de IA (UCCuyo) para analizar microdatos de la "
            "<b>Encuesta Permanente de Hogares (EPH)</b> del INDEC y sus módulos TIC.",
            "Carga bases de hogares, individuos o módulo TIC en formatos típicos del INDEC.",
            "Ofrece descriptivos, desigualdad (Gini), correlaciones, índice de exclusión digital, "
            "regresión logística, árboles, Random Forest, clústeres e interpretabilidad SHAP.",
            "Incluye <b>modo guiado</b> (excl. digital como target) y <b>modo experto</b> "
            "(elegís variable dependiente y predictoras).",
            "También: descarga automática de microdatos + informes, y GEMEPH (31 aglomerados).",
            "Marco: Larrea (2025), inclusión digital y movilidad social (UNQ).",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("2. Cómo acceder desde la web de la UCCuyo", styles))
    story.append(
        _p(
            "Podés entrar directo con el enlace del paso 4, o por la ruta institucional:",
            "body",
            styles,
        )
    )
    for title, url, img, desc in [
        (
            "Paso 1 — Sitio de la Universidad",
            URL_UCCUYO,
            "01-uccuyo.jpg",
            "Ingresá a la UCCuyo. En Accesos o el menú, buscá "
            "<b>Observatorio de Inteligencia Artificial</b>.",
        ),
        (
            "Paso 2 — Observatorio de IA",
            URL_OBS,
            "02-observatorio-inicio.jpg",
            "Usá el menú o el botón <b>Herramientas de análisis</b>.",
        ),
        (
            "Paso 3 — Herramientas de análisis",
            URL_HERR,
            "03-herramientas-eph.jpg",
            "En la tarjeta <b>Análisis EPH (INDEC)</b> hacé clic en "
            "<b>Abrir análisis EPH</b> (también podrás bajar este instructivo en PDF).",
        ),
        (
            "Paso 4 — Análisis EPH",
            URL_APP,
            "04-eph-inicio.jpg",
            "Si la app estaba dormida (Streamlit), tocá "
            "<b>Yes, get this app back up!</b> y esperá unos segundos.",
        ),
    ]:
        story.append(_p(title, "step", styles))
        story += _url_block("URL:", url, styles)
        story.append(_p(desc, "body", styles))
        story.append(_image(ASSETS / img))
        story.append(_p(f"Figura: {title}", "caption", styles))
    story.append(PageBreak())

    story.append(_section("3. Navegación de la app (tres módulos)", styles))
    story += _bullets(
        [
            "<b>Página principal (eph-analyzer)</b> — carga manual de bases y 8 secciones de análisis.",
            "<b>Microdatos INDEC automatico</b> — descarga bases oficiales y genera informe Excel/Word.",
            "<b>GEMEPH</b> — gemelo sociodemográfico de los 31 aglomerados urbanos.",
            "El menú de páginas suele estar arriba a la izquierda (selector de Streamlit multipágina).",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("4. Obtener microdatos del INDEC", styles))
    story += _url_block("Bases EPH:", URL_INDEC, styles)
    story += _url_block("Módulo TIC:", URL_TIC, styles)
    story += _bullets(
        [
            "Descargá microdatos de <b>individuos</b> (obligatorio para la carga manual).",
            "La base de <b>hogares</b> es opcional si los individuos ya traen variables de hogar.",
            "Para exclusión digital / TIC conviene el <b>4.º trimestre (T4)</b>.",
            "Formatos aceptados: .xlsx, .xls, .csv, .txt, .zip, .parquet (y .dbf en el pipeline interno).",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("5. Carga manual de bases", styles))
    story += _bullets(
        [
            "En la barra lateral: <b>1️⃣ Cargar bases</b>.",
            "Subí <b>Base de individuos (obligatoria)</b> — una fila por persona "
            "(CODUSU + NRO_HOGAR + COMPONENTE).",
            "Opcional: <b>Base de hogares</b>.",
            "Clic en <b>🔄 Procesar archivos</b>.",
            "Verás un mensaje de éxito con filas × columnas.",
            "Luego aparecen <b>2️⃣ Modo</b> (Guiado / Experto) y <b>3️⃣ Sección</b>.",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("6. Modo guiado y modo experto", styles))
    story.append(_p("Modo Guiado", "h2", styles))
    story += _bullets(
        [
            "La app usa como target la <b>exclusión digital binarizada</b> "
            "(índice ≥ 0,5).",
            "Primero calculá el índice en la sección "
            "<b>Índice de exclusión digital</b>.",
            "Después elegís predictoras (edad, sexo, educación, región, ingresos, etc.).",
        ],
        styles,
    )
    story.append(_p("Modo Experto", "h2", styles))
    story += _bullets(
        [
            "Elegís cualquier variable dependiente (target).",
            "Seleccionás el subconjunto de predictoras.",
            "Podés binarizar con umbral o valores que cuentan como “1”.",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("7. Secciones de análisis", styles))
    story += _bullets(
        [
            "<b>Vista general</b> — filas, columnas, año/trimestre, primeras filas, tipos detectados.",
            "<b>Estadística descriptiva</b> — frecuencias, estadísticos numéricos, tabla cruzada "
            "(ponderadas por PONDERA).",
            "<b>Desigualdad</b> — Gini, Theil, razón Q5/Q1 sobre IPCF/ITF/P21/P47T; quintiles/deciles.",
            "<b>Correlaciones</b> — Pearson/Kendall/Spearman y alfa de Cronbach.",
            "<b>Índice de exclusión digital</b> — acceso + competencias + uso; botón "
            "<b>Calcular índice</b>; niveles de exclusión.",
            "<b>Modelos predictivos</b> — logística, árbol de decisión, Random Forest.",
            "<b>SHAP (XAI)</b> — interpretabilidad del modelo ya entrenado "
            "(summary / dependence).",
            "<b>Clústeres</b> — K-means o jerárquico (Ward) para segmentos.",
        ],
        styles,
    )
    story.append(
        _p(
            "<b>Flujo recomendado:</b> Vista general → Descriptiva / Desigualdad → "
            "Calcular índice → Modo Guiado → Logística → SHAP → (opcional) Clústeres.",
            "body",
            styles,
        )
    )
    story.append(PageBreak())

    story.append(_section("8. Microdatos INDEC automático", styles))
    story += _bullets(
        [
            "Abrí la página <b>Microdatos INDEC automatico</b>.",
            "Configurá: título del informe, módulo (TIC o sociodemográfico), ámbito "
            "(Argentina / Gran San Juan / aglomerado), año(s) y trimestre.",
            "Marcá los análisis a incluir (o “Todos”).",
            "Clic en <b>Ejecutar análisis</b>.",
            "Descargá <b>Excel</b> y/o <b>Word</b>.",
            "Si un año no está publicado en el mirror, la app avisará; usá carga manual.",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("9. GEMEPH (gemelo territorial)", styles))
    story += _bullets(
        [
            "Título: <b>GEMEPH</b> — gemelo sociodemográfico de 31 aglomerados urbanos.",
            "Configurá módulo, años y trimestre; opcionalmente <b>Actualizar GEMEPH</b>.",
            "Pestañas: Estado del gemelo · Mapa · Comparar aglomerados · Evolución · "
            "Escenarios (what-if).",
            "Exportá catálogo Excel/JSON, baseline Excel, informe Word o escenarios.",
            "Los escenarios son contrafactuales analíticos, no proyecciones oficiales del INDEC.",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("10. Descargas y exportaciones", styles))
    story += _bullets(
        [
            "En la carga manual: botones <b>⬇ Descargar Excel</b> por módulo.",
            "INDEC automático: Excel + Word del informe completo.",
            "GEMEPH: Excel, Word y JSON según el panel Exportar.",
            "Guardá siempre los archivos en tu computadora.",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("11. Consejos útiles", styles))
    story += _bullets(
        [
            "Para TIC / exclusión digital preferí el 4.º trimestre.",
            "Si la app dormida aparece, despertála y esperá 30–60 s.",
            "En Cloud hay límite de ~200 MB por archivo y recursos acotados: "
            "RF + SHAP pueden ser lentos.",
            "Empezá SHAP con pocas filas en el slider.",
            "Clustering jerárquico trabaja con submuestra interna por memoria.",
            "No versionés microdatos sensibles en repositorios públicos.",
            f"Consultas: {URL_MAIL}",
        ],
        styles,
    )
    story.append(PageBreak())

    story.append(_section("12. URLs de referencia", styles))
    for label, url in [
        ("Universidad Católica de Cuyo", URL_UCCUYO),
        ("Observatorio de IA", URL_OBS),
        ("Herramientas de análisis", URL_HERR),
        ("Análisis EPH (acceso directo)", URL_APP),
        ("Bases EPH — INDEC", URL_INDEC),
        ("Módulo TIC — INDEC", URL_TIC),
        (f"Correo: {URL_MAIL}", f"mailto:{URL_MAIL}"),
    ]:
        story += _url_block(label, url, styles)

    story += [
        Spacer(1, 20),
        _p(
            "Análisis EPH · Observatorio de Inteligencia Artificial · Universidad Católica de Cuyo",
            "caption",
            styles,
        ),
    ]
    return story


def _draw_cover_background(canvas, doc) -> None:
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(MAROON)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(MAROON_DARK)
    canvas.setFillAlpha(0.35)
    canvas.rect(w * 0.55, 0, w * 0.45, h, fill=1, stroke=0)
    canvas.setFillAlpha(1)
    canvas.setFillColor(GREEN_BANNER)
    canvas.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        w / 2,
        h - 9 * mm,
        "UNIVERSIDAD CATÓLICA DE CUYO  ·  OBSERVATORIO DE INTELIGENCIA ARTIFICIAL",
    )
    canvas.setFillColor(GREEN_BANNER)
    canvas.rect(0, 0, w, 6 * mm, fill=1, stroke=0)
    canvas.restoreState()


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 12 * mm, "Análisis EPH · Instructivo UCCuyo · Observatorio de IA")
    canvas.drawRightString(190 * mm, 12 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def _first_page(canvas, doc) -> None:
    _draw_cover_background(canvas, doc)


def main() -> None:
    styles = _styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OBS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="Instructivo Análisis EPH (INDEC)",
        author="Observatorio de Inteligencia Artificial - UCCuyo",
    )
    doc.build(build_story(styles), onFirstPage=_first_page, onLaterPages=_header_footer)

    shutil.copy2(OUTPUT, DOCS_OUTPUT)
    if OBS_OUTPUT.parent.is_dir():
        shutil.copy2(OUTPUT, OBS_OUTPUT)
    print(f"Generado: {OUTPUT}")
    print(f"Copia:    {DOCS_OUTPUT}")
    if OBS_OUTPUT.is_file():
        print(f"Obs:      {OBS_OUTPUT}")


if __name__ == "__main__":
    main()
