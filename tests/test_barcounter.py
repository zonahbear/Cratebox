"""Bar counter (bar.beat like rekordbox): 1.1 1.2 1.3 1.4 2.1 ... on every deck, on screen and on phones.

    python tests/test_barcounter.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_ios as I  # noqa: E402
from test_fourdeck import load_all  # noqa: E402


def main():
    T.PORT = 8663
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
        # walk the first 9 beats: the middle of each beat reads bar.beat
        seq = page.evaluate("""(() => { const d = cratebox.decks[0], out = [];
            for (let k = 0; k < 9; k++) out.push(cratebox.barBeat(d, d.timeOfBeat(k + 0.5)));
            return out; })()""")
        check("counts 1.1 1.2 1.3 1.4 2.1 2.2 2.3 2.4 3.1", seq == ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "3.1"], str(seq))
        edge = page.evaluate("(() => { const d = cratebox.decks[0]; return [cratebox.barBeat(d, d.timeOfBeat(4)), cratebox.barBeat(d, d.timeOfBeat(4) - 0.001), cratebox.barBeat(d, d.timeOfBeat(64.5)), cratebox.barBeat(d, d.timeOfBeat(-0.5)), cratebox.barBeat(d, d.timeOfBeat(-4.5))]; })()")
        check("exactly on a downbeat it's x.1; just before, the previous bar's .4; bar 17 at beat 64", edge[:3] == ["2.1", "1.4", "17.1"], str(edge))
        check("before bar 1 it counts down 0.4 ... and -1.4", edge[3:] == ["0.4", "-1.4"], str(edge))

        # on screen: follows playback
        page.evaluate("(() => { const d = cratebox.decks[0]; d.seek(d.timeOfBeat(8.2)); })()")
        page.wait_for_timeout(300)
        check("deck shows the counter (bar 3 beat 1 at beat 8)", page.inner_text('.deck[data-i="0"] .bartag') == "3.1", page.inner_text('.deck[data-i="0"] .bartag'))
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.wait_for_timeout(1500)
        t = page.inner_text('.deck[data-i="0"] .bartag')
        page.evaluate("cratebox.decks[0].togglePlay()")
        check("...and moves on while playing", t not in ("", "3.1"), t)

        # BAR 1 HERE moves bar 1 to the playhead
        page.evaluate("(() => { const d = cratebox.decks[1]; d.seek(d.timeOfBeat(6)); })()")
        page.wait_for_timeout(200)
        page.evaluate("cratebox.decks[1].downbeatHere()")
        page.wait_for_timeout(300)
        # bars count from the start of the track (like rekordbox), so the playhead becomes the first beat of *a* bar
        check("BAR 1 HERE: the playhead becomes a downbeat (x.1)", page.inner_text('.deck[data-i="1"] .bartag').endswith(".1"), page.inner_text('.deck[data-i="1"] .bartag'))
        # compact decks show it too
        page.click("#fourBtn")
        load_all(page, 4)
        page.evaluate("(() => { const d = cratebox.decks[2]; d.seek(d.timeOfBeat(13.5)); })()")
        page.wait_for_timeout(300)
        check("compact deck 3 shows it", page.is_visible('.deck[data-i="2"] .bartag') and page.inner_text('.deck[data-i="2"] .bartag') == "4.2", page.inner_text('.deck[data-i="2"] .bartag'))
        ctx.close()

        # phone layout keeps it in the deck's info row
        ctx = b.new_context(viewport={"width": 956, "height": 440}, screen={"width": 440, "height": 956}, is_mobile=True, has_touch=True, user_agent=I.IPHONE_UA, device_scale_factor=3)
        ctx.add_init_script(I.STRIP)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        load_all(page, 2)
        page.evaluate("(() => { const d = cratebox.decks[0]; d.seek(d.timeOfBeat(2.5)); })()")
        page.wait_for_timeout(300)
        check("phone: counter visible", page.is_visible('.deck[data-i="0"] .bartag') and page.inner_text('.deck[data-i="0"] .bartag') == "1.3")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
