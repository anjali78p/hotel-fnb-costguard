from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)

def test_dashboard_totals():
    d = c.get("/api/dashboard").json()
    assert d["voids"] == {"count": 8, "amount": 17200}
    assert d["discounts"]["count"] == 9 and d["discounts"]["amount"] == 7620
    assert d["nc"]["amount"] == 10500 and d["amenities"]["amount"] == 20450
    assert d["nc_amenities_combined"]["combined_total"] == 30300
    assert d["stock_variance_value"] == 5015 and d["currency"] == "INR"

def test_void_filter_outlet_and_dates():
    r = c.get("/api/voids", params={"outlet": "Bar"}).json()
    assert r["kpi"]["count"] == 4 and r["kpi"]["amount"] == 10000
    r = c.get("/api/voids", params={"date_from": "2026-10-05", "date_to": "2026-10-06"}).json()
    assert r["kpi"]["count"] == 3 and r["meta"]["duplicates_excluded"] == 1

def test_discount_limit_override():
    r = c.get("/api/discounts", params={"limit_pct": 30}).json()
    flagged = {x["check_id"] for x in r["rows"] if x["above_limit"]}
    assert flagged == {"DC003", "DC006"}

def test_zero_revenue_margin_is_null():
    rows = {x["event_id"]: x for x in c.get("/api/banquets").json()["rows"]}
    assert rows["EV005"]["margin_pct"] is None and rows["EV003"]["margin_pct"] == -16.67

def test_alerts_contents_and_priority_filter():
    r = c.get("/api/alerts").json()
    flags = {a["flag"] for a in r["alerts"]}
    assert {"void_missing_approval", "discount_above_limit", "stock_shortage", "banquet_loss",
            "amenity_also_nc", "invoice_rate_mismatch", "duplicate_check", "duplicate_invoice"} <= flags
    assert r["alerts"][0]["priority"] == "High"
    high = c.get("/api/alerts", params={"priority": "High"}).json()
    assert all(a["priority"] == "High" for a in high["alerts"])

def test_inventory_and_invoices():
    assert c.get("/api/inventory", params={"outlet": "Bar"}).json()["kpi"]["amount"] == 5400
    assert c.get("/api/invoices").json()["rate_mismatches"][0]["invoice_no"] == "INV-1005"
