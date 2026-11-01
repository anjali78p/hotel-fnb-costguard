"""Business calculations for Hotel F&B CostGuard (pandas).
Conventions: variance = book - physical (positive = SHORTAGE, negative = SURPLUS).
Flags mean 'review needed', not misconduct."""
import pandas as pd
from . import config

APPROVED = "Approved"


def dedupe(df: pd.DataFrame, key: str = "check_id"):
    """Return (unique_rows, duplicate_rows). First occurrence is kept."""
    dup_mask = df.duplicated(subset=key, keep="first")
    return df[~dup_mask].copy(), df[dup_mask].copy()


def _blank(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype(str).str.strip() == "")


# ---------- Inventory ----------
def inventory_variance(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["expected_closing"] = (out.opening_qty + out.purchases_qty + out.transfers_in + out.returns_qty
                               - out.issues_qty - out.transfers_out - out.breakage_qty)
    out["book_vs_expected_diff"] = out.book_closing_qty - out.expected_closing
    out["variance_qty"] = out.book_closing_qty - out.physical_count
    out["variance_value"] = out.variance_qty * out.unit_cost
    out["variance_type"] = out.variance_qty.apply(
        lambda v: "shortage" if v > 0 else ("surplus" if v < 0 else "ok"))
    return out


# ---------- Cost ----------
def fnb_cost_pct(consumption_cost: float, net_sales: float):
    return None if not net_sales or net_sales <= 0 else round(consumption_cost / net_sales * 100, 2)


def consumption_cost(opening_value: float, purchases_value: float, closing_value: float,
                     adjustments: float = 0.0) -> float:
    """Opening + purchases - closing (+/- agreed adjustments for transfers/returns)."""
    return opening_value + purchases_value - closing_value + adjustments


# ---------- Banquet ----------
def banquet_profitability(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["gross_profit"] = out.net_revenue - out.food_cost - out.beverage_cost - out.other_direct_cost
    out["margin_pct"] = (out.gross_profit / out.net_revenue.where(out.net_revenue > 0) * 100).round(2)
    return out.sort_values("gross_profit", ascending=False)


# ---------- Purchases / invoices ----------
def invoice_exceptions(df: pd.DataFrame) -> dict:
    uniq, dups = dedupe(df, "invoice_no")
    mism = uniq[uniq.invoice_rate != uniq.po_rate].copy()
    mism["rate_diff"] = mism.invoice_rate - mism.po_rate
    mism["rate_diff_pct"] = (mism.rate_diff / mism.po_rate * 100).round(2)
    mism["excess_value"] = mism.rate_diff * mism.received_qty
    mism = mism[mism.rate_diff_pct.abs() > config.INVOICE_RATE_TOLERANCE_PCT]
    return {"unique_invoices": len(uniq), "duplicates": dups, "rate_mismatches": mism}


# ---------- Checks & Revenue Control ----------
def discount_summary(df: pd.DataFrame, limit_pct: float = None) -> dict:
    limit_pct = config.DISCOUNT_LIMIT_PCT if limit_pct is None else limit_pct
    uniq, dups = dedupe(df)
    uniq["discount_pct"] = (uniq.discount_amount / uniq.original_amount.where(uniq.original_amount > 0) * 100).round(2)
    flags = pd.DataFrame(index=uniq.index)
    flags["missing_reason"] = _blank(uniq.reason)
    flags["approval_issue"] = uniq.approval_status != APPROVED
    flags["above_limit"] = uniq.discount_pct > limit_pct
    return {"count": len(uniq), "amount": float(uniq.discount_amount.sum()),
            "avg_discount_pct": round(float(uniq.discount_pct.mean()), 2),
            "duplicates": dups, "rows": uniq.join(flags), "limit_pct": limit_pct}


def void_summary(df: pd.DataFrame, repeat_min: int = None) -> dict:
    repeat_min = config.REPEAT_VOID_MIN if repeat_min is None else repeat_min
    uniq, dups = dedupe(df)
    uniq["missing_reason"] = _blank(uniq.reason)
    uniq["approval_issue"] = uniq.approval_status != APPROVED
    grp = uniq.groupby(["voided_by", "outlet"]).size().reset_index(name="void_count")
    repeats = grp[grp.void_count >= repeat_min]
    return {"count": len(uniq), "amount": float(uniq.void_amount.sum()),
            "duplicates": dups, "rows": uniq, "repeat_patterns": repeats}


def nc_summary(df: pd.DataFrame) -> dict:
    uniq, dups = dedupe(df)
    uniq["missing_reason"] = _blank(uniq.reason)
    uniq["approval_issue"] = uniq.approval_status != APPROVED
    return {"count": len(uniq), "amount": float(uniq.nc_amount.sum()), "duplicates": dups, "rows": uniq}


def amenities_summary(df: pd.DataFrame, high_value: float = None) -> dict:
    high_value = config.HIGH_AMENITY_VALUE if high_value is None else high_value
    uniq, dups = dedupe(df)
    uniq["missing_reason"] = _blank(uniq.reason)
    uniq["approval_issue"] = uniq.approval_status != APPROVED
    uniq["high_value"] = uniq.amount > high_value
    return {"count": len(uniq), "amount": float(uniq.amount.sum()), "duplicates": dups, "rows": uniq}


def combined_nc_amenities(nc: pd.DataFrame, amenities: pd.DataFrame) -> dict:
    """NC + amenities total without double-counting amenities already booked as NC."""
    n, _ = dedupe(nc)
    a, _ = dedupe(amenities)
    overlap = n[(n.reference_type == "AMENITY") & n.reference_id.isin(a.check_id)]
    gross = float(n.nc_amount.sum() + a.amount.sum())
    overlap_val = float(overlap.nc_amount.sum())
    return {"nc_total": float(n.nc_amount.sum()), "amenities_total": float(a.amount.sum()),
            "overlap_check_ids": list(overlap.check_id), "overlap_value": overlap_val,
            "combined_total": gross - overlap_val}


# ---------- Consumption cost & F&B cost % (by category) ----------
def consumption_by_category(inv: pd.DataFrame, sales: pd.DataFrame) -> dict:
    """Consumption qty = opening + purchases + transfers_in + returns - transfers_out - physical_count.
    (Closing value uses PHYSICAL count; breakage/shortage therefore sit inside consumption.)
    Convention to be confirmed with the hotel. Cost % = consumption cost / net sales x 100."""
    d = inv.copy()
    d["category"] = d.item_id.str[:2].map(config.CATEGORY_BY_PREFIX).fillna("Other")
    d["consumption_qty"] = (d.opening_qty + d.purchases_qty + d.transfers_in + d.returns_qty
                            - d.transfers_out - d.physical_count)
    d["consumption_cost"] = d.consumption_qty * d.unit_cost
    cost = d.groupby("category").consumption_cost.sum()
    sold = sales.groupby("category").net_sales.sum()
    rows = []
    for cat in sorted(set(cost.index) | set(sold.index)):
        c, s = float(cost.get(cat, 0.0)), float(sold.get(cat, 0.0))
        rows.append({"category": cat, "consumption_cost": c, "net_sales": s, "cost_pct": fnb_cost_pct(c, s)})
    tc, ts = sum(r["consumption_cost"] for r in rows), sum(r["net_sales"] for r in rows)
    return {"rows": rows, "total_cost": tc, "total_sales": ts, "overall_cost_pct": fnb_cost_pct(tc, ts),
            "items": d}
