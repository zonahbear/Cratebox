"""iPhone inside an iOS MIDI browser app (MIDIWeb Browser and the like), emulated in headless Chromium.

Those apps are WebKit with Web MIDI added by injected script, which can arrive after the page has
started. This strips Web MIDI like Safari, then adds a stand-in DDJ-FLX4 half a second after load,
and checks: the controller is still found and mapped, the phone shows the controller settings,
tracks can be imported with the file picker, and the FLX4 plays a deck.

    python tests/test_ios_midi.py [screenshot-prefix]
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_ios as I  # noqa: E402
import test_android as AN  # noqa: E402

LATE_FLX4 = I.STRIP + """
window.__sent = [];
window.addEventListener('load', () => setTimeout(() => {
""" + AN.FAKE_FLX4.split("window.__sent = [];", 1)[1] + """
}, 500));
"""


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else None
    T.PORT = 8641
    srv = T.serve()
    check = T.check
    errors = []
    music = os.path.join(T.ROOT, "tests", "music")
    files = [os.path.join(music, n) for n in sorted(os.listdir(music)) if n.endswith(("126.wav", "140.wav"))]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 956, "height": 440}, screen={"width": 440, "height": 956},
                            is_mobile=True, has_touch=True, user_agent=I.IPHONE_UA, device_scale_factor=3)
        ctx.add_init_script(LATE_FLX4)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        check("no Web MIDI when the page starts (the app adds it later)", page.evaluate("!navigator.requestMIDIAccess"))
        page.wait_for_timeout(100)
        page.tap("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx && cratebox.MIDI.name", timeout=10000)
        st = page.evaluate("({ phone: document.documentElement.classList.contains('phone'), nomidi: document.documentElement.classList.contains('nomidi'), pill: document.querySelector('#midiPill').textContent, on: document.querySelector('#midiPill').classList.contains('on'), prof: cratebox.MIDI.profile.id })")
        check("iPhone + late Web MIDI: phone layout, FLX4 found and mapped", st["phone"] and not st["nomidi"] and st["on"] and "DDJ-FLX4" in st["pill"] and st["prof"] == "ddj-flx4", str(st))

        page.tap(".ptabs button[data-tab=lib]")
        with page.expect_file_chooser() as fc:
            page.tap("#addFolder", force=True)
        fc.value.set_files(files)
        page.wait_for_function("cratebox.lib.tracks.length === 2 && cratebox.lib.tracks.every(t => t.stored)", timeout=30000)
        check("file picker opens and imports tracks", True)
        check("file pickers are invisible but not display:none", page.evaluate("[...document.querySelectorAll('input[type=file]')].every(e => getComputedStyle(e).display !== 'none' && !e.hidden)"))
        hit = page.evaluate("(() => { const b = document.querySelector('#addFolder').getBoundingClientRect(); const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return e && e.id; })()")
        check("tapping Add music lands on the real file input, not a script click", hit == "filesInput", str(hit))

        page.tap("#list .trow >> nth=0 >> .ld[data-d='0']")
        page.wait_for_function("cratebox.decks[0].loaded", timeout=60000)
        page.tap(".ptabs button[data-tab=mix]")
        res = page.evaluate("""async () => {
          const C = cratebox, tbl = [...C.MIDI.table.values()], f = (a, d) => tbl.find(e => e[2] === a && e[3] === d);
          const play = f('play', 0);
          __flx4([play[0], play[1], 127]); __flx4([play[0] & 0xef, play[1], 0]);
          await new Promise(r => setTimeout(r, 400));
          const out = { playing: C.decks[0].playing, t: C.decks[0].now(), hint: document.querySelector('.deck[data-i="1"] .dtitle span').textContent };
          __flx4([play[0], play[1], 127]); __flx4([play[0] & 0xef, play[1], 0]);
          return out; }""")
        check("FLX4 PLAY plays the deck; empty deck hint mentions the controller", res["playing"] and res["t"] > 0.1 and "LOAD" in res["hint"], str(res))
        page.tap("#setOpen")
        check("controller settings shown in the phone settings sheet", page.is_visible("#ctlProfile"))
        if prefix:
            page.screenshot(path=prefix + "-iosmidi.png")
        ctx.close()

        # plain Safari: still touch mode, and the start screen points to a MIDI browser app
        ctx = b.new_context(viewport={"width": 956, "height": 440}, screen={"width": 440, "height": 956},
                            is_mobile=True, has_touch=True, user_agent=I.IPHONE_UA, device_scale_factor=3)
        ctx.add_init_script(I.STRIP)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        check("Safari start screen names MIDIWeb Browser", "MIDIWeb Browser" in page.inner_text("#startMidi"))
        page.tap("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx", timeout=10000)
        page.wait_for_timeout(1800)
        check("Safari: touch mode, no controller settings", page.evaluate("document.documentElement.classList.contains('nomidi')") and "Touch" in page.inner_text("#midiPill"))
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
