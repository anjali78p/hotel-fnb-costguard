"""FastAPI app. Run: uvicorn backend.main:app --reload  (from repo root). Docs at /docs"""
import json
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from . import calculations as calc, config, recommendations as rec
from .data_access import load

app = FastAPI(title="Hotel F&B CostGuard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])  # tighten for production


def clean(df: pd.DataFrame) -> list:
    """DataFrame -> JSON-safe list of dicts (NaN -> null, numpy -> python)."""
    return json.loads(df.to_json(orient="records"))


def period(df_from, df_to):
    return {"from": df_from, "to": df_to}


def kpi(count, amount, date_from, date_to, **extra):
    return {"count": count, "amount": amount, "period": period(date_from, date_to), "currency": "INR",
            "data_freshness": datetime.now(timezone.utc).isoformat(timespec="seconds"), **extra}


def report(summary: dict, date_from, date_to, **extra):
    s = summary
    return {"kpi": kpi(s["count"], s["amount"], date_from, date_to, **extra),
            "rows": clean(s["rows"]),
            "meta": {"total_rows": len(s["rows"]), "duplicates_excluded": len(s["duplicates"]),
                     "duplicate_check_ids": list(s["duplicates"].get("check_id", []))}}


Q_FROM = Query(None, description="YYYY-MM-DD")
Q_TO = Query(None, description="YYYY-MM-DD")
Q_OUT = Query(None, description="Outlet name")


@app.get("/api/voids")
def voids(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT):
    s = calc.void_summary(load("void_checks", date_from, date_to, outlet))
    out = report(s, date_from, date_to)
    out["meta"]["repeat_patterns"] = clean(s["repeat_patterns"])
    return out


@app.get("/api/discounts")
def discounts(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT,
              limit_pct: Optional[float] = Query(None, description="Override configured limit")):
    s = calc.discount_summary(load("discount_checks", date_from, date_to, outlet), limit_pct)
    return report(s, date_from, date_to, avg_discount_pct=s["avg_discount_pct"], limit_pct=s["limit_pct"])


@app.get("/api/nc-checks")
def nc_checks(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT):
    return report(calc.nc_summary(load("nc_checks", date_from, date_to, outlet)), date_from, date_to)


@app.get("/api/amenities")
def amenities(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT):
    return report(calc.amenities_summary(load("amenities_checks", date_from, date_to, outlet)), date_from, date_to)


@app.get("/api/inventory")
def inventory(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT):
    df = calc.inventory_variance(load("inventory", date_from, date_to, outlet))
    return {"kpi": kpi(int((df.variance_qty != 0).sum()), float(df.variance_value.sum()), date_from, date_to,
                       note="count = items with variance; amount = net variance value (+ve shortage)"),
            "rows": clean(df), "meta": {"total_rows": len(df), "sign_convention": "variance = book - physical; positive = shortage"}}


@app.get("/api/banquets")
def banquets(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO):
    df = calc.banquet_profitability(load("beo_events", date_from, date_to))
    return {"kpi": kpi(len(df), float(df.gross_profit.sum()), date_from, date_to, note="amount = total gross profit"),
            "rows": clean(df), "meta": {"total_rows": len(df)}}


@app.get("/api/invoices")
def invoices():
    r = calc.invoice_exceptions(load("invoices"))
    return {"unique_invoices": r["unique_invoices"], "duplicates": clean(r["duplicates"]),
            "rate_mismatches": clean(r["rate_mismatches"])}


def _all(date_from, date_to, outlet):
    return dict(
        void=calc.void_summary(load("void_checks", date_from, date_to, outlet)),
        disc=calc.discount_summary(load("discount_checks", date_from, date_to, outlet)),
        nc_df=load("nc_checks", date_from, date_to, outlet),
        am_df=load("amenities_checks", date_from, date_to, outlet))


@app.get("/api/dashboard")
def dashboard(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT):
    d = _all(date_from, date_to, outlet)
    nc, am = calc.nc_summary(d["nc_df"]), calc.amenities_summary(d["am_df"])
    comb = calc.combined_nc_amenities(d["nc_df"], d["am_df"])
    inv = calc.inventory_variance(load("inventory", date_from, date_to, outlet))
    ban = calc.banquet_profitability(load("beo_events", date_from, date_to))
    return {"period": period(date_from, date_to), "currency": "INR",
            "data_freshness": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "voids": {"count": d["void"]["count"], "amount": d["void"]["amount"]},
            "discounts": {"count": d["disc"]["count"], "amount": d["disc"]["amount"], "avg_discount_pct": d["disc"]["avg_discount_pct"]},
            "nc": {"count": nc["count"], "amount": nc["amount"]},
            "amenities": {"count": am["count"], "amount": am["amount"]},
            "nc_amenities_combined": comb,
            "stock_variance_value": float(inv.variance_value.sum()),
            "banquet_gross_profit": float(ban.gross_profit.sum()),
            "note": "Voids, discounts, NC and amenities categories may overlap; do not add them together."}


@app.get("/api/alerts")
def alerts(date_from: Optional[str] = Q_FROM, date_to: Optional[str] = Q_TO, outlet: Optional[str] = Q_OUT,
           priority: Optional[str] = Query(None, description="High / Medium / Low")):
    d = _all(date_from, date_to, outlet)
    nc, am = calc.nc_summary(d["nc_df"]), calc.amenities_summary(d["am_df"])
    comb = calc.combined_nc_amenities(d["nc_df"], d["am_df"])
    inv = calc.inventory_variance(load("inventory", date_from, date_to, outlet))
    ban = calc.banquet_profitability(load("beo_events", date_from, date_to))
    items = rec.build_alerts(d["void"], d["disc"], nc, am, comb, calc.invoice_exceptions(load("invoices")), inv, ban)
    if priority:
        items = [i for i in items if i["priority"].lower() == priority.lower()]
    return {"count": len(items), "alerts": items, "note": "Flags are for review, not conclusions of misconduct."}

from .cost_api import router as cost_router
app.include_router(cost_router)

# Serve dashboard
import pathlib
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=pathlib.Path(__file__).resolve().parent.parent / "frontend", html=True), name="frontend")
