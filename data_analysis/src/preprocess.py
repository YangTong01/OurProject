import pandas as pd
from pathlib import Path
from .utils import ensure_dir


def preprocess(input_csv: str, output_csv: str):
    """
    Preprocess raw commit csv:
    - parse date
    - create month/week/weekday/is_weekend
    - handle missing values
    - output clean csv
    """
    ensure_dir(str(Path(output_csv).parent))

    df = pd.read_csv(input_csv)

    # date parsing
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # drop invalid date rows
    df = df.dropna(subset=["date"])

    # sanitize message
    df["message"] = df["message"].fillna("").astype(str).str.strip()

    # fill numeric columns
    for col in ["files_changed", "insertions", "deletions"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # derived time fields
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["week"] = df["date"].dt.to_period("W").astype(str)
    df["weekday"] = df["date"].dt.weekday  # Monday=0
    df["is_weekend"] = df["weekday"].isin([5, 6])

    # some additional fields that are handy in analysis
    df["net_lines"] = df["insertions"] - df["deletions"]

    # sort by date
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return df
