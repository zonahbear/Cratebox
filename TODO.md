# TODO.md: everything still open (2026-11-13)

One human-readable list of unfinished work, for any model picking this up cold. The machine-readable copy is
[.agent/GLOBAL_PLAN.json](.agent/GLOBAL_PLAN.json) (task ids in brackets below); where they disagree, the plan JSON
wins for status and this file wins for order. Read [.handoffs/LATEST.md](.handoffs/LATEST.md) and
[.agent/SYSTEM_PROMPT.md](.agent/SYSTEM_PROMPT.md) first. Tick items here and in the JSON in the same PR.

Legend: **[go]** = waits for Jonah's go, don't start it. **[Jonah]** = only Jonah can do it (secrets, repos, device,
decisions). Everything else an agent can start.

## Where the code is right now (read this before touching iOS)

- **iOS code is on `main`** since PR #24 merged (2026-11-13 08:25Z, d249ca3): AI DJ v2, album art, 6-tab Settings,
  redesign phases 0-2, USB copy, Apple-analysis sharing/backup, Report a problem. New iOS work: a branch cut from `main`
  named `ios/<feature>`, one per area, follow-ups on it.
- **TestFlight is still built from the old repo** `zonahbear/cratebox-iOS-suite`, because the monorepo lacks the signing
  secrets (MONO-4). Every iOS change is committed in the monorepo, then the `apps/ios-suite/ios/` tree is copied to a suite
  branch with the same name and its `testflight.yml` is run (runner `xcode-27`). Latest: **TestFlight 76.1** = suite
  `0c6f8f0` (branch `claude/ios-ai-dj-album-art-settings`) = monorepo `ddc6678`. Suite `main` is old (a99518c); don't build from it.
- The phase plan doc is https://claude.ai/artifact/QR3rr5AKx69shwXZ6A7McS ("Cratebox iOS phase plan", rev 13).
  Its phase names are used below.

## Rules that bite (full list: SYSTEM_PROMPT.md)

- Branches: descriptive `<area>/<short-feature>` (`ios/ai-dj`, `web/match-column`, `docs/handoff-todo`), never
  `claude/project-thread-xxxx`. Small follow-ups go on the open branch for that area, not a new branch.
  Never touch `personal/heat` naming; it never merges into `main`.
- No HEAT in the shipping iOS app. iOS ships only through signed TestFlight / App Store; no sideloading, ever.
- CI: Xcode 27 on Apple Silicon (`xcode-27`) only, no Intel fallback; if a run stalls, cancel and retry on xcode-27.
  One CI run and one TestFlight build per phase. Workflows stay `workflow_dispatch`.
- Real tracks only for analysis/AI DJ checks: Jonah's rekordbox USB (D:), or `C:\Users\zonah\Desktop\usb backup` if D:
  is missing. No synthetic tracks in iOS CI. Never commit music (this repo is public).
- On-device only: no cloud services. No secrets in the repo or in these docs.
- Device sizes only from `apps/ios-suite/docs/device-sizes.md`.
- Grid priority: grid set in Cratebox > Apple (AI on, supported device) > rekordbox > Cratebox analysis. A CUE you set
  beats Apple's mix-in point.

## 1. Waiting on Jonah

- [ ] [Jonah] Install TestFlight 76.1 and check it on the phone: MIX NOW, transitions, 6-tab Settings, haptics, Sync,
      AI DJ track count, Apple analysis count (574 not 1146), `Cratebox/Apple analysis/` backup on the stick.
      Expire the stray 56.1 build in TestFlight.
- [ ] [Jonah] Create private repo `zonahbear/cratebox-test-tracks` + read-only `TEST_TRACKS_TOKEN` secret (CI-1). Until then
      `RealTrackTests` skip (and say so).
- [ ] [Jonah] OK to put the crash-fetch workflow (`crashes.yml` + `.github/scripts/testflight_crashes.py`, suite commit
      3a9200c) on cratebox-iOS-suite `main` (CI-2). GitHub only dispatches workflows that exist on the default branch.
- [ ] [Jonah] Say which rekordbox grids he fixed by hand (hand-fixed grid = ground truth; the export doesn't mark them).
- [ ] [Jonah] Analysis memory: OK to analyse at a lower sample rate? (MEM-1)
- [ ] [Jonah] Touch mode redesign: phase 4 or drop it? (TOUCH-1)
- [ ] PR #20 (MONO-6 port of suite 263608d): check whether #24 already carries it, then Jonah merges or closes it.
      Jonah: close obsolete PR #3 and delete merged branches (MONO-9).
- [ ] [Jonah] MONO-4: re-add secrets in this repo (TestFlight six, LEGACY_RELEASE_TOKEN). Then MONO-10 (stop pushing
      iOS to the suite repo), MONO-11, MONO-8 (archive old repos, never delete).
- [ ] [Jonah] MONO-5: Cloudflare production build log for the failure on main 24d8b21.

## 2. Open iOS bugs (reproduce first, put the repro in your memo)

- [ ] BUG-1 Crash when touching a fader during an AI DJ transition. Cause unknown, no stack yet. Get it from the crash
      fetch (CI-2) or from Files → Cratebox → Crash reports (MetricKit, `App/CrashLog.swift`).
- [ ] BUG-2 Copied ("From USB") tracks don't play (Jonah, 02:16Z on ~65.1; imported tracks play). Unconfirmed on later
      builds. Need the deck's error text and whether the file plays in Files.
- [ ] BUG-3 "Can't get back to the library" from some screen. Exact spot unknown; a Library entry was added to the mode
      menu in 70.1 as a stopgap. Ask Jonah where.
- [ ] BUG-4 Some tracks show no tags (e.g. "1. AFTERGLOW": file-name title, no artist, no art). Find out whether it's a
      copied or imported track and why tags weren't read.
- [ ] BUG-5 Launch log noise: "File Provider Storage doesn't look like a rekordbox USB" (an old saved non-stick folder is
      re-opened every launch). Harmless; stop re-asking.
- [ ] Next ios.yml run: confirm the SIM lines show a real iPhone 16 Pro Max / iPhone SE (or `SIM MISSING`) and check the
      SE Settings-rail screenshots (519eec8 is unverified).

## 3. Phases 1+2 remainder (P1-2, mostly shipped in 56.1-76.1)

Done: grid order, 6-tab Settings with per-move AI toggles, real-track CI step (skips without token), squircle restyle +
touch-only haptics, AI DJ v2 mixing brain (bass swap / EQ handoff / COLOR sweep / cut, 4-32 bars, phrase and CUE mix
points, beat-matched lead-in, MIX NOW within 2 bars, optional 3rd deck, loop bridge), USB copy + Sync, shared and backed-up
Apple analysis.

- [ ] CI-1 Copy the 22 tough tracks (`/mnt/project-files/test-tracks/picks.md` in the Claude project; source = desktop USB
      backup) with their PIONEER/ANLZ files into the private repo, write `manifest.json`. Needs CI-1 repo + token first.
- [ ] MEM-1 [go] Analysis decodes the whole track at full quality (~320 MB peak). Decide (lower sample rate / streaming),
      measure the saving and check grids stay the same on real tracks before shipping.

## 4. Phase 3: AI DJ experience

- [ ] SYNC-3 (first) Beat drift in AI mode / sync through tempo changes (track SAVEME, master tempo on). Measure first:
      a synced real-track test through a tempo glide that logs drift. Suspects (unverified): constant-BPM Apple grid fit,
      lockPhase cap while AI DJ glides, keylock playhead at rate != 1, `AIDJ.finish` snapping B to its own tempo.
- [ ] AIDJ-4 Continuous handoff: AI DJ ↔ performance mode without the music stopping.
- [ ] AIDJ-5 Better AI DJ card/player: now playing, next, time to next mix, the queue.
- [ ] IOS-2 Lock screen / Control Center / Now Playing (MPRemoteCommandCenter; none in the app yet): shows the top deck;
      play/pause = all playback; back = restart song; next = skip with no transition; custom = mix in next at the next
      good point. Needs a check on Jonah's phone.
- [ ] AIDJ-6 👍/👎 after each transition, optional why tags (off-beat / clash / too long / bad timing), skip right after a
      mix = soft 👎, on-device log of transition features, slow bandit-style weight tuning, "reset what it learned".
      Nothing leaves the device. (No rating code exists yet.)
- [ ] CI for phase 3: unit tests for the rating tuner and remote commands, screenshots of the card and rating prompt.

## 5. Phase 3/4: AI DJ Auto vs Hybrid (AIDJ-3) [go]

- [ ] Research basic DJ technique first (phrase matching, bass swaps/EQ handoffs, energy management, tempo riding
      through breakdowns and outros); write the findings into the PR before building.
- [ ] Two modes: **Auto** (AI does all the mixing) and **Hybrid** (you're never locked out of a control during a
      transition). 70.1 already has the first hybrid step (`Core.onUserMixer`: a control you move is yours until the mix ends).
- [ ] Tempo rule: no tempo change while the incoming track fades in; tempo moves only on a down-energy section or as the
      outgoing track fades out. Today AI DJ glides deck A's pitch through the whole mix, which breaks it.

## 6. Phase 4: performance tools and library

- [ ] LIB-4 Long-press menu on a library track: remove from this device, hide from library, edit title/artist, add to a
      playlist, load to deck 1-4, queue for AI DJ. Never deletes from a stick or the user's own folders.
- [ ] ALL-1 [go] Key sync and key shift on pads and controller buttons (FLX4 first; web has KEY SHIFT, iOS has only the
      `mode:keyshift` pad mapping, no feature).
- [ ] SUG-1 Next-track suggestions: a "play next" panel on top of the MATCH sort iOS already has.
- [ ] Browser and library polish (old redesign phase 2 of the Apple-native review).
- [ ] TOUCH-1 [go] Touch mode redesign (big tap-cut EQ), only if Jonah says so. Show screenshots before shipping visuals.

## 7. Phase 5: waveform and jog visuals [go]

- [ ] UI-5 Old redesign phase 3: waveform and jog visuals, only after profiling (glows/shadows on the 60 Hz Canvas and
      JogView cost frame time). Liquid Glass needs `#available(iOS 26)`; every width change needs the 568x320 SE check.

## 8. Release prep (needs Jonah's decisions)

- [ ] REL-1 Paywall: 7-day trial, then $7.77/month or $120 lifetime. Check in App Store Connect whether $7.77 is a valid
      price point (unverified).
- [ ] REL-2 Beta preload tracks: CC0 shortlist exists; waiting on Jonah's picks.
- [ ] REL-3 App Store submission, after the paywall, on Jonah's go.

## 9. Monorepo, CI and agent tooling

- [ ] MONO-7 kiosk-latest not rebuilt from this repo (no new ISO for app changes; only when the OS itself changes).
- [ ] MONO-10 After MONO-4: build TestFlight here, stop pushing to cratebox-iOS-suite.
- [ ] ALL-2 Mirror check for the web files copied into apps/ios-suite (cratebox.html, sw.js, tools/*.js, tests/).
- [ ] ALL-3 One verification entry point per app (prereqs, pinned tool versions, right tests).
- [ ] ALL-4 [Jonah] Fresh-session smoke check of each tool's entry file (Codex, Claude Code, Gemini CLI, Antigravity,
      Copilot): ask "what are the hard rules and the active task?" from the root and from an app folder.
- [ ] ALL-5 Cheap Ubuntu metadata check (GLOBAL_PLAN ids/deps, LATEST == newest memo, no conflict markers).
- [ ] CI-3 [go] Self-hosted arm64 Xcode 27 runner on Jonah's new 14" MacBook Pro (M4 Pro), when he's ready.

## 10. Web and Linux

- [ ] ANA-1 Bar 1 half a beat off rekordbox on ~7% of real tracks; tempo at 4/3 or 2/3 on ~2%. Measure on real stick
      tracks; Jonah's ears decide. The Swift port didn't get the 2026-11-10 web bar-1 change.
- [ ] Web: see `apps/web/AGENTS.md` "Open work" (iOS catch-up branch `claude/project-thread-0pjrfq`; key controls not in
      the Mixxx maps; no OneLibrary, tempo-change grids or AIFF in web).
- [ ] LNX-1 Linux: port web's rekordbox playlist writer (same protections as web/iOS: opt-in, backup first, read-back,
      refuse after a re-export). Linux is behind web's 1.1.x changes; check the web CHANGELOG first.
- [ ] [Jonah] Linux/Windows hardware checks: real FLX4, real sound card, WASAPI latency, Cratebox OS sleep/wake, full
      install, headphones (`apps/linux/AGENTS.md`).

## 11. Ideas backlog (not planned, needs a go)

- [ ] IDEA-1 AI DJ trainer "Learn" mode: the AI hands controls over to you step by step as you get better.

## Parked

Left out on purpose (Jonah, 2026-11-13): truecurve / HEAT work (MONO-2, MONO-3, HEAT-1, HEAT-2, porting phases to
`personal/heat`), the Apple Watch mic → PC rekordbox app (IOS-1) and rekordplayer. They stay in GLOBAL_PLAN; don't start them.
