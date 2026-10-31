from backend.calculations import inventory_variance, fnb_cost_pct, consumption_cost

def test_book_matches_expected_closing(load):
    r = inventory_variance(load("inventory.csv"))
    assert (r.book_vs_expected_diff == 0).all()

def test_vodka_shortage(load):
    r = inventory_variance(load("inventory.csv"))
    row = r[r.item_id == "LQ002"].iloc[0]
    assert row.variance_qty == 3 and row.variance_value == 5400 and row.variance_type == "shortage"

def test_chicken_surplus(load):
    r = inventory_variance(load("inventory.csv"))
    row = r[r.item_id == "FD003"].iloc[0]
    assert row.variance_qty == -2 and row.variance_value == -480 and row.variance_type == "surplus"

def test_net_variance_value(load):
    assert inventory_variance(load("inventory.csv")).variance_value.sum() == 5015

def test_cost_pct_and_zero_sales():
    assert fnb_cost_pct(30000, 100000) == 30.0
    assert fnb_cost_pct(30000, 0) is None

def test_consumption_cost():
    assert consumption_cost(50000, 20000, 15000) == 55000
