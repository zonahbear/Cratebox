"""Jog sensitivity (Settings): scales jog movement from the controller and the on-screen jog; remembered.

    python tests/test_jog.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_fourdeck import load_all  # noqa: E402


def main():
    T.PORT = 8669
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
        load_all(page, 1)
        move = """async (k) => { const d = cratebox.decks[0]; d.seek(10); await new Promise(r => setTimeout(r, 150));
            const t0 = d.now(); d.jogTicks(360, k); await new Promise(r => setTimeout(r, 150)); return d.now() - t0; }"""
        full = page.evaluate(move, "bend")            # stopped deck: the jog side moves through the track
        check("100%: half a turn (360 ticks) moves 0.9 s, like a 33 RPM record", abs(full - 0.9) < 0.02, f"{full:.3f}")
        page.evaluate("const s = document.querySelector('#jogSensSel'); s.value = '0.5'; s.dispatchEvent(new Event('change'))")
        half = page.evaluate(move, "bend")
        check("50%: the same turn moves half as far", abs(half - 0.45) < 0.02, f"{half:.3f}")
        raw = page.evaluate("""async () => { const d = cratebox.decks[0]; d.seek(10); await new Promise(r => setTimeout(r, 150));
            const t0 = d.now(); d.jogTicks(360, 'bend', true); await new Promise(r => setTimeout(r, 150)); return d.now() - t0; }""")
        check("waveform drag stays 1:1 with the hand (not scaled)", abs(raw - 0.9) < 0.02, f"{raw:.3f}")
        page.reload()
        page.wait_for_function("window.cratebox")
        check("setting remembered after a reload", page.evaluate("cratebox.jogSens") == 0.5 and page.evaluate("document.querySelector('#jogSensSel').value") == "0.5")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
