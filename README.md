# Terremotos España — Dashboard IGN

**[Ir al Dashboard](https://rodrigo-j-goncalves.github.io/terremotos-dashboard/)** 

---

- Dashboard estático de sismicidad en España
- Generado a partir de las tablas publicadas por el
[Instituto Geográfico Nacional (IGN)](https://www.ign.es/web/ultimos-terremotos).
- **[Verlo en vivo](https://rodrigo-j-goncalves.github.io/terremotos-dashboard/)** 

---

## Qué hace

1. **`terremotos.py`** — Descarga las 3 tablas del IGN (últimos 10 días, 30 días sentidos,
   año significativos), las fusiona en `terremotos_db.csv` sin duplicar eventos.
   Si el IGN revisa una magnitud o localización, la versión más reciente prevalece (`keep=last`).

2. **`generate_html.py`** — Lee `terremotos_db.csv` y genera `index.html`:
   página 100 % estática con Plotly.js (CDN) y JS vanilla.
   - Scatter magnitud vs. tiempo (hora local España)
   - Mapa de epicentros (scattergeo, cubre Península + Canarias)
   - Tabla ordenable por cualquier columna
   - Filtros sincronizados: localización, magnitud (rango), fecha (rango)

No hay backend ni servidor: el HTML resultante puede servirse directamente desde GitHub Pages.

---

## Requisitos

```
python >= 3.10
pandas
requests
html5lib
beautifulsoup4
```

```bash
pip install pandas requests html5lib beautifulsoup4
```

---

## Uso local

```bash
# 1. Scrapear y actualizar la base de datos
python terremotos.py

# 2. Generar el dashboard
python generate_html.py

# 3. Abrir en el navegador
xdg-open index.html   # Linux
open index.html        # macOS
```

---

## Automatización con GitHub Actions + Pages

El workflow `.github/workflows/update.yml` ejecuta los dos scripts a diario,
**commitea `terremotos_db.csv` de vuelta al repo** (para acumular historia),
y despliega `index.html` en GitHub Pages.

> **Por qué commitear el CSV:** GitHub Actions hace checkout limpio en cada
> ejecución. Sin el commit, el CSV solo contendría los eventos del día actual;
> con él, la base de datos crece indefinidamente y conserva sismos que el IGN
> ya no publica.

```yaml
name: Actualizar dashboard

on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC cada día
  workflow_dispatch:        # permite ejecución manual

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Instalar dependencias
        run: pip install pandas requests html5lib beautifulsoup4

      - name: Scrapear IGN y actualizar CSV
        run: python terremotos.py

      - name: Commitear CSV actualizado
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add terremotos_db.csv
          git diff --staged --quiet || git commit -m "datos: actualizar terremotos_db.csv [$(date -u +%Y-%m-%d)]"
          git push

      - name: Generar HTML
        run: python generate_html.py

      - name: Subir artefacto para Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: "."

      - name: Desplegar en GitHub Pages
        uses: actions/deploy-pages@v4
```

El workflow corre automáticamente todos los días a las 06:00 UTC. Para ejecución manual
(ej. durante un enjambre sísmico): **Actions → Actualizar dashboard → Run workflow**.

Para activarlo por primera vez:
1. En el repo → **Settings → Pages → Source**: seleccionar *GitHub Actions*.
2. Lanzar manualmente desde **Actions → Actualizar dashboard → Run workflow**.

---

## Estructura de archivos

```
terremotos-dashboard/
├── terremotos.py          # scraper + actualización de DB
├── generate_html.py       # generador de dashboard estático
├── terremotos_db.csv      # base de datos acumulada (commitear; crece con el tiempo)
├── index.html             # dashboard (generado por Actions; en .gitignore)
├── .github/
│   └── workflows/
│       └── update.yml     # automatización diaria
└── README.md
```

---

## Columnas de `terremotos_db.csv`

| Columna | Descripción |
|---|---|
| `evento` | ID único e inmutable del sismo (clave primaria) |
| `fecha` | Fecha en formato DD/MM/YYYY |
| `hora_utc` | Hora en UTC (HH:MM:SS) |
| `hora_local` | Hora local España peninsular (CET/CEST) |
| `timestamp_utc` | Datetime ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SS`) |
| `timestamp_local` | Datetime ISO 8601 hora local España (`YYYY-MM-DDTHH:MM:SS`) |
| `latitud` | Latitud del epicentro (grados decimales) |
| `longitud` | Longitud del epicentro (grados decimales) |
| `profundidad_km` | Profundidad focal en km |
| `magnitud` | Magnitud del sismo |
| `localizacion` | Descripción geográfica del epicentro |

---

## Fuente de datos

Instituto Geográfico Nacional (IGN) — Ministerio de Transportes y Movilidad Sostenible, España.
URL: https://www.ign.es/web/ultimos-terremotos

Los datos son públicos. Se recomienda no sobrecargar el servidor del IGN
(el cron diario es más que suficiente para uso personal o académico).

## Autor

[Rodrigo J. Gonçalves](https://rodrigo-j-goncalves.github.io/)
