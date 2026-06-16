"""Configuración de variables EPH / MAUTIC (módulo TIC)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

# Trimestres con módulo TIC integrado (MAUTIC en Q4; variables presentes en microdatos)
YEARS_TIC = list(range(2017, 2023))  # 2017T4 .. 2022T4
TRIMESTER_TIC = 4

MIRROR_BASE = "https://github.com/holatam/data/raw/master/eph"

# Gran San Juan (diccionario INDEC / paquete eph)
AGLOMERADO_SAN_JUAN = 27

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
    "CH12",
    "NIVEL_ED",
    "ESTADO",
    "CAT_OCUP",
    "PP07H",
    "PONDERA",
    "ITF",
    "DECIFR",
    "IPCF",
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
