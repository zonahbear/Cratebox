Task USB-3 + BUG-2 (USB copies keep rekordbox data; copies broken after restart) · branch ios-suite/usb-copy-rekordbox · base main df8daab · head = the commit carrying this memo · PR none yet (Jonah merges) · tree clean after push

## 📍 Where We Stopped
- **Active Task:** USB-3 / BUG-2 done in code, TestFlight 77.1 building (suite repo, same branch name, run 77, runner xcode-27).
- **Current State:** Jonah's reports #28/#29 (76.1): after Sync, eject and restart, no copy loaded ("file isn't there",
  avfaudio 2003334207) and the analysis count ran to 13000+. Cause, read from the logs + code (not reproduced on a device):
  `Library.scan` built `rel` with `u.path.replacingOccurrences(of: root.path + "/", …)`; the enumerator returned
  `/private/var/…` for a root of `/var/…`, so `rel` stayed absolute, every copy got a new id pointing at no file and lost its
  rekordbox data ("From USB: 574 tracks, 574 new" at launch). Then AppleMusic found the missing files, rescanned From USB,
  the library change re-kicked it 4 s later, and each `merge` appended all 574 to the analysis queue again.
- Fix: `Library.plainPath` (symlinks resolved, "/private" stripped) for scan paths; queue dedupe in merge/addCopied;
  AppleMusic rescans From USB at most once a minute. Sync now copies the stick's whole PIONEER folder to
  From USB/<stick>/PIONEER (`UsbCopy.copyPioneer`), and `UsbCopy.rehydrate` gives copies rekordbox's title, artist, key,
  length, grid, phrases and cues from it (runs after every From USB scan, copy, Sync and Re-sync grids).
- **Branch naming:** a remote branch literally named `ios` exists, so git refuses `ios/<feature>`; used `ios-suite/`.
- **Blockers/Bugs:** Jonah must Sync once with the stick in so old copies get PIONEER. Album art for copies not read yet.
  BUG-1 (fader crash), BUG-3, BUG-4, BUG-5 still open.

## 🛠️ Environmental Verification
- No local Swift compiler. Compile + upload check = suite testflight.yml run 77
  (https://github.com/zonahbear/cratebox-iOS-suite/actions/runs/43399854232); see LATEST breadcrumb line for the result.
- `python3 -m json.tool .agent/GLOBAL_PLAN.json` PASSED (verified).

## 📦 Changes Introduced in This Session
- apps/ios-suite/ios/App/Library.swift: plainPath, scan rel fix, queue dedupe, rehydrate hook, TrackRecord.anlz/rbTags, readTags keeps rekordbox names.
- apps/ios-suite/ios/App/UsbCopy.swift: copyPioneer, rehydrate, copyANLZ, Sync with nothing missing copies PIONEER + rehydrates, Re-sync grids too.
- apps/ios-suite/ios/App/Devices.swift: anlzURL for copies. AppModel.swift: copies with ANLZ load like stick tracks (cues).
- apps/ios-suite/ios/App/AppleMusic.swift: From USB rescan at most once a minute.
- TODO.md, .agent/GLOBAL_PLAN.json (BUG-2 → review, USB-3 new), this memo, LATEST.md, .claudes/breadcrumbs.md.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: install 77.1, plug the stick in, Settings → Sync once, eject, restart; check copies load with grid/cues and the
       analysis count stays sane. Report with the ladybug.
2. [ ] Agent: open a PR for ios-suite/usb-copy-rekordbox titled "USB-3: …" when Jonah wants it on main.
3. [ ] Agent: album art for copies from From USB/<stick>/PIONEER/Artwork (PDBTrack.artwork).
