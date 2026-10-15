"""Layout audit across devices: phones (landscape), tablets, laptops and big screens.

For each size: nothing sticks out sideways, no controls overlap, button text isn't cut off, touch
targets are big enough on touch screens, the decks and mixer fit without scrolling where the
layout promises it. Screenshots go to the folder given as the first argument (optional).

    python tests/test_layout.py [screenshot-folder]
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_ios as I  # noqa: E402

ANDROID_UA = "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36"
ANDROID_TAB_UA = "Mozilla/5.0 (Linux; Android 14; SM-X810) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
# (name, viewport w, h, screen short side, kind)  kind: iphone / android / ipad / atab / desktop
DEVICES = [
    ("iPhone SE", 667, 375, 375, "iphone"),
    ("iPhone 13 mini", 812, 375, 375, "iphone"),
    ("iPhone 15", 852, 393, 393, "iphone"),
    ("iPhone 16 Pro Max", 956, 440, 440, "iphone"),
    ("iPhone 16 Pro Max (Safari bars)", 956, 380, 440, "iphone"),
    ("Galaxy A (small)", 780, 360, 360, "android"),
    ("Pixel 9 Pro", 915, 412, 412, "android"),
    ("Galaxy S24 Ultra", 932, 430, 430, "android"),
    ("iPad mini landscape", 1133, 744, 744, "ipad"),
    ("iPad mini portrait", 744, 1133, 744, "ipad"),
    ("iPad Air landscape", 1180, 820, 820, "ipad"),
    ("iPad Pro 13 landscape", 1366, 1024, 1024, "ipad"),
    ("Android tablet", 1280, 800, 800, "atab"),
    ("Laptop 1280x720", 1280, 720, 0, "desktop"),
    ("Laptop 1366x768", 1366, 768, 0, "desktop"),
    ("Laptop 1440x900", 1440, 900, 0, "desktop"),
    ("Small window 1024x700", 1024, 700, 0, "desktop"),
    ("Full HD", 1920, 1080, 0, "desktop"),
    ("1440p", 2560, 1440, 0, "desktop"),
]

AUDIT = """(() => {
  const W = innerWidth, H = innerHeight, r = (e) => e.getBoundingClientRect();
  const vis = (e) => { const b = r(e); const s = getComputedStyle(e); return b.width > 0 && b.height > 0 && s.visibility !== 'hidden'; };
  const phone = document.documentElement.classList.contains('phone');
  const touch = document.documentElement.classList.contains('touch');
  const ctl = [...document.querySelectorAll('#decks button, #decks .vslider, #decks .hslider, #decks .knob svg, #decks .jog, #decks .overview, #waves canvas, header button, .ltool button, .ltool input')].filter(vis);
  const outside = ctl.filter((e) => { const b = r(e); return b.left < -1 || b.right > W + 1 || (phone && (b.top < -1 || b.bottom > H + 1)); })
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
  const clipped = [...document.querySelectorAll('#decks button, header button, .ltool button, .pbtns button, .modes button')].filter(vis)
    .filter((e) => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 2).map((e) => (e.textContent || '').trim().slice(0, 14));
  // touch targets
  const small = touch ? ctl.filter((e) => e.tagName === 'BUTTON' || e.classList.contains('vslider') || e.tagName === 'svg')
    .filter((e) => { const b = r(e); return Math.min(b.width, b.height) < (phone ? 24 : 28); }).map((e) => `${(e.textContent || e.className.baseVal || e.className || '').toString().trim().slice(0, 10)} ${Math.round(r(e).width)}x${Math.round(r(e).height)}`) : [];
  const knob = document.querySelector('#mixer .strip .knob svg'), pad = document.querySelector('.deck .pad'), jog = document.querySelector('.deck .jog');
  return { phone, touch, W, H, sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, outside, over: over.slice(0, 12), nOver: over.length,
    clipped, small: small.slice(0, 10), nSmall: small.length,
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
        for name, w, h, short, kind in DEVICES:
            if only and only.lower() not in name.lower():
                continue
            opts = {"viewport": {"width": w, "height": h}}
            if kind != "desktop":
                ua = {"iphone": I.IPHONE_UA, "ipad": I.IPAD_UA, "android": ANDROID_UA, "atab": ANDROID_TAB_UA}[kind]
                long_ = max(w, h)
                opts.update(is_mobile=kind in ("iphone", "android"), has_touch=True, user_agent=ua, device_scale_factor=3 if kind == "iphone" else 2,
                            screen={"width": short, "height": long_} if h < w else {"width": short, "height": long_})
            ctx = b.new_context(**opts)
            if kind in ("iphone", "ipad"):
                ctx.add_init_script(I.STRIP)
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
            page.wait_for_function("cratebox.decks.every(d => d.loaded)", timeout=60000)
            page.wait_for_timeout(400)
            a = page.evaluate(AUDIT)
            label = f"{name} {w}x{h}"
            problems = []
            if a["sw"] > w + 1: problems.append(f"page {a['sw']}px wide")
            if a["phone"] and a["sh"] > h + 1: problems.append(f"page {a['sh']}px tall")
            if a["outside"]: problems.append(f"off screen: {a['outside'][:5]}")
            if a["nOver"]: problems.append(f"{a['nOver']} overlaps: {a['over'][:4]}")
            if a["clipped"]: problems.append(f"cut-off text: {a['clipped'][:6]}")
            if a["nSmall"]: problems.append(f"{a['nSmall']} small touch targets: {a['small'][:5]}")
            check(f"{label}: {'phone' if a['phone'] else 'touch' if a['touch'] else 'desktop'} layout clean", not problems, "; ".join(problems) or str(a["sizes"]))
            if shots:
                page.screenshot(path=os.path.join(shots, f"{name.replace(' ', '_').replace('(', '').replace(')', '')}.png"), full_page=not a["phone"])
            ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
