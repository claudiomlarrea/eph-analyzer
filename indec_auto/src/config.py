"""Configuración de variables EPH / MAUTIC (módulo TIC)."""

from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

# Ventana amplia para EPH base (se puede ajustar desde UI/JSON)
YEAR_MIN = 2003
YEAR_MAX = datetime.now().year
YEARS_BASE = list(range(YEAR_MIN, YEAR_MAX + 1))

# Trimestres con módulo TIC integrado (MAUTIC en Q4; variables presentes en microdatos)
YEARS_TIC = list(range(2017, YEAR_MAX + 1))
TRIMESTER_TIC = 4

MIRROR_BASE = "https://github.com/holatam/data/raw/master/eph"

# Gran San Juan (diccionario INDEC / paquete eph)
AGLOMERADO_SAN_JUAN = 27
AGLOMERADO_MENDOZA = 10
AGLOMERADO_SAN_LUIS = 26

# Gran Cuyo urbano (EPH): Mendoza, San Luis y San Juan
AGLOMERADOS_CUYO = (AGLOMERADO_MENDOZA, AGLOMERADO_SAN_LUIS, AGLOMERADO_SAN_JUAN)

# Preset del proyecto UCCuyo: observación empírica de brecha digital y movilidad social en Cuyo
# Período de ejecución del proyecto: 2025–2026; ventana empírica de microdatos: 2024–2026
PROYECTO_CUYO_YEAR_MIN = 2024
PROYECTO_CUYO_YEAR_MAX = YEAR_MAX
PROYECTO_CUYO_TRIMESTRES = (1, 2, 3, 4)
PROYECTO_CUYO_TRIMESTRE = TRIMESTER_TIC  # preferido para variables TIC (MAUTIC)
PROYECTO_CUYO_TITULO = (
    "Brecha digital y movilidad social en Cuyo: "
    "observación empírica con microdatos EPH/TIC e inteligencia artificial explicable (2024–2026)"
)

REGIONES = {
    1: "GBA",
    40: "Pampeana",
    41: "Noreste",
    42: "Noroeste",
    43: "Cuyo",
    44: "Patagonia",
}

# Hogar — acceso (MAUTIC)
HOGAR_TIC = ["V10", "V11", "V12", "V14", "V15"]
# Individuo — uso TIC (sufijo _M)
IND_TIC = ["V10_M", "V11_M", "V12_M", "V18_M", "V19_AM"]

# Sociodemográficas y movilidad proxy
IND_CORE = [
    "CODUSU",
    "AGLOMERADO",
    "REGION",
    "CH04",
    "CH06",
    "CH10",  # asistencia educativa (para NEET)
    "CH12",
    "NIVEL_ED",
    "ESTADO",
    "CAT_OCUP",
    "PP07H",
    "PONDERA",
    "ITF",
    "DECIFR",
    "IPCF",
    "RELACION",  # parentesco / jefatura de hogar
]

# Análisis disponibles para solicitudes del usuario
ANALISIS_DISPONIBLES = (
    "descriptivos",
    "frecuencias",
    "correlaciones",
    "logistica",
    "cluster",
    "shap",
    "todos",
)

HOGAR_CORE = ["CODUSU", "AGLOMERADO", "REGION", "ITF", "DECIFR", "IPCF", "PONDIH"] + HOGAR_TIC
