# CLAUDE.md: Cratebox (web app)

Read this first; it exists so you don't have to re-parse the repo. Update it when you change structure,
conventions, or finish/start a piece of open work. Keep it under ~150 lines.

## What this repo is

Cratebox, a browser DJ app for the Pioneer DDJ-FLX4 (and other controllers via Mixxx-derived maps): 2 or 4 decks,
keylock, sync, beat grids, keys, phrases, Beat/Pad FX, playlists, rekordbox USB + XML, recording. Plain HTML/JS,
no build step, no framework. Runs from `http://localhost` on desktop (`start_cratebox.py`) and from GitHub Pages
(`main`, repo root) on phones as an installable PWA. Version 1.1.1.

**This repo is the source of truth for `cratebox.html`** and the other web files; the iOS suite carries a copy.

## Map

```
cratebox.html          the whole app (~6.5k lines): CSS, markup, JS, AudioWorklets as a string. Section map below.
index.html             redirect to cratebox.html (Pages entry)
sw.js                  service worker, offline cache. CACHE name "cratebox-<version>"
manifest.webmanifest icon-*.png   PWA install
start_cratebox.py      local server on port 8611 + opens Chrome (fixed port keeps IndexedDB/localStorage)
Start Cratebox.bat     Windows double-click wrapper
filetest.html          diagnostic: which file-picking APIs a MIDI browser app allows
vendor/lame.min.js     MP3 encoder for recording (lamejs, licence alongside)
tools/                 rekordbox.js / playlists.js / controllers.js: copies of cratebox.html sections loaded by tests,
                       mixxx2cratebox.py (Mixxx XML → MIXXX_MAPS)
tests/                 playwright suites (test_*.py), node test_rekordbox.js, make_tracks.py, fixtures/rekordbox_usb
releases/              zipped release builds (only 1.1.0 so far)
reports.txt            problem reports, appended by .github/workflows/reports.yml from issues with a hidden marker
CHANGELOG.md           user-facing changelog; add under "Unreleased"
```

### cratebox.html section map (line numbers drift; grep the banner text)

Banners look like `// ====` / `//  Title` / `// ====`. `grep -n '^//  ' cratebox.html` lists them.

| ~Line | Section |
| --- | --- |
| 17–747 | `<style>`: base, phone (956×440 target), touch, scaling, 4-deck, Booth look |
| 884 | Small helpers, `const VERSION` |
| 983 | Audio engine: `WORKLET` string with `DeckPlayer`, `RecTap`, `FxUnit` processors; analysis (phrases ~1461, beat grid ~1569, key ~1869) |
| 2314 | Mixer state (controls normalised 0..1) |
| 2369 | `class Deck`: grid edit, sync, jog, loops, hot cues |
| 2833 | Library: folder scan, tags, IndexedDB `cratebox` analysis cache, virtualised track list |
| 3334 | rekordbox readers: export.pdb + ANLZ (`RB`), playlist writer (`RB.writePlaylists`), XML |
| 3698 | Playlists (IndexedDB), tree UI, USB/SD devices, stick playlist editing, XML import/export |
| 4489 | UI widgets (knobs/sliders shared by mouse and MIDI) |
| 4569 | Build deck + mixer panels |
| 4728 | Beat FX / Pad FX UI and params |
| 5066 | Waveforms (pre-rendered strips) |
| 5349 | Meters |
| 5377 | MIDI: `MIXXX_MAPS`, FLX4 map, deck layers, LEDs, SMART CFX/FADER, MIDI learn |
| 5891 | Output devices, prefs, recording (~6045), Report a problem (~6160) |
| 6292 | Build UI + main loop |

## Run and test

- Run: `python3 start_cratebox.py` → http://localhost:8611/cratebox.html
- Tests need `pip install playwright numpy` + `playwright install chromium` (cloud sessions: use the preinstalled
  Chromium, don't run `playwright install`). First `python tests/make_tracks.py tests/music`, then any
  `python tests/test_<area>.py` (each serves the repo itself and prints PASS/FAIL lines).
  `node tests/test_rekordbox.js` checks the readers against `tests/fixtures/rekordbox_usb`.
  Pick the suites for what you touched (README "Tests" lists what each covers); `test_cratebox.py` is the main one.
- No CI runs tests here. The only workflow is `reports.yml`. Pages deploys `main` automatically.

## Conventions

- Branches: `main` deploys to Pages, so it must always work on a phone. Feature branches are short topic names
  (`perf/low-end-drawing`, `load-stutter-fix`); session branches are `claude/...`.
  Long-lived forks: `ios` (original Cratebox iOS app, 34 commits ahead of main, frozen; the suite repo forked
  from it) and `mac-air` (1.1.x-mac builds, 9 ahead). Don't merge those into main.
- Release: bump `VERSION` in cratebox.html **and** `CACHE` in sw.js together (otherwise installed PWAs keep the
  old cached app), add a CHANGELOG section, zip into `releases/`.
- Commit messages: a plain sentence of what changed for the user, `Area: detail` when useful.
- Code style: dense vanilla JS, short names (`A.ctx`, `ui[d]`), a comment above each block explaining why. Match it.
- Anything audio-thread lives in the `WORKLET` string; keep it allocation-free.
- User-facing text: plain and specific; say what's untested.

## Cross-repo

- **cratebox-iOS-suite** copies `cratebox.html`, `index.html`, `sw.js`, `manifest.webmanifest`, `filetest.html`,
  `start_cratebox.py`, `tests/`, `tools/`. Its Swift CrateboxKit is a port of this file's Deck/mixer/FX/analysis
  and is checked against it by oracle scripts there (`ios/tools/*_oracle.js`). A DSP or analysis change here
  means the Swift port (and its fixtures) will drift: mention it in the PR.
- **Cratebox-Linux** is a Rust port of the same behaviour (2 decks); its `src/maps.rs` is generated from `MIXXX_MAPS`.
- After changing a shared web file here, sync the copy in the iOS suite.

## Gotchas

- Must be served over http(s), not `file://`: Web MIDI, folder access and AudioWorklet need a secure origin.
- iOS Safari has no Web MIDI; FLX4 on iPhone needs the MIDIWeb Browser app. Tests emulate this (`test_ios*.py`).
- rekordbox USB: reads `export.pdb` only (not OneLibrary `exportLibrary.db`). Stick playlist editing is opt-in
  (Settings → rekordbox USB playlists), writes only playlist tables, keeps `export.pdb.cratebox-backup`, refuses
  if rekordbox re-exported since open. Not yet confirmed on a CDJ.
- Only the FLX4 is hardware-tested; other controller maps come from Mixxx and may be off in details.
- SMART CFX / SMART FADER messages aren't published by Pioneer; they're learned by pressing them.
- 2-core machines: background analysis stops while anything plays (see `test_loadstutter.py`) to avoid dropouts.
- `tools/*.js` are hand-kept copies of cratebox.html code (rekordbox.js is verbatim; playlists.js and
  controllers.js are ~96% identical, adapted). Change the html and the copy together or the tests test stale code.
- If Pages doesn't pick up a push, an empty redeploy commit has been used before ("Redeploy Pages").

## Open work (update this when it changes)

- iOS suite's copy is one commit behind (`62ffff7`); a drift check in the suite's CI was proposed, not built.
- Not in the web app: key shift, OneLibrary reading, tempo-change grids (one tempo used), AIFF decode.
