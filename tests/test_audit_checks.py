from backend.calculations import (discount_summary, void_summary, nc_summary, amenities_summary,
                                  combined_nc_amenities, invoice_exceptions)

def test_discounts(load):
    s = discount_summary(load("discount_checks.csv"), limit_pct=20)
    assert s["count"] == 9 and len(s["duplicates"]) == 1 and s["amount"] == 7620
    rows = s["rows"].set_index("check_id")
    assert rows.loc["DC003", "missing_reason"]
    assert rows.loc["DC006", "approval_issue"] and rows.loc["DC004", "approval_issue"]
    assert set(rows[rows.above_limit].index) == {"DC002", "DC003", "DC006"}
    assert rows.loc["DC007", "discount_pct"] != rows.loc["DC007", "discount_pct"]  # NaN, zero original

def test_voids(load):
    s = void_summary(load("void_checks.csv"), repeat_min=3)
    assert s["count"] == 8 and len(s["duplicates"]) == 1 and s["amount"] == 17200
    rows = s["rows"].set_index("check_id")
    assert rows.loc["VD002", "missing_reason"] and rows.loc["VD003", "approval_issue"]
    rp = s["repeat_patterns"]
    assert list(rp.voided_by) == ["EMP103"] and rp.iloc[0].void_count == 4

def test_nc(load):
    s = nc_summary(load("nc_checks.csv"))
    assert s["count"] == 5 and s["amount"] == 10500
    rows = s["rows"].set_index("check_id")
    assert rows.loc["NC002", "missing_reason"] and rows.loc["NC004", "approval_issue"]

def test_amenities(load):
    s = amenities_summary(load("amenities_checks.csv"), high_value=5000)
    assert s["count"] == 5 and s["amount"] == 20450
    rows = s["rows"].set_index("check_id")
    assert set(rows[rows.high_value].index) == {"AM003", "AM005"}
    assert rows.loc["AM004", "missing_reason"] and rows.loc["AM004", "approval_issue"]

def test_no_double_counting(load):
    c = combined_nc_amenities(load("nc_checks.csv"), load("amenities_checks.csv"))
    assert c["overlap_check_ids"] == ["NC003"] and c["overlap_value"] == 650
    assert c["combined_total"] == 30300

def test_invoice_exceptions(load):
    r = invoice_exceptions(load("invoices.csv"))
    assert r["unique_invoices"] == 6 and len(r["duplicates"]) == 1
    m = r["rate_mismatches"].iloc[0]
    assert m.invoice_no == "INV-1005" and m.rate_diff_pct == 9.17 and m.excess_value == 660
