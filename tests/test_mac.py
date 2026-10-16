"""Mac edition: the launcher (cratebox.py) and its file bridge, end to end in headless Chromium.

Starts the real launcher with a temporary home folder, then: picks the music folder through the
desktop's folder dialog (a stand-in kdialog) and by typed path (no dialog program), checks the folder
comes back by itself after a restart with its analysis kept, opens a rekordbox USB export from
/run/media, loads a track off it, and checks the bridge refuses other sites, other hosts and paths
outside home and the mount points. Also: no requests leave the computer (fonts are bundled), the
Firefox-only layout (no output picker, both headphone modes kept) and no AudioContext.setSinkId use.

    python tests/test_mac.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402

PORT = 8656
BASE = f"http://localhost:{PORT}"
MUSIC_SRC = os.path.join(T.ROOT, "tests", "music")
USB_SRC = os.path.join(T.ROOT, "tests", "fixtures", "rekordbox_usb")
USER = "cbtest"
check = T.check


def http(path, headers=None, host=None):
    h = {"X-Cratebox": "1"}
    h.update(headers or {})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", headers=h)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def main():
    tmp = tempfile.mkdtemp(prefix="cratebox-mac-")
    home = os.path.join(tmp, "home", USER)
    music = os.path.join(home, "Music", "DJ")
    os.makedirs(os.path.join(music, "Bass"))
    for n in sorted(os.listdir(MUSIC_SRC)):
        dst = os.path.join(music, "Bass" if "Wobble" in n else "", n)
        shutil.copy(os.path.join(MUSIC_SRC, n), dst)
    open(os.path.join(music, "notes.txt"), "w").write("not audio")
    os.makedirs(os.path.join(music, ".hidden")); shutil.copy(os.path.join(MUSIC_SRC, sorted(os.listdir(MUSIC_SRC))[0]), os.path.join(music, ".hidden", "x.wav"))
    # a rekordbox USB stick "plugged in" at /run/media/cbtest/RBUSB, with two real tracks on it
    media = f"/run/media/{USER}"
    usb = os.path.join(media, "RBUSB")
    shutil.rmtree(usb, ignore_errors=True)
    shutil.copytree(USB_SRC, usb)
    lm = os.path.join(usb, "Contents", "Loopmasters", "UnknownAlbum")
    os.makedirs(lm, exist_ok=True)
    shutil.copy(os.path.join(MUSIC_SRC, "Test Artist - House Groove 126.wav"), os.path.join(lm, "Demo Track 1.mp3"))
    shutil.copy(os.path.join(MUSIC_SRC, "Bass Lab - Halftime Wobble 140.wav"), os.path.join(lm, "Demo Track 2.mp3"))
    # a stand-in kdialog that "picks" whatever path is in a file (cancel when the file is empty)
    bindir = os.path.join(tmp, "bin"); os.makedirs(bindir)
    answer = os.path.join(tmp, "dialog-answer")
    with open(os.path.join(bindir, "kdialog"), "w") as f:
        f.write(f'#!/bin/sh\necho "$@" >> {tmp}/dialog-args\na=$(cat {answer} 2>/dev/null)\n[ -n "$a" ] || exit 1\necho "$a"\n')
    os.chmod(os.path.join(bindir, "kdialog"), 0o755)
    env = dict(os.environ, HOME=home, USER=USER, CRATEBOX_PORT=str(PORT), PATH=bindir + ":/usr/bin:/bin")
    srv = subprocess.Popen([sys.executable, os.path.join(T.ROOT, "cratebox.py"), "--no-browser"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    errors, outside = [], []
    try:
        for _ in range(50):
            try:
                if http("/fs/hello")[0] == 200: break
            except Exception:
                pass
            time.sleep(0.1)
        # ---- the bridge on its own
        st, body, _ = http("/fs/hello")
        check("launcher answers the page", st == 200 and json.loads(body)["app"] == "cratebox", f"{st} {body[:80]}")
        check("bridge refuses requests without Cratebox's header (other sites)", http("/fs/hello", headers={"X-Cratebox": ""})[0] == 403)
        check("bridge refuses a cross-site request", http("/fs/hello", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
        check("server refuses other host names (DNS rebinding)", http("/fs/hello", host="evil.example:8656")[0] == 403 and http("/cratebox.html", host="evil.example")[0] == 403)
        check("bridge won't read outside home and the mount points", http("/fs/file?path=/etc/passwd")[0] == 404 and http("/fs/stat?path=" + urllib.request.quote(home + "/../../../../etc/passwd"))[0] == 404)
        os.symlink("/etc", os.path.join(home, "etc-link"))
        check("...not even through a symlink in home", http("/fs/list?path=" + urllib.request.quote(home + "/etc-link"))[0] == 404)
        wav = os.path.join(music, "Test Artist - House Groove 126.wav")
        st, body, hd = http("/fs/file?path=" + urllib.request.quote(wav), headers={"Range": "bytes=4-11"})
        raw = open(wav, "rb").read()
        check("byte ranges (for tags and rekordbox files)", st == 206 and body == raw[4:12] and hd.get("Content-Range") == f"bytes 4-11/{len(raw)}", f"{st} {hd.get('Content-Range')}")
        st, body, _ = http("/fs/walk?path=" + urllib.request.quote(music))
        files = json.loads(body)["files"]
        check("folder scan: audio files only, subfolders, hidden folders skipped", sorted(f[0] for f in files) == sorted(["Bass/Bass Lab - Halftime Wobble 140.wav", "Boom Bap Crew - Dusty 92.wav", "Jungle Unit - Rollers 174.wav", "Test Artist - House Groove 126.wav"]), str([f[0] for f in files]))
        st, body, _ = http("/fs/drives")
        drives = json.loads(body)["drives"]
        check("finds the plugged-in rekordbox USB", [d["name"] for d in drives] == ["RBUSB"], str(drives))

        with sync_playwright() as p:
            b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            ctx = b.new_context(viewport={"width": 1440, "height": 770})   # Firefox's window on the Air
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: m.type == "error" and "favicon" not in m.text and errors.append(m.text))
            page.on("request", lambda r: not r.url.startswith(BASE) and not r.url.startswith("blob:") and not r.url.startswith("data:") and outside.append(r.url))
            # Firefox has neither of these: make sure Cratebox doesn't need them
            page.add_init_script("delete AudioContext.prototype.setSinkId; delete AudioContext.prototype.sinkId; delete window.showDirectoryPicker;")

            def start():
                page.goto(BASE + "/cratebox.html")
                page.click("#startBtn")
                page.wait_for_function("window.cratebox && cratebox.A.ctx && cratebox.A.decks.length >= 2")

            start()
            fonts = page.evaluate("document.fonts.ready.then(() => { const got = new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, ''))); return ['Barlow', 'Barlow Condensed', 'IBM Plex Mono'].map(f => got.has(f)); })")
            check("fonts come from the app folder, not the internet", all(fonts), str(fonts))
            check("no output picker (Firefox can't choose one); FLX4 jack and Another device kept",
                  page.evaluate("!document.querySelector('#outSel') && ['auto','quad','device','split','off'].every(v => document.querySelector(`#hpSel option[value=${v}]`))"))
            check("no phone or touch leftovers", page.evaluate("!document.querySelector('#rotate, .ptabs, #fxOpen, #setOpen, #treeBtn, #load1Btn, #filesInput, #setSheet') && !document.documentElement.classList.contains('phone') && !document.documentElement.classList.contains('touch')"))

            # ---- typed path when there's no dialog program
            os.rename(os.path.join(bindir, "kdialog"), os.path.join(bindir, "kdialog.off"))
            page.once("dialog", lambda d: d.accept(os.path.join(home, "Music", "DJ", "Bass")))
            page.click("#addFolder")
            page.wait_for_function("cratebox.lib.tracks.length === 1", timeout=20000)
            check("no folder dialog installed: type the path instead", page.evaluate("cratebox.lib.tracks[0].rel") == "Bass/Bass Lab - Halftime Wobble 140.wav", page.evaluate("cratebox.lib.tracks[0].rel"))
            os.rename(os.path.join(bindir, "kdialog.off"), os.path.join(bindir, "kdialog"))

            # ---- folder dialog: cancel, then pick
            open(answer, "w").write("")
            page.click("#addFolder"); page.wait_for_timeout(500)
            check("cancelling the folder dialog changes nothing", page.evaluate("cratebox.lib.tracks.length") == 1)
            open(answer, "w").write(music)
            t0 = time.time()
            page.click("#addFolder")
            page.wait_for_function("cratebox.lib.tracks.length === 5 && cratebox.lib.tracks.every(t => t.bpm != null)", timeout=180000)
            args = open(os.path.join(tmp, "dialog-args")).read()
            check("KDE folder dialog opens in ~/Music", "--getexistingdirectory" in args and os.path.join(home, "Music") in args, args.strip().splitlines()[-1])
            got = page.evaluate("cratebox.lib.tracks.filter(t => t.rel.startsWith('DJ/')).map(t => [t.title, Math.round(t.bpm)]).sort()")
            check("tracks read through the bridge and analysed", got == sorted([["Dusty 92", 92], ["Halftime Wobble 140", 140], ["House Groove 126", 126], ["Rollers 174", 174]]), f"{got} in {time.time() - t0:.1f}s")
            page.evaluate("cratebox.lib.sel = cratebox.lib.view.findIndex(t => t.title === 'House Groove 126'); cratebox.loadSelected(0)")
            page.wait_for_function("cratebox.decks[0].loaded && !cratebox.decks[0].loading", timeout=30000)
            page.evaluate("cratebox.decks[0].togglePlay()"); page.wait_for_timeout(600)
            check("a bridge track loads and plays", page.evaluate("cratebox.decks[0].playing && cratebox.decks[0].now() > 0.2"), str(page.evaluate("cratebox.decks[0].now()")))
            page.evaluate("cratebox.decks[0].togglePlay()")

            # ---- rekordbox USB
            page.click("#tree .thead button.ticon.wide")
            page.wait_for_function("cratebox.PL.devices.length === 1", timeout=20000)
            dev = page.evaluate("({ name: cratebox.PL.devices[0].name, n: cratebox.PL.devices[0].trackCount })")
            check("+ USB opens the plugged-in rekordbox stick", dev == {"name": "RBUSB", "n": 6}, str(dev))
            page.locator("#tree .trow2", has=page.locator(".nm", has_text="RBUSB")).first.click()      # the stick's own view
            page.wait_for_function("cratebox.lib.view.some(t => t.title === 'Demo Track 2')", timeout=10000)
            page.evaluate("cratebox.lib.sel = cratebox.lib.view.findIndex(t => t.title === 'Demo Track 2'); cratebox.loadSelected(1)")
            page.wait_for_function("cratebox.decks[1].loaded && !cratebox.decks[1].loading", timeout=30000)
            usb_t = page.evaluate("({ title: cratebox.decks[1].track.title, rb: !!cratebox.decks[1].track.rbRead, bpm: cratebox.decks[1].bpm })")
            check("a USB track loads with rekordbox's own grid", usb_t["title"] == "Demo Track 2" and usb_t["rb"], str(usb_t))
            open(answer, "w").write("")
            page.click("#tree .thead button.ticon.wide"); page.wait_for_timeout(500)
            check("+ USB again with every stick open: the dialog, starting in /run/media", f"/run/media/{USER}" in open(os.path.join(tmp, "dialog-args")).read().strip().splitlines()[-1])

            # ---- restart: the folder and the stick come back by themselves, analysis kept
            # (one saved music folder, like the Chrome version: the last one picked, ~/Music/DJ)
            start()
            page.wait_for_function("cratebox.lib.tracks.filter(t => !t.device).length === 4 && cratebox.PL.devices.length === 1", timeout=20000)
            check("after a restart: folder and USB are back, no dialog", page.evaluate("cratebox.lib.tracks.filter(t => !t.device).every(t => t.bpm > 0)") and page.evaluate("cratebox.lib.queue.length") == 0)
            # unplug the stick: next start skips it quietly
            os.rename(usb, usb + ".out")
            start()
            page.wait_for_function("cratebox.lib.tracks.filter(t => !t.device).length === 4", timeout=20000)
            page.wait_for_timeout(500)
            check("unplugged stick: skipped, no error", page.evaluate("cratebox.PL.devices.length") == 0 and "doesn't look like" not in page.inner_text("#status"))
            os.rename(usb + ".out", usb)
            # the music folder on a drive that isn't mounted yet: Reconnect
            os.rename(music, music + ".out")
            start(); page.wait_for_timeout(800)
            check("missing music folder: Reconnect button", page.is_visible("#reconnect") and "DJ" in page.inner_text("#reconnect"), page.inner_text("#reconnect"))
            os.rename(music + ".out", music)
            page.click("#reconnect")
            page.wait_for_function("cratebox.lib.tracks.filter(t => !t.device).length === 4", timeout=20000)
            check("Reconnect brings it back", not page.is_visible("#reconnect"))

            # ---- layout on the Air: 1440 x 770 (Firefox window with KDE's panel)
            ov = page.evaluate("[document.documentElement.scrollWidth, innerWidth, document.querySelector('#list').getBoundingClientRect().height]")
            check("1440x770: no sideways scroll, library visible", ov[0] <= ov[1] and ov[2] > 60, str(ov))
            if len(sys.argv) > 1: page.screenshot(path=sys.argv[1])
            check("no requests leave the computer", not outside, str(outside[:3]))
            b.close()
    finally:
        srv.terminate()
        try: srv.wait(5)
        except Exception: srv.kill()
        shutil.rmtree(usb, ignore_errors=True); shutil.rmtree(usb + ".out", ignore_errors=True)
        try: os.rmdir(media)
        except OSError: pass
        shutil.rmtree(tmp, ignore_errors=True)
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    ok = sum(1 for _, o in T.checks if o)
    print(f"\n{ok}/{len(T.checks)} checks passed")
    sys.exit(0 if ok == len(T.checks) else 1)


if __name__ == "__main__":
    main()
