# 🏆 Longshanks Tournament List Scraper & Exporter

Herramienta automatizada en **Python** para la extracción, parseo y exportación de listas de jugadores en torneos por equipos gestionados a través de **Longshanks** (especialmente optimizado para *Star Wars: X-Wing* y torneos por escuadras/equipos).

---

## 🌟 Características Principales

- ⚡ **Descarga Multihilo Paralela**: Extrae de forma ágil y respetuosa las listas de todos los integrantes del torneo (~110 jugadores en pocos segundos).
- 💾 **Almacenamiento Local (Caché JSON)**: Guarda los datos descargados en `data/event_<ID>.json`. Permite modificar el formato o re-procesar los resultados **al instante y sin conexión**, sin volver a hacer peticiones al servidor de Longshanks.
- 🌐 **Publicación Directa en Google Sheets (API)**: Genera y publica directamente un documento de **Google Sheets online** en tu cuenta de Google Drive listo para compartir mediante un enlace.
- 📊 **Exportación en Excel (.xlsx)**: Genera una pestaña por equipo y organiza a los integrantes en columnas con la lista completa consolidada en una **única celda multilínea** por participante.
- 🖥️ **Menú Interactivo CLI**: Interfaz sencilla guiada por opciones o ejecutable mediante banderas de consola.

---

## 📁 Estructura del Proyecto

```text
Longshanks_scrapper/
├── data/                         # Almacenamiento local (Caché JSON de eventos descargados)
│   └── event_36216.json
├── output/                       # Archivos Excel (.xlsx) generados localmente
│   └── event_36216_listas.xlsx
├── src/
│   ├── config.py                 # Rutas de carpetas y parámetros HTTP/paralelismo
│   ├── scraper.py                # Módulo de extracción paralela de Longshanks
│   ├── storage.py                # Gestión de lectura y escritura del caché JSON local
│   ├── parser.py                 # Extracción y limpieza del formato XWS (JSON/HTML)
│   ├── exporter.py               # Generador de libros Excel (.xlsx)
│   └── gsheet_exporter.py        # Generador y publicador directo a la API de Google Sheets
├── .gitignore                    # Exclusiones de Git (entorno virtual, temporales)
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

## 🔑 Configurar la API de Google Sheets (Opcional)

Para que el script pueda crear documentos de **Google Sheets** directamente en tu cuenta de Google Drive:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/) y crea un proyecto.
2. Habilita las APIs de **Google Sheets API** y **Google Drive API**.
3. Descarga tus credenciales:
   - **OAuth Desktop**: Descarga el archivo JSON, renómbralo como `client_secret.json` y colócalo en la raíz del proyecto.
   - *O bien* **Service Account**: Descarga el archivo JSON, renómbralo como `credentials.json` y colócalo en la raíz del proyecto.
4. Al ejecutar la opción de Google Sheets por primera vez, se abrirá tu navegador para hacer clic en **Permitir**. Se guardará la clave `token.json` y los futuros documentos se crearán automáticamente.

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
 🏆 LONGSHANKS TOURNAMENT SCRAPPER & DYNAMIC MATRIX GENERATOR
====================================================================
 Torneo Activo:       Evento #36216
 Estado Local:        [DISPONIBLE LOCALMENTE]
 Nuestro Equipo:      Iberian Mudhorns
 Formato de Equipo:   5 Jugadores (2 Escudos / 3 Lanzas)
 Fichas de Listas:    [LISTAS PERFILADAS (5P)]
--------------------------------------------------------------------
 [1] Descargar/Actualizar datos del torneo desde Longshanks
 [2] Generar GOOGLE SHEET online (Dinámico)
 [3] Flujo Completo: Descargar y Crear GOOGLE SHEET
 [4] Generar copia de respaldo local en Excel (.xlsx) [RECOMENDADO]
 [5] Cambiar ID del evento (Actual: #36216)
 [6] Seleccionar / Cambiar Equipo de Referencia (Nuestro Equipo)
 [7] Ver / Regenerar Fichas de Listas de Nuestro Equipo
 [8] Ajustar tamaño de equipo manualmente (3, 5 o 7 jugadores)
 [0] Salir
====================================================================
```

### 2. Comandos Rápidos por Consola (Flags CLI)

- **Descargar datos del torneo y guardar en local**:
  ```bash
  .\.venv\Scripts\python.exe main.py --download --event 36216
  ```

- **Fijar equipo de referencia y exportar a Excel**:
  ```bash
  .\.venv\Scripts\python.exe main.py --excel --event 36216 --ref-team "Iberian Mudhorns"
  ```

- **Forzar tamaño de equipo (3, 5 o 7 jugadores)**:
  ```bash
  .\.venv\Scripts\python.exe main.py --excel --event 36216 --team-size 5
  ```

- **Crear directamente el Google Sheet online**:
  ```bash
  .\.venv\Scripts\python.exe main.py --gsheet --event 36216
  ```

- **Ejecutar el flujo completo**:
  ```bash
  .\.venv\Scripts\python.exe main.py --all --event 36216
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
