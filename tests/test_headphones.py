"""Headphone cue: what actually comes out of the headphone mix (measured on the signal, not the settings).

- nothing in the headphones until a channel's CUE is on (the mix knob starts on CUE)
- channel CUE: that channel, and only it
- MASTER CUE: the master in the headphones, whatever the mix knob says
- the CUE/MASTER knob: cue only up to 12 o'clock (no master), master fades in past it, master only at full right

    python tests/test_headphones.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_fourdeck import load_all  # noqa: E402

LEVEL = """new Promise(res => { const A = cratebox.A;
  if (!A.hpProbe) { A.hpProbe = A.ctx.createAnalyser(); A.hpProbe.fftSize = 2048; A.hpSum.connect(A.hpProbe); }
  setTimeout(() => { const b = new Float32Array(2048); let peak = 0;
    for (let k = 0; k < 6; k++) { A.hpProbe.getFloatTimeDomainData(b); for (const v of b) peak = Math.max(peak, Math.abs(v)); }
    res(peak); }, 250); })"""


def main():
    T.PORT = 8671
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
        page.evaluate("cratebox.decks[0].togglePlay()")         # deck 1 plays to the master; no CUE pressed
        page.wait_for_timeout(300)
        lv = lambda: page.evaluate(LEVEL)
        quiet = lv()
        check("no CUE on: headphones silent (mix knob starts on CUE)", quiet < 0.001 and page.evaluate("cratebox.M.headMix") == 0, f"peak {quiet:.4f}")
        page.click('#mixer .strip[data-i="0"] .cuebtn')
        cued = lv()
        check("deck 1 CUE on: deck 1 in the headphones", cued > 0.02, f"peak {cued:.3f}")
        page.click('#mixer .strip[data-i="0"] .cuebtn')
        page.click('#mixer .strip[data-i="1"] .cuebtn')
        other = lv()
        check("deck 2 CUE on (deck 2 stopped): deck 1 not in the headphones", other < 0.001, f"peak {other:.4f}")
        page.click('#mixer .strip[data-i="1"] .cuebtn')
        page.click("#mixer .mcuebtn")
        mc = lv()
        lit = page.evaluate("document.querySelector('#mixer .mcuebtn').classList.contains('lit')")
        check("MST CUE on: the master in the headphones, button lit", mc > 0.02 and lit, f"peak {mc:.3f}")
        page.click("#mixer .mcuebtn")
        check("MST CUE off again: silent", lv() < 0.001)
        page.evaluate("cratebox.M.headMix = 1; document.querySelector('#mixer .mcuebtn').click(); document.querySelector('#mixer .mcuebtn').click()")
        full = lv()
        check("mix knob full right: the master", full > 0.02, f"peak {full:.3f}")
        # 12 o'clock on the FLX4's knob (64/127) with MASTER CUE off: cue only, no master
        page.evaluate("cratebox.midiIn([0xB6, 0x0C, 64]); cratebox.midiIn([0xB6, 0x2C, 0])")
        noon = lv()
        check("FLX4 mix knob at 12 o'clock, MASTER CUE off: no master", noon < 0.001, f"peak {noon:.4f}")
        page.click('#mixer .strip[data-i="0"] .cuebtn')
        noon_cue = lv()
        page.click('#mixer .strip[data-i="0"] .cuebtn')
        check("...but a cued channel is heard at full level there", noon_cue > 0.02, f"peak {noon_cue:.3f}")
        page.evaluate("cratebox.midiIn([0xB6, 0x0C, 96]); cratebox.midiIn([0xB6, 0x2C, 0])")
        three = lv()
        check("past 12 o'clock (about 3 o'clock): the master fades in", three > 0.01, f"peak {three:.3f}")
        # the knob through MIDI (FLX4 HEADPHONES MIX) and back to CUE side
        page.evaluate("cratebox.midiIn([0xB6, 0x0C, 0]); cratebox.midiIn([0xB6, 0x2C, 0])")
        back = lv()
        check("FLX4 mix knob turned to CUE: silent again", back < 0.001 and page.evaluate("cratebox.M.headMix") == 0, f"peak {back:.4f}")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
