"""KEY SHIFT: pads (on screen and the FLX4's KEY SHIFT pads) move the key and leave the tempo alone. Headless Chromium.

    python tests/test_keyshift.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402
import test_playlists as P  # noqa: E402

# a 20 s, 440 Hz tone as a WAV file, added to the library like any track
TONE = """(async () => { const sr = 44100, n = sr * 20, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
  const w = (o, s) => { for (let k = 0; k < s.length; k++) v.setUint8(o + k, s.charCodeAt(k)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true);
  for (let k = 0; k < n; k++) v.setInt16(44 + k * 2, Math.round(Math.sin(2 * Math.PI * 440 * k / sr) * 12000), true);
  await cratebox.addFiles([{ file: new File([buf], 'Tone - A440.wav', { lastModified: 1 }), rel: 'music/Tone - A440.wav' }]); })()"""
# the loudest frequency in deck 1's output (an FFT peak, refined between bins)
PEAK = """(async () => { const a = cratebox.A.decks[0].meterL; a.fftSize = 16384; const f = new Float32Array(a.frequencyBinCount);
  await new Promise(r => setTimeout(r, 400)); a.getFloatFrequencyData(f);
  let k = 1; for (let j = 2; j < f.length - 1; j++) if (f[j] > f[k]) k = j;
  const y0 = f[k - 1], y1 = f[k], y2 = f[k + 1], d = (y0 - y2) / (2 * (y0 - 2 * y1 + y2) || 1);
  return (k + d) * a.context.sampleRate / a.fftSize; })()"""


def main():
    T.PORT = 8673
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CRATEBOX_CHROME"]} if os.environ.get("CRATEBOX_CHROME") else {}), args=["--autoplay-policy=no-user-gesture-required"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        P.start(page)
        page.wait_for_function("cratebox.lib.tracks.length === 4 && cratebox.lib.tracks.every(t => t.bpm)", timeout=120000)
        page.evaluate("cratebox.decks[0].load(cratebox.lib.tracks.find(t => t.title.endsWith('126')))")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].ana", timeout=60000)
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.wait_for_timeout(800)
        key0 = page.evaluate("cratebox.camelot(cratebox.decks[0].keyNow()).label")

        # on screen: KEY pad mode, pad A = +1 ... the test goes an octave up with the controller action instead
        page.click('.deck[data-i="0"] .modes button:nth-child(5)')
        labels = page.evaluate("[...document.querySelectorAll('.deck[data-i=\"0\"] .pad')].map(b => b.textContent)")
        check("KEY SHIFT pad mode: +1..+4 on top, −1..−4 below", labels == ["+1", "+2", "+3", "+4", "−1", "−2", "−3", "−4"], str(labels))
        page.click('.deck[data-i="0"] .pad >> nth=1')
        page.wait_for_timeout(200)
        st = page.evaluate("({ ks: cratebox.decks[0].keyShift, key: cratebox.camelot(cratebox.decks[0].keyNow()).label, tag: document.querySelector('.deck[data-i=\"0\"] .keytag').textContent, lit: document.querySelector('.deck[data-i=\"0\"] .pad:nth-child(2)').classList.contains('on') })")
        check("pad +2: key two semitones up (Camelot +2 steps), the tag shows it, the pad is lit", st["ks"] == 2 and st["key"] != key0 and "+2" in st["tag"] and st["lit"], f"{key0} -> {st}")
        page.click('.deck[data-i="0"] .pad >> nth=1')
        check("the lit pad again: back to the original key", page.evaluate("cratebox.decks[0].keyShift") == 0)

        # FLX4: SHIFT + SAMPLER (KEY SHIFT mode), then the KEY SHIFT pads (0x70-0x77 on the pad channel)
        page.evaluate("cratebox.useProfile('ddj-flx4')")
        page.evaluate("cratebox.midiIn([0x90, 0x6f, 0x7f]); cratebox.midiIn([0x90, 0x6f, 0x00])")
        check("FLX4 KEY SHIFT mode button switches deck 1's pads", page.evaluate("cratebox.decks[0].padMode") == "keyshift")
        page.evaluate("cratebox.midiIn([0x97, 0x73, 0x7f]); cratebox.midiIn([0x97, 0x73, 0x00])")
        check("FLX4 KEY SHIFT pad 4: +4", page.evaluate("cratebox.decks[0].keyShift") == 4)
        page.evaluate("cratebox.midiIn([0x98, 0x70, 0x7f])")
        check("SHIFT + a KEY SHIFT pad: reset", page.evaluate("cratebox.decks[0].keyShift") == 0)

        # the sound, on a 440 Hz tone: +7 = 659 Hz, +12 = 880, -12 = 220; the playhead keeps its speed
        page.evaluate("cratebox.decks[0].togglePlay()")
        page.evaluate(TONE)
        page.wait_for_function("cratebox.lib.tracks.some(t => t.title === 'A440')", timeout=60000)
        page.evaluate("cratebox.decks[0].load(cratebox.lib.tracks.find(t => t.title === 'A440'))")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].title !== '' && cratebox.decks[0].track.title === 'A440'", timeout=60000)
        page.evaluate("cratebox.decks[0].togglePlay()")
        for ks, want in ((0, 440), (7, 440 * 2 ** (7 / 12)), (12, 880), (-12, 220), (-5, 440 * 2 ** (-5 / 12))):
            page.evaluate(f"cratebox.decks[0].setKeyShift({ks})")
            t0 = page.evaluate("cratebox.decks[0].now()")
            f = page.evaluate(PEAK)
            t1 = page.evaluate("cratebox.decks[0].now()")
            check(f"KEY SHIFT {ks:+d}: the tone plays at {want:.0f} Hz", abs(f / want - 1) < 0.01, f"{f:.1f} Hz")
        page.evaluate("cratebox.decks[0].setMT(false); cratebox.decks[0].setPitch(1); cratebox.decks[0].setKeyShift(-12)")
        f = page.evaluate(PEAK)
        check("master tempo off, +6% tempo and −12: the tempo's own pitch rise stays on top (233 Hz)", abs(f / (220 * 1.06) - 1) < 0.01, f"{f:.1f} Hz")
        page.evaluate("cratebox.decks[0].setPitch(0); cratebox.decks[0].setMT(true)")
        sp = page.evaluate("(async () => { const d = cratebox.decks[0]; d.setKeyShift(12); const a = d.now(), t = performance.now(); await new Promise(r => setTimeout(r, 1000)); return (d.now() - a) / ((performance.now() - t) / 1000); })()")
        check("+12 keeps the tempo: the playhead still moves at 1x", abs(sp - 1) < 0.05, f"{sp:.3f}x")
        page.evaluate("cratebox.decks[0].setKeyShift(0)")
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
