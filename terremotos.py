"""
Scraper de terremotos del IGN (España).
Descarga las 3 tablas publicadas (10 días, 30 días sentidos, año significativos),
las fusiona en una base de datos local (terremotos_db.csv) sin duplicar eventos,
y actualiza los registros existentes si el IGN los revisó.
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

URLS = {
    "10dias": "https://www.ign.es/web/ign/portal/ultimos-terremotos/-/ultimos-terremotos/get10dias",
    "30dias": "https://www.ign.es/web/ign/portal/ultimos-terremotos/-/ultimos-terremotos/get30dias",
    "anio": "https://www.ign.es/web/ign/portal/ultimos-terremotos/-/ultimos-terremotos/getAnio",
}

DB_PATH = Path(__file__).resolve().parent / "terremotos_db.csv"

COLUMN_MAP = {
    "Evento": "evento",
    "Fecha": "fecha",
    "Hora UTC": "hora_utc",
    "Hora Local  (*)": "hora_local",
    "Hora Local (*)": "hora_local",
    "Latitud": "latitud",
    "Longitud": "longitud",
    "Profundidad  (km)": "profundidad_km",
    "Profundidad (km)": "profundidad_km",
    "Magnitud": "magnitud",
    "Tipo Mag.": "tipo_mag",
    "Int. max.": "int_max",
    "Localización": "localizacion",
}

NUMERIC_COLS = ["latitud", "longitud", "profundidad_km", "magnitud"]


def fetch_table(url: str) -> pd.DataFrame:
    """Descarga una URL del IGN y devuelve la tabla de eventos como DataFrame."""
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text), flavor="html5lib")
    for t in tables:
        if "Evento" in t.columns:
            return t
    raise ValueError(f"No se encontró una tabla con columna 'Evento' en {url}")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas a nombres internos y castea tipos."""
    df = df.rename(columns=COLUMN_MAP)
    keep = [c for c in dict.fromkeys(COLUMN_MAP.values()) if c in df.columns]
    df = df[keep].copy()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "fecha" in df.columns and "hora_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(
            df["fecha"] + " " + df["hora_utc"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
        ).dt.strftime("%Y-%m-%dT%H:%M:%S")
        hora_local = (
            df["hora_local"].fillna(df["hora_utc"]) if "hora_local" in df.columns else df["hora_utc"]
        )
        df["timestamp_local"] = pd.to_datetime(
            df["fecha"] + " " + hora_local, format="%d/%m/%Y %H:%M:%S", errors="coerce"
        ).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return df


def scrape_all() -> pd.DataFrame:
    """Scrapea las 3 fuentes; si alguna falla, continúa con las demás."""
    frames = []
    for name, url in URLS.items():
        try:
            df = normalize(fetch_table(url))
            print(f"[ok] {name}: {len(df)} eventos")
            frames.append(df)
        except Exception as e:
            print(f"[aviso] fallo al scrapear {name}: {e}", file=sys.stderr)
    if not frames:
        raise RuntimeError("No se pudo scrapear ninguna de las 3 fuentes.")
    return pd.concat(frames, ignore_index=True)


def update_db(new_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Fusiona new_df con la base de datos existente.
    Dedupe por 'evento': si un evento ya existía, se conserva la versión nueva
    (el IGN revisa magnitudes/localización tras el análisis sísmico).
    Devuelve (df_combinado, cantidad_de_eventos_nuevos).
    """
    if DB_PATH.exists():
        old_df = pd.read_csv(DB_PATH, dtype={"evento": str})
        n_old = old_df["evento"].nunique()
        combined = pd.concat([old_df, new_df], ignore_index=True)
    else:
        n_old = 0
        combined = new_df

    # keep="last" => la versión recién scrapeada gana sobre la guardada previamente
    combined = combined.drop_duplicates(subset="evento", keep="last")
    combined = combined.sort_values("fecha", ascending=False, kind="stable")
    combined.to_csv(DB_PATH, index=False)

    n_new = combined["evento"].nunique() - n_old
    return combined, n_new


def main():
    new_data = scrape_all()
    db, n_new = update_db(new_data)
    print(f"Eventos nuevos añadidos: {max(n_new, 0)}")
    print(f"Total eventos en base de datos: {len(db)}")
    print(f"Base de datos: {DB_PATH}")


if __name__ == "__main__":
    main()
