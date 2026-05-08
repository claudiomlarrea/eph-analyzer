"""
Detector del tipo de base EPH a partir de las columnas presentes.

Reconoce cuatro tipos:
    - "hogar"           : base de hogares de la EPH
    - "individuo"       : base de individuos de la EPH
    - "tic_hogar"       : módulo TIC - hogar
    - "tic_individual"  : módulo TIC - individuo
    - "merged"          : base que combina hogar + individuo (ya joineada)
    - "desconocido"     : no coincide con los patrones esperados

El detector NO lee el archivo: solo recibe una lista/secuencia de nombres
de columna. Esto permite usarlo después de cualquier loader.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DICCIONARIO_PATH = Path(__file__).parent.parent / "diccionario" / "eph_variables.json"


@dataclass
class DetectionResult:
    """Resultado de la detección de tipo de archivo."""

    tipo: str
    confianza: float
    razon: str
    columnas_clave_encontradas: list[str] = field(default_factory=list)
    columnas_tipicas_encontradas: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Tipo detectado: {self.tipo.upper()} "
            f"(confianza={self.confianza:.0%}) — {self.razon}"
        )


class FileDetector:
    """Detecta el tipo de base EPH usando los fingerprints del diccionario."""

    def __init__(self, diccionario_path: Path | str = DICCIONARIO_PATH):
        with open(diccionario_path, "r", encoding="utf-8") as f:
            self.diccionario = json.load(f)
        self.fingerprints = self.diccionario["fingerprints"]

    def detectar(self, columnas: Iterable[str]) -> DetectionResult:
        cols = {str(c).strip().upper() for c in columnas}

        scores: dict[str, dict] = {}
        for tipo, fp in self.fingerprints.items():
            if tipo.startswith("_"):
                continue

            obligatorias = {c.upper() for c in fp.get("obligatorias", [])}
            tipicas = {c.upper() for c in fp.get("tipicas", [])}
            patron = fp.get("patron_columna")
            min_tipicas = fp.get("minimo_match_tipicas", 1)

            obligatorias_ok = obligatorias.issubset(cols)
            tipicas_match = sorted(tipicas & cols)
            patron_match = (
                [c for c in cols if re.search(patron, c)] if patron else []
            )

            score = 0.0
            if obligatorias_ok:
                score += 0.5
            if len(tipicas_match) >= min_tipicas:
                score += 0.3 * min(1.0, len(tipicas_match) / max(len(tipicas), 1))
            if patron and patron_match:
                score += 0.2 * min(1.0, len(patron_match) / 3)

            scores[tipo] = {
                "score": score,
                "obligatorias_ok": obligatorias_ok,
                "tipicas_match": tipicas_match,
                "patron_match": patron_match,
            }

        tiene_componente = "COMPONENTE" in cols
        tiene_tic_hogar = bool(
            scores["tic_hogar"]["tipicas_match"]
            or scores["tic_hogar"]["patron_match"]
        )
        tiene_tic_individual = bool(
            scores["tic_individual"]["tipicas_match"]
            or scores["tic_individual"]["patron_match"]
        )

        if tiene_componente and tiene_tic_individual:
            mejor_tipo = "tic_individual"
        elif tiene_componente:
            mejor_tipo = "individuo"
        elif tiene_tic_hogar:
            mejor_tipo = "tic_hogar"
        elif scores["hogar"]["obligatorias_ok"]:
            mejor_tipo = "hogar"
        else:
            mejor_tipo = max(scores, key=lambda t: scores[t]["score"])

        mejor = scores[mejor_tipo]

        if mejor["score"] < 0.5:
            return DetectionResult(
                tipo="desconocido",
                confianza=mejor["score"],
                razon=(
                    "No se reconoce el tipo de archivo. "
                    f"Mejor candidato: {mejor_tipo} (score={mejor['score']:.2f})."
                ),
                columnas_clave_encontradas=mejor["tipicas_match"],
                advertencias=[
                    "El archivo podría no ser una base EPH estándar, "
                    "o tener nombres de columna no esperados."
                ],
            )

        razon_partes = []
        if mejor["obligatorias_ok"]:
            razon_partes.append("claves identificatorias presentes")
        if mejor["tipicas_match"]:
            razon_partes.append(
                f"{len(mejor['tipicas_match'])} variables típicas encontradas"
            )
        if mejor["patron_match"]:
            razon_partes.append(
                f"{len(mejor['patron_match'])} columnas con patrón "
                f"'{self.fingerprints[mejor_tipo].get('patron_columna')}'"
            )

        return DetectionResult(
            tipo=mejor_tipo,
            confianza=min(1.0, mejor["score"]),
            razon=", ".join(razon_partes) or "coincidencia parcial",
            columnas_clave_encontradas=list(
                {c.upper() for c in self.fingerprints[mejor_tipo].get("obligatorias", [])}
                & cols
            ),
            columnas_tipicas_encontradas=mejor["tipicas_match"],
        )

    def describir_columna(self, columna: str) -> dict | None:
        """Devuelve la metadata de una columna, si está en el diccionario."""
        col = columna.strip().upper()
        for seccion, contenido in self.diccionario.items():
            if seccion.startswith("_") or seccion in {"claves_unicas", "fingerprints"}:
                continue
            if isinstance(contenido, dict) and col in contenido:
                return {"seccion": seccion, **contenido[col]}
        return None
