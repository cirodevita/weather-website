import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("aggregation.yaml")

def load_aggregation_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {
        "excluded": set(data.get("excluded_columns", [])),
        "rain": set(data.get("rain_columns", [])),
        "wind": set(data.get("wind_columns", [])),
        "units": data.get("units", {})
    }
