"""Looks: Booth is the default; a look sticks only once picked in Settings.

    python tests/test_theme.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402


def main():
    T.PORT = 8665
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        def look(init):
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            if init:
                ctx.add_init_script(init)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
            page.wait_for_function("window.cratebox")
            return ctx, page, page.evaluate("document.documentElement.dataset.theme")
        ctx, page, t = look(None)
        check("first visit: Booth", t == "booth" and page.evaluate("document.querySelector('#themeSel').value") == "booth", t)
        # pick Cratebox classic in Settings: it sticks across a reload
        page.evaluate("const s = document.querySelector('#themeSel'); s.value = 'default'; s.dispatchEvent(new Event('change'))")
        page.reload()
        page.wait_for_function("window.cratebox")
        check("Cratebox classic picked in Settings: kept after a reload", page.evaluate("document.documentElement.dataset.theme") == "default")
        ctx.close()
        # 0.10.x saved "default" on every visit without anyone choosing it: those visitors now get Booth
        ctx, page, t = look("if (!sessionStorage.getItem('x')) { localStorage.setItem('cb.theme', 'default'); sessionStorage.setItem('x', '1'); }")
        check("saved by 0.10.x but never picked: Booth", t == "booth", t)
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
