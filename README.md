# 🏆 Longshanks Tournament List Scraper & Exporter

Herramienta automatizada en **Python** para la extracción, parseo y exportación de listas de jugadores en torneos por equipos gestionados a través de **Longshanks** (especialmente optimizado para *Star Wars: X-Wing* y torneos por escuadras/equipos).

---

## 🌟 Características Principales

- ⚡ **Descarga Multihilo Paralela**: Extrae de forma ágil y respetuosa las listas de todos los integrantes del torneo (~110 jugadores en pocos segundos).
- 💾 **Almacenamiento Local (Caché JSON)**: Guarda los datos descargados en `data/event_<ID>.json`. Permite modificar el formato o re-procesar los resultados **al instante y sin conexión**, sin volver a hacer peticiones al servidor de Longshanks.
- ⚡ **Descarga Multihilo Paralela**: Extrae de forma ágil y respetuosa las listas de todos los integrantes del torneo (~140 jugadores en pocos segundos).
- 💾 **Almacenamiento Local (Caché JSON)**: Guarda los datos descargados en `data/event_<ID>.json`. Permite modificar o re-procesar los resultados **al instante y sin conexión**, sin volver a hacer peticiones al servidor de Longshanks.
- 📊 **Generación Dinámica de Excel (.xlsx)**: Genera una pestaña por equipo rival con la matriz de emparejamientos $N \times N$, Asistente de Mesa WTC con cálculo automático de Escudos y Lanzas por rival, y las listas completas consolidadas.
- 🛡️ **Fichas de Perfilado de Listas**: Generación automática de plantillas editables (`data/event_<ID>_profiles.json`) para definir fortalezas y debilidades de las listas de tu equipo sin tocar código Python.
- 🖥️ **Menú Interactivo CLI**: Interfaz sencilla guiada por opciones o ejecutable mediante banderas de consola.

---

## 📁 Estructura del Proyecto

```text
Longshanks_scrapper/
├── data/                         # Caché JSON y perfiles de listas descargadas
│   ├── event_<ID>.json           # Datos raw del torneo (equipos y listas)
│   ├── event_<ID>_config.json    # Configuración del torneo (equipo de referencia, tamaño)
│   ├── event_<ID>_profiles.json  # Fichas de listas y reglas de emparejamiento
│   └── settings.json             # Ajustes de la aplicación (último evento activo)
├── output/                       # Archivos Excel (.xlsx) generados localmente
│   └── event_<ID>_listas.xlsx
├── src/
│   ├── config.py                 # Rutas de carpetas y parámetros HTTP/paralelismo
│   ├── scraper.py                # Módulo de extracción paralela de Longshanks
│   ├── storage.py                # Gestión de lectura y escritura de caché y ajustes
│   ├── parser.py                 # Extracción y limpieza del formato XWS (JSON/HTML)
│   ├── team_manager.py           # Detección de tamaños 3/5/7, equipo de referencia y fichas
│   ├── matrix_evaluator.py       # Motor de emparejamientos y asignación dinámica de roles WTC
│   └── exporter.py               # Generador de libros Excel (.xlsx) con matrices y asistente
├── .gitignore                    # Exclusiones de Git
├── main.py                       # Script principal ejecutable (Menú interactivo / CLI)
├── README.md                     # Documentación general del proyecto
└── requirements.txt              # Dependencias de Python
```

---

## 🚀 Instalación y Configuración

### 1. Requisitos Previos
- Python 3.10 o superior instalado en el sistema.

### 2. Configurar el Entorno Virtual Local (`.venv`)
En la carpeta del proyecto, ejecuta:

```bash
# Crear entorno virtual local
py -m venv .venv

# Instalar dependencias en el entorno virtual
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 💻 Guía de Uso

### 1. Menú Interactivo (Recomendado)
Ejecuta el menú principal sin argumentos:

```bash
.\.venv\Scripts\python.exe main.py
```

Desplegará la consola interactiva:
```text
====================================================================
 🏆 LONGSHANKS TOURNAMENT SCRAPPER & WTC MATRIX GENERATOR
====================================================================
 Torneo Activo:       Evento #37716
 Estado Local:        [DISPONIBLE LOCALMENTE]
 Nuestro Equipo:      Team Spain
 Formato de Equipo:   7 Jugadores (3 Escudos / 4 Lanzas)
 Fichas de Listas:    [LISTAS PERFILADAS (7P)]
--------------------------------------------------------------------
 [1] Descargar/Actualizar datos del torneo desde Longshanks
 [2] Generar archivo Excel (.xlsx) con Matrices y Asistente WTC
 [3] Flujo Completo: Descargar datos y Generar Excel (.xlsx)
 [4] Cambiar ID del evento (Actual: #37716)
 [5] Seleccionar / Cambiar Equipo de Referencia (Nuestro Equipo)
 [6] Ver / Regenerar Fichas de Listas de Nuestro Equipo
 [7] Ajustar tamaño de equipo manualmente (3, 5 o 7 jugadores)
 [0] Salir
====================================================================
```

### 2. Comandos Rápidos por Consola (Flags CLI)

- **Descargar datos del torneo y guardar en local**:
  ```bash
  .\.venv\Scripts\python.exe main.py --download --event 37716
  ```

- **Generar Excel con el equipo de referencia especificado**:
  ```bash
  .\.venv\Scripts\python.exe main.py --excel --event 37716 --ref-team "Team Spain"
  ```

- **Forzar tamaño de equipo (3, 5 o 7 jugadores)**:
  ```bash
  .\.venv\Scripts\python.exe main.py --excel --event 37716 --team-size 7
  ```

- **Ejecutar el flujo completo (Descarga + Generación de Excel)**:
  ```bash
  .\.venv\Scripts\python.exe main.py --all --event 37716
  ```

---

## 🛡️ Fichas de Perfilado de Jugadores (`data/event_<ID>_profiles.json`)

Al seleccionar tu equipo de referencia, el sistema autogenera una ficha editable con cada uno de los jugadores de tu equipo. En ella puedes ajustar:
- **Arquetipo y afinidad defensiva**: Estilo de juego y preferencia natural de la lista.
- **Criterios favorables (`favorable`)**: Palabras clave o arquetipos rivales contra los que la lista puntúa `+1 / 🟢` (ej. `pocas_naves`, `baja_agilidad`, `ases_fragiles`, `sin_bombas`, `naves_grandes`).
- **Criterios desfavorables (`unfavorable`)**: Factores que penalizan el cruce con `-1 / 🔴` (ej. `bombas_masivas`, `trajectorysimulator`, `enjambre_5+`, `enjambre_6+`, `tractores`).
- **Notas y Experiencia**: Conocimiento empírico de mesa de los jugadores.

El evaluador recalcula automáticamente la matriz $N \times N$ y reevalúa los roles óptimos (Escudos y Lanzas) frente a cada rival específico.

---

## 📄 Licencia y Uso
Desarrollado para la automatización y consulta rápida de listas de competidores en torneos de juegos de mesa gestionados en Longshanks.
