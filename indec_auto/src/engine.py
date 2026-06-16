"""Motor principal: descarga INDEC → preparación → análisis → reportes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .analyze import ejecutar_analisis
from .config import OUTPUT_DIR
from .download import download_panel_tic
from .prepare import build_analysis_frame, validate_microdata
from .report import exportar_excel, exportar_word
from .request import SolicitudAnalisis


def procesar_solicitud(solicitud: SolicitudAnalisis) -> dict:
    """Ejecuta una solicitud completa y devuelve metadatos de salida."""
    out_dir = OUTPUT_DIR / solicitud.label
    out_dir.mkdir(parents=True, exist_ok=True)

    hogar, individual = download_panel_tic(
        years=solicitud.years,
        trimester=solicitud.trimestre,
        force=solicitud.force_download,
    )

    df = build_analysis_frame(hogar, individual, aglomerado=solicitud.aglomerado_filtro)
    validacion = validate_microdata(df)

    resultado = ejecutar_analisis(
        df,
        tipos=solicitud.analisis_resueltos,
        label=solicitud.label,
        out_dir=out_dir,
    )

    meta = {
        "titulo": solicitud.titulo,
        "ambito": solicitud.label,
        "periodo": solicitud.periodo_texto(),
        "generado": datetime.now().isoformat(timespec="seconds"),
        "registros": len(df),
        "validacion": validacion,
        "analisis": sorted(solicitud.analisis_resueltos),
        "fuente": "INDEC — EPH (hogar, individuo, módulo TIC/MAUTIC)",
    }
    resultado["meta"] = meta

    archivos: dict[str, str] = {}

    if solicitud.excel:
        xlsx = exportar_excel(resultado, out_dir / f"reporte_{solicitud.label}.xlsx")
        archivos["excel"] = str(xlsx)

    if solicitud.word:
        docx = exportar_word(
            resultado,
            out_dir / f"informe_{solicitud.label}.docx",
            titulo=solicitud.titulo,
            periodo=solicitud.periodo_texto(),
            ambito=solicitud.label,
        )
        archivos["word"] = str(docx)

    resultado["archivos"] = archivos
    resultado["directorio"] = str(out_dir)
    return resultado
