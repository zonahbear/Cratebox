"""EJECT (as in the iOS app): the header button shows while a rekordbox USB stick / SD card is open, refuses while a
deck plays from it, waits for a playlist save to finish, then lets go of the stick (its tracks leave the library).
With two sticks it asks which. Uses the mock stick from test_playlists.py.

    python tests/test_eject.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_playlists import MOCK_USB, start, tree_row, HOUSE  # noqa: E402


def main():
    T.PORT = 8671
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CRATEBOX_CHROME"]} if os.environ.get("CRATEBOX_CHROME") else {}), args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page, [HOUSE])
        check("no stick: no EJECT", page.is_hidden("#ejectBtn"))
        page.evaluate(MOCK_USB)
        page.wait_for_function("cratebox.PL.devices.length === 1")
        check("a stick open: EJECT shows", page.is_visible("#ejectBtn") and page.inner_text("#ejectBtn").strip() == "⏏ EJECT")

        tree_row(page, "SANDISK").click()
        page.evaluate("cratebox.lib.sel = cratebox.lib.view.findIndex(t => t.title === 'Demo Track 1'); cratebox.loadSelected(0)")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].track.device", timeout=60000)
        page.click("#ejectBtn")
        page.wait_for_timeout(300)
        check("a deck has a track from the stick: refused, stick stays",
              page.evaluate("cratebox.PL.devices.length") == 1 and "load something else" in page.inner_text("#status"), page.inner_text("#status"))

        page.evaluate("cratebox.setView({ kind: 'all' }); cratebox.lib.sel = 0; cratebox.loadSelected(0)")
        page.wait_for_function("cratebox.decks[0].loaded && !cratebox.decks[0].track.device", timeout=60000)
        # a save under way: EJECT waits for it
        page.evaluate("(() => { const d = cratebox.PL.devices[0]; d.saving = true; setTimeout(() => { d.saving = false; }, 800); })()")
        page.click("#ejectBtn")
        page.wait_for_timeout(300)
        check("a save under way: EJECT waits (stick still open, says so)",
              page.evaluate("cratebox.PL.devices.length") == 1 and "Finishing the save" in page.inner_text("#status"), page.inner_text("#status"))
        page.wait_for_function("cratebox.PL.devices.length === 0", timeout=5000)
        st = page.evaluate("({ dev: cratebox.lib.tracks.filter(t => t.device).length, msg: document.querySelector('#status').textContent })")
        check("...then lets go: stick tracks gone, message says eject it in the OS too", st["dev"] == 0 and "Finder / File Explorer" in st["msg"], str(st))
        check("...and EJECT hides", page.is_hidden("#ejectBtn"))

        # an unsaved change that can't be written: not ejected
        page.evaluate(MOCK_USB)
        page.wait_for_function("cratebox.PL.devices.length === 1")
        page.evaluate("(() => { const d = cratebox.PL.devices[0]; d.saving = true; })()")
        page.evaluate("cratebox.ejectDevice(cratebox.PL.devices[0])")
        page.wait_for_function("document.querySelector('#status').textContent.includes('Not ejected')", timeout=15000)
        check("a save that never finishes: not ejected, not safe to unplug", page.evaluate("cratebox.PL.devices.length") == 1)
        page.evaluate("cratebox.PL.devices[0].saving = false")

        # two sticks: EJECT ▾ asks which
        page.evaluate(MOCK_USB.replace("'SANDISK'", "'KINGSTON'"))
        page.wait_for_function("cratebox.PL.devices.length === 2")
        check("two sticks: EJECT ▾", page.inner_text("#ejectBtn").strip() == "⏏ EJECT ▾")
        page.click("#ejectBtn")
        items = page.evaluate("[...document.querySelectorAll('.popmenu button')].map(b => b.textContent)")
        check("...a menu with each stick", items == ["Eject SANDISK", "Eject KINGSTON"], str(items))
        page.click(".popmenu button >> text=Eject KINGSTON")
        page.wait_for_function("cratebox.PL.devices.length === 1", timeout=5000)
        check("...picking one ejects that one", page.evaluate("cratebox.PL.devices[0].name") == "SANDISK")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
