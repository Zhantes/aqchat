import os
from pathlib import Path

def get_data_dir() -> Path:
    return Path(os.environ.get("FRONTEND_DATA_DIR", "./data")).resolve()