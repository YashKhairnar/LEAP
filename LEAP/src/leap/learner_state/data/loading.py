"""Input routines for research datasets."""

from pathlib import Path

import pandas as pd


def load_dcu_submissions(path: str | Path) -> pd.DataFrame:
    """Load the DCU programming-submission JSON file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"DCU submission file does not exist: {path}")
    return pd.read_json(path)

