"""CSV validation shared by the upload API and (later) the AWS Lambda validator.
File-level problems (unreadable, missing column, empty) REJECT the whole file.
Row-level problems reject only those rows. Missing reason / approval are NOT errors:
they are audit exceptions and stay in the data. Duplicate keys are warnings (the calculation
layer counts each key once and reports the duplicate)."""
import io
from collections import defaultdict
import pandas as pd

APPROVAL = {"Approved", "Pending", "Missing", "Rejected"}


def _spec(req, num=(), nonneg=(), date=(), key=(), text=(), enum=None):
    return {"req": list(req), "num": list(num), "nonneg": list(nonneg), "date": list(date),
            "key": list(key), "text": list(text), "enum": enum or {}}


_INV_NUM = ["opening_qty", "purchases_qty", "issues_qty", "returns_qty", "transfers_in", "transfers_out",
            "breakage_qty", "book_closing_qty", "physical_count", "unit_cost"]
_CHK = ["check_id", "business_date", "outlet"]

SPECS = {
    "inventory": _spec(["business_date", "item_id", "item_name", "outlet"] + _INV_NUM, _INV_NUM,
                       [c for c in _INV_NUM if c != "book_closing_qty"], ["business_date"],
                       ["business_date", "item_id", "outlet"], ["item_id", "item_name", "outlet"]),
    "purchases": _spec(["purchase_id", "business_date", "supplier_id", "supplier_name", "item_id", "invoice_no", "po_no", "received_qty", "purchase_rate"],
                       ["received_qty", "purchase_rate"], ["received_qty", "purchase_rate"], ["business_date"],
                       ["purchase_id"], ["purchase_id", "supplier_id", "item_id", "invoice_no"]),
    "invoices": _spec(["invoice_no", "supplier", "item", "po_rate", "invoice_rate", "received_qty", "invoice_date"],
                      ["po_rate", "invoice_rate", "received_qty"], ["po_rate", "invoice_rate", "received_qty"], ["invoice_date"],
                      ["invoice_no"], ["invoice_no", "supplier", "item"]),
    "beo_events": _spec(["event_id", "event_name", "event_date", "covers", "quoted_revenue", "discount_amount", "net_revenue", "food_cost", "beverage_cost", "other_direct_cost"],
                        ["covers", "quoted_revenue", "discount_amount", "net_revenue", "food_cost", "beverage_cost", "other_direct_cost"],
                        ["covers", "quoted_revenue", "discount_amount", "net_revenue", "food_cost", "beverage_cost", "other_direct_cost"],
                        ["event_date"], ["event_id"], ["event_id", "event_name"]),
    "discount_checks": _spec(_CHK + ["original_amount", "discount_amount", "net_amount", "reason", "entered_by", "approved_by", "approval_status"],
                             ["original_amount", "discount_amount", "net_amount"], ["original_amount", "discount_amount", "net_amount"],
                             ["business_date"], ["check_id"], ["check_id", "outlet"], {"approval_status": APPROVAL}),
    "void_checks": _spec(_CHK + ["void_amount", "reason", "voided_by", "approved_by", "approval_status", "remarks"],
                         ["void_amount"], ["void_amount"], ["business_date"], ["check_id"], ["check_id", "outlet"], {"approval_status": APPROVAL}),
    "nc_checks": _spec(_CHK + ["reference_type", "reference_id", "nc_amount", "reason", "entered_by", "approved_by", "approval_status"],
                       ["nc_amount"], ["nc_amount"], ["business_date"], ["check_id"], ["check_id", "outlet"], {"approval_status": APPROVAL}),
    "amenities_checks": _spec(["check_id", "business_date", "room_or_event_ref", "amenity_type", "outlet", "quantity", "amount", "reason", "entered_by", "approved_by", "approval_status"],
                              ["quantity", "amount"], ["quantity", "amount"], ["business_date"], ["check_id"],
                              ["check_id", "amenity_type", "outlet"], {"approval_status": APPROVAL}),
    "sales": _spec(["business_date", "outlet", "category", "net_sales"], ["net_sales"], ["net_sales"], ["business_date"],
                   ["business_date", "outlet", "category"], ["outlet", "category"]),
}
FILE_TYPES = list(SPECS)
MAX_ERRORS = 200


def _blank(s):
    return s.isna() | (s.astype(str).str.strip() == "")


def _fail(code, message, column=None):
    return {"status": "REJECTED", "rows_total": 0, "rows_ok": 0, "rows_rejected": 0,
            "errors": [{"row": None, "column": column, "code": code, "message": message}],
            "warnings": [], "notes": {}, "clean": None}


def validate_csv_bytes(file_type: str, data: bytes) -> dict:
    if file_type not in SPECS:
        return _fail("UNSUPPORTED_FILE_TYPE", f"Unknown file type '{file_type}'. Use one of: {', '.join(FILE_TYPES)}")
    try:
        df = pd.read_csv(io.BytesIO(data), dtype=str)
    except Exception as e:  # unreadable / not a CSV
        return _fail("NOT_A_CSV", f"File could not be read as CSV: {e}")
    return validate_df(file_type, df)


def validate_df(file_type: str, df: pd.DataFrame) -> dict:
    spec = SPECS[file_type]
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in spec["req"] if c not in df.columns]
    if missing:
        res = _fail("MISSING_COLUMN", "", None)
        res["errors"] = [{"row": None, "column": c, "code": "MISSING_COLUMN",
                          "message": f"Required column '{c}' is missing. File rejected; no rows imported."} for c in missing]
        return res
    if df.empty:
        return _fail("EMPTY_FILE", "File has headers but no data rows.")

    errs = defaultdict(list)  # row position -> [(column, code, message)]

    def flag(mask, col, code, msg):
        for pos in mask[mask].index:
            errs[pos].append((col, code, msg))

    for c in spec["num"]:
        s = df[c]; blank = _blank(s); conv = pd.to_numeric(s, errors="coerce")
        flag(blank, c, "MISSING_VALUE", f"'{c}' is empty")
        flag(~blank & conv.isna(), c, "NOT_NUMERIC", f"'{c}' is not a number")
        if c in spec["nonneg"]:
            flag(conv < 0, c, "NEGATIVE_VALUE", f"'{c}' must not be negative")
    for c in spec["date"]:
        s = df[c]; blank = _blank(s)
        parsed = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
        flag(blank | parsed.isna(), c, "BAD_DATE", f"'{c}' must be a date in YYYY-MM-DD format")
    for c in spec["text"]:
        flag(_blank(df[c]), c, "MISSING_VALUE", f"'{c}' is empty")
    for c, allowed in spec["enum"].items():
        s = df[c]; blank = _blank(s)
        flag(blank, c, "MISSING_VALUE", f"'{c}' is empty")
        flag(~blank & ~s.isin(allowed), c, "BAD_VALUE", f"'{c}' must be one of {sorted(allowed)}")

    bad_pos = set(errs)
    valid = ~df.index.isin(bad_pos)
    errors = [{"row": int(p) + 2, "column": c, "code": code, "message": m}
              for p in sorted(errs) for (c, code, m) in errs[p]]
    ok_df = df[valid]
    dup = ok_df.duplicated(subset=spec["key"], keep="first")
    warnings = [{"row": int(p) + 2, "code": "DUPLICATE_KEY",
                 "message": "Key " + "/".join(str(df.at[p, k]) for k in spec["key"]) + " repeated. Counted once in totals and listed as a duplicate."}
                for p in ok_df[dup].index]
    notes = {}
    if "reason" in ok_df.columns:
        notes["missing_reason_rows"] = int(_blank(ok_df["reason"]).sum())
    if "approval_status" in ok_df.columns:
        notes["not_approved_rows"] = int((ok_df["approval_status"] != "Approved").sum())
    rows_ok = int(valid.sum())
    return {"status": "PROCESSED" if rows_ok > 0 else "REJECTED", "rows_total": len(df), "rows_ok": rows_ok,
            "rows_rejected": len(df) - rows_ok, "errors": errors[:MAX_ERRORS], "warnings": warnings[:MAX_ERRORS],
            "notes": notes, "clean": ok_df}
