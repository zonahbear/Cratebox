# CONTEXT_MAP.md: architecture map

Quick parse of the whole repo. Details live in each app's own map; read only the one you need.

## Layout

```
.agent/            machine memory: SYSTEM_PROMPT.md (rules), CONTEXT_MAP.md (this), GLOBAL_PLAN.json (tasks), REVIEW.md
.handoffs/         <YYYYMMDD-HHMM>Z_<agent>_<TASK-ID>_<role>.md memos (append-only log; 001-004 = old numbering) + LATEST.md (copy of the newest)
apps/web/        browser player cratebox.html (one file, no build; SOURCE OF TRUTH for it) + website/Worker in site/
apps/linux/      Rust/egui app: Cratebox OS (Linux kiosk ISO in distro/) and the Windows .exe
apps/ios-suite/  native Swift iOS app (ios/), Deck Bridge, a copy of the web files the parity oracles read
apps/truecurve/  NOT MERGED YET: Puffco heat curves (private repo; see GLOBAL_PLAN)
.github/workflows/ every workflow (GitHub ignores nested ones)
wrangler.toml      Cloudflare Worker for the website; paths point into apps/web/site/
LLMS.txt           project index (llms.txt layout); paste it into a chat that can't read the repo
AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .agents/rules/cratebox.md (Antigravity)   per-tool entry files, all pointing here
```

| App | Language | Map | Was repo |
|---|---|---|---|
| apps/web | HTML/JS, Python tests (Playwright) | apps/web/AGENTS.md | zonahbear/Cratebox |
| apps/linux | Rust (eframe/egui, cpal, midir, symphonia) | apps/linux/AGENTS.md | zonahbear/Cratebox-Linux |
| apps/ios-suite | Swift (SwiftUI, AVAudioEngine), XcodeGen | apps/ios-suite/AGENTS.md | zonahbear/cratebox-iOS-suite (preview/truecurve-usb) |

Each app also has a CLAUDE.md that only imports its AGENTS.md. App maps describe the app from inside: paths
relative to it, "this repo" = the app folder.

## Branches

- `main`: all apps, iOS = the **shipping** app. TestFlight builds from pushes touching `apps/ios-suite/ios/**`.
- `personal/heat`: main + Jonah's "Cratebox HEAT" iOS build in `apps/ios-suite/`. Never merges into main.
- Work branches `<agent>/<topic>`. Old per-repo branches, PRs and releases still live in the old repos.

## Deterministic verification (run before pushing; say in the PR which ran)

| App | Command |
|---|---|
| web | `python3 apps/web/start_cratebox.py` to run it; `python3 apps/web/tests/<name>.py` (Playwright) |
| linux | `cd apps/linux && python3 tests/make_tracks.py tests/music && cargo test --release` (needs `libasound2-dev`) |
| ios-suite | `cd apps/ios-suite/ios/CrateboxKit && swift test` on a Mac; otherwise Actions → ios.yml (manual) |
| website | `bash apps/web/site/build.sh` (Cloudflare runs it on every push to main) |

## Workflows (manual unless noted)

| File | App | Output |
|---|---|---|
| ios.yml | ios-suite | tests + simulator screenshots → ci-logs / ci-logs-preview branches |
| testflight.yml | ios-suite | push to main (apps/ios-suite/ios/**) → TestFlight; needs the 6 secrets in the file. Without them the run is green but says NOT BUILT / NOT UPLOADED: green ≠ shipped |
| cratebox-app.yml | linux | release `app-latest` (+ mirror to Cratebox-Linux when `LEGACY_RELEASE_TOKEN` is set) |
| cratebox-windows.yml | linux | release `windows-latest` |
| cratebox-os.yml | linux | release `kiosk-latest` (ISO in parts) |
| reports.yml | web | on issue opened: appends "Report a problem" issues to apps/web/reports.txt |

## Cross-app links

- web → ios-suite: `apps/ios-suite/cratebox.html` etc. are copies of apps/web; sync when the player changes.
- web → linux: linux ports the analysis and deck logic; `apps/linux/src/maps.rs` is generated from web's `MIXXX_MAPS`.
  linux tests fall back to `../web/tests/music`.
- HEAT safety rules shared by web, linux, personal/heat and truecurve (SYSTEM_PROMPT rule 3).
- `apps/linux/distro/overlay/usr/bin/cratebox-update` reads `app-latest` from this repo, then Cratebox-Linux.
