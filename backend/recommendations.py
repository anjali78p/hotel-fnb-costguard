"""Maps exception flags to evidence, likely cause and recommended follow-up.
Wording is deliberately neutral: flags mean 'review', not misconduct."""
import pandas as pd

ACTIONS = {
    "void_missing_reason":   ("Medium", "Void reason not recorded", "Front office / outlet manager", "Request explanation and corrected/complete void documentation."),
    "void_missing_approval": ("High", "Approval not captured", "Outlet manager", "Verify against the authorised approval matrix."),
    "void_repeat_pattern":   ("Medium", "Repeated voids by same employee/outlet", "Outlet manager", "Review transaction pattern with the responsible manager; do not assume misconduct."),
    "discount_above_limit":  ("High", "Discount exceeds configured limit", "F&B manager", "Verify policy, approval authority and documented reason."),
    "discount_missing_reason": ("Medium", "Reason not recorded", "Outlet manager", "Request the reason and supporting documentation."),
    "discount_missing_approval": ("High", "Approval missing or pending", "Outlet manager", "Verify approval authority before counting as valid."),
    "nc_missing_reason":     ("Medium", "No justification recorded", "Outlet manager", "Request supporting business purpose and authorisation."),
    "nc_missing_approval":   ("High", "Approval missing or pending", "Outlet manager", "Request authorisation per NC policy."),
    "amenity_high_value":    ("Medium", "Amenity spend above configured value", "Front office / F&B manager", "Review amenity policy, quantity, type and budget."),
    "amenity_missing_approval": ("High", "Approval missing or pending", "Front office manager", "Verify approval and purpose."),
    "amenity_missing_reason": ("Medium", "Purpose not recorded", "Front office manager", "Request purpose of amenity."),
    "duplicate_check":       ("High", "Duplicate row in source export", "Data owner", "Reject duplicate or investigate source export before counting."),
    "amenity_also_nc":       ("Low", "Amenity also booked as NC", "Accounts", "Link the records and prevent double-counting in combined totals."),
    "invoice_rate_mismatch": ("High", "Invoice rate differs from PO rate", "Purchase / store manager", "Verify rate with supplier and PO before payment."),
    "duplicate_invoice":     ("High", "Duplicate invoice number", "Accounts payable", "Hold payment until duplicate is investigated."),
    "stock_shortage":        ("High", "Book stock higher than physical count", "Store / outlet manager", "Recount, check issues/breakage/transfers records, then investigate."),
    "stock_surplus":         ("Low", "Physical count higher than book", "Store manager", "Check unposted receipts or issue entries."),
    "banquet_loss":          ("High", "Direct costs exceed net revenue", "Banquet manager", "Review quote, discount and cost allocation for the event."),
}


def make_alert(flag: str, category: str, ref: str, evidence: str) -> dict:
    priority, cause, owner, action = ACTIONS[flag]
    return {"priority": priority, "category": category, "flag": flag, "reference": ref,
            "evidence": evidence, "likely_cause": cause, "owner": owner,
            "recommended_action": action, "status": "Open"}


def build_alerts(void, disc, nc, amen, combined, inv_ex, inventory, banquet) -> list:
    a = []
    for _, r in void["rows"].iterrows():
        if r.missing_reason: a.append(make_alert("void_missing_reason", "Void", r.check_id, f"{r.outlet}, INR {r.void_amount:g}, {r.business_date}"))
        if r.approval_issue: a.append(make_alert("void_missing_approval", "Void", r.check_id, f"{r.outlet}, INR {r.void_amount:g}, status {r.approval_status}"))
    for _, r in void["repeat_patterns"].iterrows():
        a.append(make_alert("void_repeat_pattern", "Void", r.voided_by, f"{r.void_count} voids at {r.outlet}"))
    for _, r in disc["rows"].iterrows():
        if r.above_limit: a.append(make_alert("discount_above_limit", "Discount", r.check_id, f"{r.discount_pct:g}% vs limit {disc['limit_pct']:g}%"))
        if r.missing_reason: a.append(make_alert("discount_missing_reason", "Discount", r.check_id, f"{r.outlet}, INR {r.discount_amount:g}"))
        if r.approval_issue: a.append(make_alert("discount_missing_approval", "Discount", r.check_id, f"status {r.approval_status}"))
    for _, r in nc["rows"].iterrows():
        if r.missing_reason: a.append(make_alert("nc_missing_reason", "NC", r.check_id, f"{r.outlet}, INR {r.nc_amount:g}"))
        if r.approval_issue: a.append(make_alert("nc_missing_approval", "NC", r.check_id, f"status {r.approval_status}"))
    for _, r in amen["rows"].iterrows():
        if r.high_value: a.append(make_alert("amenity_high_value", "Amenities", r.check_id, f"{r.amenity_type}, INR {r.amount:g}"))
        if r.missing_reason: a.append(make_alert("amenity_missing_reason", "Amenities", r.check_id, f"{r.amenity_type}, INR {r.amount:g}"))
        if r.approval_issue: a.append(make_alert("amenity_missing_approval", "Amenities", r.check_id, f"status {r.approval_status}"))
    for cid in combined["overlap_check_ids"]:
        a.append(make_alert("amenity_also_nc", "NC / Amenities", cid, f"INR {combined['overlap_value']:g} overlap excluded from combined total"))
    for name, d in (("Void", void), ("Discount", disc), ("NC", nc), ("Amenities", amen)):
        for _, r in d["duplicates"].iterrows():
            a.append(make_alert("duplicate_check", name, r.check_id, "Duplicate row excluded from totals"))
    for _, r in inv_ex["duplicates"].iterrows():
        a.append(make_alert("duplicate_invoice", "Purchase", r.invoice_no, f"{r.supplier}"))
    for _, r in inv_ex["rate_mismatches"].iterrows():
        a.append(make_alert("invoice_rate_mismatch", "Purchase", r.invoice_no, f"{r['item']}: PO {r.po_rate:g} vs invoice {r.invoice_rate:g} ({r.rate_diff_pct:g}%), excess INR {r.excess_value:g}"))
    for _, r in inventory.iterrows():
        if r.variance_type == "shortage": a.append(make_alert("stock_shortage", "Inventory", r.item_id, f"{r.item_name} ({r.outlet}): {r.variance_qty:g} short, INR {r.variance_value:g}"))
        if r.variance_type == "surplus": a.append(make_alert("stock_surplus", "Inventory", r.item_id, f"{r.item_name} ({r.outlet}): {abs(r.variance_qty):g} surplus"))
    for _, r in banquet.iterrows():
        if r.gross_profit < 0: a.append(make_alert("banquet_loss", "Banquet", r.event_id, f"{r.event_name}: gross profit INR {r.gross_profit:g}"))
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(a, key=lambda x: order[x["priority"]])
