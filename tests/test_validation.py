import pathlib
import pytest
from backend.validation import validate_csv_bytes, FILE_TYPES

SAMPLE = pathlib.Path(__file__).resolve().parent.parent / "sample_data"

@pytest.mark.parametrize("ftype,fname", [
    ("inventory", "inventory.csv"), ("purchases", "purchases.csv"), ("invoices", "invoices.csv"),
    ("beo_events", "beo_events.csv"), ("discount_checks", "discount_checks.csv"), ("void_checks", "void_checks.csv"),
    ("nc_checks", "nc_checks.csv"), ("amenities_checks", "amenities_checks.csv"), ("sales", "sales.csv")])
def test_sample_files_are_valid(ftype, fname):
    r = validate_csv_bytes(ftype, (SAMPLE / fname).read_bytes())
    assert r["status"] == "PROCESSED" and r["rows_rejected"] == 0 and r["errors"] == []

def test_all_types_have_a_sample():
    assert len(FILE_TYPES) == 9

def test_duplicates_are_warnings_not_errors():
    for ftype, fname, n in [("discount_checks", "discount_checks.csv", 1), ("void_checks", "void_checks.csv", 1), ("invoices", "invoices.csv", 1)]:
        r = validate_csv_bytes(ftype, (SAMPLE / fname).read_bytes())
        assert [w["code"] for w in r["warnings"]] == ["DUPLICATE_KEY"] * n

def test_missing_reason_and_approval_are_kept_with_notes():
    r = validate_csv_bytes("void_checks", (SAMPLE / "void_checks.csv").read_bytes())
    assert r["rows_ok"] == 9 and r["notes"]["missing_reason_rows"] == 1 and r["notes"]["not_approved_rows"] == 1

def test_missing_column_rejects_whole_file():
    r = validate_csv_bytes("inventory", (SAMPLE / "invalid/inventory_missing_column.csv").read_bytes())
    assert r["status"] == "REJECTED" and r["rows_ok"] == 0
    assert r["errors"][0]["code"] == "MISSING_COLUMN" and r["errors"][0]["column"] == "physical_count"

def test_bad_values_give_row_level_errors():
    r = validate_csv_bytes("inventory", (SAMPLE / "invalid/inventory_bad_values.csv").read_bytes())
    got = {(e["row"], e["column"], e["code"]) for e in r["errors"]}
    assert (2, "physical_count", "NEGATIVE_VALUE") in got
    assert (3, "purchases_qty", "NOT_NUMERIC") in got and (3, "business_date", "BAD_DATE") in got
    assert r["status"] == "REJECTED" and r["rows_rejected"] == 2

def test_partial_file_imports_good_rows():
    csv = b"check_id,business_date,outlet,void_amount,reason,voided_by,approved_by,approval_status,remarks\n" \
          b"V1,2026-10-01,Bar,100,x,E1,M1,Approved,\nV2,2026-10-01,Bar,-5,x,E1,M1,Approved,\nV3,2026-10-02,Bar,abc,x,E1,M1,Bogus,\n"
    r = validate_csv_bytes("void_checks", csv)
    assert r["status"] == "PROCESSED" and r["rows_ok"] == 1 and r["rows_rejected"] == 2
    assert {e["code"] for e in r["errors"]} == {"NEGATIVE_VALUE", "NOT_NUMERIC", "BAD_VALUE"}

def test_unsupported_type_and_garbage():
    assert validate_csv_bytes("nope", b"a,b\n1,2")["errors"][0]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert validate_csv_bytes("sales", b"")["status"] == "REJECTED"
