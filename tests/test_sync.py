"""Sync: halftime/double-time locking and the beat lock that stops drift. Headless Chromium.

    python tests/test_sync.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_playlists as P  # noqa: E402


def main():
    T.PORT = 8633
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CRATEBOX_CHROME"]} if os.environ.get("CRATEBOX_CHROME") else {}), args=["--autoplay-policy=no-user-gesture-required"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        P.start(page)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)

        def load(i, tail):
            page.evaluate(f"cratebox.decks[{i}].load(cratebox.lib.tracks.find(t => t.title.endsWith('{tail}')))")
            page.wait_for_function(f"cratebox.decks[{i}].loaded && cratebox.decks[{i}].ana", timeout=60000)

        # ---- double time: 92 against 174 locks at 87 (half of 174), not 174
        load(0, "174"); load(1, "92")
        r = page.evaluate("""(() => { const [a, b] = cratebox.decks; a.togglePlay(); b.togglePlay(); b.setSync(true);
            return { mult: b.syncMult, rate: b.rate(), eff: b.effBpm(), btn: document.querySelector(".deck[data-i='1'] .sync").textContent }; })()""")
        page.wait_for_timeout(100)
        btn = page.evaluate("document.querySelector(\".deck[data-i='1'] .sync\").textContent")
        check("92 synced to 174 runs at half time (87), not doubled", r["mult"] == 0.5 and abs(r["eff"] - 87) < 0.01 and abs(r["rate"] - 87 / 92) < 0.002, str(r))
        check("SYNC button shows ½", btn == "SYNC ½", btn)
        page.wait_for_timeout(2500)
        pe = page.evaluate("cratebox.decks[1].phaseErr")
        check("half-time decks are beat-locked (every other beat of the 174)", pe is not None and abs(pe) < 0.004, f"{pe and pe * 1000:.1f} ms")
        # the master's tempo moves: the half-time deck follows at half
        page.evaluate("cratebox.decks[0].setPitch(-0.5)")      # 174 * 0.97 = 168.78
        page.wait_for_timeout(200)
        e = page.evaluate("[cratebox.decks[0].effBpm(), cratebox.decks[1].effBpm()]")
        check("master tempo change carries the half-time deck", abs(e[1] - e[0] / 2) < 0.01, str(e))
        page.evaluate("cratebox.decks[0].setPitch(0)")

        # ---- the beat lock: knock deck 2 15 ms out of phase while playing; it pulls back without a jump
        page.wait_for_timeout(500)
        page.evaluate("(() => { const d = cratebox.decks[1]; d.seek(d.now() + 0.015); })()")
        # read the slip once the deck has reported its new position (up to a second)
        page.wait_for_function("Math.abs(cratebox.decks[1].phaseErr || 0) > 0.008", timeout=1000)
        before = page.evaluate("cratebox.decks[1].phaseErr")
        page.wait_for_timeout(4000)
        after = page.evaluate("cratebox.decks[1].phaseErr")
        check("beat lock pulls a 15 ms slip back in", before is not None and abs(before) > 0.008 and abs(after) < 0.003, f"{before * 1000:.1f} ms -> {after * 1000:.1f} ms")
        trim = page.evaluate("Math.abs(cratebox.decks[1].syncTrim)")
        check("the correction is tiny (< 0.6 % speed)", trim <= 0.006, f"{trim:.4f}")

        # ---- an offset over a quarter beat that the user made with the platter is left alone (the tag says TEMPO)
        page.evaluate("(() => { const d = cratebox.decks[1]; d.jogTouch(true); d.seek(d.now() + d.spb * 0.4); d.jogTouch(false, true); })()")
        page.wait_for_timeout(1500)
        pe = page.evaluate("cratebox.decks[1].phaseErr")
        tag = page.evaluate("document.querySelector(\".deck[data-i='1'] .phasetag\")?.textContent || ''")
        check("a platter-made offset over a quarter beat isn't dragged back", abs(pe) > 0.1, f"{pe * 1000:.0f} ms")
        check("... and the phase tag says TEMPO", tag.startswith("TEMPO"), tag)
        page.evaluate("cratebox.decks[1].setSync(false); cratebox.decks[1].setSync(true)")
        page.wait_for_timeout(1500)
        page.wait_for_timeout(1500)
        pe = page.evaluate("cratebox.decks[1].phaseErr")
        check("SYNC off/on re-locks it", abs(pe) < 0.004, f"{pe * 1000:.1f} ms")
        # ---- any other big offset (a jump with Q off) is pulled back in, at up to 2 % (2026-10-28 iOS fix)
        page.evaluate("(() => { const d = cratebox.decks[1]; d.seek(d.now() + d.spb * 0.3); })()")
        page.wait_for_function("Math.abs(cratebox.decks[1].phaseErr || 0) > 0.1", timeout=1000)
        before = page.evaluate("cratebox.decks[1].phaseErr")
        took = page.evaluate("""async () => { const t0 = performance.now();
            while (performance.now() - t0 < 45000) { await new Promise(r => setTimeout(r, 250)); if (Math.abs(cratebox.decks[1].phaseErr) < 0.004) return (performance.now() - t0) / 1000; }
            return null; }""")
        check("a third-of-a-beat jump is pulled back onto the beat", took is not None, f"{before * 1000:.0f} ms -> locked in {took} s")

        # ---- stays locked over 20 s
        worst = page.evaluate("""async () => { let w = 0; for (let k = 0; k < 40; k++) { await new Promise(r => setTimeout(r, 500));
            const e = cratebox.decks[1].phaseErr; if (e != null) w = Math.max(w, Math.abs(e)); } return w; }""")
        check("no drift over 20 s of playing", worst < 0.004, f"worst {worst * 1000:.1f} ms")
        page.evaluate("cratebox.decks.forEach(d => { d.setSync(false); if (d.playing) d.togglePlay(); })")

        # ---- loading the other deck never retimes a playing synced deck (2026-10-23: a 72.5 halved to 36.25).
        # Deck 2 plays the 92 at half of the 174 (87); deck 1 stops and loads the 126. Before the fix deck 2
        # followed the stopped 126 with the old halftime: 63.
        load(0, "174"); load(1, "92")
        page.evaluate("(() => { const [a, b] = cratebox.decks; a.togglePlay(); b.setSync(true); b.togglePlay(); })()")
        page.wait_for_timeout(1000)
        page.evaluate("cratebox.decks[0].togglePlay()")
        load(0, "126")
        page.wait_for_timeout(500)
        e = page.evaluate("cratebox.decks[1].effBpm()")
        check("loading deck 1 leaves the playing synced deck 2 alone", abs(e - 87) < 0.05, f"{e:.2f} BPM")
        page.evaluate("cratebox.decks[0].togglePlay()")      # deck 1 played without SYNC: deck 2 keeps the lead
        page.wait_for_timeout(500)
        e = page.evaluate("cratebox.decks[1].effBpm()")
        check("starting the unsynced deck 1 doesn't move deck 2 either", abs(e - 87) < 0.05, f"{e:.2f} BPM")
        r = page.evaluate("(() => { const a = cratebox.decks[0]; a.togglePlay(); a.setSync(true); return { sync: a.sync, eff: a.effBpm() }; })()")
        check("SYNC on deck 1 at ±6% refuses 126 against 87 (needs -31% or +38%)", not r["sync"] and abs(r["eff"] - 126) < 0.05, str(r))
        r = page.evaluate("(() => { const a = cratebox.decks[0]; a.rangeIdx = 3; a.setSync(true); return { mult: a.syncMult, eff: a.effBpm() }; })()")
        check("at WIDE it follows the playing deck 2 (126 against 87: double time, 174)", r["mult"] == 2 and abs(r["eff"] - 174) < 0.05, str(r))
        page.evaluate("cratebox.decks[0].rangeIdx = 0")
        page.evaluate("cratebox.decks.forEach(d => { d.setSync(false); if (d.playing) d.togglePlay(); })")

        # ---- ordinary tempos still sync 1:1 (140 to 126)
        page.wait_for_timeout(200)
        load(0, "126"); load(1, "140")
        r = page.evaluate("(() => { const b = cratebox.decks[1]; b.rangeIdx = 1; b.setSync(true); return { mult: b.syncMult, eff: b.effBpm() }; })()")
        check("140 synced to 126 at ±10% runs at 126 (1:1)", r["mult"] == 1 and abs(r["eff"] - 126) < 0.01, str(r))
        page.evaluate("cratebox.decks.forEach(d => { d.setSync(false); d.rangeIdx = 0; if (d.playing) d.togglePlay(); })")

        # ---- the multiplier stays inside the tempo range: 92 against 140 at ±16% is refused at 1x (+52%)
        # and at 1/2x (-24%), so SYNC stays off and says why
        load(0, "140"); load(1, "92")
        r = page.evaluate("(() => { const b = cratebox.decks[1]; b.rangeIdx = 2; b.setSync(true); return { sync: b.sync, rate: b.rate() }; })()")
        msg = page.evaluate("document.querySelector('#status')?.textContent || ''")
        check("92 against 140 at ±16% is refused (no -24% jump)", not r["sync"] and abs(r["rate"] - 1) < 1e-6, str(r))
        check("... and the status says why", "can't sync" in msg and "WIDE" in msg, msg[:120])

        # ---- hold SYNC = master: deck 2 synced to deck 1; holding deck 2's SYNC makes deck 1 follow deck 2
        page.evaluate("cratebox.decks.forEach(d => { d.setSync(false); d.rangeIdx = 3; })")
        load(0, "126"); load(1, "140")
        page.evaluate("(() => { const [a, b] = cratebox.decks; a.togglePlay(); b.togglePlay(); a.setSync(true); b.setSync(true); })()")
        before = page.evaluate("[cratebox.decks[0].master()?.i, cratebox.decks[1].master()?.i]")
        btn = page.locator(".deck[data-i='1'] .sq.sync").first
        bb = btn.bounding_box()
        page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        page.mouse.down(); page.wait_for_timeout(700); page.mouse.up()
        page.wait_for_timeout(200)
        after = page.evaluate("({m: [cratebox.decks[0].master()?.i, cratebox.decks[1].master()?.i], sync: [cratebox.decks[0].sync, cratebox.decks[1].sync], eff: cratebox.decks[0].effBpm()})")
        check("before the hold deck 2 follows deck 1", before[1] == 0, str(before))
        check("holding SYNC on deck 2 makes it the master (deck 1 follows at 140)", after["m"][0] == 1 and after["m"][1] is None and abs(after["eff"] - 140) < 0.05, str(after))
        check("the release that ends the hold doesn't turn SYNC off", after["sync"] == [True, True], str(after["sync"]))
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
