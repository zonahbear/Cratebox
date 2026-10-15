"""Android phone with a USB MIDI controller, emulated in headless Chromium.

Chrome for Android has Web MIDI but no folder access. This fakes a DDJ-FLX4 on Web MIDI (headless
Chromium has no MIDI devices) and checks: phone layout, the controller is found and mapped,
tracks are imported by file picker and kept, the FLX4 plays/mixes a deck, LEDs answer, and the
controller settings are reachable from the phone's settings sheet.

    python tests/test_android.py [screenshot-prefix]
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_ios as I  # noqa: E402

PIXEL_UA = ("Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Mobile Safari/537.36")
# Chrome for Android: Web MIDI yes, folder picker no, output-device picking no
FAKE_FLX4 = """
delete window.showDirectoryPicker;
delete AudioContext.prototype.setSinkId;
window.__sent = [];
(() => {
  const inp = { id: 'in1', name: 'DDJ-FLX4', manufacturer: 'Pioneer DJ', type: 'input', state: 'connected', onmidimessage: null };
  const out = { id: 'out1', name: 'DDJ-FLX4', manufacturer: 'Pioneer DJ', type: 'output', state: 'connected', send(b) { window.__sent.push(Array.from(b)); } };
  window.__flx4 = (bytes) => inp.onmidimessage && inp.onmidimessage({ data: new Uint8Array(bytes) });
  navigator.requestMIDIAccess = async () => ({ inputs: new Map([['in1', inp]]), outputs: new Map([['out1', out]]), sysexEnabled: true, onstatechange: null });
})();
"""


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else None
    T.PORT = 8629
    srv = T.serve()
    check = T.check
    errors = []
    music = os.path.join(T.ROOT, "tests", "music")
    files = [os.path.join(music, n) for n in sorted(os.listdir(music)) if n.endswith(("126.wav", "140.wav"))]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 915, "height": 412}, screen={"width": 412, "height": 915},
                            is_mobile=True, has_touch=True, user_agent=PIXEL_UA, device_scale_factor=2.625)
        ctx.add_init_script(FAKE_FLX4)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.tap("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx && cratebox.MIDI.name")
        st = page.evaluate("({ phone: document.documentElement.classList.contains('phone'), pill: document.querySelector('#midiPill').textContent, on: document.querySelector('#midiPill').classList.contains('on'), prof: cratebox.MIDI.profile.id })")
        check("Android phone: landscape phone layout, FLX4 found and mapped", st["phone"] and st["on"] and "DDJ-FLX4" in st["pill"] and st["prof"] == "ddj-flx4", str(st))

        # music: no folder access on Android, so tracks are picked and copied into the browser's storage
        page.tap(".ptabs button[data-tab=lib]")
        check("library button says Add music (file picker, not folder)", page.inner_text("#addFolder") == "Add music")
        with page.expect_file_chooser() as fc:
            page.tap("#addFolder", force=True)
        fc.value.set_files(files)
        page.wait_for_function("cratebox.lib.tracks.length === 2 && cratebox.lib.tracks.every(t => t.stored)")
        page.reload()
        page.tap("#startBtn")
        page.wait_for_function("cratebox.lib.tracks.length === 2", timeout=20000)
        check("imported tracks are still there after a reload", True)

        # load from the library tab, then drive the deck from the FLX4
        page.tap(".ptabs button[data-tab=lib]")
        page.tap("#list .trow >> nth=0 >> .ld[data-d='0']")
        page.wait_for_function("cratebox.decks[0].loaded", timeout=60000)
        page.tap(".ptabs button[data-tab=mix]")
        res = page.evaluate("""async () => {
          const C = cratebox, tbl = [...C.MIDI.table.values()], f = (a, d) => tbl.find(e => e[2] === a && e[3] === d);
          const play = f('play', 0), fader = f('fader', 0), out = {};
          __flx4([fader[0], fader[1], 0]); out.faderLo = C.M.fader[0];
          __flx4([fader[0], fader[1], 127]); if (fader[4]) __flx4([fader[0], fader[4], 127]); out.faderHi = C.M.fader[0];
          __flx4([play[0], play[1], 127]); __flx4([play[0] & 0xef, play[1], 0]);
          await new Promise(r => setTimeout(r, 400));
          out.playing = C.decks[0].playing; out.t = C.decks[0].now();
          const pl = __sent.filter(m => m[0] === play[0] && m[1] === play[1]);
          out.ledPlay = pl.length > 0 && pl[pl.length - 1][2] > 0;          // blinking while paused, solid once playing
          __flx4([play[0], play[1], 127]); __flx4([play[0] & 0xef, play[1], 0]);
          return out; }""")
        check("FLX4 on Android: channel fader and PLAY work, PLAY lights up",
              res["faderLo"] < 0.01 and res["faderHi"] > 0.99 and res["playing"] and res["t"] > 0.1 and res["ledPlay"], str(res))
        lay = page.evaluate(I.LAYOUT)
        check("layout fits a 915x412 Android phone", not lay["outside"] and lay["overlaps"] == 0 and lay["scroll"][0] <= lay["scroll"][2], str(lay)[:300])
        if prefix:
            page.screenshot(path=prefix + "-android.png")

        # controller settings are in the phone's settings sheet (hidden on iPhone, which has no MIDI)
        page.tap("#setOpen")
        vis = page.evaluate("(() => { const b = document.querySelector('#ctlPanel').getBoundingClientRect(); return b.height > 0 && !!document.querySelector('#setSheet #ctlPanel'); })()")
        check("phone settings sheet shows the controller picker and Learn", vis and page.is_visible("#ctlProfile") and page.is_visible("#ctlLearn"))
        page.tap("#ctlLearn")
        check("Learn closes the sheet so the controls can be tapped", page.is_hidden("#setSheet") and page.is_visible("#learnBar"))
        page.tap("#learnDone")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
