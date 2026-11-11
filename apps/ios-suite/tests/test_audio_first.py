"""Audio first: the music never stops.

Checks that playback and sync don't depend on the screen: beat lock keeps correcting with screen drawing
stopped (as in a hidden tab); decks 3/4 can't be hidden while they play; their audio chains only exist once
4-deck mode is on; a stopped deck still reports its position; leaving the page while music plays asks first;
the recorder hands its buffers back for reuse; the default audio buffer is the safer "balanced" one.

    python tests/test_audio_first.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_fourdeck import load_all  # noqa: E402


def main():
    T.PORT = 8659
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
        check("2-deck mode: only two audio chains running", page.evaluate("cratebox.A.decks.length") == 2)
        check("default audio buffer is Medium (balanced)", page.evaluate("document.querySelector('#abufSel').value") == "balanced")
        load_all(page, 2)

        # beat lock with the screen frozen: stop requestAnimationFrame entirely, then knock deck 2 off the beat
        page.evaluate("cratebox.decks[0].togglePlay(); cratebox.decks[1].setSync(true); cratebox.decks[1].togglePlay()")
        page.wait_for_timeout(1500)
        page.evaluate("window.requestAnimationFrame = () => 0")      # drawing stops, like a hidden tab
        page.wait_for_timeout(300)
        page.evaluate("cratebox.decks[1].seek(cratebox.decks[1].now() + 0.03)")   # 30 ms off
        page.wait_for_timeout(200)
        off = page.evaluate("Math.abs(cratebox.decks[1].phaseErr)")
        page.wait_for_timeout(8000)        # the lock corrects gently (at most 0.6% speed, ~6 ms per second)
        st = page.evaluate("({ pe: cratebox.decks[1].phaseErr, playing: cratebox.decks.slice(0, 2).every(d => d.playing) })")
        check("screen drawing stopped: beat lock still pulls a 30 ms slip back in", off > 0.015 and st["pe"] is not None and abs(st["pe"]) < 0.006 and st["playing"], f"{off * 1000:.0f} ms -> {st['pe'] * 1000 if st['pe'] is not None else None} ms")

        # leaving the page while music plays asks first
        asks = page.evaluate("(() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; })()")
        check("leaving or reloading while music plays asks first", asks)
        page.evaluate("cratebox.decks.slice(0, 2).forEach(d => d.togglePlay())")
        quiet = page.evaluate("(() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; })()")
        check("...and doesn't when nothing plays", not quiet)

        # a stopped deck keeps reporting where it is (the audio thread's idle shortcut)
        page.evaluate("cratebox.decks[0].seek(20)")
        page.wait_for_timeout(400)
        check("stopped deck: position still reported after a seek", abs(page.evaluate("cratebox.decks[0].now()") - 20) < 0.05)
        ctx.close()

        # 4 decks: chains appear when turned on; decks 3/4 can't be hidden while playing
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        page.click("#fourBtn")
        check("4 DECKS builds the audio chains for decks 3 and 4", page.evaluate("cratebox.A.decks.length") == 4)
        load_all(page, 4)
        page.evaluate("cratebox.decks[2].togglePlay()")
        page.wait_for_timeout(300)
        page.click("#fourBtn")
        st = page.evaluate("({ four: document.documentElement.classList.contains('four'), playing: cratebox.decks[2].playing, gain: cratebox.A.decks[2].xf.gain.value, status: document.querySelector('#status').textContent })")
        check("2 DECKS while deck 3 plays: refused, deck 3 keeps playing and stays audible", st["four"] and st["playing"] and st["gain"] > 0.5 and "playing" in st["status"], str(st))
        page.evaluate("cratebox.decks[2].togglePlay()")
        page.click("#fourBtn")
        check("...and allowed once it's stopped", not page.evaluate("document.documentElement.classList.contains('four')"))
        page.click("#fourBtn")

        # recorder: buffers come back to the audio thread (no garbage made there while recording)
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.evaluate("cratebox.recStart()")
        page.wait_for_timeout(2500)
        pool = page.evaluate("""new Promise(res => {
          const port = cratebox.A.recTap.port, f = (e) => { if (e.data.pool != null) { port.removeEventListener('message', f); res(e.data.pool); } };
          port.addEventListener('message', f); port.postMessage('pool'); })""")
        frames = page.evaluate("cratebox.REC.frames")
        page.evaluate("cratebox.recStop()")
        page.wait_for_timeout(800)
        check("recorder: after 2.5 s (about 27 buffers) the audio thread still has its spare buffers back", frames > 44100 and pool >= 6, f"{frames} frames, {pool} spare")
        page.evaluate("cratebox.decks[0].togglePlay()")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
