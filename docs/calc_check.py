"""Independent hand-check of expected results for sample_data (run: python docs/calc_check.py)."""
import pandas as pd
d = "sample_data/"
inv = pd.read_csv(d+"inventory.csv")
inv["expected_closing"] = (inv.opening_qty + inv.purchases_qty + inv.transfers_in + inv.returns_qty
                           - inv.issues_qty - inv.transfers_out - inv.breakage_qty)
inv["variance_qty"] = inv.book_closing_qty - inv.physical_count   # +ve = SHORTAGE, -ve = SURPLUS
inv["variance_value"] = inv.variance_qty * inv.unit_cost
print("INVENTORY\n", inv[["item_id","outlet","expected_closing","book_closing_qty","physical_count","variance_qty","variance_value"]])
print("Book vs expected mismatches:", (inv.expected_closing != inv.book_closing_qty).sum())
print("Net variance value:", inv.variance_value.sum())

b = pd.read_csv(d+"beo_events.csv")
b["gross_profit"] = b.net_revenue - b.food_cost - b.beverage_cost - b.other_direct_cost
b["margin_pct"] = (b.gross_profit / b.net_revenue.where(b.net_revenue > 0) * 100).round(2)
print("\nBANQUET\n", b[["event_id","net_revenue","gross_profit","margin_pct"]])

def uniq(f): 
    x = pd.read_csv(d+f); return x.drop_duplicates("check_id"), len(x)-len(x.drop_duplicates("check_id"))
dc, dd = uniq("discount_checks.csv"); dc["pct"] = dc.discount_amount/dc.original_amount.where(dc.original_amount>0)*100
print("\nDISCOUNT unique:", len(dc), "dupes:", dd, "amount:", dc.discount_amount.sum(), "avg %:", round(dc.pct.mean(),2))
print(" missing reason:", dc.reason.isna().sum(), "| missing/pending approval:", (~dc.approval_status.eq("Approved")).sum())
v, vd = uniq("void_checks.csv"); print("VOID unique:", len(v), "dupes:", vd, "amount:", v.void_amount.sum(),
  "| missing reason:", v.reason.isna().sum(), "| missing approval:", (v.approval_status!="Approved").sum())
n, _ = uniq("nc_checks.csv"); a, _ = uniq("amenities_checks.csv")
print("NC unique:", len(n), "value:", n.nc_amount.sum(), "| AMENITIES unique:", len(a), "value:", a.amount.sum())
ov = n[(n.reference_type=="AMENITY") & n.reference_id.isin(a.check_id)]
print("Overlap NC<->Amenity:", list(ov.check_id), "value:", ov.nc_amount.sum(),
      "| combined NC+Amenities (no double count):", n.nc_amount.sum() + a.amount.sum() - ov.nc_amount.sum())
