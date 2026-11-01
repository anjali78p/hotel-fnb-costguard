"""Data loader. Reads uploaded_data/<name>.csv if a validated upload exists, else sample_data/<name>.csv.
Member 2 can swap these functions to read from RDS PostgreSQL without changing the API endpoints."""
import os
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "sample_data"

# file -> date column used for date-range filtering (None = not filterable)
DATE_COL = {"inventory": "business_date", "invoices": "invoice_date", "beo_events": "event_date",
            "discount_checks": "business_date", "void_checks": "business_date",
            "nc_checks": "business_date", "amenities_checks": "business_date", "sales": "business_date"}


def get_upload_dir() -> pathlib.Path:
    return pathlib.Path(os.getenv("COSTGUARD_UPLOAD_DIR", ROOT / "uploaded_data"))


def _csv_path(name: str) -> pathlib.Path:
    up = get_upload_dir() / f"{name}.csv"
    return up if up.exists() else DATA_DIR / f"{name}.csv"


def load(name: str, date_from: str = None, date_to: str = None, outlet: str = None) -> pd.DataFrame:
    df = pd.read_csv(_csv_path(name))
    col = DATE_COL.get(name)
    if col and date_from:
        df = df[df[col] >= date_from]
    if col and date_to:
        df = df[df[col] <= date_to]
    if outlet and "outlet" in df.columns:
        df = df[df.outlet == outlet]
    return df.reset_index(drop=True)
