"""Set recording: record the master output as WAV and as MP3, check the files and the tracklist.

    python tests/test_record.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import wave

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402


def probe(path):
    if not shutil.which("ffprobe"):
        return None
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate",
                          "-show_entries", "format=duration", "-of", "default=nw=1", path], capture_output=True, text=True).stdout
    return dict(line.split("=", 1) for line in out.split() if "=" in line)


def main():
    T.PORT = 8653
    srv = T.serve()
    check = T.check
    errors = []
    tmp = tempfile.mkdtemp()
    music = os.path.join(T.ROOT, "tests", "music")
    names = sorted(n for n in os.listdir(music) if n.endswith(("126.wav", "140.wav")))
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        page.evaluate("""async (names) => { const files = [];
            for (const n of names) files.push({ file: new File([await (await fetch('tests/music/' + encodeURIComponent(n))).blob()], n, { lastModified: 1 }), rel: 'music/' + n });
            await cratebox.addFiles(files); }""", names)
        page.wait_for_function("cratebox.lib.tracks.length === 2")
        page.evaluate("cratebox.lib.sel = 0; cratebox.loadSelected(0); cratebox.lib.sel = 1; cratebox.loadSelected(1)")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[1].loaded", timeout=60000)

        for fmt in ("wav", "mp3"):
            page.evaluate("(f) => { const s = document.querySelector('#recFmtSel'); s.value = f; s.dispatchEvent(new Event('change')); }", fmt)
            page.evaluate("cratebox.M.xfader = 0; cratebox.decks.forEach((d, i) => cratebox.M.fader[i] = 1)")
            page.click("#recBtn")
            page.wait_for_function("cratebox.REC.on")
            page.evaluate("cratebox.decks[0].togglePlay()")
            page.wait_for_timeout(1500)
            label = page.inner_text("#recBtn")
            # deck 2 plays but is crossfaded out: it must not reach the tracklist
            page.evaluate("cratebox.decks[1].togglePlay()")
            page.wait_for_timeout(1700)
            with page.expect_download(timeout=30000) as dl:
                page.click("#recBtn")
            path = os.path.join(tmp, dl.value.suggested_filename)
            dl.value.save_as(path)
            page.evaluate("cratebox.decks.forEach(d => d.playing && d.togglePlay())")
            info = page.evaluate("({ list: cratebox.REC.list.map(x => x.title), frames: cratebox.REC.frames, sr: cratebox.REC.sr, panel: !document.querySelector('#recPanel').hidden, txt: document.querySelector('#recList').textContent })")
            dur_expected = info["frames"] / info["sr"]
            check(f"{fmt}: REC button shows a running timer", label.startswith("■ 0:0"), label)
            check(f"{fmt}: file named after the date, right extension", dl.value.suggested_filename.startswith("Cratebox set ") and dl.value.suggested_filename.endswith("." + fmt), dl.value.suggested_filename)
            if fmt == "wav":
                with wave.open(path) as w:
                    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
                    raw = w.readframes(n)
                import array
                a = array.array("h", raw)
                peak = max(abs(x) for x in a[::7]) if a else 0
                check("wav: 16-bit stereo, length matches the recording", ch == 2 and sw == 2 and sr == info["sr"] and abs(n / sr - dur_expected) < 0.01 and 2.8 < n / sr < 4.5, f"{ch}ch {sw * 8}bit {sr}Hz {n / sr:.2f}s")
                check("wav: has the music in it (not silence)", peak > 3000, f"peak {peak}")
            else:
                pr = probe(path)
                if pr is None:
                    check("mp3: file starts with an MPEG frame", open(path, "rb").read(2) == b"\xff\xfb")
                else:
                    check("mp3: 320 kbps stereo, length matches", pr.get("codec_name") == "mp3" and pr.get("channels") == "2" and pr.get("bit_rate") == "320000" and abs(float(pr["duration"]) - dur_expected) < 0.1, str(pr))
            check(f"{fmt}: tracklist has the audible track only", info["list"] == ["Halftime Wobble 140"] and info["panel"] and "Halftime Wobble 140" in info["txt"], str(info["list"]))
            page.click("#recClose")

        # tracklist download
        with page.expect_download() as dl:
            page.evaluate("document.querySelector('#recPanel').hidden = false")
            page.click("#recSaveList")
        tl = open(dl.value.path(), encoding="utf-8").read()
        check("tracklist .txt: title line and a timestamped track", tl.startswith("Cratebox set ") and "0:00  " in tl and "Halftime Wobble 140 (140 BPM)" in tl, tl[:200])
        ctx.close()
        b.close()
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
