# Expected results for sample_data (verify dashboard against these; script: docs/calc_check.py)

## Inventory
- LQ002 Absolut Vodka (Bar): shortage 3 bottles = INR 5,400
- FD001 Rice: shortage 1 kg = INR 95
- FD003 Chicken: surplus 2 kg = INR -480
- Net variance value: INR 5,015 | Book closing matches formula for all rows

## Banquet
| Event | Net revenue | Gross profit | Margin |
|---|---|---|---|
| EV001 | 600000 | 285000 | 47.50% |
| EV002 | 240000 | 98000 | 40.83% |
| EV003 | 120000 | -20000 | -16.67% (loss) |
| EV004 | 215000 | 97000 | 45.12% |
| EV005 | 0 | -5000 | null (zero revenue must not crash) |

## Checks & Revenue Control
| Category | Unique count | Amount | Exceptions planted |
|---|---|---|---|
| Discounts | 9 (1 duplicate DC009) | 7,620 | DC003 no reason; DC004 pending, DC006 missing approval; DC002 25%, DC003 40%, DC006 35% high; DC007 zero original |
| Voids | 8 (1 duplicate VD008) | 17,200 | VD002 no reason; VD003 no approval; EMP103 repeats at Bar (VD002, VD003, VD005, VD006) |
| NC | 5 | 10,500 | NC002 no reason; NC004 no approval |
| Amenities | 5 | 20,450 | AM004 no reason/approval; AM003 and AM005 high value |
| Overlap | NC003 = AM001 | 650 | Combined NC + Amenities = 30,300 (not 30,950) |

## Validation tests (sample_data/invalid/)
- inventory_missing_column.csv -> error naming `physical_count`
- inventory_bad_values.csv -> row errors: negative physical_count, non-numeric purchases_qty, bad date format
- invoices.csv: INV-1005 duplicate; INV-1005 rate mismatch 240 vs 262 (+9.2%)
