# Current Workspace State

The project's savestate. Every agent reads it first and **overwrites it** before handing off (Claude, ChatGPT/Codex,
Gemini, Grok, Copilot, humans). Keep it under ~60 lines; history goes in `.claudes/breadcrumbs.md`.
How to fill it in: docs/agents/HANDOFF.md.

Updated: 2026-11-11 08:15Z · by: claude · branch: claude/project-thread-b7gf7r

## 📍 Where We Stopped
- **Active Task:** Rebuild the monorepo after the first merge attempt (folders, root workflows, agent handoff files).
- **Current State:** Done on branch `claude/project-thread-b7gf7r`, PR open into `main`, waiting on Jonah's review.
- **Blockers/Bugs:** `main` (before this PR) has `<<<<<<<` markers in 7 files and a failing Cloudflare build.
  truecurve not merged: it's private and this repo is public (Jonah decides).

## 🔀 In Flight (one line per agent: agent · branch · task · state)
- claude · claude/project-thread-b7gf7r · monorepo rebuild · PR open, review needed

## 🛠️ Environmental Verification
- Last check: each folder's tree is byte-identical to its source repo (web 0701f9f, linux 55bfa3a, ios-suite
  38194ff) apart from the listed edits; no conflict markers; all workflow YAML parses; `web/site/build.sh` builds
  from the root; `cd linux && cargo check --tests` passes; updater fallback tested with a fake GitHub.
- Not run: full `cargo test` (needs tests/music), iOS tests (need a Mac / ios.yml), Cloudflare build (runs on merge).
- Commands: `cd linux && cargo test --release` · `python3 web/tests/<name>.py` · Actions → ios.yml (manual).

## 📦 Changes Introduced in This Session
- Moved `services/api` (web + linux mixed) into `web/` and `linux/`; iOS now from preview/truecurve-usb in `ios-suite/`.
- Workflows to root `.github/workflows/` with `working-directory`; `wrangler.toml` to the root (`web/site/` paths).
- `linux/distro/overlay/usr/bin/cratebox-update` tries this repo, then Cratebox-Linux; cratebox-app.yml can mirror.
- Agent files: AGENTS.md, agents.txt, CLAUDE.md, GEMINI.md, .github/copilot-instructions.md, docs/agents/,
  .github/pull_request_template.md, this file.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: review + merge the monorepo PR.
2. [ ] Jonah: truecurve decision (make repo private, or keep truecurve separate); then merge it into `truecurve/`.
3. [ ] Re-add secrets here: TestFlight six, `IOS_PROFILE_HEAT_*`, `LEGACY_RELEASE_TOKEN`.
4. [ ] After merge: check the first Cloudflare Workers Build on main.
5. [ ] Port iOS PR #31 (old repo) onto a branch here under `ios-suite/`.
6. [ ] Then archive (never delete) the old repos.
