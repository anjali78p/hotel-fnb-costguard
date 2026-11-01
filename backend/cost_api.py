"""Cost analysis endpoint (Day 5). Included from main.py via app.include_router(router)."""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query
from . import calculations as calc
from .data_access import load

router = APIRouter()


@router.get("/api/cost")
def cost(date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None)):
    r = calc.consumption_by_category(load("inventory", date_from, date_to), load("sales", date_from, date_to))
    items = r["items"][["business_date", "item_id", "item_name", "outlet", "category", "consumption_qty", "unit_cost", "consumption_cost"]]
    return {"kpi": {"overall_cost_pct": r["overall_cost_pct"], "total_cost": r["total_cost"], "total_sales": r["total_sales"],
                    "period": {"from": date_from, "to": date_to}, "currency": "INR",
                    "data_freshness": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "by_category": r["rows"], "items": json.loads(items.to_json(orient="records")),
            "meta": {"formula": "consumption = opening + purchases + transfers in + returns - transfers out - physical count; cost % = cost / net sales x 100",
                     "note": "Convention for breakage, returns and transfers to be confirmed with the hotel. Budget comparison needs budget data (not yet loaded)."}}
