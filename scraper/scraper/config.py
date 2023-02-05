import yaml
from pathlib import Path

fp = Path(__file__).parent

def get_config():
    with open(fp / "config.yml", "r") as f:
        return yaml.safe_load(f)
