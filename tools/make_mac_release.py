"""Builds the Mac edition's release zip: only what runs on the Air, in a Cratebox-Mac/ folder.

    python3 tools/make_mac_release.py            -> releases/cratebox-1.1.1-macbook-air-cachyos.zip
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
version = re.search(r'const VERSION = "([^"]+)"', open(os.path.join(ROOT, "cratebox.html"), encoding="utf-8").read()).group(1)
base = version.replace("-mac", "")
out = os.path.join(ROOT, "releases", f"cratebox-{base}-macbook-air-cachyos.zip")
FILES = ["cratebox.html", "cratebox.py", "index.html", "icon.png", "README.md", "CHANGELOG.md",
         "vendor/lame.min.js", "vendor/LICENSE-lamejs.txt"]
FILES += sorted("fonts/" + f for f in os.listdir(os.path.join(ROOT, "fonts")))
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in FILES:
        src = os.path.join(ROOT, f)
        info = zipfile.ZipInfo.from_file(src, "Cratebox-Mac/" + f)
        info.date_time = (2026, 10, 16, 12, 0, 0)          # same bytes every build
        info.compress_type = zipfile.ZIP_DEFLATED
        mode = 0o755 if f == "cratebox.py" else 0o644
        info.external_attr = (0o100000 | mode) << 16
        with open(src, "rb") as fh:
            z.writestr(info, fh.read())
print(out, os.path.getsize(out), "bytes,", len(FILES), "files")
sys.exit(0)
