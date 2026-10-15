"""Double-click (or run `py start_cratebox.py`) to open Cratebox in Chrome.

Cratebox is a web page, but it needs to be served from http://localhost rather than opened as a
file: Chrome only allows MIDI controllers, folder access and the audio engine on secure origins.
The port stays the same every time so your library, cue points and settings are remembered.
"""
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import webbrowser

PORT = 8611
HERE = os.path.dirname(os.path.abspath(__file__))
URL = f"http://localhost:{PORT}/cratebox.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass


def open_chrome(url):
    candidates = []
    if sys.platform.startswith("win"):
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
            candidates += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                           os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    elif sys.platform == "darwin":
        candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:
        candidates += [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    for exe in candidates:
        if exe and os.path.exists(exe):
            subprocess.Popen([exe, "--new-window", url])
            return
    webbrowser.open(url)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Cratebox already seems to be running. Opening {URL}")
        open_chrome(URL)
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Cratebox is running at {URL}")
    print("Keep this window open while you play. Close it (or press Ctrl+C) to stop.")
    open_chrome(URL)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
