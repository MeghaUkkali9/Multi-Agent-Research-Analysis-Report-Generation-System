from pathlib import Path
import os
import yaml

def load_config(config_path: str | None = None):
    try:
        # Priority: function argument > ENV variable > default path
        config_path = (
            config_path
            or os.getenv("CONFIG_PATH")
            or str(_parent_root() / "config.yaml")
        )

        path = Path(config_path)

        if not path.is_file():
            raise FileNotFoundError(f"Config file not found at: {config_path}")

        with open(path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}") from e


def _parent_root():
    return Path(__file__).resolve().parents[1]