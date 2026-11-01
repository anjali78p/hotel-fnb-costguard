"""Run once from repo root: python patch_day6.py  (adds the upload router to backend/main.py)"""
p = "backend/main.py"
s = open(p).read()
line = "from .upload_api import router as upload_router\napp.include_router(upload_router)\n"
if "upload_router" in s:
    print("Already patched.")
else:
    marker = "# Serve dashboard"
    s = s.replace(marker, line + "\n" + marker) if marker in s else s + "\n" + line
    open(p, "w").write(s); print("Patched backend/main.py")
