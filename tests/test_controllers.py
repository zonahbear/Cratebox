"""Controller profiles and MIDI learn, in headless Chromium.

Every built-in Pioneer/AlphaTheta profile is driven with its own MIDI messages (taken from the
profile's table) to check the engine runs each kind of control; device-name detection is checked
for the whole range; MIDI learn is exercised end to end.

    python tests/test_controllers.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402

NAMES = {
    "DDJ-FLX4": "ddj-flx4", "DDJ-FLX4 MIDI 1": "ddj-flx4", "DDJ-400": "ddj-400", "DDJ-200": "ddj-200",
    "PIONEER DDJ-SB3": "ddj-sb3", "DDJ-SB2": "ddj-sb2", "PIONEER DDJ-SB": "ddj-sb", "DDJ-SX2": "ddj-sx2", "DDJ-SX3": "ddj-sx2",
    "PIONEER DDJ-SX": "ddj-sx", "XDJ-RX": "xdj-rx", "CDJ-2000NXS2": "cdj-2000", "CDJ-850": "cdj-850", "CDJ-350": "cdj-350",
    "DDJ-FLX6": "ddj-rekordbox", "DDJ-FLX10": "ddj-rekordbox", "DDJ-FLX2": "ddj-rekordbox", "DDJ-1000": "ddj-rekordbox",
    "DDJ-800": "ddj-rekordbox", "DDJ-GRV6": "ddj-rekordbox", "XDJ-RX3": "ddj-rekordbox", "XDJ-XZ": "ddj-rekordbox", "XDJ-AZ": "ddj-rekordbox",
    "OPUS-QUAD": "ddj-rekordbox", "DDJ-REV7": "ddj-serato", "DDJ-SR2": "ddj-serato", "DDJ-1000SRT": "ddj-serato", "DDJ-SZ2": "ddj-serato",
    "CDJ-3000": "cdj", "XDJ-1000MK2": "cdj", "nanoKONTROL2": "learn",
}


def main():
    T.PORT = 8625
    srv = T.serve()
    check = T.check
    errors = []
    music = os.path.join(T.ROOT, "tests", "music")
    names = sorted(n for n in os.listdir(music) if n.endswith(("126.wav", "140.wav")))
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox.A.ctx && window.cratebox.A.decks.length === 2")
        page.evaluate("cratebox.MIDI.outputs = [{ send() {} }]")
        page.evaluate("""async (names) => {
            const files = [];
            for (const n of names) files.push({ file: new File([await (await fetch('tests/music/' + encodeURIComponent(n))).blob()], n, { lastModified: 1 }), rel: 'music/' + n });
            await cratebox.addFiles(files); }""", names)
        page.wait_for_function("cratebox.lib.tracks.length === 2 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)
        page.evaluate("cratebox.lib.sel = 0; cratebox.loadSelected(0); cratebox.lib.sel = 1; cratebox.loadSelected(1)")
        page.wait_for_function("cratebox.decks.every(d => d.loaded)", timeout=60000)

        got = page.evaluate("(names) => Object.fromEntries(names.map(n => [n, cratebox.profileFor(n).id]))", list(NAMES))
        wrong = {n: (got[n], w) for n, w in NAMES.items() if got[n] != w}
        check(f"device names pick the right profile ({len(NAMES)} models)", not wrong, str(wrong))

        # every profile: find its messages for a set of actions and send them
        res = page.evaluate("""async () => {
          const out = {}, C = cratebox, d0 = C.decks[0], d1 = C.decks[1];
          const send = (b) => C.midiIn(b);
          for (const P of C.PROFILES) {
            if (P.id === "learn") continue;
            const p = C.useProfile(P.id), tbl = [...C.MIDI.table.values()];
            const find = (a, deck) => tbl.find(e => e[2] === a && (deck == null || e[3] === deck));
            const r = {};
            // play / pause deck 1
            let e = find("play", 0);
            if (e) { const was = d0.playing; send([e[0], e[1], 127]); send([e[0] & 0xef, e[1], 0]); r.play = d0.playing !== was; if (d0.playing) d0.togglePlay(); }
            // channel fader deck 2 (14-bit where the profile has it)
            e = find("fader", 1);
            if (e) { send([e[0], e[1], 0]); const lo = C.M.fader[1]; send([e[0], e[1], 127]); if (e[4]) send([e[0], e[4], 127]); r.fader = lo < 0.01 && C.M.fader[1] > 0.99; }
            // tempo deck 1: bottom of the fader = faster
            e = find("tempo", 0);
            if (e) { send([e[0], e[1], 127]); if (e[4]) send([e[0], e[4], 127]); const fast = d0.rate(); send([e[0], e[1], 64]); if (e[4]) send([e[0], e[4], 0]); r.tempo = fast > 1.01 && Math.abs(d0.rate() - 1) < 0.01; }
            // hot cue A on deck 2 (set), then its clear if the profile has one
            e = find("hot:0", 1);
            if (e) { d1.padMode = "hotcue"; d1.hot[0] = null; send([e[0], e[1], 127]); send([e[0], e[1], 0]); r.hot = d1.hot[0] != null;
              const c = find("hotClear:0", 1); if (c) { send([c[0], c[1], 127]); r.hotClear = d1.hot[0] == null; } }
            // jog: touch the platter and turn it: deck 1 moves forward by hand
            const t = find("touch", 0), j = find("jogTop", 0);
            if (t && j) {
              const before = d0.now(); send([t[0], t[1], 127]);
              for (let k = 0; k < 40; k++) send([j[0], j[1], 64 + 20]);
              await new Promise(res => setTimeout(res, 300)); send([t[0] & 0xef, t[1], 0]);
              await new Promise(res => setTimeout(res, 100)); r.jog = d0.now() - before > 0.5;
            }
            // EQ low kill + crossfader
            e = find("low", 0); if (e) { send([e[0], e[1], 0]); r.low = C.M.low[0] < 0.01; send([e[0], e[1], 64]); }
            e = find("xfader", -1); if (e) { send([e[0], e[1], 0]); r.xfader = C.M.xfader < 0.01; send([e[0], e[1], 64]); }
            // browse knob moves the selection
            e = find("browse", -1); if (e) { C.lib.sel = 0; send([e[0], e[1], 1]); r.browse = C.lib.sel === 1; }
            // jog: touch + turn scratches deck 1
            out[P.id] = r;
          }
          C.useProfile("ddj-flx4");
          return out;
        }""")
        for pid, r in res.items():
            r.pop("_jogTarget", None)
            bad = [k for k, v in r.items() if v is not True]
            check(f"{pid}: {', '.join(sorted(r))} respond", r and not bad, f"failed: {bad}" if bad else "")
        page.wait_for_timeout(600)

        # MIDI learn: map an unknown controller's fader and play button
        page.evaluate("cratebox.useProfile('learn'); localStorage.removeItem('cb.learn.learn'); cratebox.useProfile('learn')")
        page.evaluate("cratebox.startLearn()")
        check("Learn mode shows its bar", page.is_visible("#learnBar"))
        page.click("#mixer .faders .vslider >> nth=0")
        page.evaluate("cratebox.midiIn([0xB3, 0x05, 20])")
        page.click(".deck[data-i='1'] .round.play")
        page.evaluate("cratebox.midiIn([0x9F, 0x10, 127]); cratebox.midiIn([0x8F, 0x10, 0])")
        page.click(".deck[data-i='0'] .jog")
        page.evaluate("cratebox.midiIn([0x9F, 0x11, 127]); cratebox.midiIn([0xB3, 0x30, 70])")
        page.click("#learnBar button[data-learn=browse]")
        page.evaluate("cratebox.midiIn([0xBF, 0x01, 1])")
        page.click("#learnDone")
        learned = page.evaluate("cratebox.MIDI.learned.map(e => e.slice(0, 4).join(','))")
        check("learned: fader (with 14-bit fine part), play, jog touch + turn, browse knob",
              sorted(learned) == sorted(["179,5,fader,0", "159,16,play,1", "159,17,touch,0", "179,48,jogTop,0", "191,1,browse,-1"]), str(learned))
        page.evaluate("cratebox.midiIn([0xB3, 0x05, 127]); cratebox.midiIn([0xB3, 0x25, 127])")
        was = page.evaluate("cratebox.decks[1].playing")
        page.evaluate("cratebox.midiIn([0x9F, 0x10, 127]); cratebox.midiIn([0x8F, 0x10, 0])")
        st = page.evaluate("({ f: cratebox.M.fader[0], p: cratebox.decks[1].playing })")
        check("learned controls work", st["f"] > 0.99 and st["p"] != was, str(st))
        page.wait_for_timeout(300)
        log = page.evaluate("cratebox.MIDI.log.map(m => m.join(','))")
        check("learned buttons get LED feedback on their own note", any(m.startswith("159,16,") for m in log))
        page.reload()
        page.click("#startBtn")
        page.wait_for_function("window.cratebox.A.ctx")
        n = page.evaluate("cratebox.useProfile('learn'); cratebox.MIDI.learned.length")
        check("learned mapping is remembered", n == 5, str(n))
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
