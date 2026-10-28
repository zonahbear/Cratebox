"""HEAT's HOLD, PUFF and GLOW (the Puffco as an instrument and a light), on the simulator in headless Chromium.

DSP: Beat FX PUFF rendered offline from the fx-unit worklet with silence in: its theremin voice sings
about 880 Hz on a hard hit, lower and quieter on a light one, nothing with no hit, and stays finite.
Maths: PuffDrop reads nothing at rest and a lot during a draw on the simulated heater; Glow brightens
with the music and moves through the rainbow. Live: PUFF is only on offer in Beat FX while a Puffco is
connected; HOLD for PUFF heats, the simulator's hit button plays PUFF, Stop puts slot 4 back; GLOW
writes lantern colours between runs only.

    python tests/test_puff.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402

UNLOCK = "localStorage.setItem('cb.heatUnlocked', '1'); localStorage.setItem('cb.heat', '1');"

# PUFF's voice alone: silence in, one hit strength; pitch from upward zero crossings in the last second
SING = """async (hit) => {
  const sr = 48000, n = sr * 3, off = new OfflineAudioContext(2, n, sr);
  await off.audioWorklet.addModule(URL.createObjectURL(new Blob([cratebox.WORKLET], { type: 'text/javascript' })));
  const node = new AudioWorkletNode(off, 'fx-unit', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2] });
  const src = off.createConstantSource(); src.offset.value = 0; src.connect(node); node.connect(off.destination);
  node.port.postMessage({ t: 'slot', slot: 'beat', fx: 'PUFF', depth: 1, on: true, mod: hit });
  src.start(0);
  await new Promise((r) => setTimeout(r, 60));
  const out = (await off.startRendering()).getChannelData(0);
  let up = 0, peak = 0, nan = false;
  for (let i = 2 * sr; i < n; i++) { if (out[i - 1] < 0 && out[i] >= 0) up++; peak = Math.max(peak, Math.abs(out[i])); if (!isFinite(out[i])) nan = true; }
  return { hz: up, peak, nan };
}"""

# PuffDrop on the simulator's heater model (same plant as TC.Sim), 500°F hold, a hard draw from 10 to 14 s
DROP = """(() => {
  const { PuffDrop } = cratebox.TC, truth = { tau: 3.0, heatMax: 15, coolK: 0.011, dead: 0.45 };
  const step = (y, u, dt, air) => { const rate = u > y ? Math.min((u - y) / truth.tau, truth.heatMax) : Math.max((u - y) / truth.tau, -truth.coolK * (y - 70)); return y + (rate - air * 12) * dt; };
  const m = new PuffDrop(500);
  let y = 495, t = 0, rest = 0, peak = 0, after = 1;
  while (t < 25) {
    const air = t >= 10 && t < 14 ? 1 : 0;
    for (let k = 0; k < 10; k++) y = step(y, 500, 0.01, air);
    t += 0.1;
    const a = m.add(t, y + (Math.random() - 0.5) * 1.2);
    if (t > 2 && t < 10) rest = Math.max(rest, a);
    if (t >= 10 && t < 14) peak = Math.max(peak, a);
    if (t > 17) after = Math.min(after, a);
  }
  return { rest, peak, after };
})()"""

GLOW = """(() => {
  const g = new cratebox.TC.Glow(), max = (c) => Math.max(...c);
  let quiet, loud, low;
  for (let i = 0; i < 100; i++) quiet = g.color(0.05, 0, 0.5, 'intensity');
  for (let i = 0; i < 20; i++) loud = g.color(0.05, 0.9, 0.5, 'intensity');
  const h0 = g.hue;
  for (let i = 0; i < 100; i++) g.color(0.05, 0.5, 0.5, 'intensity');
  const moved = g.hue !== h0;
  for (let i = 0; i < 100; i++) low = g.color(0.05, 1, 0, 'intensity');
  const t = new cratebox.TC.Glow(); let sent = 0;
  for (let i = 0; i < 100; i++) if (t.tick(i * 0.05, (i % 7) / 7, 1, 'speed')) sent++;
  return { quiet: max(quiet), loud: max(loud), moved, low: max(low), sent };
})()"""


def main():
    T.PORT = 8673
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = b.new_page(viewport={"width": 1440, "height": 790})
        page.add_init_script(UNLOCK)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")

        hard, soft, none = page.evaluate(SING, 1), page.evaluate(SING, 0.2), page.evaluate(SING, 0)
        check("PUFF: a hard hit sings about 880 Hz", 780 <= hard["hz"] < 980, f"{hard['hz']} Hz, peak {hard['peak']:.3f}")
        check("PUFF: a light hit is lower and quieter", soft["hz"] < hard["hz"] * 0.6 and soft["peak"] < hard["peak"], f"{soft['hz']} Hz, peak {soft['peak']:.3f}")
        check("PUFF: no hit, no voice", none["peak"] < 1e-4, f"{none['peak']}")
        check("PUFF: finite", not (hard["nan"] or soft["nan"] or none["nan"]))

        d = page.evaluate(DROP)
        check("PuffDrop: nothing at rest, a lot on a draw, lets go after", d["rest"] == 0 and d["peak"] > 0.9 and d["after"] == 0, str(d))
        g = page.evaluate(GLOW)
        check("GLOW: louder is brighter, the rainbow moves, knob down dims it", g["loud"] > g["quiet"] * 2 and g["moved"] and g["low"] < 60, str(g))
        check("GLOW: at most 5 colours a second", 3 < g["sent"] <= 26, str(g["sent"]))

        def panel():
            if not page.evaluate("document.querySelector('#tcPanel').matches(':popover-open')"):
                page.click("#tcBtn")

        names = lambda: page.evaluate("(() => { const s = new Set(); for (let i = 0; i < 12; i++) { cratebox.fxSelect(1); s.add(cratebox.FX.beat.fx); } return [...s]; })()")
        check("PUFF not on offer without a Puffco", "PUFF" not in names())

        # GLOW on, then the simulator: colours go to the lantern
        panel()
        page.check("#tcGlow")
        page.click("#tcSim")
        page.wait_for_function("cratebox.TC.dev && cratebox.TC.dev.connected")
        page.evaluate("""(() => { const d = cratebox.TC.dev; d.colors = []; d.lamp = null;
          d.lantern = async (on) => { d.lamp = on; return true; }; d.lanternColor = async (c) => { d.colors.push(c); return true; }; })()""")
        page.wait_for_timeout(1500)
        c = page.evaluate("({ n: cratebox.TC.dev.colors.length, lamp: cratebox.TC.dev.lamp })")
        check("GLOW: lantern on and colours sent while idle", c["lamp"] is True and 2 <= c["n"] <= 9, str(c))
        check("PUFF on offer with the simulator connected", "PUFF" in names())

        # HOLD for PUFF
        page.evaluate("cratebox.TC.dev.y = 495; cratebox.TC.dev.slotIdx = 1")
        page.evaluate("while (cratebox.FX.beat.fx !== 'PUFF') cratebox.fxSelect(1); cratebox.fxOn(true)")
        panel()
        page.fill("#tcHoldF", "500")
        page.dispatch_event("#tcHoldF", "change")
        page.click("#tcHold")
        page.wait_for_function("cratebox.TC.S.phase === 'hold'", timeout=10000)
        n0 = page.evaluate("cratebox.TC.dev.colors.length")
        page.wait_for_timeout(3000)
        check("HOLD: button shows HOLD and the temperature", page.inner_text("#tcBtn").startswith("HOLD "), page.inner_text("#tcBtn"))
        panel()
        check("HOLD: hit button shown for the simulator", page.is_visible("#tcHit"))
        box = page.locator("#tcHit").bounding_box()
        page.mouse.move(box["x"] + 10, box["y"] + 5)
        page.mouse.down()
        page.wait_for_function("cratebox.TC.S.puff > 0.5", timeout=8000)
        check("HOLD: a hit plays PUFF", page.evaluate("cratebox.FX.mod") > 0.5, f"{page.evaluate('cratebox.FX.mod'):.2f}")
        check("HOLD: readout shows the dip", "dip" in page.inner_text("#tcPuffInfo"), page.inner_text("#tcPuffInfo"))
        page.mouse.up()
        page.wait_for_function("cratebox.TC.S.puff === 0", timeout=8000)
        check("HOLD: letting go lets PUFF go", page.evaluate("cratebox.FX.mod") == 0)
        check("GLOW paused during HOLD", page.evaluate("cratebox.TC.dev.colors.length") == n0)
        panel()
        page.click("#tcHold")
        page.wait_for_function("!cratebox.TC.S.running", timeout=10000)
        dev = page.evaluate("({ slot: cratebox.TC.dev.slotIdx, s3: cratebox.TC.dev.slots[3], state: cratebox.TC.dev.state })")
        check("HOLD: Stop puts slot 4 and the active slot back, heater off", dev["slot"] == 1 and dev["s3"]["temp"] == 485 and dev["state"] == 5, str(dev))
        page.wait_for_timeout(800)
        check("GLOW resumes after HOLD", page.evaluate("cratebox.TC.dev.colors.length") > n0)
        panel()
        page.uncheck("#tcGlow")
        page.wait_for_timeout(400)
        check("GLOW off turns the lantern off", page.evaluate("cratebox.TC.dev.lamp") is False)

        page.click("#tcDisc")
        page.wait_for_function("!cratebox.TC.dev")
        check("PUFF gone again after disconnecting", "PUFF" not in names())
        check("no page errors", not errors, "; ".join(errors[:3]))
        b.close()
    srv.shutdown()
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
