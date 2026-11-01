-- Hotel F&B CostGuard: PostgreSQL schema (DRAFT by Member 1, for Member 2 to review and run on RDS)
-- Conventions: dates are DATE (ISO), money is NUMERIC(14,2) in INR, quantities NUMERIC(14,3).
-- Every table keeps source_file + imported_at so a bad import can be traced and rolled back.
-- Duplicate keys in a file are NOT inserted; the loader writes them to rejected_rows instead,
-- which is what the API reports as "duplicates_excluded".

CREATE TABLE IF NOT EXISTS inventory_movements (
    business_date     DATE          NOT NULL,
    item_id           TEXT          NOT NULL,
    item_name         TEXT          NOT NULL,
    outlet            TEXT          NOT NULL,
    category          TEXT,                                  -- Food / Beverage (replaces item_id prefix rule)
    opening_qty       NUMERIC(14,3) NOT NULL CHECK (opening_qty >= 0),
    purchases_qty     NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (purchases_qty >= 0),
    issues_qty        NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (issues_qty >= 0),
    returns_qty       NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (returns_qty >= 0),
    transfers_in      NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (transfers_in >= 0),
    transfers_out     NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (transfers_out >= 0),
    breakage_qty      NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (breakage_qty >= 0),
    book_closing_qty  NUMERIC(14,3) NOT NULL,
    physical_count    NUMERIC(14,3) NOT NULL CHECK (physical_count >= 0),
    unit_cost         NUMERIC(14,2) NOT NULL CHECK (unit_cost >= 0),
    source_file       TEXT,
    imported_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, item_id, outlet)
);

CREATE TABLE IF NOT EXISTS purchases (
    purchase_id    TEXT PRIMARY KEY,
    business_date  DATE          NOT NULL,
    supplier_id    TEXT          NOT NULL,
    supplier_name  TEXT          NOT NULL,
    item_id        TEXT          NOT NULL,
    invoice_no     TEXT          NOT NULL,
    po_no          TEXT,
    received_qty   NUMERIC(14,3) NOT NULL CHECK (received_qty >= 0),
    purchase_rate  NUMERIC(14,2) NOT NULL CHECK (purchase_rate >= 0),
    source_file    TEXT,
    imported_at    TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_purchases_invoice ON purchases (invoice_no);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_no    TEXT PRIMARY KEY,
    supplier      TEXT          NOT NULL,
    item          TEXT          NOT NULL,
    po_rate       NUMERIC(14,2) NOT NULL CHECK (po_rate >= 0),
    invoice_rate  NUMERIC(14,2) NOT NULL CHECK (invoice_rate >= 0),
    received_qty  NUMERIC(14,3) NOT NULL CHECK (received_qty >= 0),
    invoice_date  DATE          NOT NULL,
    source_file   TEXT,
    imported_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS beo_events (
    event_id            TEXT PRIMARY KEY,
    event_name          TEXT          NOT NULL,
    event_date          DATE          NOT NULL,
    covers              INTEGER       NOT NULL DEFAULT 0 CHECK (covers >= 0),
    quoted_revenue      NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_amount     NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_revenue         NUMERIC(14,2) NOT NULL DEFAULT 0,
    food_cost           NUMERIC(14,2) NOT NULL DEFAULT 0,
    beverage_cost       NUMERIC(14,2) NOT NULL DEFAULT 0,
    other_direct_cost   NUMERIC(14,2) NOT NULL DEFAULT 0,
    source_file         TEXT,
    imported_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sales (
    business_date  DATE          NOT NULL,
    outlet         TEXT          NOT NULL,
    category       TEXT          NOT NULL,                  -- Food / Beverage
    net_sales      NUMERIC(14,2) NOT NULL CHECK (net_sales >= 0),
    source_file    TEXT,
    imported_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, outlet, category)
);

CREATE TABLE IF NOT EXISTS discount_checks (
    check_id         TEXT PRIMARY KEY,
    business_date    DATE          NOT NULL,
    outlet           TEXT          NOT NULL,
    original_amount  NUMERIC(14,2) NOT NULL CHECK (original_amount >= 0),
    discount_amount  NUMERIC(14,2) NOT NULL CHECK (discount_amount >= 0),
    net_amount       NUMERIC(14,2) NOT NULL,
    reason           TEXT,                                  -- NULL/blank = missing reason (kept, not rejected)
    entered_by       TEXT,
    approved_by      TEXT,
    approval_status  TEXT          NOT NULL CHECK (approval_status IN ('Approved','Pending','Missing','Rejected')),
    source_file      TEXT,
    imported_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS void_checks (
    check_id         TEXT PRIMARY KEY,
    business_date    DATE          NOT NULL,
    outlet           TEXT          NOT NULL,
    void_amount      NUMERIC(14,2) NOT NULL CHECK (void_amount >= 0),
    reason           TEXT,
    voided_by        TEXT,
    approved_by      TEXT,
    approval_status  TEXT          NOT NULL CHECK (approval_status IN ('Approved','Pending','Missing','Rejected')),
    remarks          TEXT,
    source_file      TEXT,
    imported_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nc_checks (
    check_id         TEXT PRIMARY KEY,
    business_date    DATE          NOT NULL,
    outlet           TEXT          NOT NULL,
    reference_type   TEXT,
    reference_id     TEXT,
    nc_amount        NUMERIC(14,2) NOT NULL CHECK (nc_amount >= 0),
    reason           TEXT,
    entered_by       TEXT,
    approved_by      TEXT,
    approval_status  TEXT          NOT NULL CHECK (approval_status IN ('Approved','Pending','Missing','Rejected')),
    source_file      TEXT,
    imported_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- Used to detect NC rows that are really amenities (overlap rule)
CREATE INDEX IF NOT EXISTS idx_nc_reference ON nc_checks (reference_type, reference_id);

CREATE TABLE IF NOT EXISTS amenities_checks (
    check_id           TEXT PRIMARY KEY,
    business_date      DATE          NOT NULL,
    room_or_event_ref  TEXT,                                -- keep masked, e.g. RM-XX12
    amenity_type       TEXT          NOT NULL,
    outlet             TEXT          NOT NULL,
    quantity           NUMERIC(14,3) NOT NULL CHECK (quantity >= 0),
    amount             NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    reason             TEXT,
    entered_by         TEXT,
    approved_by        TEXT,
    approval_status    TEXT          NOT NULL CHECK (approval_status IN ('Approved','Pending','Missing','Rejected')),
    source_file        TEXT,
    imported_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Rows not imported (duplicates, invalid values). Powers "duplicates_excluded" / "rejected rows" in the API.
CREATE TABLE IF NOT EXISTS rejected_rows (
    id           BIGSERIAL PRIMARY KEY,
    source_file  TEXT        NOT NULL,
    file_type    TEXT        NOT NULL,                      -- e.g. void_checks
    row_number   INTEGER,
    reject_type  TEXT        NOT NULL,                      -- DUPLICATE_KEY / INVALID_VALUE / MISSING_COLUMN
    detail       TEXT,
    raw_row      JSONB,
    rejected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rejected_file ON rejected_rows (file_type, source_file);

-- Common filter indexes (date range + outlet filters used by the dashboard)
CREATE INDEX IF NOT EXISTS idx_inv_date   ON inventory_movements (business_date, outlet);
CREATE INDEX IF NOT EXISTS idx_disc_date  ON discount_checks (business_date, outlet);
CREATE INDEX IF NOT EXISTS idx_void_date  ON void_checks (business_date, outlet);
CREATE INDEX IF NOT EXISTS idx_nc_date    ON nc_checks (business_date, outlet);
CREATE INDEX IF NOT EXISTS idx_amen_date  ON amenities_checks (business_date, outlet);
