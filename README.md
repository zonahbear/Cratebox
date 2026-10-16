# Cratebox: Mac edition

Version 1.1.2-mac. What changed: [CHANGELOG.md](CHANGELOG.md).

A lightweight DJ app (2 or 4 decks) for the Pioneer DDJ-FLX4, in this edition built for one machine: a **2017 MacBook Air running CachyOS, played in Firefox**. It's the full desktop Cratebox with the phone and tablet parts taken out, set up for Firefox and Linux, and it runs entirely from this folder: no internet needed, nothing is uploaded.

What's different from the regular Cratebox:

- **Firefox, not Chrome.** Firefox can't open or remember folders and can't send audio to a chosen device, so the launcher reads your music folder and rekordbox USB sticks for the page, and the master plays on the system's sound output.
- **Desktop only.** No phone layout, touch controls, imported-files mode or install-as-app (service worker). Less code, nothing that doesn't apply to a laptop.
- **Fonts are in the folder** (`fonts/`), so it looks the same offline and makes no network requests.
- Drawing is the low-end version from 1.1: waveforms are painted once and slid by the graphics card, and nothing repaints when it hasn't changed.

## Start it

You need Python 3 and Firefox (both normally come with CachyOS; if `python3` is missing: `sudo pacman -S python`).

1. Unzip this folder somewhere it can stay, for example `~/Cratebox`.
2. Once: open a terminal in the folder and run `python3 cratebox.py --install`. Cratebox is now in the app menu (Multimedia, or search "Cratebox").
3. Plug in the FLX4 and make it the sound output (next section), then start **Cratebox** from the menu. Firefox opens it.
4. Click **Start**. Firefox asks about MIDI devices: allow it (see below).
5. Click **Add music folder** and pick the folder you DJ from in the folder dialog. Tracks are read in place, and the folder is opened again by itself next time.

Without installing: `python3 cratebox.py` in the folder does the same. It always uses `http://localhost:8611`, so your library, BPMs, cue points, settings and Firefox's MIDI permission are kept. Closing the Cratebox tab is enough when you're done; the launcher stays running quietly in the background and uses no CPU (it stops when you log out, or with `pkill -f cratebox.py`). `python3 cratebox.py --uninstall` removes the menu entry.

**Full screen:** press **F11** in Firefox to get the whole 1440 x 900 screen (both waveforms and more of the library fit).

The folder dialog is KDE's (`kdialog`) or GNOME's (`zenity`). If neither is installed, Cratebox asks you to type the folder's path instead (`sudo pacman -S kdialog` adds the dialog on KDE).

### Firefox and MIDI

Firefox lets a page use MIDI devices through a small "site permission" add-on it installs for that page the first time you allow it. When it asks, allow it. If it offers MIDI **with SysEx** (system exclusive) access, take that one: it keeps the FLX4's lights awake. Without SysEx everything works, but the controller's lights may go to sleep. If you said no by mistake: `about:addons` → *Site permissions*, remove the one for localhost, and reload.

## Sound

Wire it like rekordbox: speakers on the FLX4's rear MASTER outputs, headphones in the front jack.

- **Output**: Cratebox plays on the system's sound output. Make the FLX4 the default *before* clicking Start: **System Settings → Sound**, and under *Playback Devices* make **DDJ-FLX4** the default. Firefox can't switch the output from inside the page.
- **Headphone cueing on the FLX4 needs 4 channels.** The FLX4 has 4 outputs: 1–2 are master, 3–4 the headphone jack. In **System Settings → Sound**, set the DDJ-FLX4's **Profile** to a 4-channel one: **Analog Surround 4.0 Output** if it's listed, otherwise **Pro Audio**. Then reload Cratebox. The **ch pill** in the header shows how many channels Firefox sees on the output: it should say **4 ch**.
- **Headphones**:
  - **Auto** (default): uses the FLX4 jack whenever the output has 4 channels.
  - **FLX4 jack (channels 3–4)**: the rekordbox setup.
  - **Another device**: the cue mix on a second sound output (for example the Air's own headphone jack), master stays on the FLX4. Firefox shows its own speaker picker, and asks again after Firefox restarts.
  - **Split**: mono master left, mono cue right, for a single output and a splitter cable.
- **Test cue** beeps three times in the headphone mix only. If you also hear it from the speakers, cue isn't separated yet.
- The **CUE/MST** knob (and the FLX4's HEADPHONES MIX knob) blends cue and master in the headphones. It starts fully on **CUE**: the headphones are silent until you press a channel's **CUE**. From fully left up to 12 o'clock it's cue only, with no master at all; past 12 o'clock the master fades in, and fully right is master only.
- **MASTER CUE**: the FLX4's own MASTER CUE button puts the master in the headphones in the controller's hardware. On other setups (Split, another device), the **MST** button under the CUE/MST knob does the same in Cratebox (also learnable on a controller).
- HEADPHONES LEVEL and MASTER LEVEL on the FLX4 are analog and always work.

### If the pill says "2 ch"

Firefox only sees what the system output offers. Check that the FLX4 is the default output and its profile is a 4-channel one (above), then close the Cratebox tab and start it again: Firefox reads the channel count when the audio starts. If no 4-channel profile is offered, use **Another device** and plug your headphones into the Air.

### Smooth playback on the Air

- Plug in the charger, and pick the **Performance** power profile (battery menu) while you play, so the CPU doesn't slow down mid-mix.
- **Audio buffer** (Settings): Medium is the default. If you hear crackles, pick Large and reload.
- Settings → **Report a problem…** shows what Firefox draws with ("Graphics:") and how long each frame takes. A renderer called *llvmpipe* or *software* means Firefox isn't using the graphics chip: check `about:support` → *Compositing* (it should say *WebRender*, not *WebRender (Software)*).

## Controllers

Cratebox picks a mapping from the controller's name. **Settings → Controller** shows which one it chose, lets you pick another, and has **Learn** for fixing or adding controls.

| Hardware | Mapping |
|---|---|
| DDJ-FLX4 | Built in, checked on the hardware (table below) |
| DDJ-400, DDJ-200, DDJ-SB, SB2, SB3, DDJ-SX, SX2, SX3, XDJ-RX, CDJ-2000 / NXS / NXS2, CDJ-850, CDJ-350 | Built from Mixxx's community mapping for that exact model |
| Other rekordbox-series units: DDJ-FLX2, FLX6, FLX6-GT, FLX10, 800, 1000, GRV6, RB, RR, RX, RZ; XDJ-RX2, RX3, XZ, AZ, OPUS-QUAD | The shared rekordbox-series layout (the FLX4's, extended to four decks) |
| Other Serato-series units: DDJ-SR, SR2, SZ, SZ2, REV1, REV5, REV7, 1000SRT | The shared Serato-series layout (the DDJ-SX's) |
| CDJ-3000, other CDJ / XDJ players in MIDI mode | The CDJ-2000 layout |
| Anything else that speaks MIDI, including DJM mixers | Learn |

Only the FLX4 has been tested on real hardware. The others come from published community mappings or from the product line's shared layout: the main controls (play, cue, sync, jog, tempo, faders, EQ, pads, browse, load) should work, details may not. Four-deck controllers drive decks 1/2 from their deck 3/4 layers too; in 4-deck mode, the **deck layer** toggles (see 4 decks) put either side on deck 3 or 4. CDJs and XDJs need their MIDI (or "PC/DJ software") mode switched on and each player on its own MIDI channel (1 and 2).

**Learn:** Settings → Controller → **Learn…**, click a control on screen (it gets a yellow outline), then press, move or turn the real one. Faders and knobs pick up Pioneer-style 14-bit fine control automatically. For the jog, touch the platter then turn it. The library buttons (browse knob, load, jog side for nudging) are in the yellow bar. What you learn overrides the built-in mapping, is saved per mapping, and can be exported to a file and imported on another computer. **Clear learned** goes back to the built-in mapping.

Mappings for the Mixxx-derived models were generated by `tools/mixxx2cratebox.py` from the [Mixxx](https://mixxx.org) project's controller mappings (GPL-2.0), credit to their authors.

### DDJ-FLX4 controls

| Control | What it does |
|---|---|
| PLAY/PAUSE | Play / pause. SHIFT: play from the cue point |
| CUE | CDJ-style: playing → back to the cue point; stopped → set cue (snapped to the beat with Q on); on the cue → preview while held. SHIFT: back to the start |
| BEAT SYNC | Match tempo and beat phase to the other deck; stays locked while on. Long press: sync on. SHIFT: tempo range ±6/10/16%/WIDE |
| Jog top (touched) | Scratch / move the track by hand. Fling it backwards and let go for a backspin; **Backspin** in Settings sets how long it spins. Too touchy? **Jog sensitivity** in Settings (25–200%) |
| Jog side | Nudge (pitch bend) while playing, fine search while stopped |
| SHIFT + jog | Fast search |
| TEMPO fader | ±range; top is slower, like a CDJ |
| LOOP IN / OUT / RELOOP-EXIT | Manual loops. Hold IN for half a second for a 4-beat loop. SHIFT+IN halves, SHIFT+OUT doubles |
| CUE/LOOP CALL ◀ ▶ | In a loop: halve/double it. Otherwise: jump to the previous/next hot cue. SHIFT: jump a bar back/forward |
| Pads, HOT CUE mode | Set or recall hot cues A–H; SHIFT+pad deletes |
| Pads, BEAT LOOP mode (SHIFT + BEAT JUMP) | 1/4, 1/2, 1, 2, 4, 8, 16, 32-beat loops |
| Pads, BEAT JUMP mode | Jump −1/+1, −2/+2, −4/+4, −8/+8 beats |
| Pads, PAD FX1 / PAD FX2 mode (SHIFT + PAD FX1) | Hold a pad for an effect on that deck, let go to stop (banks below) |
| BEAT FX: FX SELECT (SHIFT: previous), BEAT ◀ ▶, CH SELECT, LEVEL/DEPTH, ON/OFF (SHIFT: all off) | The Beat FX unit; the ON/OFF light follows it |
| Channel faders, crossfader, TRIM, HI/MID/LOW (full kill), CFX filter | Mixer |
| Headphone CUE buttons | Send a channel to the headphones |
| BROWSE knob / LOAD 1 / LOAD 2 | Scroll the library and load the selected track |
| SHIFT + BROWSE | Waveform zoom |
| SHIFT + press BROWSE | Expand the library over the jogs and mixer (or click **Expand library**) |

LEDs follow the software: PLAY and CUE blink like a CDJ, pads light for set hot cues and the active loop size, loop/sync/cue buttons light when on, and the channel level meters show each deck's level.

Not mapped yet: Beat FX, sampler, Pad FX, key shift, and the SMART CFX/keyboard modes.

## 4 decks

**4 DECKS** in the header adds decks 3 and 4 under decks 1 and 2, a fourth and fifth waveform, and a 4-channel mixer in the order **3 1 2 4**. The crossfader sends 1 and 3 left, 2 and 4 right. **2 DECKS** goes back (once decks 3 and 4 are stopped: a playing deck is never cut off). Your choice is remembered.

- Decks 3 and 4 start **compact**: title, waveform, CUE, PLAY, SYNC, a 4-beat loop and ± tempo. **⤢** opens the full deck.
- Load them by dragging a track onto them, or with Ctrl+Shift+← / → (Shift+← / → loads decks 1 and 2).
- With four decks, SYNC follows the deck that isn't synced itself and is playing (the one playing longest, if there are several).
- **Deck layers** (playing decks 3 and 4 from a 2-channel controller like the FLX4): the toggles at the top of the mixer pick which deck each side of the controller plays. **1 | 3** on the left, **2 | 4** on the right; click to switch. Everything on that side follows: PLAY, CUE, SYNC, the jog, pads, loops, LOAD, the tempo fader, and that channel's fader, EQ, TRIM, CFX and CUE, plus the lights and the VU meter. The decks the controller is playing have an outline in their colour. The BEAT FX CH SELECT lever follows the side it points at.
- **No jumps when you switch:** after switching, a fader or knob only takes over once you move it to (or past) the new deck's setting, so deck 3's tempo or volume never jumps to where deck 1's was (soft takeover). Until then, moving it does nothing.
- The toggles can be learned onto spare buttons (Settings → Controller → **Learn…**, click a toggle, press the button). Going back to **2 DECKS** puts the controller on decks 1 and 2 again.

## Recording

**● REC** in the header records the master output (exactly what the speakers get, after the limiter) until you press it again; the button shows the running time. The file is saved to your downloads as `Cratebox set <date> <time>.wav` (or `.mp3`).

- **Format** (Settings → Recording format): WAV, lossless 16-bit (about 600 MB per hour), or MP3 at 320 kbps (about 140 MB per hour). The MP3 encoder (lamejs, LGPL, in `vendor/`) runs in the background and works offline.
- A **tracklist** is kept while recording: every track that was playing and could be heard (fader up, crossfader open), with the time it came in. **Save tracklist** saves it as a text file.
- Leaving or reloading the page while recording (or while anything plays) asks first.

## Looks and screen size

- **Look** (Settings): **Booth** (the default), a club-player style: each deck becomes its own player with a black screen holding its scrolling waveform, and the controls are drawn like hardware (rubber pads, LED rings, fader caps). **Cratebox classic** is the original look, with shared waveforms across the top.
- **Interface size** (Settings): **Auto** scales the whole app up on big screens, so a 1440p or 4K monitor is filled the way a laptop is (Auto treats the window as about 1600 x 900). Or pick 100–175% yourself.

## Audio first

Playback runs on the browser's real-time audio thread and nothing else in the app can interrupt it:

- Sync and the beat lock run on their own timer, not the screen refresh: they keep working with the tab in the background or the screen busy, and a drawing error can't stop them.
- A stopped deck costs (almost) nothing; decks 3 and 4 use no audio processing until 4-deck mode is turned on.
- The recorder reuses its buffers, so it makes no garbage on the audio thread.
- Library analysis slows down while music plays; waveform drawing skips frames on a slow computer before anything else gives.
- **Audio buffer** (Settings): Medium is the default. Small gives the tightest jog feel on a strong computer; Large is the safest from dropouts. It takes effect after a reload.

## Report a problem

Settings → **Report a problem…**: describe what happened; device details (browser, screen, controller, version, recent errors; no personal info or track names) are added if you leave the box ticked. **Send on GitHub** opens a pre-filled issue (needs a GitHub account); each one is copied into [`reports.txt`](reports.txt) in this repository automatically. **Copy report** puts it on the clipboard to send any other way.

## Sync

**SYNC** (or BEAT SYNC on the FLX4) matches tempo and lines up the beats, then keeps them locked.

- **Halftime / double time:** if one track is half or double the other (70 and 140, 65 and 130, 85 and 170), sync leaves its speed alone and locks every beat of the slower one to every other beat of the faster one. The button shows **SYNC ½** or **SYNC ×2**. The master's tempo changes carry it along at half or double.
- **Beat lock:** while both decks play, Cratebox keeps comparing their beat grids and corrects with a tiny speed change (at most 0.6%), so the mix never drifts. The **±ms** readout next to the key shows how far apart the beats are: green is locked. An offset of more than a quarter beat is left alone on purpose; SYNC off and on re-locks it.
- If the readout says locked but you still hear the beats slide, that track's beat grid is off. Fix it with **GRID**.

## Waveforms

- **RGB** (default): colour shows what's playing, rekordbox-style. Red is lows (kicks, sub), green is mids, blue is highs (hats, cymbals); mixes blend (a kick with a click goes orange-white). The lighter core is the average level, the outer edge the peaks. Detail is 300 points per second, drawn pixel by pixel.
- **3-band** (Settings): the older blue/orange/white style.
- Scroll the mouse wheel over a waveform to zoom (or SHIFT + BROWSE on the FLX4).
- The waveforms follow tempo: speed a track up and its waveform squeezes together, so two synced decks show their beats at the same spacing.

## Beat FX and Pad FX

**Beat FX** (the strip at the bottom of the mixer; the FLX4's BEAT FX section):

- **Effect**: ECHO, DELAY, PING PONG, REVERB, FLANGER, FILTER (a sweep), TRANS (a gate), ROLL, HPF, LPF. Click to go to the next, Shift-click or right-click for the previous (FX SELECT / SHIFT + FX SELECT on the FLX4).
- **◀ ▶ beats**: the effect's timing, locked to the beat grid of the deck it's on (on MASTER: the deck the mix follows). ECHO 1/2 at 140 BPM repeats every 0.214 s, TRANS gates on the beat, ROLL repeats the slice of the grid you're in. Each effect remembers its own setting. REVERB, HPF and LPF have none.
- **Channel**: 1, 2 (and 3, 4 in 4-deck mode) or **M**aster. On the FLX4, the CH SELECT lever: 1, 2 or MASTER.
- **Level**: how much effect (for HPF/LPF and FILTER, how far the filter goes; for TRANS, how hard it cuts). The FLX4's LEVEL/DEPTH knob.
- **FX ON**: echoes, delays and reverb ring out naturally when you switch off, like on a club mixer; the others stop at once.

On a channel the effect sits after the EQ and filter and before the fader and CUE, so you hear it in the headphones when you cue that channel.

**Pad FX** (**PAD FX** pad mode on each deck; PAD FX1 / PAD FX2 on the FLX4): hold a pad and that effect runs on that deck until you let go.

| Pad | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **PAD FX1** | Echo 1/2 | Echo 1 | Reverb | Roll 1/4 | Roll 1/2 | Trans 1/4 | HPF | LPF |
| **PAD FX2** (press PAD FX again on screen) | Ping pong 1/2 | Delay 3/4 | Flanger 16 | Roll 1/8 | Roll 1 | Trans 1/8 | Filter 4 | Echo 1/4 |

All effects run on the audio thread with the decks; with nothing on, each insert is a plain copy and costs nothing. Reverb and echo on every insert at once still run about 17x faster than real time in testing.

## Bar counter

Each deck's waveform shows where you are as **bar.beat** beside the red playhead line, like rekordbox: 1.1, 1.2, 1.3, 1.4, 2.1 and so on, counted on the beat grid from the track's first downbeat. If the count is a beat off, the grid's downbeat is: pause on the "1" and press **BAR 1 HERE** in GRID.

## Phrases

Each track is split into phrases on bar lines and named: **Intro**, **Build**, **Drop**, **Groove** (drums in, not the peak), **Breakdown**, **Outro**. They show as a coloured strip under the track overview and along the top of the scrolling waveform, and the deck shows where you are, e.g. `DROP 13/16` = bar 13 of a 16-bar drop. Handy for landing your next drop on the 1 of the other track's.

It works from loudness, the low end, the highs and whether a kick is in, so it's reliable for the big changes (drums in or out, drops) and rougher on subtle ones (Groove vs Drop). Phrases follow the beat grid: fix the grid and they're redone automatically.

## Master tempo

The **MT** button on each deck (on by default, remembered) is keylock: moving the tempo fader or syncing changes the speed but keeps the key, like MASTER TEMPO on a CDJ. Turn it off for vinyl behaviour, where faster also means higher.

It works by rebuilding the sound from short overlapping slices (WSOLA, the same family of technique as SoundTouch). Within ±8% it's clean; past ±16% you'll hear some smearing on vocals and long pads. Scratching always plays the raw record, then keylock picks up again when you let go.

## Keys

Every track gets a key in Camelot notation (8A = A minor, 8B = C major). Tracks mix smoothly with the same code, one number either side with the same letter, or the same number with the other letter. While a deck is playing, the library highlights the keys that fit it, and typing a code like `8a` into search filters by key. With MT off, pitching a track changes its key, and the deck shows both (`9A (8A)`).

Key detection is built for electronic music (natural minor). The usual mistake is swapping a key with its relative major or minor (7A vs 7B), which still mixes fine.

## Beat grid

Analysis looks at the whole track: it finds the tempo to a fraction of a BPM (no more rounding 127.95 to 128 and drifting), puts the beat lines on the kicks and snares rather than the off-beat hats or bass, and guesses which beat is bar 1. Tracks analysed by the old version get redone automatically in the background.

To fix a grid, click **GRID** on the deck:
- Type a BPM and press Enter, or use **−.01 / +.01** (Shift: 0.1), **÷2 / ×2**, or **TAP** along with the beat. The beat under the playhead stays put.
- **◀ / ▶** slide the whole grid 5 ms (Shift: 1 ms).
- Pause on a kick, then **BEAT HERE** snaps the nearest beat line to it, or **BAR 1 HERE** makes it the first beat of a bar.
- **RESET** goes back to the analysis.

Edits are saved with the track, re-analysis never overwrites them, and the library shows hand-edited BPMs in yellow.

## Library and analysis

- New tracks are analyzed in the background: BPM, beat grid, key and a 3-band waveform (blue = lows, orange = mids, white = highs). Results are cached.
- **BPM range** (default 88–175) decides whether half/double-time tracks read as, say, 140 or 70. Change it and every track is re-folded instantly.
- Titles and artists come from MP3 ID3 tags, otherwise from "Artist - Title" file names.
- Drag a row onto a deck, double-click it, press LOAD, or use Shift+← / Shift+→. Drop any audio file from Dolphin (or any file manager) straight onto a deck too.
- Hot cues and cue points are saved per track.
- Ctrl-click and Shift-click select several rows; Ctrl+A selects the whole list. Click the **#** header to go back to the list's own order.

## Playlists

The column on the left of the library is the tree: **Collection**, your **Playlists**, and any rekordbox **Devices**.

- **+** makes a playlist, **▤** a folder. Type a name and press Enter. Double-click to rename; hover and click **×** to delete (it asks first).
- Add tracks by dragging rows onto a playlist in the tree, or select them and use **Add to ▾**. Drag a playlist onto a folder to file it there, or onto the PLAYLISTS heading to take it back out.
- Inside a playlist, drag rows up and down to rearrange them, and press **Delete** (or **Remove from list**) to take them out. That only removes them from the playlist, never from your folder.
- Playlists are kept in Firefox, for this Cratebox on this computer. A track whose folder isn't connected shows greyed out, and comes back by itself once you reconnect the folder (matched by file name and size).
- **FLX4:** press the BROWSE knob to jump to the tree, turn it to walk the playlists (the list follows as you go), press again to go back to the tracks. LOAD still loads.

## rekordbox

**USB sticks and SD cards**: plug it in (CachyOS mounts it under `/run/media/<you>/`), then click **+ USB** under DEVICES. Every plugged-in drive with a rekordbox export opens; if there's none (or they're all open already), the folder dialog asks for the drive itself (the folder that holds `PIONEER`). Cratebox reads the rekordbox export on it: every track, the playlist tree, and for each track you load, rekordbox's own beat grid, phrases, hot cues A–H and first memory cue. These replace Cratebox's own analysis for that track, until you edit the grid or set cues yourself. Your edits stay on this computer.

- **Read-only.** Cratebox never writes to the stick, so it can't damage a set you've prepared for the club.
- **⧉** on a device playlist copies it into your own playlists. Those tracks still play from the stick, so they show greyed out when it's not plugged in.
- **×** on the device closes it. Cratebox remembers the drive, and opens it again by itself at Start when it's plugged in.

**rekordbox XML** (the **⋯** next to PLAYLISTS):

- **Import:** in rekordbox, *File → Export Collection in xml format*, then pick that file. Your playlists arrive in a folder called "rekordbox (date)". For tracks Cratebox can find in your music folder (matched by file name and size), it takes rekordbox's beat grid, key, hot cues and memory cue. Tracks it can't find appear greyed out in their playlists.
- **Export:** writes `cratebox-rekordbox.xml` with every track, its grid, key and cues, and all your playlists. rekordbox needs full file paths, so the first time it asks where your music folder is on this computer (for example `/home/jonah/Music`). Change it later under *Music folder path for export*. In rekordbox: *Preferences → Advanced*, set **Imported Library** (under rekordbox xml) to the file, tick **rekordbox xml** under *Preferences → View → Layout*, and the playlists show in the rekordbox xml tree (hit its reload button after re-exporting).

## Limits

- No key shift.
- rekordbox: USB/SD exports in the classic `export.pdb` format, which every rekordbox 5/6/7 USB export still includes. Device Library Plus (`exportLibrary.db`) alone isn't read. Playlists on a stick are read-only, and Cratebox doesn't read rekordbox 6/7's own encrypted `master.db` on your PC: use the XML export for that.
- rekordbox beat grids with tempo changes come in as one tempo (the most common one).
- Audio files must be something Firefox can decode: MP3, WAV, FLAC, OGG/Opus, and AAC/M4A (through the system's ffmpeg). Not AIFF.
- Beat grids assume a steady tempo. Live-drummed tracks will drift.

## Tests

The tests live in the repository's `mac-air` branch, not in the release zip. `python tests/make_tracks.py tests/music` builds four synthetic tracks with known tempos, keys and sections. `python tests/test_mac.py` runs the real launcher with a temporary home folder and checks the file bridge end to end: the folder dialog (and typing a path when there's no dialog program), the folder and a rekordbox USB in `/run/media` coming back after a restart, loading tracks off both, and that the bridge refuses other sites, other host names and paths outside home and the mount points; also that no request leaves the computer, and that nothing needs a Chrome-only feature.

The rest is the regular Cratebox suite at desktop sizes: `test_cratebox.py` (analysis, playback, FLX4 MIDI, LEDs, sync, loops, cues), `test_controllers.py`, `test_sync.py`, `test_layout.py [folder]` (the Air's screen full screen and windowed, a smaller window and external monitors; `CB_THEME=booth` and `CB_FOUR=1` for the Booth look and 4-deck mode), `test_fourdeck.py`, `test_record.py`, `test_audio_first.py`, `test_report.py`, `test_barcounter.py`, `test_theme.py`, `test_jog.py`, `test_headphones.py`, `test_fx.py`, `test_phrases.py` and `test_playlists.py`, plus `node tests/test_rekordbox.js` for the rekordbox file readers (`tests/fixtures/rekordbox_usb`, from pyrekordbox's test data, MIT licence). They run in headless Chromium and need `pip install playwright` and `playwright install chromium`.
