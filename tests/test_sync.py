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
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
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
        page.wait_for_timeout(150)
        before = page.evaluate("cratebox.decks[1].phaseErr")
        page.wait_for_timeout(4000)
        after = page.evaluate("cratebox.decks[1].phaseErr")
        check("beat lock pulls a 15 ms slip back in", before is not None and abs(before) > 0.008 and abs(after) < 0.003, f"{before * 1000:.1f} ms -> {after * 1000:.1f} ms")
        trim = page.evaluate("Math.abs(cratebox.decks[1].syncTrim)")
        check("the correction is tiny (< 0.6 % speed)", trim <= 0.006, f"{trim:.4f}")

        # ---- a deliberate offset over a quarter beat is left alone
        page.evaluate("(() => { const d = cratebox.decks[1]; d.seek(d.now() + d.spb * 0.4); })()")
        page.wait_for_timeout(1500)
        pe = page.evaluate("cratebox.decks[1].phaseErr")
        check("an offset bigger than a quarter beat isn't dragged back", abs(pe) > 0.1, f"{pe * 1000:.0f} ms")
        page.evaluate("cratebox.decks[1].setSync(false); cratebox.decks[1].setSync(true)")
        page.wait_for_timeout(1500)
        pe = page.evaluate("cratebox.decks[1].phaseErr")
        check("SYNC off/on re-locks it", abs(pe) < 0.004, f"{pe * 1000:.1f} ms")

        # ---- stays locked over 20 s
        worst = page.evaluate("""async () => { let w = 0; for (let k = 0; k < 40; k++) { await new Promise(r => setTimeout(r, 500));
            const e = cratebox.decks[1].phaseErr; if (e != null) w = Math.max(w, Math.abs(e)); } return w; }""")
        check("no drift over 20 s of playing", worst < 0.004, f"worst {worst * 1000:.1f} ms")
        page.evaluate("cratebox.decks.forEach(d => { d.setSync(false); if (d.playing) d.togglePlay(); })")

        # ---- ordinary tempos still sync 1:1 (140 to 126)
        page.wait_for_timeout(200)
        load(0, "126"); load(1, "140")
        r = page.evaluate("(() => { const b = cratebox.decks[1]; b.setSync(true); return { mult: b.syncMult, eff: b.effBpm() }; })()")
        check("140 synced to 126 runs at 126 (1:1)", r["mult"] == 1 and abs(r["eff"] - 126) < 0.01, str(r))
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
