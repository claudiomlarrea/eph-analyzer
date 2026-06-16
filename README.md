# eph-analyzer

Herramienta interactiva para analizar microdatos de la **Encuesta Permanente de Hogares (EPH)** del INDEC y sus **módulos TIC**.

Permite cargar cualquier base de **hogares**, **individuos** o **módulo TIC**, en cualquier formato distribuido por el INDEC (`.xlsx`, `.txt`, `.csv`, `.dbf`, `.zip`), y aplicar:

- Estadística descriptiva (frecuencias, media, mediana, desvío, IC).
- Análisis de desigualdad (quintiles, Gini).
- Correlaciones (Pearson, Kendall) y consistencia interna (alfa de Cronbach).
- Construcción del **índice compuesto de exclusión digital** (acceso + competencias + uso significativo).
- Modelos inferenciales y predictivos:
  - Regresión logística (con odds ratios, p-valores, pseudo-R², AUC).
  - Árboles de decisión.
  - Random Forest.
  - Clústeres (K-means y jerárquico).
- Interpretabilidad con **SHAP (XAI)**: summary plot, dependence plot, waterfall.

## Modos de uso

- **Modo guiado**: la app calcula automáticamente la variable dependiente "exclusión digital" siguiendo la metodología de Larrea (2025) y vos solo seleccionás predictoras.
- **Modo experto**: vos elegís cualquier columna como variable dependiente y cualquier subconjunto como predictoras.

## Requisitos

- Python ≥ 3.10
- Las dependencias están en [`requirements.txt`](requirements.txt).

## Instalación local

```bash
git clone https://github.com/<usuario>/eph-analyzer.git
cd eph-analyzer
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
streamlit run app.py
```

La app queda accesible en `http://localhost:8501`.

Incluye dos modos en el menú lateral:

- **Carga manual** (`app.py`): subís archivos EPH en cualquier formato INDEC.
- **Microdatos INDEC automático** (`pages/`): descarga panel 2017–2022 (4.º trimestre / TIC) desde repositorios públicos y exporta Excel + Word.

CLI del módulo automático (sin Streamlit):

```bash
cd indec_auto
python run.py --pedido pedidos/san_juan.json
```

## Despliegue en Streamlit Community Cloud

1. Subir el repo a GitHub.
2. Ir a [streamlit.io/cloud](https://streamlit.io/cloud), conectar la cuenta de GitHub.
3. Seleccionar el repo `eph-analyzer`, archivo `app.py`, branch `main`.
4. Streamlit detecta `requirements.txt` y despliega automáticamente.

## Estructura del proyecto

```
eph-analyzer/
├── app.py                      # Punto de entrada Streamlit (carga manual)
├── pages/
│   └── 2_Microdatos_INDEC_automatico.py
├── indec_auto/                 # Descarga INDEC + pedidos JSON + CLI
│   ├── run.py
│   ├── pedidos/
│   └── src/
├── requirements.txt
├── .streamlit/config.toml
├── data/
│   ├── ejemplo/                # muestra mínima para demo
│   └── usuario/                # archivos cargados por el usuario (no se versionan)
├── diccionario/
│   ├── eph_variables.json      # códigos de variables EPH
│   └── eph_etiquetas.json      # etiquetas de valores
├── src/
│   ├── file_detector.py        # detecta tipo de archivo (hogar / individuo / TIC / merged)
│   ├── data_loader.py          # lectura de xlsx / txt / csv / dbf / zip
│   ├── data_cleaner.py         # nulos, tipos, recodificaciones
│   ├── merger.py               # join hogar ↔ individuo
│   ├── variables.py            # operacionalización de constructos
│   ├── indice_exclusion.py     # índice compuesto de exclusión digital
│   ├── analisis/
│   │   ├── descriptivo.py
│   │   ├── correlaciones.py
│   │   ├── desigualdad.py
│   │   └── comparativo.py
│   └── modelos/
│       ├── logistica.py
│       ├── arbol_decision.py
│       ├── random_forest.py
│       ├── clusters.py
│       └── shap_xai.py
├── notebooks/                  # exploración y entrenamiento offline
└── models/                     # modelos entrenados (.pkl)
```

## Datos

**Importante**: los microdatos de la EPH son públicos pero **no se versionan en este repo** por su tamaño y para evitar redistribución innecesaria. Descargalos desde el sitio oficial:

- EPH (microdatos): <https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos>
- Módulo TIC: <https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-26-89>

El usuario los carga en la app y se almacenan en `data/usuario/` (ignorada por git).

## Marco metodológico

La metodología implementada se basa en:

> Larrea, C. (2025). *Inclusión digital y movilidad social en la Argentina postpandemia: análisis empírico con inteligencia artificial y datos abiertos (2017–2024)*. Trabajo Final de Maestría en Educación, Universidad Nacional de Quilmes.

## Licencia

Pendiente de definir (sugerido MIT).
