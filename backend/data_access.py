"""Data loader. Prototype reads CSVs from sample_data/. Member 2 can swap these functions
to read from RDS PostgreSQL later without changing the API endpoints."""
import pathlib
import pandas as pd

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "sample_data"

# file -> date column used for date-range filtering (None = not filterable)
DATE_COL = {"inventory": "business_date", "invoices": "invoice_date", "beo_events": "event_date",
            "discount_checks": "business_date", "void_checks": "business_date",
            "nc_checks": "business_date", "amenities_checks": "business_date"}


def load(name: str, date_from: str = None, date_to: str = None, outlet: str = None) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    col = DATE_COL.get(name)
    if col and date_from:
        df = df[df[col] >= date_from]
    if col and date_to:
        df = df[df[col] <= date_to]
    if outlet and "outlet" in df.columns:
        df = df[df.outlet == outlet]
    return df.reset_index(drop=True)
