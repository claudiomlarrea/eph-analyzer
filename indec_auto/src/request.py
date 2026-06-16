"""Definición y parseo de solicitudes de análisis."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import AGLOMERADO_SAN_JUAN, ANALISIS_DISPONIBLES, TRIMESTER_TIC, YEARS_TIC


@dataclass
class SolicitudAnalisis:
    """Parámetros de una solicitud de análisis EPH."""

    titulo: str = "Analizador automático EPH"
    years: list[int] = field(default_factory=lambda: list(YEARS_TIC))
    trimestre: int = TRIMESTER_TIC
    ambito: str = "nacional"  # nacional | san_juan | aglomerado
    aglomerado: int | None = None
    analisis: list[str] = field(default_factory=lambda: ["todos"])
    excel: bool = True
    word: bool = True
    force_download: bool = False

    @property
    def label(self) -> str:
        if self.ambito == "san_juan":
            return "gran_san_juan"
        if self.ambito == "aglomerado" and self.aglomerado is not None:
            return f"aglomerado_{self.aglomerado}"
        return "nacional"

    @property
    def aglomerado_filtro(self) -> int | None:
        if self.ambito == "san_juan":
            return AGLOMERADO_SAN_JUAN
        if self.ambito == "aglomerado":
            return self.aglomerado
        return None

    @property
    def analisis_resueltos(self) -> set[str]:
        items = {a.strip().lower() for a in self.analisis}
        if "todos" in items:
            return {a for a in ANALISIS_DISPONIBLES if a != "todos"}
        unknown = items - set(ANALISIS_DISPONIBLES)
        if unknown:
            raise ValueError(
                f"Análisis no reconocidos: {unknown}. "
                f"Opciones: {', '.join(ANALISIS_DISPONIBLES)}"
            )
        return items

    @classmethod
    def desde_json(cls, path: Path) -> SolicitudAnalisis:
        data = json.loads(path.read_text(encoding="utf-8"))
        years = data.get("years")
        if isinstance(years, str) and "-" in years:
            y0, y1 = map(int, years.split("-"))
            years = list(range(y0, y1 + 1))
        return cls(
            titulo=data.get("titulo", cls.titulo),
            years=years or list(YEARS_TIC),
            trimestre=int(data.get("trimestre", TRIMESTER_TIC)),
            ambito=data.get("ambito", "nacional"),
            aglomerado=data.get("aglomerado"),
            analisis=data.get("analisis", ["todos"]),
            excel=bool(data.get("excel", True)),
            word=bool(data.get("word", True)),
            force_download=bool(data.get("force_download", False)),
        )

    def periodo_texto(self) -> str:
        return f"{min(self.years)}–{max(self.years)} (T{self.trimestre})"
