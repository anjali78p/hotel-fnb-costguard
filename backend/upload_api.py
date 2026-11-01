"""Local upload flow: upload -> validate -> store -> dashboard.
Valid files replace the dataset for that file type (latest upload wins) in uploaded_data/.
Rejected files are kept in uploaded_data/quarantine/. In AWS the same steps become S3 + Lambda + RDS."""
import hashlib, json, shutil
from datetime import datetime, timezone
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from .data_access import get_upload_dir
from .validation import SPECS, FILE_TYPES, validate_csv_bytes

router = APIRouter()
MAX_BYTES = 5 * 1024 * 1024


def _state():
    d = get_upload_dir(); d.mkdir(parents=True, exist_ok=True)
    p = d / "status.json"
    return d, p, (json.loads(p.read_text()) if p.exists() else {"files": {}, "hashes": {}})


@router.post("/api/upload")
async def upload(file: UploadFile = File(...), file_type: str = Form(...)):
    data = await file.read()
    if file_type not in SPECS:
        return JSONResponse({"error": "UNSUPPORTED_FILE_TYPE", "allowed": FILE_TYPES}, status_code=400)
    if len(data) > MAX_BYTES:
        return JSONResponse({"error": "FILE_TOO_LARGE", "max_bytes": MAX_BYTES}, status_code=400)
    d, sp, st = _state()
    digest = hashlib.sha256(data).hexdigest()
    key = f"{file_type}:{digest}"
    if key in st["hashes"]:
        prev = st["files"][st["hashes"][key]]
        return {**prev, "status": "SKIPPED_DUPLICATE_FILE", "message": "Identical file already processed; nothing imported again."}
    res = validate_csv_bytes(file_type, data)
    clean = res.pop("clean")
    now = datetime.now(timezone.utc)
    fid = now.strftime("f_%Y%m%d_%H%M%S_") + digest[:6]
    if res["status"] == "PROCESSED":
        clean.to_csv(d / f"{file_type}.csv", index=False)
        st["hashes"][key] = fid
    else:
        (d / "quarantine").mkdir(exist_ok=True)
        (d / "quarantine" / f"{fid}_{file_type}.csv").write_bytes(data)
    rec = {"file_id": fid, "file_type": file_type, "filename": file.filename,
           "uploaded_at": now.isoformat(timespec="seconds"), **res}
    st["files"][fid] = rec
    sp.write_text(json.dumps(st))
    return rec


@router.get("/api/uploads")
def list_uploads():
    _, _, st = _state()
    files = sorted(st["files"].values(), key=lambda r: r["uploaded_at"], reverse=True)
    return {"files": [{k: v for k, v in r.items() if k not in ("errors", "warnings")} for r in files[:20]]}


@router.get("/api/uploads/{file_id}")
def upload_status(file_id: str):
    _, _, st = _state()
    return st["files"].get(file_id) or JSONResponse({"error": "NOT_FOUND"}, status_code=404)


@router.post("/api/uploads/reset")
def reset_uploads():
    d = get_upload_dir()
    if d.exists():
        shutil.rmtree(d)
    return {"status": "RESET", "message": "Uploaded data removed. Dashboard now uses sample_data."}
