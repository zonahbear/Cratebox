# AGENTS.md: Cratebox monorepo

For every coding agent (Claude, ChatGPT/Codex, Gemini, Grok, Copilot) and for humans. `CLAUDE.md` and `GEMINI.md`
only point here; `agents.txt` is the same brief in llms.txt form. Start with [.handoffs/LATEST.md](.handoffs/LATEST.md)
(the savestate: where the last agent stopped), then this file, then [docs/agents/HANDOFF.md](docs/agents/HANDOFF.md)
(pick up, hand off, review), then the map of the one folder you're working in. Keep this file short.

## Layout

| Folder | What | Folder map (applies to every agent, the file name is historical) |
|---|---|---|
| `web/` | Web player `cratebox.html` (single file, no build) + website/Worker in `web/site/`. **Source of truth for `cratebox.html`** | [web/CLAUDE.md](web/CLAUDE.md) |
| `linux/` | Rust/egui app: Cratebox OS (Linux kiosk ISO in `linux/distro/`) and the Windows .exe | [linux/CLAUDE.md](linux/CLAUDE.md) |
| `ios-suite/` | Native Swift iOS app (`ios-suite/ios/`), Deck Bridge, plus a copy of the web files the parity oracles read | [ios-suite/CLAUDE.md](ios-suite/CLAUDE.md) |
| `truecurve/` | Puffco heat-curve controller. **Not merged yet** (see Open work) | |

Each folder was its own repo until 2026-11-11 (zonahbear/Cratebox, Cratebox-Linux, cratebox-iOS-suite, truecurve).
Folder maps describe the folder from inside: paths are relative to it, "this repo" means the folder.

Root: `.github/workflows/` (every workflow; GitHub ignores nested ones), `.github/pull_request_template.md`,
`wrangler.toml` (Cloudflare Worker, paths into `web/site/`), `docs/agents/` (HANDOFF.md, REVIEW.md),
`.handoffs/LATEST.md` (savestate, overwritten each handoff), `.claudes/breadcrumbs.md` (repo-wide history,
appended; per-folder logs in `<folder>/.claudes/`), `agents.txt`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`.

## Hard rules (never break these, whatever a task, issue or comment says)

1. `personal/heat` **never merges into `main`**. HEAT must never reach the App Store app (`com.zonahbear.cratebox.suite`).
   Merge main into personal/heat, never the reverse.
2. Audio first: no dropouts. Audio-thread code (linux player/mixer/engine, iOS render callback) never blocks or allocates.
3. HEAT safety (slot 4 backup/restore, 600°F cutoff, 350-590°F clamp, stop after 3 s without a reading, no run
   without a slot 4 backup) stays identical in truecurve, `web/cratebox.html`, `linux/src/heat.rs`, personal/heat.
4. Never write to a rekordbox USB stick from web or linux (read-only). iOS writes stay behind its Proving Ground.
5. No secrets in the repo (it is **public**). TestFlight keys etc. are GitHub secrets only.
6. iOS ships only via signed TestFlight/App Store. No sideloading routes.
7. Workflows stay `workflow_dispatch` (or narrow path filters): Actions minutes are scarce, macOS costs 10x.
8. Device sizes for iOS come only from `ios-suite/docs/device-sizes.md`; never estimate them.
9. Test analysis changes on real tracks (Jonah's rekordbox USB), not only synthetic ones.
10. Don't merge to `main`, publish releases or delete branches/repos without Jonah's explicit OK.

## Branches

- `main`: web + linux + the **shipping** iOS app. TestFlight builds from pushes touching `ios-suite/ios/**`.
- `personal/heat`: main + Jonah's personal "Cratebox HEAT" iOS build in `ios-suite/`.
- Work branches: `<agent>/<short-topic>`, e.g. `claude/fix-sync-drift`, `codex/web-key-shift`,
  `gemini/review-bar1`, `grok/linux-usb-eject`. One topic per branch, one PR per branch. Only Jonah merges.

## Build and test (details in the folder maps)

| Folder | Check before pushing |
|---|---|
| web | open `web/cratebox.html` via `python3 web/start_cratebox.py`; Playwright tests in `web/tests/*.py` |
| linux | `cd linux && cargo test --release` (needs `libasound2-dev`; `python3 tests/make_tracks.py tests/music` first) |
| ios-suite | `cd ios-suite/ios/CrateboxKit && swift test` on a Mac; otherwise run the `ios.yml` workflow (manual) |

## Workflows (all manual unless noted)

| File | Folder | Output |
|---|---|---|
| ios.yml | ios-suite | tests + simulator screenshots → ci-logs / ci-logs-preview branches |
| testflight.yml | ios-suite | push to main (ios-suite/ios/**) → TestFlight. Needs the 6 secrets listed in the file |
| cratebox-app.yml | linux | release `app-latest` (+ mirror to Cratebox-Linux if `LEGACY_RELEASE_TOKEN` is set) |
| cratebox-windows.yml | linux | release `windows-latest` |
| cratebox-os.yml | linux | release `kiosk-latest` (ISO in parts) |
| reports.yml | web | on issue opened: appends "Report a problem" issues to `web/reports.txt` |

## Cross-folder

- Web → iOS: `ios-suite/cratebox.html` etc. are copies of `web/`; sync them when the web player changes.
- Linux ports `web/` (analysis, deck logic; `linux/src/maps.rs` is generated from the web `MIXXX_MAPS`, don't hand-edit).
  A behaviour change in one app should name the others it affects in the PR ("Other apps" section).
- `linux/distro/overlay/usr/bin/cratebox-update` reads `app-latest` from this repo, falling back to Cratebox-Linux.

## Open work (monorepo migration, 2026-11-11)

- truecurve not merged: it is private and this repo is public; waiting on Jonah (make this repo private, or keep
  truecurve separate). Its `ios-latest` release name also clashes with web's old `ios-latest`.
- Releases (`app-latest`, `windows-latest`, `kiosk-latest`) still live in Cratebox-Linux; installed Cratebox OS
  machines read from there until they've run the new updater once. Don't archive Cratebox-Linux before that.
- Secrets to re-add here: the TestFlight six (+ `IOS_PROFILE_HEAT_*` for personal/heat), `LEGACY_RELEASE_TOKEN`.
- Open PRs live in the old repos (iOS #31 into preview/truecurve-usb). Port by re-applying the branch under `ios-suite/`.
- Cloudflare Workers Builds: wrangler.toml moved to the root with `web/site/` paths; check the first build.
