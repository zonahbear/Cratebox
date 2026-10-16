"""Layout audit for the Mac edition: the 2017 MacBook Air's 1440 x 900 screen (full screen, and the
Firefox window with KDE's panel and Firefox's own toolbars), a smaller window, and external monitors.

For each size: nothing sticks out sideways, no controls overlap, button text isn't cut off.
Screenshots go to the folder given as the first argument (optional).

    python tests/test_layout.py [screenshot-folder]
    CB_THEME=booth CB_FOUR=1 python tests/test_layout.py      (the Booth look, 4-deck mode)
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402

# (name, viewport w, h)
DEVICES = [
    ("Air full screen (F11)", 1440, 900),
    ("Air Firefox window", 1440, 790),
    ("Air Firefox window + KDE panel", 1440, 744),
    ("Half-screen window", 1280, 720),
    ("Small window", 1024, 700),
    ("External Full HD", 1920, 1080),
    ("External 1440p", 2560, 1440),
]

AUDIT = """(() => {
  const W = innerWidth, H = innerHeight, r = (e) => e.getBoundingClientRect();
  const vis = (e) => { const b = r(e); const s = getComputedStyle(e); return b.width > 0 && b.height > 0 && s.visibility !== 'hidden'; };
  const ctl = [...document.querySelectorAll('#decks button, #decks .vslider, #decks .hslider, #decks .knob svg, #decks .jog, #decks .overview, #waves canvas, header button, .ltool button, .ltool input')].filter(vis);
  const outside = ctl.filter((e) => { const b = r(e); return b.left < -1 || b.right > W + 1; })
    .map((e) => (e.className || e.tagName) + ':' + (e.textContent || '').trim().slice(0, 12));
  // overlapping controls (each pair once; a knob's svg sits inside its .knob, buttons inside rows)
  const boxes = ctl.map((e) => [e, r(e)]);
  const over = [];
  for (let a = 0; a < boxes.length; a++) for (let b = a + 1; b < boxes.length; b++) {
    const [ea, A] = boxes[a], [eb, B] = boxes[b];
    if (ea.contains(eb) || eb.contains(ea)) continue;
    const ix = Math.min(A.right, B.right) - Math.max(A.left, B.left), iy = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
    if (ix > 2 && iy > 2) over.push(`${(ea.className || ea.tagName)}:${(ea.textContent || '').trim().slice(0, 8)} / ${(eb.className || eb.tagName)}:${(eb.textContent || '').trim().slice(0, 8)}`);
  }
  // button text cut off
  const clipped = [...document.querySelectorAll('#decks button, header button, .ltool button, .modes button')].filter(vis)
    .filter((e) => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 2).map((e) => (e.textContent || '').trim().slice(0, 14));
  const knob = document.querySelector('#mixer .strip .knob svg'), pad = document.querySelector('.deck .pad'), jog = document.querySelector('.deck .jog');
  return { W, H, sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, outside, over: over.slice(0, 12), nOver: over.length,
    clipped,
    sizes: { knob: knob ? Math.round(r(knob).width) : 0, pad: pad ? `${Math.round(r(pad).width)}x${Math.round(r(pad).height)}` : '', jog: jog ? Math.round(r(jog).width) : 0,
      fader: Math.round(r(document.querySelector('#mixer .faders .vslider')).height), lib: Math.round(r(document.querySelector('#list')).height) } };
})()"""


def main():
    shots = sys.argv[1] if len(sys.argv) > 1 else None
    only = sys.argv[2] if len(sys.argv) > 2 else None
    T.PORT = 8635
    srv = T.serve()
    check = T.check
    errors = []
    music = os.path.join(T.ROOT, "tests", "music")
    names = sorted(n for n in os.listdir(music) if n.endswith(("126.wav", "140.wav")))
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        for name, w, h in DEVICES:
            if only and only.lower() not in name.lower():
                continue
            ctx = b.new_context(viewport={"width": w, "height": h})
            # CB_THEME=booth / CB_FOUR=1: audit the Booth look and 4-deck mode too
            ctx.add_init_script(f"localStorage.setItem('cb.theme', '{os.environ.get('CB_THEME', 'booth')}'); localStorage.setItem('cb.themeChosen', '1'); localStorage.setItem('cb.four', '{os.environ.get('CB_FOUR', '0')}');")
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
            page.click("#startBtn")
            page.wait_for_function("window.cratebox && cratebox.A.ctx")
            page.evaluate("""async (names) => { const files = [];
                for (const n of names) files.push({ file: new File([await (await fetch('tests/music/' + encodeURIComponent(n))).blob()], n, { lastModified: 1 }), rel: 'music/' + n });
                await cratebox.addFiles(files); }""", names)
            page.wait_for_function("cratebox.lib.tracks.length === 2")
            page.evaluate("cratebox.lib.sel = 0; cratebox.loadSelected(0); cratebox.lib.sel = 1; cratebox.loadSelected(1)")
            page.wait_for_function("cratebox.decks.slice(0, 2).every(d => d.loaded)", timeout=60000)
            # deck 2 on PAD FX bank 2 (the longest pad labels), so those get audited too
            page.evaluate("cratebox.decks[1].padMode = 'padfx2'; document.querySelector('.deck[data-i=\"1\"] .modes button').click(); cratebox.decks[1].padMode = 'padfx2'")
            page.evaluate("(() => { const b = document.querySelectorAll('.deck[data-i=\"1\"] .modes button')[3]; b.click(); b.click(); })()")
            page.wait_for_timeout(400)
            a = page.evaluate(AUDIT)
            label = f"{name} {w}x{h}"
            problems = []
            if a["sw"] > w + 1: problems.append(f"page {a['sw']}px wide")
            if a["outside"]: problems.append(f"off screen: {a['outside'][:5]}")
            if a["nOver"]: problems.append(f"{a['nOver']} overlaps: {a['over'][:4]}")
            if a["clipped"]: problems.append(f"cut-off text: {a['clipped'][:6]}")
            check(f"{label}: layout clean", not problems, "; ".join(problems) or str(a["sizes"]))
            if shots:
                page.screenshot(path=os.path.join(shots, f"{name.replace(' ', '_').replace('(', '').replace(')', '')}.png"), full_page=True)
            ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
