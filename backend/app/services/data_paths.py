import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_DIR / "data"
REALWORLD_DATA_DIR = DEFAULT_DATA_DIR / "resume_realworld_normalized"


def dataset_variant() -> str:
    return os.getenv("JOBSWIPE_DATASET", "canonical").strip().lower()


def data_dir() -> Path:
    override = os.getenv("JOBSWIPE_DATA_DIR")
    if override:
        return Path(override)
    if dataset_variant() == "realworld":
        return REALWORLD_DATA_DIR
    return DEFAULT_DATA_DIR


def data_path(name: str) -> Path:
    return data_dir() / name
