Task UI-0 (+ USB-2) · branch claude/ios-ai-dj-album-art-settings · base main 24d8b21 · head 2001708 (+ this memo) · PR https://github.com/zonahbear/Cratebox/pull/24 · tree clean after push

## 📍 Where We Stopped
- **Active Task:** UI-0 = redesign phase 0 (squashed MASTER box → "FLX4" pill, CUE/MST + MASTER labels fixedSize, remaining time one line, album art slot = lane height on the left, Settings tabs as a full-height left rail) and USB-2 (USB → device copy: all / playlist / selected, Sync in Settings → USB, twin rule = file name + size). Done and on TestFlight 55.1; waiting on Jonah's device check.
- **Current State:** Jonah approved a 6-tab Settings (Audio, Decks, Controller, Look, Library & USB, AI) and a grid order (user edit > Apple > rekordbox > Cratebox) for the next phase. A new multi-phase plan (phases 1-5 + release prep) is out for his approval as a Claude Doc ("Cratebox iOS phase plan"). Rule: one CI + one TestFlight per phase.
- **Blockers/Bugs:** album art fix and the SE Settings rail are not visible in this CI's screenshots (demo tracks have no art; default devices only). Real-track CI needs Jonah's private test-tracks repo + TEST_TRACKS_TOKEN.

## 🛠️ Environmental Verification
- Verified: ios.yml run 43288201356 (xcode-27) at 2001708: 129 tests, 0 failures; `** BUILD SUCCEEDED **`; iPhone 16 Pro Max screenshots on ci-logs-preview 3cfb3d7 show the FLX4 pill, full CUE/MST label, one-line times. https://github.com/zonahbear/Cratebox/actions/runs/43288201356
- Verified: cratebox-iOS-suite testflight.yml run 43295586211 (xcode-27) at 5b736b9: "UPLOAD SUCCEEDED", build 55.1 (ci-logs-testflight testflight.txt).
- Earlier run 43277729733 hung in screenshots (lost runner, logs 404); cancelled. Jonah: no Intel fallback, retry on xcode-27 only.
- Re-run: Actions → ios.yml → this branch, runner xcode-27 (add an iPhone SE to `devices` for the Settings rail shot).

## 📦 Changes Introduced in This Session
- ios/App/UsbCopy.swift (new): USB → Documents/From USB copy, .part then move, free-space check, keeps rekordbox grid/key.
- ios/App/Library.swift: twins(), twinKey, addCopied, url(of:) for the From USB folder.
- ios/App/Devices.swift: eject refuses while copying from that stick.
- ios/App/Views/SettingsView.swift: left tab rail, title bar, USB → Copy to this device section.
- ios/App/Views/LibraryView.swift: Copy toolbar button, row/playlist/device copy menus, progress + Stop.
- ios/App/Views/MixerView.swift, DeckView.swift: phase 0 layout fixes.
- apps/ios-suite/AGENTS.md: Intel fallback line removed. .agent/GLOBAL_PLAN.json: UI-0, USB-2.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah checks 55.1 on his phone (album art gap, Settings rail on a small phone, USB copy/Sync).
2. [ ] Wait for Jonah's OK on the "Cratebox iOS phase plan" doc, then start phase 1 (grid order, 6-tab Settings + AI tab, real-track CI, restyle, analysis memory).
3. [ ] When Jonah has made the private test-tracks repo + TEST_TRACKS_TOKEN: copy the 22 picks (/mnt/project-files/test-tracks/picks.md) from "C:\Users\zonah\Desktop\usb backup", drop make_tracks.py from ios.yml.
4. [ ] Port phase 0 to personal/heat when Jonah wants it there.
