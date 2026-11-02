"""Waveform layouts: HIDE / SHOW WAVES, WAVE mode with its pop-up library, and the library's drag grip. Headless Chromium.

    python tests/test_wave.py [screenshot-folder]
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_playlists as P  # noqa: E402


def main():
    shots = sys.argv[1] if len(sys.argv) > 1 else None
    T.PORT = 8671
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CRATEBOX_CHROME"]} if os.environ.get("CRATEBOX_CHROME") else {}), args=["--autoplay-policy=no-user-gesture-required"])
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        P.start(page)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)
        page.evaluate("cratebox.decks[0].load(cratebox.lib.tracks[0]); cratebox.decks[1].load(cratebox.lib.tracks[1])")
        page.wait_for_function("cratebox.decks[0].ana && cratebox.decks[1].ana", timeout=60000)
        box = lambda sel: page.evaluate(f"(() => {{ const e = document.querySelector('{sel}'); if (!e) return null; const r = e.getBoundingClientRect(); return r.height > 0 ? [r.top, r.height, r.width] : null; }})()")
        parent = lambda sel: page.evaluate(f"document.querySelector('{sel}').parentElement.id || document.querySelector('{sel}').parentElement.className")

        # ---- the Booth look (the default) stacks the waveforms across the top, like the classic look
        check("Booth look: waveforms stacked across the top", page.evaluate("document.documentElement.dataset.theme") == "booth" and parent("#lane0") == "waves" and box("#lane0") and box("#lane0")[0] < 60)
        page.click("#lanesBtn")
        check("HIDE WAVES: the top lanes go and each deck shows its own", parent("#lane0") == "lanehost" and box("#waves") is None and page.inner_text("#lanesBtn") == "SHOW WAVES")
        page.reload(); page.click("#startBtn"); page.wait_for_function("window.cratebox && cratebox.A.ctx")
        check("... remembered after a reload", parent("#lane0") == "lanehost")
        page.click("#lanesBtn")
        check("SHOW WAVES brings them back", parent("#lane0") == "waves" and page.inner_text("#lanesBtn") == "HIDE WAVES")
        page.evaluate("cratebox.applyTheme('default', true)")
        page.click("#lanesBtn")
        check("the classic look can hide them too (decks get their own lanes)", parent("#lane0") == "lanehost")
        page.click("#lanesBtn")
        page.evaluate("cratebox.applyTheme('booth', true)")
        P.start(page)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)
        page.evaluate("cratebox.decks[0].load(cratebox.lib.tracks[0]); cratebox.decks[1].load(cratebox.lib.tracks[1])")
        page.wait_for_function("cratebox.decks[0].ana && cratebox.decks[1].ana", timeout=60000)

        # ---- the grip: dragging it down makes the waveforms taller and the library shorter; double-click resets
        l0, lib0 = box("#lane0"), box("#list")
        g = box("#libGrip")
        page.mouse.move(700, g[0] + g[1] / 2); page.mouse.down(); page.mouse.move(700, g[0] - 100, steps=6); page.mouse.up()
        page.wait_for_timeout(200)
        l1, lib1 = box("#lane0"), box("#list")
        check("dragging the grip up: a bigger library, shorter waveforms", l1[1] < l0[1] - 30 and lib1[1] > lib0[1] + 80, f"lane {l0[1]:.0f} -> {l1[1]:.0f}, list {lib0[1]:.0f} -> {lib1[1]:.0f}")
        g = box("#libGrip")
        page.mouse.move(700, g[0] + g[1] / 2); page.mouse.down(); page.mouse.move(700, g[0] + 90, steps=6); page.mouse.up()
        page.wait_for_timeout(200)
        l2, lib2 = box("#lane0"), box("#list")
        check("dragging it down again: the waveforms grow as the library shrinks", l2[1] > l1[1] + 30 and lib2[1] < lib1[1] - 60, f"lane {l1[1]:.0f} -> {l2[1]:.0f}, list {lib1[1]:.0f} -> {lib2[1]:.0f}")
        page.mouse.move(700, box("#libGrip")[0] + 4); page.mouse.down(); page.mouse.move(700, 1070, steps=8); page.mouse.up()
        page.wait_for_timeout(200)
        check("the library never gets squeezed under a few rows", box("#library")[1] >= 120, str(box("#library")))
        page.dblclick("#libGrip")
        page.wait_for_timeout(200)
        check("double-click on the grip: back to the usual size", abs(box("#lane0")[1] - l0[1]) < 2, f"{box('#lane0')[1]:.0f} vs {l0[1]:.0f}")

        # ---- WAVE mode: only the waveforms, with an info strip each; 3 decks = 3 lanes
        page.evaluate("cratebox.setDecks(3)")
        page.click("#waveBtn")
        page.wait_for_timeout(300)
        lanes = [box(f"#lane{i}") for i in range(4)]
        check("WAVE mode: decks, mixer and library hidden", box("#decks") is None and box("#library") is None)
        check("... three equal lanes fill the window (3 decks)", all(lanes[:3]) and lanes[3] is None and min(l[1] for l in lanes[:3]) > 200 and abs(lanes[0][1] - lanes[2][1]) < 3, str([l and round(l[1]) for l in lanes]))
        info = page.inner_text("#laneinfo0")
        check("... each lane has an info strip (title, BPM, key, time)", "Halftime Wobble 140" in info and "140.00" in info and "4A" in info and "-1:1" in info, info.replace("\n", " | "))
        if shots: page.screenshot(path=os.path.join(shots, "wave-3decks.png"))

        # ---- the pop-up library: arrow keys / browse knob open it, 1-3 load, Esc closes, 6 s idle closes
        check("the pop-up library starts closed", page.evaluate("document.querySelector('#wavePop').hidden"))
        page.evaluate("cratebox.lib.sort = 'bpm'; cratebox.lib.dir = 1; cratebox.applyView()")
        page.keyboard.press("ArrowDown")
        rows = page.evaluate("[...document.querySelectorAll('#wavePopRows > div')].map(r => r.textContent)")
        sel = page.evaluate("document.querySelector('#wavePopRows > div.on')?.textContent || ''")
        check("ArrowDown pops the library up over the waveforms, selection marked", not page.evaluate("document.querySelector('#wavePop').hidden") and len(rows) == 4 and sel.startswith("House Groove 126"), f"{sel} / {rows}")
        if shots: page.screenshot(path=os.path.join(shots, "wave-popup.png"))
        # a trackpad's small wheel steps add up to one row per 40 px, not one row each
        s0 = page.evaluate("cratebox.lib.sel")
        pb = page.evaluate("(() => { const r = document.querySelector('#wavePop').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        page.mouse.move(pb[0], pb[1])
        for _ in range(4): page.mouse.wheel(0, 10)
        page.wait_for_timeout(200)
        s1 = page.evaluate("cratebox.lib.sel")
        for _ in range(4): page.mouse.wheel(0, -10)
        page.wait_for_timeout(200)
        check("pop-up: four 10 px wheel steps move one row (and back)", s1 == s0 + 1 and page.evaluate("cratebox.lib.sel") == s0, f"{s0} {s1}")
        page.keyboard.press("3")
        page.wait_for_function("cratebox.decks[2].loaded", timeout=30000)
        check("pressing 3 loads it on deck 3 and closes the pop-up", "126" in page.evaluate("cratebox.decks[2].track.title") and page.evaluate("document.querySelector('#wavePop').hidden"))
        page.evaluate("cratebox.midiIn([0xB6, 0x40, 0x01])")      # FLX4 browse knob, one click
        check("the browse knob pops it up too", not page.evaluate("document.querySelector('#wavePop').hidden"))
        page.keyboard.press("Escape")
        check("Esc closes it", page.evaluate("document.querySelector('#wavePop').hidden"))
        page.keyboard.press("ArrowUp")
        page.wait_for_timeout(6500)
        check("it closes itself after 6 s without scrolling", page.evaluate("document.querySelector('#wavePop').hidden"))
        page.click("#waveBtn")
        page.wait_for_timeout(200)
        check("WAVE off: decks and library are back", box("#decks") is not None and box("#library") is not None and box("#laneinfo0") is None)

        # ---- phones: SCR turns one deck into a big platter with SCRATCH / CUE / PLAY; the other deck and the mixer stay
        ctx = b.new_context(viewport={"width": 852, "height": 393}, screen={"width": 393, "height": 852}, is_mobile=True, has_touch=True,
                            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        P.start(page)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)
        page.evaluate("cratebox.decks[0].load(cratebox.lib.tracks[0])")
        page.wait_for_function("cratebox.decks[0].ana", timeout=60000)
        box = lambda sel: page.evaluate(f"(() => {{ const e = document.querySelector('{sel}'); if (!e) return null; const r = e.getBoundingClientRect(); return r.height > 0 ? [r.top, r.height, r.width, r.left] : null; }})()")
        deck0 = box('.deck[data-i="0"]')
        page.tap('.deck[data-i="0"] .scrtab')
        page.wait_for_timeout(200)
        jog = box('.deck[data-i="0"] .jog')
        check("phone SCR: deck 1 shows a big platter, its pads and tempo fader fold away",
              jog and jog[1] > 120 and box('.deck[data-i="0"] .pads') is None and box('.deck[data-i="0"] .pitchwrap') is None, str(jog))
        check("... with SCRATCH, CUE and PLAY beside it", all(box(f'.deck[data-i="0"] .scrside {s}') for s in (".scrback", ".cue", ".play")))
        check("... the deck keeps its size, the mixer and deck 2 are untouched", abs(box('.deck[data-i="0"]')[1] - deck0[1]) < 2 and box('.deck[data-i="1"] .pads') and box("#mixer"))
        page.tap('.deck[data-i="0"] .scrside .play')
        page.wait_for_timeout(300)
        check("PLAY on the scratch face plays the deck", page.evaluate("cratebox.decks[0].playing"))
        j = box('.deck[data-i="0"] .jog')
        cx, cy, r = j[3] + j[2] / 2, j[0] + j[1] / 2, j[1] * 0.35
        page.mouse.move(cx + r, cy); page.mouse.down()
        held = page.evaluate("cratebox.decks[0].touch")
        page.mouse.up()
        check("touching the platter grabs the record (scratch)", held)
        page.tap('.deck[data-i="0"] .scrback')
        page.wait_for_timeout(200)
        check("SCRATCH again: back to the normal deck", box('.deck[data-i="0"] .pads') is not None and box('.deck[data-i="0"] .scrside') is None)
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
