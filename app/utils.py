import math
import pandas as pd
import numpy as np

import numpy as np
import pandas as pd
import math

def f_to_c(temp_f):
    """Convert Fahrenheit to Celsius."""
    return (temp_f - 32) * 5.0 / 9.0

def apply_unit_conversions(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Applica i fattori di conversione o le funzioni di conversione
    definite in config.yaml al dataframe aggregato.
    """
    print(cfg)
    if "units" not in cfg:
        return df

    df = df.copy()

    for col, uconf in cfg["units"].items():
        if col not in df.columns:
            continue

        # conversione per funzione (es. FtoC)
        if "convert" in uconf:
            if uconf["convert"].lower() == "ftoc":
                print("CONVERTING")
                df[col] = df[col].apply(lambda x: f_to_c(x) if pd.notnull(x) else np.nan)
            # puoi aggiungere altre funzioni qui, es. "CtoK", "mps_to_kmh", ecc.

        # conversione per fattore numerico
        elif "factor" in uconf:
            try:
                df[col] = df[col].astype(float) * float(uconf["factor"])
            except Exception:
                pass

    return df

def ensure_monotonic_progressive(series: pd.Series) -> pd.Series:
    """
    Corregge una serie cumulativa in modo che non diminuisca mai.
    Quando rileva un reset (valore minore del precedente),
    aggiunge il valore cumulato alla differenza.
    """
    if series.empty:
        return series

    values = series.fillna(0).to_numpy()
    corrected = np.zeros_like(values, dtype=float)
    offset = 0.0
    corrected[0] = values[0]

    for i in range(1, len(values)):
        if values[i] < values[i - 1]:
            # Reset rilevato: inizia nuovo ciclo, somma offset
            offset += values[i - 1]
        corrected[i] = values[i] + offset

    return pd.Series(corrected, index=series.index)

def aggregate_weather(df: pd.DataFrame, interval_minutes: int, cfg: dict):
    """
    Aggrega i dati meteo Davis:
      - Media aritmetica per parametri normali
      - Ultimo valore per variabili cumulative (RainDay, RainMonth, ecc.)
        + correzione per garantire progressione monotona
      - Media vettoriale per il vento
      - Esclude colonne definite in config
    """
    if df.empty:
        return df

    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time")

    # Escludi colonne non desiderate
    df.drop(columns=[c for c in cfg["excluded"] if c in df.columns], inplace=True, errors="ignore")

    # Converti in numerico dove possibile
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Media base
    agg = df.resample(f"{interval_minutes}min").mean()

    # --- Pioggia ---
    for col in cfg["rain"]:
        if col in df.columns:
            if col.lower() == "rainrate":
                # RainRate è intensità (mm/h): media aritmetica
                agg[col] = df[col].resample(f"{interval_minutes}min").mean()
            else:
                # RainDay, RainMonth, RainYear, RainStorm → cumulativi
                last_vals = df[col].resample(f"{interval_minutes}min").last()
                agg[col] = ensure_monotonic_progressive(last_vals)

    # --- Vento (media vettoriale) ---
    if {"WindSpeed", "WindDir"}.issubset(df.columns):
        rad = np.deg2rad(df["WindDir"])
        u = df["WindSpeed"] * np.sin(rad)
        v = df["WindSpeed"] * np.cos(rad)
        u_mean = u.resample(f"{interval_minutes}min").mean()
        v_mean = v.resample(f"{interval_minutes}min").mean()
        wind_speed = np.sqrt(u_mean**2 + v_mean**2)
        wind_dir = (np.degrees(np.arctan2(u_mean, v_mean)) + 360) % 360
        agg["WindSpeed"] = wind_speed
        agg["WindDir"] = wind_dir

    agg = agg.reset_index()

    # Convert units defined in aggregation.yaml
    agg = apply_unit_conversions(agg, cfg)

    # Arrotonda a 2 cifre decimali (tranne vento)
    wind_cols = cfg.get("wind", set())
    for col in agg.columns:
        if col not in wind_cols and pd.api.types.is_numeric_dtype(agg[col]):
            agg[col] = agg[col].round(2)

    return agg

def convert_f_to_c(temp_in_fahrenheit):
    convert = (temp_in_fahrenheit - 32) * 5 / 9
    return float("{:.2f}".format(convert))