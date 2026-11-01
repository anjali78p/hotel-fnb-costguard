import pathlib
import pytest
from fastapi.testclient import TestClient

SAMPLE = pathlib.Path(__file__).resolve().parent.parent / "sample_data"

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("COSTGUARD_UPLOAD_DIR", str(tmp_path / "up"))
    from backend.main import app
    return TestClient(app)

def post(client, name, ftype, content=None):
    content = content if content is not None else (SAMPLE / name).read_bytes()
    return client.post("/api/upload", files={"file": (name, content, "text/csv")}, data={"file_type": ftype})

def test_valid_upload_flows_to_dashboard(client):
    r = post(client, "void_checks.csv", "void_checks").json()
    assert r["status"] == "PROCESSED" and r["rows_ok"] == 9 and r["warnings"][0]["code"] == "DUPLICATE_KEY"
    d = client.get("/api/dashboard").json()
    assert d["voids"] == {"count": 8, "amount": 17200}
    assert client.get(f"/api/uploads/{r['file_id']}").json()["status"] == "PROCESSED"

def test_new_data_replaces_sample_then_reset(client):
    csv = (b"check_id,business_date,outlet,void_amount,reason,voided_by,approved_by,approval_status,remarks\n"
           b"X1,2026-11-01,Bar,500,Test,E1,M1,Approved,\nX2,2026-11-01,Bar,250,,E1,,Missing,\n")
    assert post(client, "my_voids.csv", "void_checks", csv).json()["status"] == "PROCESSED"
    v = client.get("/api/voids").json()
    assert v["kpi"]["count"] == 2 and v["kpi"]["amount"] == 750
    flags = {a["flag"] for a in client.get("/api/alerts").json()["alerts"]}
    assert {"void_missing_reason", "void_missing_approval"} <= flags
    assert client.post("/api/uploads/reset").json()["status"] == "RESET"
    assert client.get("/api/voids").json()["kpi"]["count"] == 8

def test_same_file_twice_is_skipped(client):
    assert post(client, "nc_checks.csv", "nc_checks").json()["status"] == "PROCESSED"
    assert post(client, "nc_checks.csv", "nc_checks").json()["status"] == "SKIPPED_DUPLICATE_FILE"
    assert len(client.get("/api/uploads").json()["files"]) == 1

def test_missing_column_is_rejected_and_data_unchanged(client):
    r = post(client, "bad.csv", "inventory", (SAMPLE / "invalid/inventory_missing_column.csv").read_bytes()).json()
    assert r["status"] == "REJECTED" and r["errors"][0]["column"] == "physical_count"
    assert client.get("/api/inventory").json()["kpi"]["amount"] == 5015

def test_unsupported_type_is_400(client):
    assert post(client, "x.csv", "bogus", b"a\n1").status_code == 400
