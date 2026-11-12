# Current Workspace State

Memo 2026-11-12 08:38Z · agent: claude (coder) · task ART-1 · branch claude/project-thread-087u0n · base claude/project-thread-5yci11 (PR #21, AI DJ) · head see `git log` (after a5cddaa) · PR https://github.com/zonahbear/Cratebox/pull/22 · tree clean after push

## 📍 Where We Stopped
- **Active Task:** ART-1, album art on iOS. Library rows show rekordbox's icon (stick) or the file's cover. Decks show the file's full-size cover, then rekordbox's a1_m/a1. A grey record stands in when there's no art. There's no setting (Jonah).
- **Current State:** code done; ios.yml run 38 (43182222019, a5cddaa) passed its Kit tests step; screenshots still running at memo time.
- **Blockers/Bugs:** not checked on Jonah's real stick (device not connected) or a device. Workers Builds red = MONO-5 (not this PR).

## 🛠️ Environmental Verification
- Reported, not yet verified at memo time: ios.yml run https://github.com/zonahbear/Cratebox/actions/runs/43182222019 at a5cddaa. The Kit tests step passed, the screenshots step was running. Re-run: Actions → ios.yml on the branch, devices "iPhone SE (3rd generation),iPhone 16 Pro Max,iPad mini (A17 Pro)".
- Not run locally: no Swift toolchain in the cloud session.

## 📦 Changes Introduced in This Session
- apps/ios-suite/ios/CrateboxKit/Sources/CrateboxKit/PDB.swift: artwork table + `PDBTrack.artwork`, `bigArtwork`.
- apps/ios-suite/ios/CrateboxKit/Tests/CrateboxKitTests/PDBTests.swift: `testReadsArtwork`.
- apps/ios-suite/ios/App/Artwork.swift: new (loader, cache, ArtworkView, RecordGlyph).
- apps/ios-suite/ios/App/Views/DeckView.swift, LibraryView.swift, BrowserView.swift: covers in lanes, deck, rows.
- apps/ios-suite/.claudes/breadcrumbs.md, .agent/GLOBAL_PLAN.json (ART-1).

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Confirm run 43182222019 green; look at the SE / 16 Pro Max / iPad mini screenshots (record glyph left of the lanes).
2. [ ] Tell the Settings-tabs thread (PR #23) that #22 is final, so it rebases and uploads the one combined TestFlight build.
3. [ ] With Jonah's computer connected: read D:\PIONEER\rekordbox\export.pdb's artwork table, check paths exist under D:\PIONEER\Artwork.
4. [ ] Optional (ask Jonah): album art in web and Linux.
