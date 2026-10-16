"""Phrases (Intro / Build / Drop ...): shown on the waveforms, the overview and the deck readout, and the
Settings → Phrases switch that hides them. Also Settings → Load lock.

Checks: a track that arrives with a grid but no phrases (a rekordbox library track analysed without
rekordbox's phrase analysis) gets Cratebox's own phrases on that grid; a paused deck's waveform redraws when
its phrases change (after a grid edit re-phrases it); Hide takes phrases off everywhere and is remembered. Load lock (on by default) refuses a
track on a playing deck; unlocked, loading stops the deck and loads; the choice is remembered.

    python tests/test_phrases.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_fourdeck import load_all  # noqa: E402

# the lane's phrase label row: count pixels in the phrase colours along the top strip of a canvas
STRIP = """((sel, rows) => { const c = document.querySelector(sel), g = c.getContext('2d');
  const y = rows === 'top' ? 1 : c.height - 2, d = g.getImageData(0, y, c.width, 1).data;
  const cols = Object.values(cratebox.PHRASE_COLORS).map(h => [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16)));
  let n = 0; for (let x = 0; x < c.width; x++) { const p = [d[x*4], d[x*4+1], d[x*4+2]];
    if (cols.some(q => q.every((v, k) => Math.abs(v - p[k]) < 6))) n++; } return n; })"""


def main():
    T.PORT = 8667
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        load_all(page, 2)
        page.wait_for_timeout(400)
        check("phrases on: lane 1 has its phrase strip", page.evaluate(STRIP + "('#lane0', 'top')") > 20)
        check("...the overview its phrase strip", page.evaluate(STRIP + "('.deck[data-i=\"0\"] .overview', 'bottom')") > 20)
        check("...and the deck its phrase readout", page.inner_text('.deck[data-i="0"] .phrasetag') != "")

        # a rekordbox library track: grid known, analysis "current", but no phrases came with it
        page.evaluate("""(() => { const t = cratebox.lib.tracks[2]; const d0 = cratebox.decks[0];
            Object.assign(t, { bpm: 174, firstBeat: 0.05, key: 3, ver: cratebox.ANALYSIS_VER, phrases: [], gridManual: true, gridFrom: 'rekordbox' });
            cratebox.lib.sel = 2; cratebox.loadSelected(0); })()""")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].track === cratebox.lib.tracks[2]", timeout=60000)
        page.wait_for_function("cratebox.decks[0].ana.phrases && cratebox.decks[0].ana.phrases.length > 0", timeout=20000)
        st = page.evaluate("({ ph: cratebox.decks[0].ana.phrases.length, saved: cratebox.lib.tracks[2].phrases.length, bpm: cratebox.decks[0].ana.bpm })")
        check("rekordbox track with no phrases gets Cratebox's own, on rekordbox's grid", st["ph"] > 0 and st["saved"] > 0 and st["bpm"] == 174, str(st))
        page.wait_for_timeout(300)
        check("...and they're drawn on its (paused) waveform", page.evaluate(STRIP + "('#lane0', 'top')") > 20)

        # a paused deck redraws when its phrases change (a grid edit re-phrases in the background)
        page.evaluate("(() => { const d = cratebox.decks[1]; d.ana.phrases = [{ start: d.ana.firstBeat, bars: 64, label: 'Drop' }]; })()")
        page.wait_for_timeout(300)
        red = page.evaluate("""(() => { const c = document.querySelector('#lane1'), d = c.getContext('2d').getImageData(c.width / 2 + 40, 1, 1, 1).data; return [d[0], d[1], d[2]]; })()""")
        check("paused deck: new phrases show up without pressing play", abs(red[0] - 0xff) < 8 and abs(red[1] - 0x4d) < 8, str(red))

        # Settings → Phrases: Hide
        page.click("#setBtn")
        page.select_option("#phraseSel", "0")
        page.wait_for_timeout(300)
        off = page.evaluate(f"[{STRIP}('#lane0', 'top'), {STRIP}('#lane1', 'top'), {STRIP}('.deck[data-i=\"0\"] .overview', 'bottom'), document.querySelector('.deck[data-i=\"0\"] .phrasetag').textContent]")
        check("Hide: off the waveforms, the overview and the deck readout", off == [0, 0, 0, ""], str(off))
        check("Hide is saved", page.evaluate("localStorage.getItem('cb.phrases')") == "0")
        page.reload()
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        check("...and still hidden after a reload", page.evaluate("cratebox.showPhrases") is False and page.input_value("#phraseSel") == "0")
        load_all(page, 1)
        page.wait_for_timeout(300)
        check("...on a newly loaded track too", page.evaluate(STRIP + "('#lane0', 'top')") == 0)
        page.click("#setBtn")
        page.select_option("#phraseSel", "1")
        page.wait_for_timeout(300)
        check("Show brings them back", page.evaluate(STRIP + "('#lane0', 'top')") > 20 and page.inner_text('.deck[data-i="0"] .phrasetag') != "")

        # Settings → Load lock
        page.keyboard.press("Escape")
        check("load lock is on by default", page.evaluate("cratebox.loadLock") is True and page.input_value("#lockSel") == "1")
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.wait_for_timeout(200)
        before = page.evaluate("cratebox.decks[0].track.id")
        page.evaluate("cratebox.lib.sel = 1; cratebox.loadSelected(0)")
        page.wait_for_timeout(500)
        st = page.evaluate("({ id: cratebox.decks[0].track.id, playing: cratebox.decks[0].playing, msg: document.querySelector('#status') ? document.querySelector('#status').textContent : '' })")
        check("locked: a playing deck keeps its track and keeps playing", st["id"] == before and st["playing"], str(st))
        page.select_option("#lockSel", "0")
        page.evaluate("cratebox.lib.sel = 1; cratebox.loadSelected(0)")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].track.id !== %r" % before, timeout=60000)
        check("unlocked: loading onto a playing deck stops it and loads the new track", page.evaluate("!cratebox.decks[0].playing"))
        check("unlocked is saved", page.evaluate("localStorage.getItem('cb.loadlock')") == "0")
        page.reload()
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        check("...and still unlocked after a reload", page.evaluate("cratebox.loadLock") is False and page.input_value("#lockSel") == "0")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
