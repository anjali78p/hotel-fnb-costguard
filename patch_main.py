"""Run once from repo root: python patch_main.py  (adds the /api/cost router to backend/main.py)"""
p = "backend/main.py"
s = open(p).read()
line = "from .cost_api import router as cost_router\napp.include_router(cost_router)\n"
if "cost_router" in s:
    print("Already patched.")
else:
    marker = "# Serve dashboard"
    s = s.replace(marker, line + "\n" + marker) if marker in s else s + "\n" + line
    open(p, "w").write(s); print("Patched backend/main.py")
