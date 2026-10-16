#!/usr/bin/env python3
"""Cratebox launcher for the Mac edition (2017 MacBook Air, CachyOS, Firefox).

    python3 cratebox.py              start Cratebox and open it in Firefox
    python3 cratebox.py --install    add Cratebox to the app menu (then start it from there)
    python3 cratebox.py --uninstall  remove it from the app menu
    python3 cratebox.py --no-browser just run the server (for testing)

Cratebox is a web page, but it has to be served from http://localhost rather than opened as a file:
Firefox only allows MIDI controllers and the audio engine on secure origins. The port never changes,
so your library, cue points, settings and Firefox's MIDI permission are kept.

It also reads your music folder and rekordbox USB sticks for the page (the "file bridge"), because
Firefox can't open or remember a folder itself. The bridge is read-only, answers only this computer
(127.0.0.1), only pages served from here (a header other sites can't send), only paths under your
home folder and the usual mount points (/run/media, /media, /mnt), and it never writes anything.
"""
import http.server
import json
import mimetypes
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

PORT = int(os.environ.get("CRATEBOX_PORT", "8611"))
HERE = os.path.dirname(os.path.abspath(__file__))
URL = f"http://localhost:{PORT}/cratebox.html"
HOME = os.path.expanduser("~")
USER = os.environ.get("USER") or os.path.basename(HOME)
ROOTS = [os.path.realpath(p) for p in (HOME, "/run/media", "/media", "/mnt") if os.path.isdir(p)]
MOUNTS = [p for p in (f"/run/media/{USER}", f"/media/{USER}", "/media", "/mnt") if os.path.isdir(p)]
HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}", f"[::1]:{PORT}"}
AUDIO = re.compile(r"\.(mp3|wav|wave|flac|m4a|aac|ogg|oga|opus|webm|aif|aiff)$", re.I)
CHUNK = 1 << 20


def allowed(path):
    """The real path (symlinks resolved) if it's under one of ROOTS, else None."""
    if not path or "\0" in path or not os.path.isabs(path):
        return None
    real = os.path.realpath(path)
    for r in ROOTS:
        if real == r or real.startswith(r.rstrip("/") + "/"):
            return real
    return None


def mtime_ms(st):
    return st.st_mtime_ns // 1_000_000          # same as a browser File's lastModified


def pick_folder(kind):
    """The desktop's own folder dialog (KDE: kdialog, GNOME and others: zenity)."""
    start = MOUNTS[0] if kind == "usb" and MOUNTS else (os.path.join(HOME, "Music") if os.path.isdir(os.path.join(HOME, "Music")) else HOME)
    title = "Cratebox: pick the USB stick or SD card" if kind == "usb" else "Cratebox: pick your music folder"
    for exe, args in (("kdialog", ["--title", title, "--getexistingdirectory", start]),
                      ("zenity", ["--file-selection", "--directory", "--title=" + title, "--filename=" + start + "/"]),
                      ("qarma", ["--file-selection", "--directory", "--title=" + title, "--filename=" + start + "/"])):
        path = shutil.which(exe)
        if not path:
            continue
        r = subprocess.run([path, *args], capture_output=True, text=True)
        chosen = r.stdout.strip()
        if r.returncode != 0 or not chosen:
            return {"cancelled": True}
        real = allowed(chosen)
        if not real or not os.path.isdir(real):
            return {"error": f"Cratebox can only open folders in your home folder or on a plugged-in drive ({chosen})"}
        return {"path": real, "name": os.path.basename(real.rstrip("/")) or real}
    return {"suggest": start}                  # no dialog program: the page asks for the path instead


def rekordbox_drives():
    out = []
    for base in MOUNTS:
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for n in names:
            p = os.path.join(base, n)
            if os.path.isfile(os.path.join(p, "PIONEER", "rekordbox", "export.pdb")) and allowed(p):
                out.append({"path": os.path.realpath(p), "name": n})
    return out


def walk_audio(top):
    files = []
    for d, dirs, names in os.walk(top):
        dirs[:] = sorted(x for x in dirs if not x.startswith("."))
        rel = os.path.relpath(d, top)
        for n in sorted(names):
            if n.startswith(".") or not AUDIO.search(n):
                continue
            try:
                st = os.stat(os.path.join(d, n))
            except OSError:
                continue
            files.append([n if rel == "." else f"{rel}/{n}", st.st_size, mtime_ms(st)])
    return files


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass

    def end_headers(self):
        # the app files are read fresh each time (no stale copy after an update)
        if not self.path.startswith("/fs/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.headers.get("Host") not in HOSTS:   # another name pointing here (DNS rebinding)
            return self.send_error(403)
        if self.path.startswith("/fs/"):
            return self.bridge()
        return super().do_GET()

    def do_HEAD(self):
        if self.headers.get("Host") not in HOSTS or self.path.startswith("/fs/"):
            return self.send_error(403)
        return super().do_HEAD()

    def json(self, obj, code=200):
        body = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def bridge(self):
        # only Cratebox's own page: other sites can't send this header without the browser asking
        # first, and nothing here answers that question
        if self.headers.get("X-Cratebox") != "1" or self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return self.json({"error": "forbidden"}, 403)
        u = urllib.parse.urlsplit(self.path)
        op = u.path[len("/fs/"):]
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if op == "hello":
                return self.json({"app": "cratebox", "dialog": any(shutil.which(x) for x in ("kdialog", "zenity", "qarma"))})
            if op == "pick":
                return self.json(pick_folder(q.get("kind", "music")))
            if op == "drives":
                return self.json({"drives": rekordbox_drives()})
            real = allowed(q.get("path", ""))
            if not real:
                return self.json({"error": "not found"}, 404)
            if op == "stat":
                # "is it there?" is a normal question (a stick that isn't plugged in): no error for no
                if not os.path.exists(real):
                    return self.json({"path": real, "kind": None})
                st = os.stat(real)
                return self.json({"path": real, "kind": "directory" if os.path.isdir(real) else "file", "size": st.st_size, "mtime": mtime_ms(st)})
            if not os.path.exists(real):
                return self.json({"error": "not found"}, 404)
            if op == "list":
                entries = []
                with os.scandir(real) as it:
                    for e in it:
                        if e.name.startswith("."):
                            continue
                        try:
                            st = e.stat()
                        except OSError:
                            continue
                        entries.append({"name": e.name, "kind": "directory" if e.is_dir() else "file", "size": st.st_size, "mtime": mtime_ms(st)})
                return self.json({"entries": sorted(entries, key=lambda x: x["name"].lower())})
            if op == "walk":
                return self.json({"files": walk_audio(real)})
            if op == "file":
                return self.send_file(real)
        except PermissionError:
            return self.json({"error": "permission denied"}, 403)
        except OSError as e:
            return self.json({"error": e.strerror or str(e)}, 500)
        return self.json({"error": "unknown request"}, 404)

    def send_file(self, real):
        if not os.path.isfile(real):
            return self.json({"error": "not a file"}, 404)
        size = os.path.getsize(real)
        start, end = 0, size - 1
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "") or "")
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:                                   # the last N bytes
                start = max(0, size - int(m.group(2)))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        n = end - start + 1
        self.send_header("Content-Type", mimetypes.guess_type(real)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(max(0, n)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(real, "rb") as f:
            f.seek(start)
            while n > 0:
                b = f.read(min(CHUNK, n))
                if not b:
                    break
                self.wfile.write(b)
                n -= len(b)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def open_firefox(url):
    for name in ("firefox", "firefox-developer-edition", "firefox-nightly", "librewolf"):
        exe = shutil.which(name)
        if exe:
            subprocess.Popen([exe, "--new-window", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return
    webbrowser.open(url)


def already_running():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/fs/hello", headers={"X-Cratebox": "1", "Host": f"127.0.0.1:{PORT}"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.load(r).get("app") == "cratebox"
    except Exception:
        return False


DESKTOP = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local", "share"), "applications", "cratebox.desktop")


def install():
    os.makedirs(os.path.dirname(DESKTOP), exist_ok=True)
    py = shutil.which("python3") or sys.executable
    with open(DESKTOP, "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=Cratebox\nGenericName=DJ software\n"
                "Comment=Two or four decks, a mixer and your music folder, for the DDJ-FLX4\n"
                f'Exec="{py}" "{os.path.join(HERE, "cratebox.py")}"\nIcon={os.path.join(HERE, "icon.png")}\n'
                "Terminal=false\nCategories=AudioVideo;Audio;Music;\nStartupNotify=false\n")
    os.chmod(DESKTOP, 0o755)
    print(f"Added Cratebox to the app menu ({DESKTOP}). Start it from there (Multimedia), or search for Cratebox.")


def main():
    args = set(sys.argv[1:])
    if "--install" in args:
        return install()
    if "--uninstall" in args:
        if os.path.exists(DESKTOP):
            os.remove(DESKTOP)
        return print("Removed Cratebox from the app menu.")
    browser = "--no-browser" not in args
    try:
        srv = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        if already_running():
            print(f"Cratebox is already running. Opening {URL}")
            if browser:
                open_firefox(URL)
            return
        sys.exit(f"Port {PORT} is taken by another program, so Cratebox can't start.")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Cratebox is running at {URL}")
    print("Close this window (or press Ctrl+C) to stop it.")
    if browser:
        open_firefox(URL)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
