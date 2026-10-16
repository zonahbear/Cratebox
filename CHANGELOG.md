# Changelog

All notable changes to Cratebox (the web app). Version numbers follow `MAJOR.MINOR.PATCH`.

## 1.1.1-mac (2026-10-16): Mac edition

A build of 1.1.1 for one machine: a 2017 MacBook Air running CachyOS, played in Firefox. Lives in the `mac-air` branch; the regular Cratebox on `main` is unchanged.

### Added
- **Launcher file bridge** (`cratebox.py`): Firefox can't open or remember folders, so the launcher reads the music folder and rekordbox USB sticks for the page. The folder is picked in KDE's or GNOME's own folder dialog (or typed when there's none) and opened again by itself at Start; a folder on a drive that isn't there yet gets **Reconnect**. Read-only; answers only this computer, only Cratebox's own page (other sites and other host names are refused), and only paths under your home folder and `/run/media`, `/media`, `/mnt`.
- **rekordbox USB on Firefox**: **+ USB** opens every plugged-in stick with a rekordbox export under `/run/media`, and sticks that were open come back at Start when they're plugged in.
- `python3 cratebox.py --install` adds Cratebox to the app menu; the launcher opens Firefox.
- Problem reports say which edition it is and include the audio buffer and latency.
- `tests/test_mac.py`: the launcher and bridge end to end, including the refusals.

### Changed
- **Headphone cueing works in Firefox.** The FLX4 jack (channels 3–4) and **Another device** were switched off in browsers without `AudioContext.setSinkId`, which includes Firefox. The jack works whenever the system output has 4 channels; Another device uses Firefox's own speaker picker (`selectAudioOutput`).
- The master plays on the system's sound output (Firefox can't pick one from the page), so the **Output** menu is gone; the ch pill stays.
- Fonts (Barlow, Barlow Condensed, IBM Plex Mono; SIL OFL) are bundled in `fonts/`: no requests to Google Fonts, and the same look offline.
- The layout check (does it fit, or should the page scroll) runs again once the fonts have loaded.
- MIDI messages and the start screen talk about Firefox (and its MIDI site permission) instead of Chrome.

### Removed
- Everything for phones and tablets: the phone layout and its sheets and tabs, touch-only buttons and gestures, the imported-files library (iPhone/iPad), the iOS MIDI-browser workarounds, the low-memory mode, the "turn your phone" screen, and their tests (`test_ios.py`, `test_ios_midi.py`, `test_android.py`) and layout sizes.
- The service worker and web app manifest (it's served from this computer), the Windows launcher, the Chrome launcher and `filetest.html`.
- Settings → Waveform detail: the Air's screen is 1x, where Light and Sharp are the same.

## 1.1.1 (2026-10-16)

### Changed
- **Faster drawing on slow computers.** The scrolling waveforms are painted once into a strip and slid along by the graphics card, instead of every pixel being repainted on every frame. The overview, jog wheels and level meters only repaint when something on them changes, so a paused deck costs almost nothing. Measured in headless Chrome with the CPU slowed 4x: 4 decks at 2560x1440 went from 10.6 to 4.1 ms of drawing per frame while playing, and from 10.3 to 1.6 ms when paused; 2 decks at 1440x900 from 4.4 to 1.9 ms playing and 3.9 to 0.9 ms paused.
- Waveform, overview and meter canvases are opaque, so the browser doesn't blend them over the page.

### Added
- **Settings → Waveform detail**: Auto, Sharp or Light. Light draws the waveforms at 1x (a quarter of the pixels on a 2x screen). Auto starts sharp and switches to Light for the session if drawing stays slow for 3 seconds.
- **Settings → Load lock**: Locked (the default, as before: a playing deck won't take a new track) or Unlocked (loading onto a playing deck stops it and loads the new track).
- **Settings → Phrases**: Show or Hide the phrase strips and labels on the waveforms, the overview and the deck's phrase readout.
- Problem reports include the graphics renderer (and whether the browser is drawing without the graphics card), the waveform detail and the drawing time per frame.

### Fixed
- **Phrases on rekordbox library tracks.** A rekordbox track that came without rekordbox's own phrase analysis (no phrases in its .EXT file) showed no phrases at all. Cratebox now works them out itself, on rekordbox's beat grid, when the track loads, and keeps them. rekordbox's own phrases are still used when it has them.
- A paused deck's waveform now redraws when its phrases change (they're worked out again in the background after a grid edit); since the faster drawing it kept showing the old ones until you pressed play.

## 1.1.0 (2026-10-16)

### Added
- **Beat FX**: ECHO, DELAY, PING PONG, REVERB, FLANGER, FILTER, TRANS, ROLL, HPF, LPF, timed to the beat grid. Effect select, BEAT ◀ ▶, channel (1, 2, 3, 4 or MASTER), level, ON. Strip at the bottom of the mixer; its own sheet on phones (FX in the header). Echo, delay and reverb ring out when switched off.
- **Pad FX**: a PAD FX pad mode with two banks of 8 momentary effects (hold a pad, let go to stop).
- **DDJ-FLX4**: the BEAT FX section (FX SELECT and SHIFT, BEAT ◀ ▶, CH SELECT lever incl. MASTER, LEVEL/DEPTH, ON/OFF and SHIFT = all off, with its light) and PAD FX1 / PAD FX2 pads with their lights. Messages from Mixxx's DDJ-FLX4 mapping. Beat FX controls can also be learned on other controllers.
- `tests/test_fx.py`: renders every effect offline and measures it, and drives the controls on screen and over MIDI.

### Changed
- Pad mode buttons show short labels (CUES, LOOP, JUMP, FX) unless the deck is wide.

## 1.0.2 (2026-10-16)

### Fixed
- **Headphone mix knob at 12 o'clock no longer brings the master in.** The left half of the CUE/MASTER knob, up to and including 12 o'clock, is now cue only (with a little room for the FLX4 knob's centre detent); the master fades in only past 12 o'clock, and fully right is master only. With MASTER CUE off and the knob at the centre, you hear only the cued channels.

## 1.0.1 (2026-10-16)

### Fixed
- **Headphone cue.** The CUE/MASTER mix started halfway, so about 70% of the master was always in the headphones, even with no CUE pressed, and the FLX4's MASTER CUE seemed to do little (the master was already there). The mix now starts fully on CUE: silence until you press a channel's CUE, and MASTER CUE (or turning the knob right) clearly brings the master in. Fully left is now exactly cue-only, fully right exactly master-only.

### Added
- **MST** (master cue) button under the CUE/MST knob, for setups without the FLX4's hardware MASTER CUE (Split, another device). Learnable on a controller.

## 1.0.0 (2026-10-16)

### Changed
- **Booth is the default look.** The original look is still in Settings as **Cratebox classic**. A look now only sticks once you pick it in Settings, so everyone who never chose one gets Booth (0.10.x saved "default" without being asked).
- **Settings** moved up to the header, next to Test cue; its panel drops down from there.
### Added
- **Jog sensitivity** (Settings, 25–200%): how far the track moves per turn of the jog, for the controller's platter (scratch, nudge, search) and the on-screen jog. Dragging the waveform stays 1:1 with your hand.

### Notes
- First 1.0 release.

## 0.10.2 (2026-10-16)

### Changed
- The bar counter is now drawn on each deck's scrolling waveform, right beside the red playhead line (like rekordbox and club players), in the deck's colour, instead of in the deck's info row.

## 0.10.1 (2026-10-15)

### Added
- **Bar counter** on every deck, like rekordbox: bar.beat (1.1, 1.2, 1.3, 1.4, 2.1 ...), next to the time. Counted from the beat grid's first downbeat (bars before it read 0.4, 0.3 ...); **BAR 1 HERE** in GRID moves the downbeat. Shown on compact decks and phones too, and bigger in the Booth look.

## 0.10.0 (2026-10-15)

### Added
- **4-deck mode** (computers and tablets): **4 DECKS** in the header adds decks 3 and 4, two more waveforms and a 4-channel mixer (3 1 2 4). Decks 3 and 4 start compact (CUE, PLAY, SYNC, loop, tempo) and expand to full decks with ⤢. Crossfader: 1 and 3 left, 2 and 4 right. Sync picks a master among four decks. Remembered between sessions.
- **Set recording**: ● REC records the master output to WAV (16-bit, lossless) or MP3 (320 kbps, encoded in the background with the bundled lamejs). A tracklist with timestamps is kept while recording and can be saved as text.
- **Looks**: a new **Booth** look in Settings, an original club-player style where each deck is its own player with a screen and waveform, and controls are drawn like hardware. The current look stays the default.
- **Interface size**: Auto scales the whole app up on big screens (1440p, 4K) so it fills them like a laptop screen; or choose 100–175%.
- **Report a problem** (Settings): sends a pre-filled GitHub issue with device details, which a workflow copies into `reports.txt`; or copies the report to the clipboard.
- **Audio buffer** setting: Small / Medium (new default) / Large.
- This changelog.

### Changed: audio first
- Sync and the beat lock now run on their own 20 ms timer instead of the screen refresh: they keep correcting with the tab hidden or the screen busy, and a drawing error can't stop them.
- A stopped deck no longer costs processing on the audio thread; decks 3 and 4 have no audio chain until 4-deck mode is turned on.
- The recorder reuses its buffers (no garbage on the audio thread).
- Library analysis takes a breather between tracks while music plays.
- Waveform drawing skips every other frame when frames get slow, before anything else gives.
- Default audio buffer is now Medium ("balanced") instead of the smallest, trading a few ms of latency for fewer dropouts.
- Leaving or reloading the page while music plays (or records) asks first.
- **2 DECKS** won't hide decks 3 and 4 while they play (it used to stop them).

### Fixed
- Short laptop screens (720–820 px tall): decks and mixer tightened so both waveforms and the library stay visible.

## 0.9.3 (2026-10-15)
### Fixed
- Phones and tablets: **Add music** did nothing in some in-app browsers (iOS MIDI browsers). The tap now lands on the real file picker instead of one opened from script.
### Added
- `filetest.html`: tries four ways of picking files, to see which an in-app browser allows.

## 0.9.2 (2026-10-15)
### Added
- iPhone/iPad: FLX4 support through MIDI browser apps (MIDIWeb Browser). Web MIDI added late by such apps is picked up when you press Start.
### Changed
- File pickers are invisible instead of `display: none`, which some in-app browsers won't open.
- Safari's start screen points to MIDIWeb Browser for controller use.

## 0.9.1 (2026-10-15)
### Fixed
- Phone faders start at 100%, and the handle sits at the bottom at 0%.
- Layout scales from an iPhone SE to a 1440p monitor (narrow phones drop the tiny jog, short laptops get a tighter deck and paired mixer knobs, tablets get finger-sized controls); iPad mini landscape no longer scrolls sideways.
- Service worker: if GitHub Pages answers with an error page (it briefly 404s while redeploying), the cached app is used.
### Changed
- Bigger mixer EQ knobs on phones.

## 0.9.0 (2026-10-14)
### Added
- Sync locks halftime / double time (70↔140, 65↔130, 85↔170) without changing either track's speed; SYNC ½ / SYNC ×2 on the button.
- Beat lock: continuous tiny speed corrections keep synced decks from drifting; ±ms phase readout.
- Playlists, rekordbox USB/SD export and rekordbox XML support; Android controller support; waveform seeking. (Earlier history: see the git log.)
