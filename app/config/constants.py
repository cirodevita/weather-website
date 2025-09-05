
INSTRUMENT_TYPES = {
    "ws_on": {
        "name": "Stazione Meteorologica",
        "variables": ["TempOut", "HumOut", "WindSpeed", "WindDir", "RainRate", "Barometer"],
    },
    "ws_off": {"name": "Stazione Meteorologica - off", "variables": []},
    "radar_off": {"name": "Radar Meteorologico", "variables": ["Precipitation"]},
    "tidegauge_off": {"name": "Mareografo", "variables": ["SeaLevel"]},
    "wavebuoy_off": {"name": "Ondametro", "variables": []},
    "mooring_off": {"name": "Mooring", "variables": []},
    "owbuoy_off": {"name": "Boa Meteo-Oceanografica", "variables": []},
    "hf_off": {"name": "HF Radar", "variables": []},
    "glider_off": {"name": "Glider", "variables": ["Temp", "Salt", "Depth", "Turbidity", "Oxygen", "Nitrates"]},
}

AIRLINK_VARIABLES = ["pm_2p5_nowcast", "pm_1", "pm_10_nowcast", "aqi_nowcast_val"]


def variables_for(instrument_type: str, has_airlink: bool) -> str:
    """
    Ritorna una stringa CSV pronta per il DB con le variabili del tipo strumento
    + eventuali variabili AirLink.
    """
    base_vars = INSTRUMENT_TYPES.get(instrument_type, {}).get("variables", []) or []
    all_vars = list(base_vars)
    if has_airlink:
        all_vars += AIRLINK_VARIABLES
    # Dedup + ordine stabile
    seen = set()
    deduped = [v for v in all_vars if not (v in seen or seen.add(v))]
    return ", ".join(deduped)
