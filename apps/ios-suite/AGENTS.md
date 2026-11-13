# AGENTS.md: Cratebox Suite (iOS)

> Monorepo (2026-11-11): this folder is `apps/ios-suite/` in zonahbear/Cratebox. Paths below are relative to it; workflows
> live in the root `.github/workflows/`. Start at the root [AGENTS.md](../../AGENTS.md).

Read this first. Keep it short.

## Rules

- **Device sizes:** [`docs/device-sizes.md`](docs/device-sizes.md) is the only source for screen sizes, scales, safe
  areas and Display Zoom sizes, for the shipping app and for the personal HEAT build (`personal/heat`). Never estimate a
  size. If a device is missing, measure it (ios.yml, `measure: true`) and add it there first.
- HEAT never goes into the shipping app (`com.zonahbear.cratebox.suite`). It lives only on `personal/heat`
  (`com.zonahbear.cratebox.heat`), which never merges back.
- Installs only via TestFlight (testflight.yml) and the App Store. macOS CI is manual-only. ios.yml defaults to the `xcode-27` runner
  (Apple Silicon, iOS 27 SDK, needed for AI mode's Music Understanding). No Intel fallback (Jonah, 2026-11-12): if a run stalls, retry on xcode-27.
- AI features stay behind Settings → AI mode (`cb.ai`, off by default) and on-device only. See breadcrumbs 2026-11-11.
- Xcode 27: observed state read only inside a `GeometryReader` closure doesn't redraw. Let the reader measure and hand
  the size to a child view that reads the state in its own body (PhoneFrame, PadFrame, BridgeFrame, USBPanes), or
  read the values in `body` before the reader. ios.yml's `_redraw` screenshot checks it (`-demo -redraw`).
- AI DJ (`App/AIDJ/`, decisions in CrateboxKit `AutoMix.swift`): a fourth suite mode behind AI mode, decks 1 and 2
  (deck 3 only with Settings → AI → Third deck, for preloading; never three heard). Kinds in `AutoMix.Transition`
  (levels + lengths); each move has a toggle (`AIDJMoves`, keys `cb.aidj.*`). One bass line at a time is tested.
- Grid order (Jonah, 2026-11-12): a grid set in Cratebox (`gridManual`) > Apple's (AI mode) > rekordbox's > Cratebox's
  analysis; `AppleGridMode` (`cb.grid.order`). A CUE you set is AI DJ's mix-in point, ahead of Apple's.
- Haptics only from touch handlers (`Haptics` in Theme.swift), never from model/MIDI changes.
- Real-track tests: `RealTrackTests` read `CRATEBOX_REAL` (private repo zonahbear/cratebox-test-tracks via the
  TEST_TRACKS_TOKEN secret). No synthetic test tracks in CI (Jonah).

## Breadcrumbs

Session notes and next steps: [`.claudes/breadcrumbs.md`](.claudes/breadcrumbs.md).
