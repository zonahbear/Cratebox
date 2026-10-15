"""End-to-end test in headless Chromium: analysis accuracy, playback, FLX4 MIDI input, LEDs, sync, loops, cues.

    python tests/test_cratebox.py [screenshot.png]
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8622
EXPECT = {"House Groove 126": (126, 0.37), "Halftime Wobble 140": (140, 0.05), "Rollers 174": (174, 0.21), "Dusty 92": (92, 0.5)}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def main():
    shot = sys.argv[1] if len(sys.argv) > 1 else None
    srv = serve()
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CRATEBOX_CHROME"]} if os.environ.get("CRATEBOX_CHROME") else {}),
                              args=["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        # fonts.googleapis.com is blocked in this sandbox, and there's no favicon: ignore those two
        page.on("console", lambda m: m.type == "error" and "ERR_TUNNEL" not in m.text and "404" not in m.text and errors.append(m.text))
        page.goto(f"http://127.0.0.1:{PORT}/cratebox.html")
        page.click("#startBtn")
        page.wait_for_function("window.cratebox.A.ctx && window.cratebox.A.decks.length === 2")
        # pretend an FLX4 output is attached so LED messages are generated and logged
        page.evaluate("cratebox.MIDI.outputs = [{ send() {} }]")
        names = sorted(os.listdir(os.path.join(ROOT, "tests", "music")))
        page.evaluate("""async (names) => {
            const files = [];
            for (const n of names) {
                const blob = await (await fetch('tests/music/' + encodeURIComponent(n))).blob();
                files.push({ file: new File([blob], n, { lastModified: 1 }), rel: 'music/' + n });
            }
            await cratebox.addFiles(files);
        }""", names)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm != null)", timeout=120000)
        tracks = page.evaluate("cratebox.lib.tracks.map(t => ({title: t.title, artist: t.artist, bpm: t.bpm, first: t.firstBeat, dur: t.duration, key: cratebox.camelot(t.key)?.label}))")
        KEYS = {"126": "8A", "140": "4A", "174": "7A", "92": "5B"}
        ph = page.evaluate("(() => { const t = cratebox.lib.tracks.find(t => t.title.endsWith('126')); return t.phrases.map(p => [p.label, Math.round((p.start - t.firstBeat) / (240 / t.bpm)), p.bars]); })()")
        want_ph = [["Intro", 0], ["Drop", 8], ["Breakdown", 20], ["Drop", 32]]
        check("phrase analysis finds intro, drop, breakdown, drop", [[p[0], p[1]] for p in ph] == want_ph, str(ph))
        exact = 0
        for t in tracks:
            want = next(v for k, v in KEYS.items() if t["title"].endswith(k))
            exact += t["key"] == want
            # i-VI-III-VII uses exactly the relative major's notes, so 7A vs 7B is a coin-flip; the number must be right
            check(f"key {t['title']}: Camelot {want[:-1]}", t["key"] and t["key"][:-1] == want[:-1], f"got {t['key']}, true key {want}")
        check("key letter (minor/major) right on at least 3 of 4", exact >= 3, f"{exact}/4 exact")
        for t in tracks:
            key = next(k for k in EXPECT if k in t["title"])
            bpm, off = EXPECT[key]
            spb = 60 / bpm
            phase_err = min(abs(t["first"] - off) % spb, spb - abs(t["first"] - off) % spb)
            check(f"BPM {key}", abs(t["bpm"] - bpm) < 0.05, f"got {t['bpm']:.2f}, first beat {t['first']:.3f}s vs {off}s, phase error {phase_err*1000:.0f} ms")
            check(f"beat grid {key}", phase_err < 0.02)
        check("tags parsed from file names", any(t["artist"] == "Bass Lab" and t["title"] == "Halftime Wobble 140" for t in tracks))

        midi = lambda *bs: page.evaluate(f"cratebox.midiIn({json.dumps(list(bs))})")
        # sort by BPM so the order is known, then browse + LOAD deck 1 and deck 2
        page.evaluate("cratebox.lib.sort = 'bpm'; cratebox.lib.dir = 1; cratebox.applyView()")
        midi(0xB6, 0x40, 0x01)                    # browse knob one click clockwise -> row 2 (126)
        midi(0x96, 0x46, 0x7F)                    # LOAD deck 1
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].ana", timeout=30000)
        midi(0xB6, 0x40, 0x01)                    # -> row 3 (140)
        midi(0x96, 0x47, 0x7F)                    # LOAD deck 2
        page.wait_for_function("cratebox.decks[1].loaded && cratebox.decks[1].ana", timeout=30000)
        st = page.evaluate("cratebox.decks.map(d => ({t: d.track.title, bpm: d.bpm, cue: d.cue, first: d.ana.firstBeat}))")
        check("browse knob + LOAD buttons load the right tracks", "126" in st[0]["t"] and "140" in st[1]["t"], f"{st[0]['t']} / {st[1]['t']}")
        check("cue point defaults to the first beat", abs(st[0]["cue"] - st[0]["first"]) < 0.01)

        # faders and knobs (14-bit: MSB then LSB)
        midi(0xB0, 0x13, 0x7F); midi(0xB0, 0x33, 0x7F)      # channel 1 fader up
        midi(0xB1, 0x13, 0x7F); midi(0xB1, 0x33, 0x7F)
        midi(0xB6, 0x1F, 0x00); midi(0xB6, 0x3F, 0x00)      # crossfader hard left
        midi(0xB0, 0x0F, 0x00); midi(0xB0, 0x2F, 0x00)      # deck 1 LOW fully left = kill
        page.wait_for_timeout(100)
        g = page.evaluate("({f: cratebox.A.decks[0].fader.gain.value, x2: cratebox.A.decks[1].xf.gain.value, low: cratebox.A.decks[0].lowG.gain.value, M: cratebox.M})")
        check("channel fader, crossfader and EQ kill respond", g["f"] > 0.99 and g["x2"] < 0.01 and g["low"] < 0.001, json.dumps({k: g[k] for k in ('f', 'x2', 'low')}))
        midi(0xB0, 0x0F, 0x40); midi(0xB0, 0x2F, 0x00)      # LOW back to centre
        midi(0xB6, 0x1F, 0x40); midi(0xB6, 0x3F, 0x00)      # crossfader centre

        # play deck 1 and check it moves at the right speed + makes sound
        midi(0x90, 0x0B, 0x7F)
        page.wait_for_timeout(1500)
        s = page.evaluate("({now: cratebox.decks[0].now(), cue: cratebox.decks[0].cue, playing: cratebox.decks[0].playing})")
        check("PLAY starts deck 1", s["playing"] and 1.2 < s["now"] - s["cue"] < 1.8, f"advanced {s['now'] - s['cue']:.2f}s in 1.5s")
        lv = page.evaluate("""(async () => { let m = 0; const a = cratebox.A.decks[0].meterL, buf = new Float32Array(512);
            for (let k = 0; k < 30; k++) { a.getFloatTimeDomainData(buf); for (const v of buf) m = Math.max(m, Math.abs(v)); await new Promise(r => setTimeout(r, 20)); }
            return m; })()""")
        check("deck 1 produces audio", lv > 0.3, f"peak {lv:.2f} over 0.6 s")
        log = page.evaluate("cratebox.MIDI.log.map(m => m.join(','))")
        check("PLAY LED lit on the controller", "144,11,127" in log)

        # tempo fader: top = slower (-6%)
        midi(0xB0, 0x00, 0x00); midi(0xB0, 0x20, 0x00)
        r = page.evaluate("cratebox.decks[0].rate()")
        check("tempo fader top = -6%", abs(r - 0.94) < 0.001, f"rate {r:.4f}")
        midi(0xB0, 0x00, 0x40); midi(0xB0, 0x20, 0x00)      # centre
        r = page.evaluate("cratebox.decks[0].rate()")
        check("tempo fader centre = 0%", abs(r - 1) < 0.001)

        # deck 2: play, then SYNC to deck 1
        midi(0x91, 0x0B, 0x7F)
        page.wait_for_timeout(300)
        midi(0x91, 0x58, 0x7F)
        page.wait_for_timeout(2500)
        sy = page.evaluate("""(() => { const [a, b] = cratebox.decks;
            const pa = a.beatAt(a.now()), pb = b.beatAt(b.now());
            let d = (pa - Math.floor(pa)) - (pb - Math.floor(pb)); if (d > 0.5) d -= 1; if (d < -0.5) d += 1;
            return { ea: a.effBpm(), eb: b.effBpm(), phase: d * 60 / a.effBpm(), sync: b.sync }; })()""")
        check("SYNC matches tempo", sy["sync"] and abs(sy["ea"] - sy["eb"]) < 0.01, f"{sy['ea']:.2f} vs {sy['eb']:.2f} BPM")
        check("SYNC aligns beats", abs(sy["phase"]) < 0.012, f"{sy['phase']*1000:.1f} ms apart after 2.5 s")
        midi(0xB0, 0x00, 0x7F); midi(0xB0, 0x20, 0x7F)      # deck 1 tempo to +6%: deck 2 should follow
        page.wait_for_timeout(200)
        px = page.evaluate("[0, 1].map(i => cratebox.lanePps(i, 1000) * cratebox.decks[i].spb)")
        check("synced waveforms show beats at the same spacing", abs(px[0] - px[1]) < 0.05, f"{px[0]:.2f} px vs {px[1]:.2f} px per beat")
        f = page.evaluate("[cratebox.decks[0].effBpm(), cratebox.decks[1].effBpm()]")
        check("synced deck follows the master's tempo fader", abs(f[0] - f[1]) < 0.01 and f[0] > 133, f"{f[0]:.2f} / {f[1]:.2f}")
        midi(0xB0, 0x00, 0x40); midi(0xB0, 0x20, 0x00)

        # hot cues: pad 1 sets, pad 1 again jumps, SHIFT+pad clears
        midi(0x97, 0x00, 0x7F)
        hc = page.evaluate("cratebox.decks[0].hot[0]")
        page.wait_for_timeout(1000)
        midi(0x97, 0x00, 0x7F)
        page.wait_for_timeout(60)
        back = page.evaluate("cratebox.decks[0].now()")
        check("hot cue A set on a beat and recalled", hc is not None and abs(back - hc) < 0.1, f"cue {hc:.3f}s, now {back:.3f}s")
        page.wait_for_timeout(120)
        log = page.evaluate("cratebox.MIDI.log.map(m => m.join(','))")
        check("hot cue pad LED lit", "151,0,127" in log)
        midi(0x98, 0x00, 0x7F)
        check("SHIFT + pad clears the hot cue", page.evaluate("cratebox.decks[0].hot[0]") is None)

        # 4-beat loop via BEAT LOOP pad 5, held for ~3 s
        midi(0x97, 0x64, 0x7F)
        lp = page.evaluate("({a: cratebox.decks[0].loop.a, b: cratebox.decks[0].loop.b, on: cratebox.decks[0].loop.on})")
        page.wait_for_timeout(3000)
        n = page.evaluate("cratebox.decks[0].now()")
        check("beat loop pad makes a 4-beat loop", lp["on"] and abs((lp["b"] - lp["a"]) - 4 * 60 / 126) < 0.002)
        check("loop holds playback inside it", lp["a"] - 0.05 <= n <= lp["b"] + 0.05, f"now {n:.2f}s in [{lp['a']:.2f}, {lp['b']:.2f}]")
        midi(0x90, 0x51, 0x7F)                       # CUE/LOOP CALL left while looping = halve
        half = page.evaluate("cratebox.decks[0].loopBeats()")
        check("CUE/LOOP CALL halves an active loop", abs(half - 2) < 0.01)
        end = page.evaluate("cratebox.decks[0].loop.b")
        midi(0x90, 0x4D, 0x7F)                       # RELOOP/EXIT
        page.wait_for_timeout(1300)
        check("RELOOP/EXIT leaves the loop", not page.evaluate("cratebox.decks[0].loop.on") and page.evaluate("cratebox.decks[0].now()") > end)

        # jog: touch + spin forward while playing = scratch ahead; side = nudge
        before = page.evaluate("cratebox.decks[1].now()")
        midi(0x91, 0x36, 0x7F)
        for _ in range(40):
            midi(0xB1, 0x22, 64 + 20)
        page.wait_for_timeout(250)
        midi(0x91, 0x36, 0x00)
        after = page.evaluate("cratebox.decks[1].now()")
        check("jog scratch moves the track", after - before > 1.0, f"moved {after - before:.2f}s (800 ticks = 2.0s of platter)")
        # backspin: fling backwards and let go; the record keeps spinning back, then the motor brings it round
        page.wait_for_timeout(300)
        midi(0x91, 0x36, 0x7F)
        page.evaluate("""() => new Promise((res) => { let k = 0;      // a fling: ticks keep coming right up to the release
            const id = setInterval(() => { cratebox.midiIn([0xB1, 0x22, 64 - 12]);
              if (++k === 40) { clearInterval(id); cratebox.midiIn([0x91, 0x36, 0x00]); res(); } }, 2); })""")
        t0 = page.evaluate("cratebox.decks[1].now()")
        for _ in range(10):
            midi(0xB1, 0x21, 64 - 5)      # the physical platter still turning after release: ignored
        page.wait_for_timeout(400)
        bs = page.evaluate("({now: cratebox.decks[1].now(), coast: cratebox.decks[1].coasting, speed: cratebox.decks[1].speed})")
        check("backspin keeps spinning backwards after release", bs["now"] < t0 - 0.3 and bs["coast"] and bs["speed"] < 0,
              f"moved {bs['now'] - t0:.2f}s in 0.4s, speed {bs['speed']:.2f}x")
        page.wait_for_timeout(3200)
        bs2 = page.evaluate("({coast: cratebox.decks[1].coasting, speed: cratebox.decks[1].speed, playing: cratebox.decks[1].playing})")
        check("after the backspin the motor brings it back to play speed", not bs2["coast"] and bs2["speed"] > 0.5 and bs2["playing"], str(bs2))

        # CUE while playing: stop and return to the cue point
        midi(0x90, 0x0C, 0x7F); midi(0x90, 0x0C, 0x00)
        page.wait_for_timeout(100)
        c = page.evaluate("({p: cratebox.decks[0].playing, now: cratebox.decks[0].now(), cue: cratebox.decks[0].cue})")
        check("CUE while playing returns to the cue point", not c["p"] and abs(c["now"] - c["cue"]) < 0.02)

        # headphone cue button + LED, VU meter messages
        midi(0x90, 0x54, 0x7F)
        page.wait_for_timeout(120)
        log = page.evaluate("cratebox.MIDI.log.map(m => m.join(','))")
        check("headphone CUE toggles with LED", page.evaluate("cratebox.M.pfl[0]") and "144,84,127" in log)
        check("VU meter levels sent to the FLX4", any(m.startswith("177,2,") and int(m.split(",")[2]) > 40 for m in log))

        # headphone routing on this (2-channel) output: Auto falls back, the FLX4 jack is refused, Test cue stays out of master
        midi(0x90, 0x0B, 0x7F) if page.evaluate("cratebox.decks[0].playing") else None
        midi(0x91, 0x0B, 0x7F) if page.evaluate("cratebox.decks[1].playing") else None
        page.select_option("#hpSel", "quad")
        hp = page.evaluate("({out: cratebox.A.out, pill: document.querySelector('#chPill').textContent, st: document.querySelector('#status').textContent})")
        check("FLX4-jack mode refused on a 2-channel output, with an explanation", hp["out"] == "off" and "only 2 channels" in hp["st"], hp["st"][:90])
        page.select_option("#hpSel", "device")
        dev = page.evaluate("""(async () => {
            const A = cratebox.A, an = A.ctx.createAnalyser(); an.fftSize = 2048;
            const src = A.ctx.createMediaStreamSource(A.hpStream.stream); src.connect(an);
            const mst = A.ctx.createAnalyser(); mst.fftSize = 2048; A.limiter.connect(mst);
            document.querySelector('#cueTest').click();
            let hpPeak = 0, mPeak = 0; const buf = new Float32Array(2048);
            for (let k = 0; k < 40; k++) {
                await new Promise(r => setTimeout(r, 20));
                an.getFloatTimeDomainData(buf); for (const v of buf) hpPeak = Math.max(hpPeak, Math.abs(v));
                mst.getFloatTimeDomainData(buf); for (const v of buf) mPeak = Math.max(mPeak, Math.abs(v));
            }
            return { hpPeak, mPeak, playing: !!A.hpAudio && !!A.hpAudio.srcObject };
        })()""")
        check("'Another device' mode carries the cue mix to a second output", dev["playing"] and dev["hpPeak"] > 0.1, f"headphone peak {dev['hpPeak']:.2f}")
        check("Test cue beeps in the headphones only, not the master", dev["mPeak"] < 0.01, f"master peak {dev['mPeak']:.3f}")
        page.select_option("#hpSel", "auto")

        # the real routing code on a 4-channel device (an offline context stands in for the FLX4)
        p4 = b.new_page()
        p4.goto(f"http://127.0.0.1:{PORT}/cratebox.html")
        quadres = p4.evaluate("""(async () => {
            const off = new OfflineAudioContext(4, 22050, 44100);
            // an offline context reports its *current* channel count; a real device reports its hardware
            // channels, so make this one behave like a 4-output FLX4
            Object.defineProperty(off.destination, "maxChannelCount", { value: 4 });
            await cratebox.initAudio(off);
            const A = cratebox.A;
            const ok = cratebox.routeOutput('quad');
            const m = off.createOscillator(); m.frequency.value = 220; m.connect(A.master);
            const c = off.createOscillator(); c.frequency.value = 880; const cg = off.createGain(); cg.gain.value = 0.5;
            c.connect(cg); cg.connect(A.cueBus);
            cratebox.M.headMix = 0; A.hpCue.gain.value = 1; A.hpMaster.gain.value = 0; A.masterLevel.gain.value = 0.5;
            m.start(); c.start();
            const buf = await off.startRendering();
            const rms = (ch) => { const d = buf.getChannelData(ch).subarray(4410); let s = 0; for (const v of d) s += v * v; return Math.sqrt(s / d.length); };
            const freq = (ch) => { const d = buf.getChannelData(ch).subarray(4410); let z = 0; for (let i = 1; i < d.length; i++) if (d[i - 1] < 0 && d[i] >= 0) z++; return z / (d.length / 44100); };
            return { ok, rms: [0, 1, 2, 3].map(rms), freq: [0, 1, 2, 3].map(freq) };
        })()""")
        r, f = quadres["rms"], quadres["freq"]
        check("4-channel output: master on 1-2, headphone cue on 3-4", quadres["ok"] and r[0] > 0.1 and r[1] > 0.1 and r[2] > 0.1 and r[3] > 0.1
              and abs(f[0] - 220) < 15 and abs(f[1] - 220) < 15 and abs(f[2] - 880) < 30 and abs(f[3] - 880) < 30,
              f"channel tones {[round(x) for x in f]} Hz, levels {[round(x, 2) for x in r]}")
        p4.close()

        # master tempo: render the deck worklet offline with a tone that changes from 440 to 660 Hz at 1.0 s
        mt = page.evaluate("""(async () => {
            const sr = 44100, out = {};
            const url = URL.createObjectURL(new Blob([cratebox.WORKLET], { type: "application/javascript" }));
            const run = async (rate, mtOn, f1, f2, bass) => {
                const off = new OfflineAudioContext(2, sr * 1.6, sr);
                await off.audioWorklet.addModule(url);
                const node = new AudioWorkletNode(off, "deck-player", { outputChannelCount: [2] });
                node.connect(off.destination);
                const n = sr * 4, L = new Float32Array(n);
                let ph = 0;
                for (let i = 0; i < n; i++) { ph += 2 * Math.PI * (i < sr ? f1 : f2) / sr; L[i] = 0.4 * Math.sin(ph) + (bass ? 0.4 * Math.sin(2 * Math.PI * 55 * i / sr) : 0); }
                const R = L.slice();
                node.port.postMessage({ t: "load", L, R, mt: mtOn });
                node.port.postMessage({ t: "rate", v: rate });
                node.port.postMessage({ t: "play", v: true });
                // offline rendering outruns message delivery: pause after the first block so the worklet gets them
                off.suspend(128 / sr).then(() => setTimeout(() => off.resume(), 150));
                const b = await off.startRendering();
                return b.getChannelData(0);
            };
            const freq = (d, a, b) => { let z = 0, lo = Math.round(a * sr), hi = Math.round(b * sr), first = -1, last = -1;
                for (let i = lo + 1; i < hi; i++) if (d[i - 1] < 0 && d[i] >= 0) { const x = i - d[i] / (d[i] - d[i - 1]); if (first < 0) first = x; last = x; z++; }
                return (z - 1) / ((last - first) / sr); };
            const env = (d, a, b) => { const r = []; for (let t = a; t < b; t += 0.01) { let s = 0; const i0 = Math.round(t * sr); for (let i = i0; i < i0 + 441; i++) s += d[i] * d[i]; r.push(Math.sqrt(s / 441)); } return r; };
            let d = await run(1.08, true, 440, 660);
            out.mtBefore = freq(d, 0.70, 0.85); out.mtAfter = freq(d, 0.98, 1.12);
            const e = env(d, 0.2, 0.8); out.flat = Math.min(...e) / Math.max(...e);
            d = await run(1.08, false, 440, 660);
            out.vinyl = freq(d, 0.30, 0.80);
            d = await run(0.92, true, 440, 440, true);
            const e2 = env(d, 0.2, 1.4); out.flatBass = Math.min(...e2) / Math.max(...e2);
            d = await run(1.0, true, 440, 440);
            out.unity = freq(d, 0.2, 1.4);
            return out;
        })()""")
        check("master tempo keeps the key at +8% (440 Hz stays 440)", abs(mt["mtBefore"] - 440) < 3, f"{mt['mtBefore']:.1f} Hz")
        check("master tempo still plays 8% faster (tone change arrives at 0.93 s, not 1.0 s)", abs(mt["mtAfter"] - 660) < 4, f"{mt['mtAfter']:.1f} Hz after 0.98 s")
        check("master tempo has no warble on a steady tone", mt["flat"] > 0.85 and mt["flatBass"] > 0.6, f"level ratio {mt['flat']:.2f}, with bass {mt['flatBass']:.2f}")
        check("master tempo off = vinyl (+8% raises the pitch)", abs(mt["vinyl"] - 475.2) < 3, f"{mt['vinyl']:.1f} Hz")
        check("master tempo at 0% is transparent", abs(mt["unity"] - 440) < 1, f"{mt['unity']:.2f} Hz")

        quad = page.evaluate("cratebox.A.ctx.destination.maxChannelCount")
        print(f"(info) headless output reports {quad} channels")
        tag = page.evaluate("document.querySelector(\".deck[data-i='0'] .phrasetag\").textContent")
        check("deck shows the current phrase and bar", bool(__import__("re").match(r"^(INTRO|DROP|BREAKDOWN|BUILD|GROOVE|OUTRO) \d+/\d+$", tag)), tag)
        # waveform seeking: click the overview, drag the scrolling waveform, tap it
        page.evaluate("cratebox.decks[1].playing && cratebox.decks[1].togglePlay(); cratebox.decks[1].quant = false")
        page.wait_for_timeout(100)
        ov = page.locator(".deck[data-i='1'] .overview").bounding_box()
        page.mouse.click(ov["x"] + ov["width"] * 0.5, ov["y"] + ov["height"] / 2)
        t_ov = page.evaluate("cratebox.decks[1].now() / cratebox.decks[1].duration")
        check("click on the overview jumps there", abs(t_ov - 0.5) < 0.02, f"at {t_ov:.3f} of the track")
        page.mouse.move(ov["x"] + ov["width"] * 0.5, ov["y"] + 10)
        page.mouse.down(); page.mouse.move(ov["x"] + ov["width"] * 0.25, ov["y"] + 10, steps=5); page.mouse.up()
        t_ov2 = page.evaluate("cratebox.decks[1].now() / cratebox.decks[1].duration")
        check("dragging on the overview scrubs", abs(t_ov2 - 0.25) < 0.02, f"at {t_ov2:.3f}")
        ln = page.locator("#lane1").bounding_box()
        before = page.evaluate("cratebox.decks[1].now()")
        page.mouse.move(ln["x"] + ln["width"] * 0.6, ln["y"] + ln["height"] / 2)
        page.mouse.down(); page.mouse.move(ln["x"] + ln["width"] * 0.6 - 300, ln["y"] + ln["height"] / 2, steps=10); page.mouse.up()
        after = page.evaluate("cratebox.decks[1].now()")
        exp = page.evaluate("300 / (document.querySelector('#lane1').clientWidth / 8 / cratebox.decks[1].rate())")
        check("dragging the scrolling waveform left moves later in the track", abs((after - before) - exp) < 0.15, f"moved {after - before:.2f}s, expected {exp:.2f}s")
        before = page.evaluate("cratebox.decks[1].now()")
        page.mouse.click(ln["x"] + ln["width"] * 0.75, ln["y"] + ln["height"] / 2)
        after = page.evaluate("cratebox.decks[1].now()")
        exp = page.evaluate("(document.querySelector('#lane1').clientWidth * 0.25) / (document.querySelector('#lane1').clientWidth / 8 / cratebox.decks[1].rate())")
        check("tapping the scrolling waveform jumps to that spot", abs((after - before) - exp) < 0.1, f"moved {after - before:.2f}s, expected {exp:.2f}s")
        # while playing with Q on, a jump keeps the beat phase
        page.evaluate("cratebox.decks[1].quant = true; cratebox.decks[1].togglePlay()")
        page.wait_for_timeout(300)
        ph = page.evaluate("""(() => { const d = cratebox.decks[1]; const b0 = d.beatAt(d.now()); d.seekTo(d.now() + 7.3); const b1 = d.beatAt(d.now());
            let x = (b1 - b0) % 1; if (x < 0) x += 1; return Math.min(x, 1 - x); })()""")
        check("with Q on, jumping while playing keeps the beat phase", ph < 0.01, f"phase moved {ph:.3f} beat")
        page.evaluate("cratebox.decks[1].togglePlay()")

        # beat grid editor on deck 1
        page.evaluate("cratebox.decks[0].playing && cratebox.decks[0].togglePlay()")
        page.wait_for_timeout(100)
        page.click(".deck[data-i='0'] .dinfo button:has-text('GRID')")
        g0 = page.evaluate("(() => { const d = cratebox.decks[0]; const t = d.now(); return { t, b: d.beatAt(t), bpm: d.bpm, first: d.ana.firstBeat }; })()")
        page.fill(".deck[data-i='0'] .bpmin", "128")
        page.press(".deck[data-i='0'] .bpmin", "Enter")
        g1 = page.evaluate("(() => { const d = cratebox.decks[0]; return { b: d.beatAt(d.now()), bpm: d.bpm, manual: d.track.gridManual, cell: [...document.querySelectorAll('.trow .num.manual')].length }; })()")
        frac = lambda v: v - __import__("math").floor(v)
        check("typing a BPM sets it and keeps the beat under the playhead", abs(g1["bpm"] - 128) < 1e-6 and abs(frac(g1["b"]) - frac(g0["b"])) < 0.01 and g1["manual"] and g1["cell"] >= 1,
              f"{g0['bpm']} -> {g1['bpm']}, beat phase {frac(g0['b']):.3f} -> {frac(g1['b']):.3f}, marked in library: {g1['cell']}")
        f0 = page.evaluate("cratebox.decks[0].ana.firstBeat")
        page.click(".deck[data-i='0'] .gridbar button:has-text('5ms ▶')")
        f1 = page.evaluate("cratebox.decks[0].ana.firstBeat")
        bar = 4 * 60 / 128
        check("grid nudge slides it 5 ms", abs(((f1 - f0) % bar) - 0.005) < 1e-6, f"{(f1 - f0) * 1000:.2f} ms")
        page.click(".deck[data-i='0'] .gridbar button:has-text('BAR 1 HERE')")
        g2 = page.evaluate("(() => { const d = cratebox.decks[0]; return d.beatAt(d.now()); })()")
        check("BAR 1 HERE puts a bar line on the playhead", abs(g2 - round(g2)) < 1e-3 and round(g2) % 4 == 0, f"playhead at beat {g2:.4f}")
        saved = page.evaluate("""new Promise((res) => { const r = indexedDB.open('cratebox'); r.onsuccess = () => {
            const db = r.result, tx = db.transaction('analysis'), q = tx.objectStore('analysis').get(cratebox.decks[0].track.id);
            q.onsuccess = () => res(q.result); q.onerror = () => res(null); }; r.onerror = () => res(null); })""")
        check("edited grid is saved with the track", bool(saved) and saved.get("gridManual") and abs(saved.get("bpm", 0) - 128) < 1e-6, str({k: saved.get(k) for k in ("bpm", "gridManual", "autoBpm")} if saved else saved))
        tapped = page.evaluate("""new Promise((res) => { let k = 0; const id = setInterval(() => { cratebox.decks[0].tap(); if (++k === 9) { clearInterval(id); res(cratebox.decks[0].bpm); } }, 500); })""")
        check("TAP tempo", abs(tapped - 120) < 1.0, f"9 taps at 500 ms -> {tapped} BPM")
        page.click(".deck[data-i='0'] .gridbar button:has-text('RESET')")
        g3 = page.evaluate("({ bpm: cratebox.decks[0].bpm, first: cratebox.decks[0].ana.firstBeat, manual: cratebox.decks[0].track.gridManual })")
        check("RESET goes back to the analysed grid", abs(g3["bpm"] - g0["bpm"]) < 1e-6 and abs(g3["first"] - g0["first"]) < 1e-6 and not g3["manual"], str(g3))
        page.click(".deck[data-i='0'] .dinfo button:has-text('GRID')")

        # library size: normal, then expanded with SHIFT + BROWSE press
        page.evaluate("document.body.classList.contains('browse') && cratebox.midiIn([0x96, 0x42, 0x7F])")
        h_norm = page.evaluate("document.querySelector('#list').clientHeight")
        if shot:
            page.wait_for_timeout(300)
            page.screenshot(path=shot)
        midi(0x96, 0x42, 0x7F)
        page.wait_for_timeout(100)
        h_big = page.evaluate("document.querySelector('#list').clientHeight")
        fits = page.evaluate("document.documentElement.scrollWidth <= innerWidth && document.querySelector('#library').getBoundingClientRect().bottom <= innerHeight + 1")
        check("SHIFT + BROWSE press expands the library", page.evaluate("document.body.classList.contains('browse')") and h_big > h_norm + 250 and fits,
              f"list {h_norm}px -> {h_big}px at 1440x900")
        if shot:
            page.screenshot(path=shot.replace(".png", "-browse.png"))
        midi(0x96, 0x42, 0x7F)
        check("pressing it again brings the decks back", not page.evaluate("document.body.classList.contains('browse')"))
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
