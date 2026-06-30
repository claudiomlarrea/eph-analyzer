"""Configuración de rutas y umbrales GEMEPH."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "gemeph"
PANEL_DIR = DATA_DIR / "panels"
BASELINE_DIR = DATA_DIR / "baselines"
CATALOG_DIR = DATA_DIR / "catalogs"

# Muestra mínima para mostrar KPIs sin advertencia fuerte
MIN_N_INDIVIDUOS = 150
MIN_N_ADVERTENCIA = 80

APP_NAME = "GEMEPH"
APP_SUBTITLE = "Gemelo sociodemográfico de los 31 aglomerados urbanos de Argentina"
