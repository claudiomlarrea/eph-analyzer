#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera artículo científico y presentación PowerPoint para Jornadas IA 2026."""

from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING, WD_UNDERLINE
from docx.oxml.ns import qn
from docx.shared import Pt
from pptx import Presentation

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "JORNADAS IA 2026"
TEMPLATE_WORD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/plantilla-resumen-jornadas-ia-2026__2__9baa.docx"
)
TEMPLATE_PPT = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/plantilla-presentacion-jornadas-ia-2026__3__c4ad.pptx"
)

TITULO = (
    "GEMEPH: gemelo digital sociodemográfico de la EPH-INDEC para simular "
    "exclusión digital, vulnerabilidad y brechas territoriales en Argentina"
)

INTRO = (
    "La Encuesta Permanente de Hogares (EPH) del INDEC es la principal fuente oficial para "
    "caracterizar condiciones de vida, empleo, educación y, en trimestres específicos, acceso "
    "y uso de tecnologías de la información y la comunicación (TIC) en el aglomerado urbano "
    "argentino. Sin embargo, la EPH describe predominantemente el estado observado de la "
    "sociedad: informa qué ocurre, pero no permite explorar de manera sistemática qué podría "
    "ocurrir si se modificaran variables estructurales —conectividad, educación, formalidad "
    "laboral— bajo un mismo marco metodológico y con trazabilidad reproducible. Esa limitación "
    "dificulta el diálogo entre investigación, docencia y toma de decisiones cuando se evalúan "
    "políticas públicas o intervenciones institucionales en materia de inclusión digital y "
    "cohesión social.\n\n"
    "El proyecto GEMEPH (Gemelo digital sociodemográfico de la EPH-INDEC) responde a esa "
    "brecha mediante el diseño, implementación y validación de un gemelo digital territorial "
    "que representa el baseline oficial de microdatos públicos y lo expone a escenarios "
    "contrafactuales (what-if). El artefacto no sustituye la estadística oficial ni pretende "
    "establecer relaciones causales experimentales; su aporte consiste en ofrecer una "
    "infraestructura computacional para anticipar magnitudes de cambio en indicadores "
    "sociodemográficos, comparar aglomerados urbanos y discutir combinaciones de medidas con "
    "evidencia anclada en la EPH.\n\n"
    "El objetivo general de este trabajo es presentar la arquitectura, la metodología y los "
    "resultados empíricos de GEMEPH sobre el panel 2022–2024 (cuarto trimestre, módulo TIC), "
    "incluyendo el baseline nacional, el catálogo de 31 aglomerados y tres escenarios ficticios "
    "de política. Los objetivos específicos son: (1) describir el pipeline de integración y "
    "normalización de microdatos EPH; (2) reportar indicadores ponderados de exclusión digital, "
    "vulnerabilidad social y movilidad social proxy; (3) caracterizar brechas territoriales; "
    "(4) comparar escenarios de conectividad inclusiva, expansión educativa y paquete integrado "
    "de formalización y educación; y (5) discutir implicancias para investigación aplicada, "
    "formación en inteligencia artificial (IA) y transferencia institucional desde el "
    "Observatorio de Inteligencia Artificial de la Universidad Católica de Cuyo (UCCuyo)."
)

MARCO = (
    "Los gemelos digitales surgieron en ingeniería y manufactura como representaciones "
    "dinámicas de sistemas físicos, pero su adopción en ciencias sociales y políticas públicas "
    "es reciente y heterogénea (Fuller et al., 2020; Jones et al., 2020; Rasheed et al., 2020; "
    "VanDerHorn & Mahadevan, 2021). En el ámbito urbano y sociodemográfico, Batty (2024) "
    "sostiene que el valor de un gemelo no reside solo en replicar datos, sino en habilitar "
    "experimentación virtual sobre configuraciones alternativas de variables e indicadores. "
    "Esa perspectiva resulta pertinente para analizar la exclusión digital en Argentina, "
    "donde la conectividad, el capital humano y las condiciones laborales interactúan con "
    "desigualdades territoriales persistentes.\n\n"
    "La literatura sobre brecha digital y movilidad social subraya que el acceso a internet "
    "no agota la noción de inclusión: importan usos, competencias, calidad de empleo y "
    "trayectorias educativas (OECD, 2024). La EPH-INDEC aporta variables observables para "
    "operacionalizar esas dimensiones en el ámbito urbano, aunque su lectura tradicional es "
    "estática y desagregada por publicaciones sucesivas. GEMEPH se inscribe en la tradición "
    "de Design Science Research (DSR): el producto central es un artefacto útil y evaluable "
    "(el gemelo), construido con criterios de reproducibilidad, trazabilidad y actualización "
    "periódica conforme el INDEC libere nuevas ondas.\n\n"
    "Desde el marco ético de la IA, UNESCO (2021) recomienda transparencia metodológica, "
    "explicabilidad y uso responsable de modelos predictivos en contextos sociales. GEMEPH "
    "incorpora esos principios al explicitar que los escenarios son simulaciones contrafactuales, "
    "al documentar palancas y deltas, y al publicar una plataforma abierta de consulta. "
    "En síntesis, el proyecto articula tres capas: dato oficial (EPH), modelado (IA/ML "
    "y estadística ponderada) y transferencia (plataforma, informes y formación)."
)

METODOLOGIA = (
    "El diseño del estudio es de investigación aplicada tecnológica, cuantitativa, "
    "descriptivo-analítica y longitudinal, con foco en la construcción y validación de un "
    "artefacto digital. La unidad de análisis combina el registro individual EPH y agregados "
    "territoriales para Argentina y 31 aglomerados urbanos.\n\n"
    "Fuentes y período. Se integraron microdatos públicos y anonimizados de la EPH (bases de "
    "hogar e individuo) correspondientes a 2022, 2023 y 2024, cuarto trimestre, con módulo "
    "TIC. El panel resultante comprende 114.280 registros individuales, con expansión "
    "poblacional aproximada de 68.511.362 personas. No se emplearon datos identificables ni "
    "fuentes privadas.\n\n"
    "Variables e indicadores. Se calcularon indicadores ponderados con el factor PONDERA del "
    "INDEC: índice de exclusión digital; porcentaje de exclusión digital alta; vulnerabilidad "
    "social; movilidad social proxy; tasa de ocupación; educación secundaria y superior "
    "completa; informalidad laboral; brechas de género en ocupación; brechas de internet por "
    "quintiles de ingreso; y perfiles por agrupamiento k-means. Las palancas de simulación "
    "fueron: porcentaje de hogares del quintil I con internet, proporción de personas con "
    "educación universitaria completa y proporción de empleo formal entre ocupados.\n\n"
    "Pipeline computacional. El procesamiento se realizó en Python con pandas, NumPy y "
    "scikit-learn (k-means y regresión logística para predicción de exclusión alta). "
    "Los paneles se persisten en Parquet; los reportes se exportan a Excel y Word mediante "
    "openpyxl y python-docx. La interfaz pública se desarrolló en Streamlit con visualizaciones "
    "Plotly y se despliega en https://eph-analyzer.streamlit.app/GEMEPH. El repositorio "
    "eph-analyzer integra los módulos gemeph/ e indec_auto/ para descarga, depuración y "
    "actualización automatizada de microdatos.\n\n"
    "Escenarios contrafactuales. Sobre un mismo baseline oficial se definieron tres escenarios "
    "ficticios: E1 (conectividad inclusiva: internet en quintil I al 99,0%, frente al 94,3% "
    "observado); E2 (expansión educativa: educación superior al 40,0%, frente al 19,6% oficial); "
    "y E3 (paquete integrado: empleo formal al 90,0%, educación superior al 30,0% e internet "
    "en quintil I al 97,3%). Cada escenario recalcula indicadores agregados y, cuando "
    "corresponde, la probabilidad predicha de exclusión digital alta.\n\n"
    "Validación. Se aplicaron seis controles: (1) calidad de microdatos; (2) coherencia de KPIs "
    "ponderados; (3) catálogo territorial comparable; (4) exportación reproducible; "
    "(5) contraste baseline–escenarios con deltas explícitos; y (6) alineación con los seis "
    "objetivos del proyecto institucional. Las limitaciones incluyen cobertura urbana de la EPH, "
    "disponibilidad del módulo TIC en trimestres específicos, naturaleza no causal de las "
    "simulaciones y dependencia del calendario de publicación del INDEC."
)

RESULTADOS = (
    "Baseline nacional. En la corrida de referencia, el índice de exclusión digital alcanza "
    "0,6205 y el 53,96% de la población se ubica en exclusión digital alta. La vulnerabilidad "
    "social es 0,2667 y la movilidad social proxy, 0,4774. La ocupación se sitúa en 58,62%; "
    "la educación superior completa, en 19,59%; y la informalidad entre ocupados, en 26,18%. "
    "La brecha de ocupación mujer–hombre es de −18,42 puntos porcentuales. Las palancas "
    "oficiales ancla de toda simulación son: internet en quintil I (94,3%), educación superior "
    "(19,6%) y empleo formal (73,8%).\n\n"
    "Brechas territoriales. El catálogo de 31 aglomerados evidencia heterogeneidad sustantiva. "
    "Los cinco aglomerados con mayor exclusión digital son Ushuaia–Río Grande (0,6298), "
    "Río Gallegos (0,6277), Partidos del Gran Buenos Aires (0,6270), Gran Resistencia (0,6267) "
    "y Jujuy–Palpalá (0,6246). En el extremo opuesto, Gran Córdoba presenta la exclusión más "
    "baja (0,5979). En vulnerabilidad social destacan Formosa (0,3090), Concordia (0,3086) y "
    "Santa Rosa–Toay (0,3025). Estas diferencias confirman que el baseline no es homogéneo y "
    "que el gemelo debe preservar la lectura territorial al simular.\n\n"
    "Escenario E1 — Conectividad inclusiva. Al elevar internet en el quintil de menores "
    "ingresos al 99,0%, la exclusión digital desciende marginalmente de 0,6205 a 0,6199 "
    "(Δ −0,0006) y el porcentaje de exclusión alta pasa de 53,96% a 53,82% (Δ −0,14 pp). "
    "La predicción de exclusión alta varía de 6,08% a 5,73%. La brecha de internet entre "
    "quintiles Q1 y Q5 se invierte de +1,15 pp a −3,57 pp. El efecto agregado es pequeño "
    "porque la cobertura oficial en el quintil bajo ya es elevada.\n\n"
    "Escenario E2 — Expansión educativa superior. Al portar educación superior al 40,0%, "
    "ese indicador aumenta 20,41 puntos porcentuales y la movilidad social proxy pasa de "
    "0,4774 a 0,5183 (Δ +0,0409). La exclusión digital agregada permanece en 0,6205 y la "
    "predicción de exclusión alta se mantiene en 6,08%. El escenario muestra que el canal "
    "educativo desplaza con fuerza indicadores de oportunidad relativa, aunque no borra "
    "automáticamente la exclusión digital agregada.\n\n"
    "Escenario E3 — Paquete integrado. Con empleo formal al 90,0%, educación superior al 30,0% "
    "e internet en quintil I al 97,3%, la educación superior aumenta 10,41 pp, la movilidad "
    "proxy alcanza 0,5125 (Δ +0,0351), la exclusión digital desciende levemente a 0,6201 "
    "y la predicción de exclusión alta pasa de 6,08% a 5,84%. E3 representa una combinación "
    "más realista de medidas y produce cambios equilibrados entre conectividad, capital humano "
    "y formalidad laboral.\n\n"
    "Plataforma y productos. GEMEPH se encuentra operativo en la URL pública citada, con "
    "consulta territorial, comparación de escenarios y exportación de resultados. Se generaron "
    "archivos Excel y Word con el catálogo de aglomerados y los tres escenarios, así como "
    "pipelines reproducibles para actualización periódica.\n\n"
    "Lectura integrada de escenarios. La comparación simultánea de E1, E2 y E3 sobre un mismo "
    "baseline permite discriminar canales de impacto sin confundir simulación con proyección "
    "oficial. E1 reduce la brecha quintil Q1–Q5 de internet pero apenas modifica exclusión "
    "agregada; E2 desplaza la movilidad proxy con fuerza aun sin alterar exclusión digital "
    "global; E3 combina mejoras moderadas en conectividad, educación y formalidad con un "
    "descenso leve de la probabilidad predicha de exclusión alta. Esta lectura diferenciada es "
    "el aporte analítico central del gemelo para investigadores y tomadores de decisión."
)

DISCUSION = (
    "Los resultados permiten formular tres mensajes centrales para la discusión académica y "
    "la transferencia institucional. Primero, GEMEPH demuestra que es posible construir un "
    "gemelo digital sociodemográfico sobre microdatos oficiales abiertos, con trazabilidad "
    "metodológica y despliegue público, sin sustituir la autoridad estadística del INDEC. "
    "El artefacto cumple la función de laboratorio computacional para la ciencia social "
    "aplicada y la formación en IA responsable.\n\n"
    "Segundo, la comparación de E1, E2 y E3 sobre un mismo baseline evidencia que no todos "
    "los canales de política producen el mismo tipo de impacto. Cuando la conectividad en "
    "hogares de menores ingresos está cerca de la saturación, intervenciones exclusivamente "
    "digitales arrojan retornos decrecientes sobre indicadores agregados (E1). En cambio, "
    "la expansión educativa altera con claridad la movilidad social proxy (E2), y los paquetes "
    "integrados generan ajustes más equilibrados entre exclusión predicha, educación y "
    "formalidad (E3). El gemelo ayuda a evitar sobreprometer efectos de una sola palanca y "
    "a priorizar combinaciones de medidas en el debate público.\n\n"
    "Tercero, la dimensión territorial confirma que políticas nacionales homogéneas pueden "
    "enmascarar brechas locales relevantes. Aglomerados con alta exclusión digital no siempre "
    "coinciden con los de mayor vulnerabilidad social, lo que refuerza la necesidad de "
    "catálogos comparables y actualizables. GEMEPH ofrece esa capacidad mediante un pipeline "
    "modular que incorpora nuevas ondas EPH sin rediseño estructural.\n\n"
    "En términos de limitaciones, debe insistirse en que los escenarios son contrafactuales: "
    "no constituyen proyecciones oficiales ni inferencia causal. La EPH cubre el aglomerado "
    "urbano y el módulo TIC no está disponible en todos los trimestres. Los modelos predictivos "
    "pueden perder estabilidad ante cambios estructurales abruptos. Aun con ello, el proyecto "
    "aporta evidencia reproducible, productos tecnológicos y una línea institucional de "
    "investigación en gemelos digitales e IA aplicada a las ciencias sociales en la UCCuyo.\n\n"
    "Como proyección, se prevé la publicación de artículos académicos, la presentación en "
    "jornadas institucionales —incluidas las 1.° Jornadas Internas de IA 2026—, la ampliación "
    "de escenarios y la articulación con áreas de gobierno interesadas en exclusión digital "
    "y cohesión social. GEMEPH consolida al Observatorio de Inteligencia Artificial como "
    "espacio de innovación metodológica con pertinencia regional y nacional.\n\n"
    "Desde la perspectiva de las Jornadas de IA, el caso ilustra cómo la universidad puede "
    "desarrollar artefactos de IA con datos públicos, código abierto y gobernanza explícita de "
    "limitaciones. La experiencia es transferible a otras unidades académicas que busquen "
    "incorporar gemelos digitales en docencia de posgrado, semilleros de investigación o "
    "convenios de extensión con organismos provinciales. La actualización periódica del panel "
    "convierte a GEMEPH en un observatorio dinámico: cada nueva publicación del INDEC permite "
    "recalcular baselines, reordenar rankings territoriales y reevaluar escenarios sin "
    "reconstruir la arquitectura del sistema."
)

REFERENCIAS = (
    "Batty, M. (2024). The future of digital twins. Environment and Planning B: Urban Analytics "
    "and City Science.\n"
    "Fuller, A., Fan, Z., Day, C., & Barlow, C. (2020). Digital twin: Enabling technologies, "
    "challenges and open research. IEEE Access, 8, 108952–108971. "
    "https://doi.org/10.1109/ACCESS.2020.2998358\n"
    "Instituto Nacional de Estadística y Censos [INDEC]. (2024). Encuesta Permanente de Hogares "
    "(EPH): Bases de microdatos y metodología. https://www.indec.gob.ar\n"
    "Jones, D., Snider, C., Nassehi, A., Yon, J., & Hicks, B. (2020). Characterising the Digital "
    "Twin: A systematic literature review. CIRP Journal of Manufacturing Science and Technology, "
    "29, 36–52.\n"
    "Organisation for Economic Co-operation and Development [OECD]. (2024). OECD digital economy "
    "outlook 2024. OECD Publishing.\n"
    "Rasheed, A., San, O., & Kvamsdal, T. (2020). Digital twin: Values, challenges and enablers "
    "from a modeling perspective. IEEE Access, 8, 21980–22012.\n"
    "UNESCO. (2021). Recommendation on the ethics of artificial intelligence. UNESCO.\n"
    "VanDerHorn, E., & Mahadevan, S. (2021). Digital twin: Generalization, characterization and "
    "implementation. Decision Support Systems, 145, 113524."
)

PPT_CONTENT = {
    1: (
        f"{TITULO}\n\n"
        "Autores: C. Larrea Arnau¹, J. La Malfa², J. Coria¹, S. Young¹\n"
        "Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo\n"
        "observatorioia@uccuyo.edu.ar"
    ),
    2: (
        "¿Qué problema aborda GEMEPH?\n"
        "• Construir un gemelo digital sociodemográfico sobre microdatos oficiales EPH-INDEC\n"
        "• Simular escenarios what-if de conectividad, educación y formalidad laboral\n"
        "• Comparar exclusión digital, vulnerabilidad y brechas entre 31 aglomerados urbanos\n"
        "• Aportar evidencia reproducible para investigación y decisión en la UCCuyo"
    ),
    3: (
        "¿Cómo se hizo?\n"
        "• Panel EPH 2022–2024 (T4, módulo TIC): 114.280 registros; 31 aglomerados + nacional\n"
        "• Python, scikit-learn, Streamlit; indicadores ponderados (PONDERA)\n"
        "• Palancas: internet quintil I, educación superior, empleo formal\n"
        "• Tres escenarios ficticios (E1 conectividad; E2 educación; E3 paquete integrado)\n"
        "• Plataforma pública: eph-analyzer.streamlit.app/GEMEPH"
    ),
    4: (
        "¿Qué se obtuvo?\n"
        "• Baseline: exclusión digital 0,6205; 53,96% exclusión alta; movilidad proxy 0,4774\n"
        "• Brecha territorial: mayor exclusión en Ushuaia–Río Grande; menor en Gran Córdoba\n"
        "• E1: efecto marginal de conectividad (cobertura quintil bajo ya en 94,3%)\n"
        "• E2: educación al 40% eleva movilidad proxy +0,0409\n"
        "• E3: paquete integrado reduce exclusión predicha 6,08% → 5,84%"
    ),
    5: (
        "Mensajes clave\n"
        "• El gemelo no reemplaza al INDEC: simula sobre el dato oficial con trazabilidad\n"
        "• Una sola palanca digital aporta retornos decrecientes; educación y paquetes integrados "
        "mueven más indicadores de oportunidad\n"
        "• Infraestructura abierta del Observatorio de IA para docencia, investigación y "
        "actualización con cada onda EPH"
    ),
    6: (
        "Gracias\n\n"
        "Preguntas y comentarios\n"
        "observatorioia@uccuyo.edu.ar\n\n"
        "GEMEPH · eph-analyzer.streamlit.app/GEMEPH"
    ),
}


def _set_arial(run, size: int = 11, bold: bool = False, underline=None):
    run.bold = bold
    if underline is not None:
        run.underline = underline
    run.font.name = "Arial"
    run.font.size = Pt(size)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), "Arial")
    r_fonts.set(qn("w:hAnsi"), "Arial")


def _set_para_format(paragraph, *, align=None, space_after=6, line_spacing=1.5):
    pf = paragraph.paragraph_format
    pf.space_after = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if align is not None:
        paragraph.alignment = align


def _word_count(*texts: str) -> int:
    return sum(len(t.split()) for t in texts)


def build_word(out_path: Path) -> int:
    shutil.copy2(TEMPLATE_WORD, out_path)
    doc = Document(out_path)

    # Eliminar párrafo de instrucciones (índice 0)
    if doc.paragraphs and "INSTRUCCIONES" in doc.paragraphs[0].text:
        p = doc.paragraphs[0]._element
        p.getparent().remove(p)

    # Limpiar párrafos de plantilla restantes (conservar encabezado en tabla)
    body_paras = list(doc.paragraphs)
    for para in body_paras:
        txt = para.text.strip()
        if txt:
            p_el = para._element
            p_el.getparent().remove(p_el)

    def add_para(text: str, *, bold=False, size=11, space_after=6):
        p = doc.add_paragraph()
        _set_para_format(p, space_after=space_after)
        run = p.add_run(text)
        _set_arial(run, size=size, bold=bold)
        return p

    add_para(TITULO, bold=True, size=12, space_after=10)

    # Autores con expositor subrayado
    p_auth = doc.add_paragraph()
    _set_para_format(p_auth, space_after=4)
    r1 = p_auth.add_run("C. ")
    _set_arial(r1)
    r2 = p_auth.add_run("Larrea Arnau")
    _set_arial(r2, underline=WD_UNDERLINE.SINGLE)
    r3 = p_auth.add_run("¹, J. La Malfa², J. Coria¹, S. Young¹")
    _set_arial(r3)

    add_para("Observatorio de Inteligencia Artificial — Universidad Católica de Cuyo", space_after=2)
    add_para("observatorioia@uccuyo.edu.ar", space_after=14)

    sections = [
        ("Introducción", INTRO),
        ("Marco y antecedentes", MARCO),
        ("Metodología", METODOLOGIA),
        ("Resultados", RESULTADOS),
        ("Discusión y conclusiones", DISCUSION),
        ("Referencias", REFERENCIAS),
    ]
    for title, body in sections:
        add_para(title, bold=True, size=11, space_after=6)
        if title == "Referencias":
            for ref in body.strip().split("\n"):
                if ref.strip():
                    add_para(ref.strip(), space_after=4)
        else:
            for block in body.split("\n\n"):
                add_para(block, space_after=8)

  # Pie institucional
    add_para(
        "Artículo de 2.000 palabras · Cierre: 10 de septiembre de 2026 · "
        "Observatorio de IA — https://claudiomlarrea.github.io/observatorio-ia/",
        space_after=0,
    )

    doc.save(out_path)
    wc = _word_count(INTRO, MARCO, METODOLOGIA, RESULTADOS, DISCUSION)
    return wc


def _set_shape_text(shape, text: str) -> None:
    """Reemplaza texto preservando el marco de la plantilla (sin clear())."""
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


def build_ppt(out_path: Path) -> None:
    shutil.copy2(TEMPLATE_PPT, out_path)
    prs = Presentation(out_path)
    for idx, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.name == "Rounded Rectangle 9" and idx in PPT_CONTENT:
                _set_shape_text(shape, PPT_CONTENT[idx])
    prs.save(out_path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    word_out = OUT_DIR / "Investigacion_UCCuyo_Larrea_GEMEPH_GemeloDigitalEPH.docx"
    ppt_out = OUT_DIR / "Investigacion_UCCuyo_Larrea_GEMEPH.pptx"
    ppt_alt = OUT_DIR / "Presentacion_GEMEPH_Jornadas_IA_2026.pptx"

    wc = build_word(word_out)
    build_ppt(ppt_out)
    shutil.copy2(ppt_out, ppt_alt)

    print(f"Word: {word_out}")
    print(f"  Palabras (cuerpo): {wc}")
    print(f"PPT:  {ppt_out}")
    print(f"PPT:  {ppt_alt}")
    print(f"  Diapositivas: 6")


if __name__ == "__main__":
    main()
