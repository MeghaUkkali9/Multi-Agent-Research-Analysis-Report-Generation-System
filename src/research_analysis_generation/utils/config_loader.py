from pathlib import Path
import os
import yaml
from research_analysis_generation.exception.custom_exception import ResearchAnalysisException

def load_config(config_path: str | None = None):
    try:
        # Priority: function argument > ENV variable > default path
        config_path = (
            config_path
            or os.getenv("CONFIG_PATH")
            or str(_default_config_path())
        )

        path = Path(config_path)

        if not path.is_file():
            raise FileNotFoundError(f"Config file not found at: {config_path}")

        with open(path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    except Exception as e:
        raise ResearchAnalysisException(f"Failed to load config: {e}") from e


def _default_config_path():
    return Path(__file__).resolve().parents[1] / "config" / "config.yml"