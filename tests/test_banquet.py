import pandas as pd
from backend.calculations import banquet_profitability

def test_event_profit_and_margin(load):
    r = banquet_profitability(load("beo_events.csv")).set_index("event_id")
    assert r.loc["EV001", "gross_profit"] == 285000 and r.loc["EV001", "margin_pct"] == 47.5
    assert r.loc["EV002", "margin_pct"] == 40.83
    assert r.loc["EV004", "margin_pct"] == 45.12

def test_loss_making_event(load):
    r = banquet_profitability(load("beo_events.csv")).set_index("event_id")
    assert r.loc["EV003", "gross_profit"] == -20000 and r.loc["EV003", "margin_pct"] == -16.67

def test_zero_revenue_is_safe(load):
    r = banquet_profitability(load("beo_events.csv")).set_index("event_id")
    assert r.loc["EV005", "gross_profit"] == -5000 and pd.isna(r.loc["EV005", "margin_pct"])
