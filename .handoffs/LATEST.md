Task P1-2 (phases 1+2) · branch claude/ios-ai-dj-album-art-settings · base main 24d8b21 · head c81e2c0 (+ this memo) · PR https://github.com/zonahbear/Cratebox/pull/24 · tree clean after push

## 📍 Where We Stopped
- **Active Task:** P1-2 = redesign phases 1+2 in one build: grid order (your edit > Apple > rekordbox > Cratebox), 6-tab Settings with a toggle per AI DJ move, real-track CI (skips without TEST_TRACKS_TOKEN), squircle restyle + touch-only haptics, AI DJ v2 (bass swap / EQ handoff / COLOR sweep / cut, 4-32 bars, mix-in at CUE or Apple point, beat-matched 4-beat lead-in, MIX NOW within 2 bars, 3rd deck preload, loop bridge), plus USB ↔ local twins sharing Apple's analysis. Done and on TestFlight 56.1; waiting on Jonah's device check.
- **Current State:** plan doc "Cratebox iOS phase plan" (https://claude.ai/artifact/QR3rr5AKx69shwXZ6A7McS, rev 12) has phase 3 starting with SYNC-3 (beat drift) and phase 4 with LIB-4 (long-press menu, remove/hide).
- **Blockers/Bugs:** real-track tests skip until Jonah makes zonahbear/cratebox-test-tracks + TEST_TRACKS_TOKEN. The xcode-27 runner has no "iPhone 16 Pro Max" or "iPhone SE (3rd generation)" simulator: every earlier "16 Pro Max"/"SE" shot was really a 2622×1206 iPhone; 519eec8 creates the device or logs SIM MISSING (unverified, next ios.yml run).

## 🛠️ Environmental Verification
- Verified: ios.yml run 43308247504 (xcode-27) at a5e0f64: 139 tests, 0 failures, 4 skipped; `** BUILD SUCCEEDED **`; run red only because the screenshot step hit its 45-min timeout (raised to 60 in 519eec8). Evidence: ci-logs-preview 4e6c1ff ios-latest.txt. https://github.com/zonahbear/Cratebox/actions/runs/43308247504
- Verified: cratebox-iOS-suite testflight.yml run 43316996585 (xcode-27) at ab6b6c4: build 56.1, "UPLOAD SUCCEEDED with no errors" after three Apple 500s (ci-logs-testflight testflight.txt). Never appeared for Jonah; re-uploaded as 57.1 (run 43323997842, 22:56Z, clean "UPLOAD SUCCEEDED"). Then 58.1 (run 43327772421, suite f3ff54d = 372ed67): twin match built from stored results, so it works with the stick unplugged. Then 59.1 (run 43329503708, f04a8cb = 0490d19): Apple grid adoption for unanalysed tracks. OPEN: Jonah still sees re-analysis + only 15 gridded tracks after USB copy (see GLOBAL_PLAN P1-2 notes).
- Re-run: Actions → ios.yml → this branch, runner xcode-27, devices "iPhone 16 Pro Max,iPad Pro 13-inch (M4),iPhone SE (3rd generation)".

## 📦 Changes Introduced in This Session
- CrateboxKit AutoMix.swift (+Tests): 4 transition kinds, PlanOptions, cue/mix-point aware planning, `within` for MIX NOW. RealTrackTests.swift (new). Core.swift: setLoop/exitLoop.
- App/AIDJ/AIDJ.swift, AIDJView.swift: AI DJ v2 controller (lead-in, 3rd deck preload, loop bridge, AIDJMoves toggles).
- App/AppleMusic.swift: grid order key cb.grid.order; twin sharing (source(), twinKey) so a copied track isn't analysed again.
- App/Views/SettingsView.swift (6 tabs + AI moves), Theme.swift (squircles, FaderCap, Haptics), all views: continuous corners.
- .github/workflows/ios.yml: real-track step, no make_tracks, SE settings shots, simulator create/skip, 60-min screenshots.
- apps/ios-suite/AGENTS.md, .agent/GLOBAL_PLAN.json (P1-2, SYNC-3, LIB-4).

## 2026-11-13 additions
- 61.1 (suite 44df793): analysis failure reasons + Try again; "Analyse everything again" asks first; BPM range change skips rekordbox-gridded copies.
- 62.1 FAILED to compile (SettingsView missing `playlists` EnvironmentObject); fixed in c7b97fd.
- 63.1 (suite f5ec011, verified "UPLOAD SUCCEEDED"): Apple analysis only on request (Settings → AI whole library / playlist / selected track; long-press Analyse), toggle "Analyse while tracks play" (cb.apple.whilePlaying).
- 64.1 cancelled; 65.1 (suite 57905ba = monorepo d8812b2, verified "UPLOAD SUCCEEDED" 00:29Z, also: Sync recopies files deleted from From USB, folder restarted if deleted): root cause of "re-analysis + 15 gridded tracks": AppModel rescans folders at launch / addFolder scans, listing copied files with no grid before UsbCopy.addCopied runs; addCopied kept those. Now addCopied applies rekordbox's grid (Library.applyRekordbox) and UsbCopy.regrid = "Re-sync grids from <stick>" (Settings → Library & USB, stick long-press).
- 68.1 (suite 7f53270 = monorepo c81e2c0, verified "UPLOAD SUCCEEDED" 02:17Z; 66/67 cancelled): leaving the app pauses Apple analysis (no false failures), BGContinuedProcessingTask (id <bundle>.analysis, Info.plist BGTaskSchedulerPermittedIdentifiers + processing mode) for background runs, transient errors retried 3x, Try again re-queues; From USB never marked offline; copies saved every 10 tracks + beginBackgroundTask; failed Cratebox analysis keeps an existing (rekordbox) BPM. 56.1 (lost upload) surfaced in TestFlight at 01:24Z as "newest": Jonah should expire it.
- OPEN (02:16Z): Jonah reports NO copied (From USB) tracks play, even after force-quit, on 65.1 (probably); imported tracks play. Asked for the deck's error text and whether the file plays in Files. Not reproduced; cause unknown.

- 70.1 (suite 1bf54a0 = monorepo d7026bb, verified "UPLOAD SUCCEEDED" 06:42Z; 69 cancelled): AI DJ hybrid (Core.onUserMixer: a fader/EQ/CFX you move during a mix is yours until it ends), Settings → AI "Analyse the USB <name>", Sync/Copy all mirror the stick's rekordbox playlists (UsbCopy.mirrorPlaylists, folder named after the stick, add-only), missing files skipped not failed (AppleMusic.missingNow), MetricKit crash reports (App/CrashLog.swift → Files/Crash reports), Library in the mode menu, Apple results shared by file twin OR artist+title+length ±2 s (Stamp.meta/dur, backfilled), Library.preferLocal de-duplicates stick + copies in AI DJ pool/picker.
- Suite .github/workflows/crashes.yml + .github/scripts/testflight_crashes.py (3a9200c, branch only): can't be dispatched until on suite main (GitHub rule); waiting on Jonah's OK.
- OPEN: fader-touch crash during AI DJ transition (no stack yet); "can't get back to library" (exact spot unknown, Library menu entry added); copied tracks not playing (need deck error text).

- 73.1 (suite af35146 = monorepo e7376b0, verified "UPLOAD SUCCEEDED" 07:28Z; 71/72 cancelled): phone messages in StatusBubble (Theme.swift) over the waveforms/library, not the top bar; UsbCopy.result shown under Sync in Settings; copy() copies what fits when space is short (Jonah's Sync said "Not enough space": deleted copies sit in Files → Recently Deleted); Settings 🐞 → ReportView (App/Report.swift): AppLog session log (Documents/Logs), description + screenshot → GitHub issue on zonahbear/Cratebox, key asked once and kept in Keychain (GitHubKey), log + screenshot pushed to branch `reports` (reports/ios/<time>/), fallback = prefilled new-issue URL.
- AIDJ-3 added to GLOBAL_PLAN + plan doc (Auto vs Hybrid modes, no tempo moves while fading in; needs go).

## ⏭️ Precise Next Steps for Incoming Model
0. [ ] On Jonah's OK push crashes.yml + script to suite main, run it, read ci-logs-crashes:crashes/_run.txt. Get a crash stack for the fader crash. Diagnose copied tracks not playing (deck error text, Files playback). Then Jonah: install 68.1 (or restore From USB from Files → Recently Deleted), plug stick, Re-sync grids, report AI DJ track count.
1. [ ] Jonah checks 58.1 on his phone (MIX NOW, transitions, Settings tabs, haptics, copied-track analysis). If 56.1 never appears, re-run suite testflight.yml (runner xcode-27).
2. [ ] Next ios.yml run: confirm SIM lines show a real 16 Pro Max / SE (or SIM MISSING), check SE Settings rail shots.
3. [ ] Phase 3 on Jonah's go, starting with SYNC-3: a synced real-track test through a tempo glide that logs drift (SAVEME, master tempo on), then fix.
4. [ ] When Jonah has made the private test-tracks repo + TEST_TRACKS_TOKEN: copy the 22 picks (/mnt/project-files/test-tracks/picks.md) with their ANLZ files, write manifest.json.
5. [ ] Port phases 0-2 to personal/heat when Jonah wants it.
