# Registro Histórico de Decisiones de Diseño y Táctica WTC

Este documento recopila las decisiones de arquitectura de software, heurísticas tácticas y diseño de producto implementadas en la herramienta **Longshanks Tournament Scraper & WTC Pairing Matrix Generator**. Sirve como referencia viva para el equipo de desarrollo y el cuerpo técnico.

---

## 1. Arquitectura General del Sistema

El proyecto está diseñado para trabajar con eventos de **Longshanks** orientados a torneos por escuadras/equipos (adaptable a formatos de 3, 5 y 7 jugadores, como el WTC de *Star Wars: X-Wing*).

```text
Longshanks_scrapper/
├── data/                         # Almacenamiento local (Caché JSON y configuraciones)
│   ├── event_<ID>.json           # Datos raw del torneo (descarga de Longshanks)
│   ├── event_<ID>_config.json    # Ajustes: equipo de referencia y tamaño de equipo
│   ├── event_<ID>_profiles.json  # Fichas tácticas de listas de nuestro equipo
│   ├── event_<ID>_schedule.json  # Calendario de rondas, cruces y misiones
│   └── settings.json             # Último evento activo seleccionado
├── docs/                         # Documentación y registro de decisiones de diseño
│   └── decisiones_diseno.md      # Este documento
├── output/                       # Archivos exportados (.xlsx)
│   └── event_<ID>_listas.xlsx
├── src/
│   ├── config.py                 # Constantes globales, rutas y parámetros HTTP
│   ├── scraper.py                # Extractor paralelo multihilo con reintentos
│   ├── storage.py                # Persistencia en disco de cachés y configuraciones
│   ├── parser.py                 # Extracción y limpieza de formato XWS (YASB / LBN)
│   ├── team_manager.py           # Detección de tamaños (3/5/7), equipo base y fichas
│   ├── matrix_evaluator.py       # Motor de emparejamientos NxN y clasificación de roles
│   └── exporter.py               # Generador de hojas de cálculo interactivas (.xlsx)
└── main.py                       # Interfaz CLI principal guiada por menú
```

---

## 2. Decisiones de Infraestructura y Exportación

### Decisión 2.1: Generación Local de `.xlsx` frente a Conexión Directa a la API de Google Sheets
* **Contexto:** Se planteó si la herramienta debía crear directamente una hoja en Google Sheets o generar un archivo Excel en local para su posterior importación.
* **Decisión:** Mantener la generación en local mediante archivos `.xlsx` compatibles con OpenXML estándar.
* **Justificación:**
  1. **Independencia de APIs y credenciales:** No obliga a los usuarios a crear proyectos en Google Cloud Console, gestionar cuentas de servicio (Service Accounts) ni manipular credenciales JSON sensibles.
  2. **Operatividad Offline:** Permite preparar las matrices y emparejamientos en cualquier lugar sin conexión a internet.
  3. **Importación transparente a Google Sheets:** Google Sheets importa y convierte de forma nativa archivos `.xlsx`. Al usar nombres de funciones universales en inglés (`SUM`, `IF`, `COUNTIF`, `RANK`, `INDEX`, `MATCH`), Google traduce automáticamente todas las fórmulas y reglas condicionales sin arrojar errores `#NAME?`.

---

## 3. Decisiones Tácticas: Escala de Emparejamientos (5 Niveles)

Al comparar una lista propia contra una lista rival, el motor evalúa fortalezas y contra-factores técnicos (iniciativas, volumen de fuego, bombas, jam, control de tracción, agilidad, etc.) asignando una puntuación en el rango $[-2, +2]$:

| Nivel | Símbolo | Puntos | Concepto Táctico |
| :---: | :---: | :---: | :--- |
| **Ideal** | 🟢🟢 | `+2` | Hard counter muy favorable / Especialista ofensivo letal. Prioridad máxima para **Lanza**. |
| **Favorable** | 🟢 | `+1` | Ventaja táctica moderada (superioridad de dados o iniciativa favorable). |
| **Igualado** | 🟡 | `0` | Paridad técnica / 50-50 consistente. Perfil de roca defensiva. |
| **Desfavorable** | 🟠 | `-1` | Desventaja manejable con buen pilotaje; cruce asumible. |
| **Crítico** | 🔴🔴 | `-2` | Hard counter rival directo / Trampa mortal. **Peligro crítico**. |

---

## 4. Filosofía y Asignación de Roles WTC (Escudos vs Lanzas)

### Distribución por Formato
* **Equipos de 5 jugadores:** 2 Escudos y 3 Lanzas.
* **Equipos de 7 jugadores:** 3 Escudos y 4 Lanzas.
* **Equipos de 3 jugadores:** 1 Escudo y 2 Lanzas.

### Decisión 4.1: Doctrina del "Golpe de Vanguardia" para el Escudo #1 en Tanda 1
* **Pregunta Táctica:** ¿Debe ser el Escudo #1 una lista plana de sacrificio (todo ceros y un `-2`) o la lista más fuerte y dominante del equipo (ej. Nacho: seis `+1`, cero `-2`, balance `+5`)?
* **Decisión:** **El Escudo #1 debe ser el jugador más dominante y seguro del equipo.**
* **Justificación Estratégica:**
  1. **Neutralización del Rival:** En la Tanda 1, el rival dispone de todos sus integrantes disponibles. Al plantarle de inicio al jugador más temible de nuestro equipo, tiren lo que tiren de atacantes les irá mal, obligándoles a un dilema donde pierden ventaja en ambas opciones.
  2. **Caza de Premios Gordos:** El rival se ve forzado a quemar a uno de sus mejores jugadores para intentar frenar a nuestro Escudo #1, liberando al resto de nuestras listas de esa amenaza para las tandas posteriores.
  3. **Cero Tolerancia a Trampas:** Sacar a ciegas en la Tanda 1 a alguien con un `-2` permite al rival tender una emboscada con ese rival concreto. El Escudo #1 debe ser inexpugnable.

### Decisión 4.2: Ordenación Escalonada de Escudos (#1, #2, #3)
1. **Escudo #1 (Tanda 1):** Mayor dominio y seguridad (menor cantidad de `-2`, menor cantidad de `-1`, mayor Balance Net Score positivo).
2. **Escudo #2 (Tanda 2):** Segunda muralla más sólida y consistente.
3. **Escudo #3 (Tanda 3):** Perfil de absorción de daño / aguante. Para la Tanda 3, muchas de las amenazas rivales ya han sido emparejadas o descartadas, reduciendo el riesgo de cruces críticos.
4. **Lanzas (#1 a #N):** Jugadores reservados para la Oferta A, donde el rival expone a su defensor a ciegas y nosotros elegimos qué lanza ofensiva enviarle.

---

## 5. Implementación de la Matriz Interactiva y el Asistente en Excel

### Decisión 5.1: Matriz de Emparejamientos Numérica Pura
* **Diseño anterior:** Textos estáticos con emojis quemados (`"🟢 (+1)"`, `"🟡 (0)"`).
* **Nuevo diseño:**
  * Valores enteros puros (`-2, -1, 0, 1, 2`).
  * Formato numérico de celda: `+0;-0;0` (los positivos muestran el `+`, los ceros muestran `0`).
  * Formato condicional nativo de 5 colores: la celda reacciona al instante a la edición manual.
  * Notas tácticas emergentes (`Comment`) preservadas sobre cada celda.
  * Balance Net Score dinámico: `=SUM(D{row}:J{row})`.

### Decisión 5.2: Fórmulas Reactivas en Segundo Plano (Columnas Auxiliares Ocultas)
Para que el usuario pueda cambiar un número en la matriz y el Excel recalcule roles y recomendaciones en vivo sin necesidad de macros ni VBA, se crearon columnas auxiliares en segundo plano (ocultadas con `hidden=True`):
* `_IdxDef`: Índice de penalización defensiva ponderada.
* `_RankDef`: Ranking defensivo de 1 a $N$ con la función `=RANK(...)`.
* `_ScoreDef1`: Búsqueda con `=INDEX` y `=MATCH` del score particular contra el Defensor Rival de la Tanda 1.
* `_MetricSp1` y `_RankSp1`: Clasificación de lanzas idóneas para la Tanda 1.

### Decisión 5.3: Asistente de Pairing WTC en Mesa (Bloque B)
* **Títulos de Ofertas B:** Fórmulas dinámicas que buscan el nombre del Escudo asignado a esa tanda:
  ```excel
  ="[OFERTA 1B] Nuestro Escudo #1 (" & INDEX(Nombres, MATCH(1, Rankings, 0)) & ") -> Sus Atacantes"
  ```
* **Etiqueta Explícita de Recomendación:** Muestra el nombre del compañero evaluado para evitar confusiones de mesa:
  ```excel
  ="💡 Recomendación para " & INDEX(Nombres, MATCH(1, Rankings, 0)) & " (Escudo #1):"
  ```
* **Recomendación Dinámica:** Compara en tiempo real la puntuación del Escudo contra el Atacante 1A y Atacante 1B en la matriz.
  * Si detecta un `-2`: Alerta inmediata: `⛔ ¡EVITAR (-2) Rival A! -> Elegir: Rival B`.
  * Si compara ventajas: `🟢 Preferir: Rival A (+1 vs 0)`.
  * Si empatan: `🟡 Parejos: cualquiera (+1)`.
