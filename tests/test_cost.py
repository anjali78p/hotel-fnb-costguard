from backend.calculations import consumption_by_category, inventory_variance

def test_cost_by_category(load):
    r = consumption_by_category(load("inventory.csv"), load("sales.csv"))
    rows = {x["category"]: x for x in r["rows"]}
    assert rows["Food"]["consumption_cost"] == 30045 and rows["Food"]["net_sales"] == 100000 and abs(rows["Food"]["cost_pct"] - 30.05) <= 0.011
    assert rows["Beverage"]["consumption_cost"] == 97180 and rows["Beverage"]["cost_pct"] == 30.37
    assert r["total_cost"] == 127225 and r["total_sales"] == 420000 and r["overall_cost_pct"] == 30.29

def test_transfer_nets_out(load):
    r = consumption_by_category(load("inventory.csv"), load("sales.csv"))
    it = r["items"]
    assert it[it.item_id == "LQ004"].consumption_qty.sum() == 9   # transfer Bar->Banquet cancels

def test_api_cost():
    from fastapi.testclient import TestClient
    from backend.main import app
    d = TestClient(app).get("/api/cost").json()
    assert d["kpi"]["overall_cost_pct"] == 30.29
