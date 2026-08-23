"""
Genera terremotos.html a partir de terremotos_db.csv.
Página 100% estática: Plotly.js vía CDN, JS embebido, sin servidor.

Uso:
    python generate_html.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "terremotos_db.csv"
HTML_PATH = Path(__file__).resolve().parent / "index.html"

# Columnas que se incluyen en el JSON embebido (orden = orden de la tabla)
COLS = [
    "evento", "fecha", "hora_local", "timestamp_local",
    "latitud", "longitud", "profundidad_km", "magnitud", "localizacion",
]


# ── Carga y preparación de datos ──────────────────────────────────────────────

def load_data() -> tuple[list[dict], dict]:
    df = pd.read_csv(DB_PATH, dtype={"evento": str})
    df["localizacion"] = df["localizacion"].fillna("Localización no disponible")
    for col in ["latitud", "longitud", "profundidad_km", "magnitud"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    existing = [c for c in COLS if c in df.columns]
    df = df[existing].sort_values("timestamp_local", ascending=False, na_position="last")
    df = df.where(pd.notnull(df), None)

    records = df.to_dict(orient="records")

    mags = df["magnitud"].dropna().tolist()
    dates = df["timestamp_local"].dropna().str[:10].tolist()
    locs = sorted(df["localizacion"].unique().tolist())

    meta = {
        "mag_min": round(min(mags), 1) if mags else 0.0,
        "mag_max": round(max(mags), 1) if mags else 10.0,
        "date_min": min(dates) if dates else "",
        "date_max": max(dates) if dates else "",
        "locs": locs,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "n": len(records),
    }
    return records, meta


# ── Plantilla HTML ────────────────────────────────────────────────────────────
# Los marcadores __XYZ__ se sustituyen en build_html(); así evitamos
# escapar los cientos de llaves del JS con {{ }}.

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Terremotos España — IGN</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #f0f2f5; color: #1a1a1a; }

    /* Header */
    header {
      background: #0f172a; color: #fff;
      padding: 0.75rem 1.5rem; display: flex; align-items: baseline; gap: 1rem;
    }
    header h1 { font-size: 1.05rem; font-weight: 700; }
    header p  { font-size: 0.78rem; color: #94a3b8; }

    /* Filtros */
    .filters {
      background: #fff; border-bottom: 1px solid #e2e8f0;
      padding: 0.75rem 1.5rem; display: flex; flex-wrap: wrap; gap: 1.25rem; align-items: flex-end;
    }
    .fg { display: flex; flex-direction: column; gap: 0.25rem; }
    .fg label {
      font-size: 0.68rem; font-weight: 700; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.07em;
    }
    .fg select,
    .fg input[type=text],
    .fg input[type=date] {
      border: 1px solid #cbd5e1; border-radius: 5px;
      padding: 0.3rem 0.5rem; font-size: 0.875rem;
      background: #f8fafc; color: #1a1a1a;
    }
    .fg select:focus,
    .fg input:focus { outline: 2px solid #3b82f6; border-color: #3b82f6; }

    /* Sliders de magnitud */
    .mag-group { display: flex; flex-direction: column; gap: 0.25rem; }
    .mag-group > span {
      font-size: 0.68rem; font-weight: 700; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.07em;
    }
    .mag-row { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: #475569; }
    .mag-row input[type=range] { width: 120px; cursor: pointer; accent-color: #3b82f6; }
    .mag-val { min-width: 2.2rem; text-align: right; font-variant-numeric: tabular-nums; }

    /* Badge y botones */
    .count-badge { font-size: 0.82rem; color: #475569; margin-left: auto; }
    .btn-reset,
    .btn-csv {
      padding: 0.3rem 0.7rem; border: 1px solid #cbd5e1; border-radius: 5px;
      background: #fff; cursor: pointer; font-size: 0.8rem; color: #475569;
    }
    .btn-reset:hover,
    .btn-csv:hover { background: #f1f5f9; }

    /* Grid de gráficos */
    .plots {
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 1rem; padding: 1rem 1.5rem 0;
    }
    .card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: hidden;
    }
    .card-title {
      font-size: 0.72rem; font-weight: 700; color: #475569;
      padding: 0.55rem 1rem; border-bottom: 1px solid #f1f5f9;
      text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* Tabla */
    .table-wrap { padding: 1rem 1.5rem 1.5rem; }
    .table-card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: auto;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    thead th {
      background: #f8fafc; font-weight: 700; text-align: left;
      padding: 0.5rem 0.75rem; border-bottom: 2px solid #e2e8f0;
      white-space: nowrap; user-select: none; cursor: pointer;
      color: #475569; font-size: 0.72rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    thead th:hover { background: #f1f5f9; color: #1a1a1a; }
    thead th[data-sort=asc]::after  { content: " ↑"; color: #3b82f6; }
    thead th[data-sort=desc]::after { content: " ↓"; color: #3b82f6; }
    td { padding: 0.42rem 0.75rem; border-bottom: 1px solid #f1f5f9; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #f8fafc; }
    .mag-hi  { color: #dc2626; font-weight: 700; }
    .mag-md  { color: #d97706; font-weight: 600; }
    .loc-nd  { color: #94a3b8; font-style: italic; }
    .ev-id   { font-size: 0.72rem; color: #94a3b8; }

    @media (max-width: 800px) {
      .plots { grid-template-columns: 1fr; }
      .filters { flex-direction: column; }
      .count-badge { margin-left: 0; }
    }
  </style>
</head>
<body>

<header>
  <h1>Terremotos España</h1>
  <p>Fuente: IGN (Instituto Geográfico Nacional) &nbsp;·&nbsp; Actualizado: __UPDATED__ &nbsp;·&nbsp; __N__ eventos</p>
</header>

<div class="filters">
  <div class="fg">
    <label>Localización</label>
    <select id="loc-select" style="max-width:220px">
      <option value="">Todas</option>
    </select>
  </div>
  <div class="fg">
    <label>Búsqueda parcial</label>
    <input type="text" id="loc-text" placeholder="texto libre…" style="width:170px">
  </div>
  <div class="mag-group">
    <span>Magnitud</span>
    <div class="mag-row">
      <span>≥</span>
      <input type="range" id="mag-min" step="0.1">
      <span class="mag-val" id="mag-min-val"></span>
    </div>
    <div class="mag-row">
      <span>≤</span>
      <input type="range" id="mag-max" step="0.1">
      <span class="mag-val" id="mag-max-val"></span>
    </div>
  </div>
  <div class="fg">
    <label>Desde</label>
    <input type="date" id="date-from">
  </div>
  <div class="fg">
    <label>Hasta</label>
    <input type="date" id="date-to">
  </div>
  <span class="count-badge" id="count"></span>
  <button class="btn-csv"   onclick="downloadCSV()" title="Descargar todos los eventos como CSV">&#8659; CSV</button>
  <button class="btn-reset" onclick="resetFilters()">&#8635; Reset</button>
</div>

<div class="plots">
  <div class="card">
    <div class="card-title">Magnitud vs. tiempo (hora local España peninsular)</div>
    <div id="chart-scatter" style="height:340px"></div>
  </div>
  <div class="card">
    <div class="card-title">Mapa de epicentros</div>
    <div id="chart-map" style="height:340px"></div>
  </div>
</div>

<div class="table-wrap">
  <div class="table-card">
    <table id="tabla-eventos">
      <thead>
        <tr>
          <th data-col="timestamp_local" data-sort="desc">Fecha</th>
          <th data-col="hora_local">Hora local (España peninsular)</th>
          <th data-col="magnitud">Mag</th>
          <th data-col="profundidad_km">Prof. (km)</th>
          <th data-col="localizacion">Localización</th>
          <th data-col="latitud">Lat</th>
          <th data-col="longitud">Lon</th>
          <th data-col="evento">Evento</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<script>
  // ── Datos embebidos ──────────────────────────────────────────────────────────
  const DATA            = __DATA__;
  const ALL_LOCS        = __LOCS__;
  const MAG_GLOBAL_MIN  = __MAG_MIN__;
  const MAG_GLOBAL_MAX  = __MAG_MAX__;
  const DATE_GLOBAL_MIN = '__DATE_MIN__';
  const DATE_GLOBAL_MAX = '__DATE_MAX__';

  // ── Estado global de filtros ─────────────────────────────────────────────────
  const state = {
    locExact : '',
    locText  : '',
    magMin   : MAG_GLOBAL_MIN,
    magMax   : MAG_GLOBAL_MAX,
    dateFrom : DATE_GLOBAL_MIN,
    dateTo   : DATE_GLOBAL_MAX,
    sortCol  : 'timestamp_local',
    sortAsc  : false,
  };

  // ── Filtrado ─────────────────────────────────────────────────────────────────
  function applyFilters() {
    const filtered = DATA.filter(d => {
      if (state.locExact !== '' && d.localizacion !== state.locExact) return false;
      if (state.locText  !== '' && !d.localizacion.toLowerCase().includes(state.locText.toLowerCase())) return false;
      const mag = d.magnitud;
      if (mag === null || mag < state.magMin || mag > state.magMax) return false;
      const date = (d.timestamp_local || '').slice(0, 10);
      if (state.dateFrom && date < state.dateFrom) return false;
      if (state.dateTo   && date > state.dateTo)   return false;
      return true;
    });
    document.getElementById('count').textContent =
      filtered.length + ' evento' + (filtered.length !== 1 ? 's' : '');
    updateScatter(filtered);
    updateMap(filtered);
    updateTable(filtered);
  }

  // ── Scatter: magnitud vs tiempo ──────────────────────────────────────────────
  const SCATTER_CFG    = { responsive: true, displayModeBar: false };
  const SCATTER_LAYOUT = {
    margin : { t: 10, r: 24, l: 46, b: 50 },
    xaxis  : { title: { text: 'Hora local (España peninsular)', font: { size: 11 } }, type: 'date' },
    yaxis  : { title: { text: 'Magnitud',            font: { size: 11 } } },
    hovermode     : 'closest',
    paper_bgcolor : '#ffffff',
    plot_bgcolor  : '#fafafa',
    font          : { family: 'system-ui, sans-serif', size: 11 },
  };

  function updateScatter(data) {
    Plotly.react('chart-scatter', [{
      x    : data.map(d => d.timestamp_local),
      y    : data.map(d => d.magnitud),
      mode : 'markers',
      type : 'scatter',
      text       : data.map(d => d.localizacion),
      customdata : data.map(d => [d.evento, d.profundidad_km, d.fecha]),
      hovertemplate:
        '<b>%{text}</b><br>' +
        'Mag: <b>%{y:.1f}</b> · Prof: %{customdata[1]} km<br>' +
        '%{customdata[2]} — %{x|%H:%M} h local<br>' +
        '<span style="color:#94a3b8">%{customdata[0]}</span><extra></extra>',
      marker: {
        color      : data.map(d => d.magnitud),
        colorscale : 'Reds',
        cmin       : MAG_GLOBAL_MIN,
        cmax       : MAG_GLOBAL_MAX,
        size       : 8,
        opacity    : 0.78,
        line       : { width: 0.5, color: '#555' },
        colorbar   : { title: { text: 'Mag', side: 'right' }, thickness: 12, len: 0.8 },
      },
    }], SCATTER_LAYOUT, SCATTER_CFG);
  }

  // ── Mapa ─────────────────────────────────────────────────────────────────────
  const MAP_CFG    = { responsive: true, displayModeBar: false };
  const MAP_LAYOUT = {
    margin        : { t: 0, r: 0, l: 0, b: 0 },
    paper_bgcolor : '#ffffff',
    font          : { family: 'system-ui, sans-serif', size: 11 },
    geo: {
      scope         : 'europe',
      center        : { lat: 40.0, lon: -5.0 },
      lataxis       : { range: [26.5, 44.5] },
      lonaxis       : { range: [-19.0, 5.0] },
      showland      : true,  landcolor      : '#e8ecef',
      showocean     : true,  oceancolor     : '#cce3f0',
      showcoastlines: true,  coastlinecolor : '#8aa',
      showsubunits  : true,  subunitcolor   : '#aab',
      showframe     : false,
      bgcolor       : '#ffffff',
      projection    : { type: 'mercator' },
    },
  };

  function updateMap(data) {
    Plotly.react('chart-map', [{
      type      : 'scattergeo',
      lat       : data.map(d => d.latitud),
      lon       : data.map(d => d.longitud),
      mode      : 'markers',
      hoverinfo : 'text',
      text      : data.map(d =>
        `${d.localizacion}<br>` +
        `Mag <b>${d.magnitud != null ? d.magnitud.toFixed(1) : '?'}</b>` +
        ` · Prof: ${d.profundidad_km != null ? d.profundidad_km.toFixed(0) : '?'} km<br>` +
        `${d.fecha}  ${d.hora_local || ''}`
      ),
      marker: {
        size       : data.map(d => Math.max(4, (d.magnitud || 0) * 3.5)),
        color      : data.map(d => d.magnitud),
        colorscale : 'Reds',
        cmin       : MAG_GLOBAL_MIN,
        cmax       : MAG_GLOBAL_MAX,
        opacity    : 0.80,
        line       : { width: 0.5, color: '#555' },
        colorbar   : { title: { text: 'Mag', side: 'right' }, thickness: 12, len: 0.65 },
      },
    }], MAP_LAYOUT, MAP_CFG);
  }

  // ── Tabla ─────────────────────────────────────────────────────────────────────
  function sortData(data) {
    const col = state.sortCol;
    const asc = state.sortAsc;
    return [...data].sort((a, b) => {
      let va = a[col], vb = b[col];
      if (va == null) va = asc ? '\uFFFF' : '';
      if (vb == null) vb = asc ? '\uFFFF' : '';
      if (typeof va === 'number' && typeof vb === 'number') return asc ? va - vb : vb - va;
      return asc
        ? String(va).localeCompare(String(vb), 'es')
        : String(vb).localeCompare(String(va), 'es');
    });
  }

  function magClass(m) {
    if (m >= 4.0) return 'mag-hi';
    if (m >= 3.0) return 'mag-md';
    return '';
  }

  function updateTable(data) {
    const rows = sortData(data).map(d => {
      const mc  = magClass(d.magnitud);
      const loc = d.localizacion === 'Localización no disponible';
      return `<tr>
        <td>${d.fecha || ''}</td>
        <td>${d.hora_local || ''}</td>
        <td class="${mc}">${d.magnitud != null ? d.magnitud.toFixed(1) : ''}</td>
        <td>${d.profundidad_km != null ? d.profundidad_km.toFixed(0) : ''}</td>
        <td class="${loc ? 'loc-nd' : ''}">${d.localizacion || ''}</td>
        <td>${d.latitud  != null ? d.latitud.toFixed(4)  : ''}</td>
        <td>${d.longitud != null ? d.longitud.toFixed(4) : ''}</td>
        <td class="ev-id">${d.evento || ''}</td>
      </tr>`;
    });
    document.querySelector('#tabla-eventos tbody').innerHTML = rows.join('');
  }

  function initTableSort() {
    document.querySelectorAll('#tabla-eventos thead th').forEach(th => {
      th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (state.sortCol === col) {
          state.sortAsc = !state.sortAsc;
        } else {
          state.sortCol = col;
          // numéricos y fecha: desc por defecto; texto: asc
          state.sortAsc = ['localizacion', 'evento'].includes(col);
        }
        document.querySelectorAll('#tabla-eventos thead th')
          .forEach(h => delete h.dataset.sort);
        th.dataset.sort = state.sortAsc ? 'asc' : 'desc';
        applyFilters();
      });
    });
  }

  // ── Controles de filtros ──────────────────────────────────────────────────────
  function initControls() {
    // Dropdown de localización
    const sel = document.getElementById('loc-select');
    ALL_LOCS.forEach(loc => {
      const opt = document.createElement('option');
      opt.value = loc;
      opt.textContent = loc.length > 35 ? loc.slice(0, 33) + '…' : loc;
      opt.title = loc;
      sel.appendChild(opt);
    });
    sel.addEventListener('change', () => { state.locExact = sel.value; applyFilters(); });

    // Texto libre
    document.getElementById('loc-text').addEventListener('input', e => {
      state.locText = e.target.value;
      applyFilters();
    });

    // Sliders de magnitud
    const minS = document.getElementById('mag-min');
    const maxS = document.getElementById('mag-max');
    const minV = document.getElementById('mag-min-val');
    const maxV = document.getElementById('mag-max-val');
    [minS, maxS].forEach(s => {
      s.min  = MAG_GLOBAL_MIN;
      s.max  = MAG_GLOBAL_MAX;
      s.step = 0.1;
    });
    minS.value = MAG_GLOBAL_MIN;
    maxS.value = MAG_GLOBAL_MAX;
    minV.textContent = MAG_GLOBAL_MIN.toFixed(1);
    maxV.textContent = MAG_GLOBAL_MAX.toFixed(1);

    minS.addEventListener('input', () => {
      if (+minS.value > +maxS.value) minS.value = maxS.value;
      state.magMin = +minS.value;
      minV.textContent = state.magMin.toFixed(1);
      applyFilters();
    });
    maxS.addEventListener('input', () => {
      if (+maxS.value < +minS.value) maxS.value = minS.value;
      state.magMax = +maxS.value;
      maxV.textContent = state.magMax.toFixed(1);
      applyFilters();
    });

    // Rango de fechas
    document.getElementById('date-from').value = DATE_GLOBAL_MIN;
    document.getElementById('date-to').value   = DATE_GLOBAL_MAX;
    document.getElementById('date-from').addEventListener('change', e => {
      state.dateFrom = e.target.value;
      applyFilters();
    });
    document.getElementById('date-to').addEventListener('change', e => {
      state.dateTo = e.target.value;
      applyFilters();
    });
  }

  // ── Descarga CSV ──────────────────────────────────────────────────────────────
  function downloadCSV() {
    const cols = Object.keys(DATA[0] || {});
    const esc = v => {
      if (v === null || v === undefined) return '';
      const s = String(v);
      return (s.includes(',') || s.includes('"') || /\\n/.test(s))
        ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const lines = [cols.join(','), ...DATA.map(d => cols.map(c => esc(d[c])).join(','))];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'terremotos_ign.csv';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  function resetFilters() {
    state.locExact = '';   document.getElementById('loc-select').value = '';
    state.locText  = '';   document.getElementById('loc-text').value   = '';
    state.magMin = MAG_GLOBAL_MIN;
    state.magMax = MAG_GLOBAL_MAX;
    document.getElementById('mag-min').value     = MAG_GLOBAL_MIN;
    document.getElementById('mag-max').value     = MAG_GLOBAL_MAX;
    document.getElementById('mag-min-val').textContent = MAG_GLOBAL_MIN.toFixed(1);
    document.getElementById('mag-max-val').textContent = MAG_GLOBAL_MAX.toFixed(1);
    state.dateFrom = DATE_GLOBAL_MIN;
    state.dateTo   = DATE_GLOBAL_MAX;
    document.getElementById('date-from').value = DATE_GLOBAL_MIN;
    document.getElementById('date-to').value   = DATE_GLOBAL_MAX;
    applyFilters();
  }

  // ── Arranque ──────────────────────────────────────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    initControls();
    initTableSort();
    applyFilters();
  });
</script>
</body>
</html>
"""


# ── Generación ────────────────────────────────────────────────────────────────

def build_html(records: list[dict], meta: dict) -> str:
    html = HTML_TEMPLATE
    html = html.replace("__DATA__",    json.dumps(records, ensure_ascii=False, default=str))
    html = html.replace("__LOCS__",    json.dumps(meta["locs"], ensure_ascii=False))
    html = html.replace("__MAG_MIN__", str(meta["mag_min"]))
    html = html.replace("__MAG_MAX__", str(meta["mag_max"]))
    html = html.replace("__DATE_MIN__", meta["date_min"])
    html = html.replace("__DATE_MAX__", meta["date_max"])
    html = html.replace("__UPDATED__",  meta["updated"])
    html = html.replace("__N__",        str(meta["n"]))
    return html


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No encontré {DB_PATH}. Ejecutá primero terremotos.py.")
    records, meta = load_data()
    html = build_html(records, meta)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"[ok] {HTML_PATH.name} generado — {meta['n']} eventos · {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
