"""Beat FX and Pad FX: the effects measured on real audio, and the controls (screen + FLX4 MIDI).

DSP part: Cratebox's own "fx-unit" audio worklet is rendered offline (OfflineAudioContext) on test
signals (impulses, tones, noise) with a known beat clock (120 BPM), and the output is measured:
echo timing and decay, echo tails ringing out after OFF, ping pong sides, reverb tail, trans gating
on the beat, roll repeating a grid-aligned slice, HPF/LPF, filter sweep, flanger, a clean pass-through
when nothing is on, no NaNs, and how much CPU the effects take.

Live part: the Beat FX panel and the FLX4's BEAT FX section (select, beat, CH SELECT lever incl.
MASTER, depth, on/off + LED) route the effect to the right insert; PAD FX mode holds an effect while a
pad is held (screen and FLX4 pads, LEDs); effects running on a playing deck stay finite.

    python tests/test_fx.py
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
from test_fourdeck import load_all  # noqa: E402

# render the fx-unit offline. spec: { sig, dur, slot: {...}, offAt, clock } -> { L, R } sampled arrays + stats
RENDER = """async (spec) => {
  const sr = 44100, n = Math.round(spec.dur * sr);
  const off = new OfflineAudioContext(2, n, sr);
  await off.audioWorklet.addModule(URL.createObjectURL(new Blob([cratebox.WORKLET], { type: 'text/javascript' })));
  const buf = off.createBuffer(2, n, sr), L = buf.getChannelData(0), R = buf.getChannelData(1);
  const sig = spec.sig;
  for (let i = 0; i < n; i++) {
    const t = i / sr; let v = 0;
    if (sig.kind === 'impulse') v = sig.at.some((a) => Math.abs(t - a) < 0.5 / sr) ? 1 : 0;
    else if (sig.kind === 'tone') v = 0.5 * Math.sin(2 * Math.PI * sig.f * t);
    else if (sig.kind === 'noise') { v = (Math.sin(i * 12.9898) * 43758.5453) % 1; v = (v - Math.floor(v)) - 0.5; }
    else if (sig.kind === 'ramp') v = (t % 1) - 0.5;      // a sawtooth with a 1 s period: every moment is different
    L[i] = v; R[i] = sig.right === 0 ? 0 : v;
  }
  const src = off.createBufferSource(); src.buffer = buf;
  const node = new AudioWorkletNode(off, 'fx-unit', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2] });
  src.connect(node); node.connect(off.destination);
  node.port.postMessage({ t: 'clock', t0: 0, beat0: 0, bps: 2, spb: 0.5, ...(spec.clock || {}) });
  if (spec.slot) node.port.postMessage({ t: 'slot', slot: spec.slotName || 'beat', ...spec.slot, on: spec.onAt == null });
  if (spec.onAt != null) off.suspend(spec.onAt).then(() => { node.port.postMessage({ t: 'slot', slot: spec.slotName || 'beat', on: true }); off.resume(); });
  if (spec.offAt != null) off.suspend(spec.offAt).then(() => { node.port.postMessage({ t: 'slot', slot: spec.slotName || 'beat', on: false }); off.resume(); });
  src.start(0);
  await new Promise((r) => setTimeout(r, 60));          // let the messages reach the processor before rendering
  const t0 = performance.now();
  const out = await off.startRendering();
  const ms = performance.now() - t0;
  const oL = out.getChannelData(0), oR = out.getChannelData(1);
  let nan = false; for (let i = 0; i < n; i += 7) if (!isFinite(oL[i]) || !isFinite(oR[i])) { nan = true; break; }
  // summaries the Python side asks for
  const at = (ch, t) => (ch === 0 ? oL : oR)[Math.round(t * sr)];
  const peakIn = (ch, a, b) => { const x = ch === 0 ? oL : oR; let p = 0; for (let i = Math.round(a * sr); i < Math.round(b * sr); i++) p = Math.max(p, Math.abs(x[i])); return p; };
  const rmsIn = (ch, a, b) => { const x = ch === 0 ? oL : oR; let s = 0, k = 0; for (let i = Math.round(a * sr); i < Math.round(b * sr); i++) { s += x[i] * x[i]; k++; } return Math.sqrt(s / Math.max(1, k)); };
  const res = { nan, ms, inMax: 0, diffIn: 0 };
  for (const q of spec.ask || []) res[q.name] = q.kind === 'peak' ? peakIn(q.ch || 0, q.a, q.b) : q.kind === 'rms' ? rmsIn(q.ch || 0, q.a, q.b) : at(q.ch || 0, q.t);
  if (spec.compare) { let d = 0; for (let i = 0; i < n; i++) d = Math.max(d, Math.abs(oL[i] - L[i]), Math.abs(oR[i] - R[i])); res.diffIn = d; }
  if (spec.period) {   // largest difference between out(t) and out(t + period) inside [a, b]
    const p = Math.round(spec.period.p * sr); let d = 0, m = 0;
    for (let i = Math.round(spec.period.a * sr); i < Math.round(spec.period.b * sr); i++) { d = Math.max(d, Math.abs(oL[i] - oL[i + p])); m = Math.max(m, Math.abs(oL[i])); }
    res.periodDiff = d; res.periodPeak = m;
  }
  return res;
}"""


def main():
    T.PORT = 8679
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
        page.wait_for_function("window.cratebox")
        R = lambda spec: page.evaluate(RENDER, spec)

        # ---- pass-through when nothing is on
        r = R({"sig": {"kind": "noise"}, "dur": 1, "compare": True})
        check("nothing on: the insert passes audio through untouched", r["diffIn"] < 1e-6 and not r["nan"], f"max diff {r['diffIn']:.2e}")

        # ---- ECHO 1/2 at 120 BPM: repeats every 0.25 s, each 0.6x the one before (x depth on the first)
        imp = {"kind": "impulse", "at": [0.1]}
        r = R({"sig": imp, "dur": 1.2, "slot": {"fx": "ECHO", "beats": 0.5, "depth": 1},
               "ask": [{"name": f"e{k}", "kind": "peak", "a": 0.1 + 0.25 * k - 0.002, "b": 0.1 + 0.25 * k + 0.002} for k in range(1, 4)]
               + [{"name": "between", "kind": "peak", "a": 0.2, "b": 0.33}]})
        ok = abs(r["e1"] - 1) < 0.05 and abs(r["e2"] / r["e1"] - 0.6) < 0.05 and abs(r["e3"] / r["e2"] - 0.6) < 0.05 and r["between"] < 0.01
        check("ECHO 1/2 @120: echoes every 0.25 s, each 0.6x the last, nothing in between", ok and not r["nan"], f"{r['e1']:.3f} {r['e2']:.3f} {r['e3']:.3f} / gap {r['between']:.4f}")

        # ---- tails: switch ECHO off at 0.5 s; echoes of the 0.1 s hit keep going, a hit after OFF isn't echoed
        r = R({"sig": {"kind": "impulse", "at": [0.1, 0.6]}, "dur": 1.6, "slot": {"fx": "ECHO", "beats": 0.5, "depth": 1}, "offAt": 0.5,
               "ask": [{"name": "tail", "kind": "peak", "a": 0.848, "b": 0.852}, {"name": "newEcho", "kind": "peak", "a": 0.848 - 0.0, "b": 0.852}]
               + [{"name": "after", "kind": "peak", "a": 0.6 + 0.25 * 3 - 0.002, "b": 0.6 + 0.25 * 3 + 0.002}]})
        check("ECHO off: earlier echoes ring out (0.85 s still there)", r["tail"] > 0.05, f"tail {r['tail']:.3f}")
        r2 = R({"sig": {"kind": "impulse", "at": [0.7]}, "dur": 1.4, "slot": {"fx": "ECHO", "beats": 0.5, "depth": 1}, "offAt": 0.5,
                "ask": [{"name": "e", "kind": "peak", "a": 0.948, "b": 0.952}]})
        check("...and a hit after OFF isn't echoed", r2["e"] < 0.001, f"{r2['e']:.4f}")

        # ---- PING PONG: echoes alternate sides (left first, then right)
        r = R({"sig": {"kind": "impulse", "at": [0.1]}, "dur": 1.0, "slot": {"fx": "PING PONG", "beats": 0.5, "depth": 1},
               "ask": [{"name": "l1", "kind": "peak", "ch": 0, "a": 0.348, "b": 0.352}, {"name": "r1", "kind": "peak", "ch": 1, "a": 0.348, "b": 0.352},
                       {"name": "l2", "kind": "peak", "ch": 0, "a": 0.598, "b": 0.602}, {"name": "r2", "kind": "peak", "ch": 1, "a": 0.598, "b": 0.602}]})
        check("PING PONG: first echo left, second right", r["l1"] > 0.3 and r["r1"] < 0.01 and r["r2"] > 0.1 and r["l2"] < 0.01, json.dumps({k: round(r[k], 3) for k in ("l1", "r1", "l2", "r2")}))

        # ---- REVERB: an impulse leaves a decaying tail; it rings out after OFF and ends
        r = R({"sig": {"kind": "impulse", "at": [0.1]}, "dur": 3.0, "slot": {"fx": "REVERB", "beats": 1, "depth": 1}, "offAt": 0.2,
               "ask": [{"name": "early", "kind": "rms", "a": 0.15, "b": 0.4}, {"name": "late", "kind": "rms", "a": 1.0, "b": 1.3}, {"name": "end", "kind": "rms", "a": 2.7, "b": 3.0}]})
        check("REVERB: a decaying tail that rings out after OFF", r["early"] > 1e-3 and r["late"] < r["early"] * 0.5 and r["end"] < r["early"] * 0.05 and not r["nan"],
              f"{r['early']:.4f} -> {r['late']:.4f} -> {r['end']:.5f}")

        # ---- TRANS 1/4 at 120 BPM on a tone: open for 1/16 s, shut for 1/16 s, starting on the beat
        r = R({"sig": {"kind": "tone", "f": 1000}, "dur": 1.0, "slot": {"fx": "TRANS", "beats": 0.25, "depth": 1},
               "ask": [{"name": "open", "kind": "rms", "a": 0.505, "b": 0.56}, {"name": "shut", "kind": "rms", "a": 0.57, "b": 0.62}, {"name": "open2", "kind": "rms", "a": 0.63, "b": 0.685}]})
        check("TRANS 1/4 @120: open on the beat, shut on the off-step, open again", r["open"] > 0.3 and r["shut"] < 0.02 and r["open2"] > 0.3,
              f"open {r['open']:.3f} shut {r['shut']:.4f} open {r['open2']:.3f}")

        # ---- ROLL 1/2 at 120 BPM: on at 0.6 s, the output repeats a 0.25 s slice that started on the grid (0.5 s)
        r = R({"sig": {"kind": "ramp"}, "dur": 1.6, "slot": {"fx": "ROLL", "beats": 0.5, "depth": 1}, "onAt": 0.6, "period": {"p": 0.25, "a": 0.8, "b": 1.2},
               "ask": [{"name": "o", "kind": "at", "t": 1.0}, {"name": "o2", "kind": "at", "t": 0.75}]})
        # the ramp at 0.5 + x is (0.5 + x) - 0.5 = x; after the roll starts, out(t) = in(0.5 + ((t - 0.5) mod 0.25))
        check("ROLL 1/2 @120: repeats the grid slice (0.5-0.75 s) every 0.25 s", r["periodDiff"] < 0.01 and abs(r["o"] - 0.0) < 0.01 and abs(r["o2"] - 0.0) < 0.01 and r["periodPeak"] > 0.2,
              f"repeat diff {r['periodDiff']:.4f}, out(1.0) {r['o']:.3f}")

        # ---- HPF / LPF
        hp = R({"sig": {"kind": "tone", "f": 100}, "dur": 0.6, "slot": {"fx": "HPF", "depth": 0.8}, "ask": [{"name": "x", "kind": "rms", "a": 0.3, "b": 0.6}]})
        lp = R({"sig": {"kind": "tone", "f": 8000}, "dur": 0.6, "slot": {"fx": "LPF", "depth": 0.8}, "ask": [{"name": "x", "kind": "rms", "a": 0.3, "b": 0.6}]})
        keep = R({"sig": {"kind": "tone", "f": 8000}, "dur": 0.6, "slot": {"fx": "HPF", "depth": 0.8}, "ask": [{"name": "x", "kind": "rms", "a": 0.3, "b": 0.6}]})
        check("HPF cuts a 100 Hz tone, keeps 8 kHz; LPF cuts 8 kHz", hp["x"] < 0.02 and lp["x"] < 0.02 and keep["x"] > 0.3, f"hp100 {hp['x']:.4f} lp8k {lp['x']:.4f} hp8k {keep['x']:.3f}")

        # ---- FILTER: an LFO sweep (4 beats = 2 s at 120): an 8 kHz tone is cut at mid-cycle, open at the cycle start
        r = R({"sig": {"kind": "tone", "f": 8000}, "dur": 2.4, "slot": {"fx": "FILTER", "beats": 4, "depth": 1},
               "ask": [{"name": "open", "kind": "rms", "a": 0.02, "b": 0.12}, {"name": "dip", "kind": "rms", "a": 0.95, "b": 1.05}]})
        check("FILTER sweeps with the beat (open at the cycle start, closed mid-cycle)", r["open"] > 0.25 and r["dip"] < 0.05, f"open {r['open']:.3f} dip {r['dip']:.4f}")

        # ---- FLANGER changes the sound but keeps the level sensible
        r = R({"sig": {"kind": "noise"}, "dur": 1.0, "slot": {"fx": "FLANGER", "beats": 4, "depth": 0.8}, "compare": True, "ask": [{"name": "x", "kind": "rms", "a": 0.2, "b": 1.0}]})
        check("FLANGER: changes the sound, level stays in range", r["diffIn"] > 0.05 and 0.1 < r["x"] < 0.6 and not r["nan"], f"diff {r['diffIn']:.3f} rms {r['x']:.3f}")

        # ---- a deck's pad slot and the beat slot together, and CPU: ECHO + REVERB on 5 inserts
        cost = page.evaluate("""async () => {
          const sr = 44100, n = sr * 10, off = new OfflineAudioContext(2, n, sr);
          await off.audioWorklet.addModule(URL.createObjectURL(new Blob([cratebox.WORKLET], { type: 'text/javascript' })));
          const osc = off.createOscillator(); osc.frequency.value = 220; osc.start();
          for (let k = 0; k < 5; k++) {
            const nd = new AudioWorkletNode(off, 'fx-unit', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2] });
            nd.port.postMessage({ t: 'clock', t0: 0, beat0: 0, bps: 2, spb: 0.5 });
            nd.port.postMessage({ t: 'slot', slot: 'beat', fx: 'REVERB', beats: 1, depth: 0.6, on: true });
            nd.port.postMessage({ t: 'slot', slot: 'pad', fx: 'ECHO', beats: 0.5, depth: 0.6, on: true });
            osc.connect(nd); nd.connect(off.destination);
          }
          await new Promise((r) => setTimeout(r, 60));
          const t0 = performance.now(); await off.startRendering(); return performance.now() - t0; }""")
        check("CPU: reverb + echo on all 5 inserts at once renders far faster than real time", cost < 2500, f"10 s of audio in {cost:.0f} ms ({10000 / cost:.0f}x real time)")

        # ---- live: the controls
        page.click("#startBtn")
        page.wait_for_function("window.cratebox && cratebox.A.ctx")
        load_all(page, 2)
        sent = []
        page.evaluate("window.__sent = []; cratebox.MIDI.outputs = [{ send(b) { window.__sent.push(Array.from(b)); } }]")
        st = lambda: page.evaluate("({ fx: cratebox.FX.beat.fx, beat: cratebox.FX.beat.beats[cratebox.FX.beat.fx], ch: cratebox.FX.beat.ch, on: cratebox.FX.beat.on, depth: cratebox.FX.beat.depth, label: document.querySelector('.bfxsel').textContent, beatTxt: document.querySelector('.bfxbeat').textContent })")
        page.click(".bfxsel")
        s1 = st()
        page.click(".bfxsel", button="right")
        s2 = st()
        check("FX select (screen): next / previous", s1["fx"] == "DELAY" and s1["label"] == "DELAY" and s2["fx"] == "ECHO", f"{s1['fx']} / {s2['fx']}")
        page.click(".bfxb >> nth=1")
        check("BEAT ▶: 1/2 -> 3/4 for ECHO, shown", st()["beat"] == 0.75 and st()["beatTxt"] == "3/4", str(st()))
        page.click(".bfxb >> nth=0")
        midi = lambda *bs: page.evaluate(f"cratebox.midiIn({json.dumps(list(bs))})")
        midi(0x94, 0x63, 0x7F); midi(0x94, 0x63, 0x00)
        a = st()
        midi(0x94, 0x4B, 0x7F); midi(0x94, 0x4B, 0x00)
        b2 = st()
        check("FLX4 FX SELECT (94 63) and BEAT ▶ (94 4B)", a["fx"] == "DELAY" and b2["beat"] == 1, f"{a['fx']} {b2['beat']}")
        midi(0x94, 0x64, 0x7F); midi(0x94, 0x64, 0x00)
        check("FLX4 SHIFT+FX SELECT (94 64): previous effect", st()["fx"] == "ECHO")
        # CH SELECT lever: CH2 (95 11 7F), then to MASTER (95 11 00), then CH1 (94 10 7F)
        midi(0x95, 0x11, 0x7F); c2 = st()["ch"]
        midi(0x95, 0x11, 0x00); cm = st()["ch"]
        midi(0x94, 0x10, 0x7F); c1 = st()["ch"]
        check("FLX4 CH SELECT lever: CH2, MASTER (neither), CH1", c2 == 1 and cm == "M" and c1 == 0, f"{c2} {cm} {c1}")
        midi(0xB4, 0x02, 0x40)
        dep = st()["depth"]
        midi(0x94, 0x47, 0x7F); midi(0x94, 0x47, 0x00)
        page.wait_for_timeout(120)
        on = st()["on"]
        led = page.evaluate("(() => { const m = __sent.filter(x => x[0] === 0x94 && x[1] === 0x47); return m.length ? m[m.length - 1][2] : -1; })()")
        lit = page.evaluate("document.querySelector('.bfxon').classList.contains('lit')")
        check("FLX4 LEVEL/DEPTH (B4 02) and FX ON (94 47): on, FX ON lit on screen and LED", abs(dep - 0x40 / 127) < 0.01 and on and lit and led > 0, f"depth {dep:.3f} on {on} lit {lit} led {led}")
        # on a playing deck: finite, and different from the dry signal
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.wait_for_timeout(1200)
        live = page.evaluate("""new Promise(res => { const A = cratebox.A, a = A.ctx.createAnalyser(), dry = A.ctx.createAnalyser(); a.fftSize = dry.fftSize = 4096;
          A.decks[0].fx.connect(a); A.decks[0].hp.connect(dry);
          setTimeout(() => { const x = new Float32Array(4096), y = new Float32Array(4096); a.getFloatTimeDomainData(x); dry.getFloatTimeDomainData(y);
            let nan = false, d = 0, pk = 0; for (let i = 0; i < 4096; i++) { if (!isFinite(x[i])) nan = true; d = Math.max(d, Math.abs(x[i] - y[i])); pk = Math.max(pk, Math.abs(x[i])); } res({ nan, d, pk }); }, 400); })""")
        check("live: ECHO on a playing deck changes the sound, stays finite", not live["nan"] and live["d"] > 0.01 and live["pk"] < 4, str(live))
        midi(0x94, 0x43, 0x7F); midi(0x94, 0x43, 0x00)
        check("FLX4 SHIFT+FX ON (94 43): off", not st()["on"])

        # ---- PAD FX: screen
        page.click('.deck[data-i="0"] .modes button >> nth=3')
        labels = page.evaluate("[...document.querySelectorAll('.deck[data-i=\"0\"] .pad')].map(b => b.textContent)")
        check("PAD FX mode: pads show their effects", labels[0] == "ECHO 1/2" and labels[2] == "VERB" and labels[3] == "ROLL 1/4" and labels[6] == "HPF", str(labels))
        pad = page.locator('.deck[data-i="0"] .pad >> nth=3')
        bx = pad.bounding_box()
        page.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
        page.mouse.down()
        page.wait_for_timeout(150)
        held = page.evaluate("({ pad: cratebox.FX.pad[0], cls: document.querySelectorAll('.deck[data-i=\"0\"] .pad')[3].className })")
        page.mouse.up()
        page.wait_for_timeout(100)
        rel = page.evaluate("cratebox.FX.pad[0]")
        check("PAD FX: hold pad 4 = ROLL 1/4 on (lit), let go = off", held["pad"] == {"p": 3, "bank": "padfx"} and "fxon" in held["cls"] and rel is None, f"{held} / {rel}")
        page.click('.deck[data-i="0"] .modes button >> nth=3')
        labels2 = page.evaluate("[...document.querySelectorAll('.deck[data-i=\"0\"] .pad')].map(b => b.textContent)")
        btn = page.inner_text('.deck[data-i="0"] .modes button >> nth=3')
        check("PAD FX pressed again: bank 2", labels2[0] == "PING 1/2" and "FX" in btn and "2" in btn, f"{labels2[:3]} {btn}")
        # ---- PAD FX: FLX4 (mode button 90 1E, pad 3 in PAD FX1 = 97 12), LED while held
        midi(0x90, 0x1E, 0x7F); midi(0x90, 0x1E, 0x00)
        page.evaluate("window.__sent = []")
        midi(0x97, 0x12, 0x7F)
        page.wait_for_timeout(150)
        h1 = page.evaluate("({ pad: cratebox.FX.pad[0], mode: cratebox.decks[0].padMode, led: (() => { const m = __sent.filter(x => x[0] === 0x97 && x[1] === 0x12); return m.length ? m[m.length - 1][2] : -1; })() })")
        midi(0x97, 0x12, 0x00)
        page.wait_for_timeout(150)
        h2 = page.evaluate("({ pad: cratebox.FX.pad[0], led: (() => { const m = __sent.filter(x => x[0] === 0x97 && x[1] === 0x12); return m.length ? m[m.length - 1][2] : -1; })() })")
        check("FLX4 PAD FX1 pad 3 (97 12): REVERB held while pressed, pad LED on, then off", h1["mode"] == "padfx" and h1["pad"] == {"p": 2, "bank": "padfx"} and h1["led"] > 0 and h2["pad"] is None and h2["led"] == 0, f"{h1} {h2}")
        page.evaluate("cratebox.decks[0].togglePlay()")
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
