# Hotel F&B CostGuard

A cloud-ready control tower for hotel food, beverage and liquor cost, inventory exceptions, banquet profitability and revenue-control checks (voids, discounts, NC and amenities). It turns daily CSV records into validated data, KPIs, exception flags and recommended corrective actions.

> **Fabricated data only.** All records in this repo are dummy data. Never commit real guest, employee, supplier or hotel financial data, and never commit access keys or passwords.

## What it does

| Module | What the dashboard shows |
|---|---|
| Overview | F&B cost %, void, discount, NC and amenities totals, stock variance, banquet gross profit |
| Checks & Revenue Control | Void, discount, NC and amenities KPI cards, outlet and reason charts, transaction-level tables with review flags |
| Cost analysis | Consumption cost and cost % for Food, Beverage and overall |
| Inventory | Expected closing, book vs physical count, variance quantity and value |
| Banquet profitability | Net revenue, direct costs, gross profit and margin per event |
| Corrective actions | Priority, evidence, likely cause, owner and recommended action for every exception |
| Upload data | Upload a CSV, validate it, and see the result on the dashboard |

Flags mean **"review needed"**, not misconduct. NC and amenities are reported separately, and an amenity that is also booked as an NC is counted once in the combined total.

## How it works

```
CSV upload (or sample_data/)
  -> validation.py       checks columns, types, dates, negatives, duplicates
  -> data_access.py      loads data, applies date and outlet filters
  -> calculations.py     variance, cost %, banquet profit, check totals, flags
  -> recommendations.py  turns flags into evidence, cause, owner, action
  -> FastAPI endpoints   JSON for the dashboard
  -> frontend            KPI cards, Chart.js charts, tables
```

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/anjali78p/hotel-fnb-costguard.git
cd hotel-fnb-costguard
pip install -r requirements.txt
python -m pytest -q
uvicorn backend.main:app --reload
```

Open the server URL in a browser. The dashboard is served at `/` and the interactive API docs at `/docs`. In GitHub Codespaces, use the "Open in Browser" popup.

If `/` shows a 404, the dashboard mount is missing from `backend/main.py`. Add these lines at the end of the file:

```python
# Serve dashboard
import pathlib
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=pathlib.Path(__file__).resolve().parent.parent / "frontend", html=True), name="frontend")
```

`patch_main.py` and `patch_day6.py` are one-time helper scripts that register the cost and upload routers in `backend/main.py`. They are safe to run again and do nothing if already applied.

## Project structure

```
hotel-fnb-costguard/
  backend/
    main.py              FastAPI app and core endpoints
    cost_api.py          /api/cost endpoint
    upload_api.py        upload, status and reset endpoints
    validation.py        CSV validation (reusable in AWS Lambda)
    calculations.py      all business formulas
    recommendations.py   flag -> recommended action mapping
    data_access.py       data loader (CSV now, RDS later)
    config.py            configurable limits (placeholders)
  frontend/              index.html, style.css, dashboard.js
  sample_data/           dummy CSVs with planted test cases
    invalid/             bad files for validation tests
  database/schema.sql    draft PostgreSQL schema
  docs/                  data dictionary, expected results, hand-check script
  tests/                 45 automated tests
  .github/workflows/     CI: runs pytest on every push and pull request
```

## API

All endpoints are GET unless noted. Dates use `YYYY-MM-DD`. Currency is INR.

| Endpoint | Filters | Returns |
|---|---|---|
| `/api/dashboard` | date_from, date_to, outlet | Overview totals |
| `/api/voids` | date_from, date_to, outlet | KPI, rows, duplicates, repeat patterns |
| `/api/discounts` | date_from, date_to, outlet, limit_pct | KPI, average discount %, rows with flags |
| `/api/nc-checks` | date_from, date_to, outlet | KPI, rows with flags |
| `/api/amenities` | date_from, date_to, outlet | KPI, rows with flags |
| `/api/inventory` | date_from, date_to, outlet | Stock variance rows and net value |
| `/api/banquets` | date_from, date_to | Event profit and margin |
| `/api/invoices` | none | Duplicate invoices and rate mismatches |
| `/api/cost` | date_from, date_to | Cost % by category and item |
| `/api/alerts` | date_from, date_to, outlet, priority | Corrective actions, High first |
| `POST /api/upload` | form: file, file_type | Validation result |
| `/api/uploads`, `/api/uploads/{id}` | none | Upload history and status |
| `POST /api/uploads/reset` | none | Removes uploaded data, back to sample data |

## Data and formulas

| Metric | Formula |
|---|---|
| Expected closing | opening + purchases + transfers in + returns - issues - transfers out - breakage |
| Stock variance | book closing - physical count (positive = shortage, negative = surplus) |
| Variance value | variance quantity x unit cost |
| Consumption cost | (opening + purchases + transfers in + returns - transfers out - physical count) x unit cost |
| F&B cost % | consumption cost / net sales x 100 |
| Banquet gross profit | net revenue - food - beverage - other direct cost |
| Banquet margin % | gross profit / net revenue x 100 (null when revenue is 0) |
| Discount % | discount / original amount x 100 |
| Void, NC, amenity totals | unique check IDs only; duplicates are reported separately |

Full column definitions: [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md). Numbers the dashboard should show for the sample data: [docs/EXPECTED_RESULTS.md](docs/EXPECTED_RESULTS.md).

## Upload and validation

Upload from the **Upload data** page or with `POST /api/upload` (`file` and `file_type`). Supported types: inventory, purchases, invoices, beo_events, discount_checks, void_checks, nc_checks, amenities_checks, sales.

- A missing required column **rejects the whole file** and names the column.
- Negative or non-numeric values and bad dates reject **only those rows**, with row number and column.
- Missing reasons and approvals are **kept** and flagged as audit exceptions.
- Duplicate keys are warnings and are counted once in totals.
- Uploading the identical file again is skipped.
- A valid file replaces the data for that file type. Rejected files go to `uploaded_data/quarantine/`.

Try it with `sample_data/invalid/inventory_missing_column.csv` and `sample_data/void_checks.csv`.

## Testing

```bash
python -m pytest -q
```

Tests cover inventory variance, cost %, banquet profit, discount, void, NC and amenity checks, no double-counting, invoice exceptions, validation rules, upload flow and every API endpoint. Expected values were checked independently with `python docs/calc_check.py`. GitHub Actions runs the suite on every push and pull request.

## Assumptions to confirm with the hotel

- Returns are added back to stock, and variance sign is book minus physical.
- Closing value uses the physical count, so breakage and shortage fall inside consumption cost.
- Limits in `backend/config.py` (discount 20%, amenity value 5,000, repeat voids 3) are **placeholders**, not hotel policy.
- Food and Beverage are identified from the `item_id` prefix (FD, LQ) until a `category` column is added.

## AWS architecture and status

| Component | Purpose | Status |
|---|---|---|
| Local FastAPI + CSV data | Prototype and tests | Done |
| Validation module | Reusable in Lambda | Done |
| `database/schema.sql` | RDS PostgreSQL tables | Draft, not yet run on a live database |
| S3 + Lambda | Raw uploads and event-triggered validation | Planned (Member 2) |
| RDS PostgreSQL | Business records | Planned (Member 2) |
| DynamoDB | File status, idempotency, alert status | Planned (Member 2) |
| Docker, ECR, ECS Fargate | Backend deployment | Planned (Member 2) |
| IAM, VPC, Secrets Manager, KMS, CloudWatch, CloudTrail | Security and monitoring | Planned (Member 2) |

Switching to RDS only requires changing `backend/data_access.py`; calculations and the dashboard stay the same.

## Known limitations

- No authentication, and CORS is open. Fine for a local prototype; restrict both before any public deployment.
- No budget comparison yet, and cost % uses a single day of inventory.
- Alert status is always "Open" until a status store is connected.


