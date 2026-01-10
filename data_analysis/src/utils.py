import os
from pathlib import Path


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def project_paths():
    """
    Return important project paths relative to the project root.
    Assumes this file is in src/ and main.py is in root.
    """
    root = Path(__file__).resolve().parent.parent
    paths = {
        "root": root,
        "repo": root / "flask",  # cloned repo folder name
        "data_raw": root / "data" / "raw",
        "data_processed": root / "data" / "processed",
        "figures": root / "figures",
    }
    return paths
