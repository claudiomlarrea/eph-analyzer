"""
Helper para mostrar nombres humanos de variables EPH en la UI.

Usa el diccionario `eph_variables.json` y agrega nombres para las
variables derivadas que crea el `DataCleaner`.

Funciones principales:
    - `nombre_variable(col)`           → "Edad"
    - `nombre_completo(col)`           → "Edad (CH06)"
    - `renombrar_dataframe(df, ...)`   → rename de columnas/índice
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DICCIONARIO_PATH = Path(__file__).parent.parent / "diccionario" / "eph_variables.json"

NOMBRES_DERIVADAS = {
    "GRUPO_ETARIO": "Grupo etario",
    "ES_JEFE_HOGAR": "Es jefe/a de hogar",
    "OCUPADO": "Está ocupado/a",
    "DESOCUPADO": "Está desocupado/a",
    "INACTIVO": "Es inactivo/a",
    "EDUC_SUPERIOR_COMPLETA": "Educación superior completa",
    "EDUC_SECUNDARIA_COMPLETA_O_MAS": "Secundaria completa o más",
    "QUINTIL_IPCF": "Quintil de IPCF",
    "INDICE_EXCLUSION": "Índice de exclusión digital",
    "NIVEL_EXCLUSION": "Nivel de exclusión digital",
    "DIM_ACCESO": "Dim.: acceso material a TIC",
    "DIM_COMPETENCIAS": "Dim.: competencias digitales",
    "DIM_USO": "Dim.: uso significativo de TIC",
    # Variables derivadas del analizador automático (indec_auto)
    "ANIO": "Año",
    "TRIMESTRE": "Trimestre",
    "EDAD": "Edad (años)",
    "SEXO_MUJER": "Es mujer (1=sí)",
    "SECUNDARIO_COMPLETO": "Secundario completo (proxy)",
    "SUPERIOR": "Educación superior (proxy)",
    "ASALARIADO_REGISTRADO": "Asalariado registrado",
    "INFORMAL_PROXY": "Trabajo informal (proxy)",
    "QUINTIL_BAJO": "Quintil bajo de ingreso",
    "QUINTIL_ALTO": "Quintil alto de ingreso",
    "DECIL_INGRESO": "Decil de ingreso",
    "SCORE_MOVILIDAD_PROXY": "Score de movilidad social (proxy)",
    "VULNERABILIDAD_SOCIAL": "Índice de vulnerabilidad social",
    "VULNERABILIDAD_ALTA": "Vulnerabilidad social alta",
    "EXCLUSION_DIGITAL_ALTA": "Exclusión digital alta",
    "IDX_EXCLUSION_DIGITAL": "Índice de exclusión digital",
    "IDX_ACCESO": "Índice de exclusión — acceso",
    "IDX_USO": "Índice de exclusión — uso",
    "EXCL_SIN_PC": "Sin PC en el hogar",
    "EXCL_SIN_INTERNET_HOGAR": "Sin internet en el hogar",
    "EXCL_SIN_USO_CEL": "No usa celular",
    "EXCL_SIN_USO_PC": "No usa PC",
    "EXCL_SIN_USO_INTERNET": "No usa internet",
    "REGION_NOMBRE": "Región",
    "AGLOMERADO_NOMBRE": "Aglomerado urbano",
    "NOMBRE_CLUSTER": "Nombre del clúster",
    "PCT_EXCLUSION_DIGITAL_ALTA": "% con exclusión digital alta",
    "PCT_SECUNDARIO_COMPLETO": "% con secundario completo",
    "PCT_SUPERIOR": "% con educación superior",
    "PCT_OCUPADO": "% ocupado/a",
    "PCT_INFORMAL": "% informal (entre ocupados)",
    "ITF_MEDIANO_PONDERADO": "ITF mediano ponderado",
    "PESO_RELATIVO_PCT": "Peso relativo SHAP (%)",
}

NOMBRES_FRECUENTES = {
    "CODUSU": "ID de vivienda",
    "NRO_HOGAR": "N° de hogar",
    "COMPONENTE": "N° de componente",
    "ANO4": "Año",
    "TRIMESTRE": "Trimestre",
    "REGION": "Región",
    "AGLOMERADO": "Aglomerado urbano",
    "PONDERA": "Ponderador (general)",
    "PONDIH": "Ponderador (ingresos hogar)",
    "PONDII": "Ponderador (ingresos individuales)",
    "PONDIIO": "Ponderador (ocupación principal)",
    "MAS_500": "Aglomerado de más de 500 mil hab.",
    "REALIZADA": "Encuesta realizada",
    "H15": "Encuesta efectiva (jefe presente)",
    "CH03": "Relación con jefe/a de hogar",
    "CH04": "Sexo",
    "CH05": "Fecha de nacimiento",
    "CH06": "Edad (años)",
    "CH07": "Estado civil",
    "CH08": "Cobertura médica",
    "CH09": "Sabe leer y escribir",
    "CH10": "Asiste o asistió a un establecimiento educativo",
    "CH11": "Establecimiento educativo (público/privado)",
    "CH12": "Nivel educativo cursado",
    "CH13": "Finalizó ese nivel",
    "CH14": "Último año aprobado",
    "CH15": "Lugar de nacimiento",
    "NIVEL_ED": "Nivel educativo (recodificado)",
    "ESTADO": "Condición de actividad",
    "CAT_OCUP": "Categoría ocupacional",
    "CAT_INAC": "Categoría de inactividad",
    "P21": "Ingreso de la ocupación principal",
    "P47T": "Ingreso total individual",
    "TOT_P12": "Otros ingresos no laborales",
    "ITF": "Ingreso total familiar",
    "IPCF": "Ingreso per cápita familiar",
    "DECCFR": "Decil regional de IPCF",
    "DECIFR": "Decil regional de ingreso familiar",
    "IV1": "Tipo de vivienda",
    "IV2": "Cantidad de ambientes",
    "IV3": "Material de pisos",
    "IV4": "Material de techos",
    "IV6": "Tiene agua",
    "IV7": "Procedencia del agua",
    "IV8": "Tiene baño",
    "IV9": "Baño dentro de la vivienda",
    "IV10": "Tiene desagüe",
    "IX_TOT": "Tamaño del hogar (miembros)",
    "IX_MEN10": "Miembros menores de 10 años",
    "IX_MAYEQ10": "Miembros de 10 años o más",
    "II1": "Habitaciones para dormir",
    "II7": "Régimen de tenencia",
    "IH_II_01": "TIC: hogar - teléfono fijo",
    "IH_II_02": "TIC: hogar - teléfono celular",
    "IH_II_03": "TIC: hogar - computadora",
    "IH_II_04": "TIC: hogar - internet",
    "IP_III_04": "TIC: persona - usa internet",
    "IP_III_05": "TIC: persona - usa computadora",
    "IP_III_06": "TIC: persona - usa celular",
}


@lru_cache(maxsize=1)
def _cargar_diccionario() -> dict:
    try:
        with open(DICCIONARIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=2048)
def nombre_variable(col: str) -> str:
    """
    Devuelve el nombre humano de una variable.

    Estrategia:
        1. Variable derivada conocida (ej. INDICE_EXCLUSION).
        2. Mapeo manual rápido (NOMBRES_FRECUENTES).
        3. Diccionario JSON (campo `desc`).
        4. Si es one-hot (REGION_41, CH04_2), arma "Región = 41".
        5. Si termina en _LABEL: "<nombre> (etiqueta)".
        6. Fallback: el mismo código.
    """
    if col is None:
        return ""
    c = str(col).strip()
    cu = c.upper()

    if cu in NOMBRES_DERIVADAS:
        return NOMBRES_DERIVADAS[cu]
    if cu in NOMBRES_FRECUENTES:
        return NOMBRES_FRECUENTES[cu]

    if cu.endswith("_LABEL"):
        base = cu[:-6]
        return f"{nombre_variable(base)} (etiqueta)"

    diccionario = _cargar_diccionario()
    for seccion, contenido in diccionario.items():
        if seccion.startswith("_") or seccion in {"claves_unicas", "fingerprints"}:
            continue
        if isinstance(contenido, dict) and cu in contenido:
            meta = contenido[cu]
            if isinstance(meta, dict) and "desc" in meta:
                return meta["desc"]

    m = re.match(r"^([A-Z_0-9]+?)_([A-Za-z0-9 .+\-]+)$", cu)
    if m:
        base, valor = m.groups()
        if base in NOMBRES_FRECUENTES or base in NOMBRES_DERIVADAS:
            base_nombre = nombre_variable(base)
            return f"{base_nombre} = {valor}"

    return c


def nombre_completo(col: str) -> str:
    """Devuelve 'Edad (CH06)' — útil cuando el código sigue siendo importante."""
    if col is None:
        return ""
    nombre = nombre_variable(col)
    if nombre.lower() == str(col).lower():
        return str(col)
    return f"{nombre} ({col})"


def renombrar_dataframe(
    df,
    columnas: bool = True,
    indice: bool = False,
    incluir_codigo: bool = False,
):
    """
    Devuelve una copia del DataFrame con columnas (y/o índice) renombrados.

    Parámetros
    ----------
    columnas : bool
        Si True, renombra los nombres de columna.
    indice : bool
        Si True, renombra el índice (útil para tablas tipo perfil).
    incluir_codigo : bool
        Si True usa formato 'Edad (CH06)'; si False, solo 'Edad'.
    """
    fn = nombre_completo if incluir_codigo else nombre_variable
    df_out = df.copy()
    if columnas:
        df_out.columns = [fn(c) for c in df_out.columns]
    if indice:
        df_out.index = [fn(i) for i in df_out.index]
    return df_out


def renombrar_columna_de_variables(
    df,
    columna_con_codigos: str,
    incluir_codigo: bool = False,
):
    """
    Reescribe la columna que contiene códigos de variables (ej. 'variable')
    con los nombres humanos.
    """
    fn = nombre_completo if incluir_codigo else nombre_variable
    df_out = df.copy()
    if columna_con_codigos in df_out.columns:
        df_out[columna_con_codigos] = df_out[columna_con_codigos].astype(str).map(fn)
    return df_out
