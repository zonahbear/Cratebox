# Current Workspace State

Memo 001 · 2026-11-11 08:30Z · agent: claude (coder) · branch: claude/project-thread-b7gf7r

## 📍 Where We Stopped
- **Active Task:** MONO-1, rebuild the monorepo after the first merge attempt on main (0b52c0a).
- **Current State:** Done and pushed; PR open into `main`, waiting on Jonah's review. Branch `personal/heat` pushed.
- **Blockers/Bugs:** `main` (until this PR merges) has `<<<<<<<` markers in 7 files and a failing Cloudflare build;
  the live site is still the 0701f9f deploy. truecurve not merged (private repo, this one is public): MONO-2.

## 🛠️ Environmental Verification
- Each app's tree is byte-identical to its source (apps/web = Cratebox 0701f9f, apps/linux = Cratebox-Linux
  55bfa3a, apps/ios-suite = cratebox-iOS-suite preview/truecurve-usb 38194ff; personal/heat's = faaf702), apart from
  the edits listed below. Checked with `git rev-parse HEAD:<dir>` against `<sha>^{tree}` before the edits.
- No conflict markers: `git grep -nE '^<<<<<<< ' HEAD` → none. All workflow YAML parses.
- `bash apps/web/site/build.sh` → PASSED (11 files). `cd apps/linux && cargo check --tests` → PASSED.
- Updater fallback (Cratebox → Cratebox-Linux) → PASSED against a fake GitHub (404 on the first repo).
- Not run: full `cargo test` (needs tests/music), iOS tests (need macOS: Actions → ios.yml), Cloudflare build.

## 📦 Changes Introduced in This Session
- `services/api` (web + linux mixed, conflicted) → `apps/web/`, `apps/linux/`; iOS → `apps/ios-suite/` from
  preview/truecurve-usb with history (original SHAs kept).
- Workflows → root `.github/workflows/` with `working-directory: apps/<app>`; testflight on main + `apps/ios-suite/ios/**`;
  reports.yml → `apps/web/reports.txt`; cratebox-app.yml can mirror app-latest to Cratebox-Linux.
- `wrangler.toml` → repo root, paths `apps/web/site/...`.
- `apps/linux/distro/overlay/usr/bin/cratebox-update`: tries zonahbear/Cratebox, then Cratebox-Linux.
- `apps/linux/tests/*.rs`: test-track fallback `../web/tests/music`.
- New: `.agent/` (SYSTEM_PROMPT, CONTEXT_MAP, GLOBAL_PLAN.json, REVIEW), `.handoffs/`, LLMS.txt, agents.txt,
  AGENTS.md, CLAUDE.md, GEMINI.md, .github/copilot-instructions.md, PR template, root README/.gitignore,
  `apps/<app>/AGENTS.md`, a monorepo note at the top of each app's CLAUDE.md.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: review and merge the monorepo PR (MONO-1).
2. [ ] Jonah: truecurve decision (MONO-2), then merge it into `apps/truecurve/` with history (MONO-3).
3. [ ] Jonah: re-add secrets here (MONO-4): TestFlight six, `IOS_PROFILE_HEAT_BASE64`, `IOS_PROFILE_HEAT_WATCH_BASE64`, `LEGACY_RELEASE_TOKEN`.
4. [ ] After the merge: check the Workers Builds check run on main's head commit (MONO-5).
5. [ ] Port iOS PR #31 onto a branch here under `apps/ios-suite/` (MONO-6).
6. [ ] Then MONO-7 (releases) and MONO-8 (archive old repos; never delete).
