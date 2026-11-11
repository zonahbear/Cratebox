<<<<<<< HEAD
# CLAUDE.md: Cratebox (web app)
=======
# CLAUDE.md: Cratebox-Linux
>>>>>>> temp-source/main

Read this first; it exists so you don't have to re-parse the repo. Update it when you change structure,
conventions, or finish/start a piece of open work. Keep it under ~150 lines.

## What this repo is

<<<<<<< HEAD
Cratebox, a browser DJ app for the Pioneer DDJ-FLX4 (and other controllers via Mixxx-derived maps): 2, 3 or 4 decks (`NUSE`, `setDecks`), WAVE mode,
keylock, sync, beat grids, keys, phrases, Beat/Pad FX, playlists, rekordbox USB + XML, recording. Plain HTML/JS,
no build step, no framework. Runs from `http://localhost` on desktop (`start_cratebox.py`) and from GitHub Pages
(`main`, repo root) on phones as an installable PWA. Version 1.1.1.

**This repo is the source of truth for `cratebox.html`** and the other web files; the iOS suite carries a copy.
=======
Native Linux port of the Cratebox web app (and the iOS performance mode) in Rust (eframe/egui on glow, cpal for audio, midir for MIDI,
symphonia for decoding). Two or four decks (deck layers 1⇄3 / 2⇄4), DDJ-FLX4 first, other Pioneer/AlphaTheta controllers via Mixxx-derived maps.
Same behaviour and analysis as the web version, no browser or server. The same crate also builds a Windows .exe
(cfg-gated: `win.rs`, `heat_win.rs`; cross-compiled with MinGW). v0.1.0: passes its tests, not yet tried
on real sound hardware or a controller. Built for x86-64-v3 CPUs.
>>>>>>> temp-source/main

## Map

```
<<<<<<< HEAD
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
wrangler.toml          Cloudflare Worker config for the public website (PR #6): build, assets, KV, cron, vars
site/                  website: public/ (landing, privacy), src/worker.js (beta signup → ASC team invite → internal
                       TestFlight group), build.sh (copies the player into /player), test/worker.test.mjs, README (setup)
```

### cratebox.html section map (line numbers drift; grep the banner text)

Banners look like `// ====` / `//  Title` / `// ====`. `grep -n '^//  ' cratebox.html` lists them.

Line numbers below are from 2026-10-22 and have drifted (the file is ~8k lines now); grep the banner.

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
| ~6560 | TrueCurve mini (`const TC`, HEAT button): Puffco heat curves over Web Bluetooth, copy of zonahbear/truecurve web code (merged PR #5) |
| 6292 | Build UI + main loop |

## Run and test

- Run: `python3 start_cratebox.py` → http://localhost:8611/cratebox.html
- Tests need `pip install playwright numpy` + `playwright install chromium` (cloud sessions: don't run `playwright install`;
  set `CRATEBOX_CHROME=/opt/pw-browsers/chromium-*/chrome-linux64/chrome`, which most suites honour). First `python tests/make_tracks.py tests/music`, then any
  `python tests/test_<area>.py` (each serves the repo itself and prints PASS/FAIL lines).
  `node tests/test_rekordbox.js` checks the readers against `tests/fixtures/rekordbox_usb`.
  Pick the suites for what you touched (README "Tests" lists what each covers); `test_cratebox.py` is the main one.
- No CI runs tests here. The only workflow is `reports.yml`. `main` deploys automatically (Cloudflare; leave the deploy setup alone).

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

Session notes and next steps: [`.claudes/breadcrumbs.md`](.claudes/breadcrumbs.md).

## Open work (update this when it changes)
- Web ← iOS catch-up (branch `claude/project-thread-0pjrfq`, 2026-11-02): iOS SYNC rules (`pickMult`, hold = `makeMaster`,
  `phaseFree`), 3 decks, Booth top waveforms + HIDE WAVES, WAVE mode + pop-up library (`wavePop*`), library grip
  (`laneH`/`blaneH`), phone SCRATCH tab, Settings window, phone Touch mode (`html.tmode`), KEY SHIFT (worklet `ps`,
  pad mode `keyshift`, FLX4 notes 0x70+p UNVERIFIED on hardware). Tests: test_wave.py, test_keyshift.py.
  EJECT lets go of a stick (browsers can't unmount; the OS eject still comes after). Not done: key controls in the Mixxx-derived maps (MIDI learn instead).
- test_phrases and test_playlists pass again (2026-11-09, review thread: test drift, not app bugs). test_playlists now runs at 1440x1200:
  at 1440x900 the library only shows ~4 rows since the 1280x800 fit, so drags to off-screen rows failed.
- Website + beta signup: PRs #6 and #7 merged to main (latest 072dc71, 2026-10-22). Live at https://cratebox.zonahbear.workers.dev; Cloudflare production branch is `main`. Secrets set and verified (owner-only `/api/status?k=<LINK_SECRET>&mail=1&asc=1`). #beta has a 6-step iPhone install guide (Jonah-approved copy). Full signup → Apple invite → TestFlight pipeline confirmed working live (2026-10-22). Cloudflare PR preview builds fail instantly (dashboard setting, ignore). Setup: project files website/SETUP.md. Real screenshots wanted. HEAT stays in the public player.
- HEAT / TrueCurve mini: merged to main (PR #5, 2026-10-21). Simulator-tested only (`tests/test_truecurve.py`); not yet tried on a real Puffco. Follow-up idea: learnable controller button. iOS suite copy synced (cratebox-iOS-suite PR #4, merged).

- Analysis (2026-11-10): bar 1 now comes from spectrum changes per beat-of-bar (`BAR_LOW`, ANALYSIS_VER 4), checked against rekordbox grids on
  real tracks (see breadcrumbs). Known gaps: ~7% of tracks half a beat off rekordbox, ~2% tempo at 4/3 or 2/3. Swift port not updated.
- iOS suite copy matches Cratebox main 8a02028 (suite PR #4 merged); a drift check in the suite CI was proposed, not built.
- Not in the web app: OneLibrary reading, tempo-change grids (one tempo used), AIFF decode.
=======
src/main.rs        entry; CPU feature check, --version, --screenshot FILE [FRAMES] (used by tests), --kiosk (full screen),
                   --cmd WORDS (sends to the running app via src/remote.rs: Unix socket, $XDG_RUNTIME_DIR/cratebox.sock)
src/lib.rs         module list (the binary and tests both use the lib)
src/app.rs         App: decks, mixer, library, playlists, controller, background jobs; `poll` drains job results each frame
src/ui.rs          the window, XDJ-style, sized for 1152×720 pt (MacBook10,1 at 2x): header (REC, WAVE, 4 DECKS,
                   HEAT ▾, ⚙), stacked waveform lanes with info strips, decks either side of the mixer (3 1 2 4
                   + BEAT FX), library; WAVE = only the lanes; BROWSE = lanes + big library; HEAT panel
src/widgets.rs     custom-drawn knobs, faders, jogs, meters, waveform painters, header icons; colour THEMES
                   (BG()/FG()/… are functions of the theme; CUE/LOOP/GREEN/RED stay consts)
src/dialog.rs      egui file/folder picker (no GTK/portal)
src/engine.rs      audio engine: 2 players → mixer; commands in by channel, try-locked snapshot out
src/player.rs      deck player on the audio thread, WSOLA keylock; port of the web AudioWorklet (128-sample blocks)
src/mixer.rs       trim, 3-band isolator EQ, CFX filter, cue, faders, limiter, routing
src/deck.rs        deck logic on the UI thread: transport, cue, sync, quantize, loops, hot cues, jog, grid editor
src/analysis.rs    BPM / grid / key / phrases / waveform bands; line-by-line port of the web analyser
src/fft.rs keys.rs FFT, Camelot keys
src/decode.rs      symphonia → planar f32 + tags
src/library.rs     folder scan, tags, analysis cache, search/sort
src/playlists.rs   playlists + folders, rekordbox USB (read-only), rekordbox XML import/export
src/usbcopy.rs     stick → ~/Music/Cratebox USB/<name> local (copy/update, never deletes); a copy keeps the
                   stick's device id so the two are one device; library scans skip "Cratebox USB"
src/rekordbox.rs   export.pdb + ANLZ readers, XML (crate-digger layouts)
src/midi.rs        controller profiles, table-driven MIDI engine, LEDs, MIDI learn
src/maps.rs        GENERATED from the web app's MIXXX_MAPS; don't hand-edit (regenerate instead)
src/midi_io.rs audio_io.rs   midir / cpal device handling (rescans, "no output" timer mode)
src/store.rs       JSON persistence in ~/.local/share/cratebox ($XDG_DATA_HOME, or $CRATEBOX_DATA); the 1 s saves
                   write on a "cratebox-save" thread (flush_bg), flush() drains it then writes inline
src/net.rs         Settings → Wi-Fi / Bluetooth: nmcli + bluetoothctl on a "cratebox-net" worker thread (scans only on request)
src/ring.rs        lock-free ring buffer
src/fx.rs          Beat FX / Pad FX DSP (FxUnit: one per channel insert + master), port of the iOS FxUnit
src/beatfx.rs      BEAT FX unit + PAD FX state on the UI thread; sends beat clocks every 100 ms
src/recorder.rs    REC: master → 16-bit WAV (ring from the audio thread, writer thread)
src/heat_win.rs    HEAT's Bluetooth on Windows (WinRT BLE: watcher, GATT, pairing); same Bus/Seen/Ble shape as heat.rs's
                   bluez module; the Lorax Device impl is shared via the `lorax_device!` macro in heat.rs
src/win.rs         Windows only: MMCSS "Pro Audio" for the audio thread, message boxes, console attach, drive letters,
                   CPU/memory/network/battery readouts, shutdown/restart, opening URLs/folders/ms-settings, Nicotine+.
                   On Windows: remote.rs (--cmd) is off, drives.rs finds sticks by drive letter (eject = Windows'
                   own), WEB/FILES/SOULSEEK open the browser/Explorer/Nicotine+, Wi-Fi/Bluetooth tabs link to Windows Settings
src/heat.rs        HEAT (TrueCurve mini): curve maths, driver, learner, PuffDrop, simulator, Lorax bytes,
                   BlueZ GATT via zbus (pure Rust, no libdbus), worker thread; port of iOS personal/heat
src/uitest.rs      scripted UI driver: CRATEBOX_UITEST=script.json, output to CRATEBOX_UITEST_OUT
examples/grid_compare.rs  analysis vs rekordbox's grids on a stick (or a copy): BPM, beat offset, bar 1. Real-track check for analysis changes
tests/analysis.rs  analysis accuracy on synthetic tracks
tests/app.rs       whole app end-to-end with FLX4 MIDI messages, persistence
tests/ui.rs        real window under Xvfb (skipped without xvfb-run)
CHANGELOG.md       human-readable "what's new" for Jonah: add a line per user-facing PR
docs/keyboard.md   keyboard + trackpad shortcuts (same list as ui.rs SHORTCUTS, the F12 window)
tests/four.rs      4 decks end-to-end: channel 3, sync, layer buttons, FX, REC, HEAT simulator → PUFF
tests/make_tracks.py   synthetic test tracks → tests/music (same script as the web repo)
tests/fixtures/    rekordbox USB export (pyrekordbox test data, MIT)
assets/fonts/      Inter + DejaVu (licences alongside); assets/icon-512.png
packaging/         install.sh, cratebox.desktop, cratebox.png (go into the release tarball)
build-release.sh   distributable tarball via cargo-zigbuild, glibc 2.31 baseline → dist/
env.sh             build env for one past sandbox (points at a local ALSA shim); not needed with libasound2-dev
distro/            Cratebox OS ISO: build-iso.sh remasters Lubuntu 26.04.1 (layered squashfs: chroot-setup.sh runs
                   in the minimal.standard layer, live-setup.sh in the live layer), overlay/ = files for the
                   installed system, live/ = live-session script. distro/README.md = guide + verified/proposed table.
                   plymouth/make-theme.py draws the boot splash PNGs (committed). Calamares "Minimal" always unpacks
                   the full layer, then cratebox-minimal-install autoremoves Lubuntu's extras (list made in chroot-setup).
                   Also: facetimehd DKMS + firmware, maclight (shell, F5/F6), playerctl media keys (openbox-rc.xml),
                   cratebox-boot-update.service (online at boot → cratebox-update --auto with a saved token)
.github/workflows/cratebox-app.yml manual-only: app binary → release "app-latest" (overlay/usr/bin/cratebox-update installs it)
.github/workflows/cratebox-windows.yml manual-only: MinGW cross-build → release "windows-latest" (cratebox.exe)
.github/workflows/cratebox-os.yml  manual-only ubuntu job → release "kiosk-latest" (ISO in <2 GiB parts)
```

## Build and test

- Needs ALSA dev files: `apt install build-essential pkg-config libasound2-dev` (plus `xvfb` for tests/ui.rs).
- Realtime audio: `promote_to_realtime` in src/audio_io.rs (direct SCHED_FIFO, needs rtprio). Don't go back to cpal's
  `audio_thread_priority`: it sets RLIMIT_RTTIME, and SIGXCPU killed Cratebox when the callback overran.
  In a cloud session, install those first; don't rely on `env.sh` (its shim path won't exist).
- `cargo build --release` (x86-64-v3 via `.cargo/config.toml`, target `x86_64-unknown-linux-gnu`, so the binary
  is at `target/x86_64-unknown-linux-gnu/release/cratebox`). Older CPU: `--config 'build.rustflags=[]'`.
- `python3 tests/make_tracks.py tests/music` (needs numpy) then `cargo test --release`.
  Tests fall back to `../cratebox/tests/music` if `tests/music` is missing.
- With no sound card the engine runs on a timer, so timing tests still work in containers.
- Windows: `rustup target add x86_64-pc-windows-gnu`, `apt install mingw-w64`, `cargo build --release --target
  x86_64-pc-windows-gnu` (one .exe, system DLLs only). Smoke test under Wine + Xvfb works (`wine explorer
  /desktop=cb,WxH cratebox.exe --screenshot Z:\path.png 240`, CRATEBOX_DATA as a Z:\ path). On Windows `ui::fit_scale`
  zooms everything to a 720-pt-high canvas (the MacBook's layout); CRATEBOX_FIT=1 does it on Linux.
- No CI on pushes. Releases are built by hand with `./build-release.sh`; the Cratebox OS ISO by the manual
  cratebox-os workflow (Actions minutes are scarce: keep workflows `workflow_dispatch`).

## Conventions

- `main` only; session branches are `claude/...`. Version in `Cargo.toml`.
- Module docs: every file opens with `//!` lines saying what it is and which thread it runs on. Keep that.
- Audio thread code (player, mixer, engine callback) never blocks: try-lock, no allocation.
- Ports stay close to the web code (same names, same maths) so results match; `analysis.rs` and `player.rs`
  are meant to be line-by-line ports.
- Commit messages: plain sentence of what changed for the user.
- Cratebox OS is audio first, for Jonah's MacBook10,1: keep the ISO's kernel (7.0.0-30, verified with the
  speaker driver) and hold it; s2idle only; never TLP or HDA power_save tweaks; never remove
  pipewire/wireplumber/rtkit. StartupMute=%00 is per-machine NVRAM (first-boot step in distro/README.md).

## Cross-repo

- Behaviour reference is **zonahbear/Cratebox** `cratebox.html` (see that repo's CLAUDE.md for its section map).
  When the web app's analysis, deck logic or controller maps change, this port drifts; nothing checks it
  automatically.
- `src/maps.rs` comes from the web app's `MIXXX_MAPS` table (itself from `tools/mixxx2cratebox.py` there).
- **cratebox-iOS-suite** is a separate Swift port; no shared code.

## Gotchas

- 3-deck mode = settings four+three (deck_count()): left layer button switches 1⇄3, right stays on 2; header button cycles 2→3→4.
- Command(Super) shortcuts: egui drops Super on Linux, so openbox-rc.xml binds them to `cratebox --cmd …`
  (⌘⇧X / ⌘⇧. = bar 1 on the left / right deck; Ctrl+Shift does the same in-app). Shift+deck key never plays.
- Battery (ui.rs battery_watch): 5% alert; 3% stops decks + App::eject_all (drives::eject_all thread, SCHED_FIFO 40).
  Shutdown/restart = App::power_off (save, unload decks, eject, then systemctl). CRATEBOX_FAKE_BATTERY="pc,charging" to try it.
- Layer buttons are learned once (Settings → Controller → Set up layer buttons…): the FLX4's SMART CFX/FADER
  notes aren't in the map. Their LEDs stay off.
- Decks are XDJ-style screens (platter, time, key, BPM, beat/phrase, hot cues) with buttons under them, or
  screens only (Settings → Decks; auto = screens only while a MIDI controller is connected; `deck_view`).
- HEAT registers its own BlueZ agent (NoInputNoOutput, /org/cratebox/agent) since the kiosk has no desktop one;
  HEAT's messages go to heat.log in the data dir.
- HEAT GLOW: heat::Glow (rainbow + music envelope, FX depth knob) → Cmd::Glow → lantern writes /p/app/ltrn/cmd +
  /p/app/ltrn/colr (paths from HA-Puff puffco_ble, MIT; untested on a Proxy). Never sent during a heat run or HOLD.
- HEAT safety rules (slot 4 backed up/restored, 600°F cutoff, 350-590°F clamp) must match zonahbear/truecurve.
- CRATEBOX_DEMO=1 (+ CRATEBOX_DEMO_HEAT=1) drive the screenshots; 4-deck demo loads decks 3/4 too.
- rekordbox grids win: stick tracks, XML imports, and collection tracks with a stick twin (same file name + size,
  app.rs adopt_rb_grid at load). Settings → rekordbox → Compare grids logs bar-1 offsets to grid-compare.log
  (evidence for the "bar 1 half a bar late" report; synthetic tests are all on bar 1, so tuning needs real tracks).
  2026-11-10: bar-1 vote replaced after measuring on 113 real stick tracks (breadcrumbs); ~7% still half a beat off rekordbox.
- A mounted stick is never copied by itself: Job::Mounted sets App.ask_copy, ui.rs copy_dialog asks, answer_copy(yes) runs copy_device (Jonah's rule, 2026-11-10).
- rekordbox is read-only here: never writes to a stick (the web app's playlist writer isn't ported).
- Header launchers: WEB = cratebox-web (Chromium, xtradeb PPA deb; Chrome only as a fallback on old images), SOULSEEK = cratebox-soulseek (Nicotine+), FILES = pcmanfm-qt; openbox-rc.xml
  gives every window but Cratebox a frame at 80%, resizable. Settings is tabbed (SETTINGS_TABS in ui.rs, one fn per tab).
- egui closed_line: never repeat the first point at the end (the zero-length segment drew a spike through the globe icon).
- Binary refuses to run on CPUs without AVX2/FMA/BMI2 and says how to rebuild.
- Scrolling lanes are GPU tiles (widgets::WaveCache; overviews likewise: OverviewCache, Gui.ov_cache, 512 px at normal speed, linear filtering, drawn at fractional x,
  stretched for tempo; Gui.lane_cache). Don't go back to whole-pixel meshes: that stepped 4/5 px a frame.
- Waveforms are timed by deck::frame_tick/frame_time (whole refresh intervals, not wall clock at update()); App eases
  vis_delay. Settings → Look → Show frame rate puts FPS/missed refreshes in the header; CRATEBOX_PROFILE=1 also logs them.
- `build-release.sh` links with `--allow-shlib-undefined` on purpose (user's own libasound at run time).

## Open work (update this when it changes)

- Windows build: only tested under Wine (UI, analysis, 4 decks, HEAT simulator); WASAPI latency/dropouts, FLX4 MIDI/audio
  and WinRT BLE to a real Puffco untested on a real PC.
- Untested on real audio hardware and a real FLX4; HEAT's BlueZ link untested on a real Puffco (simulator only).
- Cratebox OS: builds on Actions (cratebox-os → release kiosk-latest). On the MacBook (Jonah): live speakers work;
  sleep/wake reconnect, a full install (normal and minimal), headphones, Claude sign-in and HEAT still to check.
  The "proposed" settings in distro/README.md are unmeasured.
- Behind the web app: stick playlist editing, other
  1.1.x changes. Check the web CHANGELOG against this port before claiming parity.
>>>>>>> temp-source/main
