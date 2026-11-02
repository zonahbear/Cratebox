# Breadcrumbs: Cratebox (web)

## 2026-11-02: web catch-up with the iOS app (branch claude/project-thread-0pjrfq)

Done (one commit each): iOS SYNC rules; 3 decks; Booth top waveforms + HIDE WAVES, WAVE mode + pop-up library,
library grip; phone SCRATCH tab; Settings window (⚙); phone Touch mode; KEY SHIFT pads (new, not on iOS yet);
EJECT; 1440p 4-deck overflow fix.

Tests: run with `CRATEBOX_CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome` in cloud sessions. Run suites
one at a time: in parallel, the timing tests (cratebox, sync, layers, fourdeck, audio_first) fail at random.
New: test_wave.py, test_keyshift.py, test_eject.py.
Failing on main before this branch too: test_phrases (`select_option #lockSel` after Esc closes Settings),
test_playlists (`.rbwarn` also matches #heatSheet).

Next:
- FLX4 KEY SHIFT notes (0x70+p, SHIFT 0x70+p = reset) are inferred; check on hardware (MIDI monitor in Settings).
- Mixxx-derived maps have no key controls: add pitch_up/pitch_down/reset_key rules to tools/mixxx2cratebox.py, or rely on MIDI learn.
- The iOS suite's copy of cratebox.html needs a sync after merge; KEY SHIFT should go to iOS (Swift) too.
- Fix the two old test failures above.

## 2026-11-02 (later): self-review of PR #13
- Keylock grain search with KEY SHIFT read the track through idx() per sample (~20k calls a grain); now copies the
  window once (buf sized for steps up to 4x) and reads the array.
- Library grip: resize + layout checks once per frame (rAF), not per pointer event.
- WAVE pop-up: trackpad wheel deltas add up (one row per 40 px) instead of a row per event.
- WAVE strips: key colour only written when the key changes.
- EJECT: re-checks the decks after waiting for a save (a stick track loaded meanwhile now refuses).
- 4 decks fit at 1280x800 (library min 86 px there) and 1440x900; under ~800 px tall it still scrolls (tallapp).
