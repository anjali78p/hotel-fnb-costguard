# Data Dictionary & Conventions (Member 1 + Member 2 to agree on Day 1)

## Global conventions
- Dates: `YYYY-MM-DD` | Currency: INR (plain numbers, no symbol/commas) | IDs: text, unique per file
- Empty `reason` / `approved_by` = missing (exception). `approval_status`: Approved / Pending / Missing / Rejected
- Room refs are masked (`RM-XX12`). Only fabricated data in repo.

## Conventions TO CONFIRM (assumed for prototype)
| Topic | Assumed convention |
|---|---|
| Expected closing | opening + purchases + transfers_in + returns - issues - transfers_out - breakage |
| Returns | returns to stock (added back) |
| Variance qty | book_closing - physical_count. **Positive = shortage, negative = surplus** |
| Variance value | variance_qty x unit_cost |
| Policy limits (discount %, etc.) | Configurable in a config file; NOT hard-coded, hotel policy not assumed |

## Files
| File | Key | Fields |
|---|---|---|
| inventory.csv | business_date+item_id+outlet | opening_qty, purchases_qty, issues_qty, returns_qty, transfers_in, transfers_out, breakage_qty, book_closing_qty, physical_count, unit_cost |
| purchases.csv | purchase_id | business_date, supplier_id, supplier_name, item_id, invoice_no, po_no, received_qty, purchase_rate |
| invoices.csv | invoice_no | supplier, item, po_rate, invoice_rate, received_qty, invoice_date |
| beo_events.csv | event_id | event_name, event_date, covers, quoted_revenue, discount_amount, net_revenue, food_cost, beverage_cost, other_direct_cost |
| discount_checks.csv | check_id | business_date, outlet, original_amount, discount_amount, net_amount, reason, entered_by, approved_by, approval_status |
| void_checks.csv | check_id | business_date, outlet, void_amount, reason, voided_by, approved_by, approval_status, remarks |
| nc_checks.csv | check_id | business_date, outlet, reference_type, reference_id, nc_amount, reason, entered_by, approved_by, approval_status |
| amenities_checks.csv | check_id | business_date, room_or_event_ref, amenity_type, outlet, quantity, amount, reason, entered_by, approved_by, approval_status |

## Formulas
- Banquet GP = net_revenue - food_cost - beverage_cost - other_direct_cost
- Banquet margin % = GP / net_revenue x 100 (null if net_revenue <= 0)
- Discount % = discount_amount / original_amount x 100 (null if original = 0)
- F&B cost % = consumption cost / net F&B sales x 100
- Void/NC/Amenity totals: count unique check_id only; duplicates reported separately
- NC with `reference_type = AMENITY` and `reference_id` in amenities -> overlap; exclude from combined total

## Draft API response shapes
KPI: `{"count": 8, "amount": 17200, "period": {"from": "2026-10-01", "to": "2026-10-07"}, "currency": "INR", "data_freshness": "2026-10-31T10:00:00Z"}`
Report: `{"rows": [...], "meta": {"total_rows": 9, "duplicates_excluded": 1, "rejected_rows": 0, "exceptions": [...]}}`
