Task P1-2 (phases 1+2) · branch claude/ios-ai-dj-album-art-settings · base main 24d8b21 · head 5b88848 (+ this memo) · PR https://github.com/zonahbear/Cratebox/pull/24 · tree clean after push

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
- 64.1 (suite 4476341 = monorepo 5b88848, building at 00:21Z): root cause of "re-analysis + 15 gridded tracks": AppModel rescans folders at launch / addFolder scans, listing copied files with no grid before UsbCopy.addCopied runs; addCopied kept those. Now addCopied applies rekordbox's grid (Library.applyRekordbox) and UsbCopy.regrid = "Re-sync grids from <stick>" (Settings → Library & USB, stick long-press).

## ⏭️ Precise Next Steps for Incoming Model
0. [ ] Confirm 64.1 uploaded (ci-logs-testflight testflight.txt); Jonah: install, plug stick, Re-sync grids, report AI DJ track count.
1. [ ] Jonah checks 58.1 on his phone (MIX NOW, transitions, Settings tabs, haptics, copied-track analysis). If 56.1 never appears, re-run suite testflight.yml (runner xcode-27).
2. [ ] Next ios.yml run: confirm SIM lines show a real 16 Pro Max / SE (or SIM MISSING), check SE Settings rail shots.
3. [ ] Phase 3 on Jonah's go, starting with SYNC-3: a synced real-track test through a tempo glide that logs drift (SAVEME, master tempo on), then fix.
4. [ ] When Jonah has made the private test-tracks repo + TEST_TRACKS_TOKEN: copy the 22 picks (/mnt/project-files/test-tracks/picks.md) with their ANLZ files, write manifest.json.
5. [ ] Port phases 0-2 to personal/heat when Jonah wants it.
